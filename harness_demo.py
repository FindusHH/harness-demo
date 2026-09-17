"""
Agent Harness Demo (Microsoft Agent Framework + Foundry)
========================================================

Dieses Skript zeigt Schritt fuer Schritt, wie man mit `create_harness_agent`
einen "harnessed" Agenten baut und betreibt. Es ist als Schulungsdemo gedacht
und laesst sich in mehreren Stufen ausfuehren:

    python harness_demo.py --demo minimal      # 1. Einfachster Harness
    python harness_demo.py --demo tools        # 2. Harness mit Function Tools
    python harness_demo.py --demo observability # 3. Harness + OpenTelemetry
    python harness_demo.py --demo observability --fail-tool  # 3b. Fehlerfall (Tool wirft)
    python harness_demo.py --demo interactive  # 4. Interaktive Session-Schleife
    python harness_demo.py --demo approval     # 5. Human-in-the-Loop Tool-Approval
    python harness_demo.py --demo planning     # 6. Plan-/Execute-Modus mit Todos

Client-Auswahl ueber Umgebungsvariablen (Foundry bevorzugt, sonst OpenAI):

    Foundry:
        FOUNDRY_PROJECT_ENDPOINT = https://<resource>.services.ai.azure.com/api/projects/<project>
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
import sys
from pathlib import Path
from typing import Annotated

from agent_framework import Message, create_harness_agent, tool

# Konsole auf UTF-8 stellen, damit Modell-Antworten mit Sonderzeichen
# (z. B. schmales geschuetztes Leerzeichen \u202f) nicht die Ausgabe abbrechen
# und korrekt (statt als Mojibake) erscheinen.
if sys.platform == "win32":
    try:
        import ctypes

        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:  # noqa: BLE001 - reine Kosmetik, darf nie den Lauf stoppen
        pass
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass

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


@tool
def get_weather_unstable(
    city: Annotated[str, "Name der Stadt, z. B. 'Muenchen'"],
) -> str:
    """Wie get_weather, wirft aber absichtlich einen Fehler (fuer die Fehlerfall-Demo)."""
    raise RuntimeError(f"Wetterdienst nicht erreichbar (Simulation) fuer {city}.")


# --------------------------------------------------------------------------- #
# Demo 1: Minimaler Harness
# --------------------------------------------------------------------------- #
async def demo_minimal() -> None:
    print("== Demo 1: Minimaler Harness ==")
    agent = create_harness_agent(client=build_chat_client())

    session = agent.create_session()
    prompt = "Plane ein Wochenende in Seattle in drei Stichpunkten."
    print(f"\n>> Prompt an den Agenten:\n   \"{prompt}\"\n")
    response = await agent.run(prompt, session=session)
    print("--- Antwort des Agenten ---")
    print(response.text)


# --------------------------------------------------------------------------- #
# Demo 2: Harness mit Function Tools + getrennten Instructions
# --------------------------------------------------------------------------- #
async def demo_tools() -> None:
    print("== Demo 2: Harness mit Function Tools ==")
    harness_instructions = "Nutze Tools bewusst und berichte nur verifizierte Ergebnisse."
    agent_instructions = "Du bist ein hilfreicher Reise-Assistent."
    agent = create_harness_agent(
        client=build_chat_client(),
        name="reise-agent",
        harness_instructions=harness_instructions,
        agent_instructions=agent_instructions,
        tools=[get_weather, convert_currency],
        max_context_window_tokens=128_000,
        max_output_tokens=16_384,
    )

    session = agent.create_session()
    prompt = "Wie ist das Wetter in Amsterdam und was sind 250 Euro in USD?"
    print(f"\n>> harness_instructions: \"{harness_instructions}\"")
    print(f">> agent_instructions:   \"{agent_instructions}\"")
    print(f">> Verfuegbare Tools:    get_weather, convert_currency")
    print(f">> Prompt an den Agenten:\n   \"{prompt}\"\n")
    response = await agent.run(prompt, session=session)
    print("--- Antwort des Agenten ---")
    print(response.text)


# --------------------------------------------------------------------------- #
# Demo 3: Harness mit Observability (OpenTelemetry)
# --------------------------------------------------------------------------- #
def _classify_span(name: str) -> tuple[str, str]:
    """Ordnet einen technischen Span-Namen einer verstaendlichen Rolle + Erklaerung zu."""
    lower = (name or "").lower()
    if "invoke_agent" in lower or ("agent" in lower and "run" in lower):
        return ("AGENT-LAUF", "Der Harness nimmt deine Anfrage an und steuert den gesamten Ablauf.")
    if lower.startswith("execute_tool") or "tool" in lower:
        return ("TOOL-AUFRUF", "Der Harness ruft deine Python-Funktion auf (nicht das Sprachmodell).")
    if "chat" in lower or "completion" in lower or "response" in lower or "gen_ai" in lower:
        return ("MODELL-AUFRUF", "Der Harness schickt den Kontext ans Sprachmodell und erhaelt eine Antwort.")
    return (name or "SCHRITT", "Ein Arbeitsschritt der Harness-Pipeline.")


def _span_details(attributes: dict) -> list[str]:
    """Zieht die fuer Laien interessanten Werte aus den Span-Attributen."""
    a = dict(attributes or {})
    out: list[str] = []
    model = a.get("gen_ai.response.model") or a.get("gen_ai.request.model")
    if model:
        out.append(f"Modell: {model}")
    in_tok = a.get("gen_ai.usage.input_tokens")
    out_tok = a.get("gen_ai.usage.output_tokens")
    if in_tok is not None or out_tok is not None:
        out.append(f"Tokens (Eingabe/Ausgabe): {in_tok}/{out_tok}")
    tool = a.get("gen_ai.tool.name") or a.get("tool.name")
    if tool:
        out.append(f"Funktion: {tool}")
    args = a.get("gen_ai.tool.call.arguments") or a.get("tool.arguments")
    if args:
        out.append(f"Argumente: {args}")
    return out


def _render_harness_trace(spans: list) -> None:
    """Rendert die gesammelten Spans als verstaendlichen, verschachtelten Ablaufbaum."""
    if not spans:
        print("(Keine Ablaufdaten erfasst - OpenTelemetry-SDK evtl. nicht aktiv.)")
        return

    by_id = {s.context.span_id: s for s in spans}
    children: dict = {}
    for s in spans:
        parent_id = s.parent.span_id if s.parent else None
        # Eltern-Span ausserhalb unserer Erfassung -> als Wurzel behandeln.
        if parent_id is not None and parent_id not in by_id:
            parent_id = None
        children.setdefault(parent_id, []).append(s)
    for group in children.values():
        group.sort(key=lambda s: s.start_time)

    step_counter = {"n": 0}

    def walk(span, depth: int) -> None:
        step_counter["n"] += 1
        role, meaning = _classify_span(span.name)
        # Todo-/Plan-Tools klarer benennen (Funktionsname steht in den Attributen).
        attrs_for_role = dict(span.attributes or {})
        tool_name = attrs_for_role.get("gen_ai.tool.name") or attrs_for_role.get("tool.name") or ""
        if role == "TOOL-AUFRUF" and str(tool_name).startswith("todos"):
            role = "PLAN/TODO"
            meaning = "Der Harness verwaltet die Todo-Liste (Plan anlegen bzw. abhaken)."
        duration_ms = (span.end_time - span.start_time) / 1_000_000
        indent = "    " * depth
        connector = "" if depth == 0 else "└─ "

        # Status ermitteln: OK, oder blockiert/fehlgeschlagen.
        status = getattr(span, "status", None)
        status_name = getattr(getattr(status, "status_code", None), "name", "") or ""
        blocked = status_name == "ERROR"
        marker = "  [!! BLOCKIERT/FEHLER]" if blocked else ""

        print(f"{indent}{connector}Schritt {step_counter['n']}: [{role}]  ({duration_ms:.0f} ms){marker}")
        print(f"{indent}    Was passiert: {meaning}")
        for detail in _span_details(span.attributes):
            print(f"{indent}    - {detail}")

        # Fehlerursache sichtbar machen (Status-Text + aufgezeichnete Ausnahmen).
        if blocked:
            desc = getattr(status, "description", None)
            if desc:
                print(f"{indent}    !! Grund: {desc}")
        for event in getattr(span, "events", None) or []:
            if event.name == "exception":
                attrs = dict(event.attributes or {})
                etype = attrs.get("exception.type", "Exception")
                emsg = attrs.get("exception.message", "")
                print(f"{indent}    !! Ausnahme: {etype}: {emsg}")

        for child in children.get(span.context.span_id, []):
            walk(child, depth + 1)

    for root in children.get(None, []):
        walk(root, 0)


def _setup_span_capture():
    """Konfiguriert OpenTelemetry mit einem In-Memory-Exporter fuer die Ablauf-Analyse.

    Rueckgabe: (exporter, trace_modul) oder (None, None), falls das OTel-SDK fehlt.
    Wichtig: Ohne uebergebenen Exporter legt configure_otel_providers keinen
    TracerProvider an - dann wuerden keine Spans aufgezeichnet.
    """
    from agent_framework.observability import configure_otel_providers

    # Den rohen JSON-Konsolen-Export unterdruecken - wir rendern selbst lesbar.
    os.environ.pop("ENABLE_CONSOLE_EXPORTERS", None)
    try:
        from opentelemetry import trace as _otel_trace
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
            InMemorySpanExporter,
        )

        exporter = InMemorySpanExporter()
        configure_otel_providers(exporters=[exporter])
        return exporter, _otel_trace
    except ImportError:
        configure_otel_providers()
        return None, None


def _collect_spans(exporter, otel_trace) -> list:
    """Liest die aufgezeichneten Spans aus dem In-Memory-Exporter aus."""
    if exporter is None:
        return []
    provider = otel_trace.get_tracer_provider()
    if hasattr(provider, "force_flush"):
        provider.force_flush()
    return list(exporter.get_finished_spans())


def _print_todo_list(session) -> None:
    """Zeigt die Todo-Liste, die der Harness in der Session gefuehrt hat."""
    state = getattr(session, "state", None)
    todo_state = state.get("todo") if isinstance(state, dict) else None
    items = todo_state.get("items") if isinstance(todo_state, dict) else None
    print("\n--- Vom Harness aus deinem Prompt gefuehrte Todo-Liste ---")
    if not items:
        print("(Keine Todos - die Aufgabe war einfach genug fuer einen direkten Schritt.)")
        return
    done = sum(1 for it in items if it.get("is_complete"))
    print(f"{done}/{len(items)} erledigt:")
    for it in items:
        mark = "[x]" if it.get("is_complete") else "[ ]"
        print(f"  {mark} {it.get('title', '?')}")
        desc = it.get("description")
        if desc:
            print(f"        {desc}")


async def demo_observability(fail_tool: bool = False) -> None:
    print("== Demo 3: Harness mit Observability ==")
    print(
        "\nZiel dieser Demo: sichtbar machen, WAS der Harness intern tut. Jeder Arbeits-\n"
        "schritt (Agent-Lauf, Modell-Aufruf, Tool-Aufruf) wird als 'Span' aufgezeichnet.\n"
        "Unten siehst du diese Schritte NICHT als Roh-JSON, sondern als lesbaren Ablauf-\n"
        "baum. Die Einrueckung zeigt die Verschachtelung: Was eingerueckt steht, laeuft\n"
        "INNERHALB des darueberstehenden Schritts - genau das ist das 'Harnessing'.\n"
    )
    if fail_tool:
        print(
            ">> FEHLERFALL-MODUS (--fail-tool): Das Wetter-Tool wirft absichtlich eine\n"
            "   Ausnahme. Achte im Ablaufbaum auf den Schritt mit [!! BLOCKIERT/FEHLER].\n"
        )

    exporter, otel_trace = _setup_span_capture()

    agent = create_harness_agent(
        client=build_chat_client(),
        otel_provider_name="schulung.harness.demo",
        tools=[get_weather_unstable if fail_tool else get_weather],
    )

    session = agent.create_session()
    prompt = "Wie ist das Wetter in Muenchen?"
    tool_name = "get_weather_unstable" if fail_tool else "get_weather"
    print(f">> Verfuegbares Tool:     {tool_name}")
    print(f">> Prompt an den Agenten:\n   \"{prompt}\"\n")
    # Im Fehlerfall kann agent.run eine Ausnahme werfen - trotzdem wollen wir den
    # Ablaufbaum (inkl. blockiertem Schritt) rendern, daher geschuetzt ausfuehren.
    response = None
    run_error: Exception | None = None
    try:
        response = await agent.run(prompt, session=session)
    except Exception as ex:  # noqa: BLE001 - Demo soll den Fehler zeigen, nicht abstuerzen
        run_error = ex

    print("--- Antwort des Agenten ---")
    if response is not None:
        print(response.text)
    else:
        print("(Keine Antwort - der Lauf wurde durch einen Fehler abgebrochen.)")

    print("\n--- Was der Harness dafuer getan hat (Ablaufbaum) ---")
    _render_harness_trace(_collect_spans(exporter, otel_trace))

    if run_error is not None:
        print(
            f"\n>> BLOCKIERT: Der Lauf endete mit einer Ausnahme: "
            f"{type(run_error).__name__}: {run_error}\n"
        )

    # Zweiter Blockade-Typ: der Harness pausiert absichtlich und wartet auf Freigabe.
    if getattr(response, "user_input_requests", None):
        print(
            "\n>> HINWEIS: Der Harness ist BLOCKIERT und wartet auf eine menschliche\n"
            "   Freigabe (Human-in-the-Loop). Erkennbar an response.user_input_requests.\n"
            "   Siehe Demo 5 (--demo approval) fuer diesen Fall.\n"
        )

    print(
        "\n--- Fazit ---\n"
        "Ein blanker LLM-Aufruf waere nur EIN Schritt gewesen. Hier siehst du mehrere,\n"
        "ineinander verschachtelte Schritte: Der AGENT-LAUF umschliesst den MODELL-AUFRUF\n"
        "und den TOOL-AUFRUF (get_weather). Diese Koordination - Kontext aufbauen, Modell\n"
        "fragen, passendes Tool ausfuehren, Ergebnis einbauen - ist die Arbeit des Harness.\n"
        "\n"
        "Blockaden erkennst du so:\n"
        "  * [!! BLOCKIERT/FEHLER] am Schritt = ein Span mit Fehlerstatus (z. B. 403 RBAC,\n"
        "    Rate-Limit, Tool-Ausnahme). Grund/Ausnahme stehen direkt darunter.\n"
        "  * response.user_input_requests gesetzt = der Harness pausiert und wartet auf\n"
        "    eine Freigabe (gewollte Blockade, Human-in-the-Loop).\n"
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
    print(
        "Hier bist DU der Prompt-Geber: Jede Eingabe an 'Du >' ist der Ausloeser.\n"
        "Der Harness haelt Verlauf/Kontext, du kannst also Rueckbezuege nutzen\n"
        "(z. B. erst 'Wetter in Muenchen?', dann 'Und 100 Euro dort in CHF?').\n"
        "Leere Eingabe oder 'exit' beendet die Demo.\n"
    )

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
    agent_instructions = (
        "Du bist ein Reise-Assistent. Wenn der Nutzer eine Buchung wuenscht, rufe direkt "
        "das Tool book_hotel mit Stadt und Anzahl der Naechte auf. Stelle KEINE Rueckfragen "
        "- die Freigabe holt das System selbst ein."
    )
    agent = create_harness_agent(
        client=build_chat_client(),
        agent_instructions=agent_instructions,
        tools=[book_hotel],
    )

    # Die Approval-Middleware benoetigt dieselbe Session ueber alle Runden.
    session = agent.create_session()
    query = "Buche das Hotel in Muenchen fuer 3 Naechte."
    print(f"\n>> agent_instructions:   \"...rufe direkt das Tool book_hotel auf, keine Rueckfragen...\"")
    print(f">> Tool (freigabepflichtig): book_hotel (approval_mode='always_require')")
    print(f">> Prompt an den Agenten:\n   \"{query}\"\n")
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

            # Nur die Freigabe-Antwort zuruecksenden. Der Harness hat die urspruengliche
            # Anfrage in der Session gespeichert und bindet die Antwort selbst daran -
            # die Anfrage erneut mitzusenden wuerde den Function-Call doppeln
            # (Foundry-Responses-API: "No tool output found for function call").
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
    print(
        "\nZiel dieser Demo: zeigen, wie der Harness auf DEINEN Prompt reagiert. Bei einer\n"
        "komplexen, mehrstufigen Aufgabe zerlegt der Harness sie in eine Todo-Liste, arbeitet\n"
        "die Punkte anhand der LLM-Antworten ab und hakt sie ab. Unten siehst du dreierlei:\n"
        "  1) die Antwort des Agenten,\n"
        "  2) die Todo-Liste, die der Harness AUS DEINEM PROMPT gebaut hat,\n"
        "  3) den Ablaufbaum - dort tauchen [PLAN/TODO]-Schritte auf, weil das LLM in seiner\n"
        "     Antwort entscheidet, Todos anzulegen bzw. abzuhaken.\n"
    )
    # Todo-Tracking und Plan/Execute-Modi sind im Harness standardmaessig aktiv.
    exporter, otel_trace = _setup_span_capture()

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
    print(f">> agent_instructions:   \"Du bist ein Reiseplaner. Zerlege komplexe Aufgaben in Todos ...\"")
    print(f">> Verfuegbare Tools:    get_weather, convert_currency")
    print(f">> Prompt an den Agenten:\n   \"{task}\"\n")
    response = await agent.run(task, session=session)

    print("--- Antwort des Agenten ---")
    print(response.text)

    _print_todo_list(session)

    print("\n--- Was der Harness dafuer getan hat (Ablaufbaum) ---")
    _render_harness_trace(_collect_spans(exporter, otel_trace))

    print(
        "\n--- Fazit ---\n"
        "Der EINE Prompt hat den Harness zu einem ganzen Ablauf veranlasst: Er hat die\n"
        "Aufgabe in Todos zerlegt (sichtbar in der Liste oben und als [PLAN/TODO]-Schritte),\n"
        "pro Todo das passende Tool aufgerufen (Wetter, Waehrung) und die Ergebnisse zu einer\n"
        "Antwort zusammengefuehrt. Prompt-Komplexitaet -> mehr Harness-Aktivitaet: genau das\n"
        "ist der sichtbare Effekt des Harnessing.\n"
    )


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
    parser.add_argument(
        "--fail-tool",
        action="store_true",
        help="Nur fuer --demo observability: laesst das Tool absichtlich scheitern, "
        "um die [!! BLOCKIERT/FEHLER]-Ausgabe zu demonstrieren.",
    )
    args = parser.parse_args()
    if args.demo == "observability":
        asyncio.run(demo_observability(fail_tool=args.fail_tool))
    else:
        asyncio.run(DEMOS[args.demo]())


if __name__ == "__main__":
    main()
