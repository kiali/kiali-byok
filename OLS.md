# Enhancing OpenShift Lightspeed with Kiali and Istio Knowledge

## Overview

This guide explains how to extend the intelligence of OpenShift Lightspeed by integrating specialized knowledge for **Kiali** and **Istio**. By configuring a custom Retrieval-Augmented Generation (RAG) database, you ensure the service provides precise, context-aware assistance for your service mesh queries.

The OpenShift Lightspeed service leverages Large Language Models (LLMs) to provide intelligent, context-aware responses. To ensure the model has deep expertise in your specific environment, you can use the Bring Your Own Knowledge (BYOK) tool to integrate a RAG database.

By connecting this database, you bridge the gap between general AI knowledge and specific technical documentation, ensuring more accurate troubleshooting and configuration advice for service mesh workloads.

---

## Pre-packaged Knowledge

We have curated and optimized specialized knowledge sets for the following components:

| Component | Description |
|-----------|-------------|
| **Kiali** | Observability console for Istio — topology, health, traffic management, tracing |
| **Istio** | Service mesh platform — traffic management, security (mTLS), observability, resiliency |

Because Kiali and Istio are tightly related, both knowledge bases are **merged into a single index** at build time for richer, unified context. The image is published at:

```
quay.io/kiali/kiali-byok:v0.0.1
```

---

## Prerequisites

- You are logged in to the OpenShift Container Platform web console as a user with the `cluster-admin` role.
- You have an LLM provider available for use with the OpenShift Lightspeed Service.
- You have installed and configured the **OpenShift Lightspeed Operator**.

---

## Configure OLSConfig CR (Operator)

Modify the `OLSConfig` CR to deploy the pre-packaged RAG database alongside the existing one:

1. In the OpenShift Container Platform web console, click **Operators → Installed Operators**.
2. Select **All Projects** in the Project dropdown.
3. Click **OpenShift Lightspeed Operator**.
4. Click **OLSConfig**, then click the **cluster** configuration instance in the list.
5. Click the **YAML** tab.
6. Insert the `spec.ols.rag` section as shown below and click **Save**.

### Example `OLSConfig` CR

```yaml
apiVersion: ols.openshift.io/v1alpha1
kind: OLSConfig
metadata:
  name: cluster
spec:
  ols:
    rag:
      - image: quay.io/kiali/kiali-byok:v0.0.1
        indexPath: /rag/vector_db/kiali
        indexID: kiali-istio-docs
```

> **Note:** Kiali and Istio documentation are merged into a single index (`kiali-istio-docs`) at build time, so only one entry is needed in the CR.

---

## Verify the integration

After saving, the operator will restart the Lightspeed pod with the new indexes mounted. To confirm the indexes loaded correctly, check the pod logs:

```sh
oc logs -n openshift-lightspeed deployment/lightspeed-app-server | grep -E "vector index|All indexes"
```

Expected output:

```
INFO: Loading vector index #0...
INFO: Vector index #0 is loaded.
INFO: Loading vector index #1...
INFO: Vector index #1 is loaded.
INFO: All indexes are loaded.
```

Once loaded, Lightspeed will automatically retrieve relevant Kiali and Istio documentation when answering service mesh questions, and cite the source pages in its responses.

---

## Available image tags

| Tag | Contents |
|-----|----------|
| `latest` | Most recent build from `main` branch |
| `v0.0.1` | First stable release |

See the [releases page](https://github.com/kiali/kiali-byok/releases) for the full list.
