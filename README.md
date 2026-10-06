# Deployment Risk Engine

> **Don't just scan the deployment. Decide whether it should ship.**

Deployment Risk Engine (DRE) is a security gate for CI/CD pipelines that evaluates Dockerfiles and Kubernetes manifests before deployment.

DRE converts individual security findings into a normalized domain model, calculates an aggregated deployment risk score from **0–100**, evaluates the result against an organization-defined policy, and returns a machine-readable **ALLOW / BLOCK** decision through CLI exit codes.

The project was built to demonstrate production-oriented **Cloud Security, DevSecOps, Kubernetes Security, CI/CD, Backend Engineering, policy-as-code, and risk-based deployment decisions**.

---

## 1. Why I Built This

A security scanner can tell an engineering team that a deployment contains a privileged container, a mutable image tag, privilege escalation, host networking, or another dangerous configuration.

But a CI/CD pipeline still needs to answer the operational question:

> **Should this deployment be allowed to continue?**

That is the problem DRE solves.

Instead of treating security findings as isolated warnings, DRE creates a deployment-level decision:

```text
Security Findings
       ↓
Normalized Findings
       ↓
Risk Score (0–100)
       ↓
Organization Policy
       ↓
ALLOW / BLOCK
       ↓
CI/CD Decision
```

The objective was deliberately different from building another generic vulnerability scanner. The project demonstrates how security analysis becomes an **enforceable deployment control**.

---

# 2. The Problem

Modern CI/CD systems can build and deploy infrastructure very quickly. That speed creates a security problem when infrastructure configuration is unsafe.

Examples include:

- privileged containers
- mutable `:latest` images
- containers that can escalate privileges
- workloads explicitly allowed to run as root
- host networking
- host PID/IPC namespaces
- dangerous Linux capabilities
- Dockerfiles without a non-root user

A scanner that only prints findings still leaves the deployment system to interpret those findings.

DRE introduces an explicit decision layer:

```text
Detection → Risk → Policy → Decision
```

This makes the security control consumable by Jenkins and other automation systems.

---

# 3. What DRE Does

DRE currently analyzes two deployment surfaces.

## Dockerfile analysis

| Rule | Severity | Purpose |
|---|---|---|
| `DOCKER-001` | HIGH | Detect mutable `:latest` base images |
| `DOCKER-002` | HIGH | Detect Dockerfiles without a `USER` instruction |

## Kubernetes analysis

| Rule | Severity | Purpose |
|---|---|---|
| `KUBE-001` | CRITICAL | Detect privileged containers |
| `KUBE-002` | HIGH | Detect mutable `:latest` images |
| `KUBE-003` | HIGH | Detect explicit privilege escalation |
| `KUBE-004` | HIGH | Detect explicit root execution |
| `KUBE-005` | HIGH | Detect host networking |
| `KUBE-006` | HIGH | Detect host PID/IPC namespaces |
| `KUBE-007` | HIGH | Detect dangerous Linux capabilities |

The analyzer produces a common finding model:

```python
Finding(
    rule_id=...,
    severity=...,
    resource=...,
    message=...,
    remediation=...
)
```

This keeps the security detection layer independent from the risk and policy layers.

---

# 4. Architecture

## High-level architecture

```text
                         GitHub
                            │
                            ▼
                         Jenkins
                            │
                     ┌──────┴──────┐
                     │             │
                     ▼             ▼
              Docker Analyzer   K8s Analyzer
                     │             │
                     └──────┬──────┘
                            ▼
                        Findings
                            │
                            ▼
                       Risk Engine
                         0–100
                            │
                            ▼
                      Policy Engine
                            │
                       ┌────┴────┐
                       ▼         ▼
                    ALLOW      BLOCK
                       │         │
                       ▼         ▼
                  Build/Deploy  Stop
```

## Internal responsibility boundaries

```text
Detection  → What is wrong?
Finding    → How is the issue represented?
Risk       → How risky is the deployment?
Policy     → What does the organization permit?
Decision   → Should the pipeline continue?
Reporting  → What does the engineer need to see?
```

The implementation deliberately separates these concerns so a new analyzer, rule, risk model, or policy can evolve without rewriting the complete application.

---

# 5. CI/CD Architecture

The final Jenkins pipeline is:

```text
GitHub
  ↓
Checkout
  ↓
Install Dependencies
  ↓
Run 23 Automated Tests
  ↓
Generate Exact Deployment Manifest
  ↓
Docker Security Scan
  ↓
Kubernetes Security Scan
  ↓
Build Immutable Docker Image
  ↓
Deploy Exact Scanned Manifest
  ↓
Kubernetes Rollout Verification
```

The key design decision is that Jenkins does **not** scan one Kubernetes configuration and deploy another.

The repository stores a template:

```yaml
image: __IMAGE_NAME__
```

Jenkins renders it using its build number:

```text
Build #6
    ↓
dre-demo:6
```

The generated manifest is then scanned:

```text
.generated/deployment.yaml
```

The exact same generated manifest is deployed.

This creates the following invariant:

> **The Kubernetes configuration that passes DRE is the configuration Kubernetes receives.**

---

# 6. Immutable Image Strategy

The pipeline deliberately avoids:

```text
dre-demo:latest
```

Instead:

```text
dre-demo:<JENKINS_BUILD_NUMBER>
```

For example:

```text
Build #6 → dre-demo:6
Build #7 → dre-demo:7
```

This provides a simple immutable build identity for the local CI/CD demonstration and prevents the pipeline from bypassing the mutable-image security rule.

A future production implementation could move from build-number tags to Git SHA tags plus registry digests.

---

# 7. Risk Engine

The current severity weights are:

| Severity | Score |
|---|---:|
| CRITICAL | 40 |
| HIGH | 25 |
| MEDIUM | 10 |
| LOW | 3 |

The total is capped at 100.

Examples:

```text
1 CRITICAL                  = 40
2 HIGH                      = 50
1 CRITICAL + 1 HIGH        = 65
1 CRITICAL + 2 HIGH        = 90
```

Example observed during validation:

```text
KUBE-001 CRITICAL = 40
KUBE-002 HIGH     = 25
-------------------------
Risk Score         = 65
```

The risk engine answers:

> **How risky is this deployment?**

It does not decide whether the risk is acceptable. That is the policy engine's responsibility.

---

# 8. Policy Engine

The default policy is stored in:

```text
policies/default.yaml
```

```yaml
policy:
  name: default
  block_on:
    - CRITICAL
    - HIGH
```

This creates a clean separation:

```text
Risk Engine
    │
    │ Risk = 65
    ▼
Policy Engine
    │
    │ CRITICAL/HIGH are blocked
    ▼
Deployment BLOCKED
```

An organization could therefore change policy without changing the security analyzers.

---

# 9. CLI Contract

DRE exposes:

```bash
uv run dre --help
uv run dre version
uv run dre docker <Dockerfile>
uv run dre k8s <manifest>
```

The CI/CD exit-code contract is:

```text
0 → Deployment allowed
1 → Deployment blocked
2 → Invalid or missing input
```

This is important because Jenkins does not need to understand Python internals. It only needs the process result.

```text
DRE exits 0 → Jenkins continues
DRE exits 1 → Jenkins stops
```

---

# 10. Technology Stack

### Application

- Python 3.13
- Typer
- Rich
- PyYAML
- pytest
- uv
- Hatchling

### Infrastructure

- Docker
- Docker Desktop
- Kubernetes
- kubectl
- Jenkins
- GitHub
- Git

### Engineering practices

- Domain modeling
- Clean separation of concerns
- Rule-based security analysis
- Policy-as-code
- Risk scoring
- CI/CD security gates
- Unit testing
- Immutable image tagging
- Container hardening
- Kubernetes security contexts

Validated local/CI tooling included Python 3.13, Docker 28.5.1, kubectl v1.34.1, Jenkins 2.580.1, pytest 9.1.1, and uv-managed environments.

---

# 11. Repository Structure

```text
deployment-risk-engine/
│
├── deployment_risk_engine/
│   ├── __init__.py
│   ├── docker.py
│   ├── kubernetes.py
│   ├── main.py
│   ├── models.py
│   ├── policy.py
│   ├── risk.py
│   └── rules.py
│
├── tests/
│   ├── __init__.py
│   ├── test_docker.py
│   ├── test_kubernetes.py
│   ├── test_policy.py
│   └── test_risk.py
│
├── examples/
│   ├── docker/
│   │   ├── insecure/
│   │   └── secure/
│   ├── insecure/
│   └── secure/
│
├── policies/
│   └── default.yaml
│
├── jenkins/
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── k8s/
│   ├── deployment.yaml
│   └── service.yaml
│
├── Jenkinsfile
├── pyproject.toml
├── uv.lock
├── .python-version
└── README.md
```

Detailed build notes and validation evidence are available in `docs/PROJECT_BUILD_AND_VALIDATION.md`.

---

# 12. How the Project Was Built

The implementation was developed in phases rather than as one large application.

## Phase 1 — Define the deployment decision problem

The first architectural decision was to make DRE a **decision engine**, not only a scanner.

The target flow became:

```text
Analyze → Normalize → Score → Evaluate Policy → Decide
```

This established the separation between security detection and deployment governance.

## Phase 2 — Create the domain model

A common `Finding` model and `Severity` enum were created.

The model is immutable using a frozen dataclass so downstream layers cannot accidentally mutate security findings after detection.

## Phase 3 — Build the rule engine

Security rules were implemented as small functions with clear responsibilities.

This made the analyzers thin and kept security logic testable.

## Phase 4 — Build the Docker analyzer

The Docker analyzer reads a Dockerfile and applies Docker-specific rules.

The insecure fixture deliberately demonstrated two failures:

- mutable `python:latest`
- missing `USER`

## Phase 5 — Build the Kubernetes analyzer

The Kubernetes analyzer was designed to handle multiple YAML documents and multiple containers.

Rules were added for privileged execution, mutable images, privilege escalation, root execution, host namespaces, and dangerous capabilities.

## Phase 6 — Add risk scoring

Individual findings were aggregated into one deployment-level score.

This made the output useful to CI/CD rather than just producing a list of findings.

## Phase 7 — Add policy-as-code

The policy engine reads YAML configuration and decides whether findings violate deployment policy.

This intentionally separates organizational policy from technical detection.

## Phase 8 — Build the CLI

Typer was used to create the `dre` command.

The CLI became the contract between the security engine and Jenkins.

## Phase 9 — Containerize the Jenkins environment

Jenkins was run in Docker rather than requiring Java and Jenkins tooling to be installed directly on Windows.

The custom Jenkins image includes:

- Jenkins with JDK 21
- Git
- Docker CLI
- uv
- kubectl

## Phase 10 — Connect Jenkins to Docker and Kubernetes

The local Jenkins environment was connected to Docker Desktop and the local Kubernetes cluster.

The Docker socket and read-only kubeconfig mount were used for the local demonstration.

## Phase 11 — Build the secure application image

The demo application was hardened to run as UID `10001`.

The Kubernetes workload also requires:

```yaml
privileged: false
allowPrivilegeEscalation: false
runAsNonRoot: true
runAsUser: 10001
capabilities:
  drop:
    - ALL
```

## Phase 12 — Integrate immutable deployment manifests

An initial pipeline used a mutable image parameter and `kubectl set image`.

DRE correctly exposed the weakness: `:latest` was blocked.

Instead of weakening the rule, the pipeline was redesigned to render the exact deployment manifest with an immutable build tag before scanning.

## Phase 13 — Validate secure and insecure paths

The secure pipeline was successfully built and deployed.

The insecure Docker path was intentionally blocked by DRE before Docker build and Kubernetes deployment.

The insecure Kubernetes fixture was independently blocked with a risk score of 65/100.

## Phase 14 — Repository hardening

Final cleanup included:

- accurate project metadata
- generated CI artifact exclusion
- removal of unused code
- final regression tests
- clean Git history and working tree

---

# 13. Local Setup

Requirements:

- Python 3.13
- uv
- Docker Desktop
- Kubernetes enabled in Docker Desktop
- kubectl
- Git

Clone the repository and enter it:

```bash
git clone https://github.com/SriKrishna40007/deployment-risk-engine.git
cd deployment-risk-engine
```

Install dependencies:

```bash
uv sync --dev
```

Run tests:

```bash
uv run pytest
```

Run the CLI:

```bash
uv run dre --help
```

---

# 14. Run DRE Locally

Secure Dockerfile:

```bash
uv run dre docker examples/docker/secure/Dockerfile
```

Expected:

```text
Risk Score: 0/100
Deployment ALLOWED
```

Secure Kubernetes manifest:

```bash
uv run dre k8s examples/secure/deployment.yaml
```

Expected:

```text
Risk Score: 0/100
Deployment ALLOWED
```

Insecure Dockerfile:

```bash
uv run dre docker examples/docker/insecure/Dockerfile
```

Expected result:

```text
DOCKER-001 HIGH
DOCKER-002 HIGH
Risk Score: 50/100
Deployment BLOCKED
```

Insecure Kubernetes deployment:

```bash
uv run dre k8s examples/insecure/deployment.yaml
```

Expected result:

```text
CRITICAL KUBE-001
HIGH KUBE-002
Risk Score: 65/100
Deployment BLOCKED
```

---

# 15. Local Kubernetes Deployment

The local demo uses Docker Desktop Kubernetes.

Apply the deployment template after rendering an image name:

```bash
mkdir -p .generated
sed 's|__IMAGE_NAME__|dre-demo:local|g' k8s/deployment.yaml > .generated/deployment.yaml
```

Build the secure image:

```bash
docker build -t dre-demo:local examples/docker/secure
```

Apply the deployment and service:

```bash
kubectl apply -f .generated/deployment.yaml
kubectl apply -f k8s/service.yaml
```

Check the rollout:

```bash
kubectl rollout status deployment/dre-demo
```

The application can be exposed locally with:

```bash
kubectl port-forward deployment/dre-demo 8081:8080
```

Then:

```bash
curl http://localhost:8081
```

The demo application responds with:

```text
Deployment Risk Engine secure application is running
```

Generated files can be removed with:

```bash
rm -rf .generated
```

---

# 16. Jenkins Local Environment

Jenkins is containerized under:

```text
jenkins/
├── Dockerfile
└── docker-compose.yml
```

The local setup provides:

- Jenkins
- Docker CLI
- Docker daemon access through Docker Desktop
- uv
- kubectl
- access to the local Docker Desktop Kubernetes context

The local environment intentionally uses a read-only kubeconfig mount and Docker socket access.

This is a **portfolio/demo architecture**, not the recommended production Jenkins security model.

---

# 17. Jenkins Pipeline

The final Jenkinsfile performs:

```text
Checkout
  ↓
Install Dependencies
  ↓
Test
  ↓
Prepare Deployment
  ↓
Docker Security Scan
  ↓
Kubernetes Security Scan
  ↓
Build Docker Image
  ↓
Deploy
  ↓
Rollout Status
```

The deployment image is derived from the Jenkins build number:

```groovy
environment {
    IMAGE_NAME = "dre-demo:${BUILD_NUMBER}"
}
```

The generated deployment is scanned before it is deployed.

---

# 18. Production-Style Validation

The project was validated through multiple layers instead of relying only on unit tests.

## Layer 1 — Unit tests

Final result:

```text
23 passed
```

Coverage includes:

- Docker rules
- Kubernetes rules
- policy evaluation
- risk scoring

## Layer 2 — Local CLI tests

Secure Docker and Kubernetes inputs returned:

```text
0/100 ALLOWED
```

Insecure inputs returned non-zero exit status and:

```text
BLOCKED
```

## Layer 3 — Jenkins secure pipeline

A real Jenkins build successfully performed:

```text
23 tests
Docker scan → 0/100 ALLOWED
Kubernetes scan → 0/100 ALLOWED
Build dre-demo:6
Kubernetes rollout → SUCCESS
```

## Layer 4 — Jenkins security failure

An intentionally insecure Docker context produced:

```text
DOCKER-001 HIGH
DOCKER-002 HIGH
Risk Score: 50/100
Deployment BLOCKED
```

Jenkins correctly skipped:

```text
Kubernetes Security Scan
Build Docker Image
Deploy
```

The pipeline ended with exit code `1` / `FAILURE`.

This is an expected and desired result.

## Layer 5 — Independent Kubernetes failure

The insecure Kubernetes fixture produced:

```text
KUBE-001 CRITICAL
KUBE-002 HIGH
Risk Score: 65/100
Deployment BLOCKED
```

This independently proves the Kubernetes analyzer feeds the same deployment decision model.

---

# 19. Engineering Debugging Lessons

This project also involved real integration debugging.

### Jenkins parameter resolution

An early pipeline attempted to execute DRE against an invalid Dockerfile path. The pipeline parameters were redesigned and simplified.

### Docker build context

Jenkins initially encountered Docker context issues. The final pipeline explicitly builds from the intended Docker context.

### Windows vs Linux execution

The development machine is Windows while Jenkins runs Linux inside a container. Commands and paths were therefore tested in both environments.

### Docker socket access

The Jenkins container required access to the Docker Desktop daemon for builds. The local compose environment uses `/var/run/docker.sock` and `DOCKER_HOST`.

### Kubernetes non-root execution

Kubernetes rejected a named non-root user when `runAsNonRoot` could not verify the image user. The image was changed to use numeric UID `10001`.

### Jenkins port collision

Jenkins occupied host port `8080`, so the application was verified through port `8081` using Kubernetes port forwarding.

### Mutable image detection

DRE correctly blocked the initial `:latest` deployment. The solution was not to disable the rule, but to redesign the CI/CD flow around immutable build tags.

### Docker legacy builder warning

The local Jenkins Docker CLI reported the legacy builder deprecation warning. It did not affect the successful build or deployment. BuildKit/buildx is a future infrastructure improvement.

---

# 20. Security Trade-offs and Production Considerations

The local Jenkins environment currently uses:

```text
Jenkins as root
Docker socket access
Developer kubeconfig mounted read-only
```

These choices simplify the Docker Desktop portfolio demonstration.

They should not be copied directly into a production CI/CD environment.

A production implementation should consider:

- ephemeral Jenkins agents
- dedicated build workers
- narrowly scoped Kubernetes service accounts
- short-lived credentials
- workload identity
- isolated builders
- registry authentication
- signed images
- image digest verification
- secret management
- restricted Jenkins permissions
- network isolation

The important engineering point is that these are **known and documented trade-offs**.

---

# 21. Why This Is Not Just Another Security Scanner

DRE is intentionally not trying to replace mature security products.

The project demonstrates a different problem:

> **How do we turn security analysis into an enforceable deployment decision?**

The architecture therefore focuses on:

```text
Security Detection
       +
Risk Aggregation
       +
Policy Evaluation
       +
CI/CD Enforcement
```

This makes the project useful as a demonstration of:

- Cloud Security
- DevSecOps
- Backend Engineering
- Security Architecture
- Policy-as-Code
- CI/CD Engineering
- Kubernetes Security

---

# 22. Interview Explanation

### 30-second explanation

> Deployment Risk Engine is a security gate I built for CI/CD pipelines. It analyzes Dockerfiles and Kubernetes manifests, normalizes security findings, calculates a 0–100 deployment risk score, evaluates the findings against policy, and returns an ALLOW or BLOCK decision. I integrated it with Jenkins so security failures stop the pipeline before Docker build and Kubernetes deployment. I also implemented immutable build tags so the exact Kubernetes manifest scanned by DRE is the manifest that gets deployed.

### Architecture explanation

> I separated the system into detection, finding normalization, risk calculation, policy evaluation, and decision layers. The analyzers only detect issues. The risk engine aggregates severity into a deployment score. The policy engine decides whether those findings violate organizational policy. Jenkins consumes the final CLI exit code, which keeps the CI/CD layer independent of the Python implementation.

### Why separate risk and policy?

Risk answers:

> How risky is this?

Policy answers:

> Is that risk acceptable for this environment?

Separating them allows risk weights and organizational policy to evolve independently.

### Why immutable image tags?

Using `latest` makes the artifact ambiguous. A build-number tag gives the CI run a concrete image identity. More importantly, DRE scans the rendered deployment manifest containing that exact image tag, and Kubernetes deploys the same manifest.

### What happens when DRE blocks?

The analyzer returns findings, the risk engine calculates the score, the policy engine evaluates the findings, and the CLI exits with code `1`. Jenkins interprets the non-zero exit code as a failed stage, so later build and deployment stages are skipped.

---

# 23. Interview Questions to Prepare

### Security

1. Why are privileged containers dangerous?
2. Why should containers run as non-root?
3. What is `allowPrivilegeEscalation`?
4. Why are host PID/IPC namespaces risky?
5. Why is `hostNetwork` dangerous?
6. Why should Linux capabilities be minimized?
7. Why is `:latest` undesirable for production deployments?

### DevSecOps

1. Where should security gates run in a CI/CD pipeline?
2. What should happen when a security gate fails?
3. Why should the scanner return meaningful exit codes?
4. How do you prevent scanning one configuration and deploying another?
5. What are the risks of mounting the Docker socket into Jenkins?

### Architecture

1. Why separate analyzers from the risk engine?
2. Why separate risk from policy?
3. How would you add Terraform support?
4. How would you add JSON/SARIF output?
5. How would you scale analysis across thousands of manifests?
6. How would you make the policy engine environment-specific?

### Kubernetes

1. What does `runAsNonRoot` enforce?
2. Why did numeric UID `10001` solve the earlier Kubernetes issue?
3. What is the purpose of dropping Linux capabilities?
4. Why is `imagePullPolicy: IfNotPresent` useful for this local Docker Desktop demo?
5. What would change when deploying to a remote cluster?

---

# 24. Future Improvements

The core project is complete. Possible future extensions include:

- Docker image digest enforcement
- additional Kubernetes rules
- `initContainers` analysis
- Kubernetes workload kind validation
- richer policy expressions
- configurable risk weights
- JSON output
- SARIF output
- GitHub Actions integration
- image signing and verification
- registry integration
- admission-controller integration
- persistent audit history
- expiring policy exceptions
- security trend analysis
- parallel analysis for very large repositories
- BuildKit/buildx integration

These are deliberately future improvements rather than unfinished core requirements.

---

# 25. What I Learned

This project strengthened my practical understanding of:

- Python application architecture
- security rule engines
- Docker security
- Kubernetes security
- CI/CD architecture
- Jenkins pipelines
- policy-as-code
- risk modeling
- immutable deployment strategies
- container hardening
- Linux permissions
- Kubernetes security contexts
- automated testing
- cross-platform debugging
- DevSecOps engineering

The most important lesson was architectural:

> **Security tooling becomes much more valuable when it can turn a finding into an explicit engineering decision.**

---

# 26. Project Status

**Project 3 — Deployment Risk Engine**

```text
████████████████████ 100%
```

Validated with:

- 23 automated tests
- secure Docker scan
- secure Kubernetes scan
- successful Jenkins CI/CD execution
- immutable Docker image build
- successful Kubernetes rollout
- intentionally blocked Docker deployment
- intentionally blocked Kubernetes deployment analysis
- clean repository state

The implementation is complete and released as the third project in the engineering portfolio.
