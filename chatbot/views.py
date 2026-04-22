"""
Numen Chatbot — three-phase agentic assistant.

Phase 1  LAUNCH    — parse natural language → validated launch payload → confirm card
Phase 2  RECOMMEND — ML-backed suggestions based on workload + user history
Phase 3  SUPPORT   — L1 technical support with KB retrieval (RAG)

Intent is classified by the LLM on every request (no fragile keyword lists).
All JSON data is served from a TTL cache so runtime rewrites by deployFunctions.py
are picked up within 60 seconds.
"""
import json
import logging
import os

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from chatbot import data_cache as dc
from chatbot import cost as cost_mod
from chatbot import kb as kb_mod
from chatbot import llm

logger = logging.getLogger(__name__)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _resource_bucket() -> str:
    """Read the resource bucket name from config.json (written by deployFunctions.py)."""
    try:
        cfg_path = os.path.join(
            os.path.dirname(__file__), "..", "staticfiles", "assets", "Json", "config.json"
        )
        with open(cfg_path) as f:
            return json.load(f).get("resourcebucket", "")
    except Exception:
        return ""


def _clean_history_for_llm(history: list) -> list:
    """
    Strip the large summary blocks from assistant messages before sending to LLM.
    We only want the short conversational acknowledgement, not the full config dump.
    The frontend should store a 'llm_content' field on assistant messages for this.
    Falls back to truncating at 300 chars.
    """
    cleaned = []
    for h in history:
        role = h.get("role", "user")
        content = h.get("llm_content") or h.get("content", "")
        if isinstance(content, str):
            content = content[:300]
        cleaned.append({"role": role, "content": content})
    return cleaned


def _app_list_line(app: dict) -> str:
    """
    Build a single line describing an app for the LLM app_list context.
    Includes available instance types so the model can answer config questions.
    """
    title   = app["title"]
    pkg     = app["packageName"]
    lic     = " [licensed]" if app.get("licenced") else ""
    desc    = app.get("description", "")[:80]
    try:
        schema  = dc.get_config_schema(app)
        choices = schema.get("nodeType", {}).get("choices", [])
        # choices may be strings or dicts with a 'value' key
        types   = [c if isinstance(c, str) else c.get("value", "") for c in choices]
        types   = [t for t in types if t]
        inst    = f" | instances: {', '.join(types)}" if types else ""
    except Exception:
        inst = ""
    return f"• {title} ({pkg}){lic} — {desc}{inst}"


# ── Phase 1: LAUNCH ───────────────────────────────────────────────────────────
# Delegated entirely to launch.py — no duplicate logic here.
from chatbot.launch import handle_launch as _handle_launch  # noqa: E402


# ── Phase 2: RECOMMEND ────────────────────────────────────────────────────────

def _build_recommend_system_prompt(user_history_summary: str = "") -> str:
    apps = dc.implemented_apps()
    app_info = [
        {
            "title": a["title"],
            "description": a.get("description", ""),
            "infra": a.get("compatibleInfra", []),
            "licenced": a.get("licenced", False),
        }
        for a in apps
    ]
    instances = dc.infra().get("Instances", [])
    inst_info = [{"family": i["family"], "type": i["type"], "cost_mo": i["cost"]}
                 for i in instances]

    history_section = ""
    if user_history_summary:
        history_section = f"\nUser's past launches:\n{user_history_summary}\n"

    return f"""You are the Numen HPC platform advisor. Help users choose the right application and infrastructure for their scientific workload.

Available applications:
{json.dumps(app_info, indent=2)}

Available instance families:
{json.dumps(inst_info, indent=2)}
{history_section}
RULES:
- Be warm, direct, and specific. No vague answers.
- If the user describes a cryo-EM workload → recommend Relion or cryoSPARC and explain why briefly.
- If they want molecular dynamics → Gromacs.
- If they want a notebook environment → JupyterHub or Posit Workbench.
- Always mention whether the app needs a GPU instance and roughly why.
- End every recommendation with: "Want me to set that up? Just say launch <app name>."
- If the question is not about choosing a Numen app or instance, say: "I can only advise on Numen applications and infrastructure."
- No markdown. Keep it conversational and under 5 sentences."""


def _handle_recommend(message: str, history: list, email: str):
    try:
        # Use the enriched session loader for better personalisation
        records = _load_user_sessions(email)
        user_history_summary = _get_user_launch_history(email) if not records else _build_history_context(records[-5:])
        prompt = _build_recommend_system_prompt(user_history_summary)
        msgs = _clean_history_for_llm(history[-6:])
        msgs.append({"role": "user", "content": message})
        reply = llm.recommend_reply(prompt, msgs)
        return JsonResponse({"reply": reply, "action": "info", "beta": True})
    except Exception as e:
        logger.error(f"_handle_recommend error: {e}")
        return JsonResponse({"reply": "I had trouble generating a recommendation. Try asking again.", "action": "info"})


def _get_user_launch_history(email: str) -> str:
    """
    Read result.json and return a plain-text summary of the last 10 stacks
    for this user. Used to personalise recommendations.
    """
    records = _load_user_sessions(email)
    if not records:
        return ""
    lines = []
    for r in records[-10:]:
        lines.append(
            f"{r['app']} | {r['instance']} | {r['cluster']} | "
            f"Status: {r['status']} | Started: {r['started']}"
        )
    return "\n".join(lines)


def _load_user_sessions(email: str) -> list:
    """
    Parse result.json and return a list of enriched session dicts for this user,
    sorted oldest-first. Each dict contains:
      app, instance, cluster, status, started, stopped, duration, stack_name, cost
    """
    try:
        result_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "scripts", "result.json"
        )
        with open(result_path) as f:
            data = json.load(f)
    except Exception:
        return []

    records = []
    for status_key, stacks in data.items():
        if not isinstance(stacks, list):
            continue
        for s in stacks:
            if s.get("CREATEDBY", "").lower() != email.lower():
                continue

            stack_name = s.get("StackName", "")
            display    = s.get("displayName", stack_name)

            # Derive app name from stack name (e.g. "relionv400-alinux2-001" → "relionv400")
            app = stack_name.split("-")[0] if stack_name else "unknown"

            # Instance type — may be nested inside instanceDetails
            instance = s.get("InstanceType", "")
            if not instance:
                details = s.get("instanceDetails", {})
                if isinstance(details, dict):
                    instance = details.get("InstanceType", "")

            # Cluster type from stack name convention
            cluster = "Parallel Cluster" if "parallelcluster" in stack_name.lower() else "Single Node"

            # Timing
            started  = s.get("CreationTime", s.get("creationTime", ""))
            stopped  = s.get("StoppedSince", "")
            duration = _compute_duration(started, stopped)

            # Cost
            cost = s.get("costUtilised", "")
            cost_str = f"${float(cost):.2f}" if cost else ""

            records.append({
                "stack_name": stack_name,
                "display":    display,
                "app":        app,
                "instance":   instance or "unknown",
                "cluster":    cluster,
                "status":     status_key,
                "started":    _fmt_time(started),
                "stopped":    _fmt_time(stopped),
                "duration":   duration,
                "cost":       cost_str,
            })

    # Sort by started time, oldest first (unknown times go to the end)
    records.sort(key=lambda r: r["started"] or "9999")
    return records


def _compute_duration(started: str, stopped: str) -> str:
    """Return a human-readable duration string, or '' if times are unavailable."""
    import datetime
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
    """Trim datetime strings to 'YYYY-MM-DD HH:MM' for readability."""
    if not ts:
        return ""
    return str(ts)[:16]


# ── Phase 4: HISTORY ─────────────────────────────────────────────────────────

_HISTORY_SYSTEM_TEMPLATE = """You are the Numen HPC assistant answering questions about a user's past compute sessions.
The user is already authenticated and logged in to Numen — do not tell them to log in.

Answer ONLY from the session data provided below. Do not guess, invent, or use outside knowledge.
If the data does not contain enough information to answer, say so clearly.
Be concise and conversational. No markdown.

USER SESSION DATA (most recent last):
{session_context}"""


def _build_history_context(records: list) -> str:
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
        if r["started"]:
            parts.append(f"Started: {r['started']}")
        if r["stopped"]:
            parts.append(f"Stopped: {r['stopped']}")
        if r["duration"]:
            parts.append(f"Duration: {r['duration']}")
        if r["cost"]:
            parts.append(f"Cost: {r['cost']}")
        lines.append(" | ".join(parts))
    return "\n".join(lines)


def _handle_history(message: str, history: list, email: str):
    try:
        records = _load_user_sessions(email)
        if not records:
            return JsonResponse({
                "reply": "I don't have any session history for you yet. "
                         "Once you've launched a job, I'll be able to answer questions about it.",
                "action": "info",
            })

        context = _build_history_context(records)
        system  = _HISTORY_SYSTEM_TEMPLATE.format(session_context=context)

        msgs = _clean_history_for_llm(history[-4:])
        msgs.append({"role": "user", "content": message})
        reply = llm.history_reply(system, msgs)
        return JsonResponse({"reply": reply, "action": "info"})
    except Exception as e:
        logger.error(f"_handle_history error: {e}")
        return JsonResponse({
            "reply": "I had trouble reading your session history. Try again in a moment.",
            "action": "info",
        })


# ── Phase 3: SUPPORT ─────────────────────────────────────────────────────────

_SUPPORT_SYSTEM = """You are the Numen HPC platform L1 support assistant.
You ONLY help with issues related to the Numen platform and its compute sessions.
The user is already authenticated and logged in to Numen — do not tell them to log in.

Topics you handle:
- CloudFormation stack stuck in CREATE_IN_PROGRESS or ROLLBACK
- DCV connection problems
- CryoSPARC licence errors
- Instance not starting or stopping
- FSx mount issues
- Idle-stop behaviour questions
- How to share a session with a colleague

RULES:
- Be calm, clear, and actionable. Give numbered steps when there are multiple actions.
- Start with the most likely cause before listing steps.
- If you don't know, say so honestly — do NOT guess or hallucinate AWS console steps.
- If the issue needs admin access or is beyond L1, say: "This one needs the Numen admin team — I'll flag it for you."
- If the question is not about Numen at all, say: "I can only help with Numen platform issues."
- No markdown. Plain text only. Keep it human."""


def _handle_support(message: str, history: list, email: str):
    try:
        bucket = _resource_bucket()
        kb_articles = kb_mod.retrieve(message, bucket) if bucket else []
        kb_context = kb_mod.format_context(kb_articles)

        msgs = _clean_history_for_llm(history[-8:])
        msgs.append({"role": "user", "content": message})
        reply = llm.support_reply(_SUPPORT_SYSTEM, msgs, kb_context)
        return JsonResponse({"reply": reply, "action": "info", "beta": True})
    except Exception as e:
        logger.error(f"_handle_support error: {e}")
        return JsonResponse({
            "reply": "I'm having trouble right now. For urgent issues, contact the Numen admin team.",
            "action": "info",
        })


# ── Phase 5: GUIDE ───────────────────────────────────────────────────────────

_GUIDE_SYSTEM = """You are the Numen HPC platform assistant answering how-to and informational questions.
Use the knowledge base articles provided to give accurate, helpful answers.
The user is already authenticated and logged in to Numen — do not tell them to log in or navigate to a login page.
Be concise, friendly, and specific. No markdown — plain text only.

At the end of every answer, add one line:
"You can also launch apps directly from the chatbot or from the Numen dashboard."

If the knowledge base doesn't contain enough information, say so honestly and suggest
the user visit the Help section in the Numen dashboard for full documentation."""


def _handle_guide(message: str, history: list, email: str):
    try:
        bucket = _resource_bucket()
        kb_articles = kb_mod.retrieve(message, bucket) if bucket else []
        kb_context  = kb_mod.format_context(kb_articles)

        msgs = _clean_history_for_llm(history[-6:])
        msgs.append({"role": "user", "content": message})
        reply = llm.guide_reply(_GUIDE_SYSTEM, msgs, kb_context)
        return JsonResponse({"reply": reply, "action": "info"})
    except Exception as e:
        logger.error(f"_handle_guide error: {e}")
        return JsonResponse({
            "reply": "I had trouble finding that in the docs. Try the Help section in the Numen dashboard for full guides.",
            "action": "info",
        })




# These are returned verbatim — no LLM involved, so no chance of the model
# deciding to be "helpful" and answering anyway.
_OUT_OF_SCOPE_REPLY = (
    "That's outside what I can help with — I'm focused on Numen HPC.\n\n"
    "Here's what I'm good at:\n"
    "• *Launch* — \"Launch Relion on a g5 instance\"\n"
    "• *Recommend* — \"What should I use for cryo-EM processing?\"\n"
    "• *Troubleshoot* — \"My cluster is stuck in CREATE_IN_PROGRESS\"\n\n"
    "Give one of those a try and I'll get you sorted."
)


def _handle_other(message: str, history: list):
    return JsonResponse({"reply": _OUT_OF_SCOPE_REPLY, "action": "info"})


# ── Main endpoint ─────────────────────────────────────────────────────────────
# NOTE: /chatbot/message is not called by the frontend (uses /chatbot/stream).
# Commented out — kept for reference only.

# @csrf_exempt
# def chat_message(request):
#     if request.method != "POST":
#         return JsonResponse({"error": "POST required"}, status=405)
#
#     try:
#         body = json.loads(request.body)
#         message = body.get("message", "").strip()[:1000]
#         history = body.get("history", [])
#         email = body.get("email", "dev@localhost.com")
#         current_payload = body.get("current_payload")
#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=400)
#
#     if not message:
#         return JsonResponse({"error": "Empty message"}, status=400)
#
#     llm_history = _clean_history_for_llm(history[-10:])
#     bucket      = _resource_bucket()
#
#     quick_intent = llm.classify_intent(message, history[-6:] if history else [], current_payload=current_payload)
#     if quick_intent == llm.INTENT_LAUNCH:
#         return _handle_launch(message, history, email, current_payload)
#
#     kb_context      = ""
#     session_context = ""
#     recommend_ctx   = ""
#
#     kb_articles = kb_mod.retrieve(message, bucket) if bucket else []
#     kb_context  = kb_mod.format_context(kb_articles)
#
#     if quick_intent == llm.INTENT_HISTORY:
#         records = _load_user_sessions(email)
#         session_context = _build_history_context(records) if records else "No sessions found."
#
#     if quick_intent == llm.INTENT_RECOMMEND:
#         records = _load_user_sessions(email)
#         recommend_ctx = _get_user_launch_history(email) if not records else _build_history_context(records[-5:])
#
#     result = llm.classify_and_respond(
#         message, llm_history,
#         kb_context=kb_context,
#         session_context=session_context,
#         recommend_context=recommend_ctx,
#         current_payload=current_payload,
#         app_list="\n".join(_app_list_line(a) for a in dc.implemented_apps()),
#     )
#
#     intent = result["intent"]
#     reply  = result["reply"]
#
#     if intent == llm.INTENT_LAUNCH:
#         return _handle_launch(message, history, email, current_payload)
#
#     if not reply:
#         return _handle_other(message, history)
#
#     beta = intent in (llm.INTENT_RECOMMEND, llm.INTENT_SUPPORT)
#     return JsonResponse({"reply": reply, "action": "info", "beta": beta, "intent": intent})


@csrf_exempt
def chatbot_status(request):
    """
    Lightweight health check — pings Bedrock with a minimal call.
    Returns {"online": true/false}.
    Called by the frontend on chatbot open to show Online/Offline in the header.
    """

    try:
        llm._call("Reply with OK.", [{"role": "user", "content": "ping"}])
        return JsonResponse({"online": True})
    except Exception as e:
        logger.warning(f"chatbot_status: LLM unreachable: {e}")
        return JsonResponse({"online": False})

@csrf_exempt
def chatbot_options(request):
    # NOTE: /chatbot/options is not called by the frontend. Commented out — kept for reference.
    # try:
    #     return JsonResponse({
    #         "applications": [
    #             {"label": a["title"], "value": a["packageName"], "description": a.get("description", "")}
    #             for a in dc.implemented_apps()
    #         ],
    #     })
    # except Exception as e:
    #     return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Not in use"}, status=404)


@csrf_exempt
def chatbot_feedback(request):
    """
    Receive thumbs-up / thumbs-down feedback from the frontend ChatMessage component.
    Writes a structured log entry so we can track which intents are failing users.

    Expected body:
        {
            "email":    "user@example.com",
            "message":  "the assistant message text",
            "intent":   "support" | "recommend" | ...,
            "helpful":  true | false
        }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        import hashlib
        import datetime as _feedback_dt
        body    = json.loads(request.body)
        email   = body.get('email', '')
        message = body.get('message', '')
        intent  = body.get('intent', 'unknown')
        helpful = body.get('helpful', None)

        # Anonymise — store a hash of the message, not the raw text
        msg_hash = hashlib.sha256(message.encode()).hexdigest()[:16]

        logger.warning(
            'CHATBOT_FEEDBACK | ts=%s | email=%s | intent=%s | helpful=%s | msg_hash=%s',
            _feedback_dt.datetime.utcnow().isoformat(),
            email,
            intent,
            helpful,
            msg_hash,
        )
        return JsonResponse({'ok': True})
    except Exception as e:
        logger.warning('chat_feedback error: %s', e)
        return JsonResponse({'error': str(e)}, status=500)


# =============================================================================
# Numen Agent endpoints — migrated from numen/agent_views.py
# =============================================================================
import datetime as _dt

from django.http import StreamingHttpResponse

from chatbot import bedrock as _bedrock
from chatbot import context as _context
from chatbot import jobs as _jobs
from chatbot import launch as _launch
from chatbot import prompt as _prompt
from chatbot import resources as _resources


# ---------------------------------------------------------------------------
# Non-streaming endpoint  — /chatbot (not used by frontend)
# NOTE: Not called by the frontend (uses /chatbot/stream exclusively).
# Commented out — kept for reference only.
# ---------------------------------------------------------------------------

# @csrf_exempt
# def chatbot(request):
#     if request.method != 'POST':
#         return JsonResponse({'error': 'POST required'}, status=405)
#     try:
#         body            = json.loads(request.body)
#         user_message    = body.get('message', '').strip()
#         history         = body.get('history', [])
#         email           = body.get('email', 'user@numen.local')
#         current_payload = body.get('current_payload') or None
#
#         if not user_message:
#             return JsonResponse({'reply': 'Please tell me what you would like to launch!',
#                                  'action': None, 'payload': None})
#
#         ctx           = _context.get_user_context(email)
#         system_prompt = _prompt.build_system_prompt(ctx, current_payload=current_payload)
#
#         if _jobs.is_job_status_question(user_message):
#             job_ctx = _jobs.build_job_context(email)
#             if job_ctx:
#                 user_message = user_message + '\n\n[LIVE CONTEXT FOR YOUR ANSWER — do not show raw to user]' + job_ctx
#
#         quick_intent = llm.classify_intent(user_message, history[-6:] if history else [], current_payload=current_payload)
#         if quick_intent == llm.INTENT_LAUNCH:
#             return _launch.handle_launch(user_message, history, email, current_payload)
#
#         messages   = _bedrock.build_messages(history, user_message)
#         reply_text = _bedrock.call_nova(messages, system_prompt)
#
#         reply_text, action_data = _resources.extract_action_payload(reply_text)
#         if action_data:
#             act        = action_data.get('action', '').lower()
#             res_type   = action_data.get('resourceType', '').upper()
#             inst_id    = action_data.get('instanceId', '')
#             stack_name = action_data.get('stackName', '')
#             res_name   = action_data.get('resourceName', stack_name)
#             result_msg = _resources.execute_action(act, res_type, inst_id, stack_name)
#             return JsonResponse({
#                 'reply': (reply_text + '\n\n' + result_msg).strip(),
#                 'action': 'action_result',
#                 'payload': None,
#                 'actionResult': {
#                     'action': act, 'resourceName': res_name,
#                     'resourceType': res_type, 'result': result_msg,
#                 },
#                 'context': ctx,
#             })
#
#         reply_text, payload = _launch.extract_payload(reply_text, email)
#         if payload:
#             _schema = None
#             _cost   = None
#             try:
#                 _app = dc.resolve_app(payload.get('applicationName'))
#                 if _app:
#                     _schema = dc.get_config_schema(_app)
#                     _cost   = cost_mod.estimate(payload)
#             except Exception as _e:
#                 logger.warning('chatbot: schema/cost resolve failed: %s', _e)
#         action = 'launch' if payload else None
#
#         return JsonResponse({'reply': reply_text, 'action': action,
#                              'payload': payload, 'context': ctx,
#                              'schema': _schema if payload else None,
#                              'cost':   _cost   if payload else None})
#
#     except Exception as exc:
#         logger.warning("chatbot error %s: %s" % (str(_dt.datetime.now()), str(exc)))
#         return JsonResponse({
#             'reply': (
#                 "I'm having a little trouble right now. Please try again in a moment, "
#                 "or use the step-by-step launch wizard on the main page."
#             ),
#             'action': None, 'payload': None,
#         })


# ---------------------------------------------------------------------------
# Streaming SSE endpoint  — /chatbot/stream
# ---------------------------------------------------------------------------

@csrf_exempt
def chatbot_stream(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        body         = json.loads(request.body)
        user_message = body.get('message', '').strip()
        history      = body.get('history', [])
        email        = body.get('email', 'user@numen.local')

        if not user_message:
            def _empty():
                yield 'data: ' + json.dumps({'type': 'text', 'text': 'Please tell me what you would like to launch!'}) + '\n\n'
                yield 'data: ' + json.dumps({'type': 'done'}) + '\n\n'
            resp = StreamingHttpResponse(_empty(), content_type='text/event-stream')
            resp['Cache-Control'] = 'no-cache'
            resp['X-Accel-Buffering'] = 'no'
            return resp

        ctx             = _context.get_user_context(email)
        current_payload = body.get('current_payload') or None
        system_prompt   = _prompt.build_system_prompt(ctx, current_payload=current_payload)

        # Inject live job status if relevant
        if _jobs.is_job_status_question(user_message):
            job_ctx = _jobs.build_job_context(email)
            if job_ctx:
                user_message = user_message + '\n\n[LIVE CONTEXT FOR YOUR ANSWER — do not show raw to user]' + job_ctx

        # Binary launch check — return structured response (non-streaming for launch)
        quick_intent = llm.classify_intent(user_message, history[-6:] if history else [], current_payload=current_payload)
        if quick_intent == llm.INTENT_LAUNCH:
            current_payload = body.get('current_payload') or None
            launch_response = _launch.handle_launch(user_message, history, email, current_payload)
            # Wrap launch response as SSE so the frontend stream reader handles it
            launch_data = json.loads(launch_response.content)
            def _launch_stream():
                yield 'data: ' + json.dumps({'type': 'text', 'text': launch_data.get('reply', '')}) + '\n\n'
                if launch_data.get('payload'):
                    yield 'data: ' + json.dumps({
                        'type': 'payload',
                        'payload': launch_data['payload'],
                        'cleanText': launch_data.get('reply', ''),
                        'schema':   launch_data.get('schema'),
                        'cost':     launch_data.get('cost'),
                    }) + '\n\n'
                yield 'data: ' + json.dumps({'type': 'done', 'context': ctx}) + '\n\n'
            resp = StreamingHttpResponse(_launch_stream(), content_type='text/event-stream')
            resp['Cache-Control'] = 'no-cache'
            resp['X-Accel-Buffering'] = 'no'
            return resp

        # Package validation — detect before streaming starts
        validate_instance_id = ''
        if _jobs.is_validate_request(user_message):
            validate_instance_id = _jobs.extract_instance_id(user_message)
            if not validate_instance_id:
                user_message = user_message + (
                    "\n\n[NOTE: No EC2 instance ID (i-xxxxxxxx) was found in the user's message. "
                    "Ask them: 'Please share the instance ID (e.g. i-0abc1234) so I can run the validation.']"
                )

        # ── Intent-aware pre-classification for non-launch messages ──────────
        # Loads KB articles and session context appropriate to the likely intent
        # so the streaming Nova call has the right context injected into the prompt.
        _bucket          = _resource_bucket()
        _kb_articles     = kb_mod.retrieve(user_message, _bucket) if _bucket else []
        _kb_context      = kb_mod.format_context(_kb_articles)
        _session_context = ''
        _recommend_ctx   = ''

        if quick_intent == llm.INTENT_HISTORY:
            _records = _load_user_sessions(email)
            _session_context = _build_history_context(_records) if _records else 'No sessions found.'
        elif quick_intent == llm.INTENT_RECOMMEND:
            _records = _load_user_sessions(email)
            _recommend_ctx = _build_history_context(_records[-5:]) if _records else ''

        # Augment system prompt with KB and session context before streaming
        _augmented_system = system_prompt
        if _kb_context:
            _augmented_system += f'\n\n[KNOWLEDGE BASE]\n{_kb_context}\n[/KNOWLEDGE BASE]'
        if _session_context:
            _augmented_system += f'\n\n[USER SESSION HISTORY]\n{_session_context}\n[/USER SESSION HISTORY]'
        if _recommend_ctx:
            _augmented_system += f'\n\n[USER HISTORY FOR RECOMMENDATIONS]\n{_recommend_ctx}\n[/USER HISTORY FOR RECOMMENDATIONS]'

        messages = _bedrock.build_messages(history, user_message)

    except Exception as exc:
        logger.warning("chatbot_stream parse error: " + str(exc))
        def _err():
            yield 'data: ' + json.dumps({'type': 'error',
                'message': 'Could not process your request. Please try again.'}) + '\n\n'
        resp = StreamingHttpResponse(_err(), content_type='text/event-stream')
        resp['Cache-Control'] = 'no-cache'
        resp['X-Accel-Buffering'] = 'no'
        return resp

    def event_stream():
        full_text = ''
        _messages = messages
        try:
            # Package validation — run SSM inside the stream to avoid ALB idle timeout
            if validate_instance_id:
                yield 'data: ' + json.dumps({'type': 'text',
                    'text': f'Running package validation on `{validate_instance_id}` — this may take up to 60 seconds...\n\n'}) + '\n\n'

                raw    = _jobs.validate_packages_on_instance(validate_instance_id)
                lines  = raw.splitlines()
                formatted = []
                for ln in lines:
                    if ln.startswith('PASS |'):
                        parts = ln.split('|', 2)
                        formatted.append(f"PASS: {parts[1].strip()} — {parts[2].strip() if len(parts) > 2 else 'OK'}")
                    elif ln.startswith('FAIL |'):
                        parts = ln.split('|', 2)
                        formatted.append(f"FAIL: {parts[1].strip()} — NOT INSTALLED")
                    elif ln.startswith('SKIP |'):
                        parts = ln.split('|', 2)
                        formatted.append(f"SKIP: {parts[1].strip()} — {parts[2].strip() if len(parts) > 2 else 'skipped'}")
                    elif ln.startswith('SUMMARY') or ln.startswith('---'):
                        formatted.append(ln)
                validate_ctx = (
                    f"\n\n[LIVE VALIDATION RESULTS for instance {validate_instance_id} — present these clearly to the user with checkmark/x icons]\n"
                    + '\n'.join(formatted)
                )
                augmented = user_message + validate_ctx
                _messages  = _bedrock.build_messages(history, augmented)
                full_text  = f'Running package validation on `{validate_instance_id}` — this may take up to 60 seconds...\n\n'

            for chunk in _bedrock.stream_nova(_messages, _augmented_system):
                full_text += chunk
                yield 'data: ' + json.dumps({'type': 'text', 'text': chunk}) + '\n\n'

            # Check for action-payload
            clean_text, action_data = _resources.extract_action_payload(full_text)
            if action_data:
                action      = action_data.get('action', '').lower()
                res_type    = action_data.get('resourceType', '').upper()
                instance_id = action_data.get('instanceId', '')
                stack_name  = action_data.get('stackName', '')
                res_name    = action_data.get('resourceName', stack_name)
                result_msg  = _resources.execute_action(action, res_type, instance_id, stack_name)
                yield 'data: ' + json.dumps({
                    'type': 'action_result',
                    'cleanText': clean_text,
                    'resultMessage': result_msg,
                    'action': action,
                    'resourceName': res_name,
                    'resourceType': res_type,
                }) + '\n\n'
            else:
                # Check for launch-payload
                clean_text, payload = _launch.extract_payload(full_text, email)
                if payload:
                    # Resolve schema + cost so the LaunchConfirmCard is fully editable
                    _schema = None
                    _cost   = None
                    try:
                        _app = dc.resolve_app(payload.get('applicationName'))
                        if _app:
                            _schema = dc.get_config_schema(_app)
                            _cost   = cost_mod.estimate(payload)
                    except Exception as _e:
                        logger.warning("chatbot_stream: schema/cost resolve failed: %s", _e)
                    yield 'data: ' + json.dumps({
                        'type':      'payload',
                        'payload':   payload,
                        'cleanText': clean_text,
                        'schema':    _schema,
                        'cost':      _cost,
                    }) + '\n\n'

            yield 'data: ' + json.dumps({'type': 'done', 'context': ctx, 'sanitized': llm._sanitize_text(full_text)}) + '\n\n'

        except Exception as exc:
            logger.warning("chatbot_stream stream error: " + str(exc))
            error_msg = _bedrock.friendly_error(str(exc))
            yield 'data: ' + json.dumps({'type': 'error', 'message': error_msg}) + '\n\n'

    resp = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    resp['Cache-Control'] = 'no-cache'
    resp['X-Accel-Buffering'] = 'no'
    return resp
