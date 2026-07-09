#!/usr/bin/env python3
"""Build a LlamaIndex FAISS vector index from Kiali documentation.

The generated index is compatible with OpenShift Lightspeed Service (OLS)
and can be packaged into a BYOK container image.

Expected node metadata (consumed by OLS):
  - title    : page / section title
  - docs_url : canonical URL of the source page
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

import requests
import yaml
from bs4 import BeautifulSoup
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


# ---------------------------------------------------------------------------
# Document loading helpers
# ---------------------------------------------------------------------------


def _get_sitemap_urls(base_url: str, sitemap_path: str) -> list[str]:
    """Return all <loc> URLs from a sitemap.xml (handles sitemap indexes)."""
    sitemap_url = base_url.rstrip("/") + sitemap_path
    logger.info("Fetching sitemap: %s", sitemap_url)
    try:
        resp = requests.get(sitemap_url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Failed to fetch sitemap %s: %s", sitemap_url, exc)
        return []

    root = ET.fromstring(resp.content)
    tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag

    if tag == "sitemapindex":
        # Recursive: each <sitemap><loc> points to another sitemap
        sub_sitemaps = [
            el.text
            for el in root.findall(f".//{{{SITEMAP_NS}}}loc")
            if el.text
        ]
        urls: list[str] = []
        for sub in sub_sitemaps:
            try:
                sub_resp = requests.get(sub, timeout=30)
                sub_resp.raise_for_status()
                sub_root = ET.fromstring(sub_resp.content)
                urls.extend(
                    el.text
                    for el in sub_root.findall(f".//{{{SITEMAP_NS}}}loc")
                    if el.text
                )
            except requests.RequestException as exc:
                logger.warning("Skipping sub-sitemap %s: %s", sub, exc)
        return urls

    # Plain sitemap
    return [
        el.text
        for el in root.findall(f".//{{{SITEMAP_NS}}}loc")
        if el.text
    ]


def _fetch_page(url: str, timeout: int = 30) -> Optional[tuple[str, str, str]]:
    """Fetch a URL and return (url, title, text) or None on failure."""
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "kiali-byok/1.0"})
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.debug("Skipping %s: %s", url, exc)
        return None

    soup = BeautifulSoup(resp.content, "html.parser")

    # Title: prefer <h1>, fallback to <title>
    h1 = soup.find("h1")
    title_tag = soup.find("title")
    if h1:
        title = h1.get_text(strip=True)
    elif title_tag:
        title = title_tag.get_text(strip=True).split("|")[0].strip()
    else:
        title = url

    # Main content: try common semantic containers
    content = (
        soup.find("main")
        or soup.find("article")
        or soup.find(id="content")
        or soup.find(class_="content")
        or soup.find("body")
    )
    if content is None:
        return None

    for tag in content.find_all(["nav", "footer", "header", "script", "style", "aside"]):
        tag.decompose()

    text = content.get_text(separator="\n", strip=True)
    if len(text) < 100:
        return None

    return url, title, text


def load_documents_from_web(cfg: dict) -> list:
    """Crawl kiali.io using its sitemap and return LlamaIndex Document objects."""
    from llama_index.core import Document

    base_url = cfg["base_url"].rstrip("/")
    sitemap_path = cfg.get("sitemap_path", "/sitemap.xml")
    url_prefixes = cfg.get("url_prefixes", [])
    max_pages = cfg.get("max_pages", 0)
    request_timeout = cfg.get("request_timeout", 30)
    crawl_delay = cfg.get("crawl_delay", 0.1)

    all_urls = _get_sitemap_urls(base_url, sitemap_path)
    logger.info("Sitemap contains %d URLs", len(all_urls))

    # Filter by prefix if configured
    if url_prefixes:
        filtered = [
            u for u in all_urls
            if any(u.startswith(base_url + p) for p in url_prefixes)
        ]
        logger.info(
            "Filtered to %d URLs matching prefixes %s", len(filtered), url_prefixes
        )
        all_urls = filtered

    if max_pages and len(all_urls) > max_pages:
        logger.info("Capping at %d pages (max_pages setting)", max_pages)
        all_urls = all_urls[:max_pages]

    documents: list[Document] = []
    for url in tqdm(all_urls, desc="Fetching pages"):
        result = _fetch_page(url, timeout=request_timeout)
        if result:
            page_url, title, text = result
            documents.append(
                Document(
                    text=text,
                    metadata={"title": title, "docs_url": page_url},
                )
            )
        if crawl_delay > 0:
            time.sleep(crawl_delay)

    logger.info("Fetched %d documents from the web", len(documents))
    return documents


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse optional YAML frontmatter from a markdown document."""
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    try:
        frontmatter = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return {}, text

    if not isinstance(frontmatter, dict):
        return {}, text

    body = parts[2].lstrip("\n")
    return frontmatter, body


def _build_local_document_text(frontmatter: dict, body: str) -> str:
    """Prepend structured metadata so embeddings capture example context."""
    header_lines: list[str] = []
    if title := frontmatter.get("title"):
        header_lines.append(f"# {title}")
    if category := frontmatter.get("category"):
        header_lines.append(f"Category: {category}")
    if versions := frontmatter.get("istio_versions"):
        if isinstance(versions, list):
            header_lines.append(f"Istio versions: {', '.join(str(v) for v in versions)}")
        else:
            header_lines.append(f"Istio versions: {versions}")
    if crds := frontmatter.get("crd_types"):
        if isinstance(crds, list):
            header_lines.append(f"CRDs: {', '.join(crds)}")
        else:
            header_lines.append(f"CRDs: {crds}")
    if description := frontmatter.get("description"):
        header_lines.append(description)

    if not header_lines:
        return body
    return "\n\n".join(header_lines) + "\n\n" + body


def load_documents_from_local(cfg: dict) -> list:
    """Read markdown/text/HTML files from a local directory."""
    from llama_index.core import Document

    local_path = Path(cfg.get("local_path", "./docs"))
    extensions = cfg.get("file_extensions", [".md", ".rst", ".txt", ".html"])
    logger.info("Reading local files from %s (extensions: %s)", local_path, extensions)

    if not local_path.exists():
        logger.warning("Local path does not exist: %s", local_path)
        return []

    documents: list[Document] = []
    for file_path in sorted(local_path.rglob("*")):
        if not file_path.is_file() or file_path.suffix not in extensions:
            continue

        raw_text = file_path.read_text(encoding="utf-8")
        frontmatter, body = _parse_frontmatter(raw_text)
        text = _build_local_document_text(frontmatter, body)
        if len(text.strip()) < 50:
            logger.debug("Skipping short local file: %s", file_path)
            continue

        rel_path = file_path.relative_to(local_path)
        title = frontmatter.get("title") or file_path.stem.replace("-", " ").title()
        docs_url = frontmatter.get(
            "docs_url",
            f"file://{file_path.resolve()}",
        )

        metadata = {
            "title": title,
            "docs_url": docs_url,
            "file_name": file_path.name,
            "file_path": str(file_path.resolve()),
        }
        for key in ("category", "description"):
            if key in frontmatter:
                metadata[key] = frontmatter[key]
        if versions := frontmatter.get("istio_versions"):
            metadata["istio_versions"] = (
                ", ".join(str(v) for v in versions)
                if isinstance(versions, list)
                else str(versions)
            )
        if crds := frontmatter.get("crd_types"):
            metadata["crd_types"] = (
                ", ".join(crds) if isinstance(crds, list) else str(crds)
            )

        documents.append(Document(text=text, metadata=metadata))

    logger.info("Loaded %d documents from local path", len(documents))
    return documents


def load_documents(cfg: dict) -> list:
    """Load documents from a single source config dict."""
    source_type = cfg.get("type")
    if source_type == "web":
        return load_documents_from_web(cfg)
    elif source_type == "local":
        return load_documents_from_local(cfg)
    else:
        raise ValueError(f"Unknown source type: {source_type!r}. Use 'web' or 'local'.")


# ---------------------------------------------------------------------------
# Index building
# ---------------------------------------------------------------------------


def build_index(config: dict) -> None:
    """Build and persist a FAISS vector index from one or more configured sources."""
    import faiss
    from llama_index.core import Settings, VectorStoreIndex
    from llama_index.core.node_parser import SentenceSplitter
    from llama_index.core.storage.storage_context import StorageContext
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    from llama_index.vector_stores.faiss import FaissVectorStore

    index_id = config["index_id"]
    output_path = config["output_path"]
    embedding_model_name = config["embedding_model"]
    chunk_size = config.get("chunk_size", 512)
    chunk_overlap = config.get("chunk_overlap", 64)

    logger.info("Embedding model: %s", embedding_model_name)
    embed_model = HuggingFaceEmbedding(model_name=embedding_model_name)
    Settings.embed_model = embed_model
    Settings.llm = None  # No LLM needed for indexing

    # Support both legacy single `source:` and new `sources:` list
    if "sources" in config:
        documents = []
        for i, source in enumerate(config["sources"]):
            logger.info("Loading source %d/%d (%s: %s)...",
                        i + 1, len(config["sources"]),
                        source.get("type"), source.get("base_url") or source.get("local_path"))
            docs = load_documents(source)
            documents.extend(docs)
            logger.info("Source %d contributed %d documents (total so far: %d)",
                        i + 1, len(docs), len(documents))
    elif "source" in config:
        documents = load_documents(config["source"])
    else:
        raise ValueError("Config must have a 'source' or 'sources' key.")

    if not documents:
        raise RuntimeError("No documents loaded — check your source configuration.")

    logger.info("Splitting %d documents into chunks (size=%d, overlap=%d)...",
                len(documents), chunk_size, chunk_overlap)
    splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    nodes = splitter.get_nodes_from_documents(documents, show_progress=True)
    logger.info("Created %d nodes", len(nodes))

    # Determine embedding dimension
    sample_embedding = embed_model.get_text_embedding("kiali")
    embed_dim = len(sample_embedding)
    logger.info("Embedding dimension: %d", embed_dim)

    # Inner product index (cosine similarity with L2-normalized embeddings)
    faiss_index = faiss.IndexFlatIP(embed_dim)
    vector_store = FaissVectorStore(faiss_index=faiss_index)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    logger.info("Building FAISS index (index_id=%s)...", index_id)
    index = VectorStoreIndex(
        nodes=nodes,
        storage_context=storage_context,
        show_progress=True,
    )
    index.set_index_id(index_id)

    # Persist to disk
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Persisting index to %s", output_dir)
    index.storage_context.persist(persist_dir=str(output_dir))

    # Write metadata.json (used by OLS to locate the index by id)
    metadata = {
        "index-id": index_id,
        "name": config.get("index_name", index_id),
        "embedding-model": embedding_model_name,
        "chunk-size": chunk_size,
        "chunk-overlap": chunk_overlap,
        "num-documents": len(documents),
        "num-nodes": len(nodes),
    }
    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info("Wrote metadata.json: %s", metadata)
    logger.info("Index build complete. Output: %s", output_dir.resolve())


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a LlamaIndex FAISS vector index for Kiali docs (OLS BYOK).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build from web (uses config.yaml defaults)
  python build_index.py

  # Build from a local docs clone
  python build_index.py --source-type local --local-path ./kiali.io/content/en/docs

  # Override output directory
  python build_index.py --output ./vector_db/kiali
""",
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        metavar="FILE",
        help="Path to the YAML configuration file (default: config.yaml)",
    )
    parser.add_argument(
        "--source-type",
        choices=["web", "local"],
        help="Override the source type from the config",
    )
    parser.add_argument(
        "--local-path",
        help="Override the local source path",
    )
    parser.add_argument(
        "--output",
        dest="output_path",
        help="Override the output directory",
    )
    parser.add_argument(
        "--index-id",
        help="Override the index ID",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        help="Override max_pages for web source",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.getLogger().setLevel(args.log_level)

    config_path = Path(args.config)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Apply CLI overrides
    # For multi-source configs these override the first source only.
    first_source = (config.get("sources") or [config.get("source", {})])[0]
    if args.source_type:
        first_source["type"] = args.source_type
    if args.local_path:
        first_source["local_path"] = args.local_path
    if args.max_pages is not None:
        first_source["max_pages"] = args.max_pages
    if args.output_path:
        config["output_path"] = args.output_path
    if args.index_id:
        config["index_id"] = args.index_id

    sources = config.get("sources", [config["source"]] if "source" in config else [])
    source_summary = ", ".join(
        f"{s.get('type')}:{s.get('base_url') or s.get('local_path', '?')}"
        for s in sources
    )
    logger.info("Configuration: index_id=%s, sources=[%s], output=%s",
                config["index_id"], source_summary, config["output_path"])

    build_index(config)


if __name__ == "__main__":
    main()
