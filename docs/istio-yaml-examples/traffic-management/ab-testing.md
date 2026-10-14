---
title: "A/B Testing with Header-Based Routing"
category: traffic-management
description: "Route users to variant A or B based on a custom header for A/B experiments."
istio_versions: ["1.20", "1.21", "1.22", "1.23", "1.24"]
crd_types: ["VirtualService", "DestinationRule"]
docs_url: "https://github.com/kiali/kiali-byok/blob/main/docs/istio-yaml-examples/traffic-management/ab-testing.md"
---

A/B test: send users with `x-experiment: b` to variant B; everyone else sees variant A.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: ratings
  namespace: bookinfo
spec:
  host: ratings
  subsets:
    - name: variant-a
      labels:
        version: v1
    - name: variant-b
      labels:
        version: v2
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: ratings
  namespace: bookinfo
spec:
  hosts:
    - ratings
  http:
    - match:
        - headers:
            x-experiment:
              exact: b          # users assigned to experiment B
      route:
        - destination:
            host: ratings
            subset: variant-b
    - route:
        - destination:
            host: ratings
            subset: variant-a   # default control group (A)
```

Your app gateway sets `x-experiment` based on user ID hash or cookie.
