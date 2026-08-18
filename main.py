import logging

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from agents.chain_agent import ChainAgent
from agents.nlp_parser import parse_query
from config import FORTYGUARD_API_KEY
from memory.session import SessionMemory
from monitor.loop import MonitorLoop
from utils.datasets import format_location_context, get_location_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

console = Console()


def build_polygon_aoi(lat: float, lon: float, size: float = 0.01) -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [lon - size, lat - size],
                            [lon + size, lat - size],
                            [lon + size, lat + size],
                            [lon - size, lat + size],
                            [lon - size, lat - size],
                        ]
                    ],
                },
            }
        ],
    }


def handle_query(query: str, session_id: str, memory: SessionMemory) -> str:
    parsed = parse_query(query)

    console.print(f"[dim]Intent: {parsed.intent} | Confidence: {parsed.confidence:.0%}[/dim]")
    console.print(f"[dim]Entities: {', '.join(parsed.entities_found)}[/dim]")
    console.print(f"[dim]Endpoints: {', '.join(parsed.endpoints_needed)}[/dim]")

    if not parsed.latitude:
        parsed.latitude = 40.7128
        parsed.longitude = -74.0060
        parsed.location = "New York (default)"

    context = get_location_context(parsed.latitude, parsed.longitude)
    console.print(format_location_context(context))

    polygon_aoi = build_polygon_aoi(parsed.latitude, parsed.longitude)

    params = {
        "latitude": parsed.latitude,
        "longitude": parsed.longitude,
        "date": parsed.date,
        "time": parsed.time,
        "filter_type": parsed.filter_type,
        "polygon_aoi": polygon_aoi,
        "temperature": 35.0,
    }

    chain_agent = ChainAgent(memory=memory)
    result = chain_agent.execute_chain(
        query=query,
        session_id=session_id,
        endpoints=parsed.endpoints_needed,
        params=params,
    )

    if result.get("reasoning"):
        table = Table(title="Reasoning Chain", show_header=True, header_style="bold cyan")
        table.add_column("Step", style="dim")
        table.add_column("Action")
        table.add_column("Endpoint", style="green")
        table.add_column("Status")
        for step in result["reasoning"]:
            status = "✓" if step["status"] == "success" else "✗"
            table.add_row(
                str(step["step"]),
                step["action"],
                step["endpoint"],
                f"{status} {step['status']}",
            )
        console.print(table)

    if result.get("api_calls"):
        console.print("[dim]API Calls Made:[/dim]")
        for call in result["api_calls"]:
            console.print(f"  [dim]{call['method']} {call['url']}[/dim]")

    return result.get("response", "No response generated.")


def interactive_mode():
    if not FORTYGUARD_API_KEY:
        console.print("[yellow]Warning: No API key set. Set FORTYGUARD_API_KEY in .env[/yellow]")
        console.print("[yellow]Running in demo mode — API calls will fail.[/yellow]\n")

    memory = SessionMemory()
    session_id = memory.create_session("cli_user")
    console.print("[green]HeatMind session started.[/green]")
    console.print("Type 'quit' to exit, 'monitor' to start monitoring.\n")

    while True:
        try:
            query = Prompt.ask("[bold blue]HeatMind>[/bold blue]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Exiting...[/yellow]")
            break

        if query.lower() in ("quit", "exit", "q"):
            break

        if query.lower() == "monitor":
            console.print("[yellow]Starting monitor loop (Ctrl+C to stop)...[/yellow]")
            loop = MonitorLoop(memory=memory)
            loop.add_zone(
                name="New York Downtown",
                polygon_aoi=build_polygon_aoi(40.7128, -74.0060),
                latitude=40.7128,
                longitude=-74.0060,
            )
            try:
                loop.start()
            except KeyboardInterrupt:
                console.print("\n[yellow]Monitor stopped.[/yellow]")
            continue

        response = handle_query(query, session_id, memory)
        console.print(f"\n{response}\n")


def main():
    console.print(
        Panel.fit(
            "[bold green]HeatMind[/bold green] — Multi-Agent Heat Intelligence System\n"
            "[dim]Powered by FortyGuard Temperature API[/dim]",
            border_style="green",
        )
    )
    interactive_mode()


if __name__ == "__main__":
    main()
