---
title: "Ingress Gateway — HTTP"
category: traffic-management
description: "Expose a service through the Istio ingress gateway on plain HTTP port 80."
istio_versions: ["1.20", "1.21", "1.22", "1.23", "1.24"]
crd_types: ["Gateway", "VirtualService"]
docs_url: "https://github.com/kiali/kiali-byok/blob/main/docs/istio-yaml-examples/traffic-management/ingress-gateway-http.md"
---

HTTP ingress: bind Gateway to the istio-ingressgateway and route to a backend service.

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: bookinfo-gateway
  namespace: bookinfo
spec:
  selector:
    istio: ingressgateway     # uses the default Istio ingress deployment
  servers:
    - port:
        number: 80
        name: http
        protocol: HTTP
      hosts:
        - "bookinfo.example.com"
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: bookinfo
  namespace: bookinfo
spec:
  hosts:
    - "bookinfo.example.com"
  gateways:
    - bookinfo-gateway          # attach to the Gateway above
  http:
    - match:
        - uri:
            prefix: /
      route:
        - destination:
            host: productpage
            port:
              number: 9080
```

Ensure DNS for `bookinfo.example.com` points to the ingress gateway external IP.
