from .record import Record


class Result:
    def __init__(self, result):
        self.result = result

    @property
    def rowcount(self):
        return self.result.rowcount

    def fetchone(self):
        row = self.result.mappings().fetchone()
        return Record(row) if row is not None else None

    def fetchall(self):
        return [Record(row) for row in self.result.mappings().fetchall()]

    def __iter__(self):
        return iter(self.fetchall())
