---
title: "VirtualService — Retry with Exponential Backoff"
category: resilience
description: "Retry failed requests with configurable attempts, timeout, and per-try timeout."
istio_versions: ["1.20", "1.21", "1.22", "1.23", "1.24"]
crd_types: ["VirtualService"]
docs_url: "https://github.com/kiali/kiali-byok/blob/main/docs/istio-yaml-examples/resilience/retry-exponential-backoff.md"
---

Retry policy: retry up to 3 times on gateway errors and connection failures.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: ratings-retry
  namespace: bookinfo
spec:
  hosts:
    - ratings
  http:
    - route:
        - destination:
            host: ratings
      timeout: 10s                  # total request budget
      retries:
        attempts: 3                 # max retry attempts
        perTryTimeout: 2s           # timeout per individual try
        retryOn: 5xx,reset,connect-failure,refused-stream
        # Envoy applies exponential backoff between retries automatically
```

Idempotent methods (GET, HEAD) are safest for retries. Use caution with POST/PUT.
