---
title: "DestinationRule — Connection Pool Settings"
category: resilience
description: "Limit concurrent connections and pending requests to prevent resource exhaustion."
istio_versions: ["1.20", "1.21", "1.22", "1.23", "1.24"]
crd_types: ["DestinationRule"]
docs_url: "https://github.com/kiali/kiali-byok/blob/main/docs/istio-yaml-examples/resilience/connection-pool.md"
---

Connection pool: cap TCP connections and HTTP pending requests to the reviews service.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-pool
  namespace: bookinfo
spec:
  host: reviews
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 50        # max TCP connections to each upstream host
        connectTimeout: 30ms      # fail fast on connect
      http:
        http2MaxRequests: 100     # max concurrent HTTP/2 requests
        http1MaxPendingRequests: 50  # queue limit for HTTP/1.1
        maxRequestsPerConnection: 10 # connection reuse limit
        idleTimeout: 60s          # close idle connections after 60s
```

Tune based on pod CPU/memory and upstream capacity. Monitor 503 URX (upstream reset) metrics.
