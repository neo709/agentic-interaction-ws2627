# Agentic Interaction – WS 2026/27

Ein Agent, der Fragen zu **Terminen, Wetter und Zugverbindungen** beantwortet.
Das Sprachmodell entscheidet selbst, welche Werkzeuge es braucht; die Daten kommen
aus den [Mock-Daten](https://github.com/jhbelz/agentic-interaction-data) des Kurses.

```text
$ python -m agent "Wie komme ich am 29.10.2026 nach München, und brauche ich einen Regenschirm?"

Von Ulm nach München fährt um 07:12 der ICE 594 (an 08:31) …
In München gibt es Schauer bei 60 % Regenwahrscheinlichkeit – nimm einen Schirm mit.
```

## Einrichten

Python 3.11 oder neuer:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # danach eigenen OPENAI_API_KEY eintragen
```

| Variable | Bedeutung |
| --- | --- |
| `OPENAI_BASE_URL` | Modell-Endpunkt, z. B. Groq `https://api.groq.com/openai/v1` |
| `MODEL` | Modellname, z. B. `openai/gpt-oss-20b` |
| `OPENAI_API_KEY` | eigener Schlüssel – nie committen |
| `DATA_BASE_URL` | `https://jhbelz.github.io/agentic-interaction-data/v1` |
| `MAX_STEPS` | optional, höchstens so viele Modellaufrufe pro Lauf (Standard 10) |

Umgebungsvariablen haben Vorrang vor `.env`. Statt Groq geht jeder OpenAI-kompatible
Endpunkt, z. B. OpenRouter: `cp .env.openrouter.example .env`.

## Starten

```bash
python -m agent "Was steht am 29.10.2026 im Kalender?"
```

Die Antwort kommt auf die Standardausgabe (Exitcode `0`), ein Fehler auf die
Standardfehlerausgabe (Exitcode `1`).

**In VS Code:** Ordner öffnen, links *Run and Debug*, Startpunkt wählen (z. B.
„Blatt 4: München + Regenschirm“), **F5**. Ein Haltepunkt in `agent/loop.py`
zeigt, was das Modell in jedem Schritt tut.

## So funktioniert es

```text
Frage ─▶ Modell ─▶ ruft es Werkzeuge auf?
           ▲         ├─ ja   ─▶ Werkzeuge ausführen ─┐
           │         └─ nein ─▶ Antwort, fertig      │
           └────── Ergebnisse in den Verlauf ◀───────┘
```

1. Das Modell bekommt die Frage und die Beschreibungen der Werkzeuge.
2. Will es Werkzeuge aufrufen, führt der Agent sie aus und gibt die Ergebnisse zurück.
3. Das wiederholt sich, bis das Modell antwortet – höchstens `MAX_STEPS`-mal.
   Danach endet der Lauf als Fehler.
4. Geht unterwegs etwas schief (falsches Datum, Server nicht erreichbar), bekommt das
   Modell den Fehler als Ergebnis und kann es noch einmal versuchen.

| Werkzeug | Parameter | liest |
| --- | --- | --- |
| `calendar` | `date` | `calendar/{date}.json` |
| `weather` | `city`, `date` | `weather/{city}/{date}.json` |
| `connections` | `from_city`, `to_city`, `date` | `transit/{from}/{to}/{date}.json` |
| `context` | – | `context.json` (Wohnort, aktuelles Datum) |

**Nichts erfinden:** Gibt es für einen Ort oder Tag keine Daten (HTTP 404), liefert das
Werkzeug `{"no_data": true}` und das Modell sagt das so. Im ersten Schritt *muss*
das Modell ein Werkzeug aufrufen – ohne Daten kann es also gar nicht antworten.

| Datei | Aufgabe |
| --- | --- |
| `agent/__main__.py` | Frage lesen, Lauf starten, Exitcode |
| `agent/config.py` | `.env` und Umgebungsvariablen lesen |
| `agent/loop.py` | die Schleife aus dem Bild oben |
| `agent/tools.py` | die Werkzeuge |
| `agent/log.py` | das Protokoll |

## Protokoll

Jeder Lauf schreibt `logs/<run_id>.jsonl`, eine Zeile pro Ereignis mit den Feldern
`ts`, `run_id`, `event`, `tool`, `args`, `ok`, `model`, `duration_ms`
(dazu z. B. `step`, `result`, `answer`, `reason`).

| `event` | wann |
| --- | --- |
| `user_task` | Frage kommt rein |
| `tool_call` / `tool_result` | Werkzeug aufgerufen / Ergebnis (`ok: false` bei Fehler) |
| `final` | Antwort – Lauf erfolgreich |
| `error` | Fehler; als letzter Eintrag mit `reason` (z. B. `step_limit`) – Lauf gescheitert |

## Testen

```bash
python -m unittest discover -s tests -v     # ohne Netz und ohne API-Schlüssel
```

Von Hand, danach jeweils das neueste Log in `logs/` ansehen:

```bash
python -m agent "Was steht am 29.10.2026 und am 30.10.2026 im Kalender?"   # mehrere Schritte
python -m agent "Was steht am 01.12.2026 im Kalender?"                     # Tag ohne Daten
python -m agent "Wie ist das Wetter am 29.10.2026 in Berlin?"              # Ort ohne Daten
MAX_STEPS=1 python -m agent "Was steht am 29.10.2026 und am 30.10.2026 an?"  # Schrittlimit → Exitcode 1
```

## Abgabe

Öffentliches Repo `agentic-interaction-ws2627`, eingereicht als
`https://github.com/neo709/agentic-interaction-ws2627.git`. `.env`, `.venv/` und
`logs/` sind in `.gitignore`. Die Stände der Übungen sind als Tags gesichert
(`uebung-1`, `uebung-3`); `DELEGATION.md` enthält Übung 2.
