"""Write participant .env with baked secrets for event packages."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.pin_service import generate_pin_verifier

EVENT_ENV_LINES = """# TRADEVERSE participant event package — auto-generated, do not edit
LOCAL_INSTANCE_MODE=true
PARTICIPANT_EVENT_MODE=true
DEVELOPER_MODE=false
ENVIRONMENT=production
DEBUG=false
AUTO_INIT_DB=true

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

PROJECTOR_ENV_LINES = """# TRADEVERSE projector package — auto-generated
LOCAL_INSTANCE_MODE=true
PARTICIPANT_EVENT_MODE=false
DEVELOPER_MODE=false
PROJECTOR_MODE=true
ENVIRONMENT=production
DEBUG=false
AUTO_INIT_DB=true

BACKEND_HOST=127.0.0.1
BACKEND_PORT=8765
BACKEND_URL=http://127.0.0.1:8765
FRONTEND_URL=http://127.0.0.1:8765
CORS_ORIGINS=http://127.0.0.1:8765,http://localhost:8765

DEFAULT_STARTING_CAPITAL=500000
SIMULATION_SPEED=1
RANDOM_SEED=42

SERVE_STATIC_UI=true
HIDE_ADMIN_UI=true
NEXT_PUBLIC_LOCAL_INSTANCE=true

NEXT_PUBLIC_API_URL=http://127.0.0.1:8765
NEXT_PUBLIC_WS_URL=ws://127.0.0.1:8765
NEXT_PUBLIC_API_PREFIX=/api/v1
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate participant event .env")
    parser.add_argument("--event-pin", default=os.environ.get("EVENT_PIN", "0000"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--projector", action="store_true", help="Write projector .env (no PIN)")
    args = parser.parse_args()

    if args.projector:
        content = PROJECTOR_ENV_LINES
    else:
        pin_salt, pin_hash = generate_pin_verifier(args.event_pin.strip())
        content = EVENT_ENV_LINES.format(pin_salt=pin_salt, pin_hash=pin_hash)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")
    print(f"Wrote event .env to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
