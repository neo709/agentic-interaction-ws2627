# Agentic Interaction – Wintersemester 2026/27

## Kalenderagent – Übungen 1 und 3

Der Agent beantwortet Fragen zu einem oder mehreren Kalendertagen. Das Modell
bestimmt die Aufrufe des Werkzeugs `calendar`. Dieses lädt die Termine per HTTP.
Die Ergebnisse werden an das Modell zurückgegeben, bis es eine abschließende
Antwort liefert oder das Schrittlimit erreicht ist.

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
Optional begrenzt `MAX_STEPS` die Zahl der Modellaufrufe pro Lauf; ohne Angabe
gilt `10`. Der Wert muss eine positive ganze Zahl sein. Werkzeugaufrufe zählen
nicht zusätzlich als Modellschritte.

### Alternative: OpenRouter

Falls Groq nicht verfügbar ist, kann stattdessen OpenRouter verwendet werden:

```bash
cp .env.openrouter.example .env
```

Anschließend einen eigenen Schlüssel unter
[OpenRouter API Keys](https://openrouter.ai/settings/keys) erstellen und lokal in
`.env` bei `OPENAI_API_KEY` eintragen. Die Vorlage nutzt `openrouter/free`.
Dieser Router wählt kostenlose Modelle aus, die die angefragten Funktionen wie
Werkzeugaufrufe unterstützen. Das tatsächlich verwendete Modell kann wechseln.
Es gelten Nutzungslimits; jeder Modellschritt benötigt eine Anfrage.
Der Python-Code bleibt bei diesem Anbieterwechsel unverändert.

### Ausführen

```bash
python -m agent "Was steht am 29.10.2026 im Kalender?"
python -m agent "Was steht am 29.10.2026 und am 30.10.2026 im Kalender?"
```

Ein Programmaufruf bearbeitet die gesamte Frage. Die Antwort erscheint auf der Standardausgabe.
Erfolgreiche Läufe enden mit Exitcode `0`, Fehler mit Exitcode `1` und einer Meldung
auf der Standardfehlerausgabe. Auch das Erreichen des Schrittlimits ist ein Fehler.

Die Mock-Daten umfassen den 26.10. bis 08.11.2026. Ein Tag mit leerer Terminliste
ist frei. HTTP 404 bedeutet dagegen, dass für den Tag keine Daten vorliegen.
Die Termine werden vom Datenserver abgerufen und nicht im Code hinterlegt.

### Ablauf und Protokoll

Die Umsetzung steht in `agent/__main__.py`:

1. `main()` liest Aufgabe und Konfiguration ein und beginnt das Protokoll.
2. Pro Schleifendurchlauf übermittelt `call_model()` den bisherigen Gesprächsverlauf
   und die Werkzeugbeschreibung. Das Modell entscheidet über weitere Aufrufe oder
   eine abschließende Antwort.
3. Bei einem Werkzeugaufruf prüft `read_calendar()` das Datum und lädt die
   Kalenderdatei. Das Ergebnis kommt in den Gesprächsverlauf für den nächsten Schritt.
4. Fehler eines Werkzeugaufrufs werden als Werkzeugergebnis zurückgegeben, damit
   das Modell den Aufruf korrigieren oder die übrige Aufgabe weiterbearbeiten kann.
   Fehlgeschlagene Modellaufrufe verbrauchen einen Schritt und werden innerhalb
   des verbleibenden Limits erneut versucht.
5. Eine abschließende Antwort beendet den Lauf erfolgreich. Ist nach dem letzten
   erlaubten Modellaufruf noch keine Antwort vorhanden, endet er als Fehler.

Jeder Lauf erzeugt eine eigene Datei `logs/<run_id>.jsonl`. Jede Zeile ist ein
JSON-Objekt mit `ts`, `run_id`, `event`, `tool`, `args`, `ok`, `model` und
`duration_ms`. Je nach Ereignis kommen `task`, `result`, `answer` oder `message`
hinzu. Die Ereignisse heißen `user_task`, `tool_call`, `tool_result`, `final` und
`error`. Das zusätzliche Feld `step` zählt die Modellaufrufe ab `1`.
`duration_ms` misst beim `tool_call` den Modellaufruf, beim `tool_result` den
Werkzeugaufruf und bei `final` den abschließenden Modellaufruf.
Ein fehlgeschlagener Werkzeugaufruf hat `ok: false` im `tool_result`; ein
fehlgeschlagener Modellaufruf einen `error`-Eintrag mit `stage: "model"`.
Der letzte Eintrag zeigt den Abschluss: `final` oder `error`. Beim Schrittlimit
lautet `reason` im letzten Eintrag `step_limit`.

### Selbst prüfen

```bash
python -m agent "Was steht am 29.10.2026 im Kalender?"
python -m agent "Was steht am 01.11.2026 im Kalender?"
python -m agent "Was steht am 01.12.2026 im Kalender?"
python -m agent "Vergleiche den 29.10.2026 mit dem 30.10.2026. Welche Termine stehen an?"
python -m agent "Was steht am 01.12.2026 und am 29.10.2026 an? Bearbeite beide Tage, auch wenn für einen die Daten fehlen."
```

Danach die jeweilige Logdatei prüfen: Das Modell muss `calendar` mit dem richtigen
Datum aufgerufen haben. Die Antwort muss dem `tool_result` entsprechen. Der letzte
Eintrag ist bei Erfolg `final`, bei einem Fehler `error` mit `ok: false`.

Das Schrittlimit lässt sich gezielt prüfen:

```bash
MAX_STEPS=1 python -m agent "Was steht am 29.10.2026 und am 30.10.2026 an?"
echo $?
```

Nach dem ersten Modellaufruf mit Werkzeugaufruf fehlt ein weiterer Modellschritt
für die Antwort. Erwartet sind deshalb Exitcode `1` und `reason: "step_limit"`
im letzten Logeintrag.

Automatisierte Tests ohne Netzwerk und API-Schlüssel:

```bash
python -m unittest discover -s tests -v
```

Sie prüfen einzelne und mehrere Tage, eine Antwort im letzten erlaubten Schritt,
das Schrittlimit, die Korrektur ungültiger Argumente, das Weiterarbeiten nach
Werkzeug- und Modellfehlern sowie fehlende Daten neben anderen Kalendertagen.

### Repository und Abgabe

Das öffentliche GitHub-Repository muss `agentic-interaction-ws2627` heißen. In
Moodle wird der HTTPS-Link mit `.git` am Ende eingereicht, also
`https://github.com/neo709/agentic-interaction-ws2627.git`.
Bewertet wird der rechtzeitig gepushte
Stand. `.env`, `.venv/` und `logs/` sind durch `.gitignore` ausgeschlossen.
Der abgeschlossene Stand von Übung 1 ist mit dem Git-Tag `uebung-1` gesichert.

Daten und Schnittstellenbeschreibung:
[agentic-interaction-data](https://github.com/jhbelz/agentic-interaction-data).
