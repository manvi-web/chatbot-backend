"""
launch.py — Launch extraction pipeline.

Handles the fast-path when a user gives enough info upfront:
  1. Build extraction prompt from live data_cache data
  2. Call LLM to extract params as JSON
  3. Validate + fill defaults against live JSON
  4. Return payload + config schema + cost estimate

Also owns <launch-payload> tag extraction from Agent conversational replies.
"""
import json
import logging
import re

from django.http import JsonResponse

from chatbot import cost as cost_mod
from chatbot import data_cache as dc
from chatbot import llm

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# <launch-payload> extraction (from Agent conversational replies)
# ---------------------------------------------------------------------------

def extract_payload(reply_text: str, email: str):
    """
    Extract <launch-payload>...</launch-payload> and inject real email.
    Returns (clean_text, payload_dict_or_None).
    """
    match = re.search(r'<launch-payload>(.*?)</launch-payload>', reply_text, re.DOTALL)
    if not match:
        return reply_text, None
    raw = match.group(1).strip()
    try:
        payload = json.loads(raw)
        payload['email'] = email
        clean = reply_text.replace(match.group(0), '').strip()
        return clean, payload
    except json.JSONDecodeError as e:
        logger.warning("launch: payload JSON parse error: " + str(e))
        return reply_text, None


# ---------------------------------------------------------------------------
# Extraction prompt builder
# ---------------------------------------------------------------------------

def _build_launch_system_prompt() -> str:
    """
    Build the extraction prompt with full instance type lists from data_cache
    so the LLM never has to hallucinate a size suffix.
    """
    apps    = [{"title": a["title"], "pkg": a["packageName"]} for a in dc.implemented_apps()]
    os_list = [o["packageName"] for o in dc.apps().get("os", [])]

    instance_map = {}
    for obj in dc.instances().get("InstancesList", []):
        for family, sizes in obj.items():
            instance_map[family] = sizes
    master_types = [m["packageName"] for m in dc.infra().get("masterInstances", [])]

    ebs  = [{"label": fs["displayTitle"], "gb": int(fs["packageName"])} for fs in dc.ebs_options()]
    fsx  = [{"label": fs["displayTitle"], "gb": int(fs["packageName"])} for fs in dc.fsx_options()]
    idle = [{"label": t["displayTitle"],  "minutes": int(t["packageName"])} for t in dc.idle_options()]

    app_names_str = ", ".join(a["title"] for a in dc.implemented_apps())

    # Build dynamic app name mapping from live app list
    app_aliases = []
    for a in dc.implemented_apps():
        title = a["title"].lower().replace(" ", "").replace("'", "").replace("-", "")
        pkg   = a["packageName"]
        short = ''.join(c for c in title if not c.isdigit() and c != '.')
        if short != pkg.lower():
            app_aliases.append(f"{short}→{pkg}")
        app_aliases.append(f"{title}→{pkg}")
    app_aliases += ["rds→amazonrds", "mysql→amazonrds", "postgres→amazonrds",
                    "redshift→amazonredshift", '"data warehouse"→amazonredshift']
    app_alias_str = ", ".join(dict.fromkeys(app_aliases))

    return f"""You extract launch parameters for the Numen HPC platform. Return ONLY valid JSON.

AVAILABLE APPS (use exact pkg value):
{json.dumps(apps, indent=2)}

AVAILABLE OS:
{json.dumps(os_list)}

AVAILABLE INSTANCE TYPES (pick ONLY from these exact strings):
{json.dumps(instance_map, indent=2)}

MASTER NODE TYPES (for parallelCluster master node only):
{json.dumps(master_types)}

EBS VOLUMES:
{json.dumps(ebs)}

FSX VOLUMES:
{json.dumps(fsx)}

IDLE TIMEOUT OPTIONS:
{json.dumps(idle)}

RETURN FORMAT:
{{"params": {{"applicationName": "<pkg or null>", "os": "<pkg or null>", "clusterType": "<SINGLE|PARALLEL|SAGEMAKER|RDS|REDSHIFT or null>", "nodeType": "<exact instance type or null>", "instanceName": "<lowercase-hyphenated name or null>", "idleTimeout": "<minutes int or null>", "ebsSize": "<gb int or null>", "fsxSize": "<gb int or null>", "dbEngine": "<mysql|postgres|mariadb|aurora-mysql|aurora-postgresql|oracle-ee|sqlserver-se or null>", "dbName": "<database name or null>"}}}}

RULES:
- Extract ONLY what the user explicitly said. Use null for anything not mentioned.
- nodeType MUST be one of the exact strings in AVAILABLE INSTANCE TYPES. Never invent one.
- instanceName: extract only if the user explicitly provides a name (e.g. "call it relion-july"). Lowercase, hyphens only, max 30 chars. Use null if not mentioned.
- Match app names flexibly: {app_alias_str}
- For amazonrds or amazonredshift apps, set clusterType to RDS or REDSHIFT respectively.
- If no app is mentioned at all: {{"error": "Which app would you like to launch? Available: {app_names_str}"}}
- ONLY return JSON. No explanation, no markdown."""


# ---------------------------------------------------------------------------
# Validate and fill defaults
# ---------------------------------------------------------------------------

def _validate_and_fill(params: dict):
    """
    Validate LLM-extracted params against live data, fill defaults.
    Returns (payload_dict, reply_str, cost_dict, schema_dict)
    or (None, error_str, None, None).
    """
    app = dc.resolve_app(params.get("applicationName"))
    if not app:
        titles = ", ".join(a["title"] for a in dc.implemented_apps())
        return None, f"I couldn't find that app. Available: {titles}", None, None

    compat_os   = [o.lower() for o in app.get("compatibleOS", [])]
    os_val      = (params.get("os") or "").lower()
    if os_val not in compat_os:
        os_val = compat_os[0] if compat_os else ""

    compat_infra = app.get("compatibleInfra", [])
    ct = (params.get("clusterType") or "").upper()
    ct_map = {"SINGLE": "singlenode", "PARALLEL": "parallelcluster",
              "SAGEMAKER": "sagemaker", "RDS": "rds", "REDSHIFT": "redshift"}
    infra_lower = [i.lower() for i in compat_infra]

    if any("rds" == i.lower() for i in compat_infra):
        ct = "RDS"
    elif any("redshift" == i.lower() for i in compat_infra):
        ct = "REDSHIFT"
    elif any("sagemaker" in i.lower() for i in compat_infra):
        ct = "SAGEMAKER"
    elif any("healthomics" in i.lower() for i in compat_infra):
        if app.get("redirectURL"):
            return None, f"{app['title']} opens in a separate portal. Visit: {app['redirectURL']}", None, None
        ct = "SINGLE"
    elif ct not in ct_map or ct_map[ct] not in infra_lower:
        if any("single" in i.lower() for i in compat_infra):
            ct = "SINGLE"
        elif any("parallel" in i.lower() for i in compat_infra):
            ct = "PARALLEL"
        else:
            ct = "SINGLE"

    # Database apps — early return
    if ct in ("RDS", "REDSHIFT"):
        if ct == "RDS":
            rds_defaults = dc.build_params().get("rds", {})
            db_cfg = {
                "dbType":               "RDS",
                "engine":               params.get("dbEngine",     rds_defaults.get("DBEngine", "mysql")),
                "engineVersion":        params.get("engineVersion", ""),
                "dbTemplate":           "dev-test",
                "dbInstanceClass":      params.get("nodeType",      rds_defaults.get("DBInstanceClass", "db.t3.medium")),
                "multiAZ":              params.get("multiAZ",       False),
                "storageType":          "gp3",
                "allocatedStorage":     int(params.get("ebsSize",   rds_defaults.get("AllocatedStorage", 20))),
                "maxAllocatedStorage":  int(rds_defaults.get("MaxAllocatedStorage", 200)),
                "dbName":               params.get("dbName",        rds_defaults.get("DBName", "numendatabase")),
                "backupRetentionPeriod": int(rds_defaults.get("BackupRetentionPeriod", 7)),
            }
            display = f"{db_cfg['engine']}, {db_cfg['dbInstanceClass']}, {db_cfg['allocatedStorage']}GB"
        else:
            rs_defaults = dc.build_params().get("redshift", {})
            db_cfg = {
                "dbType":        "Redshift",
                "nodeType":      params.get("nodeType",      rs_defaults.get("NodeType", "ra3.large")),
                "numberOfNodes": int(params.get("numberOfNodes", rs_defaults.get("NumberOfNodes", 2))),
                "clusterType":   "multi-node",
                "dbName":        params.get("dbName",        rs_defaults.get("DBName", "numendw")),
                "backupRetentionPeriod": int(rs_defaults.get("AutomatedSnapshotRetentionPeriod", 7)),
            }
            display = f"{db_cfg['nodeType']}, {db_cfg['numberOfNodes']} nodes"

        payload = {
            "applicationName": app["packageName"],
            "type":            "DATABASE",
            "clusterType":     ct,
            "databaseConfig":  db_cfg,
            "idleTimeout":     {"value": 0, "unit": "MINUTES", "behaviour": "STOP"},
            "email":           params.get("email", ""),
        }
        if params.get("instanceName"):
            payload["instanceName"] = params["instanceName"][:30].lower().replace(" ", "-").replace("_", "-")
        cost   = cost_mod.estimate(payload)
        schema = dc.get_config_schema(app)
        reply  = (
            f"Got it — here's your {app['title']} config ({display}). "
            f"Adjust anything in the card below, then hit Confirm."
        )
        return payload, reply, cost, schema

    # Compute apps — instance type resolution
    valid_types  = dc.all_instance_types()
    node         = (params.get("nodeType") or "").lower()
    is_gpu_app   = app["title"].lower() in dc.gpu_apps()
    disable_cpu  = app.get("disableCPU", False)

    if ct == "SAGEMAKER":
        sm_instances = dc.sagemaker_instances()
        sm_types     = [i["packageName"] for i in sm_instances]
        if node not in sm_types:
            node = sm_types[0] if sm_types else ""
    elif node not in valid_types:
        if node and "." not in node:
            matches = sorted(t for t in valid_types if t.startswith(node + "."))
            node = matches[0] if matches else None
        if not node or node not in valid_types:
            all_infra = dc.infra().get("Instances", [])
            if ct == "PARALLEL":
                masters = dc.infra().get("masterInstances", [])
                node = masters[0]["packageName"] if masters else None
            elif is_gpu_app or disable_cpu:
                gpu_fams = [f["family"] for f in all_infra if f.get("type") == "GPU"]
                node = None
                for obj in dc.instances().get("InstancesList", []):
                    for fam, sizes in obj.items():
                        if fam in gpu_fams and sizes:
                            node = sizes[0].lower(); break
                    if node: break
            else:
                cpu_fams = [f["family"] for f in all_infra if f.get("type") == "CPU"]
                node = None
                for obj in dc.instances().get("InstancesList", []):
                    for fam, sizes in obj.items():
                        if fam in cpu_fams and sizes:
                            node = sizes[0].lower(); break
                    if node: break
            if not node:
                node = next(iter(valid_types), "")

    valid_idle   = [int(t["packageName"]) for t in dc.idle_options()]
    idle_default = valid_idle[0] if valid_idle else 0
    try:
        idle = int(params.get("idleTimeout", idle_default))
    except (ValueError, TypeError):
        idle = idle_default
    if idle not in valid_idle:
        idle = min(valid_idle, key=lambda x: abs(x - idle)) if valid_idle else idle_default

    volumes   = []
    ebs_valid = {int(fs["packageName"]) for fs in dc.ebs_options()}
    fsx_valid = {int(fs["packageName"]) for fs in dc.fsx_options()}
    for vol_type, param_key, valid_set in [("EBS", "ebsSize", ebs_valid), ("FSX", "fsxSize", fsx_valid)]:
        raw = params.get(param_key)
        if raw:
            try:
                size = int(raw)
                if size not in valid_set:
                    size = min(valid_set, key=lambda x: abs(x - size))
                volumes.append({"type": vol_type, "size": size, "sizeUnit": "GB"})
            except (ValueError, TypeError):
                pass

    ds = [d["title"] for d in dc.apps().get("DataSources", [])
          if d["packageName"] in app.get("compatibleDS", [])]

    node_groups = params.get("nodeGroups") or []
    if ct == "PARALLEL" and not node_groups:
        all_infra_families = dc.infra().get("Instances", [])
        if is_gpu_app:
            gpu_fams       = [f["family"] for f in all_infra_families if f.get("type") == "GPU"]
            default_family = gpu_fams[0] if gpu_fams else "g5"
            default_type   = "gpu"
            gpu_counts     = sorted({
                int(i["GpuCount"]) for i in dc.instance_info().get("InstanceInfo", [])
                if i.get("Type") == "GPU" and i.get("GpuCount") not in (None, "NA")
            })
            default_cat = str(gpu_counts[0]) if gpu_counts else "1"
        else:
            cpu_fams       = [f["family"] for f in all_infra_families if f.get("type") == "CPU"]
            default_family = cpu_fams[0] if cpu_fams else None
            default_type   = "cpu"
            pc_cats        = dc.infra().get("ParallelClusterConfig", {}).get("cpuCategories", [])
            default_cat    = pc_cats[0]["value"] if pc_cats else "tier1"
        node_groups = (
            [{"code": f"{default_type}-{default_family}-{default_cat}",
              "count": dc.infra().get("ParallelClusterConfig", {}).get("defaultNodeCount", 2)}]
            if default_family else []
        )

    payload = {
        "applicationName": app["packageName"],
        "type":            "APPLICATION",
        "amiId":           None,
        "packages":        [],
        "os":              os_val,
        "dataSources":     ds,
        "clusterType":     ct,
        "nodes":           [{"code": node, "isMaster": True}] if ct == "PARALLEL" else [{"code": node}],
        "nodeGroups":      node_groups,
        "volumes":         volumes,
        "idleTimeout": {
            "value":     idle,
            "unit":      "MINUTES",
            "behaviour": "TERMINATE" if ct == "PARALLEL" else "STOP",
        },
        "email": params.get("email", ""),
    }
    if params.get("instanceName"):
        payload["instanceName"] = params["instanceName"][:30].lower().replace(" ", "-").replace("_", "-")

    cost   = cost_mod.estimate(payload)
    schema = dc.get_config_schema(app)

    cluster_label = "Single Node" if ct == "SINGLE" else "Parallel Cluster"
    vol_parts     = [f"{v['type']} {v['size']}GB" for v in volumes]
    vol_str       = ", ".join(vol_parts) if vol_parts else "no extra storage"
    reply = (
        f"Got it — here's your {app['title']} config on a {cluster_label} "
        f"({node}, {idle} min idle timeout, {vol_str}). "
        f"{cost['note']}. "
        f"Adjust anything in the card below, then hit Confirm."
    )
    return payload, reply, cost, schema


# ---------------------------------------------------------------------------
# Main launch handler
# ---------------------------------------------------------------------------

def handle_launch(message: str, history: list, email: str, current_payload: dict = None):
    """
    Extract params from message, merge onto current_payload if present,
    validate, return launch_confirm JsonResponse.
    """
    try:
        prompt      = _build_launch_system_prompt()
        llm_history = _clean_history(history[-6:])
        llm_history.append({"role": "user", "content": message})

        result = llm.extract_launch_params(prompt, llm_history)

        if result.get("error"):
            return JsonResponse({"reply": result["error"], "action": "info"})

        params = result.get("params", {})
        params = {k: v for k, v in params.items() if v is not None and str(v).lower() != "null"}
        params["email"] = email

        if current_payload and any(k != "email" for k in params):
            if "applicationName" not in params and current_payload.get("applicationName"):
                params["applicationName"] = current_payload["applicationName"]
            if "clusterType" not in params and current_payload.get("clusterType"):
                params["clusterType"] = current_payload["clusterType"]
            if "nodeType" not in params and current_payload.get("nodes"):
                params["nodeType"] = current_payload["nodes"][0]["code"]
            if "os" not in params and current_payload.get("os"):
                params["os"] = current_payload["os"]
            if "idleTimeout" not in params and current_payload.get("idleTimeout"):
                params["idleTimeout"] = current_payload["idleTimeout"]["value"]
            if "nodeGroups" not in params and current_payload.get("nodeGroups"):
                params["nodeGroups"] = current_payload["nodeGroups"]
            if "instanceName" not in params and current_payload.get("instanceName"):
                params["instanceName"] = current_payload["instanceName"]
            for v in current_payload.get("volumes", []):
                if v["type"] == "EBS" and "ebsSize" not in params:
                    params["ebsSize"] = v["size"]
                if v["type"] == "FSX" and "fsxSize" not in params:
                    params["fsxSize"] = v["size"]

        if not any(k != "email" for k in params):
            app_names = ", ".join(a["title"] for a in dc.implemented_apps())
            return JsonResponse({
                "reply": f"I'd love to help you launch something. Which app are you looking to run?\n\nAvailable: {app_names}",
                "action": "info",
            })

        payload, reply, cost, schema = _validate_and_fill(params)
        if payload is None:
            return JsonResponse({"reply": reply, "action": "info"})

        return JsonResponse({
            "reply":      reply,
            "action":     "launch_confirm",
            "intent":     "launch",
            "payload":    payload,
            "cost":       cost,
            "schema":     schema,
            "had_config": True,
            "llm_reply":  f"Configured {payload['applicationName']} on {payload['nodes'][0]['code']}.",
        })

    except json.JSONDecodeError:
        return JsonResponse({"reply": "I had trouble parsing that. Could you rephrase?", "action": "info"})
    except Exception as e:
        logger.error(f"launch.handle_launch error: {e}")
        return JsonResponse({"reply": "Something went wrong on my end. Try again.", "action": "error"})


def _clean_history(history: list) -> list:
    cleaned = []
    for h in history:
        role    = h.get("role", "user")
        content = h.get("llm_content") or h.get("content", "")
        if isinstance(content, str):
            content = content[:300]
        cleaned.append({"role": role, "content": content})
    return cleaned
