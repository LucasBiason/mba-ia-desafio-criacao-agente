import json


def serialize_pending(rows):
    return [{"id": row["id"], **json.loads(row["payload"])} for row in rows]


def serialize_events(events):
    return [event.model_dump(mode="json", exclude_none=True) for event in events]
