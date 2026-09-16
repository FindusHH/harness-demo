"""
Agent Harness Demo (Microsoft Agent Framework + Foundry)
========================================================

Dieses Skript zeigt Schritt fuer Schritt, wie man mit `create_harness_agent`
einen "harnessed" Agenten baut und betreibt. Es ist als Schulungsdemo gedacht
und laesst sich in mehreren Stufen ausfuehren:

    python harness_demo.py --demo minimal      # 1. Einfachster Harness
    python harness_demo.py --demo tools        # 2. Harness mit Function Tools
    python harness_demo.py --demo observability # 3. Harness + OpenTelemetry
    python harness_demo.py --demo interactive  # 4. Interaktive Session-Schleife
    python harness_demo.py --demo approval     # 5. Human-in-the-Loop Tool-Approval
    python harness_demo.py --demo planning     # 6. Plan-/Execute-Modus mit Todos

Client-Auswahl ueber Umgebungsvariablen (Foundry bevorzugt, sonst OpenAI):

    Foundry:
        FOUNDRY_PROJECT_ENDPOINT = https://<resource>.ai.azure.com/api/projects/<project>
        FOUNDRY_MODEL            = z. B. gpt-4o  (optional, Default gpt-4o)
        -> vorher: az login
        -> RBAC: Die angemeldete Identitaet braucht auf DIESER Foundry-Ressource
           die Rolle "Azure AI Developer" (Recht ...accounts/AIServices/agents/write).
           Ohne diese Rolle bricht der Harness mit HTTP 403 (UserError) ab.
           Siehe https://learn.microsoft.com/azure/foundry/concepts/rbac-foundry

    OpenAI (Fallback fuer lokale Demos):
        OPENAI_API_KEY = sk-...
        OPENAI_MODEL   = z. B. gpt-4o (optional)

Doku:
    Agent Harness (Konzept):  https://learn.microsoft.com/agent-framework/concepts/harness
    Getting Started, Step 6:  https://learn.microsoft.com/agent-framework/get-started/harness
    Function Tools:           https://learn.microsoft.com/agent-framework/agents/tools/function-tools
    Observability:            https://learn.microsoft.com/agent-framework/agents/observability
    Tool Approval (HITL):     https://learn.microsoft.com/agent-framework/agents/tools/tool-approval
    Planning und Todos:       https://learn.microsoft.com/agent-framework/agents/planning-and-todos
    Responses API (Foundry):  https://learn.microsoft.com/azure/foundry/agents/quickstarts/responses-api
"""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
from typing import Annotated

from agent_framework import Message, create_harness_agent, tool

try:
    from dotenv import load_dotenv

    # .env neben diesem Skript laden, unabhaengig vom aktuellen Arbeitsverzeichnis.
    load_dotenv(Path(__file__).with_name(".env"))
except ImportError:
    pass

# --------------------------------------------------------------------------- #
# 1. Chat-Client auswaehlen (Foundry bevorzugt, sonst OpenAI)
# --------------------------------------------------------------------------- #
def build_chat_client():
    """Erzeugt einen Chat-Client abhaengig von den gesetzten Umgebungsvariablen.

    Rueckgabe ist ein Client, den der Harness umschliesst. Der Harness selbst
    ist client-agnostisch - dieselbe Harness-Konfiguration funktioniert mit
    Foundry, Azure OpenAI oder OpenAI.
    """
    foundry_endpoint = os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
    if foundry_endpoint:
        # Foundry-Projekt-Endpoint ueber die Responses API.
        from agent_framework.foundry import FoundryChatClient
        from azure.identity import AzureCliCredential

        return FoundryChatClient(
            project_endpoint=foundry_endpoint,
            model=os.environ.get("FOUNDRY_MODEL", "gpt-4o"),
            credential=AzureCliCredential(),
        )

    if os.environ.get("OPENAI_API_KEY"):
        from agent_framework.openai import OpenAIChatClient

        return OpenAIChatClient(model=os.environ.get("OPENAI_MODEL", "gpt-4o"))

    raise SystemExit(
        "Kein Client konfiguriert.\n"
        "Setze entweder FOUNDRY_PROJECT_ENDPOINT (+ az login) "
        "oder OPENAI_API_KEY."
    )


# --------------------------------------------------------------------------- #
# 2. Function Tools (werden vom Harness automatisch aufgerufen)
# --------------------------------------------------------------------------- #
@tool
def get_weather(
    city: Annotated[str, "Name der Stadt, z. B. 'Amsterdam'"],
) -> str:
    """Gibt eine (simulierte) Wettervorhersage fuer eine Stadt zurueck."""
    fake_forecast = {
        "amsterdam": "bewoelkt, 18 Grad",
        "seattle": "Regen, 14 Grad",
        "muenchen": "sonnig, 24 Grad",
    }
    return fake_forecast.get(city.strip().lower(), f"Keine Daten fuer {city}.")


@tool
def convert_currency(
    amount: Annotated[float, "Betrag in Euro"],
    target: Annotated[str, "Zielwaehrung, z. B. 'USD'"],
) -> str:
    """Rechnet einen Euro-Betrag in eine Zielwaehrung um (simulierte Kurse)."""
    rates = {"usd": 1.08, "gbp": 0.85, "chf": 0.95}
    rate = rates.get(target.strip().lower())
    if rate is None:
        return f"Kein Kurs fuer {target} hinterlegt."
    return f"{amount:.2f} EUR = {amount * rate:.2f} {target.upper()}"


@tool(approval_mode="always_require")
def book_hotel(
    city: Annotated[str, "Stadt fuer die Buchung"],
    nights: Annotated[int, "Anzahl der Naechte"],
) -> str:
    """Bucht ein Hotel (folgenreiche Aktion, erfordert menschliche Freigabe)."""
    return f"Hotel in {city} fuer {nights} Naechte gebucht. Buchungsnr.: DEMO-{abs(hash((city, nights))) % 10000:04d}"


# --------------------------------------------------------------------------- #
# Demo 1: Minimaler Harness
# --------------------------------------------------------------------------- #
async def demo_minimal() -> None:
    print("== Demo 1: Minimaler Harness ==")
    agent = create_harness_agent(client=build_chat_client())

    session = agent.create_session()
    response = await agent.run(
        "Plane ein Wochenende in Seattle in drei Stichpunkten.",
        session=session,
    )
    print(response.text)


# --------------------------------------------------------------------------- #
# Demo 2: Harness mit Function Tools + getrennten Instructions
# --------------------------------------------------------------------------- #
async def demo_tools() -> None:
    print("== Demo 2: Harness mit Function Tools ==")
    agent = create_harness_agent(
        client=build_chat_client(),
        name="reise-agent",
        harness_instructions="Nutze Tools bewusst und berichte nur verifizierte Ergebnisse.",
        agent_instructions="Du bist ein hilfreicher Reise-Assistent.",
        tools=[get_weather, convert_currency],
        max_context_window_tokens=128_000,
        max_output_tokens=16_384,
    )

    session = agent.create_session()
    response = await agent.run(
        "Wie ist das Wetter in Amsterdam und was sind 250 Euro in USD?",
        session=session,
    )
    print(response.text)


# --------------------------------------------------------------------------- #
# Demo 3: Harness mit Observability (OpenTelemetry)
# --------------------------------------------------------------------------- #
async def demo_observability() -> None:
    print("== Demo 3: Harness mit Observability ==")
    from agent_framework.observability import configure_otel_providers

    # Ohne gesetzten OTEL_EXPORTER_OTLP_ENDPOINT werden nur die
    # Standard-Provider konfiguriert. Setze ENABLE_CONSOLE_EXPORTERS=true,
    # um Traces direkt in der Konsole zu sehen.
    configure_otel_providers()

    console_traces = os.environ.get("ENABLE_CONSOLE_EXPORTERS", "").lower() in {"1", "true", "yes"}
    if console_traces:
        print(
            "\nHinweis: ENABLE_CONSOLE_EXPORTERS ist aktiv - gleich erscheinen\n"
            "OpenTelemetry-SPANS als JSON-Bloecke in der Konsole. So liest du sie:\n"
            "  * 'name'          = welcher Schritt (z. B. 'invoke_agent <name>',\n"
            "                      'chat' fuer den LLM-Aufruf, 'execute_tool get_weather').\n"
            "  * parent/trace_id = verschachtelte Struktur: der Tool-Span liegt INNERHALB\n"
            "                      des Agent-Spans -> Beweis, dass der Harness orchestriert.\n"
            "  * 'attributes'    = Details wie Modellname, Token-Zahlen, Tool-Argumente.\n"
            "  * start/end time  = Dauer jedes Schritts.\n"
            "Jeder Span = ein Arbeitsschritt der Harness-Pipeline, nicht nur ein LLM-Call.\n"
        )

    agent = create_harness_agent(
        client=build_chat_client(),
        otel_provider_name="schulung.harness.demo",
        tools=[get_weather],
    )

    session = agent.create_session()
    response = await agent.run(
        "Wie ist das Wetter in Muenchen?",
        session=session,
    )
    print("\n--- Antwort des Agenten ---")
    print(response.text)
    if console_traces:
        print(
            "\n--- Deutung ---\n"
            "Oben siehst du die Span-Baeume: der Tool-Span 'execute_tool get_weather'\n"
            "haengt unter dem Agent-Span. Genau diese Verschachtelung macht das\n"
            "'Harnessing' sichtbar - der Harness ruft Modell und Tool koordiniert auf.\n"
        )
    else:
        print(
            "(Traces werden ueber den konfigurierten OTLP-Exporter emittiert. "
            "Setze ENABLE_CONSOLE_EXPORTERS=true, um sie hier in der Konsole zu sehen.)"
        )


# --------------------------------------------------------------------------- #
# Demo 4: Interaktive Session-Schleife (Harness haelt Plan/Todos/History)
# --------------------------------------------------------------------------- #
async def demo_interactive() -> None:
    print("== Demo 4: Interaktive Session (Ctrl+C zum Beenden) ==")
    agent = create_harness_agent(
        client=build_chat_client(),
        agent_instructions="Du bist ein hilfreicher Assistent fuer eine Schulung.",
        tools=[get_weather, convert_currency],
    )

    session = agent.create_session()
    print("Stelle Fragen. Leere Eingabe oder 'exit' beendet die Demo.\n")

    while True:
        try:
            user_input = input("Du > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBeendet.")
            break

        if not user_input or user_input.lower() in {"exit", "quit"}:
            print("Beendet.")
            break

        response = await agent.run(user_input, session=session)
        print(f"Agent > {response.text}\n")


# --------------------------------------------------------------------------- #
# Demo 5: Human-in-the-Loop Tool-Approval
# --------------------------------------------------------------------------- #
async def demo_approval() -> None:
    print("== Demo 5: Human-in-the-Loop Tool-Approval ==")
    agent = create_harness_agent(
        client=build_chat_client(),
        agent_instructions="Du bist ein Reise-Assistent. Buche nur nach Freigabe.",
        tools=[book_hotel],
    )

    # Die Approval-Middleware benoetigt dieselbe Session ueber alle Runden.
    session = agent.create_session()
    query = "Buche mir ein Hotel in Muenchen fuer 3 Naechte."
    current_input: str | list = query

    while True:
        result = await agent.run(current_input, session=session)

        if not result.user_input_requests:
            print(f"Agent > {result.text}")
            break

        new_inputs: list = []
        for request in result.user_input_requests:
            if request.function_call is None:
                continue
            print(f"\n[Freigabe erforderlich] Tool: {request.function_call.name}")
            print(f"                        Argumente: {request.function_call.arguments}")

            answer = input("Freigeben? [j/N] > ").strip().lower()
            approved = answer in {"j", "ja", "y", "yes"}
            print("-> genehmigt" if approved else "-> abgelehnt")

            new_inputs.append(Message(role="assistant", contents=[request]))
            new_inputs.append(
                Message(
                    role="user",
                    contents=[request.to_function_approval_response(approved)],
                )
            )

        current_input = new_inputs


# --------------------------------------------------------------------------- #
# Demo 6: Plan-/Execute-Modus mit Todos
# --------------------------------------------------------------------------- #
async def demo_planning() -> None:
    print("== Demo 6: Plan-/Execute-Modus mit Todos ==")
    # Todo-Tracking und Plan/Execute-Modi sind im Harness standardmaessig aktiv.
    agent = create_harness_agent(
        client=build_chat_client(),
        agent_instructions=(
            "Du bist ein Reiseplaner. Zerlege komplexe Aufgaben in Todos, "
            "arbeite sie ab und nutze die verfuegbaren Tools."
        ),
        tools=[get_weather, convert_currency],
    )

    session = agent.create_session()
    task = (
        "Plane einen Tagesausflug: Pruefe das Wetter in Muenchen, schlage je nach "
        "Wetter eine Aktivitaet vor und rechne ein Budget von 150 Euro in CHF um. "
        "Fasse das Ergebnis als kurze Liste zusammen."
    )
    response = await agent.run(task, session=session)
    print(response.text)


DEMOS = {
    "minimal": demo_minimal,
    "tools": demo_tools,
    "observability": demo_observability,
    "interactive": demo_interactive,
    "approval": demo_approval,
    "planning": demo_planning,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent Harness Schulungsdemo")
    parser.add_argument(
        "--demo",
        choices=list(DEMOS),
        default="minimal",
        help="Welche Demo ausgefuehrt werden soll (Default: minimal).",
    )
    args = parser.parse_args()
    asyncio.run(DEMOS[args.demo]())


if __name__ == "__main__":
    main()
