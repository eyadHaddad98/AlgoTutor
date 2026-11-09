import json
from pathlib import Path
import pytest
from algotutor.config import Settings, ROOT
from algotutor.retrieval import Retriever, RetrievalError


def test_corpus_covers_all_supplied_lectures_with_unambiguous_sources():
    r = Retriever(Settings(demo=True))
    assert len(r.records) == 479
    assert {row["lecture"] for row in r.records} == set(range(1, 12))
    assert len({row["id"] for row in r.records}) == len(r.records)
    assert all(row["slide"] and row["page"] and row["text"] for row in r.records)
    manifest = json.loads((ROOT / "data/processed/manifest.json").read_text())
    assert sum(row["pdf_pages"] for row in manifest) == 124
    for row in r.records:
        assert (ROOT / "data/lectures" / row["file"]).exists()
        assert row["page"] <= next(m["pdf_pages"] for m in manifest if m["lecture"] == row["lecture"])


def test_demo_search_is_explicitly_labelled():
    sources = Retriever(Settings(demo=True)).search("Dijkstra דייקסטרה", 3)
    assert sources
    assert all(s["score_type"] == "lexical_demo" and s["lecture"] == 3 for s in sources)


def test_empty_chroma_collection_raises_clear_error():
    class EmptyCollection:
        def count(self):
            return 0
    class Client:
        def get_collection(self, *args):
            return EmptyCollection()
    r = Retriever(Settings(demo=False))
    r._client = Client()
    with pytest.raises(RetrievalError, match="ריק"):
        r.search("BFS")


def test_model_mismatch_is_not_silently_used():
    class Collection:
        metadata = {"embedding_model": "different-model"}
        def count(self):
            return 10
    class Client:
        def get_collection(self, *args):
            return Collection()
    r = Retriever(Settings(demo=False))
    r._client = Client()
    with pytest.raises(RetrievalError, match="תואם"):
        r.search("BFS")
