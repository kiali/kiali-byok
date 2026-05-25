# kiali-byok

**BYOK (Bring Your Own Knowledge)** vector database builder for [Kiali](https://kiali.io) and [Istio](https://istio.io) documentation.

The generated container image can be consumed directly by [OpenShift Lightspeed Service (OLS)](https://github.com/openshift/lightspeed-service) to give the AI assistant knowledge about Kiali and the Istio service mesh ecosystem.

| Document | Description |
|----------|-------------|
| [OLS.md](OLS.md) | How to configure the pre-packaged image in OpenShift Lightspeed (operator CR) |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Local development environment setup and testing against a running OLS instance |

---

## How it works

```
Kiali docs (web or local)
        │
        ▼
  build_index.py
  ┌──────────────────────────────────────────────┐
  │  1. Fetch pages from kiali.io sitemap        │
  │  2. Chunk text with SentenceSplitter         │
  │  3. Embed with sentence-transformers model   │
  │     (all-mpnet-base-v2, 768 dims)            │
  │  4. Store in FAISS IndexFlatIP               │
  │  5. Persist via LlamaIndex storage context   │
  └──────────────────────────────────────────────┘
        │
        ▼
  vector_db/kiali/
    ├── default__vector_store.json
    ├── docstore.json
    ├── graph_store.json
    ├── index_store.json
    └── metadata.json
        │
        ▼
  Containerfile (multi-stage)
  └─► quay.io/kiali/kiali-byok:latest
        │
        ▼
  OLS olsconfig.yaml
  └─► reference_content.indexes
```

The embedding model used to build the index **must match** the model OLS uses at query time (`embeddings_model_path`).  The default model for both is `sentence-transformers/all-mpnet-base-v2`.

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | ≥ 3.11 |
| uv | latest |
| podman or docker | any recent |

---

## Quick start — build the index locally

```sh
# 1. Clone
git clone https://github.com/kiali/kiali-byok.git
cd kiali-byok

# 2. Install dependencies
make install

# 3. Build the index (crawls kiali.io — takes a few minutes)
make build-index

# 4. Verify the output
make validate-index
```

The index is written to `vector_db/kiali/`.

---

## Build from a local docs clone (faster, offline)

```sh
# Clone the Kiali docs site
git clone https://github.com/kiali/kiali.io.git

# Build from local markdown files
make build-index-local LOCAL_PATH=./kiali.io/content/en/docs
```

---

## Build and push the container image

```sh
# Build image
make image-build IMAGE_ORG=<your-org>

# Push
make image-push IMAGE_ORG=<your-org>

# Or both at once
make image-build-push IMAGE_ORG=<your-org> IMAGE_TAG=v1.0.0
```

---

## Use with OpenShift Lightspeed Service

### 1. Extract the vector database from the image

```sh
podman create --replace --name tmp-kiali-byok quay.io/kiali/kiali-byok:latest true
podman cp tmp-kiali-byok:/rag/vector_db/kiali ./vector_db/kiali
podman rm tmp-kiali-byok
```

Or run `make extract-index` which does the above and prints the config snippet.

### 2. Configure OLS

Add the Kiali index to your `olsconfig.yaml`.  You can combine it with the standard OCP product docs index:

```yaml
ols_config:
  reference_content:
    embeddings_model_path: ./embeddings_model   # from lightspeed-rag-content image
    indexes:
      - product_docs_index_path: ./vector_db/ocp_product_docs/4.19
        product_docs_index_id: ocp-product-docs-4_19
      - product_docs_index_path: ./vector_db/kiali
        product_docs_index_id: kiali-docs
```

The `product_docs_index_id` must match the `index-id` field in `vector_db/kiali/metadata.json`.

### 3. (Operator) Use the image directly

If you use the OLS Operator you can reference the BYOK image in the `OLSConfig` CR:

```yaml
spec:
  ols:
    rag:
      - image: quay.io/kiali/kiali-byok:latest
        indexPath: /rag/vector_db/kiali
        indexID: kiali-docs
```

---

## Confirming OLS loaded the index

At `DEBUG` log level, OLS will print:

```
DEBUG: Config used for index load: ... indexes=[..., ReferenceContentIndex(product_docs_index_path='./vector_db/kiali', product_docs_index_id='kiali-docs')]
INFO:  Loading vector index #N...
INFO:  Vector index #N is loaded.
INFO:  All indexes are loaded.
```

---

## Configuration reference

All settings live in `config.yaml`:

| Key | Default | Description |
|-----|---------|-------------|
| `index_id` | `kiali-docs` | Must match `product_docs_index_id` in OLS config |
| `source.type` | `web` | `web` or `local` |
| `source.base_url` | `https://kiali.io` | Base URL for web crawl |
| `source.sitemap_path` | `/sitemap.xml` | Path to sitemap |
| `source.url_prefixes` | `["/docs/"]` | Only crawl these URL paths |
| `source.max_pages` | `500` | Cap on pages fetched (0 = unlimited) |
| `source.local_path` | `./docs` | Directory for `local` source type |
| `embedding_model` | `sentence-transformers/all-mpnet-base-v2` | HuggingFace model name |
| `chunk_size` | `512` | Token chunk size |
| `chunk_overlap` | `64` | Chunk overlap in tokens |
| `output_path` | `./vector_db/kiali` | Where to write the persisted index |

CLI flags (`python build_index.py --help`) can override any of these.

---

## Vector database format

The index follows the **LlamaIndex persistence format** with a FAISS backend, identical to OCP product docs indexes:

```
vector_db/kiali/
├── default__vector_store.json   # FAISS vectors (Base64-encoded)
├── docstore.json                # LlamaIndex document store
├── graph_store.json             # LlamaIndex graph store
├── index_store.json             # Index registry (contains index-id)
└── metadata.json                # BYOK metadata { "index-id": "kiali-docs", ... }
```

Each indexed node carries the metadata fields expected by OLS:
- `title` — page title (shown in citations)
- `docs_url` — source URL (shown in citations)

---

## Development

```sh
# Run tests
make test

# Lint
make lint

# Clean generated artifacts
make clean
```

---

## CI / CD

GitHub Actions automatically builds and pushes the image on every push to `main` and on version tags.

Required secrets:
- `QUAY_USERNAME` — Quay.io robot account username
- `QUAY_PASSWORD` — Quay.io robot account password (or OAuth token)

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
