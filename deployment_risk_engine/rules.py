from typing import Any

from deployment_risk_engine.models import Finding, Severity


def check_privileged_container(
    container: dict[str, Any],
    resource_name: str,
) -> Finding | None:
    security_context = container.get("securityContext", {})

    if security_context.get("privileged") is True:
        return Finding(
            rule_id="KUBE-001",
            severity=Severity.CRITICAL,
            resource=resource_name,
            message="Privileged container detected",
            remediation="Set securityContext.privileged to false.",
        )

    return None


def check_latest_image(
    image: str,
    resource_name: str,
) -> Finding | None:
    if image.endswith(":latest"):
        return Finding(
            rule_id="KUBE-002",
            severity=Severity.HIGH,
            resource=resource_name,
            message="Container uses the mutable :latest image tag",
            remediation="Pin the image to a specific version or digest.",
        )

    return None


def check_dockerfile_latest(
    line: str,
) -> Finding | None:
    instruction = line.strip()

    if instruction.upper().startswith("FROM ") and ":latest" in instruction:
        return Finding(
            rule_id="DOCKER-001",
            severity=Severity.HIGH,
            resource="Dockerfile",
            message="Base image uses the mutable :latest tag",
            remediation="Pin the base image to a specific version or digest.",
        )

    return None


def check_dockerfile_user(
    lines: list[str],
) -> Finding | None:
    has_user_instruction = any(
        line.strip().upper().startswith("USER ")
        for line in lines
    )

    if not has_user_instruction:
        return Finding(
            rule_id="DOCKER-002",
            severity=Severity.HIGH,
            resource="Dockerfile",
            message="No USER instruction found; container may run as root",
            remediation="Create a non-root user and switch to it with USER.",
        )

    return None


def check_allow_privilege_escalation(
    container: dict[str, Any],
    resource_name: str,
) -> Finding | None:
    security_context = container.get("securityContext", {})

    if security_context.get("allowPrivilegeEscalation") is True:
        return Finding(
            rule_id="KUBE-003",
            severity=Severity.HIGH,
            resource=resource_name,
            message="Privilege escalation is explicitly allowed",
            remediation=(
                "Set securityContext.allowPrivilegeEscalation to false."
            ),
        )

    return None


def check_run_as_non_root(
    container: dict[str, Any],
    resource_name: str,
) -> Finding | None:
    security_context = container.get("securityContext", {})

    if security_context.get("runAsNonRoot") is False:
        return Finding(
            rule_id="KUBE-004",
            severity=Severity.HIGH,
            resource=resource_name,
            message="Container explicitly allows running as root",
            remediation="Set securityContext.runAsNonRoot to true.",
        )

    return None


def check_host_network(
    pod_spec: dict[str, Any],
    resource_name: str,
) -> Finding | None:
    if pod_spec.get("hostNetwork") is True:
        return Finding(
            rule_id="KUBE-005",
            severity=Severity.HIGH,
            resource=resource_name,
            message="Pod uses the host network namespace",
            remediation="Set spec.template.spec.hostNetwork to false.",
        )

    return None


def check_host_namespaces(
    pod_spec: dict[str, Any],
    resource_name: str,
) -> Finding | None:
    if pod_spec.get("hostPID") is True:
        return Finding(
            rule_id="KUBE-006",
            severity=Severity.HIGH,
            resource=resource_name,
            message="Pod shares the host process namespace",
            remediation="Set spec.template.spec.hostPID to false.",
        )

    if pod_spec.get("hostIPC") is True:
        return Finding(
            rule_id="KUBE-006",
            severity=Severity.HIGH,
            resource=resource_name,
            message="Pod shares the host IPC namespace",
            remediation="Set spec.template.spec.hostIPC to false.",
        )

    return None


DANGEROUS_CAPABILITIES = {
    "SYS_ADMIN",
    "NET_ADMIN",
    "SYS_PTRACE",
}


def check_dangerous_capabilities(
    container: dict[str, Any],
    resource_name: str,
) -> Finding | None:
    security_context = container.get("securityContext", {})
    capabilities = security_context.get("capabilities", {})
    added_capabilities = capabilities.get("add", [])

    if not isinstance(added_capabilities, list):
        return None

    dangerous = [
        capability
        for capability in added_capabilities
        if isinstance(capability, str)
        and capability.upper() in DANGEROUS_CAPABILITIES
    ]

    if dangerous:
        capability_names = ", ".join(sorted(set(dangerous)))

        return Finding(
            rule_id="KUBE-007",
            severity=Severity.HIGH,
            resource=resource_name,
            message=f"Dangerous Linux capabilities added: {capability_names}",
            remediation=(
                "Remove unnecessary Linux capabilities and follow "
                "least-privilege principles."
            ),
        )

    return None
