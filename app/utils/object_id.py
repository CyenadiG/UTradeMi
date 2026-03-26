from bson import ObjectId
from fastapi import HTTPException, status


def parse_object_id(value: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ObjectId",
        )
    return ObjectId(value)


def doc_to_json(doc: dict | None) -> dict | None:
    if doc is None:
        return None

    result = {}

    for key, value in doc.items():
        if key == "_id":
            result["id"] = str(value)
        elif isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, list):
            result[key] = [
                str(item) if isinstance(item, ObjectId) else item
                for item in value
            ]
        else:
            result[key] = value

    return result