---
title: "Ingress Gateway — HTTPS with TLS Termination"
category: traffic-management
description: "Terminate TLS at the Istio ingress gateway using a Kubernetes TLS secret."
istio_versions: ["1.20", "1.21", "1.22", "1.23", "1.24"]
crd_types: ["Gateway", "VirtualService"]
docs_url: "https://github.com/kiali/kiali-byok/blob/main/docs/istio-yaml-examples/traffic-management/ingress-gateway-https.md"
---

HTTPS ingress: terminate TLS at the gateway and forward plain HTTP to the backend.

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: bookinfo-gateway
  namespace: bookinfo
spec:
  selector:
    istio: ingressgateway
  servers:
    - port:
        number: 443
        name: https
        protocol: HTTPS
      tls:
        mode: SIMPLE              # terminate TLS at the gateway
        credentialName: bookinfo-tls  # secret in the same namespace
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
    - bookinfo-gateway
  http:
    - route:
        - destination:
            host: productpage
            port:
              number: 9080
```

Create the TLS secret: `kubectl create secret tls bookinfo-tls --cert=tls.crt --key=tls.key -n bookinfo`
