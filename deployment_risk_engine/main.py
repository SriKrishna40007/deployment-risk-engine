from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from deployment_risk_engine.docker import scan_file as scan_docker
from deployment_risk_engine.kubernetes import scan_file as scan_kubernetes
from deployment_risk_engine.policy import evaluate, load_policy
from deployment_risk_engine.risk import calculate_score

app = typer.Typer(
    name="dre",
    help="Deployment Risk Engine - security checks before deployment.",
)

console = Console()


@app.command()
def version() -> None:
    """Display the current version."""
    console.print("Deployment Risk Engine v0.1.0")


def display_results(findings) -> None:
    console.print(
        Panel.fit(
            "Deployment Risk Engine",
            title="DRE",
            border_style="blue",
        )
    )

    if findings:
        for finding in findings:
            console.print(
                f"\n[red]{finding.severity.value}[/red] "
                f"{finding.rule_id}"
            )
            console.print(f"Resource: {finding.resource}")
            console.print(f"Finding: {finding.message}")
            console.print(f"Remediation: {finding.remediation}")

    risk_score = calculate_score(findings)
    blocked_severities = load_policy("policies/default.yaml")
    decision = evaluate(findings, blocked_severities)

    console.print(f"\nRisk Score: {risk_score}/100")

    if decision.allowed:
        console.print("[green]Deployment ALLOWED[/green]")
        console.print(f"Reason: {decision.reason}")
        raise typer.Exit(code=0)

    console.print("[red]Deployment BLOCKED[/red]")
    console.print(f"Reason: {decision.reason}")
    raise typer.Exit(code=1)


@app.command()
def k8s(file: Path) -> None:
    """Scan a Kubernetes manifest."""
    if not file.is_file():
        console.print(f"[red]File not found:[/red] {file}")
        raise typer.Exit(code=2)

    display_results(scan_kubernetes(str(file)))


@app.command()
def docker(file: Path) -> None:
    """Scan a Dockerfile."""
    if not file.is_file():
        console.print(f"[red]File not found:[/red] {file}")
        raise typer.Exit(code=2)

    display_results(scan_docker(str(file)))


if __name__ == "__main__":
    app()
