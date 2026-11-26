# Agentic Interaction – WS 2026/27

Ein Agent, der Fragen zu **Terminen, Wetter und Zugverbindungen** beantwortet und
**Termine anlegen** kann. Das Sprachmodell entscheidet selbst, welche Werkzeuge es
braucht; die Daten kommen aus den
[Mock-Daten](https://github.com/jhbelz/agentic-interaction-data) des Kurses.

```text
$ CONDITION=direct python -m agent "Wie komme ich am 29.10.2026 nach München, und brauche ich einen Regenschirm?"

Zugverbindungen Ulm → München am 29.10.2026:
- 07:12 → 08:31  ICE 594, direkt, 29,90 €
…
Wetter in München:
- Schauer, 8 °C, 60 % Regenwahrscheinlichkeit → Regenschirm mitnehmen
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
| `CONDITION` | **Pflicht** beim Start: `preview` oder `direct` (siehe unten) |
| `AUTO_APPROVE` | optional, `1` = in `preview` ohne Nachfrage freigeben |

Umgebungsvariablen haben Vorrang vor `.env`. Statt Groq geht jeder OpenAI-kompatible
Endpunkt, z. B. OpenRouter: `cp .env.openrouter.example .env`.

## Starten

```bash
CONDITION=preview python -m agent "Blocke mir am 29.10.2026 um 17:00 eine Stunde Puffer."
CONDITION=direct  python -m agent "Blocke mir am 29.10.2026 um 17:00 eine Stunde Puffer."
```

Ohne `CONDITION` (oder mit einem anderen Wert) startet der Agent nicht. Die Antwort
kommt auf die Standardausgabe (Exitcode `0`); Plan, Rückfrage, Bericht und Fehler
kommen auf die Standardfehlerausgabe (Fehler mit Exitcode `1`).

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
   Modell den Fehler als Ergebnis und kann es noch einmal versuchen. Meldet der
   Modell-Endpunkt sein Nutzungslimit (HTTP 429), wartet der Agent kurz (höchstens 30 s).

| Werkzeug | Parameter | liest |
| --- | --- | --- |
| `calendar` | `date` | `calendar/{date}.json` |
| `weather` | `city`, `date` | `weather/{city}/{date}.json` |
| `connections` | `from_city`, `to_city`, `date` | `transit/{from}/{to}/{date}.json` |
| `context` | – | `context.json` (Wohnort, aktuelles Datum) |
| `create_event` | `date`, `start`, `end`, `title` | **schreibt** eine Zeile in `var/calendar.jsonl` |

**Nichts erfinden:** Gibt es für einen Ort oder Tag keine Daten (HTTP 404), liefert das
Werkzeug `{"no_data": true}` und das Modell sagt das so. Im ersten Schritt *muss*
das Modell ein Werkzeug aufrufen – ohne Daten kann es also gar nicht antworten.
Kennt die Datenquelle eine Stadt nicht (z. B. `munich`), schickt das Werkzeug die Liste
aus `index.json` mit (`known_cities`); das Modell korrigiert sich dann auf `muenchen`.

| Datei | Aufgabe |
| --- | --- |
| `agent/__main__.py` | Frage lesen, Lauf starten, Exitcode |
| `agent/config.py` | `.env` und Umgebungsvariablen lesen |
| `agent/loop.py` | die Schleife aus dem Bild oben |
| `agent/tools.py` | die Werkzeuge und welche davon unumkehrbar sind |
| `agent/approval.py` | Plan zeigen, fragen, berichten |
| `agent/log.py` | das Protokoll |

## Termine anlegen: `preview` und `direct`

`create_event` ist das einzige Werkzeug, das etwas verändert. Es schreibt in
`var/calendar.jsonl` (in `.gitignore`); die Mock-Daten bleiben unverändert, `calendar`
liest weiter nur von dort. Welche Werkzeuge unumkehrbar sind, steht an genau einer
Stelle: `IRREVERSIBLE_TOOLS` in `agent/tools.py`.

| | `CONDITION=preview` | `CONDITION=direct` |
| --- | --- | --- |
| vor dem Ausführen | zeigt den Plan des Schritts | – |
| unumkehrbare Aktion | fragt einzeln: `[j/N]` | führt sie aus |
| nach dem Ausführen | – | berichtet, was ausgeführt wurde |

- Nur `j`/`ja` gibt frei. `n`, Enter oder keine Eingabe heißt **nicht freigegeben**:
  Das Modell bekommt `{"denied": true}` als Ergebnis, plant weiter, und der Lauf endet normal.
- `AUTO_APPROVE=1` gibt in `preview` ohne Nachfrage frei.
- Systemprompt, Werkzeuge und Modell sind in beiden Bedingungen gleich; das Modell
  erfährt nie, in welcher Bedingung es läuft.

**Amershi-Richtlinien:** Der Freigabedialog verletzt G9 (*Support efficient
correction*), weil man den vorgeschlagenen Termin nur annehmen oder ablehnen kann und
zum Beispiel eine andere Uhrzeit nur über eine komplett neue Anfrage erreicht. Außerdem
verletzt er G11 (*Make clear why the system did what it did*) und G16 (*Convey the
consequences of user actions*), weil er nur den technischen Aufruf `create_event(…)`
zeigt, ohne zu erklären, warum der Agent genau diesen Termin plant und dass ein „j“ ihn
tatsächlich in den Kalender schreibt.

## Protokoll

Jeder Lauf schreibt `logs/<run_id>.jsonl`, eine Zeile pro Ereignis mit den Feldern
`ts`, `run_id`, `event`, `tool`, `args`, `ok`, `model`, `duration_ms`, `condition`
(dazu z. B. `step`, `result`, `answer`, `reason`).

| `event` | wann |
| --- | --- |
| `user_task` | Frage kommt rein |
| `tool_call` / `tool_result` | Werkzeug aufgerufen / Ergebnis (`ok: false` bei Fehler) |
| `approval_request` | nur `preview`: Frage nach Freigabe einer unumkehrbaren Aktion |
| `approval_granted` / `approval_denied` | nur `preview`: Antwort darauf (`auto: true` bei `AUTO_APPROVE`) |
| `final` | Antwort – Lauf erfolgreich |
| `error` | Fehler; als letzter Eintrag mit `reason` (z. B. `step_limit`) – Lauf gescheitert |

## Testen

```bash
python -m unittest discover -s tests -v     # ohne Netz und ohne API-Schlüssel
```

Von Hand, danach jeweils das neueste Log in `logs/` ansehen. Vorher einmal
`export CONDITION=direct` (oder `preview`), dann:

```bash
python -m agent "Was steht am 29.10.2026 und am 30.10.2026 im Kalender?"   # mehrere Schritte
python -m agent "Was steht am 01.12.2026 im Kalender?"                     # Tag ohne Daten
python -m agent "Wie ist das Wetter am 29.10.2026 in Berlin?"              # Ort ohne Daten
MAX_STEPS=1 python -m agent "Was steht am 29.10.2026 und am 30.10.2026 an?"  # Schrittlimit → Exitcode 1
```

Freigabe prüfen (danach `var/calendar.jsonl` ansehen):

```bash
echo n | CONDITION=preview python -m agent "Blocke mir am 29.10.2026 um 17:00 eine Stunde Puffer."  # abgelehnt → nichts geschrieben
CONDITION=preview AUTO_APPROVE=1 python -m agent "Blocke mir am 29.10.2026 um 17:00 eine Stunde Puffer."
```

## Abgabe

Öffentliches Repo `agentic-interaction-ws2627`, eingereicht als
`https://github.com/neo709/agentic-interaction-ws2627.git`. `.env`, `.venv/`,
`logs/` und `var/` sind in `.gitignore`. Die Stände der Übungen sind als Tags gesichert
(`uebung-1`, `uebung-3`, `uebung-4`, `uebung-5`); `DELEGATION.md` enthält Übung 2.
