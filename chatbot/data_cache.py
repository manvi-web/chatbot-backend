"""
TTL-based cache for JSON data files that deployFunctions.py rewrites at runtime.
Thread-safe via a lock on first load and on TTL expiry.
"""
import json
import os
import threading
import time

_lock = threading.Lock()
_cache = {}
_TTL = 60  # seconds — short enough to pick up deployFunctions.py rewrites

_BASE = os.path.join(os.path.dirname(__file__), "..", "staticfiles", "assets", "Json")


def _path(name):
    return os.path.join(_BASE, name)


def _load(name):
    with open(_path(name)) as f:
        return json.load(f)


def get(name: str):
    """Return parsed JSON for *name*, reloading if the TTL has expired."""
    now = time.monotonic()
    with _lock:
        entry = _cache.get(name)
        if entry is None or now - entry["ts"] > _TTL:
            _cache[name] = {"data": _load(name), "ts": now}
        return _cache[name]["data"]


def invalidate(name: str = None):
    """Force a reload on next access. Pass None to clear everything."""
    with _lock:
        if name:
            _cache.pop(name, None)
        else:
            _cache.clear()


# ── Typed accessors ───────────────────────────────────────────────────────────

def apps():
    return get("applications.json")

def infra():
    return get("customInfrastructure.json")

def instances():
    return get("instancesListed.json")

def instance_info():
    return get("instanceInfo.json")

def build_params():
    return get("buildParameters.json")

def price_instances() -> dict:
    """Return the flat {instance_type: $/hr} price map from priceInstances.json."""
    try:
        data = get("priceInstances.json")
        return data.get("PriceInstances", [{}])[0]
    except Exception:
        return {}

def result_json() -> dict:
    """
    Return parsed result.json with a 60-second TTL.
    Uses a separate cache key so it doesn't collide with the Json/ assets.
    Falls back to {} on any read error.
    """
    import os as _os
    _RESULT_PATH = _os.path.join(_os.path.dirname(__file__), '..', 'scripts', 'result.json')
    _KEY = '__result_json__'
    import time as _time
    now = _time.monotonic()
    with _lock:
        entry = _cache.get(_KEY)
        if entry is None or now - entry['ts'] > _TTL:
            try:
                with open(_RESULT_PATH) as _f:
                    import json as _json
                    _data = _json.load(_f)
            except Exception:
                _data = {}
            _cache[_KEY] = {'data': _data, 'ts': now}
        return _cache[_KEY]['data']


def implemented_apps():
    return [a for a in apps().get("Applications", []) if a.get("implemented")]


def resolve_app(name: str):
    """Fuzzy-match an app by packageName or title. Returns the app dict or None."""
    if not name:
        return None
    nl = name.lower()
    # exact match first
    for a in implemented_apps():
        if a["packageName"].lower() == nl or a["title"].lower() == nl:
            return a
    # substring match
    for a in implemented_apps():
        if nl in a["title"].lower() or nl in a["packageName"].lower():
            return a
    return None


def all_instance_types() -> set:
    """Full set of specific instance types (e.g. 'g5.xlarge') from instancesListed.json."""
    types = set()
    for obj in instances().get("InstancesList", []):
        for sizes in obj.values():
            types.update(s.lower() for s in sizes)
    # also include masterInstances from customInfrastructure
    for m in infra().get("masterInstances", []):
        types.add(m["packageName"].lower())
    return types


def ebs_options() -> list:
    return [fs for fs in infra().get("FileSystem", []) if fs["title"].startswith("EBS")]


def fsx_options() -> list:
    return [fs for fs in infra().get("FileSystem", []) if fs["title"].startswith("FSX")]


def idle_options() -> list:
    return infra().get("IdleTermination", [])


def sagemaker_instances() -> list:
    return infra().get("SageMakerInstances", [])


def gpu_apps() -> set:
    """
    App titles that are GPU-primary (need GPU compute nodes).
    Derived from applications.json: any app with disableCPU=True is GPU-only.
    Also includes apps whose compatibleOS is Windows (Warp'M) since those are GPU workstations.
    """
    result = set()
    for a in implemented_apps():
        if a.get("disableCPU", False):
            result.add(a["title"].lower())
    # Also treat any app whose only compatible infra is SingleNode + Windows as GPU
    # (covers Warp'M which doesn't set disableCPU but is GPU-only in practice)
    for a in implemented_apps():
        if "Windows" in a.get("compatibleOS", []):
            result.add(a["title"].lower())
    return result


def get_config_schema(app: dict) -> dict:
    """
    Derive a config schema for a given app dict.
    For database apps (RDS/Redshift) returns a minimal schema — the LaunchConfirmCard
    handles database config display separately via databaseConfig on the payload.
    """
    compat_infra = app.get("compatibleInfra", [])

    # ── Database apps — return minimal schema, card handles the rest ─────────
    is_database = app.get("appType") == "database" or any(
        i.lower() in ("rds", "redshift") for i in compat_infra
    )
    if is_database:
        return {
            "appVersion": app.get("version", ""),
            "appCost":    app.get("cost", ""),
            "licenced":   app.get("licenced", False),
        }

    # ── HealthOmics / redirect apps — also minimal ────────────────────────────
    if app.get("redirectURL"):
        return {
            "appVersion": app.get("version", ""),
            "appCost":    app.get("cost", ""),
            "licenced":   app.get("licenced", False),
        }

    compat_os    = app.get("compatibleOS", [])
    compat_infra = app.get("compatibleInfra", [])
    is_gpu       = app["title"].lower() in gpu_apps()

    # ── OS — with display titles from os array ───────────────────────────────
    os_display_map = {
        o["packageName"]: o.get("title", o["packageName"])
        for o in apps().get("os", [])
    }
    os_choices_with_labels = [
        {"value": o, "label": os_display_map.get(o, o)}
        for o in compat_os
    ]
    os_schema = (
        {"fixed": True, "value": compat_os[0], "label": os_display_map.get(compat_os[0], compat_os[0])}
        if len(compat_os) == 1
        else {"fixed": False, "choices": os_choices_with_labels, "default": compat_os[0]}
    )

    # ── Cluster type ──────────────────────────────────────────────────────────
    ct_choices = []
    if any("single" in i.lower() for i in compat_infra):
        ct_choices.append("SINGLE")
    if any("parallel" in i.lower() for i in compat_infra):
        ct_choices.append("PARALLEL")
    if any("sagemaker" in i.lower() for i in compat_infra):
        ct_choices.append("SAGEMAKER")

    ct_schema = (
        {"fixed": True, "value": ct_choices[0]}
        if len(ct_choices) == 1
        else {"fixed": False, "choices": ct_choices, "default": ct_choices[0]}
    )

    # ── Instance type — scoped to families valid for this app ─────────────────
    is_sagemaker = any("sagemaker" in i.lower() for i in compat_infra)
    disable_cpu  = app.get("disableCPU", False)

    if is_sagemaker:
        # SageMaker uses ml.* instances from SageMakerInstances — include displayTitle
        sm_list = sagemaker_instances()
        node_choices = [
            {"value": i["packageName"], "label": i.get("displayTitle", i["packageName"]), "cost": i.get("cost", "0")}
            for i in sm_list
        ]
        default_node = node_choices[0]["value"] if node_choices else None
        node_schema = {
            "fixed": False,
            "choices": node_choices,
            "default": default_node,
            "grouped": False,
            "sagemaker": True,
        }
    else:
        all_families = infra().get("Instances", [])
        if is_gpu or disable_cpu:
            preferred_families = [f["family"] for f in all_families if f.get("type") == "GPU"]
            fallback_families  = [f["family"] for f in all_families if f.get("type") == "CPU"]
        else:
            preferred_families = [f["family"] for f in all_families if f.get("type") == "CPU"]
            fallback_families  = []

        # Collect specific instance types for preferred families from instancesListed
        node_choices = []
        try:
            for obj in instances().get("InstancesList", []):
                for family, sizes in obj.items():
                    if family in preferred_families:
                        node_choices.extend(sizes)
            if not node_choices:
                for obj in instances().get("InstancesList", []):
                    for family, sizes in obj.items():
                        if family in fallback_families:
                            node_choices.extend(sizes)
        except Exception:
            pass

        # Always include master instances as valid node choices
        master_types = [m["packageName"] for m in infra().get("masterInstances", [])]
        for mt in master_types:
            if mt not in node_choices:
                node_choices.append(mt)

        default_node = (
            next((n for n in node_choices if any(g in n for g in [f["family"] for f in all_families if f.get("type") == "GPU"])), None) or
            next((n for n in node_choices if any(c in n for c in [f["family"] for f in all_families if f.get("type") == "CPU"])), None) or
            (node_choices[0] if node_choices else None)
        )

        node_schema = {
            "fixed": False,
            "choices": node_choices,
            "default": default_node,
            "grouped": True,
        }

    # ── Idle timeout ──────────────────────────────────────────────────────────
    idle_choices = [
        {"value": int(t["packageName"]), "label": t["displayTitle"]}
        for t in idle_options()
    ]
    idle_default = idle_choices[0]["value"] if idle_choices else 0
    idle_schema = {
        "fixed": False,
        "choices": idle_choices,
        "default": idle_default,
    }

    # ── Volumes — optional, single-choice per type ────────────────────────────
    ebs_choices = [
        {"value": int(fs["packageName"]), "label": fs["displayTitle"], "cost": fs.get("cost", "0")}
        for fs in ebs_options()
    ]
    fsx_choices = [
        {"value": int(fs["packageName"]), "label": fs["displayTitle"], "cost": fs.get("cost", "0")}
        for fs in fsx_options()
    ]

    ebs_schema = {"fixed": False, "optional": True, "choices": ebs_choices, "default": None}
    fsx_schema = {"fixed": False, "optional": True, "choices": fsx_choices, "default": None}

    # ── Data sources — always fixed, auto-set from app ────────────────────────
    ds_titles = [
        d["title"] for d in apps().get("DataSources", [])
        if d["packageName"] in app.get("compatibleDS", [])
    ]
    ds_schema = {"fixed": True, "value": ds_titles}

    # ── Node groups — only relevant for PARALLEL clusters ────────────────────
    # Everything comes from JSON — no hardcoded values.
    _all_families = infra().get("Instances", [])
    cpu_families = [f["family"] for f in _all_families if f.get("type") == "CPU"]
    gpu_families = [f["family"] for f in _all_families if f.get("type") == "GPU"]

    # CPU categories come from customInfrastructure.json → ParallelClusterConfig
    # If ParallelClusterConfig is absent, derive categories from the number of
    # size tiers in instancesListed.json (small=first third, medium=middle, large=last third)
    pc_config = infra().get("ParallelClusterConfig", {})
    cpu_categories = pc_config.get("cpuCategories", [])
    if not cpu_categories:
        # Derive from the first CPU family's instance list length
        first_cpu_family = cpu_families[0] if cpu_families else None
        tier_count = 3  # default to 3 tiers
        if first_cpu_family:
            for obj in instances().get("InstancesList", []):
                if first_cpu_family in obj:
                    n = len(obj[first_cpu_family])
                    tier_count = min(n, 3)
                    break
        cpu_categories = [
            {"value": f"tier{i+1}", "label": f"Tier {i+1}"}
            for i in range(tier_count)
        ]
    max_groups    = pc_config.get("maxNodeGroups", 10)
    default_count = pc_config.get("defaultNodeCount", 2)

    # GPU categories are derived from instanceInfo.json — the distinct GpuCount
    # values that actually exist for GPU instances in this deployment.
    # This means if the data only has 1-GPU and 4-GPU instances, we only show those.
    gpu_counts_seen = set()
    try:
        for item in instance_info().get("InstanceInfo", []):
            if item.get("Type") == "GPU":
                gc = item.get("GpuCount")
                if gc and gc != "NA":
                    try:
                        gpu_counts_seen.add(int(gc))
                    except (ValueError, TypeError):
                        pass
    except Exception:
        pass

    gpu_categories = [
        {"value": str(gc), "label": f"{gc} GPU"}
        for gc in sorted(gpu_counts_seen)
    ] if gpu_counts_seen else []  # empty means no GPU instance data available

    node_groups_schema = {
        "applicable":      "PARALLEL" in ct_choices,
        "cpu_families":    cpu_families,
        "gpu_families":    gpu_families,
        "cpu_categories":  cpu_categories,
        "gpu_categories":  gpu_categories,
        "max_groups":      max_groups,
        "default_count":   default_count,
    }

    return {
        "os":          os_schema,
        "clusterType": ct_schema,
        "nodeType":    node_schema,
        "nodeGroups":  node_groups_schema,
        "idleTimeout": idle_schema,
        "ebsVolume":   ebs_schema,
        "fsxVolume":   fsx_schema,
        "dataSources": ds_schema,
        # App metadata — used by the frontend card for display
        "appVersion":  app.get("version", ""),
        "appCost":     app.get("cost", ""),
        "licenced":    app.get("licenced", False),
    }
