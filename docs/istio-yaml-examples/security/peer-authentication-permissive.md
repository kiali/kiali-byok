---
title: "PeerAuthentication — Permissive mTLS (Migration)"
category: security
description: "Allow both mTLS and plain-text during a gradual migration to strict mode."
istio_versions: ["1.20", "1.21", "1.22", "1.23", "1.24"]
crd_types: ["PeerAuthentication"]
docs_url: "https://github.com/kiali/kiali-byok/blob/main/docs/istio-yaml-examples/security/peer-authentication-permissive.md"
---

Permissive mode: accept mTLS when available, but allow plain-text for legacy workloads.

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: staging
spec:
  mtls:
    mode: PERMISSIVE          # dual-stack: mTLS preferred, plain-text allowed
```

Migration path: set PERMISSIVE → verify all workloads have sidecars → switch to STRICT.

Exclude a single workload from mTLS (e.g. legacy DB client):

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: legacy-client
  namespace: staging
spec:
  selector:
    matchLabels:
      app: legacy-client
  mtls:
    mode: DISABLE             # this pod only — use sparingly
```
