from deployment_risk_engine.models import Finding, Severity
from deployment_risk_engine.policy import evaluate


def make_finding(severity: Severity) -> Finding:
    return Finding(
        rule_id="TEST-001",
        severity=severity,
        resource="test-resource",
        message="Test finding",
        remediation="Fix the issue",
    )


def test_critical_finding_is_blocked():
    decision = evaluate(
        [make_finding(Severity.CRITICAL)],
        {Severity.CRITICAL, Severity.HIGH},
    )

    assert decision.allowed is False


def test_high_finding_is_blocked():
    decision = evaluate(
        [make_finding(Severity.HIGH)],
        {Severity.CRITICAL, Severity.HIGH},
    )

    assert decision.allowed is False


def test_medium_finding_is_allowed_when_policy_blocks_high():
    decision = evaluate(
        [make_finding(Severity.MEDIUM)],
        {Severity.CRITICAL, Severity.HIGH},
    )

    assert decision.allowed is True


def test_low_finding_is_allowed_when_policy_blocks_high():
    decision = evaluate(
        [make_finding(Severity.LOW)],
        {Severity.CRITICAL, Severity.HIGH},
    )

    assert decision.allowed is True


def test_no_findings_are_allowed():
    decision = evaluate(
        [],
        {Severity.CRITICAL, Severity.HIGH},
    )

    assert decision.allowed is True
