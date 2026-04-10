"""
Storage Adapter for Seora Premium Music CRM
============================================
Implements a dual-backend pattern: MongoDB (production) / JSON (sandbox/demo).

Architecture: Storage Interface Adapter Pattern
Demonstrates:
  - Graceful degradation without infrastructure dependencies
  - Clean abstraction over heterogeneous storage backends
  - Zero-configuration demo mode for evaluators/recruiters
"""

import json
import os
import re
import copy
from datetime import datetime


class JSONCursor:
    """
    Chainable result cursor for JSON collections.
    Mimics PyMongo's Cursor API with sort() and limit() chaining.
    """

    def __init__(self, data):
        self._data = list(data)

    def sort(self, key_or_list, direction=None):
        if isinstance(key_or_list, str):
            self._data.sort(
                key=lambda x: (x.get(key_or_list) or ''),
                reverse=(direction == -1)
            )
        else:
            for key, dir_ in reversed(key_or_list):
                self._data.sort(
                    key=lambda x: (x.get(key) or ''),
                    reverse=(dir_ == -1)
                )
        return self

    def limit(self, n):
        self._data = self._data[:n]
        return self

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)


class JSONCollection:
    """
    JSON-backed collection mimicking the PyMongo Collection API.
    All data is stored in-memory with JSON file persistence.
    """

    def __init__(self, name, database):
        self._name = name
        self._db = database

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get_data(self):
        return self._db._store.setdefault(self._name, [])

    def _flush(self):
        self._db._persist()

    @staticmethod
    def _stringify(val):
        """Convert ObjectId or datetime to JSON-safe string."""
        if val is None:
            return val
        type_name = type(val).__name__
        if type_name == 'ObjectId':
            return str(val)
        if isinstance(val, datetime):
            return val.isoformat()
        return val

    def _normalize_doc(self, doc):
        """Recursively stringify non-JSON-serializable values."""
        result = {}
        for k, v in doc.items():
            result[k] = self._stringify(v)
        return result

    def _ensure_id(self, doc):
        """Guarantee document has a string _id."""
        if '_id' not in doc:
            from bson import ObjectId
            doc['_id'] = str(ObjectId())
        else:
            doc['_id'] = str(doc['_id'])
        return doc

    def _matches(self, doc, query):
        """Evaluate a MongoDB-style filter query against a doc."""
        for key, value in query.items():
            if key == '$or':
                if not any(self._matches(doc, cond) for cond in value):
                    return False
                continue

            doc_val = doc.get(key)

            # Always compare _id as strings
            if key == '_id':
                if str(doc_val or '') != str(value):
                    return False
                continue

            if isinstance(value, dict):
                for op, op_val in value.items():
                    if op == '$gt':
                        if not (doc_val is not None and doc_val > op_val):
                            return False
                    elif op == '$gte':
                        if not (doc_val is not None and doc_val >= op_val):
                            return False
                    elif op == '$lt':
                        if not (doc_val is not None and doc_val < op_val):
                            return False
                    elif op == '$lte':
                        if not (doc_val is not None and doc_val <= op_val):
                            return False
                    elif op == '$ne':
                        if doc_val == op_val:
                            return False
                    elif op == '$regex':
                        flags = re.IGNORECASE if value.get('$options', '') == 'i' else 0
                        if not (doc_val and re.search(op_val, str(doc_val), flags)):
                            return False
                    elif op == '$options':
                        continue
            else:
                if doc_val != value:
                    return False

        return True

    # ── Public API (mirrors PyMongo Collection) ───────────────────────────────

    def count_documents(self, query=None):
        q = query or {}
        return sum(1 for d in self._get_data() if self._matches(d, q))

    def find(self, query=None):
        q = query or {}
        results = [copy.deepcopy(d) for d in self._get_data() if self._matches(d, q)]
        return JSONCursor(results)

    def find_one(self, query):
        for doc in self._get_data():
            if self._matches(doc, query):
                return copy.deepcopy(doc)
        return None

    def insert_one(self, doc):
        doc = self._normalize_doc(self._ensure_id(copy.deepcopy(doc)))
        self._get_data().append(doc)
        self._flush()
        inserted_id = doc['_id']
        class Result:
            pass
        r = Result()
        r.inserted_id = inserted_id
        return r

    def insert_many(self, docs):
        for doc in docs:
            doc = self._normalize_doc(self._ensure_id(copy.deepcopy(doc)))
            self._get_data().append(doc)
        self._flush()

    def update_one(self, query, update):
        for doc in self._get_data():
            if self._matches(doc, query):
                if '$set' in update:
                    for k, v in update['$set'].items():
                        doc[k] = self._stringify(v)
                if '$inc' in update:
                    for k, v in update['$inc'].items():
                        doc[k] = (doc.get(k) or 0) + v
                break
        self._flush()

    def delete_one(self, query):
        data = self._get_data()
        for i, doc in enumerate(data):
            if self._matches(doc, query):
                data.pop(i)
                break
        self._flush()

    def aggregate(self, pipeline):
        data = [copy.deepcopy(d) for d in self._get_data()]
        total = 0
        result_field = 'total'

        for stage in pipeline:
            if '$match' in stage:
                data = [d for d in data if self._matches(d, stage['$match'])]
            elif '$group' in stage:
                for field_name, expr in stage['$group'].items():
                    if field_name == '_id':
                        continue
                    if isinstance(expr, dict) and '$sum' in expr:
                        result_field = field_name
                        sum_expr = expr['$sum']
                        if isinstance(sum_expr, str) and sum_expr.startswith('$'):
                            src_field = sum_expr[1:]
                            total = sum(d.get(src_field, 0) for d in data)
                        else:
                            total = float(sum_expr) * len(data)

        return iter([{'_id': None, result_field: total}])


class JSONDatabase:
    """
    File-backed document database for zero-config sandbox operation.
    Automatically initializes and persists to a local JSON file.
    Data survives restarts; reset by deleting 'data/sandbox_db.json'.
    """

    _DB_FILE = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'data',
        'sandbox_db.json'
    )

    def __init__(self):
        self._store = {}
        os.makedirs(os.path.dirname(self._DB_FILE), exist_ok=True)
        if os.path.exists(self._DB_FILE):
            try:
                with open(self._DB_FILE, 'r', encoding='utf-8') as f:
                    self._store = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._store = {}

    def _persist(self):
        with open(self._DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(self._store, f, indent=2, default=str)

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        return JSONCollection(name, self)
