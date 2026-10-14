---
title: "AuthorizationPolicy — Service-to-Service RBAC"
category: security
description: "Allow only specific source services to call a target service using ALLOW policies."
istio_versions: ["1.20", "1.21", "1.22", "1.23", "1.24"]
crd_types: ["AuthorizationPolicy"]
docs_url: "https://github.com/kiali/kiali-byok/blob/main/docs/istio-yaml-examples/security/authorization-policy-rbac.md"
---

RBAC: only `productpage` pods may call `reviews`; all other sources are denied (with deny-by-default).

```yaml
# Step 1: deny all traffic to reviews (implicit default when ALLOW policies exist)
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: reviews-allow-productpage
  namespace: bookinfo
spec:
  selector:
    matchLabels:
      app: reviews              # applies to reviews pods
  action: ALLOW
  rules:
    - from:
        - source:
            principals:
              - "cluster.local/ns/bookinfo/sa/bookinfo-productpage"
      to:
        - operation:
            methods: ["GET", "POST"]
            paths: ["/reviews/*"]
```

Principals use SPIFFE format: `cluster.local/ns/<namespace>/sa/<service-account>`.
