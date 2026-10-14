---
title: "Blue-Green Deployment with VirtualService"
category: traffic-management
description: "Switch all traffic between two versions using header-based routing for instant cutover."
istio_versions: ["1.20", "1.21", "1.22", "1.23", "1.24"]
crd_types: ["VirtualService", "DestinationRule"]
docs_url: "https://github.com/kiali/kiali-byok/blob/main/docs/istio-yaml-examples/traffic-management/blue-green-deployment.md"
---

Blue-green pattern: route production traffic to blue (v1) and test green (v2) via a header before cutover.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: productpage
  namespace: bookinfo
spec:
  host: productpage
  subsets:
    - name: blue
      labels:
        version: v1          # current production (blue)
    - name: green
      labels:
        version: v2          # new release (green)
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: productpage
  namespace: bookinfo
spec:
  hosts:
    - productpage
  http:
    # Internal testers hit green via header
    - match:
        - headers:
            x-test-version:
              exact: green
      route:
        - destination:
            host: productpage
            subset: green
    # Default production traffic goes to blue
    - route:
        - destination:
            host: productpage
            subset: blue
```

Cutover: change the default route from `blue` to `green`, then decommission blue pods.
