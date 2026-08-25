"""Write participant .env with baked secrets for event packages."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.pin_service import generate_pin_verifier
from app.services.timeline_crypto import bake_timeline_for_participant

EVENT_ENV_LINES = """# TRADEVERSE participant event package — auto-generated, do not edit
LOCAL_INSTANCE_MODE=true
PARTICIPANT_EVENT_MODE=true
DEVELOPER_MODE=false
ENVIRONMENT=production
DEBUG=false
AUTO_INIT_DB=true
TIMELINE_EMBEDDED=true

BACKEND_HOST=127.0.0.1
BACKEND_PORT=8765
BACKEND_URL=http://127.0.0.1:8765
FRONTEND_URL=http://127.0.0.1:8765
CORS_ORIGINS=http://127.0.0.1:8765,http://localhost:8765

DEFAULT_STARTING_CAPITAL=500000
MAX_POSITION_PER_STOCK=100
SIMULATION_SPEED=1
RANDOM_SEED=42

SERVE_STATIC_UI=true
HIDE_ADMIN_UI=true
NEXT_PUBLIC_LOCAL_INSTANCE=true
NEXT_PUBLIC_PARTICIPANT_EVENT_MODE=true

NEXT_PUBLIC_API_URL=http://127.0.0.1:8765
NEXT_PUBLIC_WS_URL=ws://127.0.0.1:8765
NEXT_PUBLIC_API_PREFIX=/api/v1

EVENT_PIN_SALT={pin_salt}
EVENT_PIN_HASH={pin_hash}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate participant event .env")
    parser.add_argument("--timeline-key", required=True)
    parser.add_argument("--event-pin", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--bake-timeline",
        type=Path,
        default=None,
        help="Optional path to write baked timeline JSON for participant runtime",
    )
    args = parser.parse_args()

    pin_salt, pin_hash = generate_pin_verifier(args.event_pin.strip())
    bake_dest = args.bake_timeline
    if bake_dest is None:
        bake_dest = Path(__file__).resolve().parents[1] / "app" / "seed" / "tradeverse_timeline.baked.json"
    bake_timeline_for_participant(args.timeline_key.strip(), dest=bake_dest)

    content = EVENT_ENV_LINES.format(pin_salt=pin_salt, pin_hash=pin_hash)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")
    print(f"Wrote event .env to {args.output}")
    print(f"Baked timeline to {bake_dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
