"""
prompt.py — Unified system prompt builder.

Merges the Numen Agent system prompt with live context injection.
The compute apps section is built dynamically from data_cache so it
never goes stale.
"""
import logging

from chatbot import data_cache as dc
from chatbot.resources import get_manageable_resources

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dynamic apps section (replaces hardcoded list in original agent_views.py)
# ---------------------------------------------------------------------------

_INFRA_MAP = {
    'SingleNode':      'SingleNode',
    'parallelCluster': 'ParallelCluster',
    'SageMaker':       'SageMaker (managed)',
    'HealthOmics':     'HealthOmics (managed)',
}


def build_compute_apps_section() -> str:
    """Build AVAILABLE APPLICATIONS block from live data_cache. DB apps excluded."""
    try:
        apps = [a for a in dc.implemented_apps() if a.get('appType') != 'database']
    except Exception:
        return '(no applications configured)'
    lines = []
    for i, app in enumerate(apps, 1):
        title    = app.get('title', '')
        pkg      = app.get('packageName', '')
        oses     = ', '.join(app.get('compatibleOS', []))
        infras   = ', '.join(_INFRA_MAP.get(inf, inf) for inf in app.get('compatibleInfra', []))
        gpu_note = ' [GPU required]' if app.get('disableCPU') else ''
        lines.append(f"{i}. {title:<30} packageName={pkg:<22} OS={oses}  infra={infras}{gpu_note}")
    return '\n'.join(lines) if lines else '(no applications configured)'


def _build_instance_types_section() -> str:
    """
    Build the INSTANCE TYPES section dynamically from customInfrastructure.json
    and instancesListed.json so it never drifts from the actual platform config.
    """
    try:
        all_families = dc.infra().get('Instances', [])
        instances_list = dc.instances().get('InstancesList', [])
        master_instances = dc.infra().get('masterInstances', [])

        # Build family → sizes map
        family_sizes: dict = {}
        for obj in instances_list:
            for fam, sizes in obj.items():
                family_sizes[fam] = sizes

        cpu_lines = []
        gpu_lines = []
        for fam_info in all_families:
            fam  = fam_info.get('family', '')
            kind = fam_info.get('type', 'CPU').upper()
            sizes = family_sizes.get(fam, [])
            if not sizes:
                continue
            line = f"  {fam}: {' | '.join(sizes)}"
            if kind == 'GPU':
                gpu_lines.append(line)
            else:
                cpu_lines.append(line)

        master_str = ' | '.join(m['packageName'] for m in master_instances) if master_instances else ''

        parts = ['Single Node (nodes[0].code):']
        if cpu_lines:
            parts.append('  CPU:')
            parts.extend(cpu_lines)
        if gpu_lines:
            parts.append('  GPU:')
            parts.extend(gpu_lines)

        if master_str:
            parts.append(f'\nParallel Cluster Head (nodes[0].code, isMaster=true):\n  {master_str}')

        # Parallel compute groups from ParallelClusterConfig
        pc_config = dc.infra().get('ParallelClusterConfig', {})
        cpu_cats  = [c['value'] for c in pc_config.get('cpuCategories', ['small', 'medium', 'large']
                     if not pc_config.get('cpuCategories') else pc_config.get('cpuCategories', []))]
        cpu_fams  = [f['family'] for f in all_families if f.get('type') == 'CPU']
        gpu_fams  = [f['family'] for f in all_families if f.get('type') == 'GPU']

        # GPU categories from instanceInfo
        gpu_counts = sorted({
            int(i['GpuCount']) for i in dc.instance_info().get('InstanceInfo', [])
            if i.get('Type') == 'GPU' and i.get('GpuCount') not in (None, 'NA')
        })

        cpu_group_examples = ' | '.join(
            f"cpu-{f}-{c}" for f in cpu_fams[:2] for c in cpu_cats[:3]
        )
        gpu_group_examples = ' | '.join(
            f"gpu-{f}-{g}" for f in gpu_fams[:2] for g in gpu_counts[:3]
        )
        default_count = pc_config.get('defaultNodeCount', 2)
        max_count     = pc_config.get('maxNodeGroups', 10)

        parts.append(f'\nParallel Cluster Compute Groups (nodeGroups[].code):')
        if cpu_group_examples:
            parts.append(f'  CPU: {cpu_group_examples}')
        if gpu_group_examples:
            parts.append(f'  GPU: {gpu_group_examples}')
        parts.append(f'  Default count: {default_count} (max {max_count} per queue)')

        return '\n'.join(parts)
    except Exception as e:
        logger.warning('prompt: _build_instance_types_section failed: %s', e)
        # Fallback to safe static values rather than crashing
        return (
            'Single Node (nodes[0].code): see platform instance list\n'
            'Parallel Cluster Head: see platform instance list\n'
            'Parallel Cluster Compute Groups: cpu-<family>-<size> | gpu-<family>-<gpucount>'
        )


def _build_database_section() -> str:
    """
    Build the DATABASE section of the prompt dynamically from buildParameters.json.
    Reads RDS engine versions, instance classes, and Redshift node types so the
    Agent never quotes stale version strings.
    Falls back to safe generic text if the file is unavailable.
    """
    try:
        bp = dc.build_params()
        rds = bp.get('rds', {})
        rs  = bp.get('redshift', {})

        # RDS engines — stored as a list or comma-separated string
        engines_raw = rds.get('SupportedEngines', rds.get('supportedEngines', []))
        if isinstance(engines_raw, str):
            engines_raw = [e.strip() for e in engines_raw.split(',') if e.strip()]
        engines_str = ' | '.join(engines_raw) if engines_raw else 'mysql | postgres | mariadb | oracle-se2 | sqlserver-ex'

        # RDS instance classes
        classes_raw = rds.get('InstanceClasses', rds.get('instanceClasses', []))
        if isinstance(classes_raw, str):
            classes_raw = [c.strip() for c in classes_raw.split(',') if c.strip()]
        classes_str = ' | '.join(classes_raw) if classes_raw else 'db.t3.medium | db.t3.large | db.m5.large | db.m5.xlarge'

        # RDS storage range
        min_storage = rds.get('MinAllocatedStorage', rds.get('AllocatedStorage', 20))
        max_storage = rds.get('MaxAllocatedStorage', 500)

        # Redshift node types — may be a list of dicts with nodeType + cost, or plain list
        rs_nodes_raw = rs.get('NodeTypes', rs.get('nodeTypes', []))
        if rs_nodes_raw and isinstance(rs_nodes_raw[0], dict):
            rs_nodes_str = ' | '.join(
                f"{n['nodeType']} (${n.get('cost', '?')}/hr)" for n in rs_nodes_raw
            )
        elif rs_nodes_raw:
            rs_nodes_str = ' | '.join(str(n) for n in rs_nodes_raw)
        else:
            rs_nodes_str = 'ra3.large | ra3.xlplus | ra3.4xlarge'

        rs_default_node  = rs.get('NodeType', 'ra3.large')
        rs_default_nodes = rs.get('NumberOfNodes', 2)

        return f"""- Amazon RDS       packageName=amazonrds          clusterType=RDS
  Engines: {engines_str}
  Instance classes: {classes_str}
  Storage: {min_storage}–{max_storage} GB (gp3). Multi-AZ: yes/no. Backup retention: 1–35 days.

- Amazon Redshift  packageName=amazonredshift     clusterType=REDSHIFT
  Node types: {rs_nodes_str}
  Default: {rs_default_node} x{rs_default_nodes} nodes. Cluster: single-node | multi-node (2–32 nodes)"""

    except Exception as e:
        logger.warning('prompt: _build_database_section failed: %s', e)
        return """- Amazon RDS       packageName=amazonrds          clusterType=RDS
  Engines: mysql | postgres | mariadb | oracle-se2 | sqlserver-ex
  Instance classes: db.t3.medium | db.t3.large | db.m5.large | db.m5.xlarge
  Storage: 20–500 GB (gp3). Multi-AZ: yes/no. Backup retention: 1–35 days.

- Amazon Redshift  packageName=amazonredshift     clusterType=REDSHIFT
  Node types: ra3.large | ra3.xlplus | ra3.4xlarge
  Cluster: single-node | multi-node (2–32 nodes)"""


def _build_rds_kb_section() -> str:
    """
    Build the RDS knowledge base section with live engine versions and instance classes
    from buildParameters.json so the Agent never quotes stale version strings.
    """
    try:
        bp  = dc.build_params()
        rds = bp.get('rds', {})

        engines_raw = rds.get('SupportedEngines', rds.get('supportedEngines', []))
        if isinstance(engines_raw, str):
            engines_raw = [e.strip() for e in engines_raw.split(',') if e.strip()]
        engines_str = ' | '.join(engines_raw) if engines_raw else 'mysql | postgres | mariadb | oracle-se2 | sqlserver-ex'

        classes_raw = rds.get('InstanceClasses', rds.get('instanceClasses', []))
        if isinstance(classes_raw, str):
            classes_raw = [c.strip() for c in classes_raw.split(',') if c.strip()]

        # Build instance guidance lines from the class list
        guidance_lines = []
        for cls in classes_raw:
            if 't3.medium' in cls:
                guidance_lines.append(f'- {cls}: dev/test only')
            elif 't3.large' in cls:
                guidance_lines.append(f'- {cls}: small production')
            elif 'm5.large' in cls:
                guidance_lines.append(f'- {cls}: general purpose')
            elif 'm5.xlarge' in cls:
                guidance_lines.append(f'- {cls}: high connection counts')
            else:
                guidance_lines.append(f'- {cls}')
        instance_guidance = '\n'.join(guidance_lines) if guidance_lines else '- db.t3.medium: dev/test  - db.m5.large: general purpose'

        return f"""- Supported: {engines_str}

INSTANCE GUIDANCE:
{instance_guidance}"""

    except Exception as e:
        logger.warning('prompt: _build_rds_kb_section failed: %s', e)
        return '- Supported: mysql | postgres | mariadb | oracle-se2 | sqlserver-ex'


def _build_pricing_section() -> str:
    """
    Build the ON-DEMAND PRICING TABLE dynamically from priceInstances.json.
    Falls back to a note if the file is unavailable.
    """
    try:
        prices = dc.price_instances()
        if not prices:
            return '(pricing data unavailable — check priceInstances.json)'

        # Group by family prefix for readability
        from collections import defaultdict
        by_family: dict = defaultdict(list)
        for inst, price in sorted(prices.items()):
            fam = inst.split('.')[0] if '.' in inst else inst
            by_family[fam].append(f'{inst}=${price}/hr')

        lines = []
        for fam in sorted(by_family):
            lines.append('  ' + ' | '.join(by_family[fam]))

        return 'ON-DEMAND PRICING (us-east-1, Linux/hr):\n' + '\n'.join(lines)
    except Exception as e:
        logger.warning('prompt: _build_pricing_section failed: %s', e)
        return '(pricing data unavailable)'


# ---------------------------------------------------------------------------
# Base system prompt (full Agent prompt — nothing removed)
# ---------------------------------------------------------------------------

def _make_base() -> str:
    return """You are Numen Agent, a strictly scoped AI assistant built into the Numen scientific HPC cloud platform. Your ONLY purpose is to help users launch and manage the specific computing resources available on this platform.

=== ABSOLUTE RESTRICTIONS ===

Refuse ANY question not directly related to:
  - Launching one of the supported applications/resources listed below
  - Clarifying questions needed to complete a launch
  - Explaining what supported applications do in the context of launching them
  - Checking the status of running jobs on Relion or Linux instances
  - Answering questions about instance or job health based on live context provided
  - Stopping, starting, or terminating instances listed in [MANAGEABLE RESOURCES]
  - Answering questions about consumption metrics, budget, instance count, cost (use the live context)
  - Explaining reserved instance capacity or on-demand vs reserved pricing

For off-topic requests, always respond with:
  "I'm Numen Agent and I can only help you launch and manage computing resources on this platform. I'm not able to help with that topic. Would you like to launch something or manage an existing resource?"

=== YOUR JOB ===

Help users launch computing resources through natural conversation — one clear question at a time, validating answers, and ultimately triggering the right launch.

=== AVAILABLE APPLICATIONS ===

COMPUTE (clusterType: SINGLE or PARALLEL):
""" + build_compute_apps_section() + """

DATABASE:
""" + _build_database_section() + """

=== INSTANCE TYPES ===

""" + _build_instance_types_section() + """

INSTANCE SELECTION GUIDANCE:
- Genomics CLI / RNA-seq / Single-cell CPU: recommend r7i.2xlarge (alignment) or r7i.4xlarge (STAR/large datasets)
- Biostatistics / Collaborative Data Science: recommend m6i.xlarge or m6i.2xlarge
- Imaging Desktop / Digital Pathology: recommend m6i.2xlarge (CPU) or g5.xlarge (GPU-accelerated)
- Structural Biology: recommend g5.2xlarge (visualisation + MD) or c6i.4xlarge (CPU-only simulation)
- Relion / cryoSPARC: recommend g5.2xlarge or g5.4xlarge (GPU cryo-EM)

=== GENERAL COMPUTE PACKAGES (Linux / Windows only) ===

When the user is launching a Linux or Windows General Compute environment, after collecting the instance type, ask:
  "Which tools would you like pre-installed? Available options:
  1. Docker          2. VS Code         3. Mambaforge (conda/mamba)
  4. JupyterLab      5. R               6. RStudio Server
  7. Apptainer       8. Anaconda        9. Git           10. Python3
  — or say 'all' to install everything, 'none' to skip."

Rules:
- If the user says 'all', use ALL ten: ["Docker","VS Code","Mambaforge","JupyterLab","R","RStudio","Apptainer","Anaconda","Git","Python3"]
- If the user lists specific tools, map them to the exact names above.
- If the user says 'none' or 'skip', omit the "packages" field from the payload entirely.
- Always include the "packages" array in the launch payload for Linux/Windows when tools are selected.

=== IDLE TIMEOUT ===
SingleNode/SageMaker: 30 | 60 | 90 minutes | 0=never stop
ParallelCluster: 30 | 60 | 90 minutes | 0=never terminate

=== DATA SOURCES ===
Default: Home. Optional: Projects (CryoEMProjects), OpenZFS

=== INSTANCE NAMING ===
Early in the conversation (after confirming the application), ask the user for a friendly name:
  "What would you like to name this resource? (e.g. 'relion-july-run', 'cryo-em-test')"
- Lowercase letters, numbers, hyphens only — max 30 characters.
- IMPORTANT: When you have asked for an instance name, treat the user's ENTIRE next message as the name they want — even if it looks like a short word (e.g. "sure", "test", "demo", "ok").
- If the user's response to the name question is a common confirmation word (yes/sure/ok/go/yep/absolutely/correct/proceed/confirm/launch) with nothing else, auto-generate a sensible default: "{app-abbreviation}-{MMDD}" and tell the user.
- If user says "skip" or "anything", generate a sensible default like "{app}-{MMDD}".
- Strip any spaces and truncate to 30 characters. Convert underscores to hyphens.
- Include "instanceName" in the launch payload.
- NEVER emit "⚠️ Launch blocked:" text yourself — that format is reserved for the UI system layer.

=== CONVERSATION RULES ===
1. Ask EXACTLY ONE question per message.
2. Be concise and professional. Never say "Great!", "Excellent choice!", "Perfect!", "Sure!", "Of course!", "Absolutely!" or any similar affirmation. Acknowledge neutrally and move to the next question.
3. Auto-select single-option fields (OS, infra) and tell the user.
4. For databases, skip OS/infra — go straight to engine/config.
5. Present choices as a numbered list.
6. After collecting all info, show a clear summary and ask: "Shall I launch this now?"
7. After the user confirms the FINAL summary question, output EXACTLY and ONLY the <launch-payload> block — no other text before or after it.
8. If user says "cancel" or "never mind", acknowledge and reset gracefully.
9. Use the live user context below to give budget-aware advice.
10. For STOP/START/TERMINATE requests: look up the resource in [MANAGEABLE RESOURCES]. If there is exactly one matching resource, confirm with the user. For TERMINATE, add a strong warning: "⚠️ This will permanently delete `<name>` and all associated data. Are you sure?" After the user confirms, output EXACTLY and ONLY the <action-payload> block.
11. COST TRANSPARENCY: When presenting instance options, always quote the on-demand hourly cost. E.g. "g5.2xlarge at $1.21/hr — at your current budget that gives you ~X hours." Also mention if reserved capacity is available.
12. TAGGING: After collecting the instance name, ask: "Would you like to add any custom tags? (e.g. Project=CryoEM, CostCenter=BIO-123, Team=Research) — or say 'skip'." Include in payload as `"userTags": [{"Key":"...","Value":"..."}]`. If skipped, omit userTags.
13. CONSUMPTION METRICS: When users ask about instances/spend/budget — answer directly from [LIVE USER CONTEXT].

=== LAUNCH PAYLOAD FORMAT ===
Output EXACTLY one block below with no extra text after it:

Single Node (non-Linux/Windows apps):
<launch-payload>{"instanceName":"NAME","applicationName":"PACKAGE","type":"APPLICATION","os":"OS","clusterType":"SINGLE","nodes":[{"code":"INSTANCE"}],"nodeGroups":[],"volumes":[],"dataSources":["Home"],"idleTimeout":{"value":MINUTES,"unit":"MINUTES","behaviour":"STOP"},"email":"__USER_EMAIL__"}</launch-payload>

Single Node — Linux or Windows General Compute (include packages array):
<launch-payload>{"instanceName":"NAME","applicationName":"linux","type":"APPLICATION","os":"OS","clusterType":"SINGLE","nodes":[{"code":"INSTANCE"}],"nodeGroups":[],"volumes":[],"dataSources":["Home"],"packages":["Docker","VS Code","Mambaforge","JupyterLab","R","RStudio","Apptainer","Anaconda","Git","Python3"],"idleTimeout":{"value":MINUTES,"unit":"MINUTES","behaviour":"STOP"},"email":"__USER_EMAIL__"}</launch-payload>

Parallel Cluster:
<launch-payload>{"instanceName":"NAME","applicationName":"PACKAGE","type":"APPLICATION","os":"OS","clusterType":"PARALLEL","nodes":[{"code":"HEAD_NODE","isMaster":true}],"nodeGroups":[{"code":"COMPUTE_GROUP","count":NODE_COUNT}],"volumes":[],"dataSources":["Home"],"idleTimeout":{"value":MINUTES,"unit":"MINUTES","behaviour":"TERMINATE"},"email":"__USER_EMAIL__"}</launch-payload>

SageMaker:
<launch-payload>{"instanceName":"NAME","applicationName":"sagemaker","type":"APPLICATION","os":"alinux2","clusterType":"SAGEMAKER","nodes":[{"code":"ml.t3.medium"}],"nodeGroups":[],"volumes":[],"dataSources":["Home"],"idleTimeout":{"value":MINUTES,"unit":"MINUTES","behaviour":"STOP"},"email":"__USER_EMAIL__"}</launch-payload>

RDS:
<launch-payload>{"instanceName":"NAME","applicationName":"amazonrds","type":"DATABASE","clusterType":"RDS","databaseConfig":{"dbType":"RDS","engine":"ENGINE","engineVersion":"VERSION","dbTemplate":"dev-test","dbInstanceClass":"INSTANCE_CLASS","multiAZ":MULTI_AZ,"storageType":"gp3","allocatedStorage":STORAGE_GB,"maxAllocatedStorage":200,"dbName":"numendatabase","backupRetentionPeriod":RETENTION_DAYS},"idleTimeout":{"value":0,"unit":"MINUTES","behaviour":"STOP"},"email":"__USER_EMAIL__"}</launch-payload>

Redshift:
<launch-payload>{"instanceName":"NAME","applicationName":"amazonredshift","type":"DATABASE","clusterType":"REDSHIFT","databaseConfig":{"dbType":"REDSHIFT","nodeType":"NODE_TYPE","numberOfNodes":NUM_NODES,"clusterType":"CLUSTER_TYPE","dbName":"numendw","dbTemplate":"dev-test","dbInstanceClass":"NODE_TYPE","allocatedStorage":0,"maxAllocatedStorage":0},"idleTimeout":{"value":0,"unit":"MINUTES","behaviour":"STOP"},"email":"__USER_EMAIL__"}</launch-payload>

Replace UPPERCASE placeholders with actual values. Replace __USER_EMAIL__ exactly as written.
Use EXACTLY the version strings listed. Never invent version strings.
If the user provided custom tags, add "userTags":[...] at the root level. If no tags, omit entirely.

=== STOP / START RESOURCE MANAGEMENT ===

After the user confirms, output EXACTLY and ONLY:
<action-payload>{"action":"ACTION","resourceType":"TYPE","instanceId":"INSTANCE_ID","stackName":"STACK_NAME","resourceName":"DISPLAY_NAME"}</action-payload>

- ACTION: "stop" | "start" | "terminate"
- TYPE: "EC2" | "RDS" | "REDSHIFT"
- Never invent stack names or instance IDs — always use values from [MANAGEABLE RESOURCES].
- For terminate: ALWAYS warn the user this is irreversible before outputting the action-payload.

""" + _build_pricing_section() + """

Always calculate: hours_available = floor(remaining_budget / hourly_cost) and mention it.
Check [RESERVED CAPACITY] first — if the instance type has reserved capacity, say so.

=== JOB STATUS MONITORING ===

You MUST answer job status questions. When the user message contains [LIVE CONTEXT] with RELION job data, use it to answer directly and naturally.
If [LIVE CONTEXT] shows no instances found, say: "I couldn't find any running Relion instances on your account."
If [LIVE CONTEXT] is not present but the question is job-related, say: "I don't have live access to your instance right now. Please check the RELION GUI directly."

=== RELION HPC KNOWLEDGE BASE ===

SINGLE NODE vs PARALLEL CLUSTER:
- Single Node: Best for MotionCor2, CTF estimation, AutoPick, small 2D/3D classification, or quick tests.
- Parallel Cluster: Essential for large particle stacks during 3D classification and refinement.

RECOMMENDED INSTANCES FOR RELION:
- Single Node GPU: g5.2xlarge or g5.4xlarge (NVIDIA A10G GPUs, best value for cryo-EM)
- Parallel Cluster Head: c6i.xlarge or c6i.2xlarge
- Parallel Cluster Compute (GPU): gpu-g5-2-gpu or gpu-g5-4-gpu
- Parallel Cluster Compute (CPU): cpu-c6i-large or cpu-m6id-large

MPI + THREADS: one MPI process per GPU is standard. Example on 32-core node: 4 MPI x 8 threads.
GPU TIPS: Leave "Which GPUs to use" empty for auto-detection. CUDA OOM → reduce classes/pool/box size.
SLURM: Always copy particles to local scratch. Use --scratch_dir for fast local storage.
COMMON ERRORS: Job zombification → cancel and restart from checkpoint. Parallel disc I/O: disable on NFS.

When a user asks to launch Relion, ask ONE AT A TIME:
1. Single node or parallel cluster?
2. GPU or CPU compute? (1. GPU — recommended  2. CPU — preprocessing/small tests)
3. Instance size based on answer to step 2
4. Idle timeout
5. Instance name
Then confirm and generate the payload.

=== GENOMICS CLI KNOWLEDGE BASE ===

Tools pre-installed: FastQC, MultiQC, Cutadapt, Trimmomatic, BWA, minimap2, samtools, bcftools, BEDTools, GATK4, Picard.
All in the 'genomics' conda environment, activated automatically.

INSTANCE GUIDANCE:
- Light QC: m6i.xlarge ($0.192/hr)
- Standard alignment (BWA, minimap2): r7i.2xlarge ($0.504/hr) [recommended]
- Large genome / STAR RNA-seq / large GATK: r7i.4xlarge ($1.008/hr)
- No GPU needed — always recommend CPU instances.

When a user asks to launch Genomics CLI, ask ONE AT A TIME:
1. Single node or parallel cluster?
2. What analysis are they running?
3. Instance size (offer the 3 options above)
4. Storage size (default 128 GB EBS; suggest 500 GB for large datasets)
5. Idle timeout
6. Instance name
Then confirm and generate the payload.

=== AMAZON RDS KNOWLEDGE BASE ===

GOOD FOR: metadata catalogs, LIMS/ELN backends, pipeline job tracking, structured results.
NOT FOR: raw FASTQ/BAM files — those belong in S3.

ENGINE GUIDANCE:
- PostgreSQL: complex queries, geospatial, analytics
- MySQL/MariaDB: LIMS, simple web apps, lower cost
- Oracle SE2: legacy enterprise, regulated data
- SQL Server: Windows stack, mixed OLTP/reporting
""" + _build_rds_kb_section() + """

COMPLIANCE: RDS is HIPAA-eligible. Use KMS encryption + SSL. Never hardcode credentials.

When a user asks to launch RDS, ask ONE AT A TIME:
1. Database engine?
2. Instance class?
3. Storage size?
4. Multi-AZ?
5. Backup retention days?
6. Database name
Then confirm and generate the payload.
=================================
"""


# ---------------------------------------------------------------------------
# Live context injection
# ---------------------------------------------------------------------------

def build_system_prompt(context: dict, current_payload: dict = None) -> str:
    """Inject live user context into the base system prompt.
    
    Args:
        context: Live user context dict from context.get_user_context().
        current_payload: If the user has a launch card open, pass the current
                         payload so the Agent knows what config is active and
                         can answer follow-up questions about it intelligently.
    """
    remaining = context['remaining']

    budget_note = ''
    if remaining < 50:
        budget_note = (
            f'\n⚠️  BUDGET WARNING: Only ${remaining} remaining. '
            'Strongly recommend the smallest viable instance and warn the user.'
        )
    elif remaining < 150:
        budget_note = f'\n💡 Budget note: ${remaining} remaining — suggest cost-effective options.'

    instance_note = ''
    if context['instance_count'] >= 4:
        instance_note = (
            f'\n💡 The user has {context["instance_count"]} active instances. '
            'Remind them to terminate unused resources before launching more.'
        )

    # Manageable resources block
    resources = get_manageable_resources()
    if resources:
        res_lines = '\n'.join(
            f"  - {r['name']} | type={r['resourceType']} | status={r['status']} "
            f"| instanceId={r['instanceId'] or 'N/A'} | stackName={r['stackName']}"
            for r in resources
        )
        manageable_block = f'\n[MANAGEABLE RESOURCES]\n{res_lines}\n[/MANAGEABLE RESOURCES]'
    else:
        manageable_block = '\n[MANAGEABLE RESOURCES]\n  (none found)\n[/MANAGEABLE RESOURCES]'

    # Reserved instance note
    reserved = context.get('reserved', {})
    if reserved:
        res_list = ', '.join(f"{k}x{v}" for k, v in reserved.items())
        reserved_note = (
            f'\n[RESERVED CAPACITY] Active EC2 reserved instances: {res_list}. '
            'When the user requests one of these instance types, proactively say: '
            '"Good news — you have reserved capacity for this instance type, so it will use your reserved pricing." '
            'For all other types, note it will launch on-demand.'
        )
    else:
        reserved_note = (
            '\n[RESERVED CAPACITY] No active EC2 reserved instances found. '
            'All EC2 launches will use on-demand pricing.'
        )

    context_block = f"""
=== LIVE USER CONTEXT ===
Monthly budget  : ${context['budget_limit']}
Consumed        : ${context['consumed']}
Forecasted      : ${context['forecasted']}
Remaining       : ${remaining}
Active instances: {context['instance_count']}
Stopped instances: {context.get('stopped_count', 0)}
Cost this session: ${context.get('total_cost_used', 0.0)}{budget_note}{instance_note}
{reserved_note}
{manageable_block}
=========================
"""

    # Active launch card — injected when the user has a config open in the UI.
    # Lets the Agent answer follow-up questions about the specific config
    # (e.g. "what does idle timeout do here?", "change to g5.4xlarge") without
    # losing context of what's already been configured.
    active_card_block = ''
    if current_payload:
        app_name = current_payload.get('applicationName', 'unknown')
        ct       = current_payload.get('clusterType', 'unknown')
        nodes    = current_payload.get('nodes', [])
        node_str = nodes[0].get('code', '') if nodes else ''
        idle     = current_payload.get('idleTimeout', {}).get('value', '')
        volumes  = current_payload.get('volumes', [])
        vol_str  = ', '.join(f"{v['type']} {v['size']}GB" for v in volumes) if volumes else 'none'
        ngs      = current_payload.get('nodeGroups', [])
        ng_str   = ', '.join(f"{g['code']} x{g['count']}" for g in ngs) if ngs else ''
        db_cfg   = current_payload.get('databaseConfig')

        active_card_block = '\n[ACTIVE LAUNCH CARD]\n'
        active_card_block += f'  App         : {app_name}\n'
        active_card_block += f'  ClusterType : {ct}\n'
        if db_cfg:
            active_card_block += f'  DB Engine   : {db_cfg.get("engine", "")}\n'
            active_card_block += f'  DB Instance : {db_cfg.get("dbInstanceClass", "")}\n'
            active_card_block += f'  Storage     : {db_cfg.get("allocatedStorage", "")}GB\n'
        else:
            active_card_block += f'  Instance    : {node_str}\n'
            active_card_block += f'  Idle timeout: {idle} min\n'
            active_card_block += f'  Volumes     : {vol_str}\n'
            if ng_str:
                active_card_block += f'  Node groups : {ng_str}\n'
        active_card_block += (
            'The user is reviewing this config in the launch card. '
            'Follow-up questions likely relate to this configuration. '
            'If they ask to change something, acknowledge the change and confirm the updated config.\n'
            '[/ACTIVE LAUNCH CARD]\n'
        )

    return _make_base() + context_block + active_card_block
