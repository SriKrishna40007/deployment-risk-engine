from pathlib import Path
from typing import Any

import yaml

from deployment_risk_engine.models import Finding
from deployment_risk_engine.rules import (
    check_allow_privilege_escalation,
    check_dangerous_capabilities,
    check_host_namespaces,
    check_host_network,
    check_latest_image,
    check_run_as_non_root,
    check_privileged_container,
)


def scan_file(file_path: str) -> list[Finding]:
    """Scan a Kubernetes YAML file for supported security risks."""

    path = Path(file_path)

    with path.open("r", encoding="utf-8") as file:
        documents = list(yaml.safe_load_all(file))

    findings: list[Finding] = []

    for document in documents:
        if not document:
            continue

        if not isinstance(document, dict):
            continue

        resource_name = document.get("metadata", {}).get(
            "name",
            "unknown",
        )

        pod_spec = (
            document.get("spec", {})
            .get("template", {})
            .get("spec", {})
        )

        host_namespace_finding = check_host_namespaces(
            pod_spec,
            resource_name,
        )

        if host_namespace_finding:
            findings.append(host_namespace_finding)

        host_network_finding = check_host_network(
            pod_spec,
            resource_name,
        )

        if host_network_finding:
            findings.append(host_network_finding)

        containers = pod_spec.get("containers", [])

        for container in containers:
            if not isinstance(container, dict):
                continue

            container_name = container.get("name", "unknown")
            resource = f"{resource_name}/{container_name}"

            capabilities_finding = check_dangerous_capabilities(
                container,
                resource,
            )

            if capabilities_finding:
                findings.append(capabilities_finding)

            privileged_finding = check_privileged_container(
                container,
                resource,
            )

            if privileged_finding:
                findings.append(privileged_finding)

            escalation_finding = check_allow_privilege_escalation(
                container,
                resource,
            )

            if escalation_finding:
                findings.append(escalation_finding)

            non_root_finding = check_run_as_non_root(
                container,
                resource,
            )

            if non_root_finding:
                findings.append(non_root_finding)

            image = container.get("image")

            if isinstance(image, str):
                image_finding = check_latest_image(
                    image,
                    resource,
                )

                if image_finding:
                    findings.append(image_finding)

    return findings
