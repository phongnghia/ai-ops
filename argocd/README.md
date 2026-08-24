# ArgoCD Integration — AI Ops Log Analyzer

Connects ArgoCD deployment failures to the AI Ops backend. When an Application
transitions to a Degraded or sync-failed state, ArgoCD Notifications sends the
failure context to `POST /api/analyze-log`. The backend analyzes it with the
configured LLM and dispatches the diagnosis to Slack or Teams.

## How it works

```
ArgoCD Application → Degraded / Sync Failed
        │
        ▼ argocd-notifications-cm.yaml
trigger.on-sync-failed / trigger.on-health-degraded
        │
        ▼ template.ai-ops-analysis
POST /api/analyze-log (ai-ops-backend service)
        │
        ├─ LLM analysis (Gemini / Azure / Ollama)
        └─ Slack / Teams notification
```

ArgoCD does not expose raw container logs via Notifications. Instead the
template assembles a structured diagnostic summary from ArgoCD metadata
fields (app name, namespace, sync status, health status, operation message)
and sends that as the `cleaned_log`.

## Prerequisites

- A running Kubernetes cluster (minikube, kind, or managed)
- ArgoCD installed in the `argocd` namespace
- ArgoCD Notifications controller installed
- AI Ops backend reachable from inside the cluster or via an external address

## Installation

### 1. Install ArgoCD

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

Wait for all pods to be ready:

```bash
kubectl wait --for=condition=available deployment --all -n argocd --timeout=120s
```

Access the UI (default credentials: admin / auto-generated password):

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
# Get the initial admin password
kubectl get secret argocd-initial-admin-secret -n argocd \
  -o jsonpath="{.data.password}" | base64 -d
```

### 2. Install ArgoCD Notifications

```bash
kubectl apply -n argocd \
  -f https://raw.githubusercontent.com/argoproj-labs/argocd-notifications/stable/manifests/install.yaml
```

### 3. Configure the AI Ops backend URL

Edit `argocd-notifications-secret.yaml` and set the backend URL:

```yaml
stringData:
  # In-cluster (if the AI Ops stack is deployed to Kubernetes):
  ai-ops-backend-url: http://ai-ops-backend.ai-ops.svc.cluster.local:8000

  # External (if the AI Ops stack runs via Docker Compose on the host):
  ai-ops-backend-url: http://<host-ip>:8000
```

Apply the secret:

```bash
kubectl apply -f argocd/argocd-notifications-secret.yaml
```

### 4. Apply the Notifications ConfigMap

```bash
kubectl apply -f argocd/argocd-notifications-cm.yaml
```

### 5. Subscribe an Application to the triggers

Add annotations to the ArgoCD Application you want to monitor:

```bash
kubectl annotate application <app-name> -n argocd \
  notifications.argoproj.io/subscribe.on-sync-failed.ai-ops-backend="" \
  notifications.argoproj.io/subscribe.on-health-degraded.ai-ops-backend=""
```

Or add them directly to the Application manifest:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-service
  namespace: argocd
  annotations:
    notifications.argoproj.io/subscribe.on-sync-failed.ai-ops-backend: ""
    notifications.argoproj.io/subscribe.on-health-degraded.ai-ops-backend: ""
spec:
  ...
```

## Payload sent to the backend

```json
{
  "build_number": "my-service",
  "job_name":     "argocd/my-service",
  "build_url":    "https://argocd.example.com/applications/my-service",
  "cleaned_log":  "ArgoCD Application Failure\nApplication: my-service\nNamespace: production\nERROR: Sync status: OutOfSync\nERROR: Health status: Degraded\nMessage: one or more pods failed to start"
}
```

The backend returns a plain-text analysis with three sections
(🚨 Problem / 🔍 Root Cause / 🛠️ Fix Steps) and triggers Slack/Teams
notifications as configured in the AI Ops `.env`.

## Standalone scripts (optional)

The `scripts/` folder contains shell and Python helpers for testing the
integration outside of the Notifications controller — useful for debugging
or for CI pipelines that call ArgoCD APIs directly.

### `scripts/analyze.sh`

Reads ArgoCD context from environment variables and calls the backend:

```bash
export ARGOCD_APP_NAME=my-service
export ARGOCD_APP_NAMESPACE=production
export ARGOCD_APP_SYNC_STATUS=OutOfSync
export ARGOCD_APP_HEALTH_STATUS=Degraded
export ARGOCD_APP_CONDITIONS="Deployment has minimum availability"
export AI_OPS_BACKEND_URL=http://localhost:8000

source argocd/scripts/analyze.sh
```

After sourcing, `AI_ANALYSIS`, `AI_PROVIDER`, `AI_MODEL`, and `AI_STATUS`
are available in the shell.

### `scripts/notify.py`

Formats the exported `AI_*` variables for console output:

```bash
python3 argocd/scripts/notify.py
```

## Comparison with Jenkins integration

| Aspect | Jenkins | ArgoCD |
|---|---|---|
| Trigger | Build failure (`post { failure }`) | App health/sync state change |
| Log source | Jenkins build console log file on disk | ArgoCD metadata fields |
| Script entry | `jenkins/scripts/analyze.sh` | `argocd/scripts/analyze.sh` |
| Notification | Backend handles Slack/Teams | Backend handles Slack/Teams |
| Configuration | `Jenkinsfile` parameters | ArgoCD Application annotations |

Both integrations share the same backend `POST /api/analyze-log` contract
and the same Slack/Teams notification pipeline — only the log source and
trigger mechanism differ.

## Verify the integration

Trigger a sync failure manually:

```bash
# Point an application at a bad image tag to cause a health failure
kubectl patch application my-service -n argocd \
  --type merge \
  -p '{"spec":{"source":{"helm":{"parameters":[{"name":"image.tag","value":"nonexistent"}]}}}}'
```

Check the Notifications controller logs:

```bash
kubectl logs -n argocd deployment/argocd-notifications-controller -f
```

You should see a webhook call to the AI Ops backend followed by the
analysis appearing in the Slack/Teams channel.

## ArgoCD overview

ArgoCD is a free, open source, self-hosted GitOps continuous delivery tool
for Kubernetes. It continuously monitors Git repositories and syncs the
desired state (manifests, Helm charts, Kustomize) to a target cluster.

**Key facts:**
- License: Apache 2.0 — fully free with no paid tiers
- Self-hosted on any Kubernetes cluster (minikube, kind, EKS, GKE, AKS...)
- ArgoCD Notifications supports webhooks, Slack, Teams, PagerDuty, email,
  and more via a plugin-based service catalog
- The ArgoCD UI provides a real-time dependency graph, diff view, and
  rollback capability

**Minimum cluster resources for ArgoCD:**
- 2 vCPU, 4 GB RAM (suitable for minikube or a small cloud node)
