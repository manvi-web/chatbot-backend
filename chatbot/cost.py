"""
Cost estimation for a launch payload.
Uses priceInstances.json (written by deployFunctions.py) for live $/hr,
falls back to customInfrastructure.json cost fields if pricing data is absent.
"""
import logging
from chatbot import data_cache as dc

logger = logging.getLogger(__name__)


def _instance_hourly(instance_type: str) -> float:
    """Return $/hr for a specific instance type, or 0.0 if unknown."""
    try:
        price_data = dc.get("priceInstances.json")
        prices = price_data.get("PriceInstances", [{}])[0]
        val = prices.get(instance_type) or prices.get(instance_type.lower())
        if val:
            return float(val)
    except Exception:
        pass
    # fallback: look up family cost from customInfrastructure
    family = instance_type.split(".")[0].lower() if "." in instance_type else instance_type.lower()
    for inst in dc.infra().get("Instances", []):
        if inst.get("family", "").lower() == family:
            try:
                return float(inst.get("cost", 0)) / 730  # monthly → hourly
            except (ValueError, TypeError):
                pass
    return 0.0


def _resolve_node_group_instances(code: str) -> list:
    """
    Resolve a nodeGroup code (e.g. "cpu-c6i-small", "gpu-g5-1") to a list
    of specific instance types, mirroring getInstances / getInstancesGPU in numen/views.py.

    CPU category values (small/medium/large) come from customInfrastructure.json
    → ParallelClusterConfig → cpuCategories[].value — positional slices of the family list.

    GPU category values are the GpuCount as a string ("1", "4", "8") — derived from
    instanceInfo.json, same as getInstancesGPU.

    Returns [] if the code can't be resolved.
    """
    try:
        parts = code.lower().split("-")
        if len(parts) < 3:
            return []
        kind, family, category = parts[0], parts[1], parts[2]

        # Use instancesListed.json — instanceListedPC.json is not used in this deployment
        data = dc.instances()

        instances_list = data.get("InstancesList", [])
        family_instances = []
        for obj in instances_list:
            if family in obj:
                family_instances = obj[family]
                break

        if not family_instances:
            return []

        if kind == "cpu":
            pc_config   = dc.infra().get("ParallelClusterConfig", {})
            cpu_cats    = [c["value"] for c in pc_config.get("cpuCategories", [])]
            # If no ParallelClusterConfig, derive tier names from instance list position
            if not cpu_cats:
                cpu_cats = [f"tier{i+1}" for i in range(3)]
            n = len(family_instances)
            avg = round(n / 2)
            # Map each category value to its slice by position in the list
            cat_slices = {}
            if len(cpu_cats) >= 1:
                cat_slices[cpu_cats[0]] = family_instances[:3]
            if len(cpu_cats) >= 2:
                cat_slices[cpu_cats[1]] = family_instances[max(0, avg - 1): avg + 2]
            if len(cpu_cats) >= 3:
                cat_slices[cpu_cats[2]] = family_instances[-3:]
            return cat_slices.get(category, family_instances[:3])

        elif kind == "gpu":
            # GPU category is the GpuCount as a string — filter instanceInfo.json
            try:
                gpu_count = int(category)
            except ValueError:
                return []
            try:
                info_list = dc.instance_info().get("InstanceInfo", [])
            except Exception:
                return []
            return [
                i["InstanceType"] for i in info_list
                if i["InstanceType"] in family_instances
                and i.get("Type") == "GPU"
                and i.get("GpuCount") == gpu_count
            ][:3]

    except Exception as e:
        logger.warning(f"_resolve_node_group_instances({code}): {e}")
    return []


def _node_group_hourly(code: str, count: int) -> float:
    """
    Estimate hourly cost for a nodeGroup entry.
    Resolves the code to instance types and averages their prices.
    """
    instances = _resolve_node_group_instances(code)
    if not instances:
        return 0.0
    prices = [_instance_hourly(inst) for inst in instances]
    prices = [p for p in prices if p > 0]
    if not prices:
        return 0.0
    avg_price = sum(prices) / len(prices)
    return avg_price * count


def _storage_monthly(volumes: list) -> float:
    total = 0.0
    ebs_map = {int(fs["packageName"]): float(fs.get("cost", 0))
               for fs in dc.ebs_options()}
    fsx_map = {int(fs["packageName"]): float(fs.get("cost", 0))
               for fs in dc.fsx_options()}
    for v in volumes:
        try:
            size = int(v["size"])
            if v["type"] == "EBS":
                total += ebs_map.get(size, 0.0)
            elif v["type"] == "FSX":
                total += fsx_map.get(size, 0.0)
        except (KeyError, ValueError, TypeError):
            pass
    return total


def estimate(payload: dict) -> dict:
    """
    Returns:
        {
          "instance_hourly": 1.23,
          "storage_monthly": 168.0,
          "note": "~$1.23/hr compute + $168/mo storage"
        }
    """
    try:
        # Database payloads have no EC2 nodes — return cost-unavailable gracefully
        if payload.get("type") == "DATABASE":
            return {"instance_hourly": 0, "storage_monthly": 0, "note": "Cost data unavailable"}

        nodes        = payload.get("nodes", [])
        node_groups  = payload.get("nodeGroups", [])
        cluster_type = payload.get("clusterType", "SINGLE")

        compute_hourly = 0.0

        if cluster_type == "SINGLE":
            if nodes:
                compute_hourly = _instance_hourly(nodes[0]["code"])
        else:
            # Master node (always a specific instance type like c6i.xlarge)
            if nodes:
                compute_hourly += _instance_hourly(nodes[0]["code"])
            # Compute node groups (codes like "cpu-c6i-small", "gpu-g5-1")
            for ng in node_groups:
                count = int(ng.get("count", 1))
                compute_hourly += _node_group_hourly(ng.get("code", ""), count)

        storage_mo = _storage_monthly(payload.get("volumes", []))

        parts = []
        if compute_hourly:
            parts.append(f"~${compute_hourly:.2f}/hr compute")
        if storage_mo:
            parts.append(f"~${storage_mo:.0f}/mo storage")
        note = " + ".join(parts) if parts else "Cost data unavailable"

        return {
            "instance_hourly": round(compute_hourly, 4),
            "storage_monthly": round(storage_mo, 2),
            "note": note,
        }
    except Exception as e:
        logger.warning(f"cost.estimate failed: {e}")
        return {"instance_hourly": 0, "storage_monthly": 0, "note": "Cost data unavailable"}
