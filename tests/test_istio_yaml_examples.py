"""Tests for Istio YAML example documents."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

EXAMPLES_DIR = Path(__file__).parent.parent / "docs" / "istio-yaml-examples"
REQUIRED_FRONTMATTER_KEYS = {"title", "category", "description", "istio_versions", "crd_types", "docs_url"}
VALID_CATEGORIES = {"traffic-management", "security", "resilience"}
ISTIO_API_VERSIONS = {
    "networking.istio.io/v1",
    "networking.istio.io/v1beta1",
    "security.istio.io/v1",
    "security.istio.io/v1beta1",
    "install.istio.io/v1alpha1",
}
ISTIO_KINDS = {
    "VirtualService",
    "DestinationRule",
    "Gateway",
    "ServiceEntry",
    "PeerAuthentication",
    "AuthorizationPolicy",
    "RequestAuthentication",
    "IstioOperator",
}


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    frontmatter = yaml.safe_load(parts[1]) or {}
    return frontmatter, parts[2].lstrip("\n")


def _extract_yaml_blocks(body: str) -> list[str]:
    return re.findall(r"```yaml\n(.*?)```", body, re.DOTALL)


def _load_example_files() -> list[Path]:
    return sorted(EXAMPLES_DIR.rglob("*.md"))


@pytest.fixture
def example_files() -> list[Path]:
    files = _load_example_files()
    assert files, f"No example files found in {EXAMPLES_DIR}"
    return files


def test_minimum_example_count(example_files: list[Path]):
    assert len(example_files) >= 20, f"Expected >= 20 examples, found {len(example_files)}"


@pytest.mark.parametrize("path", _load_example_files(), ids=lambda p: p.stem)
def test_example_frontmatter(path: Path):
    frontmatter, body = _parse_frontmatter(path.read_text(encoding="utf-8"))
    missing = REQUIRED_FRONTMATTER_KEYS - frontmatter.keys()
    assert not missing, f"{path.name} missing frontmatter keys: {missing}"
    assert frontmatter["category"] in VALID_CATEGORIES
    assert isinstance(frontmatter["istio_versions"], list)
    assert len(frontmatter["istio_versions"]) >= 1
    assert isinstance(frontmatter["crd_types"], list)
    assert len(frontmatter["crd_types"]) >= 1
    assert len(body.strip()) > 50


@pytest.mark.parametrize("path", _load_example_files(), ids=lambda p: p.stem)
def test_example_yaml_blocks(path: Path):
    _, body = _parse_frontmatter(path.read_text(encoding="utf-8"))
    blocks = _extract_yaml_blocks(body)
    assert blocks, f"{path.name} has no ```yaml blocks"

    for i, block in enumerate(blocks):
        docs = list(yaml.safe_load_all(block))
        assert docs, f"{path.name} block {i} is empty"
        for doc in docs:
            if doc is None:
                continue
            assert "apiVersion" in doc, f"{path.name} block {i}: missing apiVersion"
            assert "kind" in doc, f"{path.name} block {i}: missing kind"
            assert doc["apiVersion"] in ISTIO_API_VERSIONS, (
                f"{path.name} block {i}: unexpected apiVersion {doc['kind']}"
            )
            assert doc["kind"] in ISTIO_KINDS, f"{path.name} block {i}: unexpected kind {doc['kind']}"
            assert "metadata" in doc, f"{path.name} block {i}: missing metadata"
            assert "name" in doc["metadata"], f"{path.name} block {i}: missing metadata.name"


def test_categories_coverage(example_files: list[Path]):
    categories = set()
    for path in example_files:
        frontmatter, _ = _parse_frontmatter(path.read_text(encoding="utf-8"))
        categories.add(frontmatter["category"])
    assert categories == VALID_CATEGORIES


def test_load_documents_from_local_integration():
    """Smoke test: load curated examples through build_index local loader."""
    import importlib
    import sys

    for name in list(sys.modules):
        if name == "build_index" or name.startswith(("llama_index", "faiss")):
            del sys.modules[name]

    import build_index as bi

    bi = importlib.reload(bi)
    docs = bi.load_documents_from_local({"local_path": str(EXAMPLES_DIR)})
    assert len(docs) >= 20
    sample = docs[0]
    assert sample.metadata.get("title")
    assert sample.metadata.get("docs_url")
    assert len(sample.text) > 100
    assert "Category:" in sample.text
