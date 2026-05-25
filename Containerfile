# ---------------------------------------------------------------------------
# Stage 1: builder
# ---------------------------------------------------------------------------
# Installs Python dependencies, downloads the embedding model, then crawls
# both Kiali and Istio docs to build two FAISS/LlamaIndex vector databases.
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /workspace

# System libraries required by faiss-cpu and sentence-transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN pip install --no-cache-dir uv

# Install only runtime dependencies (no editable install needed in the image)
COPY pyproject.toml ./
RUN uv pip install --system --no-cache \
        llama-index-core \
        llama-index-vector-stores-faiss \
        llama-index-embeddings-huggingface \
        faiss-cpu \
        sentence-transformers \
        beautifulsoup4 \
        requests \
        pyyaml \
        tqdm

# Copy sources and config
COPY build_index.py config.yaml ./

# Build a single merged index (Kiali + Istio sources combined)
RUN python build_index.py \
        --config config.yaml \
        --output /rag/vector_db/kiali \
        --log-level INFO

# Fix permissions in the builder stage (ubi-micro has no shell utilities)
RUN find /rag/vector_db -type f -exec chmod 644 {} + && \
    find /rag/vector_db -type d -exec chmod 755 {} +

# ---------------------------------------------------------------------------
# Stage 2: final image
# ---------------------------------------------------------------------------
# Stores ONLY the vector database files.  The embedding model is intentionally
# NOT included here — OLS loads it from the path set in embeddings_model_path
# (typically the lightspeed-rag-content image or a locally extracted copy).
#
# Image layout consumed by OLS / the operator:
#   /rag/vector_db/kiali/
#     ├── default__vector_store.json   (Kiali + Istio docs merged)
#     ├── docstore.json
#     ├── graph_store.json
#     ├── index_store.json
#     └── metadata.json
# ---------------------------------------------------------------------------
FROM registry.access.redhat.com/ubi9/ubi-micro:latest

COPY --from=builder /rag/vector_db /rag/vector_db

LABEL org.opencontainers.image.title="kiali-byok" \
      org.opencontainers.image.description="Kiali and Istio BYOK vector databases for OpenShift Lightspeed" \
      org.opencontainers.image.source="https://github.com/kiali/kiali-byok" \
      org.opencontainers.image.licenses="Apache-2.0"

# No entrypoint — this image is only used as a data volume source.
# Usage (operator):
#   spec.ols.rag:
#     - image: quay.io/kiali/kiali_byok:latest
#       indexPath: /rag/vector_db/kiali
#       indexID: kiali-istio-docs
CMD ["true"]
