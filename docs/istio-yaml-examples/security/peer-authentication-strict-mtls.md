---
title: "PeerAuthentication — Strict mTLS"
category: security
description: "Enforce mutual TLS for all workloads in a namespace; reject plain-text traffic."
istio_versions: ["1.20", "1.21", "1.22", "1.23", "1.24"]
crd_types: ["PeerAuthentication"]
docs_url: "https://github.com/kiali/kiali-byok/blob/main/docs/istio-yaml-examples/security/peer-authentication-strict-mtls.md"
---

Strict mTLS: all pod-to-pod traffic in the namespace must use mutual TLS.

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: production
spec:
  mtls:
    mode: STRICT              # reject connections without valid mTLS certs
```

Mesh-wide strict mTLS (all namespaces):

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT
```

Apply namespace policy first, then roll out mesh-wide. Verify with `istioctl authn tls-check <pod> <service>`.
