from deployment_risk_engine.models import Finding, Severity


SEVERITY_SCORES = {
    Severity.CRITICAL: 40,
    Severity.HIGH: 25,
    Severity.MEDIUM: 10,
    Severity.LOW: 3,
}


def calculate_score(findings: list[Finding]) -> int:
    """Calculate a bounded deployment risk score from 0 to 100."""

    score = sum(SEVERITY_SCORES[finding.severity] for finding in findings)

    return min(score, 100)
