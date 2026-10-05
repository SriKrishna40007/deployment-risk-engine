from pathlib import Path

from deployment_risk_engine.models import Finding
from deployment_risk_engine.rules import (
    check_dockerfile_latest,
    check_dockerfile_user,
)


def scan_file(file_path: str) -> list[Finding]:
    """Scan a Dockerfile for security risks."""

    path = Path(file_path)

    lines = path.read_text(encoding="utf-8").splitlines()

    findings: list[Finding] = []

    for line in lines:
        finding = check_dockerfile_latest(line)

        if finding:
            findings.append(finding)

    user_finding = check_dockerfile_user(lines)

    if user_finding:
        findings.append(user_finding)

    return findings
