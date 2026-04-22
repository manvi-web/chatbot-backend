"""
Phase 3 — Knowledge Base retrieval.

Reads all Numen help .md files directly from S3 — the same files
the frontend Help section serves. Covers:
  - App user guides (Relion, cryoSPARC, AlphaFold, Warpem, SBGrid, Gromacs)
  - FAQs
  - Product documentation
  - About Numen

No intermediate JSON files, no ingestion step.
Sections are chunked by # headings and cached in-memory (TTL = 1 hour).

Set KB_ENABLED=true in the environment to activate.
"""
import logging
import os
import re
import time

import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)

KB_ENABLED = os.environ.get("KB_ENABLED", "false").lower() == "true"
KB_TTL     = 3600  # seconds

# Help doc version prefix — set NUMEN_HELP_DOC_VERSION in env to override.
# Mirrors the version prefix used in the S3 help-docs bucket.
_DOC_VER = os.environ.get("NUMEN_HELP_DOC_VERSION", "1.5")

# All known help doc keys — mirrors app.constants.ts HelpApplications + others
MD_FILES = [
    (f"assets/help-docs/md/{_DOC_VER}-relion-4-user-guide.md",        "relion"),
    (f"assets/help-docs/md/{_DOC_VER}-cryosparc-user-guide.md",       "cryosparc"),
    (f"assets/help-docs/md/{_DOC_VER}-alphafold-user-guide.md",       "alphafold"),
    (f"assets/help-docs/md/{_DOC_VER}-warpem-user-guide.md",          "warpem"),
    (f"assets/help-docs/md/{_DOC_VER}-sbgrid-user-guide.md",          "sbgrid"),
    (f"assets/help-docs/md/{_DOC_VER}-gromacs-user-guide.md",         "gromacs"),
    (f"assets/help-docs/md/{_DOC_VER}-numen-faqs.md",                 "faqs"),
    (f"assets/help-docs/md/{_DOC_VER}-product-documentation.md",      "numen"),
    (f"assets/help-docs/md/{_DOC_VER}-about.md",                      "numen"),
]

_config = Config(retries={"max_attempts": 3, "mode": "standard"})
_s3     = None

_kb_cache: list  = []
_kb_loaded_at: float = 0.0


def _get_s3():
    global _s3
    if _s3 is None:
        region = os.environ.get("CHATBOT_AWS_REGION", "us-east-1")
        _s3 = boto3.client("s3", config=_config, region_name=region)
    return _s3


# ── Markdown chunking ─────────────────────────────────────────────────────────

def _chunk_markdown(content: str, app: str) -> list:
    """
    Split a markdown file into sections by # headings.
    Each section → one searchable chunk: {title, tags, body}.
    """
    sections      = []
    current_title = app
    current_lines = []

    for line in content.splitlines():
        m = re.match(r"^#{1,3}\s+(.+)", line)
        if m:
            body = "\n".join(current_lines).strip()
            if body:
                tags = [app] + [w.lower() for w in current_title.split() if len(w) > 3]
                sections.append({"title": f"{app} — {current_title}", "tags": tags, "body": body})
            current_title = m.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)

    # flush last section
    body = "\n".join(current_lines).strip()
    if body:
        tags = [app] + [w.lower() for w in current_title.split() if len(w) > 3]
        sections.append({"title": f"{app} — {current_title}", "tags": tags, "body": body})

    return sections


# ── Loading ───────────────────────────────────────────────────────────────────

def _load_kb(bucket: str):
    global _kb_cache, _kb_loaded_at

    now = time.monotonic()
    if _kb_cache and (now - _kb_loaded_at) < KB_TTL:
        return  # still fresh

    s3 = _get_s3()
    articles = []
    for key, app in MD_FILES:
        try:
            content = s3.get_object(Bucket=bucket, Key=key)["Body"].read().decode("utf-8")
            chunks  = _chunk_markdown(content, app)
            articles.extend(chunks)
            logger.info(f"KB: loaded {len(chunks)} sections from {key}")
        except Exception as e:
            logger.warning(f"KB: skipped {key}: {e}")

    if articles:
        _kb_cache     = articles
        _kb_loaded_at = now
        logger.info(f"KB ready: {len(articles)} total sections")
    elif not _kb_cache:
        _kb_cache = []


# ── Retrieval ─────────────────────────────────────────────────────────────────

def _score(article: dict, query_words: set) -> int:
    text = (article.get("title", "") + " " +
            " ".join(article.get("tags", [])) + " " +
            article.get("body", "")).lower()
    return sum(1 for w in query_words if w in text)


def retrieve(query: str, bucket: str, top_k: int = 3) -> list:
    """
    Returns up to top_k article bodies relevant to the query.
    Returns [] if KB is disabled or nothing matches.
    """
    if not KB_ENABLED:
        return []
    _load_kb(bucket)
    if not _kb_cache:
        return []
    words  = {w for w in query.lower().split() if len(w) > 2}
    scored = [(a, _score(a, words)) for a in _kb_cache]
    scored = [(a, s) for a, s in scored if s > 0]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [a["body"] for a, _ in scored[:top_k]]


def format_context(articles: list) -> str:
    if not articles:
        return ""
    parts = ["Relevant knowledge base articles:"]
    for i, body in enumerate(articles, 1):
        parts.append(f"[{i}] {body}")
    return "\n\n".join(parts)
