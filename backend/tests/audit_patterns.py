"""Shared forbidden-content patterns for participant and projector static builds.

Must stay aligned with scripts/offline/audit-participant-build.ps1 (Phase 3.5 frozen).
"""

from __future__ import annotations

PARTICIPANT_FORBIDDEN_DIRS = ("admin", "market-screen", "developer")

PARTICIPANT_FORBIDDEN_PATTERNS = (
    "TIMELINE_DECRYPT_KEY",
    "tradeverse_timeline.json",
    "tradeverse_timeline.baked.json",
    "tradeverse_timeline.pkg",
    "SUPABASE",
    "supabase.co",
    "railway.app",
    "leaderboard",
    "EUPHORIA",
    "CRASH",
    "RECOVERY",
    "PHASE 1",
    "PHASE 2",
    "PHASE 3",
    "PHASE 4",
    "AI_TICK",
    "MARKET_PULSE",
    "sector_impacts",
    "effective_impact",
    "stop_loss",
    "take_profit",
    "current_phase",
    "OrganizerDebugPanel",
    "/developer",
    "adminLogin",
)

PROJECTOR_FORBIDDEN_DIRS = ("admin", "market-screen", "developer", "terminal")

PROJECTOR_FORBIDDEN_PATTERNS = (
    "TIMELINE_DECRYPT_KEY",
    "tradeverse_timeline.json",
    "tradeverse_timeline.baked.json",
    "tradeverse_timeline.pkg",
    "SUPABASE",
    "supabase.co",
    "railway.app",
    "leaderboard",
    "EUPHORIA",
    "CRASH",
    "RECOVERY",
    "PHASE 1",
    "PHASE 2",
    "PHASE 3",
    "PHASE 4",
    "AI_TICK",
    "sector_impacts",
    "effective_impact",
    "stop_loss",
    "take_profit",
    "current_phase",
    "OrganizerDebugPanel",
    "/developer",
    "adminLogin",
    "fair_value",
    "PinGateOverlay",
    "RecoveryScreen",
    "EventCompleteScreen",
)

PROJECTOR_ALLOWED_ROUTES = frozenset({"", "projector", "_next", "404", "favicon.ico"})
