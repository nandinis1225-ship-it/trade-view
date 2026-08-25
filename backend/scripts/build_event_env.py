"""Write participant .env with baked secrets for event packages."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

DEFAULT_TEMPLATE = Path(__file__).resolve().parents[2] / ".env.offline-participant.example"

EVENT_ENV_LINES = """# TRADEVERSE participant event package — auto-generated, do not edit
LOCAL_INSTANCE_MODE=true
PARTICIPANT_EVENT_MODE=true
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

TIMELINE_DECRYPT_KEY={timeline_key}
EVENT_PIN={event_pin}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate participant event .env")
    parser.add_argument("--timeline-key", required=True)
    parser.add_argument("--event-pin", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    content = EVENT_ENV_LINES.format(
        timeline_key=args.timeline_key.strip(),
        event_pin=args.event_pin.strip(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")
    print(f"Wrote event .env to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
