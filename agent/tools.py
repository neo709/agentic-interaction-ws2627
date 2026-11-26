"""Die Werkzeuge des Agenten.

Jedes Werkzeug besteht aus zwei Teilen:
  1. einer Beschreibung (JSON-Schema), die das Modell sieht – TOOL_SCHEMAS
  2. einer Python-Funktion, die wir ausführen, wenn das Modell sie aufruft – TOOL_FUNCTIONS
"""

import json
import re
from datetime import date as Date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from uuid import uuid4

# Hierhin schreibt create_event. Die Mock-Daten auf dem Server bleiben unverändert.
EVENTS_FILE = Path(__file__).resolve().parent.parent / "var" / "calendar.jsonl"


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


def check_time(value) -> str:
    if isinstance(value, str) and re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", value):
        return value
    raise ToolError(f"Ungültige Uhrzeit {value!r}, erwartet wird HH:MM.")


# --- Die Werkzeuge -----------------------------------------------------------

def calendar(base_url: str, date: str) -> dict:
    date = check_date(date)
    data = fetch_json(base_url, f"calendar/{date}.json")
    return data if data is not None else no_data(f"den Kalender am {date}")


def unknown_city(base_url: str, *cities: str):
    """Prüft die Städte gegen die Liste in index.json.

    Kennt die Datenquelle eine Stadt nicht (z. B. 'munich' statt 'muenchen' oder 'berlin'),
    kommt no_data mit der Liste der bekannten Städte zurück – damit kann sich das Modell
    selbst korrigieren. Sonst None.
    """
    index = fetch_json(base_url, "index.json") or {}
    known = index.get("cities")  # z. B. {"ulm": "Ulm", "muenchen": "München"}
    if not known:
        return None  # keine Liste verfügbar → nicht prüfen
    for city in cities:
        if city not in known:
            return {"no_data": True, "message": f"Keine Daten für die Stadt {city!r}.",
                    "known_cities": known}
    return None


def weather(base_url: str, city: str, date: str) -> dict:
    city, date = check_city(city), check_date(date)
    if missing := unknown_city(base_url, city):
        return missing
    data = fetch_json(base_url, f"weather/{city}/{date}.json")
    return data if data is not None else no_data(f"das Wetter in {city} am {date}")


def connections(base_url: str, from_city: str, to_city: str, date: str) -> dict:
    from_city, to_city, date = check_city(from_city), check_city(to_city), check_date(date)
    if missing := unknown_city(base_url, from_city, to_city):
        return missing
    data = fetch_json(base_url, f"transit/{from_city}/{to_city}/{date}.json")
    return data if data is not None else no_data(f"Verbindungen {from_city} → {to_city} am {date}")


def context(base_url: str) -> dict:
    data = fetch_json(base_url, "context.json")
    return data if data is not None else no_data("den Kontext")


def create_event(base_url: str, date: str, start: str, end: str, title: str) -> dict:
    """Legt einen Termin an: eine JSON-Zeile in var/calendar.jsonl (base_url wird nicht gebraucht)."""
    date, start, end = check_date(date), check_time(start), check_time(end)
    if end <= start:
        raise ToolError("Das Ende muss nach dem Beginn liegen.")
    if not isinstance(title, str) or not title.strip():
        raise ToolError("Der Titel darf nicht leer sein.")

    # Gleiche Felder wie die Termine in den Mock-Daten.
    event = {"id": f"local-{uuid4().hex[:8]}", "date": date, "start": start, "end": end,
             "all_day": False, "title": title.strip(), "location": None}
    EVENTS_FILE.parent.mkdir(exist_ok=True)
    with EVENTS_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=False) + "\n")
    return {"created": True, "event": event}


TOOL_FUNCTIONS = {
    "calendar": calendar,
    "weather": weather,
    "connections": connections,
    "context": context,
    "create_event": create_event,
}

# Die einzige Stelle, die festlegt, welche Werkzeuge etwas Unumkehrbares tun.
# Nur für diese Werkzeuge fragt der Agent in CONDITION=preview um Erlaubnis.
IRREVERSIBLE_TOOLS = {"create_event"}


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
TIME = {"type": "string", "description": "Uhrzeit im Format HH:MM"}
CITY = {"type": "string", "description": "Stadtkürzel wie in den Daten: deutscher Name, "
        "klein, Umlaute als ae/oe/ue – z. B. ulm, muenchen. Bei unbekannter Stadt kommt "
        "no_data mit der Liste known_cities zurück."}

TOOL_SCHEMAS = [
    describe("calendar", "Liest alle Termine eines Tages aus dem Kalender.",
             date=DATE),
    describe("weather", "Liest die Wettervorhersage für eine Stadt an einem Tag "
             "(Temperatur, Wetterlage, Regenwahrscheinlichkeit, Wind).",
             city=CITY, date=DATE),
    describe("connections", "Sucht Zugverbindungen zwischen zwei Städten an einem Tag "
             "(Abfahrt, Ankunft, Zug, Umstiege, Preis).",
             from_city=CITY, to_city=CITY, date=DATE),
    describe("create_event", "Legt einen neuen Termin im Kalender an.",
             date=DATE, start=TIME, end=TIME,
             title={"type": "string", "description": "Titel des Termins"}),
    describe("context", "Liest die aktuelle Situation der Nutzerin oder des Nutzers: "
             "jetziger Zeitpunkt (now), Wohnort (home) und Hinweise. Nutzen, wenn in der "
             "Frage Startort oder Datum fehlen, z. B. bei 'heute' oder 'nach München'."),
]

# Parameter je Werkzeug in der Reihenfolge der Beschreibung, z. B. date, start, end, title.
# Damit zeigt der Freigabedialog die Argumente lesbar an, egal in welcher Reihenfolge
# das Modell sie schickt.
PARAMETER_ORDER = {schema["function"]["name"]: list(schema["function"]["parameters"]["properties"])
                   for schema in TOOL_SCHEMAS}


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
