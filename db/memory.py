"""Agent memory lookups: skip redundant LLM planning calls for known failures."""

import hashlib
import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from db.models import AgentMemory


def compute_error_signature(log_excerpt: str) -> str:
    """Normalize a log excerpt (strip paths/line numbers/timestamps) and hash it,
    so semantically identical failures map to the same signature.
    """
    normalized = re.sub(r"\d+", "", log_excerpt)
    normalized = re.sub(r"\s+", " ", normalized).strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def lookup_known_fix(session: Session, error_signature: str) -> str | None:
    """Return a previously successful diff for this error signature, if any."""
    memory = (
        session.query(AgentMemory)
        .filter(AgentMemory.error_signature == error_signature)
        .one_or_none()
    )
    if memory is None:
        return None
    memory.hit_count += 1
    memory.last_used_at = datetime.now(timezone.utc)
    session.commit()
    return memory.successful_diff


def record_successful_fix(session: Session, error_signature: str, diff_text: str) -> None:
    memory = (
        session.query(AgentMemory)
        .filter(AgentMemory.error_signature == error_signature)
        .one_or_none()
    )
    if memory is None:
        memory = AgentMemory(error_signature=error_signature, successful_diff=diff_text)
        session.add(memory)
    else:
        memory.successful_diff = diff_text
    session.commit()
