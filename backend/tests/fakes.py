from copy import deepcopy

from bson import ObjectId


class InsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class UpdateResult:
    def __init__(self, matched_count: int):
        self.matched_count = matched_count


class FakeCollection:
    def __init__(self, documents=None):
        self.documents = []
        for document in documents or []:
            self.documents.append(self._prepare(document))

    def _prepare(self, document):
        prepared = deepcopy(document)
        prepared.setdefault("_id", ObjectId())
        return prepared

    def _matches(self, document, query):
        if not query:
            return True

        for key, expected in query.items():
            if key == "$and":
                if not all(self._matches(document, option) for option in expected):
                    return False
                continue

            if key == "$or":
                if not any(self._matches(document, option) for option in expected):
                    return False
                continue

            actual = document.get(key)
            if isinstance(expected, dict):
                if "$exists" in expected:
                    exists = key in document
                    if exists != expected["$exists"]:
                        return False
                elif "$regex" in expected:
                    if expected["$regex"].lower() not in str(actual or "").lower():
                        return False
                else:
                    return False
            elif actual != expected:
                return False

        return True

    async def find_one(self, query):
        for document in self.documents:
            if self._matches(document, query):
                return deepcopy(document)
        return None

    async def insert_one(self, document):
        prepared = self._prepare(document)
        self.documents.append(prepared)
        return InsertResult(prepared["_id"])

    def find(self, query):
        matches = [deepcopy(document) for document in self.documents if self._matches(document, query)]
        return FakeCursor(matches)

    async def find_one_and_update(self, query, update, return_document=True):
        for document in self.documents:
            if self._matches(document, query):
                document.update(update.get("$set", {}))
                return deepcopy(document)
        return None

    async def find_one_and_delete(self, query):
        for index, document in enumerate(self.documents):
            if self._matches(document, query):
                return deepcopy(self.documents.pop(index))
        return None

    async def update_one(self, query, update):
        for document in self.documents:
            if self._matches(document, query):
                if "$inc" in update:
                    for key, amount in update["$inc"].items():
                        document[key] = document.get(key, 0) + amount
                if "$set" in update:
                    document.update(update["$set"])
                return UpdateResult(1)
        return UpdateResult(0)


class FakeCursor:
    def __init__(self, documents):
        self.documents = documents

    async def to_list(self, limit):
        return self.documents[:limit]
