# Agentic Interaction – Wintersemester 2026/27

## Übung 1: Kalenderabfrage

Der Agent beantwortet Fragen zu einem Kalendertag. Das Modell bestimmt das Datum
für das Werkzeug `calendar`. Dieses lädt die Termine per HTTP. Anschließend
formuliert das Modell aus dem Ergebnis die Antwort.

### Einrichtung

Python **3.11 oder neuer** verwenden. Im Projektordner:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

In `.env` den eigenen API-Schlüssel bei `OPENAI_API_KEY` eintragen. Die Vorlage
verwendet den OpenAI-kompatiblen Groq-Endpunkt mit `openai/gpt-oss-20b`.
`OPENAI_BASE_URL`, `MODEL`, `OPENAI_API_KEY` und `DATA_BASE_URL` werden beim Start
eingelesen. Bereits gesetzte Umgebungsvariablen haben Vorrang vor `.env`.
Ein anderer OpenAI-kompatibler Endpunkt kann über diese Werte eingestellt werden.

### Ausführen

```bash
python -m agent "Was steht am 29.10.2026 im Kalender?"
```

Ein Aufruf fragt genau einen Tag ab. Die Antwort erscheint auf der Standardausgabe.
Erfolgreiche Läufe enden mit Exitcode `0`, Fehler mit Exitcode `1` und einer Meldung
auf der Standardfehlerausgabe. Mehrere Tage in einem Lauf folgen in Übung 3.

Die Mock-Daten umfassen den 26.10. bis 08.11.2026. Ein Tag mit leerer Terminliste
ist frei. HTTP 404 bedeutet dagegen, dass für den Tag keine Daten vorliegen.
Die Termine werden vom Datenserver abgerufen und nicht im Code hinterlegt.

### Ablauf und Protokoll

Die Umsetzung steht in `agent/__main__.py`:

1. `main()` liest Aufgabe und Konfiguration ein und beginnt das Protokoll.
2. `call_model()` übermittelt Aufgabe und Werkzeugbeschreibung. Der erste Aufruf
   fordert das Kalender-Tool an; das Modell liefert dessen Datumsargument.
3. `read_calendar()` prüft das Datum und lädt die Kalenderdatei.
4. Der zweite Modellaufruf erhält das Werkzeugergebnis und liefert die Antwort.

Jeder Lauf erzeugt eine eigene Datei `logs/<run_id>.jsonl`. Jede Zeile ist ein
JSON-Objekt mit `ts`, `run_id`, `event`, `tool`, `args`, `ok`, `model` und
`duration_ms`. Je nach Ereignis kommen `task`, `result`, `answer` oder `message`
hinzu. Die Ereignisse heißen `user_task`, `tool_call`, `tool_result`, `final` und
`error`. `duration_ms` misst beim `tool_call` den ersten Modellaufruf, beim
`tool_result` den Kalenderabruf und bei `final` den zweiten Modellaufruf.

### Selbst prüfen

```bash
python -m agent "Was steht am 29.10.2026 im Kalender?"
python -m agent "Was steht am 01.11.2026 im Kalender?"
python -m agent "Was steht am 01.12.2026 im Kalender?"
```

Danach die jeweilige Logdatei prüfen: Das Modell muss `calendar` mit dem richtigen
Datum aufgerufen haben. Die Antwort muss dem `tool_result` entsprechen. Der letzte
Eintrag ist bei Erfolg `final`, bei einem Fehler `error` mit `ok: false`.

### Repository und Abgabe

Das öffentliche GitHub-Repository muss `agentic-interaction-ws2627` heißen. In
Moodle wird der HTTPS-Link mit `.git` am Ende eingereicht, also
`https://github.com/<benutzername>/agentic-interaction-ws2627.git`.
Bewertet wird der rechtzeitig gepushte
Stand. `.env`, `.venv/` und `logs/` sind durch `.gitignore` ausgeschlossen.

Daten und Schnittstellenbeschreibung:
[agentic-interaction-data](https://github.com/jhbelz/agentic-interaction-data).
