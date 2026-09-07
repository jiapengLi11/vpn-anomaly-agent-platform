from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from pathlib import Path

DOCS = Path(__file__).with_name("knowledge_docs")
VERSION = "public-knowledge-v1"


def tokenize(text):
    terms = re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]+", text.lower())
    return [token for term in terms for token in
            ([term] if not re.fullmatch(r"[\u4e00-\u9fff]+", term) or len(term) == 1
             else [term[i:i + 2] for i in range(len(term) - 1)])]


def load_chunks(directory=DOCS):
    chunks = []
    for path in sorted(directory.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        for section in raw.split("\n## ")[1:]:
            title, _, content = section.partition("\n")
            content = content.strip()
            chunk_hash = hashlib.sha256(f"{path.name}\n{title}\n{content}".encode()).hexdigest()
            chunks.append({"id": f"KB-{chunk_hash[:16]}", "title": title,
                           "content": content, "source": path.name, "section": title,
                           "sourceHash": digest, "version": VERSION,
                           "sourceType": "SELF_AUTHORED_DEMO",
                           "tokens": tokenize(title + " " + content)})
    return chunks


def search(query, limit=6, chunks=None):
    if not 1 <= limit <= 20:
        raise ValueError("limit must be between 1 and 20")
    documents = load_chunks() if chunks is None else chunks
    terms = set(tokenize(query))
    average = sum(len(d["tokens"]) for d in documents) / max(len(documents), 1)
    frequencies = Counter(t for d in documents for t in set(d["tokens"]))
    hits = []
    for doc in documents:
        counts = Counter(doc["tokens"])
        score = 0.0
        for term in terms:
            tf = counts[term]
            if tf:
                idf = math.log(1 + (len(documents) - frequencies[term] + .5) / (frequencies[term] + .5))
                score += idf * tf * 2.5 / (tf + 1.5 * (.25 + .75 * len(doc["tokens"]) / average))
        if score > 0:
            hits.append({**{k: v for k, v in doc.items() if k != "tokens"},
                         "score": round(score, 6), "retrievalChannels": ["BM25"]})
    hits.sort(key=lambda h: (-h["score"], h["id"]))
    return {"items": hits[:limit], "query": query, "knowledgeBackend": "local-bm25",
            "strategy": {"name": "bm25", "version": VERSION}, "totalChunks": len(documents)}


def retrieve_context(context):
    codes = sorted({str(e.get("code", "")) for c in context.get("candidates", [])
                    for e in c.get("evidence", []) if isinstance(e, dict) and e.get("code")})
    return search(" ".join(codes) or "调查候选 证据边界", limit=3)
