---
title: "Traffic Mirroring and Shadowing"
category: traffic-management
description: "Mirror live production traffic to a shadow version without affecting responses."
istio_versions: ["1.20", "1.21", "1.22", "1.23", "1.24"]
crd_types: ["VirtualService", "DestinationRule"]
docs_url: "https://github.com/kiali/kiali-byok/blob/main/docs/istio-yaml-examples/traffic-management/traffic-mirroring.md"
---

Shadow traffic: send 100% of requests to v1; mirror a percentage to v2 for testing.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
  namespace: bookinfo
spec:
  host: reviews
  subsets:
    - name: v1
      labels:
        version: v1
    - name: v2
      labels:
        version: v2
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
  namespace: bookinfo
spec:
  hosts:
    - reviews
  http:
    - route:
        - destination:
            host: reviews
            subset: v1
      mirror:
        host: reviews
        subset: v2
      mirrorPercentage:
        value: 100.0            # mirror 100% of requests (adjust as needed)
```

Mirrored requests are fire-and-forget; response always comes from the primary route.
