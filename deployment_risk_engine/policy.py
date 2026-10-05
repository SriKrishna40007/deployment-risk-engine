from pathlib import Path
from dataclasses import dataclass

import yaml

from deployment_risk_engine.models import Finding, Severity


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str


def load_policy(file_path: str) -> set[Severity]:
    """Load blocked severities from a policy file."""

    path = Path(file_path)

    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    blocked = config.get("policy", {}).get("block_on", [])

    return {Severity(severity) for severity in blocked}


def evaluate(
    findings: list[Finding],
    blocked_severities: set[Severity],
) -> PolicyDecision:
    """Evaluate findings against the configured policy."""

    for finding in findings:
        if finding.severity in blocked_severities:
            return PolicyDecision(
                allowed=False,
                reason=(
                    f"{finding.rule_id} ({finding.severity.value}) "
                    "matches the deployment policy."
                ),
            )

    return PolicyDecision(
        allowed=True,
        reason="No findings violated the deployment policy.",
    )
