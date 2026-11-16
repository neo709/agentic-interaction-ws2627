import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from agent import __main__ as agent


def tool_call(day, call_id="call_1"):
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": call_id,
            "type": "function",
            "function": {"name": "calendar", "arguments": json.dumps({"date": day})},
        }],
    }


class AgentTests(unittest.TestCase):
    def run_agent(self, responses, max_steps=10, calendar=None):
        # Die Tests laufen ohne Netzwerk, Zugangsdaten oder Änderungen an echten Logs.
        with tempfile.TemporaryDirectory() as folder:
            stdout, stderr = io.StringIO(), io.StringIO()
            config = {
                "OPENAI_BASE_URL": "http://test.invalid/v1",
                "MODEL": "test-model",
                "OPENAI_API_KEY": "test-key",
                "DATA_BASE_URL": "http://data.invalid/v1",
                "MAX_STEPS": str(max_steps),
            }
            with (
                patch.object(agent, "ROOT", Path(folder)),
                patch.dict(os.environ, config, clear=True),
                patch("sys.argv", ["agent", "Kalenderfrage"]),
                patch.object(agent, "call_model", side_effect=responses) as model,
                patch.object(agent, "read_calendar", side_effect=calendar or (
                    lambda base, day: {"date": day, "events": []}
                )) as reader,
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                exit_code = agent.main()
            paths = list((Path(folder) / "logs").glob("*.jsonl"))
            self.assertEqual(len(paths), 1)
            entries = [json.loads(line) for line in paths[0].read_text().splitlines()]
            return exit_code, stdout.getvalue(), stderr.getvalue(), entries, model, reader

    def test_single_day_still_works(self):
        result = self.run_agent([
            tool_call("2026-10-29"),
            {"role": "assistant", "content": "Antwort zum Tag"},
        ])
        code, stdout, stderr, entries, model, reader = result
        self.assertEqual((code, stdout.strip(), stderr), (0, "Antwort zum Tag", ""))
        self.assertEqual(model.call_count, 2)
        reader.assert_called_once_with("http://data.invalid/v1", "2026-10-29")
        self.assertEqual(entries[-1]["event"], "final")

    def test_multiple_days_finish_on_last_allowed_step(self):
        result = self.run_agent([
            tool_call("2026-10-29"),
            tool_call("2026-10-30", "call_2"),
            {"role": "assistant", "content": "Antwort zu beiden Tagen"},
        ], max_steps=3)
        code, stdout, stderr, entries, model, reader = result
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(model.call_count, 3)
        self.assertEqual([call.args[1] for call in reader.call_args_list],
                         ["2026-10-29", "2026-10-30"])
        self.assertEqual(entries[-1]["event"], "final")
        self.assertEqual(entries[-1]["step"], 3)
        messages = model.call_args.args[1]
        results = [json.loads(message["content"]) for message in messages
                   if message["role"] == "tool"]
        self.assertEqual([result["date"] for result in results],
                         ["2026-10-29", "2026-10-30"])

    def test_step_limit_is_an_error(self):
        result = self.run_agent([
            tool_call("2026-10-29"), tool_call("2026-10-30", "call_2")
        ], max_steps=2)
        code, stdout, stderr, entries, model, reader = result
        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("Schrittlimit", stderr)
        self.assertEqual(model.call_count, 2)
        self.assertEqual(entries[-1]["event"], "error")
        self.assertEqual(entries[-1]["reason"], "step_limit")
        self.assertFalse(entries[-1]["ok"])
        self.assertNotIn("final", [entry["event"] for entry in entries])

    def test_tool_error_can_be_followed_by_success(self):
        result = self.run_agent([
            tool_call("2026-10-29"),
            tool_call("2026-10-29", "call_2"),
            {"role": "assistant", "content": "Abruf erfolgreich wiederholt"},
        ], calendar=[RuntimeError("Vorübergehend nicht erreichbar"),
                     {"date": "2026-10-29", "events": []}])
        code, stdout, stderr, entries, model, reader = result
        self.assertEqual(code, 0)
        self.assertEqual(model.call_count, 3)
        results = [entry for entry in entries if entry["event"] == "tool_result"]
        self.assertEqual([entry["ok"] for entry in results], [False, True])
        messages = model.call_args.args[1]
        error = next(json.loads(message["content"]) for message in messages
                     if message["role"] == "tool")
        self.assertIn("Vorübergehend", error["error"])
        self.assertEqual(entries[-1]["event"], "final")

    def test_invalid_arguments_can_be_corrected(self):
        invalid = tool_call("2026-10-29")
        invalid["tool_calls"][0]["function"]["arguments"] = '{"date":'
        result = self.run_agent([
            invalid, tool_call("2026-10-29", "call_2"),
            {"role": "assistant", "content": "Korrigierter Abruf"},
        ])
        code, stdout, stderr, entries, model, reader = result
        self.assertEqual(code, 0)
        self.assertEqual(reader.call_count, 1)
        results = [entry for entry in entries if entry["event"] == "tool_result"]
        self.assertEqual([entry["ok"] for entry in results], [False, True])
        self.assertEqual(entries[-1]["event"], "final")

    def test_model_error_consumes_one_step_and_can_recover(self):
        result = self.run_agent([
            RuntimeError("Vorübergehender Modellfehler"), tool_call("2026-10-29"),
            {"role": "assistant", "content": "Antwort nach erneutem Versuch"},
        ], max_steps=3)
        code, stdout, stderr, entries, model, reader = result
        self.assertEqual(code, 0)
        self.assertEqual(model.call_count, 3)
        self.assertEqual(entries[1]["event"], "error")
        self.assertEqual(entries[1]["stage"], "model")
        self.assertEqual(entries[1]["step"], 1)
        self.assertEqual(entries[-1]["event"], "final")
        self.assertEqual(entries[-1]["step"], 3)

    def test_missing_data_does_not_prevent_other_days(self):
        result = self.run_agent([
            tool_call("2026-12-01"), tool_call("2026-10-29", "call_2"),
            {"role": "assistant", "content": "Fehlende Daten und anderer Tag"},
        ], calendar=[{"date": "2026-12-01", "no_data": True},
                     {"date": "2026-10-29", "events": []}])
        code, stdout, stderr, entries, model, reader = result
        self.assertEqual(code, 0)
        self.assertEqual(reader.call_count, 2)
        self.assertEqual(entries[-1]["event"], "final")


if __name__ == "__main__":
    unittest.main()
