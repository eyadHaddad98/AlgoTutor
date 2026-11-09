"""Semantic RAG via multilingual E5 + a separate Chroma HTTP service.

Demo search is explicitly lexical and is never reported as vector retrieval.
"""
import hashlib
import json
import re
import threading


class RetrievalError(RuntimeError):
    pass


class Retriever:
    def __init__(self, settings):
        self.settings = settings
        self._model = None
        self._client = None
        self._lock = threading.Lock()
        path = settings.data_dir / "processed/slides.jsonl"
        self.records = ([json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
                        if path.is_file() else [])

    @property
    def model(self):
        with self._lock:
            if self._model is None:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.settings.embedding_model, device="cpu")
                self._model.max_seq_length = 512
            return self._model

    @property
    def client(self):
        if self._client is None:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            self._client = chromadb.HttpClient(host=self.settings.chroma_host, port=self.settings.chroma_port,
                                               settings=ChromaSettings(anonymized_telemetry=False,
                                                                       chroma_server_request_timeout_seconds=8))
        return self._client

    def chunks(self):
        tokenizer = self.model.tokenizer
        for record in self.records:
            prefix = f"הרצאה {record['lecture']}: {record['topic']}. {record['title']}\n"
            # Account for title, passage prefix and special tokens; never silently truncate a slide.
            prefix_tokens = len(tokenizer.encode("passage: " + prefix, add_special_tokens=True))
            budget = max(64, 500 - prefix_tokens)
            encoded = tokenizer(record["text"], add_special_tokens=False, return_offsets_mapping=True)
            offsets = encoded["offset_mapping"]
            for index, start in enumerate(range(0, len(offsets), max(1, budget - 40))):
                end = min(start + budget, len(offsets))
                piece = record["text"][offsets[start][0]:offsets[end - 1][1]]
                content = prefix + piece
                yield {**record, "id": record["id"] + f"-chunk-{index}", "text": content, "chunk": index}
                if end == len(offsets):
                    break

    def ingest(self):
        if not self.records:
            raise RetrievalError("No lecture data found. Add your authorized PDFs and run scripts/prepare_materials.py first.")
        collection = self.client.get_or_create_collection(self.settings.collection,
            metadata={"hnsw:space": "cosine", "embedding_model": self.settings.embedding_model})
        current_model = (collection.metadata or {}).get("embedding_model")
        if current_model != self.settings.embedding_model:
            raise RetrievalError("Embedding model mismatch: use a new CHROMA_COLLECTION.")
        chunks = list(self.chunks())
        for start in range(0, len(chunks), 24):
            batch = chunks[start:start + 24]
            vectors = self.model.encode(["passage: " + c["text"] for c in batch], normalize_embeddings=True).tolist()
            collection.upsert(ids=[c["id"] for c in batch], embeddings=vectors,
                              documents=[c["text"] for c in batch], metadatas=[{
                                  key: c[key] for key in ("lecture", "page", "position", "file", "topic", "title", "chunk")}
                                  | {"slide": c["slide"] or 0} for c in batch])
            print(f"Indexed {min(start + 24, len(chunks))}/{len(chunks)} chunks", flush=True)
        # Remove stale chunks only after the whole new corpus has been successfully upserted.
        old_ids = set(collection.get(include=[])["ids"]) - {c["id"] for c in chunks}
        if old_ids:
            collection.delete(ids=list(old_ids))
        digest = hashlib.sha256("".join(c["text"] for c in chunks).encode()).hexdigest()
        # hnsw:space is immutable and must not be included in a metadata update,
        # even when its value is unchanged. Chroma retains its index configuration.
        collection.modify(metadata={"embedding_model": self.settings.embedding_model,
                                    "corpus_sha256": digest, "lecture_count": 11})
        return {"chunks": len(chunks), "lectures": 11, "corpus_sha256": digest}

    def status(self):
        if self.settings.demo:
            return {"status": "demo_lexical", "slides": len(self.records)}
        try:
            self.client.heartbeat()
            count = self.client.get_collection(self.settings.collection).count()
            return {"status": "ready" if count else "empty", "chunks": count}
        except Exception:
            return {"status": "unavailable", "hint": "הריצו את Chroma ואת פקודת ingest לפי README."}

    def search(self, query, lecture=None):
        if self.settings.demo:
            return self.lexical_search(query, lecture)
        try:
            collection = self.client.get_collection(self.settings.collection)
            if not collection.count():
                raise RetrievalError("מאגר הידע ריק. יש להריץ את פקודת ingest.")
            if (collection.metadata or {}).get("embedding_model") != self.settings.embedding_model:
                raise RetrievalError("מודל ה־embedding אינו תואם למאגר. יש לאנדקס מחדש באוסף חדש.")
            query_vector = self.model.encode(["query: " + query], normalize_embeddings=True).tolist()
            result = collection.query(query_embeddings=query_vector, n_results=min(12, collection.count()),
                where={"lecture": lecture} if lecture else None, include=["documents", "metadatas", "distances"])
            sources, seen = [], set()
            for uid, doc, meta, distance in zip(result["ids"][0], result["documents"][0], result["metadatas"][0], result["distances"][0]):
                key = (meta["lecture"], meta["page"], meta["position"])
                if key in seen:
                    continue
                seen.add(key)
                sources.append(self.source(uid, doc, meta, 1 - distance, "cosine"))
                if len(sources) == self.settings.top_k:
                    break
            return sources
        except RetrievalError:
            raise
        except Exception as exc:
            raise RetrievalError("מאגר הידע אינו זמין. בדקו את Chroma, הורדת מודל החיפוש ופקודת ingest.") from exc

    def lexical_search(self, query, lecture=None):
        words = set(re.findall(r"[\w\u0590-\u05ff]+", query.lower())) - {"מה", "זה", "את", "על", "של", "איך", "לי", "the", "is"}
        matches = []
        for row in self.records:
            if lecture and row["lecture"] != lecture:
                continue
            terms = set(re.findall(r"[\w\u0590-\u05ff]+", (row["topic"] + " " + row["text"]).lower()))
            score = len(words & terms) / max(1, len(words))
            if score:
                matches.append((score, row))
        matches.sort(key=lambda item: item[0], reverse=True)
        return [self.source(r["id"], r["text"], r, score, "lexical_demo") for score, r in matches[:self.settings.top_k]]

    @staticmethod
    def source(uid, doc, meta, score, kind):
        return {"id": uid, "lecture": meta["lecture"], "page": meta["page"], "slide": meta.get("slide") or None,
                "title": meta["title"], "text": doc, "score": round(score, 4), "score_type": kind,
                "url": f"/lectures/{meta['lecture']}#page={meta['page']}"}
