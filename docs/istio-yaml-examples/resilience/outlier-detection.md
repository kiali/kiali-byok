---
title: "DestinationRule — Outlier Detection"
category: resilience
description: "Automatically eject unhealthy hosts from the load balancing pool."
istio_versions: ["1.20", "1.21", "1.22", "1.23", "1.24"]
crd_types: ["DestinationRule"]
docs_url: "https://github.com/kiali/kiali-byok/blob/main/docs/istio-yaml-examples/resilience/outlier-detection.md"
---

Outlier detection: remove pods returning errors or high latency from the rotation.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: ratings-outlier
  namespace: bookinfo
spec:
  host: ratings
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 3     # eject after 3 consecutive 5xx
      consecutiveGatewayErrors: 3
      interval: 10s               # scan interval
      baseEjectionTime: 30s       # minimum ejection duration
      maxEjectionPercent: 30      # never eject more than 30% of endpoints
      minHealthPercent: 50        # stop ejecting if <50% hosts remain healthy
      splitExternalLocalOriginErrors: true
```

Works with Kubernetes readiness probes — outlier detection handles transient failures between probe intervals.
