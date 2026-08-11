"""Typed failures and declared scientific boundaries used by the reproduction CLI."""
from __future__ import annotations


class ReproductionError(RuntimeError):
    """Base class for an expected, user-actionable reproduction failure."""


class BlockedError(ReproductionError):
    """A run cannot proceed without a declared external prerequisite."""
    def __init__(self, code: str, message: str, *, details: list[str] | None = None):
        super().__init__(message); self.code = code; self.details = details or []


class ScientificBoundary(ReproductionError):
    """Execution succeeded but a frozen scientific continuation gate did not reproduce."""
    def __init__(self, code: str, message: str, *, details: list[str] | None = None, evidence: dict | None = None):
        super().__init__(message); self.code = code; self.details = details or []; self.evidence = evidence or {}


class IntegrityError(ReproductionError):
    """A sealed input, source file, or generated output failed verification."""
