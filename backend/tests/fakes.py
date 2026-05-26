from copy import deepcopy

from bson import ObjectId


class InsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class UpdateResult:
    def __init__(self, matched_count: int):
        self.matched_count = matched_count


class DeleteResult:
    def __init__(self, deleted_count: int):
        self.deleted_count = deleted_count


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
                elif "$in" in expected:
                    if actual not in expected["$in"]:
                        return False
                else:
                    return False
            elif isinstance(actual, list):
                if expected not in actual:
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
                if "$set" in update:
                    document.update(update["$set"])
                if "$push" in update:
                    for key, value in update["$push"].items():
                        document.setdefault(key, []).append(value)
                if "$pull" in update:
                    for key, value in update["$pull"].items():
                        if key in document:
                            document[key] = [i for i in document[key] if i != value]
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

    async def update_many(self, query, update):
        matched_count = 0
        for document in self.documents:
            if self._matches(document, query):
                if "$set" in update:
                    document.update(update["$set"])
                if "$pull" in update:
                    for key, value in update["$pull"].items():
                        if key in document:
                            document[key] = [i for i in document[key] if i != value]
                matched_count += 1
        return UpdateResult(matched_count)

    async def delete_many(self, query):
        kept = []
        deleted_count = 0
        for document in self.documents:
            if self._matches(document, query):
                deleted_count += 1
            else:
                kept.append(document)
        self.documents = kept
        return DeleteResult(deleted_count)


    async def count_documents(self, query):
        return sum(1 for doc in self.documents if self._matches(doc, query))

    async def distinct(self, field: str, query=None):
        values = set()
        for doc in self.documents:
            if query is None or self._matches(doc, query):
                if field in doc:
                    values.add(doc[field])
        return sorted(values)


class FakeCursor:
    def __init__(self, documents):
        self.documents = documents

    def sort(self, field_name, direction):
        reverse = direction < 0
        self.documents.sort(key=lambda document: document.get(field_name), reverse=reverse)
        return self

    def skip(self, n):
        self.documents = self.documents[n:]
        return self

    async def to_list(self, limit):
        return self.documents[:limit]
