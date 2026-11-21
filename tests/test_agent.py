"""Tests für einen ganzen Lauf – Modell und Datenserver werden simuliert."""

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from openai import APIConnectionError
from openai.types.chat import ChatCompletionMessage

from agent import __main__ as main_module
from agent import config, loop, tools


def wants_tools(*calls):
    """Antwort des Modells mit Werkzeugaufrufen, z. B. ("calendar", {"date": "…"})."""
    return ChatCompletionMessage.model_validate({
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {"id": f"call_{i}", "type": "function",
             "function": {"name": name, "arguments": json.dumps(args)}}
            for i, (name, args) in enumerate(calls)
        ],
    })


def answers(text):
    """Abschließende Antwort des Modells."""
    return ChatCompletionMessage(role="assistant", content=text)


def fake_data(base_url, path):
    """Simulierter Datenserver: nur diese Pfade gibt es, alles andere ist 404 (None)."""
    return {
        "calendar/2026-10-29.json": {"date": "2026-10-29", "events": [{"title": "Standup"}]},
        "calendar/2026-10-30.json": {"date": "2026-10-30", "events": []},
        "weather/muenchen/2026-10-29.json": {"condition": "Schauer", "rain_probability": 0.6},
        "transit/ulm/muenchen/2026-10-29.json": {"connections": [{"train": "ICE 594"}]},
    }.get(path)


class AgentRunTests(unittest.TestCase):
    def run_agent(self, model_replies, env=None):
        environment = {
            "OPENAI_BASE_URL": "http://model.invalid/v1",
            "MODEL": "test-model",
            "OPENAI_API_KEY": "test-key",
            "DATA_BASE_URL": "http://data.invalid/v1",
            "MAX_STEPS": "10",
            **(env or {}),
        }
        with tempfile.TemporaryDirectory() as folder:
            stdout, stderr = io.StringIO(), io.StringIO()
            with (
                patch.dict(os.environ, environment, clear=True),
                patch.object(config, "ENV_FILE", Path(folder) / "keine.env"),
                patch.object(main_module, "LOG_DIR", Path(folder)),
                patch.object(loop, "call_model", side_effect=model_replies) as model,
                patch.object(tools, "fetch_json", side_effect=fake_data),
                patch("sys.argv", ["agent", "Testfrage"]),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                exit_code = main_module.main()
            log_file, = Path(folder).glob("*.jsonl")
            log = [json.loads(line) for line in log_file.read_text().splitlines()]
        self.model = model
        return exit_code, stdout.getvalue().strip(), stderr.getvalue(), log

    def results(self, log):
        return [entry for entry in log if entry["event"] == "tool_result"]

    # --- Übung 1: ein Werkzeugaufruf ---------------------------------------

    def test_single_day(self):
        code, out, err, log = self.run_agent([
            wants_tools(("calendar", {"date": "2026-10-29"})),
            answers("Am 29.10. ist Standup."),
        ])
        self.assertEqual((code, out, err), (0, "Am 29.10. ist Standup.", ""))
        self.assertEqual([e["event"] for e in log],
                         ["user_task", "tool_call", "tool_result", "final"])
        self.assertEqual(log[2]["result"]["events"], [{"title": "Standup"}])
        self.assertTrue(all(e["model"] == "test-model" for e in log))
        # Erst muss ein Werkzeug aufgerufen werden, danach darf das Modell antworten.
        self.assertEqual([c.kwargs["force_tool"] for c in self.model.call_args_list],
                         [True, False])

    # --- Übung 3: mehrere Schritte, Ende, Fehler unterwegs ------------------

    def test_two_days_in_two_steps(self):
        code, out, _, log = self.run_agent([
            wants_tools(("calendar", {"date": "2026-10-29"})),
            wants_tools(("calendar", {"date": "2026-10-30"})),
            answers("Beide Tage"),
        ], env={"MAX_STEPS": "3"})
        self.assertEqual(code, 0)
        self.assertEqual(log[-1]["event"], "final")
        self.assertEqual(log[-1]["step"], 3)
        # Das Modell bekommt im letzten Schritt beide Ergebnisse im Verlauf.
        history = self.model.call_args.args[2]
        self.assertEqual(len([m for m in history if m["role"] == "tool"]), 2)

    def test_step_limit_is_an_error(self):
        code, out, err, log = self.run_agent([
            wants_tools(("calendar", {"date": "2026-10-29"})),
        ], env={"MAX_STEPS": "1"})
        self.assertEqual((code, out), (1, ""))
        self.assertIn("Schrittlimit", err)
        self.assertEqual(log[-1]["event"], "error")
        self.assertEqual(log[-1]["reason"], "step_limit")
        self.assertFalse(log[-1]["ok"])

    def test_tool_error_lets_model_correct_itself(self):
        code, _, _, log = self.run_agent([
            wants_tools(("calendar", {"date": "29.10.2026"})),   # falsches Format
            wants_tools(("calendar", {"date": "2026-10-29"})),
            answers("Korrigiert"),
        ])
        self.assertEqual(code, 0)
        self.assertEqual([e["ok"] for e in self.results(log)], [False, True])

    def test_model_error_costs_one_step_and_run_continues(self):
        code, _, _, log = self.run_agent([
            APIConnectionError(request=None),
            wants_tools(("calendar", {"date": "2026-10-29"})),
            answers("Trotzdem fertig"),
        ])
        self.assertEqual(code, 0)
        self.assertEqual((log[1]["event"], log[1]["stage"], log[1]["step"]), ("error", "model", 1))
        self.assertEqual(log[-1]["step"], 3)

    def test_missing_config_ends_as_error(self):
        code, _, err, log = self.run_agent([], env={"OPENAI_API_KEY": ""})
        self.assertEqual(code, 1)
        self.assertIn("OPENAI_API_KEY", err)
        self.assertEqual(log[-1]["reason"], "config")

    # --- Übung 4: zwei neue Werkzeuge, Lücken -------------------------------

    def test_weather_and_connections_in_one_run(self):
        code, out, _, log = self.run_agent([
            wants_tools(("connections", {"from_city": "ulm", "to_city": "muenchen",
                                         "date": "2026-10-29"}),
                        ("weather", {"city": "muenchen", "date": "2026-10-29"})),
            answers("ICE 594, Schirm mitnehmen"),
        ])
        self.assertEqual(code, 0)
        self.assertEqual([e["tool"] for e in self.results(log)], ["connections", "weather"])
        self.assertTrue(all(e["ok"] for e in self.results(log)))

    def test_place_without_data_returns_no_data(self):
        code, _, _, log = self.run_agent([
            wants_tools(("weather", {"city": "berlin", "date": "2026-10-29"})),
            answers("Für Berlin gibt es keine Wetterdaten."),
        ])
        self.assertEqual(code, 0)
        self.assertTrue(self.results(log)[0]["result"]["no_data"])


if __name__ == "__main__":
    unittest.main()
