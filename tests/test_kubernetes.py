from pathlib import Path

from deployment_risk_engine.kubernetes import scan_file
from deployment_risk_engine.models import Severity


def test_privileged_container_is_detected():
    findings = scan_file(
        "examples/insecure/deployment.yaml"
    )

    assert any(
        finding.rule_id == "KUBE-001"
        and finding.severity == Severity.CRITICAL
        for finding in findings
    )


def test_latest_image_is_detected():
    findings = scan_file(
        "examples/insecure/deployment.yaml"
    )

    assert any(
        finding.rule_id == "KUBE-002"
        and finding.severity == Severity.HIGH
        for finding in findings
    )


def test_privilege_escalation_is_detected():
    findings = scan_file(
        "examples/insecure/privilege-escalation.yaml"
    )

    assert any(
        finding.rule_id == "KUBE-003"
        for finding in findings
    )


def test_run_as_non_root_false_is_detected():
    findings = scan_file(
        "examples/insecure/root-container.yaml"
    )

    assert any(
        finding.rule_id == "KUBE-004"
        for finding in findings
    )


def test_host_network_is_detected():
    findings = scan_file(
        "examples/insecure/host-network.yaml"
    )

    assert any(
        finding.rule_id == "KUBE-005"
        for finding in findings
    )


def test_host_pid_is_detected():
    findings = scan_file(
        "examples/insecure/host-pid.yaml"
    )

    assert any(
        finding.rule_id == "KUBE-006"
        for finding in findings
    )


def test_host_ipc_is_detected():
    findings = scan_file(
        "examples/insecure/host-ipc.yaml"
    )

    assert any(
        finding.rule_id == "KUBE-006"
        for finding in findings
    )


def test_dangerous_capability_is_detected():
    findings = scan_file(
        "examples/insecure/dangerous-capabilities.yaml"
    )

    assert any(
        finding.rule_id == "KUBE-007"
        for finding in findings
    )


def test_secure_deployment_has_no_findings():
    findings = scan_file(
        "examples/secure/deployment.yaml"
    )

    assert findings == []


def test_multi_container_deployment_is_scanned():
    findings = scan_file(
        "examples/insecure/multi-container.yaml"
    )

    assert len(findings) == 3


def test_multi_document_manifest_is_scanned():
    findings = scan_file(
        "examples/insecure/multi-document.yaml"
    )

    assert len(findings) == 2
