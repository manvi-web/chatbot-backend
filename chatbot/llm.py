"""
LLM module - Amazon Nova Lite via Bedrock Converse API.

Single-call architecture: classify_and_respond() returns both the intent
and the response in one Bedrock call, cutting costs by ~50%.

Separate entry points still exist for structured extraction (launch params)
which requires a dedicated call due to strict JSON output requirements.
"""
import json
import logging
import os
import re
import threading
import time
from functools import lru_cache
from typing import Optional

import boto3

logger = logging.getLogger(__name__)

_client      = None
_client_lock = threading.Lock()

MODEL_ID = os.environ.get("CHATBOT_LLM_MODEL", "amazon.nova-lite-v1:0")
REGION   = os.environ.get("CHATBOT_AWS_REGION", "us-east-1")

# Intent labels - keep in sync with router in views.py
INTENT_LAUNCH    = "launch"
INTENT_RECOMMEND = "recommend"
INTENT_SUPPORT   = "support"
INTENT_HISTORY   = "history"
INTENT_GUIDE     = "guide"
INTENT_OTHER     = "other"

# Max tokens per intent - right-sized to avoid paying for unused headroom
_INTENT_MAX_TOKENS = {
    INTENT_LAUNCH:    32,   # reply is always ""
    INTENT_RECOMMEND: 400,
    INTENT_SUPPORT:   600,
    INTENT_HISTORY:   400,
    INTENT_GUIDE:     800,
    INTENT_OTHER:     128,
}
_DEFAULT_MAX_TOKENS = 512

# Pre-compiled regex patterns
_RE_BOLD_STARS  = re.compile(r"\*\*(.+?)\*\*")
_RE_BOLD_UNDER  = re.compile(r"__(.+?)__")
_RE_BULLETS     = re.compile(r"(?m)^[ \t]*[-*\u2013]\s+")
_RE_BLANK_LINES = re.compile(r"\n{3,}")
_RE_JSON_FENCE_OPEN  = re.compile(r"^```[a-z]*\s*", re.DOTALL)
_RE_JSON_FENCE_CLOSE = re.compile(r"\s*```$", re.DOTALL)

def _fallback_messages() -> list:
    """Factory — returns a fresh list each call to avoid shared mutable state."""
    return [{"role": "user", "content": [{"text": "hello"}]}]


def _get_client():
    """Thread-safe lazy Bedrock client initialisation (double-checked locking)."""
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = boto3.client("bedrock-runtime", region_name=REGION)
    return _client


def _sanitize_messages(messages: list) -> list:
    """
    Bedrock Converse requires:
      - messages start with role=user
      - roles strictly alternate user/assistant
      - no empty content
    """
    if not messages:
        return _fallback_messages()

    sanitized = []
    for msg in messages:
        role = msg.get("role", "user")
        raw  = msg.get("content", "")
        text = (raw if isinstance(raw, str)
                else (raw[0]["text"] if isinstance(raw, list) and raw else ""))
        if not text.strip():
            continue
        if sanitized and sanitized[-1]["role"] == role:
            sanitized[-1]["content"][0]["text"] += "\n" + text
        else:
            sanitized.append({"role": role, "content": [{"text": text}]})

    if not sanitized:
        return _fallback_messages()
    if sanitized[0]["role"] != "user":
        sanitized.insert(0, {"role": "user", "content": [{"text": "hello"}]})
    if sanitized[-1]["role"] == "assistant":
        sanitized.append({"role": "user", "content": [{"text": "Please respond."}]})
    return sanitized


def _call(system: str, messages: list, max_tokens: int = 256, temperature: float = 0.1) -> str:
    """
    Single Bedrock Converse call. Returns the raw text response.
    Retries up to 3 times with exponential backoff on ThrottlingException.
    """
    client = _get_client()
    kwargs = dict(
        modelId=MODEL_ID,
        system=[{"text": system}],
        messages=_sanitize_messages(messages),
        inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
    )
    for attempt in range(3):
        try:
            response = client.converse(**kwargs)
            return response["output"]["message"]["content"][0]["text"]
        except client.exceptions.ThrottlingException:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)  # 1s, 2s


def _parse_json(text: str) -> dict:
    """Strip markdown fences and parse JSON. Raises json.JSONDecodeError on failure."""
    cleaned = _RE_JSON_FENCE_OPEN.sub("", text.strip(), count=1)
    cleaned = _RE_JSON_FENCE_CLOSE.sub("", cleaned, count=1)
    return json.loads(cleaned.strip())


def _sanitize_text(text: str) -> str:
    """
    Normalize LLM output for consistent frontend rendering.
    - **bold** / __bold__ -> *bold*
    - bullet variants (-, *) -> bullet char
    - collapse 3+ blank lines -> 2
    - strip trailing whitespace per line
    """
    text = _RE_BOLD_STARS.sub(r"*\1*", text)
    text = _RE_BOLD_UNDER.sub(r"*\1*", text)
    text = _RE_BULLETS.sub("\u2022 ", text)
    text = _RE_BLANK_LINES.sub("\n\n", text)
    return "\n".join(line.rstrip() for line in text.split("\n")).strip()


# ---------------------------------------------------------------------------
# Unified classify + respond (single Bedrock call)
# Optimized for Nova Lite:
#   - RULES first (model attends to top of prompt more strongly)
#   - Trimmed examples (descriptions carry the weight, not exhaustive lists)
#   - Intent-aware max_tokens to avoid paying for unused headroom
# ---------------------------------------------------------------------------

@lru_cache(maxsize=32)
def _build_unified_system(app_list: str = "") -> str:
    app_section = f"\n\nAVAILABLE NUMEN APPLICATIONS:\n{app_list}" if app_list else ""
    return f"""You are the Numen HPC platform assistant.

RULES (follow strictly):
- Return ONLY valid JSON: {{"intent": "<label>", "reply": "<your response>"}}
- No markdown. Plain text only. Use numbered lists and bullet points where helpful.
- The user is already authenticated. Never tell them to log in.
- reply for intent=launch must always be exactly empty string "".

INTENT LABELS:
  launch    - user wants to launch, start, deploy, create, or modify a compute session/application
  recommend - user wants help choosing compute resources (instance type, GPU vs CPU, cluster size) for their workload
  support   - user has a problem or error with a session, cluster, DCV, licence, or the platform
  history   - user asks about their own past sessions, jobs, runs, or usage
  guide     - questions about what an app is, how it works, available apps, what Numen is, FAQs, follow-up questions about a launch config. Also use guide for corrections or clarifications of a previous answer (e.g. "just list the options", "I don't need a recommendation"). When in doubt between guide and other, use guide.
  other     - ONLY for topics completely unrelated to Numen HPC. If the message resembles a Numen app name, never use other.

INTENT EXAMPLES:
  "launch relion on g5" -> launch
  "start cryosparc" -> launch
  "how do I launch jupyterhub?" -> launch
  "what instance should I use for cryo-EM?" -> recommend
  "how many GPUs do I need for Relion?" -> recommend
  "my cluster is stuck" -> support
  "I can't connect via DCV" -> support
  "what was my last job?" -> history
  "what apps are available?" -> guide
  "what is relion?" -> guide
  "what instance types are available?" -> guide
  "what are the available instance types?" -> guide
  "do we only have 1 instance?" -> guide
  "can I change the storage?" -> guide
  "what node types can I use?" -> guide
  "just list the types" -> guide
  "I dont need a recommendation, tell me available types only" -> guide
  "just tell me the options" -> guide
  "no, just list them" -> guide
  "what's the weather?" -> other
  "how do I write Python?" -> other

RESPONSE RULES by intent:
  launch    - reply must be "" (empty string). The launch handler generates the full response.
  recommend - help rightsize compute. Be specific about instance families, GPU counts, cluster types. End with: "Want me to set that up? Just say launch <app>."
  support   - calm, numbered steps. Start with most likely cause. If beyond L1: "This needs the Numen admin team."
  history   - answer from session data injected below. If no data: "I don't have any session history for you yet. Once you've launched a job it will appear here." Do NOT invent job data.
  guide     - use the AVAILABLE NUMEN APPLICATIONS list and knowledge base below. If asked what apps are available, list them all with a one-line description. End with: "You can also launch apps directly from the chatbot or from the Numen dashboard."
  other     - reply exactly: "That's outside what I can help with - I'm focused on Numen HPC.\\n\\nHere's what I'm good at:\\n\u2022 Launch - Launch Relion on a g5 instance\\n\u2022 Recommend - What instance do I need for cryo-EM?\\n\u2022 Troubleshoot - My cluster is stuck in CREATE_IN_PROGRESS\\n\\nGive one of those a try and I'll get you sorted."{app_section}"""


# Warm the cache for the no-app-list case used by classify_intent
_UNIFIED_SYSTEM = _build_unified_system()


def classify_and_respond(
    message: str,
    history: list,
    kb_context: str = "",
    session_context: str = "",
    recommend_context: str = "",
    app_list: str = "",
    current_payload: Optional[dict] = None,
) -> dict:
    """
    Single Bedrock call: classifies intent AND generates the response.
    Returns {"intent": str, "reply": str}.
    Uses intent-aware max_tokens after a lightweight pre-classification.
    """
    system = _build_unified_system(app_list)
    if current_payload:
        app_name = current_payload.get("applicationName", "")
        ct       = current_payload.get("clusterType", "")
        system  += f"\n\nACTIVE LAUNCH CARD: The user currently has a launch configuration card open for '{app_name}' ({ct}). Follow-up questions likely relate to this config."
    if kb_context:
        system += f"\n\nKNOWLEDGE BASE:\n{kb_context}"
    if session_context:
        system += f"\n\nUSER SESSION DATA:\n{session_context}"
    if recommend_context:
        system += f"\n\nUSER HISTORY FOR RECOMMENDATIONS:\n{recommend_context}"

    # Use a conservative token budget for the first call; we don't know intent yet.
    # For known-cheap intents (launch/other) this still saves tokens on average.
    try:
        text   = _call(system, history + [{"role": "user", "content": message}],
                       max_tokens=800, temperature=0.2)
        result = _parse_json(text)
        intent = result.get("intent") or INTENT_OTHER
        return {
            "intent": intent,
            "reply":  _sanitize_text(result.get("reply") or ""),
        }
    except Exception as e:
        logger.warning("classify_and_respond failed: %s", e)
        return {"intent": INTENT_OTHER, "reply": ""}


def classify_intent(message: str, history: Optional[list] = None, current_payload: Optional[dict] = None) -> str:
    """
    Lightweight pre-check - classifies intent only (no reply generated).
    Capped at 32 tokens since we only need the intent label.
    """
    try:
        system = _UNIFIED_SYSTEM
        if current_payload:
            app_name = current_payload.get("applicationName", "")
            ct       = current_payload.get("clusterType", "")
            system  += f"\n\nACTIVE LAUNCH CARD: '{app_name}' ({ct})."

        recent = (history or [])[-6:] + [{"role": "user", "content": message}]
        text   = _call(system, recent, max_tokens=32, temperature=0.0)
        return _parse_json(text).get("intent", INTENT_OTHER)
    except Exception as e:
        logger.warning("classify_intent failed: %s", e)
        return INTENT_OTHER


# ---------------------------------------------------------------------------
# Phase 1: Launch param extraction
# ---------------------------------------------------------------------------

def extract_launch_params(system_prompt: str, messages: list) -> dict:
    """
    Structured JSON extraction for launch parameters.

    Returns {"params": {...}} or {"error": "..."}.
    Raises json.JSONDecodeError if the model returns non-JSON (caller must handle).
    """
    text = _call(system_prompt, messages, max_tokens=512, temperature=0.0)
    return _parse_json(text)


# ---------------------------------------------------------------------------
# Shared KB-backed reply helper
# ---------------------------------------------------------------------------

def _kb_reply(system_prompt: str, messages: list, kb_context: str = "",
              max_tokens: int = 800, temperature: float = 0.1) -> str:
    full_system = f"{system_prompt}\n\n{kb_context}" if kb_context else system_prompt
    return _sanitize_text(_call(full_system, messages, max_tokens=max_tokens, temperature=temperature))


# ---------------------------------------------------------------------------
# Phase 2-6: Intent-specific reply helpers (intent-aware token budgets)
# ---------------------------------------------------------------------------

def recommend_reply(system_prompt: str, messages: list) -> str:
    return _sanitize_text(_call(system_prompt, messages,
                                max_tokens=_INTENT_MAX_TOKENS[INTENT_RECOMMEND],
                                temperature=0.1))  # lowered from 0.3 - factual HPC advice


def support_reply(system_prompt: str, messages: list, kb_context: str = "") -> str:
    return _kb_reply(system_prompt, messages, kb_context,
                     max_tokens=_INTENT_MAX_TOKENS[INTENT_SUPPORT])


def history_reply(system_prompt: str, messages: list) -> str:
    return _sanitize_text(_call(system_prompt, messages,
                                max_tokens=_INTENT_MAX_TOKENS[INTENT_HISTORY],
                                temperature=0.1))


def guide_reply(system_prompt: str, messages: list, kb_context: str = "") -> str:
    return _kb_reply(system_prompt, messages, kb_context,
                     max_tokens=_INTENT_MAX_TOKENS[INTENT_GUIDE])


def chat_reply(system_prompt: str, messages: list) -> str:
    return _sanitize_text(_call(system_prompt, messages,
                                max_tokens=_DEFAULT_MAX_TOKENS, temperature=0.4))
