"""Unit tests for build_index.py helper functions."""

from __future__ import annotations

import json
import textwrap
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests
import responses as resp_lib
import yaml


# ---------------------------------------------------------------------------
# Helpers under test (imported lazily to avoid heavy llama_index deps)
# ---------------------------------------------------------------------------


def _import_helpers():
    """Import lightweight helpers that do not pull in llama_index."""
    import importlib
    import sys
    import types

    core = types.ModuleType("llama_index.core")
    node_parser = types.ModuleType("llama_index.core.node_parser")
    storage = types.ModuleType("llama_index.core.storage")
    storage_context = types.ModuleType("llama_index.core.storage.storage_context")
    embeddings = types.ModuleType("llama_index.embeddings.huggingface")
    vector_stores = types.ModuleType("llama_index.vector_stores.faiss")
    faiss_mod = types.ModuleType("faiss")

    core.Document = MagicMock()
    core.Settings = MagicMock()
    core.VectorStoreIndex = MagicMock()
    node_parser.SentenceSplitter = MagicMock()
    storage_context.StorageContext = MagicMock()
    embeddings.HuggingFaceEmbedding = MagicMock()
    vector_stores.FaissVectorStore = MagicMock()
    faiss_mod.IndexFlatIP = MagicMock()

    sys.modules["llama_index"] = types.ModuleType("llama_index")
    sys.modules["llama_index.core"] = core
    sys.modules["llama_index.core.node_parser"] = node_parser
    sys.modules["llama_index.core.storage"] = storage
    sys.modules["llama_index.core.storage.storage_context"] = storage_context
    sys.modules["llama_index.embeddings"] = types.ModuleType("llama_index.embeddings")
    sys.modules["llama_index.embeddings.huggingface"] = embeddings
    sys.modules["llama_index.vector_stores"] = types.ModuleType("llama_index.vector_stores")
    sys.modules["llama_index.vector_stores.faiss"] = vector_stores
    sys.modules["faiss"] = faiss_mod

    tqdm_mock = types.ModuleType("tqdm")
    tqdm_mock.tqdm = lambda iterable, **kw: iterable
    sys.modules["tqdm"] = tqdm_mock

    if "build_index" in sys.modules:
        import build_index
        return importlib.reload(build_index)

    import build_index

    return build_index


# ---------------------------------------------------------------------------
# _get_sitemap_urls
# ---------------------------------------------------------------------------


SITEMAP_XML = textwrap.dedent(
    """\
    <?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://kiali.io/docs/overview/</loc></url>
      <url><loc>https://kiali.io/docs/installation/</loc></url>
      <url><loc>https://kiali.io/blog/post1/</loc></url>
    </urlset>
    """
)

SITEMAP_INDEX_XML = textwrap.dedent(
    """\
    <?xml version="1.0" encoding="UTF-8"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <sitemap><loc>https://kiali.io/sitemap-docs.xml</loc></sitemap>
    </sitemapindex>
    """
)

SUB_SITEMAP_XML = textwrap.dedent(
    """\
    <?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://kiali.io/docs/faq/</loc></url>
    </urlset>
    """
)


@resp_lib.activate
def test_get_sitemap_urls_plain():
    bi = _import_helpers()
    resp_lib.add(
        resp_lib.GET,
        "https://kiali.io/sitemap.xml",
        body=SITEMAP_XML,
        status=200,
        content_type="application/xml",
    )
    urls = bi._get_sitemap_urls("https://kiali.io", "/sitemap.xml")
    assert urls == [
        "https://kiali.io/docs/overview/",
        "https://kiali.io/docs/installation/",
        "https://kiali.io/blog/post1/",
    ]


@resp_lib.activate
def test_get_sitemap_urls_index():
    bi = _import_helpers()
    resp_lib.add(
        resp_lib.GET,
        "https://kiali.io/sitemap.xml",
        body=SITEMAP_INDEX_XML,
        status=200,
        content_type="application/xml",
    )
    resp_lib.add(
        resp_lib.GET,
        "https://kiali.io/sitemap-docs.xml",
        body=SUB_SITEMAP_XML,
        status=200,
        content_type="application/xml",
    )
    urls = bi._get_sitemap_urls("https://kiali.io", "/sitemap.xml")
    assert urls == ["https://kiali.io/docs/faq/"]


@resp_lib.activate
def test_get_sitemap_urls_network_error():
    bi = _import_helpers()
    resp_lib.add(
        resp_lib.GET,
        "https://kiali.io/sitemap.xml",
        body=requests.exceptions.ConnectionError("connection error"),
    )
    urls = bi._get_sitemap_urls("https://kiali.io", "/sitemap.xml")
    assert urls == []


# ---------------------------------------------------------------------------
# _fetch_page
# ---------------------------------------------------------------------------

PAGE_HTML = textwrap.dedent(
    """\
    <html>
    <head><title>Kiali Overview | Kiali</title></head>
    <body>
      <main>
        <h1>Kiali Overview</h1>
        <p>Kiali is an observability console for Istio service mesh.</p>
        <p>It provides topology, health, and tracing information.</p>
      </main>
    </body>
    </html>
    """
)


@resp_lib.activate
def test_fetch_page_success():
    bi = _import_helpers()
    resp_lib.add(
        resp_lib.GET,
        "https://kiali.io/docs/overview/",
        body=PAGE_HTML,
        status=200,
        content_type="text/html",
    )
    result = bi._fetch_page("https://kiali.io/docs/overview/")
    assert result is not None
    url, title, text = result
    assert url == "https://kiali.io/docs/overview/"
    assert "Kiali Overview" in title
    assert "Istio service mesh" in text


@resp_lib.activate
def test_fetch_page_404():
    bi = _import_helpers()
    resp_lib.add(
        resp_lib.GET,
        "https://kiali.io/docs/missing/",
        status=404,
    )
    result = bi._fetch_page("https://kiali.io/docs/missing/")
    assert result is None


@resp_lib.activate
def test_fetch_page_short_content():
    bi = _import_helpers()
    resp_lib.add(
        resp_lib.GET,
        "https://kiali.io/docs/stub/",
        body="<html><body><main><p>Hi</p></main></body></html>",
        status=200,
    )
    result = bi._fetch_page("https://kiali.io/docs/stub/")
    assert result is None  # content < 100 chars


# ---------------------------------------------------------------------------
# config loading & CLI overrides
# ---------------------------------------------------------------------------


def test_config_yaml_is_valid(tmp_path):
    """The shipped config.yaml must be parseable and contain required keys."""
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path) as f:
        cfg = yaml.safe_load(f)
    assert "index_id" in cfg
    assert "sources" in cfg
    assert len(cfg["sources"]) >= 1
    assert any(s.get("type") == "web" for s in cfg["sources"])
    assert any(s.get("type") == "local" for s in cfg["sources"])
    assert "embedding_model" in cfg
    assert "output_path" in cfg


def test_parse_frontmatter():
    bi = _import_helpers()
    text = "---\ntitle: Test\ncategory: security\n---\n\nBody content here."
    frontmatter, body = bi._parse_frontmatter(text)
    assert frontmatter["title"] == "Test"
    assert body.startswith("Body content")


def test_build_local_document_text():
    bi = _import_helpers()
    frontmatter = {
        "title": "Canary",
        "category": "traffic-management",
        "istio_versions": ["1.24"],
        "crd_types": ["VirtualService"],
        "description": "Canary routing example.",
    }
    text = bi._build_local_document_text(frontmatter, "Example body.")
    assert "# Canary" in text
    assert "traffic-management" in text
    assert "VirtualService" in text
    assert "Example body." in text


def test_metadata_json_written(tmp_path, monkeypatch):
    """build_index() writes a metadata.json with the correct index-id."""
    bi = _import_helpers()

    # Patch the document loader and llama_index pieces
    dummy_doc = MagicMock()
    dummy_doc.text = "Hello Kiali " * 50
    dummy_doc.metadata = {"title": "Test", "docs_url": "https://example.com"}

    with patch.object(bi, "load_documents_from_web", return_value=[dummy_doc]):
        with patch("llama_index.embeddings.huggingface.HuggingFaceEmbedding") as hfe:
            hfe.return_value.get_text_embedding.return_value = [0.0] * 768
            with patch("llama_index.vector_stores.faiss.FaissVectorStore"):
                with patch("llama_index.core.storage.storage_context.StorageContext"):
                    with patch("llama_index.core.VectorStoreIndex") as vi_cls:
                        vi_inst = MagicMock()
                        vi_cls.return_value = vi_inst
                        with patch("llama_index.core.node_parser.SentenceSplitter") as sp_cls:
                            sp_inst = MagicMock()
                            sp_inst.get_nodes_from_documents.return_value = [MagicMock()] * 3
                            sp_cls.return_value = sp_inst
                            with patch("faiss.IndexFlatIP"):
                                with patch("llama_index.core.Settings"):
                                    cfg = {
                                        "index_id": "test-index",
                                        "index_name": "Test Index",
                                        "embedding_model": "fake-model",
                                        "chunk_size": 512,
                                        "chunk_overlap": 64,
                                        "output_path": str(tmp_path / "out"),
                                        "source": {"type": "web"},
                                    }
                                    bi.build_index(cfg)

    meta_path = tmp_path / "out" / "metadata.json"
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text())
    assert meta["index-id"] == "test-index"
    assert meta["num-nodes"] == 3
