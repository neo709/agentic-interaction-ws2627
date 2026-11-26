"""Protokoll eines Laufs: eine JSONL-Datei pro Lauf in logs/."""

import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import uuid4

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"


def elapsed_ms(start: float) -> int:
    """Millisekunden seit `start` (Wert von perf_counter())."""
    return round((perf_counter() - start) * 1000)


class RunLog:
    def __init__(self, folder: Path):
        folder.mkdir(exist_ok=True)
        self.run_id = uuid4().hex
        self.path = folder / f"{self.run_id}.jsonl"
        self.model = None      # beide werden gesetzt, sobald die Konfiguration gelesen ist
        self.condition = None  # preview oder direct

    def write(self, event, *, tool=None, args=None, ok=True, duration_ms=0, **extra):
        """Schreibt eine Zeile. Die Pflichtfelder stehen immer drin, `extra` kommt dazu."""
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "run_id": self.run_id,
            "event": event,  # user_task, tool_call, tool_result, final, error,
                             # approval_request, approval_granted, approval_denied
            "tool": tool,
            "args": args,
            "ok": ok,
            "model": self.model,
            "duration_ms": duration_ms,
            "condition": self.condition,
            **extra,
        }
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(entry, ensure_ascii=False) + "\n")
