"""Einstiegspunkt: python -m agent "Was steht am 29.10.2026 im Kalender?" """

import argparse
import sys

from .config import ConfigError, load_config
from .log import LOG_DIR, RunLog
from .loop import StepLimitReached, run_agent


def fail(log: RunLog, error: Exception | str, **fields) -> int:
    """Letzter Logeintrag bei einem Fehler, Meldung auf stderr, Exitcode 1."""
    log.write("error", ok=False, message=str(error), **fields)
    print(f"Fehler: {error}", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Fragen zu Kalender, Wetter und Zügen.")
    parser.add_argument("task", help="die Frage in Anführungszeichen")
    task = parser.parse_args().task

    log = RunLog(LOG_DIR)
    try:
        config = load_config()
        log.model = config.model
        log.condition = config.condition
        log.write("user_task", task=task)
        answer = run_agent(task, config, log)
    except ConfigError as error:
        return fail(log, error, reason="config")
    except StepLimitReached as error:
        return fail(log, error, reason="step_limit", step=error.step)
    except KeyboardInterrupt:
        # Strg+C, z. B. während der Rückfrage – auch dann bekommt das Log einen Abschluss.
        return fail(log, "Abgebrochen mit Strg+C.", reason="interrupted")
    except Exception as error:
        # Unerwarteter Fehler: Auch dann soll das Log zeigen, wie der Lauf endete.
        return fail(log, error, reason="unexpected")

    print(answer)
    return 0


if __name__ == "__main__":
    sys.exit(main())
