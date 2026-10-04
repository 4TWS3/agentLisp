"""Command Line Interface for Agent Lisp Runtime."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import structlog
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .engine import AgentEngine
from .loader import AgentLoader

app = typer.Typer(
    name="agentlisp",
    help="Agent Lisp Runtime - Execute Scheme-defined agent workflows",
    no_args_is_help=True,
)
console = Console()
logger = structlog.get_logger()


@app.command("validate")
def validate(
    agent_file: Path = typer.Argument(..., exists=True, readable=True, help="Agent definition file"),
    format: str = typer.Option("json", "--format", "-f", help="Input format: json|yaml|scheme"),
) -> None:
    """Validate an agent definition file."""
    try:
        agent = _load_agent(agent_file, format)
        console.print(
            Panel.fit(
                f"[bold green]✓ Agent '{agent.name}' is valid[/bold green]\n"
                f"Purpose: {agent.purpose or '(none)'}\n"
                f"Tools: {len(agent.tools)}\n"
                f"Workflows: {len(agent.workflows)}",
                title="Validation Result",
                border_style="green",
            )
        )
        if agent.workflows:
            table = Table(title="Workflows")
            table.add_column("Name")
            table.add_column("Steps")
            table.add_column("Triggers")
            for wf in agent.workflows:
                table.add_row(wf.name, str(len(wf.steps)), ", ".join(wf.triggers) or "-")
            console.print(table)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[bold red]✗ Validation failed:[/bold red] {exc}")
        raise typer.Exit(code=1)


@app.command("run")
def run_workflow(
    agent_file: Path = typer.Argument(..., exists=True, readable=True, help="Agent definition file"),
    workflow: str = typer.Argument(..., help="Workflow name to execute"),
    format: str = typer.Option("json", "--format", "-f", help="Input format: json|yaml|scheme"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Write result to file"),
) -> None:
    """Execute a workflow defined in the agent file."""
    import asyncio

    async def _run() -> None:
        agent = _load_agent(agent_file, format)
        engine = AgentEngine(agent)
        result = await engine.run_workflow(workflow)
        result_dict = result.model_dump(mode="json")

        result_text = json.dumps(result_dict, indent=2, ensure_ascii=False, default=str)

        if output:
            output.write_text(result_text, encoding="utf-8")
            console.print(f"[green]Result written to {output}[/green]")
        else:
            console.print_json(result_text)

        if not result.success:
            raise typer.Exit(code=2)

    asyncio.run(_run())


@app.command("export")
def export(
    scheme_file: Path = typer.Argument(..., exists=True, readable=True, help="Scheme .rkt file"),
    output: Path = typer.Option(Path("agent.json"), "--output", "-o", help="Output JSON file"),
    racket_exe: str = typer.Option("racket", "--racket", help="Racket executable path"),
) -> None:
    """Export a Scheme agent definition to JSON."""
    try:
        agent = AgentLoader.from_scheme(scheme_file, racket_exe=racket_exe)
        output.write_text(
            agent.model_dump_json(indent=2),
            encoding="utf-8",
        )
        console.print(
            f"[bold green]✓ Exported agent '{agent.name}' to {output}[/bold green]"
        )
    except Exception as exc:  # noqa: BLE001
        console.print(f"[bold red]✗ Export failed:[/bold red] {exc}")
        raise typer.Exit(code=1)


def _load_agent(path: Path, fmt: str):
    fmt = fmt.lower()
    if fmt == "json":
        return AgentLoader.from_json(path)
    if fmt in {"yaml", "yml"}:
        return AgentLoader.from_yaml(path)
    if fmt in {"scheme", "racket", "rkt"}:
        return AgentLoader.from_scheme(path)
    raise typer.BadParameter(f"Unsupported format: {fmt}")


if __name__ == "__main__":
    app()
