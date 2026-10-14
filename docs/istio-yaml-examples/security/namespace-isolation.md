---
title: "AuthorizationPolicy — Namespace Isolation"
category: security
description: "Prevent cross-namespace traffic except from explicitly allowed namespaces."
istio_versions: ["1.20", "1.21", "1.22", "1.23", "1.24"]
crd_types: ["AuthorizationPolicy"]
docs_url: "https://github.com/kiali/kiali-byok/blob/main/docs/istio-yaml-examples/security/namespace-isolation.md"
---

Namespace isolation: only allow traffic from the `frontend` namespace into `backend`.

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: backend-namespace-isolation
  namespace: backend
spec:
  action: ALLOW
  rules:
    - from:
        - source:
            namespaces: ["frontend"]   # only frontend namespace may connect
      to:
        - operation:
            methods: ["GET", "POST", "PUT"]
```

Combine with a namespace-wide deny-all policy in `backend` for defense in depth:

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: deny-all
  namespace: backend
spec: {}
```

The ALLOW policy above takes precedence for matching rules; everything else is denied.
