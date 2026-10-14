---
title: "RequestAuthentication — JWT Validation"
category: security
description: "Validate JWT tokens at the ingress using an OIDC issuer and JWKS endpoint."
istio_versions: ["1.20", "1.21", "1.22", "1.23", "1.24"]
crd_types: ["RequestAuthentication"]
docs_url: "https://github.com/kiali/kiali-byok/blob/main/docs/istio-yaml-examples/security/request-authentication-jwt.md"
---

JWT validation: verify Bearer tokens issued by your OIDC provider before traffic reaches the app.

```yaml
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: jwt-auth
  namespace: bookinfo
spec:
  selector:
    matchLabels:
      app: productpage          # apply to productpage ingress pods
  jwtRules:
    - issuer: "https://accounts.example.com"
      jwksUri: "https://accounts.example.com/.well-known/jwks.json"
      audiences:
        - "bookinfo-api"
      forwardOriginalToken: true  # pass token to the app after validation
```

RequestAuthentication alone does not block unauthenticated requests — pair with AuthorizationPolicy (see jwt-rbac example).
