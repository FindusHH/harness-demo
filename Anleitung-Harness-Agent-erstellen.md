# Schritt für Schritt: einen Harness-Agenten erstellen

Praktische Anleitung – Stand: 2026-09-17

> **Hinweis zu den Fachbegriffen:** Die Begriffe *Harnessing*, *Agent Harness* und *Harness*
> werden bewusst in ihrer englischen Originalform verwendet, weil es keine etablierte deutsche
> Übersetzung gibt. Sinngemäß ist ein *Harness* das Software-„Gerüst", das ein Sprachmodell erst
> zu einem handlungsfähigen Agenten macht. Alle übrigen Fachbegriffe werden bei der ersten
> Nennung erklärt.

Diese Anleitung führt in nachvollziehbaren Schritten vom leeren Ordner bis zum lauffähigen
Harness-Agenten mit Werkzeugen, Freigaben und Nachverfolgbarkeit. Jeder Schritt erklärt **was**
zu tun ist und **warum** dieser Schritt nötig ist. Als Begleitmaterial dienen die
Schulungsunterlage [`Agent-Harnessing-Schulung.md`](Agent-Harnessing-Schulung.md) und die
lauffähige Demo [`harness_demo.py`](harness_demo.py).

---

## Überblick der Schritte

```mermaid
flowchart TD
    S0[0. Voraussetzungen] --> S1[1. Projekt und Umgebung]
    S1 --> S2[2. Pakete installieren]
    S2 --> S3[3. Chat-Client waehlen]
    S3 --> S4[4. Minimalen Harness bauen]
    S4 --> S5[5. Sitzung anlegen und ausfuehren]
    S5 --> S6[6. Werkzeuge ergaenzen]
    S6 --> S7[7. Anweisungen trennen]
    S7 --> S8[8. Freigaben - Mensch in der Schleife]
    S8 --> S9[9. Planung und Aufgabenlisten]
    S9 --> S10[10. Nachverfolgbarkeit]
    S10 --> S11[11. Testen und ausfuehren]
    S11 --> S12[12. Optional: als Hosted Agent bereitstellen]
```

---

## Schritt 0: Voraussetzungen prüfen

**Was:** Stelle sicher, dass folgende Dinge vorhanden sind:

- **Python 3.10 oder neuer** (`python --version`).
- Zugang zu einem **Sprachmodell** (englisch *Large Language Model*, kurz *LLM* – ein großes,
  auf Text trainiertes KI-Modell wie GPT-4o), entweder über
  - **Microsoft Foundry** (ein Foundry-Projekt-Endpunkt und das Kommandozeilenwerkzeug `az` mit
    ausgeführtem `az login`), **oder**
  - **OpenAI** mit einem API-Schlüssel (englisch *API key*, ein geheimes Zugangskennwort).

**Warum:** Ein Harness ist nur das Gerüst – er braucht immer ein Sprachmodell im Hintergrund, an
das er die eigentliche Textverarbeitung weiterreicht. Ohne einen erreichbaren Chat-Client
(Verbindung zum Modell) kann kein Agent laufen.

---

## Schritt 1: Projektordner und virtuelle Umgebung anlegen

**Was:** Lege einen Projektordner an und darin eine **virtuelle Umgebung** (englisch *virtual
environment* – ein abgekapselter Python-Bereich pro Projekt).

```bash
mkdir mein-harness-agent
cd mein-harness-agent
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

**Warum:** Die virtuelle Umgebung hält die Pakete dieses Projekts von anderen Projekten und der
System-Installation getrennt. So bleiben die Versionen stabil und Konflikte werden vermieden.

---

## Schritt 2: Pakete installieren

**Was:** Installiere das **Microsoft Agent Framework** und je nach Modellwahl den passenden
Zusatz.

```bash
pip install agent-framework                 # Kern des Agent Frameworks
pip install azure-identity                  # nur fuer Foundry: Anmeldung ueber az login
```

Alternativ – falls eine `requirements.txt` vorhanden ist (wie in diesem Ordner):

```bash
pip install -r requirements.txt
```

**Warum:** Das Agent Framework liefert die Funktion `create_harness_agent` und alle Bausteine des
Harness (Sitzung, Werkzeuge, Freigaben, Verdichtung, Nachverfolgbarkeit) fertig mit. Man baut das
Gerüst also nicht selbst, sondern konfiguriert nur die gewünschten Fähigkeiten. `azure-identity`
wird gebraucht, damit sich der Foundry-Client sicher über die Anmeldung von `az login` ausweisen
kann.

---

## Schritt 3: Chat-Client auswählen

**Was:** Erzeuge den **Chat-Client** – die Softwareverbindung zwischen Agent und Sprachmodell. In
der Praxis wählt man ihn abhängig von Umgebungsvariablen (Einstellungen, die außerhalb des
Programms gesetzt werden), damit dieselbe Datei mit Foundry **oder** OpenAI läuft.

```python
import os

def build_chat_client():
    # Foundry bevorzugt, sonst OpenAI als Ausweichloesung
    if os.environ.get("FOUNDRY_PROJECT_ENDPOINT"):
        from agent_framework.foundry import FoundryChatClient
        from azure.identity import AzureCliCredential

        return FoundryChatClient(
            project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
            model=os.environ.get("FOUNDRY_MODEL", "gpt-4o"),
            credential=AzureCliCredential(),   # nutzt die Anmeldung von 'az login'
        )

    if os.environ.get("OPENAI_API_KEY"):
        from agent_framework.openai import OpenAIChatClient

        return OpenAIChatClient(model=os.environ.get("OPENAI_MODEL", "gpt-4o"))

    raise SystemExit("Kein Client konfiguriert: FOUNDRY_PROJECT_ENDPOINT (+ az login) oder OPENAI_API_KEY setzen.")
```

**Warum:** Der Harness ist **client-agnostisch** – dieselbe Harness-Konfiguration funktioniert
mit Foundry, Azure OpenAI oder OpenAI. Indem man den Client an einer zentralen Stelle erzeugt,
bleibt der übrige Code unverändert, egal welches Modell im Hintergrund arbeitet.

Dokumentation: <https://learn.microsoft.com/azure/foundry/how-to/develop/sdk-overview>

---

## Schritt 4: Den minimalen Harness bauen

**Was:** Erzeuge mit `create_harness_agent` den Agenten. Im einfachsten Fall genügt der Client.

```python
from agent_framework import create_harness_agent

agent = create_harness_agent(client=build_chat_client())
```

**Warum:** `create_harness_agent` schaltet die einzelnen Bausteine (Chat-Pipeline, Aufgabenliste,
Betriebsmodi, Freigaben, Datei-Gedächtnis, Nachverfolgbarkeit) zu einem einzigen, normalen Agenten
zusammen und versieht sie mit sinnvollen Voreinstellungen. Schon der minimale Aufruf liefert also
einen arbeitsfähigen Agenten – weitere Fähigkeiten werden in den folgenden Schritten nur noch
zugeschaltet.

Dokumentation: <https://learn.microsoft.com/agent-framework/concepts/harness>

---

## Schritt 5: Sitzung anlegen und Agenten ausführen

**Was:** Lege eine **Sitzung** (englisch *session*) an und übergib sie bei jedem Aufruf von
`agent.run(...)`.

```python
import asyncio

async def main():
    agent = create_harness_agent(client=build_chat_client())

    session = agent.create_session()
    response = await agent.run(
        "Plane ein Wochenende in Seattle in drei Stichpunkten.",
        session=session,
    )
    print(response.text)

asyncio.run(main())
```

**Warum:** Die Sitzung ist der **verbindende Faden** über einzelne Aufrufe hinweg. In ihr liegen
Gesprächsverlauf, Aufgabenliste und Betriebsmodus. Ohne dieselbe Sitzung würde der Agent bei
jedem Aufruf sein Gedächtnis verlieren, und die später aktivierten Freigaben würden nicht
funktionieren – sie setzen dieselbe Sitzung über alle Runden zwingend voraus. `agent.run` ist
asynchron, deshalb wird alles in einer `async`-Funktion mit `asyncio.run` gestartet.

Dokumentation: <https://learn.microsoft.com/agent-framework/concepts/agents/conversations/session>

---

## Schritt 6: Werkzeuge (Function Tools) ergänzen

**Was:** Ein **Werkzeug** (englisch *tool*) ist eine normale Python-Funktion, die der Agent bei
Bedarf aufrufen darf. Mit dem Zusatz `@tool` wird sie als Werkzeug kenntlich gemacht; die
`Annotated`-Beschreibungen erklären dem Modell die Parameter.

```python
from typing import Annotated
from agent_framework import tool

@tool
def get_weather(city: Annotated[str, "Name der Stadt, z. B. 'Amsterdam'"]) -> str:
    """Gibt eine (simulierte) Wettervorhersage fuer eine Stadt zurueck."""
    forecast = {"amsterdam": "bewoelkt, 18 Grad", "muenchen": "sonnig, 24 Grad"}
    return forecast.get(city.strip().lower(), f"Keine Daten fuer {city}.")

agent = create_harness_agent(
    client=build_chat_client(),
    tools=[get_weather],
)
```

**Warum:** Ein Sprachmodell allein kann nur Text erzeugen. Erst Werkzeuge geben dem Agenten
Handlungsfähigkeit – etwa Daten abrufen oder Aktionen auslösen. Der Harness ruft die Werkzeuge
**automatisch** auf, wenn das Modell sie anfordert, und sichert den Verlauf nach jedem Aufruf. Mit
`@tool` markierte Funktionen brauchen standardmäßig keine Freigabe
(`approval_mode="never_require"`).

Dokumentation: <https://learn.microsoft.com/agent-framework/agents/tools/function-tools>

---

## Schritt 7: Anweisungen trennen

**Was:** Gib dem Agenten gezielte **Anweisungen** (englisch *instructions* – Vorgaben in
natürlicher Sprache). Der Harness unterscheidet zwei Ebenen.

```python
agent = create_harness_agent(
    client=build_chat_client(),
    name="reise-agent",
    harness_instructions="Nutze Werkzeuge bewusst und berichte nur gepruefte Ergebnisse.",
    agent_instructions="Du bist ein hilfreicher Reise-Assistent.",
    max_context_window_tokens=128_000,
    max_output_tokens=16_384,
)
```

**Warum:** `harness_instructions` gelten für das Gerüst insgesamt und stehen **vor** den
agentenspezifischen `agent_instructions`. So trennt man allgemeines Verhalten (z. B. „nur
geprüfte Ergebnisse berichten") von der konkreten Rolle des Agenten. Das gleichzeitige Setzen von
`max_context_window_tokens` (maximale Größe des Kontextfensters) und `max_output_tokens`
(maximale Antwortlänge) schaltet zusätzlich die **Verdichtung** (englisch *compaction*) ein: Der
Harness kürzt dann automatisch ältere Verlaufsteile, um Kontextgrenze, Kosten und Antwortzeit im
Griff zu behalten.

Dokumentation: <https://learn.microsoft.com/agent-framework/concepts/agents/conversations/compaction>

---

## Schritt 8: Freigaben einrichten (Mensch in der Schleife)

**Was:** Markiere folgenreiche Werkzeuge mit `approval_mode="always_require"` und verarbeite die
Freigabeanfragen in der Ausführungsschleife.

```python
from agent_framework import Message

@tool(approval_mode="always_require")
def book_hotel(
    city: Annotated[str, "Stadt fuer die Buchung"],
    nights: Annotated[int, "Anzahl der Naechte"],
) -> str:
    """Bucht ein Hotel (folgenreiche Aktion, erfordert menschliche Freigabe)."""
    return f"Hotel in {city} fuer {nights} Naechte gebucht."

async def run_with_approval():
    agent = create_harness_agent(client=build_chat_client(), tools=[book_hotel])
    session = agent.create_session()               # dieselbe Sitzung ueber alle Runden!
    current_input = "Buche mir ein Hotel in Muenchen fuer 3 Naechte."

    while True:
        result = await agent.run(current_input, session=session)
        if not result.user_input_requests:
            print(result.text)
            break

        new_inputs = []
        for request in result.user_input_requests:
            if request.function_call is None:
                continue
            answer = input(f"Freigeben? {request.function_call.name} [j/N] > ").strip().lower()
            approved = answer in {"j", "ja", "y", "yes"}
            # Nur die Freigabe-ANTWORT zuruecksenden. Die Zwischenschicht hat die
            # urspruengliche Anfrage bereits in der Sitzung gespeichert und bindet
            # die Antwort selbst daran. Die Anfrage NICHT erneut als assistant-Message
            # mitschicken (siehe Hinweis unten).
            new_inputs.append(Message(
                role="user",
                contents=[request.to_function_approval_response(approved)],
            ))
        current_input = new_inputs
```

**Warum:** Manche Aktionen sind folgenreich (etwa eine Buchung) und dürfen nicht ohne menschliche
Bestätigung laufen. Dieses Muster heißt „Mensch in der Schleife" (englisch *human-in-the-loop*).
Der Harness aktiviert dafür standardmäßig eine **Freigabe-Zwischenschicht** (englisch
*middleware*), die den Werkzeugaufruf abfängt, bereits erteilte Freigaben anwendet und offene
Fälle als `user_input_requests` zurückgibt. Wichtig: Die Freigabe braucht über alle Runden
hinweg **dieselbe Sitzung**, sonst geht der Bezug zum ursprünglichen Aufruf verloren.

> **Session-basiert vs. zustandslos – ein wichtiger Unterschied.** Die Microsoft-Learn-Doku zeigt
> in ihren *zustandslosen* Beispielen (ohne Sitzung) ein Muster, bei dem man in jeder Runde den
> **gesamten** Kontext erneut sendet: die ursprüngliche Anweisung, die Anfrage als
> `Message(role="assistant", contents=[request])` **und** die Freigabe-Antwort. Das ist nötig,
> weil ohne Sitzung („thread") kein Zustand gespeichert wird (O-Ton der Doku: *„When we don't have
> a thread, we need to ensure we include the original query, the approval request, and the approval
> response in each iteration."*).
>
> **Hier** arbeiten wir aber **mit** einer Sitzung – und zusätzlich mit dem Foundry-Client, der den
> Gesprächsverlauf **serverseitig** hält. Dann darf man die Anfrage **nicht** noch einmal als
> `assistant`-Message einspeisen: Sie steckt bereits im serverseitigen Verlauf, und ein erneutes
> Einspeisen erzeugt einen doppelten Werkzeugaufruf ohne passendes Ergebnis
> (`BadRequestError: No tool output found for function call`). Es genügt – und ist korrekt –, nur
> die **Freigabe-Antwort** zu senden; die Zwischenschicht bindet sie an die in der Sitzung
> gespeicherte Anfrage. Für den Session-Fall verweist die Doku auf das Beispiel
> `function_tool_with_approval_and_sessions.py`.

Dokumentation: <https://learn.microsoft.com/agent-framework/agents/tools/tool-approval>

---

## Schritt 9: Planung und Aufgabenlisten nutzen

**Was:** Für mehrstufige Aufgaben gibt man eine Anweisung, die den Agenten zum Zerlegen in
Teilaufgaben anhält. Aufgabenliste und Betriebsmodi sind im Harness bereits eingeschaltet.

```python
agent = create_harness_agent(
    client=build_chat_client(),
    agent_instructions=(
        "Du bist ein Reiseplaner. Zerlege komplexe Aufgaben in Todos, "
        "arbeite sie ab und nutze die verfuegbaren Werkzeuge."
    ),
    tools=[get_weather],
)
```

**Warum:** Der **Aufgaben-Provider** (englisch *todo provider*) gibt dem Modell Werkzeuge, um
Teilaufgaben anzulegen, abzuschließen und wieder abzurufen; die aktuelle Liste wird vor jedem
Aufruf eingefügt, damit der Agent offene Arbeit wieder aufnimmt. Der **Modus-Provider** trennt
das interaktive **Planen** (Analyse, Rückfragen, Plan vorstellen) vom eigenständigen
**Ausführen** (Plan abarbeiten). So bleiben auch länger laufende Aufgaben nachvollziehbar und
zielgerichtet.

Dokumentation: <https://learn.microsoft.com/agent-framework/agents/planning-and-todos>

---

## Schritt 10: Nachverfolgbarkeit aktivieren

**Was:** Schalte die **Nachverfolgbarkeit** (englisch *observability*) ein, um jeden Modell- und
Werkzeugaufruf mitzuschneiden.

```python
from agent_framework.observability import configure_otel_providers

configure_otel_providers()   # ENABLE_CONSOLE_EXPORTERS=true zeigt die Messpunkte in der Konsole

agent = create_harness_agent(
    client=build_chat_client(),
    otel_provider_name="mein.projekt.harness",
    tools=[get_weather],
)
```

**Warum:** Ohne Nachverfolgbarkeit ist ein Agent eine „Blackbox" – man sieht nicht, warum er
welche Entscheidung getroffen hat. Die Nachverfolgbarkeit ist standardmäßig aktiv und protokolliert
jeden Schritt als **Messpunkt** (englisch *span*) über den offenen Industriestandard
**OpenTelemetry**. `otel_provider_name` legt nur den Namen fest; **wohin** die Daten gehen (z. B.
Aspire-Dashboard, Jaeger, Azure Monitor), bestimmt ein separater Empfänger (englisch *exporter*)
über Umgebungsvariablen wie `OTEL_EXPORTER_OTLP_ENDPOINT`.

Dokumentation: <https://learn.microsoft.com/agent-framework/agents/observability>

---

## Schritt 11: Testen und ausführen

**Was:** Setze die nötigen Umgebungsvariablen und starte das Skript.

```bash
# Mit Foundry:
export FOUNDRY_PROJECT_ENDPOINT="https://<ressource>.services.ai.azure.com/api/projects/<projekt>"
export FOUNDRY_MODEL="gpt-4o"
az login

# ... oder mit OpenAI:
export OPENAI_API_KEY="sk-..."

python mein_agent.py
```

Zum Ausprobieren aller Stufen dient die fertige Demo in diesem Ordner:

```bash
python harness_demo.py --demo minimal        # Schritt 4-5
python harness_demo.py --demo tools          # Schritt 6-7
python harness_demo.py --demo approval        # Schritt 8
python harness_demo.py --demo planning        # Schritt 9
python harness_demo.py --demo observability   # Schritt 10
python harness_demo.py --demo interactive     # Sitzung als fortlaufende Schleife
```

**Warum:** Erst der reale Lauf zeigt, ob Client, Anmeldung und Werkzeuge korrekt
zusammenspielen. Die Demo deckt genau die Bausteine ab, die in dieser Anleitung Schritt für
Schritt aufgebaut werden, und eignet sich zum Vergleichen und Nachschlagen.

---

## Schritt 12 (optional): Als Hosted Agent bereitstellen

**Was:** Für einen dauerhaft erreichbaren Agenten wird er als **Hosted Agent** (von Foundry
gehostet) veröffentlicht.

```bash
pip install "azure-ai-projects>=2.3.0"
docker build --platform linux/amd64 -t myagent:v1 .
az acr login --name myregistry
docker tag myagent:v1 myregistry.azurecr.io/myagent:v1
docker push myregistry.azurecr.io/myagent:v1
```

Ablauf: **bauen und hochladen → Agenten-Version anlegen → warten, bis der Status `active`
erreicht ist → aufrufen**.

**Warum:** Bisher lief der Agent nur **kurzlebig** (englisch *ephemeral*) während der
Programmausführung. Als Hosted Agent bekommt er einen festen **Endpunkt** (englisch *endpoint*,
eine feste Adresse zum Aufrufen), den andere Anwendungen oder Agenten nutzen können. Foundry
übernimmt dann Skalierung, Identität und Nachverfolgbarkeit.

Dokumentation: <https://learn.microsoft.com/azure/foundry/agents/how-to/deploy-hosted-agent>

---

## Checkliste

- [ ] Python 3.10+ und Zugang zu einem Sprachmodell vorhanden (Schritt 0)
- [ ] Projektordner und virtuelle Umgebung angelegt (Schritt 1)
- [ ] `agent-framework` (und ggf. `azure-identity`) installiert (Schritt 2)
- [ ] Chat-Client erzeugt (Schritt 3)
- [ ] Harness mit `create_harness_agent` gebaut (Schritt 4)
- [ ] Sitzung angelegt und `agent.run` ausgeführt (Schritt 5)
- [ ] Werkzeuge mit `@tool` ergänzt (Schritt 6)
- [ ] Anweisungen getrennt, ggf. Token-Grenzen gesetzt (Schritt 7)
- [ ] Freigaben für folgenreiche Werkzeuge eingerichtet (Schritt 8)
- [ ] Planung/Aufgabenlisten genutzt (Schritt 9)
- [ ] Nachverfolgbarkeit aktiviert (Schritt 10)
- [ ] Getestet und ausgeführt (Schritt 11)
- [ ] Optional: als Hosted Agent bereitgestellt (Schritt 12)

---

## Weiterführende Links

| Thema | Link |
|---|---|
| Agent Harness (Konzept) | <https://learn.microsoft.com/agent-framework/concepts/harness> |
| Einstieg, Schritt 6: Agent Harness | <https://learn.microsoft.com/agent-framework/get-started/harness> |
| Werkzeuge (Function Tools) | <https://learn.microsoft.com/agent-framework/agents/tools/function-tools> |
| Werkzeug-Freigabe (Human-in-the-Loop) | <https://learn.microsoft.com/agent-framework/agents/tools/tool-approval> |
| Planung und Aufgabenlisten | <https://learn.microsoft.com/agent-framework/agents/planning-and-todos> |
| Nachverfolgbarkeit (Observability) | <https://learn.microsoft.com/agent-framework/agents/observability> |
| Hosted Agent bereitstellen | <https://learn.microsoft.com/azure/foundry/agents/how-to/deploy-hosted-agent> |

Ausführliche Hintergründe zu jedem Baustein stehen in der Schulungsunterlage
[`Agent-Harnessing-Schulung.md`](Agent-Harnessing-Schulung.md); ein Glossar aller Fachbegriffe
findet sich dort am Ende.
