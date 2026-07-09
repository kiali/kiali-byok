---
title: "AuthorizationPolicy — Deny-All Default (Security Best Practice)"
category: security
description: "Start with a namespace-wide deny-all policy, then add explicit ALLOW rules."
istio_versions: ["1.20", "1.21", "1.22", "1.23", "1.24"]
crd_types: ["AuthorizationPolicy"]
docs_url: "https://github.com/kiali/kiali-byok/blob/main/docs/istio-yaml-examples/security/authorization-policy-deny-all.md"
---

Security best practice: zero-trust baseline — deny everything, then whitelist per service.

```yaml
# Namespace-wide deny-all (applies to all workloads in the namespace)
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: deny-all
  namespace: production
spec:
  {}                            # empty spec = deny all inbound traffic
---
# Explicit allow for health checks from the mesh
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: allow-health-checks
  namespace: production
spec:
  selector:
    matchLabels:
      app: my-service
  action: ALLOW
  rules:
    - to:
        - operation:
            paths: ["/health", "/ready"]
            methods: ["GET"]
```

Add one ALLOW policy per service pair as you onboard workloads.
