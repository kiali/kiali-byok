---
title: "DestinationRule — Circuit Breaker"
category: resilience
description: "Trip the circuit when consecutive errors exceed a threshold to protect upstream services."
istio_versions: ["1.20", "1.21", "1.22", "1.23", "1.24"]
crd_types: ["DestinationRule"]
docs_url: "https://github.com/kiali/kiali-byok/blob/main/docs/istio-yaml-examples/resilience/circuit-breaker.md"
---

Circuit breaker: eject unhealthy hosts after 5 consecutive 5xx errors within 30 seconds.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: ratings-cb
  namespace: bookinfo
spec:
  host: ratings
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        maxRequestsPerConnection: 2
    outlierDetection:
      consecutive5xxErrors: 5       # trip after 5 consecutive 5xx
      interval: 30s                 # evaluation window
      baseEjectionTime: 30s         # host ejected for at least 30s
      maxEjectionPercent: 50        # max 50% of hosts ejected at once
```

Combine with connection pool limits to prevent retry storms during outages.
