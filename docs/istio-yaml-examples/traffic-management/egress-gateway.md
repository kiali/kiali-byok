---
title: "Egress Gateway for External HTTPS"
category: traffic-management
description: "Route outbound traffic to external services through a dedicated Istio egress gateway."
istio_versions: ["1.20", "1.21", "1.22", "1.23", "1.24"]
crd_types: ["ServiceEntry", "Gateway", "VirtualService", "DestinationRule"]
docs_url: "https://github.com/kiali/kiali-byok/blob/main/docs/istio-yaml-examples/traffic-management/egress-gateway.md"
---

Egress gateway: control and observe traffic leaving the mesh to an external API.

```yaml
# Register the external host in the mesh
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
  namespace: default
spec:
  hosts:
    - api.external.com
  ports:
    - number: 443
      name: https
      protocol: HTTPS
  resolution: DNS
---
# Egress gateway listener for HTTPS
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: istio-egressgateway
  namespace: istio-system
spec:
  selector:
    istio: egressgateway
  servers:
    - port:
        number: 443
        name: https
        protocol: HTTPS
      hosts:
        - api.external.com
      tls:
        mode: ISTIO_MUTUAL       # mTLS between sidecar and egress gateway
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: egressgateway-for-external-api
  namespace: istio-system
spec:
  host: istio-egressgateway.istio-system.svc.cluster.local
  subsets:
    - name: external-api
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: direct-external-api-through-egress-gateway
  namespace: default
spec:
  hosts:
    - api.external.com
  gateways:
    - mesh
    - istio-system/istio-egressgateway
  tls:
    - match:
        - gateways:
            - mesh
          port: 443
          sniHosts:
            - api.external.com
      route:
        - destination:
            host: istio-egressgateway.istio-system.svc.cluster.local
            subset: external-api
            port:
              number: 443
    - match:
        - gateways:
            - istio-egressgateway
          port: 443
          sniHosts:
            - api.external.com
      route:
        - destination:
            host: api.external.com
            port:
              number: 443
          weight: 100
```

Enable egress gateway: `istioctl install --set components.egressGateways[0].enabled=true`
