from deployment_risk_engine.models import Finding, Severity
from deployment_risk_engine.risk import calculate_score


def test_empty_findings_have_zero_risk():
    assert calculate_score([]) == 0


def test_critical_finding_has_high_risk():
    finding = Finding(
        rule_id="KUBE-001",
        severity=Severity.CRITICAL,
        resource="test",
        message="Privileged container",
        remediation="Disable privileged mode",
    )

    assert calculate_score([finding]) == 40


def test_multiple_high_findings_accumulate():
    findings = [
        Finding(
            rule_id="DOCKER-001",
            severity=Severity.HIGH,
            resource="Dockerfile",
            message="Uses latest tag",
            remediation="Pin image",
        ),
        Finding(
            rule_id="DOCKER-002",
            severity=Severity.HIGH,
            resource="Dockerfile",
            message="Runs as root",
            remediation="Use non-root user",
        ),
    ]

    assert calculate_score(findings) == 50
