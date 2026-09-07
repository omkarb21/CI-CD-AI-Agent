"""SQLAlchemy models for CI run tracking, patch history, and agent memory."""

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Run(Base):
    """One observed GitHub Actions run (successful or failed)."""

    __tablename__ = "runs"

    id = Column(Integer, primary_key=True)
    repo = Column(String, nullable=False)
    workflow_run_id = Column(String, nullable=False)
    commit_sha = Column(String, nullable=False)
    branch = Column(String, nullable=False)
    status = Column(String, nullable=False)  # queued | running | fixed | failed | abandoned
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    failures = relationship("Failure", back_populates="run", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("repo", "workflow_run_id", name="uq_run_repo_workflow"),)


class Failure(Base):
    """A specific failure detected within a run (e.g. one failing job/step)."""

    __tablename__ = "failures"

    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False)
    job_name = Column(String, nullable=False)
    step_name = Column(String, nullable=True)
    error_signature = Column(String, nullable=False, index=True)  # hash of normalized error text
    log_excerpt = Column(Text, nullable=False)
    diff_context = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    run = relationship("Run", back_populates="failures")
    patches = relationship("Patch", back_populates="failure", cascade="all, delete-orphan")


class Patch(Base):
    """A patch the agent proposed for a given failure, and its outcome."""

    __tablename__ = "patches"

    id = Column(Integer, primary_key=True)
    failure_id = Column(Integer, ForeignKey("failures.id"), nullable=False)
    diff = Column(Text, nullable=False)
    planner_reasoning = Column(Text, nullable=True)
    critic_verdict = Column(String, nullable=True)  # pass | fail
    critic_notes = Column(Text, nullable=True)
    iteration = Column(Integer, nullable=False, default=1)
    committed = Column(String, nullable=False, default="no")  # no | pr_opened | pushed
    pr_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    failure = relationship("Failure", back_populates="patches")


class AgentMemory(Base):
    """Cache of (error_signature -> best known patch) to skip redundant LLM calls."""

    __tablename__ = "agent_memory"

    id = Column(Integer, primary_key=True)
    error_signature = Column(String, nullable=False, unique=True, index=True)
    successful_diff = Column(Text, nullable=False)
    hit_count = Column(Integer, nullable=False, default=0)
    last_used_at = Column(DateTime(timezone=True), default=utcnow)
    created_at = Column(DateTime(timezone=True), default=utcnow)
