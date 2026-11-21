"""Die Werkzeuge des Agenten.

Jedes Werkzeug besteht aus zwei Teilen:
  1. einer Beschreibung (JSON-Schema), die das Modell sieht – TOOL_SCHEMAS
  2. einer Python-Funktion, die wir ausführen, wenn das Modell sie aufruft – TOOL_FUNCTIONS
"""

import json
import re
from datetime import date as Date
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


class ToolError(Exception):
    """Fehler bei einem Werkzeugaufruf. Das Modell bekommt ihn als Ergebnis zurück."""


# --- Daten holen -------------------------------------------------------------

def fetch_json(base_url: str, path: str):
    """Lädt {base_url}/{path}. Gibt None zurück, wenn es keine Daten gibt (HTTP 404)."""
    url = f"{base_url.rstrip('/')}/{path}"
    try:
        with urlopen(url, timeout=20) as response:
            return json.load(response)
    except HTTPError as error:
        if error.code == 404:
            return None
        raise ToolError(f"Datenabruf fehlgeschlagen: HTTP {error.code}.") from None
    except URLError:
        raise ToolError("Der Datenserver ist nicht erreichbar.") from None


def no_data(what: str) -> dict:
    # Eigenes Ergebnis statt Fehler: Das Modell soll sagen, dass nichts da ist – nicht raten.
    return {"no_data": True, "message": f"Keine Daten für {what} vorhanden."}


# --- Eingaben prüfen, bevor sie in eine URL kommen ---------------------------

def check_date(value) -> str:
    try:
        if Date.fromisoformat(value).isoformat() == value:
            return value
    except (TypeError, ValueError):
        pass
    raise ToolError(f"Ungültiges Datum {value!r}, erwartet wird YYYY-MM-DD.")


def check_city(value) -> str:
    if isinstance(value, str) and re.fullmatch(r"[a-z]+", value):
        return value
    raise ToolError(f"Ungültiges Stadtkürzel {value!r}, erwartet z. B. 'ulm' oder 'muenchen'.")


# --- Die Werkzeuge -----------------------------------------------------------

def calendar(base_url: str, date: str) -> dict:
    date = check_date(date)
    data = fetch_json(base_url, f"calendar/{date}.json")
    return data if data is not None else no_data(f"den Kalender am {date}")


def weather(base_url: str, city: str, date: str) -> dict:
    city, date = check_city(city), check_date(date)
    data = fetch_json(base_url, f"weather/{city}/{date}.json")
    return data if data is not None else no_data(f"das Wetter in {city} am {date}")


def connections(base_url: str, from_city: str, to_city: str, date: str) -> dict:
    from_city, to_city, date = check_city(from_city), check_city(to_city), check_date(date)
    data = fetch_json(base_url, f"transit/{from_city}/{to_city}/{date}.json")
    return data if data is not None else no_data(f"Verbindungen {from_city} → {to_city} am {date}")


def context(base_url: str) -> dict:
    data = fetch_json(base_url, "context.json")
    return data if data is not None else no_data("den Kontext")


TOOL_FUNCTIONS = {
    "calendar": calendar,
    "weather": weather,
    "connections": connections,
    "context": context,
}


# --- Beschreibungen für das Modell -------------------------------------------

def describe(name: str, description: str, **parameters) -> dict:
    """Baut die Werkzeugbeschreibung im Format der Chat-Completions-API."""
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": list(parameters),
                "additionalProperties": False,
            },
        },
    }


DATE = {"type": "string", "description": "Datum im Format YYYY-MM-DD"}
CITY = {"type": "string", "description": "Stadtname klein und ohne Umlaute, z. B. ulm, "
        "muenchen. Jede Stadt ist erlaubt; ohne Daten kommt no_data zurück."}

TOOL_SCHEMAS = [
    describe("calendar", "Liest alle Termine eines Tages aus dem Kalender.",
             date=DATE),
    describe("weather", "Liest die Wettervorhersage für eine Stadt an einem Tag "
             "(Temperatur, Wetterlage, Regenwahrscheinlichkeit, Wind).",
             city=CITY, date=DATE),
    describe("connections", "Sucht Zugverbindungen zwischen zwei Städten an einem Tag "
             "(Abfahrt, Ankunft, Zug, Umstiege, Preis).",
             from_city=CITY, to_city=CITY, date=DATE),
    describe("context", "Liest die aktuelle Situation der Nutzerin oder des Nutzers: "
             "jetziger Zeitpunkt (now), Wohnort (home) und Hinweise. Nutzen, wenn in der "
             "Frage Startort oder Datum fehlen, z. B. bei 'heute' oder 'nach München'."),
]


# --- Einen Aufruf des Modells ausführen --------------------------------------

def parse_arguments(raw: str):
    """Argumente des Modells als dict – oder der Originaltext, wenn es kein JSON ist."""
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return raw


def run_tool(name: str, args, base_url: str) -> tuple[dict, bool]:
    """Führt ein Werkzeug aus und gibt (Ergebnis, ok) zurück.

    Fehler werden nicht weitergeworfen, sondern als Ergebnis zurückgegeben:
    So sieht das Modell, was schiefging, und kann den Aufruf korrigieren.
    """
    function = TOOL_FUNCTIONS.get(name)
    if function is None:
        return {"error": f"Unbekanntes Werkzeug: {name}"}, False
    if not isinstance(args, dict):
        return {"error": "Die Argumente müssen ein JSON-Objekt sein."}, False
    try:
        return function(base_url, **args), True
    except TypeError:
        return {"error": f"Falsche Parameter für {name}: {sorted(args)}"}, False
    except ToolError as error:
        return {"error": str(error)}, False
