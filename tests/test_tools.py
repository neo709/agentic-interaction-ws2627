"""Tests für die Werkzeuge – ohne Netzwerk, fetch_json wird ersetzt."""

import unittest
from unittest.mock import patch

from agent import tools

BASE = "http://data.invalid/v1"


class ToolTests(unittest.TestCase):
    def test_calendar_builds_url(self):
        with patch.object(tools, "fetch_json", return_value={"events": []}) as fetch:
            result, ok = tools.run_tool("calendar", {"date": "2026-10-29"}, BASE)
        fetch.assert_called_once_with(BASE, "calendar/2026-10-29.json")
        self.assertEqual((result, ok), ({"events": []}, True))

    def test_weather_and_connections_build_urls(self):
        with patch.object(tools, "fetch_json", return_value={}) as fetch:
            tools.run_tool("weather", {"city": "muenchen", "date": "2026-10-29"}, BASE)
            tools.run_tool("connections", {"from_city": "ulm", "to_city": "muenchen",
                                           "date": "2026-10-29"}, BASE)
        self.assertEqual([call.args[1] for call in fetch.call_args_list],
                         ["weather/muenchen/2026-10-29.json",
                          "transit/ulm/muenchen/2026-10-29.json"])

    def test_missing_data_is_a_result_not_an_error(self):
        with patch.object(tools, "fetch_json", return_value=None):
            result, ok = tools.run_tool("weather", {"city": "berlin", "date": "2026-10-29"}, BASE)
        self.assertTrue(ok)
        self.assertTrue(result["no_data"])

    def test_invalid_inputs_become_error_results(self):
        cases = [
            ("calendar", {"date": "29.10.2026"}),           # falsches Datumsformat
            ("weather", {"city": "../x", "date": "2026-10-29"}),  # unsicheres Stadtkürzel
            ("calendar", {"day": "2026-10-29"}),            # falscher Parametername
            ("calendar", '{"date":'),                       # kaputtes JSON
            ("flights", {"date": "2026-10-29"}),            # unbekanntes Werkzeug
        ]
        with patch.object(tools, "fetch_json") as fetch:
            for name, args in cases:
                with self.subTest(name=name, args=args):
                    result, ok = tools.run_tool(name, args, BASE)
                    self.assertFalse(ok)
                    self.assertIn("error", result)
        fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
