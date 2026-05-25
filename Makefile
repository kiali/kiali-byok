IMAGE_REGISTRY ?= quay.io
IMAGE_ORG      ?= kiali
IMAGE_NAME     ?= kiali-byok
IMAGE_TAG      ?= latest

IMAGE_REF = $(IMAGE_REGISTRY)/$(IMAGE_ORG)/$(IMAGE_NAME):$(IMAGE_TAG)

CONTAINER_TOOL  ?= podman
CONFIG          ?= config.yaml
VECTOR_DB_DIR   ?= vector_db/kiali
EMBEDDING_MODEL ?= sentence-transformers/all-mpnet-base-v2

VERSION        := $(shell cat VERSION | tr -d '[:space:]')

.DEFAULT_GOAL := help

.PHONY: version
version: ## Show current version from VERSION file
	@echo $(VERSION)

.PHONY: help
help: ## Show this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} \
	  /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# ---------------------------------------------------------------------------
# Local development
# ---------------------------------------------------------------------------

.PHONY: install
install: ## Install Python dependencies (requires uv)
	uv sync --extra dev

.PHONY: get-embeddings-model
get-embeddings-model: install ## Download the embedding model to ./embeddings_model
	uv run python -c "\
	from sentence_transformers import SentenceTransformer; \
	print('Downloading $(EMBEDDING_MODEL) ...'); \
	SentenceTransformer('$(EMBEDDING_MODEL)').save('./embeddings_model'); \
	print('Saved to ./embeddings_model')"

.PHONY: build-index
build-index: install ## Build the FAISS vector index locally (output: vector_db/kiali)
	uv run python build_index.py --config $(CONFIG) --output $(VECTOR_DB_DIR)

.PHONY: build-index-local
build-index-local: install ## Build index from a local docs directory (set LOCAL_PATH=./docs)
	uv run python build_index.py --config $(CONFIG) \
	  --source-type local \
	  --local-path "$(LOCAL_PATH)" \
	  --output $(VECTOR_DB_DIR)

.PHONY: validate-index
validate-index: ## Validate the built index (vector_db/kiali)
	uv run python -c "\
	import json, sys; \
	from pathlib import Path; \
	required = ['default__vector_store.json','docstore.json','index_store.json','metadata.json']; \
	missing = [f for f in required if not (Path('$(VECTOR_DB_DIR)') / f).exists()]; \
	sys.exit(1) if missing else print('OK:', json.loads((Path('$(VECTOR_DB_DIR)') / 'metadata.json').read_text()))"

# ---------------------------------------------------------------------------
# Container image
# ---------------------------------------------------------------------------

.PHONY: image-build
image-build: ## Build the BYOK container image
	$(CONTAINER_TOOL) build \
	  --tag $(IMAGE_REF) \
	  --file Containerfile \
	  .

.PHONY: image-push
image-push: ## Push the BYOK container image to the registry
	$(CONTAINER_TOOL) push $(IMAGE_REF)

.PHONY: image-build-push
image-build-push: image-build image-push ## Build and push the container image

# ---------------------------------------------------------------------------
# Extract index from image (for local testing with OLS)
# ---------------------------------------------------------------------------

.PHONY: extract-index
extract-index: ## Extract the merged index from the image into ./vector_db/kiali
	$(CONTAINER_TOOL) create --replace --name tmp-kiali-byok $(IMAGE_REF) true
	mkdir -p vector_db
	$(CONTAINER_TOOL) cp tmp-kiali-byok:/rag/vector_db/kiali $(VECTOR_DB_DIR)
	$(CONTAINER_TOOL) rm tmp-kiali-byok
	@echo "Index extracted to $(VECTOR_DB_DIR)"
	@echo ""
	@echo "Add the following to your olsconfig.yaml:"
	@echo ""
	@echo "  ols_config:"
	@echo "    reference_content:"
	@echo "      embeddings_model_path: ./embeddings_model"
	@echo "      indexes:"
	@echo "        - product_docs_index_path: ./$(VECTOR_DB_DIR)"
	@echo "          product_docs_index_id: kiali-istio-docs"

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

.PHONY: test
test: ## Run unit tests
	uv run pytest tests/ -v

.PHONY: lint
lint: ## Run linting
	uv run ruff check build_index.py

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

.PHONY: clean
clean: ## Remove generated vector_db directory
	rm -rf vector_db embeddings_model __pycache__ .pytest_cache .ruff_cache
