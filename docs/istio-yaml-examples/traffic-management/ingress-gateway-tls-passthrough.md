---
title: "Ingress Gateway — TLS Passthrough"
category: traffic-management
description: "Pass encrypted TLS traffic through the gateway without terminating it at the proxy."
istio_versions: ["1.20", "1.21", "1.22", "1.23", "1.24"]
crd_types: ["Gateway", "VirtualService", "DestinationRule"]
docs_url: "https://github.com/kiali/kiali-byok/blob/main/docs/istio-yaml-examples/traffic-management/ingress-gateway-tls-passthrough.md"
---

TLS passthrough: the gateway forwards encrypted traffic; the backend pod terminates TLS.

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: nginx-gateway
  namespace: default
spec:
  selector:
    istio: ingressgateway
  servers:
    - port:
        number: 443
        name: tls
        protocol: TLS
      tls:
        mode: PASSTHROUGH       # do not decrypt; forward as-is
      hosts:
        - "nginx.example.com"
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: nginx
  namespace: default
spec:
  hosts:
    - "nginx.example.com"
  gateways:
    - nginx-gateway
  tls:
    - match:
        - port: 443
          sniHosts:
            - "nginx.example.com"
      route:
        - destination:
            host: nginx
            port:
              number: 443
```

The backend service must present a valid certificate for SNI `nginx.example.com`.
