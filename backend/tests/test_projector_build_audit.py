"""Projector static build must not ship participant/admin/developer routes or leaks."""

from __future__ import annotations

from pathlib import Path

from tests.audit_patterns import (
    PROJECTOR_ALLOWED_ROUTES,
    PROJECTOR_FORBIDDEN_DIRS,
    PROJECTOR_FORBIDDEN_PATTERNS,
)


def _scan_projector_out(out: Path) -> list[str]:
    failures: list[str] = []
    for forbidden in PROJECTOR_FORBIDDEN_DIRS:
        if (out / forbidden).exists():
            failures.append(f"projector build must not include out/{forbidden}")
    for entry in out.iterdir():
        if not entry.is_dir():
            continue
        rel = entry.name
        if rel.startswith("_"):
            continue
        if rel not in PROJECTOR_ALLOWED_ROUTES:
            failures.append(f"projector build must not include out/{rel}")
    for path in out.rglob("*"):
        if not path.is_file():
            continue
        rel = str(path.relative_to(out))
        if rel.startswith("_next/static/chunks/framework"):
            continue
        if "/framework-" in rel:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern in PROJECTOR_FORBIDDEN_PATTERNS:
            if pattern in content:
                failures.append(f"{rel}: contains '{pattern}'")
    return failures


def test_projector_out_prunes_participant_routes():
    root = Path(__file__).resolve().parents[2]
    out = root / "frontend" / "out"
    if not out.is_dir():
        return
    for forbidden in PROJECTOR_FORBIDDEN_DIRS:
        assert not (out / forbidden).exists(), f"projector build must not include out/{forbidden}"


def test_projector_out_forbidden_content_audit():
    root = Path(__file__).resolve().parents[2]
    out = root / "frontend" / "out"
    if not out.is_dir():
        return
    failures = _scan_projector_out(out)
    assert not failures, "\n".join(failures[:25])


def test_projector_page_renders_market_change_pct():
    """Projector UI must surface overall market movement (Phase 4.5 P45-001)."""
    root = Path(__file__).resolve().parents[2]
    page = root / "frontend" / "src" / "app" / "projector" / "page.tsx"
    source = page.read_text(encoding="utf-8")
    assert "market_change_pct" in source
    assert "Market movement" in source or "market movement" in source.lower()
