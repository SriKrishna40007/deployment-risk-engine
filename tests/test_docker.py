from deployment_risk_engine.docker import scan_file
from deployment_risk_engine.models import Severity


def test_latest_base_image_is_detected():
    findings = scan_file(
        "examples/docker/insecure/Dockerfile"
    )

    assert any(
        finding.rule_id == "DOCKER-001"
        and finding.severity == Severity.HIGH
        for finding in findings
    )


def test_missing_user_instruction_is_detected():
    findings = scan_file(
        "examples/docker/insecure/Dockerfile"
    )

    assert any(
        finding.rule_id == "DOCKER-002"
        and finding.severity == Severity.HIGH
        for finding in findings
    )


def test_secure_dockerfile_has_no_findings():
    findings = scan_file(
        "examples/docker/secure/Dockerfile"
    )

    assert findings == []


def test_insecure_dockerfile_has_two_findings():
    findings = scan_file(
        "examples/docker/insecure/Dockerfile"
    )

    assert len(findings) == 2
