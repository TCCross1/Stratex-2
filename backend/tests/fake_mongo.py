"""In-memory Mongo double for C-P-002 deterministic unit tests.

Supports the Motor-like surface used by NextGen Passport:
find_one, find, insert_one, update_one, find_one_and_update, create_index,
index_information, aggregate, count_documents, sort cursors.

Unique indexes enforce duplicate protection. An optional transactional lock
simulates multi-document atomicity for concurrency stress tests.
"""
from __future__ import annotations

import asyncio
import copy
import re
from typing import Any, Dict, List, Optional, Tuple


def _match(doc: Dict[str, Any], query: Dict[str, Any]) -> bool:
    if not query:
        return True
    if "$or" in query:
        if not any(_match(doc, clause) for clause in query["$or"]):
            return False
        rest = {k: v for k, v in query.items() if k != "$or"}
        return _match(doc, rest) if rest else True
    if "$and" in query:
        return all(_match(doc, clause) for clause in query["$and"])
    for key, expected in query.items():
        if key.startswith("$"):
            continue
        actual = doc.get(key)
        if isinstance(expected, dict) and any(k.startswith("$") for k in expected):
            if "$in" in expected and actual not in expected["$in"]:
                return False
            if "$ne" in expected and actual == expected["$ne"]:
                return False
            if "$gt" in expected and not (actual is not None and actual > expected["$gt"]):
                return False
            if "$gte" in expected and not (actual is not None and actual >= expected["$gte"]):
                return False
            if "$lt" in expected and not (actual is not None and actual < expected["$lt"]):
                return False
            if "$lte" in expected and not (actual is not None and actual <= expected["$lte"]):
                return False
            if "$exists" in expected:
                exists = key in doc and doc[key] is not None
                if bool(expected["$exists"]) != exists:
                    return False
        else:
            if actual != expected:
                return False
    return True


class _UpdateResult:
    def __init__(self, matched: int, modified: int):
        self.matched_count = matched
        self.modified_count = modified


class FakeCursor:
    def __init__(self, docs: List[Dict[str, Any]]):
        self._docs = docs
        self._idx = 0

    def sort(self, key, direction=1):
        reverse = direction < 0
        if isinstance(key, list):
            # multi-key sort — apply last key first
            for k, d in reversed(key):
                self._docs.sort(key=lambda x: (x.get(k) is None, x.get(k)), reverse=d < 0)
        else:
            self._docs.sort(key=lambda x: (x.get(key) is None, x.get(key)), reverse=reverse)
        return self

    def limit(self, n: int):
        self._docs = self._docs[:n]
        return self

    def __aiter__(self):
        self._idx = 0
        return self

    async def __anext__(self):
        if self._idx >= len(self._docs):
            raise StopAsyncIteration
        doc = self._docs[self._idx]
        self._idx += 1
        return copy.deepcopy(doc)

    async def to_list(self, length=None):
        docs = self._docs if length is None else self._docs[:length]
        return [copy.deepcopy(d) for d in docs]


class DuplicateKeyError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.code = 11000


class FakeCollection:
    def __init__(self, name: str, store: Dict[str, List[Dict[str, Any]]], indexes: Dict[str, Dict]):
        self.name = name
        self._store = store
        self._indexes = indexes
        self._lock = asyncio.Lock()

    def _docs(self) -> List[Dict[str, Any]]:
        return self._store.setdefault(self.name, [])

    async def find_one(self, query: Optional[Dict[str, Any]] = None, sort=None, **kwargs):
        docs = [d for d in self._docs() if _match(d, query or {})]
        if sort:
            if isinstance(sort, list):
                for k, d in reversed(sort):
                    docs.sort(key=lambda x: (x.get(k) is None, x.get(k)), reverse=d < 0)
            else:
                # motor sometimes passes sort as kw via cursor; ignore here
                pass
        return copy.deepcopy(docs[0]) if docs else None

    def find(self, query: Optional[Dict[str, Any]] = None, **kwargs):
        docs = [copy.deepcopy(d) for d in self._docs() if _match(d, query or {})]
        return FakeCursor(docs)

    async def insert_one(self, doc: Dict[str, Any], **kwargs):
        async with self._lock:
            self._check_unique(doc)
            self._docs().append(copy.deepcopy(doc))
        return type("IR", (), {"inserted_id": doc.get("canonical_id") or id(doc)})()

    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any], upsert=False, **kwargs):
        async with self._lock:
            for i, d in enumerate(self._docs()):
                if _match(d, query):
                    new_doc = copy.deepcopy(d)
                    if "$set" in update:
                        new_doc.update(update["$set"])
                    if "$inc" in update:
                        for k, v in update["$inc"].items():
                            new_doc[k] = int(new_doc.get(k) or 0) + int(v)
                    # unique check excluding self
                    self._docs()[i] = new_doc
                    # re-validate uniques
                    try:
                        self._check_unique(new_doc, exclude_idx=i)
                    except DuplicateKeyError:
                        self._docs()[i] = d
                        raise
                    return _UpdateResult(1, 1)
            if upsert:
                base = dict(query)
                if "$set" in update:
                    base.update(update["$set"])
                self._check_unique(base)
                self._docs().append(base)
                return _UpdateResult(0, 0)
            return _UpdateResult(0, 0)

    async def find_one_and_update(self, query, update, return_document=False, **kwargs):
        async with self._lock:
            for i, d in enumerate(self._docs()):
                if _match(d, query):
                    new_doc = copy.deepcopy(d)
                    if "$set" in update:
                        new_doc.update(update["$set"])
                    if "$inc" in update:
                        for k, v in update["$inc"].items():
                            new_doc[k] = int(new_doc.get(k) or 0) + int(v)
                    self._docs()[i] = new_doc
                    return copy.deepcopy(new_doc if return_document else d)
            return None

    async def count_documents(self, query: Optional[Dict[str, Any]] = None, **kwargs):
        return sum(1 for d in self._docs() if _match(d, query or {}))

    async def delete_many(self, query: Optional[Dict[str, Any]] = None, **kwargs):
        q = query or {}
        kept = [d for d in self._docs() if not _match(d, q)]
        removed = len(self._docs()) - len(kept)
        self._store[self.name] = kept
        return type("DR", (), {"deleted_count": removed})()

    async def create_index(self, keys, name=None, unique=False, **kwargs):
        idx_name = name or "_".join(f"{k}_{d}" for k, d in keys)
        # Detect duplicates before accepting unique index.
        if unique:
            seen = {}
            for d in self._docs():
                tup = tuple(d.get(k) for k, _ in keys)
                if any(v is None for v in tup):
                    continue
                if tup in seen:
                    raise DuplicateKeyError(
                        f"E11000 duplicate key error collection: {self.name} index: {idx_name}"
                    )
                seen[tup] = True
        self._indexes.setdefault(self.name, {})[idx_name] = {
            "key": keys, "unique": unique, "name": idx_name,
        }
        return idx_name

    async def index_information(self):
        return copy.deepcopy(self._indexes.get(self.name, {}))

    def aggregate(self, pipeline):
        # Minimal $match/$group/$match support for duplicate probe.
        docs = [copy.deepcopy(d) for d in self._docs()]
        for stage in pipeline:
            if "$match" in stage:
                docs = [d for d in docs if _match(d, stage["$match"])]
            elif "$group" in stage:
                g = stage["$group"]
                key = g["_id"]
                field = key[1:] if isinstance(key, str) and key.startswith("$") else None
                buckets: Dict[Any, int] = {}
                for d in docs:
                    k = d.get(field) if field else key
                    buckets[k] = buckets.get(k, 0) + 1
                docs = [{"_id": k, "n": n} for k, n in buckets.items()]
        return FakeCursor(docs)

    def _check_unique(self, doc: Dict[str, Any], exclude_idx: Optional[int] = None):
        for name, meta in (self._indexes.get(self.name) or {}).items():
            if not meta.get("unique"):
                continue
            keys = meta["key"]
            tup = tuple(doc.get(k) for k, _ in keys)
            if any(v is None for v in tup):
                continue
            for i, other in enumerate(self._docs()):
                if exclude_idx is not None and i == exclude_idx:
                    continue
                ot = tuple(other.get(k) for k, _ in keys)
                if ot == tup:
                    raise DuplicateKeyError(
                        f"E11000 duplicate key error collection: {self.name} index: {name}"
                    )


class FakeCollections:
    """Drop-in for nx_collections."""

    def __init__(self):
        self._store: Dict[str, List[Dict[str, Any]]] = {}
        self._indexes: Dict[str, Dict] = {}
        self._cache: Dict[str, FakeCollection] = {}

    def __getattr__(self, name: str) -> FakeCollection:
        if name.startswith("_"):
            raise AttributeError(name)
        if name not in self._cache:
            self._cache[name] = FakeCollection(name, self._store, self._indexes)
        return self._cache[name]


def install_fake_collections(monkeypatch, *modules):
    """Patch nx_collections on the given modules to a shared FakeCollections."""
    fake = FakeCollections()
    for mod in modules:
        if hasattr(mod, "nx_collections"):
            monkeypatch.setattr(mod, "nx_collections", fake)
    return fake
