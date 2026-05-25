# Development Guide

This document covers how to set up a local development environment to build and test the Kiali BYOK index against a running OpenShift Lightspeed Service (OLS).

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | ≥ 3.11 | |
| [uv](https://docs.astral.sh/uv/) | latest | `pip install uv` |
| podman | any recent | or docker |
| An LLM API key | — | OpenAI, Azure, WatsonX, etc. |

---

## 1. Install Python dependencies

```sh
make install
```

This runs `uv sync --extra dev` and creates a `.venv` inside the project.

---

## 2. Build the index locally

```sh
make build-index
```

This crawls both kiali.io and istio.io and merges all documents into a single index:

```
vector_db/
└── kiali/    ← combined Kiali + Istio knowledge
```

> The first run downloads `sentence-transformers/all-mpnet-base-v2` (~420 MB) from HuggingFace. Subsequent runs reuse the cache.

---

## 3. Download the embedding model

OLS needs the embedding model at query time. Generate it from the already-downloaded HuggingFace cache:

```sh
make get-embeddings-model
```

This saves the model to `./embeddings_model/`.

---

## 4. Configure OLS

Create (or update) your `dev_olsconfig.yaml`:

```yaml
llm_providers:
  - name: openai
    type: openai
    credentials_path: /app-root/.openai
    models:
      - name: gpt-4o-mini

ols_config:
  default_provider: openai
  default_model: gpt-4o-mini

  logging_config:
    app_log_level: info      # set to "debug" to see retrieved doc details
    lib_log_level: warning
    uvicorn_log_level: warning

  reference_content:
    embeddings_model_path: ./embeddings_model
      indexes:
      - product_docs_index_path: ./vector_db/kiali
        product_docs_index_id: kiali-istio-docs
```

---

## 5. Run OLS locally with podman

Set your project path and run:

```sh
export BYOK_DOCS="$(pwd)"   # run from kiali_byok/ root

podman run -it --rm \
  -v /path/to/dev_olsconfig.yaml:/app-root/config/olsconfig.yaml:Z \
  -v ~/.openai:/app-root/.openai:Z \
  -v "${BYOK_DOCS}/vector_db:/app-root/vector_db:Z" \
  -v "${BYOK_DOCS}/embeddings_model:/app-root/embeddings_model:Z" \
  -e OLS_CONFIG_FILE=/app-root/config/olsconfig.yaml \
  -p 8080:8080 \
  quay.io/openshift-lightspeed/lightspeed-service-api:latest
```

---

## 6. Test a query

```sh
curl -s -X POST http://localhost:8080/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I configure traffic management in Kiali?"}' \
  | python3 -m json.tool
```

### Confirm RAG is working

Look for these lines in the OLS logs:

```
INFO: Retrieved 5 documents from indexes
INFO: Retrieved doc #1: title='Traffic Management', url='https://kiali.io/docs/...', score=0.48
```

If you see `rag=0` in the token budget log or the warning `Proceeding without RAG content`, check:
- The `vector_db/` mount is correct inside the container
- The `embeddings_model/` mount is correct
- The `product_docs_index_id` in the config matches the `index-id` in `vector_db/kiali/metadata.json`

---

## 7. Validate indexes without running OLS

```sh
make validate-index
```

---

## 8. Rebuild after changing docs sources

If you update `config.yaml` (e.g. to add URL prefixes, add a new source, or change chunk size), re-run the build and restart OLS:

```sh
make build-index
```

---

## Useful make targets

```sh
make help               # list all targets
make build-index           # build merged Kiali+Istio FAISS index
make get-embeddings-model  # download embedding model locally
make validate-index     # validate both index directories
make image-build        # build container image locally
make extract-index      # extract indexes from the built image
make clean              # remove vector_db/, embeddings_model/
```
