---
title: "Canary Deployment with VirtualService"
category: traffic-management
description: "Gradually shift traffic to a new version using weighted routing in a VirtualService."
istio_versions: ["1.20", "1.21", "1.22", "1.23", "1.24"]
crd_types: ["VirtualService", "DestinationRule"]
docs_url: "https://github.com/kiali/kiali-byok/blob/main/docs/istio-yaml-examples/traffic-management/canary-deployment.md"
---

Production-ready canary deployment: route 90% of traffic to the stable version and 10% to the canary.

```yaml
# DestinationRule defines subsets (versions) for the reviews service
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
        version: v1          # stable version selector
    - name: v2
      labels:
        version: v2          # canary version selector
---
# VirtualService splits traffic by weight between subsets
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
          weight: 90          # 90% to stable
        - destination:
            host: reviews
            subset: v2
          weight: 10          # 10% to canary
```

To advance the canary, increase the v2 weight (e.g. 50/50, then 0/100) and remove the old subset when done.
