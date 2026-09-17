# Übersicht: Alle Aufrufe der Harness-Demo

Diese Datei listet **jeden möglichen Aufruf** von `harness_demo.py` auf und erklärt im
Detail, **was er demonstriert** und **worauf du in der Ausgabe achten solltest**.

> **Wichtig – immer das venv-Python nutzen:**
> ```powershell
> .\.venv\Scripts\python.exe .\harness_demo.py --demo <name>
> ```
> Der bloße Befehl `python` findet das `agent_framework`-Paket nicht.

> **Voraussetzungen:**
> - `az login` (bei Foundry-Client) **und** RBAC-Rolle *Azure AI Developer* auf der
>   Foundry-Ressource. Ohne diese Rolle bricht der Harness mit **HTTP 403** ab.
> - Alternativ `OPENAI_API_KEY` setzen (OpenAI-Fallback).
> - `.env` neben dem Skript konfiguriert (`FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_MODEL`).

---

## Schnellübersicht

| # | Aufruf | Thema | Kernaussage |
|---|--------|-------|-------------|
| 1 | `--demo minimal` | Minimaler Harness | So wenig Code wie möglich für einen lauffähigen Agenten |
| 2 | `--demo tools` | Function Tools | Der Harness ruft eigene Python-Funktionen automatisch auf |
| 3 | `--demo observability` | Observability | Was der Harness intern tut, als lesbarer Ablaufbaum |
| 3b | `--demo observability --fail-tool` | Fehlerfall | Wie ein blockierter/fehlgeschlagener Schritt aussieht |
| 4 | `--demo interactive` | Interaktive Session | Der Harness hält Verlauf/Plan über mehrere Runden |
| 5 | `--demo approval` | Human-in-the-Loop | Folgenreiche Tools warten auf menschliche Freigabe |
| 6 | `--demo planning` | Plan-/Execute-Modus | Der Harness zerlegt einen Prompt in eine Todo-Liste |

> **Hinweis:** Jede Demo gibt **vor dem Lauf** den verwendeten Prompt (und die
> relevanten Instructions/Tools) aus – so ist immer klar, was der Auslöser ist.

---

## Prompt-Spickzettel (was löst was aus?)

| Demo | Instructions / Tools | Prompt (Auslöser) |
|------|----------------------|-------------------|
| 1 minimal | keine | „Plane ein Wochenende in Seattle in drei Stichpunkten." |
| 2 tools | *harness:* „Nutze Tools bewusst …" · *agent:* „hilfreicher Reise-Assistent" · Tools: `get_weather`, `convert_currency` | „Wie ist das Wetter in Amsterdam und was sind 250 Euro in USD?" |
| 3 observability | Tool: `get_weather` | „Wie ist das Wetter in München?" |
| 3b fail-tool | Tool: `get_weather_unstable` (wirft) | „Wie ist das Wetter in München?" |
| 4 interactive | *agent:* „hilfreicher Assistent für eine Schulung" · Tools: `get_weather`, `convert_currency` | **deine** Eingaben an `Du >` |
| 5 approval | *agent:* „…rufe direkt `book_hotel` auf, keine Rückfragen…" · Tool: `book_hotel` (freigabepflichtig) | „Buche das Hotel in München für 3 Nächte." |
| 6 planning | *agent:* „Reiseplaner … zerlege in Todos" · Tools: `get_weather`, `convert_currency` | „Plane einen Tagesausflug: Prüfe das Wetter in München, schlage je nach Wetter eine Aktivität vor und rechne ein Budget von 150 Euro in CHF um. Fasse das Ergebnis als kurze Liste zusammen." |

---

## 1. Minimaler Harness

```powershell
.\.venv\Scripts\python.exe .\harness_demo.py --demo minimal
```

**Was es demonstriert:**
Der kleinstmögliche Einstieg. Ein einziger Aufruf `create_harness_agent(client=...)`
genügt, um einen voll funktionsfähigen, „harnessed" Agenten zu erhalten – ganz ohne
Tools, Instructions oder Konfiguration.

**Was im Hintergrund passiert:**
Auch bei dieser minimalen Variante bringt der Harness bereits sein komplettes Gerüst mit:
Session-Verwaltung, Verlaufs-/Kontext-Management, Plan-/Todo-Infrastruktur und die
Middleware-Kette. Man sieht davon nur das Endergebnis.

**Worauf achten:**
Die Ausgabe ist schlicht die Antwort des Modells (Wochenendplan für Seattle in drei
Stichpunkten). Dies ist die **Vergleichsbasis** für alle folgenden Demos: „So sieht ein
Lauf aus, wenn man nichts weiter konfiguriert."

---

## 2. Harness mit Function Tools

```powershell
.\.venv\Scripts\python.exe .\harness_demo.py --demo tools
```

**Was es demonstriert:**
Wie man dem Agenten eigene **Python-Funktionen als Werkzeuge** gibt (`get_weather`,
`convert_currency`) und wie **getrennte Instructions** wirken:
- `harness_instructions` – Regeln für die Orchestrierung („Nutze Tools bewusst, berichte
  nur verifizierte Ergebnisse.")
- `agent_instructions` – die Persona/Rolle des Agenten („hilfreicher Reise-Assistent").

Außerdem werden **Kontext- und Ausgabe-Limits** gesetzt
(`max_context_window_tokens`, `max_output_tokens`).

**Was im Hintergrund passiert:**
Der Prompt fragt nach Wetter **und** Währungsumrechnung. Das Modell erkennt, dass es
dafür beide Tools braucht, der Harness ruft sie auf und fügt die Ergebnisse zusammen.

**Worauf achten:**
Die Antwort enthält konkrete Tool-Ergebnisse (Wetter Amsterdam + 250 EUR in USD), die
**nicht** aus dem Modellwissen stammen, sondern aus deinen Funktionen.

---

## 3. Harness mit Observability

```powershell
.\.venv\Scripts\python.exe .\harness_demo.py --demo observability
```

**Was es demonstriert:**
Macht das „Harnessing" **sichtbar**. Über OpenTelemetry wird jeder interne Arbeitsschritt
als *Span* aufgezeichnet und als **lesbarer, verschachtelter Ablaufbaum** ausgegeben –
nicht als Roh-JSON.

**Was du im Ablaufbaum siehst (deutsch beschriftet):**
- `[AGENT-LAUF]` – der äußere Rahmen, der den ganzen Ablauf steuert.
- `[MODELL-AUFRUF]` – der Harness fragt das Sprachmodell (mit Modellname + Token-Zahlen).
- `[TOOL-AUFRUF]` – der Harness ruft deine Python-Funktion auf (z. B. `get_weather`).
- `[PLAN/TODO]` – der Harness verwaltet die Todo-Liste (siehe Demo 6).

Die **Einrückung** zeigt die Verschachtelung: Was eingerückt steht, läuft *innerhalb* des
darüberstehenden Schritts. Genau diese Koordination ist die Arbeit des Harness.

**Worauf achten:**
Ein blanker LLM-Aufruf wäre **ein** Schritt. Hier siehst du mehrere ineinander
verschachtelte Schritte inklusive Dauer (ms) und Token-Verbrauch. Das Fazit am Ende
erklärt außerdem, **wie man Blockaden erkennt**.

---

## 3b. Fehlerfall / Blockade sichtbar machen

```powershell
.\.venv\Scripts\python.exe .\harness_demo.py --demo observability --fail-tool
```

**Was es demonstriert:**
Denselben Ablauf wie Demo 3, aber das Wetter-Tool (`get_weather_unstable`) wirft
**absichtlich eine Ausnahme**. So wird gezeigt, wie ein **blockierter/fehlgeschlagener
Schritt** aussieht und wie robust der Harness damit umgeht.

**Worauf achten:**
- Der betroffene Schritt im Baum ist mit `[!! BLOCKIERT/FEHLER]` markiert.
- Direkt darunter stehen `!! Grund:` (Status-Text) und `!! Ausnahme:` (Typ + Meldung).
- **Resilienz-Lektion:** Der Harness fängt die Tool-Ausnahme ab und lässt das Modell
  darauf reagieren, statt den ganzen Lauf abstürzen zu lassen.

**Die zwei Blockade-Typen (im Fazit erklärt):**
1. **Fehler-Blockade** – ein Span mit Fehlerstatus (z. B. 403 RBAC, Rate-Limit,
   Tool-Ausnahme) → Marker `[!! BLOCKIERT/FEHLER]`.
2. **Freigabe-Blockade** – der Harness pausiert absichtlich und wartet
   (`response.user_input_requests`) → siehe Demo 5.

---

## 4. Interaktive Session

```powershell
.\.venv\Scripts\python.exe .\harness_demo.py --demo interactive
```

**Was es demonstriert:**
Eine fortlaufende Chat-Schleife über **dieselbe Session**. Der Harness hält
**Verlauf, Kontext und Plan/Todos** über mehrere Runden hinweg – man muss den Zustand
nicht selbst verwalten.

**Bedienung:**
Fragen eingeben; leere Eingabe oder `exit`/`quit` beendet die Demo. Auch `Ctrl+C`
beendet sauber.

**Worauf achten:**
Stelle aufeinander aufbauende Fragen (z. B. erst „Wie ist das Wetter in München?", dann
„Und was kosten 100 Euro dort in CHF?"). Der Agent versteht den Bezug, weil die Session
den Kontext trägt.

---

## 5. Human-in-the-Loop Tool-Approval

```powershell
.\.venv\Scripts\python.exe .\harness_demo.py --demo approval
```

**Was es demonstriert:**
Wie **folgenreiche Aktionen** vor der Ausführung eine **menschliche Freigabe** erfordern.
Das Tool `book_hotel` ist mit `@tool(approval_mode="always_require")` markiert.

**Was im Hintergrund passiert:**
Der Harness unterbricht den Lauf, bevor das Tool ausgeführt wird, und liefert eine
`user_input_requests`-Anfrage zurück. Das Skript zeigt dir Toolname + Argumente und
fragt `Freigeben? [j/N]`. Die Antwort wird als Approval-Response zurück in dieselbe
Session gegeben. **Wichtig:** Es wird **nur** die Freigabe-Antwort
(`to_function_approval_response(...)`) zurückgesendet – die ursprüngliche Anfrage
steckt schon im (bei Foundry serverseitigen) Verlauf und darf nicht erneut als
`assistant`-Nachricht eingespeist werden, sonst `BadRequestError: No tool output found`.

**Worauf achten:**
- Bei **`j`** wird die Buchung ausgeführt (Buchungsnummer erscheint).
- Bei **`N`** wird das Tool abgelehnt und der Agent reagiert entsprechend.
- Dies ist die **gewollte Blockade** (Human-in-the-Loop) – der Gegenpol zur
  Fehler-Blockade aus Demo 3b.

---

## 6. Plan-/Execute-Modus mit Todos

```powershell
.\.venv\Scripts\python.exe .\harness_demo.py --demo planning
```

**Was es demonstriert:**
Der stärkste Sichtbarmacher des Harness-Effekts. Ein **einziger, komplexer Prompt** wird
vom Harness in eine **Todo-Liste** zerlegt, Punkt für Punkt anhand der LLM-Antworten
abgearbeitet und abgehakt.

**Der Prompt:**
> „Plane einen Tagesausflug: Prüfe das Wetter in München, schlage je nach Wetter eine
> Aktivität vor und rechne ein Budget von 150 Euro in CHF um. Fasse das Ergebnis als
> kurze Liste zusammen."

**Die drei Ausgabeblöcke:**
1. **Antwort des Agenten** – das fertige Ergebnis.
2. **Todo-Liste** – die Punkte, die der Harness **aus deinem Prompt** gebaut hat, mit
   Häkchen (`[x]`/`[ ]`) und „N/M erledigt".
3. **Ablaufbaum** – hier tauchen `[PLAN/TODO]`-Schritte auf (`todos_add`,
   `todos_complete`), weil das LLM in seiner Antwort entscheidet, Todos anzulegen bzw.
   abzuhaken.

**Kernaussage:**
**Prompt-Komplexität → mehr Harness-Aktivität.** Genau hier wird der Effekt des
Harnessing greifbar: Der Harness übersetzt *deinen* Prompt in einen strukturierten Plan
und die *Antworten des LLM* treiben dessen Abarbeitung.

---

## Anhang: Verfügbare Tools im Skript

| Tool | Zweck | Besonderheit |
|------|-------|--------------|
| `get_weather` | Simulierte Wettervorhersage | Standard-Tool |
| `convert_currency` | Simulierte Währungsumrechnung | Standard-Tool |
| `book_hotel` | Simulierte Hotelbuchung | `approval_mode="always_require"` (Demo 5) |
| `get_weather_unstable` | Wirft absichtlich eine Ausnahme | Nur für den Fehlerfall (Demo 3b) |

## Anhang: Client-Konfiguration (`.env`)

```dotenv
# Foundry (bevorzugt) – vorher: az login + RBAC "Azure AI Developer"
FOUNDRY_PROJECT_ENDPOINT=https://<resource>.services.ai.azure.com/api/projects/<project>
FOUNDRY_MODEL=gpt-5.2

# Alternativ: OpenAI-Fallback
# OPENAI_API_KEY=sk-...
# OPENAI_MODEL=gpt-4o
```
