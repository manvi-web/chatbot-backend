"""
resources.py — Resource management and result.json utilities.

Handles:
  - Reading result.json (manageable resources, user session history)
  - Stop / Start EC2, RDS, Redshift
  - Terminate CloudFormation stacks
  - Parsing <action-payload> from LLM replies
"""
import datetime
import logging
import os
import re

import boto3

from chatbot import data_cache as dc

logger = logging.getLogger(__name__)

_REGION          = os.environ.get('CHATBOT_AWS_REGION', 'us-east-1')
_ec2_client      = boto3.client('ec2',            region_name=_REGION)
_rds_client      = boto3.client('rds',            region_name=_REGION)
_redshift_client = boto3.client('redshift',       region_name=_REGION)
_cfn_client      = boto3.client('cloudformation', region_name=_REGION)

_RESULT_JSON = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'result.json')


def _read_result_json() -> dict:
    return dc.result_json()


# ---------------------------------------------------------------------------
# Manageable resources
# ---------------------------------------------------------------------------

def get_manageable_resources() -> list:
    """
    Return all Running + Stopped + Inprogress instances that the agent can
    stop, start, or terminate.
    Each entry: {name, instanceId, resourceType, stackName, status}
    """
    resources = []
    try:
        data = _read_result_json()
        for bucket in ('Running', 'Stopped', 'Inprogress'):
            for item in data.get(bucket, []):
                rt = item.get('resourceType', item.get('type', '')).upper()
                if rt in ('EC2', 'SINGLE', 'PARALLEL', 'SINGLENODE', 'PARALLELCLUSTER',
                          'APPLICATION', 'COMPUTE'):
                    rt = 'EC2'
                elif rt in ('RDS', 'DATABASE_RDS'):
                    rt = 'RDS'
                elif rt in ('REDSHIFT', 'DATABASE_REDSHIFT'):
                    rt = 'REDSHIFT'
                resources.append({
                    'name':         item.get('displayName') or item.get('StackName', 'unknown'),
                    'instanceId':   item.get('instanceId', ''),
                    'resourceType': rt,
                    'stackName':    item.get('StackName', ''),
                    'status':       bucket.lower(),
                })
    except Exception as e:
        logger.debug("resources: manageable resources read failed: " + str(e))
    return resources


# ---------------------------------------------------------------------------
# CloudFormation physical ID helper
# ---------------------------------------------------------------------------

def get_cf_physical_id(stack_name: str, resource_type: str) -> str:
    """Return the PhysicalResourceId for the first resource of the given type in a CF stack."""
    try:
        paginator = _cfn_client.get_paginator('list_stack_resources')
        for page in paginator.paginate(StackName=stack_name):
            for r in page.get('StackResourceSummaries', []):
                if r.get('ResourceType') == resource_type:
                    return r.get('PhysicalResourceId', '')
    except Exception as e:
        logger.warning("resources: CF physical id lookup failed for %s: %s" % (stack_name, str(e)))
    return ''


# ---------------------------------------------------------------------------
# Execute stop / start / terminate
# ---------------------------------------------------------------------------

def execute_action(action: str, resource_type: str,
                   instance_id: str, stack_name: str) -> str:
    """
    Execute stop, start, or terminate for EC2, RDS, or Redshift.
    Returns a human-readable result string.
    """
    try:
        rt = resource_type.upper()

        if rt == 'EC2':
            if not instance_id:
                return "❌ Could not resolve the EC2 instance ID. Please check the instance name."
            if action == 'stop':
                _ec2_client.stop_instances(InstanceIds=[instance_id])
                return f"✅ Stop signal sent to EC2 instance `{instance_id}`. It will shut down within a minute."
            else:
                _ec2_client.start_instances(InstanceIds=[instance_id])
                return f"✅ Start signal sent to EC2 instance `{instance_id}`. It will be running shortly."

        elif rt == 'RDS':
            db_id = get_cf_physical_id(stack_name, 'AWS::RDS::DBInstance') if stack_name else instance_id
            if not db_id:
                db_id = instance_id
            if not db_id:
                return "❌ Could not resolve the RDS DB identifier. Please check the instance name."
            if action == 'stop':
                _rds_client.stop_db_instance(DBInstanceIdentifier=db_id)
                return f"✅ Stop signal sent to RDS instance `{db_id}`. It will be stopped within a few minutes."
            else:
                _rds_client.start_db_instance(DBInstanceIdentifier=db_id)
                return f"✅ Start signal sent to RDS instance `{db_id}`. It will be available within a few minutes."

        elif rt == 'REDSHIFT':
            cluster_id = get_cf_physical_id(stack_name, 'AWS::Redshift::Cluster') if stack_name else instance_id
            if not cluster_id:
                cluster_id = instance_id
            if not cluster_id:
                return "❌ Could not resolve the Redshift cluster identifier. Please check the instance name."
            if action == 'stop':
                _redshift_client.pause_cluster(ClusterIdentifier=cluster_id)
                return f"✅ Pause signal sent to Redshift cluster `{cluster_id}`. It will be paused within a few minutes."
            else:
                _redshift_client.resume_cluster(ClusterIdentifier=cluster_id)
                return f"✅ Resume signal sent to Redshift cluster `{cluster_id}`. It will be available within a few minutes."

        elif action == 'terminate':
            if not stack_name:
                return "❌ Could not resolve the stack name. Cannot terminate."
            _cfn_client.delete_stack(StackName=stack_name)
            return (
                f"✅ Termination initiated for `{stack_name}`. "
                "The CloudFormation stack and all associated resources are being deleted. "
                "This may take a few minutes."
            )

        else:
            return f"❌ Unknown resource type '{resource_type}'. Cannot perform action."

    except Exception as e:
        err = str(e)
        logger.warning("resources: execute_action failed (%s %s %s): %s" % (
            action, resource_type, stack_name or instance_id, err))
        if 'InvalidDBInstanceState' in err or 'is not in an available state' in err.lower():
            return "❌ The resource is already in transition or not in a stoppable state. Please wait and try again."
        if 'already' in err.lower():
            return f"❌ The resource is already {'stopped' if action == 'stop' else 'running'}."
        return f"❌ Action failed: {err}"


# ---------------------------------------------------------------------------
# Action payload extraction
# ---------------------------------------------------------------------------

def extract_action_payload(text: str):
    """
    Extract <action-payload>...</action-payload> from agent reply.
    Returns (clean_text, action_dict_or_None).
    """
    match = re.search(r'<action-payload>(.*?)</action-payload>', text, re.DOTALL)
    if not match:
        return text, None
    raw = match.group(1).strip()
    try:
        action_data = json.loads(raw)
        clean = text.replace(match.group(0), '').strip()
        return clean, action_data
    except json.JSONDecodeError as e:
        logger.warning("resources: action-payload JSON parse error: " + str(e))
        return text, None


# ---------------------------------------------------------------------------
# User session history (consolidated from both apps)
# ---------------------------------------------------------------------------

def _compute_duration(started: str, stopped: str) -> str:
    if not started:
        return ""
    try:
        fmt = "%Y-%m-%d %H:%M:%S"
        t0 = datetime.datetime.strptime(started[:19], fmt)
        t1 = (
            datetime.datetime.strptime(stopped[:19], fmt)
            if stopped
            else datetime.datetime.utcnow()
        )
        delta = t1 - t0
        total_minutes = int(delta.total_seconds() / 60)
        if total_minutes < 60:
            return f"~{total_minutes}min"
        hours, mins = divmod(total_minutes, 60)
        return f"~{hours}h {mins}min" if mins else f"~{hours}h"
    except Exception:
        return ""


def _fmt_time(ts: str) -> str:
    if not ts:
        return ""
    return str(ts)[:16]


def load_user_sessions(email: str) -> list:
    """
    Parse result.json and return enriched session dicts for this user, oldest-first.
    Each dict: app, instance, cluster, status, started, stopped, duration, stack_name, cost
    """
    try:
        data = _read_result_json()
    except Exception:
        return []

    records = []
    for status_key, stacks in data.items():
        if not isinstance(stacks, list):
            continue
        for s in stacks:
            if s.get('CREATEDBY', '').lower() != email.lower():
                continue
            stack_name = s.get('StackName', '')
            app        = stack_name.split('-')[0] if stack_name else 'unknown'
            instance   = s.get('InstanceType', '')
            if not instance:
                details = s.get('instanceDetails', {})
                if isinstance(details, dict):
                    instance = details.get('InstanceType', '')
            cluster  = 'Parallel Cluster' if 'parallelcluster' in stack_name.lower() else 'Single Node'
            started  = s.get('CreationTime', s.get('creationTime', ''))
            stopped  = s.get('StoppedSince', '')
            cost     = s.get('costUtilised', '')
            cost_str = f"${float(cost):.2f}" if cost else ""
            records.append({
                'stack_name': stack_name,
                'display':    s.get('displayName', stack_name),
                'app':        app,
                'instance':   instance or 'unknown',
                'cluster':    cluster,
                'status':     status_key,
                'started':    _fmt_time(started),
                'stopped':    _fmt_time(stopped),
                'duration':   _compute_duration(started, stopped),
                'cost':       cost_str,
            })

    records.sort(key=lambda r: r['started'] or '9999')
    return records


def build_history_context(records: list) -> str:
    """Format session records into a numbered list for the LLM prompt."""
    if not records:
        return "No sessions found for this user."
    lines = []
    for i, r in enumerate(records, 1):
        parts = [
            f"{i}. App: {r['app']}",
            f"Instance: {r['instance']}",
            f"Type: {r['cluster']}",
            f"Status: {r['status']}",
        ]
        if r['started']:  parts.append(f"Started: {r['started']}")
        if r['stopped']:  parts.append(f"Stopped: {r['stopped']}")
        if r['duration']: parts.append(f"Duration: {r['duration']}")
        if r['cost']:     parts.append(f"Cost: {r['cost']}")
        lines.append(" | ".join(parts))
    return "\n".join(lines)
