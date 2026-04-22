"""
jobs.py — Live instance monitoring via SSM.

Handles:
  - RELION job status (check_relion.py deployed via base64)
  - Package validation (bash script via SSM)
  - Keyword detectors for routing
"""
import base64
import logging
import os
import re
import time

import boto3

logger = logging.getLogger(__name__)

_REGION     = os.environ.get('CHATBOT_AWS_REGION', 'us-east-1')
_ssm_client = boto3.client('ssm', region_name=_REGION)

_RESULT_JSON = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'result.json')

# EFS home directory — configurable per environment
_EFS_HOME = os.environ.get('NUMEN_EFS_HOME', '/efshome')

# ---------------------------------------------------------------------------
# Keyword detectors
# ---------------------------------------------------------------------------

_JOB_STATUS_KEYWORDS = [
    'job', 'running', 'relion', 'status', 'pipeline', 'finished',
    'failed', 'how long', 'progress', 'import', 'motion', 'ctf',
    'classification', 'refinement', 'picking', 'extraction',
]

_VALIDATE_KEYWORDS = [
    'validate', 'check install', 'packages installed', 'verify install',
    'installed on', 'check packages', 'test install', 'validation',
]


def is_job_status_question(message: str) -> bool:
    msg = message.lower()
    return any(kw in msg for kw in _JOB_STATUS_KEYWORDS)


def is_validate_request(message: str) -> bool:
    msg = message.lower()
    return any(kw in msg for kw in _VALIDATE_KEYWORDS)


def extract_instance_id(message: str) -> str:
    """Pull the first i-xxxxxxxx EC2 instance ID out of a message."""
    m = re.search(r'\b(i-[0-9a-f]{8,17})\b', message, re.IGNORECASE)
    return m.group(1) if m else ''


# ---------------------------------------------------------------------------
# SSM runner
# ---------------------------------------------------------------------------

def ssm_run(instance_id: str, command: str, timeout: int = 30) -> str:
    """Run a shell command on an EC2 instance via SSM and return stdout."""
    try:
        resp = _ssm_client.send_command(
            InstanceIds=[instance_id],
            DocumentName='AWS-RunShellScript',
            Parameters={'commands': [command]},
        )
        cmd_id   = resp['Command']['CommandId']
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(2)
            out = _ssm_client.get_command_invocation(
                CommandId=cmd_id, InstanceId=instance_id
            )
            if out['Status'] in ('Success', 'Failed', 'Cancelled', 'TimedOut'):
                return out.get('StandardOutputContent', '').strip()
        return ''
    except Exception as e:
        logger.warning("jobs: SSM command failed: " + str(e))
        return ''


# ---------------------------------------------------------------------------
# Package validation
# ---------------------------------------------------------------------------

_VALIDATE_SCRIPT = r"""#!/bin/bash
PASS=0; FAIL=0
check() {
  local label="$1" cmd="$2"
  if command -v "$cmd" &>/dev/null; then
    local ver; ver=$("$cmd" --version 2>&1 | head -1)
    echo "PASS | $label | $ver"; ((PASS++))
  else
    echo "FAIL | $label | not found"; ((FAIL++))
  fi
}
check "R"                  "R"
check "Rscript"            "Rscript"
check "Python3"            "python3"
check "Git"                "git"
check "Docker"             "docker"
check "Conda/Mamba"        "conda" || check "Mamba" "mamba"
check "Apptainer"          "apptainer" || check "Singularity" "singularity"

if command -v jupyter &>/dev/null || command -v jupyter-lab &>/dev/null; then
  ver=$(jupyter --version 2>&1 | grep -i lab | head -1 || echo "installed")
  echo "PASS | JupyterLab | $ver"; ((PASS++))
elif python3 -c "import jupyterlab" &>/dev/null 2>&1; then
  ver=$(python3 -c "import jupyterlab; print(jupyterlab.__version__)" 2>&1)
  echo "PASS | JupyterLab | v$ver (module)"; ((PASS++))
else
  echo "FAIL | JupyterLab | not found"; ((FAIL++))
fi

if command -v code &>/dev/null || command -v code-server &>/dev/null; then
  echo "PASS | VS Code | $(code --version 2>&1 | head -1 || code-server --version 2>&1 | head -1)"; ((PASS++))
else
  echo "SKIP | VS Code | desktop app — check GUI session";
fi

if command -v rstudio-server &>/dev/null || [ -f /usr/lib/rstudio-server/bin/rserver ]; then
  echo "PASS | RStudio Server | installed"; ((PASS++))
else
  echo "SKIP | RStudio | commercial tool — may require manual install"
fi

if command -v conda &>/dev/null && conda info --base 2>/dev/null | grep -q anaconda; then
  echo "PASS | Anaconda | $(conda --version 2>&1)"; ((PASS++))
elif [ -d /opt/anaconda3 ] || [ -d "$HOME/anaconda3" ]; then
  echo "PASS | Anaconda | directory found"; ((PASS++))
else
  echo "SKIP | Anaconda | commercial tool — may require manual install"
fi

echo "---"
echo "SUMMARY: $PASS passed, $FAIL failed"
"""


def validate_packages_on_instance(instance_id: str) -> str:
    """Deploy and run the package-validation script on an EC2 instance via SSM."""
    b64 = base64.b64encode(_VALIDATE_SCRIPT.encode()).decode()
    ssm_run(instance_id, f"echo {b64} | base64 -d > /tmp/numen_validate.sh", timeout=15)
    result = ssm_run(instance_id, "bash /tmp/numen_validate.sh 2>&1", timeout=90)
    return result or "Could not retrieve validation output — check SSM agent status on the instance."


# ---------------------------------------------------------------------------
# RELION job status
# ---------------------------------------------------------------------------

_CHECK_RELION_SCRIPT = r"""import os, datetime, sys
project_dir = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("NUMEN_EFS_HOME", "/efshome") + "/test"
pipeline_file = os.path.join(project_dir, "default_pipeline.star")
NUMERIC_STATUS_MAP = {"0":"Unknown","1":"Running","2":"Finished","3":"Failed","4":"Aborted","5":"Scheduled"}
NAME_COLS   = ("_rlnPipeLineJobNameShort",  "_rlnPipeLineProcessName")
ALIAS_COLS  = ("_rlnPipeLineJobAlias",      "_rlnPipeLineProcessAlias")
STATUS_COLS = ("_rlnPipeLineJobStatus",     "_rlnPipeLineProcessStatus",
               "_rlnPipeLineProcessStatusLabel", "_rlnPipeLineJobStatusLabel")
JOB_SECTIONS = {"data_pipeline_jobs", "data_pipeline_processes"}
seen = {}
try:
    with open(pipeline_file) as f:
        content = f.read()
    current_section = None
    in_loop = False
    col = {}
    header_count = 0
    for raw in content.split("\n"):
        line = raw.strip()
        if not line or line.startswith("#"): continue
        if line.startswith("data_"):
            current_section = line; in_loop = False; col = {}; header_count = 0; continue
        if line == "loop_":
            in_loop = True; col = {}; header_count = 0; continue
        if in_loop and line.startswith("_rln"):
            col[line.split()[0]] = header_count; header_count += 1; continue
        if not (in_loop and col and current_section in JOB_SECTIONS): continue
        name_idx   = next((col[k] for k in NAME_COLS   if k in col), None)
        alias_idx  = next((col[k] for k in ALIAS_COLS  if k in col), None)
        status_idx = next((col[k] for k in STATUS_COLS if k in col), None)
        if None in (name_idx, status_idx): continue
        parts = line.split()
        needed = max(name_idx, alias_idx if alias_idx is not None else 0, status_idx) + 1
        if len(parts) < needed: continue
        job_path   = parts[name_idx].rstrip("/")
        alias      = parts[alias_idx] if alias_idx is not None else "-"
        raw_status = parts[status_idx]
        label      = NUMERIC_STATUS_MAP.get(raw_status, raw_status)
        full_path = os.path.join(project_dir, job_path)
        success   = os.path.join(full_path, "RELION_JOB_EXIT_SUCCESS")
        failure   = os.path.join(full_path, "RELION_JOB_EXIT_FAILURE")
        if os.path.exists(success):
            mtime = datetime.datetime.fromtimestamp(os.path.getmtime(success))
            seen[job_path] = f"  {job_path} ({alias}): Finished at {mtime.strftime('%Y-%m-%d %H:%M UTC')}"
        elif os.path.exists(failure):
            seen[job_path] = f"  {job_path} ({alias}): Failed"
        elif label in ("Running", "1"):
            run_log = os.path.join(full_path, "run.out")
            age = ""
            if os.path.exists(run_log):
                elapsed = datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(run_log))
                age = f" (log last updated {int(elapsed.total_seconds()/60)}m ago)"
            seen[job_path] = f"  {job_path} ({alias}): Running{age}"
        elif label in ("Succeeded", "Finished", "2"):
            seen[job_path] = f"  {job_path} ({alias}): Succeeded"
        elif label in ("Failed", "3"):
            seen[job_path] = f"  {job_path} ({alias}): Failed"
        else:
            seen[job_path] = f"  {job_path} ({alias}): {label}"
except Exception as ex:
    print(f"ERROR: {ex}"); sys.exit(1)
if seen:
    print("RELION jobs in " + project_dir + ":")
    for entry in seen.values(): print(entry)
else:
    print("No jobs found in pipeline at " + project_dir)
"""


def get_relion_job_status(instance_id: str, project_dir: str = '') -> str:
    """
    SSM into the Relion instance and run check_relion.py.
    Always overwrites the script via base64 to ensure the latest parser is active.
    Uses find to pick the most recently modified pipeline under _EFS_HOME.
    """
    efs_home = _EFS_HOME
    if not project_dir:
        project_dir = efs_home + '/test'
    b64 = base64.b64encode(_CHECK_RELION_SCRIPT.encode()).decode()
    ssm_run(instance_id, f"echo {b64} | base64 -d > /tmp/check_relion.py", timeout=15)
    cmd = (
        f"PIPELINE=$(find {efs_home} -maxdepth 4 -name default_pipeline.star 2>/dev/null "
        f"  | grep -v '/job[0-9]' "
        f"  | xargs ls -t 2>/dev/null | head -1); "
        f"if [ -n \"$PIPELINE\" ]; then "
        f"  python3 /tmp/check_relion.py \"$(dirname $PIPELINE)\" 2>&1; "
        f"else "
        f"  echo 'No default_pipeline.star found under {efs_home}'; "
        f"fi"
    )
    return ssm_run(instance_id, cmd) or 'Could not retrieve job status from instance.'


def get_user_relion_instances(email: str) -> list:
    """
    Read result.json and return running Relion instance dicts for this user.
    Falls back to ALL running Relion instances if none owned by this user.
    Returns list of {instanceId, stackName}.
    """
    import json

    def _is_relion(i):
        name    = i.get('StackName', '').lower()
        display = i.get('displayName', '').lower()
        app     = i.get('instanceDetails', {}).get('Application Name', '').lower()
        return 'relion' in name or 'linux' in name or 'relion' in display or 'relion' in app

    try:
        with open(_RESULT_JSON) as f:
            data = json.load(f)
        running = data.get('Running', [])
        owned = [
            {'instanceId': i.get('instanceId', ''), 'stackName': i.get('StackName', '')}
            for i in running
            if i.get('CREATEDBY', '').lower() == email.lower() and _is_relion(i)
        ]
        if owned:
            return owned
        return [
            {'instanceId': i.get('instanceId', ''), 'stackName': i.get('StackName', '')}
            for i in running if _is_relion(i)
        ]
    except Exception as e:
        logger.warning("jobs: result.json relion lookup failed: " + str(e))
        return []


def build_job_context(email: str) -> str:
    """Fetch live RELION job status for all running instances and return as context string."""
    instances = get_user_relion_instances(email)
    if not instances:
        return ''
    parts = []
    for inst in instances:
        iid  = inst['instanceId']
        name = inst['stackName']
        if not iid:
            continue
        status = get_relion_job_status(iid)
        parts.append(f'Instance: {name} ({iid})\n{status}')
    if not parts:
        return ''
    return '\n=== LIVE RELION JOB STATUS ===\n' + '\n\n'.join(parts) + '\n==============================\n'
