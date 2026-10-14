---
title: "VirtualService — Request Timeout"
category: resilience
description: "Set per-route timeouts to prevent slow upstreams from blocking callers."
istio_versions: ["1.20", "1.21", "1.22", "1.23", "1.24"]
crd_types: ["VirtualService"]
docs_url: "https://github.com/kiali/kiali-byok/blob/main/docs/istio-yaml-examples/resilience/timeout-configuration.md"
---

Timeout: fail fast if `details` service does not respond within 3 seconds.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: details-timeout
  namespace: bookinfo
spec:
  hosts:
    - details
  http:
    - route:
        - destination:
            host: details
      timeout: 3s                 # return 504 if upstream exceeds 3s
```

Global default timeout in mesh config (IstioOperator):

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: mesh-timeouts
spec:
  meshConfig:
    defaultConfig:
      holdApplicationUntilProxyStarts: true
  # Per-route VirtualService timeouts override mesh defaults
```

Always set timeouts shorter than client-side deadlines to surface errors cleanly.
