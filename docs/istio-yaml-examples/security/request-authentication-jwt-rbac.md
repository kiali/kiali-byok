---
title: "RequestAuthentication + AuthorizationPolicy — JWT RBAC"
category: security
description: "Require a valid JWT and restrict access to users with a specific claim or role."
istio_versions: ["1.20", "1.21", "1.22", "1.23", "1.24"]
crd_types: ["RequestAuthentication", "AuthorizationPolicy"]
docs_url: "https://github.com/kiali/kiali-byok/blob/main/docs/istio-yaml-examples/security/request-authentication-jwt-rbac.md"
---

JWT + RBAC: validate tokens and allow only requests with `role: admin` in the JWT payload.

```yaml
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: jwt-auth
  namespace: bookinfo
spec:
  selector:
    matchLabels:
      app: productpage
  jwtRules:
    - issuer: "https://accounts.example.com"
      jwksUri: "https://accounts.example.com/.well-known/jwks.json"
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: require-admin-jwt
  namespace: bookinfo
spec:
  selector:
    matchLabels:
      app: productpage
  action: ALLOW
  rules:
    - from:
        - source:
            requestPrincipals: ["*"]   # must have a validated JWT
      when:
        - key: request.auth.claims[role]
          values: ["admin"]            # claim-based access control
```

Unauthenticated requests or tokens without `role: admin` are denied.
