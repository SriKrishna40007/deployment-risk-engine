# Deployment Risk Engine — Engineering Build & Validation Record

This document records how Project 3 was built, integrated, tested, debugged, and validated.

It is intentionally more detailed than the main README. The README explains the project to a recruiter or engineer visiting the repository. This document preserves the engineering journey and the evidence used to decide that the project was ready for release.

---

## 1. Project Objective

The objective was to build a production-oriented deployment security decision engine rather than another generic scanner.

The central question was:

> **Don't just scan the deployment. Decide whether it should ship.**

The target engineering capabilities were:

- security analysis
- Docker security
- Kubernetes security
- policy-as-code
- risk scoring
- CI/CD integration
- Jenkins
- immutable deployment artifacts
- container hardening
- automated testing
- architecture and clean separation of responsibilities

---

# 2. Target Architecture

```text
GitHub
  ↓
Jenkins
  ↓
Build/Test
  ↓
Security Analysis
  ├── Docker Analyzer
  └── Kubernetes Analyzer
       ↓
     Findings
       ↓
   Risk Engine (0–100)
       ↓
   Policy Engine
       ↓
   BLOCK / ALLOW
       ↓
   Kubernetes deployment
```

Internally:

```text
Detection → Findings → Risk → Policy → Decision → CLI/Jenkins
```

This separation was kept throughout implementation.

---

# 3. Phase-by-Phase Build Record

## Phase 1 — Define the problem

The project began with a distinction between scanning and deployment governance.

A scanner answers:

> What is wrong?

The CI/CD system needs:

> Should this release continue?

That led to the architecture:

```text
Detection
   ↓
Finding Model
   ↓
Risk Score
   ↓
Policy
   ↓
Deployment Decision
```

---

## Phase 2 — Domain Model

A common immutable finding object was created.

```python
@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: Severity
    resource: str
    message: str
    remediation: str
```

Why it matters:

- analyzers have one output contract
- risk calculation does not depend on analyzer internals
- policy evaluation can operate on all finding types
- future analyzers can be added without changing the decision model

The `Severity` enum defines:

```text
CRITICAL
HIGH
MEDIUM
LOW
```

---

## Phase 3 — Security Rule Engine

Rules were implemented as focused functions.

Docker rules:

```text
DOCKER-001 → :latest base image
DOCKER-002 → missing USER
```

Kubernetes rules:

```text
KUBE-001 → privileged container
KUBE-002 → :latest image
KUBE-003 → allowPrivilegeEscalation=true
KUBE-004 → runAsNonRoot=false
KUBE-005 → hostNetwork=true
KUBE-006 → hostPID/hostIPC=true
KUBE-007 → dangerous Linux capabilities
```

The design deliberately avoided putting every security check into one giant analyzer function.

---

## Phase 4 — Docker Analyzer

The Docker analyzer reads a Dockerfile as text and applies Docker-specific rules.

The insecure fixture was deliberately designed to demonstrate multiple failures:

```dockerfile
FROM python:latest
WORKDIR /app
COPY . .
CMD ["python", "-m", "http.server", "8080"]
```

This produces:

```text
DOCKER-001 HIGH
DOCKER-002 HIGH
Risk = 50/100
BLOCK
```

The secure Dockerfile uses a versioned base image and numeric non-root UID:

```dockerfile
FROM python:3.13-slim
RUN useradd --create-home --uid 10001 appuser
WORKDIR /app
COPY app.py .
USER 10001
EXPOSE 8080
CMD ["python", "app.py"]
```

The secure scan produces:

```text
Risk = 0/100
ALLOW
```

---

## Phase 5 — Kubernetes Analyzer

The Kubernetes analyzer uses PyYAML and supports:

- multiple YAML documents
- multiple containers
- pod-level checks
- container-level checks

A container finding uses a resource identifier such as:

```text
insecure-app/app
```

Pod-level findings use the workload resource name.

The analyzer intentionally avoids flagging a missing `runAsNonRoot` as an automatic failure because that would create a false-positive-heavy policy. Explicitly unsafe configuration is treated as a finding.

---

## Phase 6 — Risk Engine

Severity weights:

```text
CRITICAL = 40
HIGH     = 25
MEDIUM   = 10
LOW      = 3
```

The sum is capped at 100.

Observed examples:

```text
1 CRITICAL                → 40
2 HIGH                    → 50
CRITICAL + HIGH           → 65
CRITICAL + HIGH + HIGH   → 90
```

This makes the score understandable during an interview and useful as a CI/CD signal.

---

## Phase 7 — Policy Engine

Default policy:

```yaml
policy:
  name: default
  block_on:
    - CRITICAL
    - HIGH
```

The policy engine converts findings into a decision object:

```text
allowed: true/false
reason: ...
```

This intentionally keeps policy separate from the risk algorithm.

---

## Phase 8 — CLI

The CLI became the integration contract.

Commands:

```bash
uv run dre version
uv run dre docker <Dockerfile>
uv run dre k8s <manifest>
```

Exit contract:

```text
0 = ALLOW
1 = BLOCK
2 = invalid/missing input
```

This is what lets Jenkins treat DRE as a security gate without knowing anything about its Python internals.

---

# 4. Jenkins Integration Build

## Jenkins runtime

The development machine is Windows, so Jenkins was run inside Docker rather than requiring Java/Jenkins directly on Windows.

The custom Jenkins image includes:

- Jenkins LTS with JDK 21
- Git
- Docker CLI 28.5.1
- uv
- kubectl v1.34.1

The local runtime was validated with Jenkins 2.580.1.

---

## Docker integration

The Jenkins container uses:

```text
/var/run/docker.sock
```

with:

```text
DOCKER_HOST=unix:///var/run/docker.sock
```

This allows Jenkins to build images using the Docker Desktop daemon.

This is explicitly treated as a local demonstration trade-off. Production Jenkins should use isolated builders or dedicated ephemeral agents instead of granting a controller direct host Docker socket access.

---

## Kubernetes integration

The local Docker Desktop Kubernetes context is:

```text
docker-desktop
```

The Jenkins container receives a read-only kubeconfig mount.

This allows Jenkins to execute:

```bash
kubectl get nodes
kubectl apply
kubectl rollout status
```

The local kubeconfig approach is suitable for the portfolio demonstration but should be replaced by narrowly scoped, short-lived CI credentials in production.

---

# 5. Kubernetes Application Hardening

The deployed application uses:

```yaml
securityContext:
  privileged: false
  allowPrivilegeEscalation: false
  runAsNonRoot: true
  runAsUser: 10001
  capabilities:
    drop:
      - ALL
```

The Docker image also runs as UID `10001`.

This was important because Kubernetes rejected an earlier version that used a named user while `runAsNonRoot` required Kubernetes to verify the user was non-root.

The final numeric UID solved that validation issue.

---

# 6. Immutable Image Pipeline

The first CI/CD design used an image parameter with:

```text
dre-demo:latest
```

DRE correctly blocked `:latest` in the deployment manifest.

Instead of weakening the security rule, the pipeline was redesigned.

Final flow:

```text
Jenkins BUILD_NUMBER
        ↓
IMAGE_NAME=dre-demo:<BUILD_NUMBER>
        ↓
Render k8s/deployment.yaml
        ↓
.generated/deployment.yaml
        ↓
DRE scans exact manifest
        ↓
Docker builds same image
        ↓
kubectl applies same manifest
        ↓
rollout status
```

This is a key engineering decision in the final implementation.

---

# 7. Test Strategy

Testing was performed at several levels.

## Unit tests

Final local result:

```text
23 passed
```

Test areas:

```text
tests/test_docker.py
 tests/test_kubernetes.py
 tests/test_policy.py
 tests/test_risk.py
```

The tests validate the rule engine, analyzers, policy behavior, and risk calculation.

---

## Local secure tests

```bash
uv run dre docker examples/docker/secure/Dockerfile
```

Result:

```text
Risk Score: 0/100
Deployment ALLOWED
```

```bash
uv run dre k8s k8s/deployment.yaml
```

Result:

```text
Risk Score: 0/100
Deployment ALLOWED
```

The deployment template uses a placeholder image, so a Jenkins-style rendered manifest was also tested locally:

```bash
mkdir -p .generated
IMAGE_NAME="dre-demo:999"
sed "s|__IMAGE_NAME__|${IMAGE_NAME}|g" k8s/deployment.yaml > .generated/deployment.yaml
uv run dre k8s .generated/deployment.yaml
rm -rf .generated
```

Result:

```text
Risk Score: 0/100
Deployment ALLOWED
```

This specifically validated the immutable-manifest rendering logic before Jenkins execution.

---

# 8. Production-Style CI/CD Validation

## Secure Jenkins execution

A real Jenkins build checked out commit:

```text
6d03f49 feat: use immutable images in deployment pipeline
```

The pipeline generated:

```text
dre-demo:6
```

Then:

```text
23 tests → PASS
Docker Security Scan → 0/100 ALLOWED
Kubernetes Security Scan → 0/100 ALLOWED
Docker Build → SUCCESS
dre-demo:6 → BUILT
kubectl apply → SUCCESS
rollout status → SUCCESS
```

The build finished:

```text
SUCCESS
```

This is the positive production-like path.

---

# 9. Negative CI/CD Validation — Docker

A second Jenkins build used:

```text
DOCKER_CONTEXT=examples/docker/insecure
```

DRE detected:

```text
DOCKER-001 HIGH
Base image uses mutable :latest

DOCKER-002 HIGH
No USER instruction found
```

Risk:

```text
50/100
```

Decision:

```text
Deployment BLOCKED
```

Jenkins then showed:

```text
Kubernetes Security Scan → SKIPPED
Build Docker Image       → SKIPPED
Deploy                   → SKIPPED
```

The pipeline finished with:

```text
ERROR: script returned exit code 1
Finished: FAILURE
```

This failure is **expected and desired**. It proves that DRE is enforcing a security gate rather than simply printing warnings.

---

# 10. Negative Validation — Kubernetes

The insecure Kubernetes fixture was executed independently:

```bash
uv run dre k8s examples/insecure/deployment.yaml
```

DRE found:

```text
CRITICAL KUBE-001
Privileged container detected

HIGH KUBE-002
Container uses the mutable :latest image tag
```

Risk:

```text
65/100
```

Decision:

```text
Deployment BLOCKED
```

This independently validates the Kubernetes analyzer and proves that the same policy/risk architecture handles Kubernetes findings.

---

# 11. Failure and Debugging Record

## Jenkins parameter/path issue

Early Jenkins execution attempted to scan an incorrect Dockerfile path.

The pipeline parameter handling was simplified and later redesigned so the deployment image is owned by Jenkins and the manifest is generated in the workspace.

## Docker build context issue

An early Jenkins build encountered a missing Docker context.

The final pipeline explicitly passes the Docker context to:

```bash
docker build -t <image> <context>
```

## Windows/Linux command differences

Local development used Git Bash on Windows. Jenkins executes Linux shell commands.

The final pipeline therefore uses `sh` and was validated inside the Jenkins container.

## Docker socket

The Jenkins container required Docker daemon access. The local compose environment mounts the Docker socket and sets `DOCKER_HOST`.

## Kubeconfig

The local Docker Desktop kubeconfig was mounted read-only into Jenkins. This enabled the Kubernetes rollout validation.

## Non-root Kubernetes issue

A named image user combined with `runAsNonRoot: true` caused Kubernetes to reject the container because it could not verify the user as non-root.

The final Docker image uses numeric UID `10001`.

## Port collision

Jenkins already occupied host port 8080. The deployed application was tested using Kubernetes port-forwarding on host port 8081.

## Mutable image issue

DRE caught the use of `:latest` in the actual deployment manifest. The pipeline was redesigned to render an immutable image tag rather than weakening the security rule.

## Docker legacy builder warning

The Jenkins Docker CLI reported a legacy builder deprecation warning. The image still built successfully. BuildKit/buildx is a future infrastructure improvement.

---

# 12. Production Security Assessment

The application workload is hardened.

The CI/CD infrastructure is intentionally simplified for local demonstration.

Known local-only trade-offs:

1. Jenkins runs as root.
2. Jenkins has Docker socket access.
3. Jenkins uses a developer kubeconfig mounted read-only.
4. Docker Desktop is the local Kubernetes runtime.
5. The application image is available through the local Docker daemon rather than a production registry.

Production improvements would include:

- ephemeral Jenkins agents
- dedicated builders
- isolated Docker/BuildKit workers
- scoped Kubernetes service accounts
- short-lived credentials
- workload identity
- private image registries
- image signing
- digest verification
- secrets management
- network isolation
- audit logging

These limitations are intentionally documented rather than hidden.

---

# 13. Release Readiness Checklist

## Application

- [x] Domain model implemented
- [x] Docker analyzer implemented
- [x] Kubernetes analyzer implemented
- [x] Risk engine implemented
- [x] Policy engine implemented
- [x] CLI implemented
- [x] Exit-code contract implemented

## Security

- [x] Docker security rules
- [x] Kubernetes security rules
- [x] Risk scoring
- [x] Policy-as-code
- [x] Non-root application image
- [x] Kubernetes securityContext
- [x] Dangerous capability detection
- [x] Immutable image strategy

## Testing

- [x] 23 automated tests passing
- [x] Secure Docker scan validated
- [x] Secure Kubernetes scan validated
- [x] Secure Jenkins pipeline validated
- [x] Docker failure gate validated
- [x] Kubernetes failure path validated
- [x] Kubernetes rollout validated

## Repository

- [x] Accurate package metadata
- [x] uv.lock committed
- [x] generated artifacts ignored
- [x] unused module removed
- [x] clean working tree
- [x] README/documentation complete

---

# 14. Final Engineering Outcome

The final project demonstrates a complete security decision loop:

```text
                    SECURITY INPUT
                         │
             ┌───────────┴───────────┐
             ▼                       ▼
       Dockerfile              Kubernetes YAML
             │                       │
             └───────────┬───────────┘
                         ▼
                     Findings
                         │
                         ▼
                   Risk Score 0–100
                         │
                         ▼
                    Policy Engine
                         │
                  ┌──────┴──────┐
                  ▼             ▼
                ALLOW         BLOCK
                  │             │
                  ▼             ▼
             Build/Deploy    Stop Pipeline
```

The most important engineering result is not the individual rules.

It is the integration of **security analysis into an enforceable deployment decision**.

---

# 15. Project Completion

**Project 3 — Deployment Risk Engine: COMPLETE**

The project has been implemented, tested locally, integrated with Jenkins, validated against a local Kubernetes cluster, tested on both secure and intentionally insecure paths, and documented for portfolio and interview use.
