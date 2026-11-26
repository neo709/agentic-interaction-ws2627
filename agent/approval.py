"""Freigabe: Plan zeigen und fragen (preview) oder ausführen und berichten (direct).

Alles hier geht auf stderr – auf stdout steht nur die Antwort des Agenten.
"""

import sys
from time import perf_counter

from .log import RunLog, elapsed_ms
from .tools import IRREVERSIBLE_TOOLS, PARAMETER_ORDER

# Ergebnis, das das Modell bei einer Ablehnung bekommt. Es plant damit weiter.
DENIED = {"denied": True, "message": "Nicht freigegeben – die Aktion wurde nicht ausgeführt."}


def describe_call(name: str, args) -> str:
    """z. B. create_event(date=2026-10-29, start=17:00, end=18:00, title=Puffer)"""
    if not isinstance(args, dict):
        return f"{name}({args})"
    order = PARAMETER_ORDER.get(name, [])
    keys = sorted(args, key=lambda key: order.index(key) if key in order else len(order))
    return f"{name}(" + ", ".join(f"{key}={args[key]}" for key in keys) + ")"


def say(text: str = "", end: str = "\n"):
    print(text, end=end, file=sys.stderr, flush=True)


def show_plan(step: int, calls: list):
    """preview: vor dem Ausführen zeigen, was das Modell vorhat."""
    say(f"\nPlan (Schritt {step}):")
    for number, (name, args) in enumerate(calls, 1):
        note = "   ← braucht deine Freigabe" if name in IRREVERSIBLE_TOOLS else ""
        say(f"  {number}. {describe_call(name, args)}{note}")


def report(step: int, done: list):
    """direct: nach dem Ausführen berichten, was passiert ist."""
    say(f"\nAusgeführt (Schritt {step}):")
    for number, (name, args, ok) in enumerate(done, 1):
        say(f"  {number}. {describe_call(name, args)} → {'ok' if ok else 'fehlgeschlagen'}")


def ask_user(name: str, args) -> bool:
    """Ja nur bei j/ja/y/yes. Alles andere – auch keine Eingabe – ist ein Nein."""
    say(f"Soll ich {describe_call(name, args)} ausführen? [j/N] ", end="")
    reply = sys.stdin.readline()  # "" wenn keine Eingabe mehr kommt
    if not reply.endswith("\n"):
        say()  # Zeilenumbruch, falls keine Eingabe kam
    return reply.strip().lower() in ("j", "ja", "y", "yes")


def approve(name: str, args, step: int, auto_approve: bool, log: RunLog) -> bool:
    """Fragt eine unumkehrbare Aktion ab und protokolliert Frage und Entscheidung."""
    log.write("approval_request", tool=name, args=args, step=step)
    start = perf_counter()
    granted = True if auto_approve else ask_user(name, args)
    if auto_approve:
        say(f"Automatisch freigegeben (AUTO_APPROVE=1): {describe_call(name, args)}")
    log.write("approval_granted" if granted else "approval_denied", tool=name, args=args,
              step=step, auto=auto_approve, duration_ms=elapsed_ms(start))
    return granted
