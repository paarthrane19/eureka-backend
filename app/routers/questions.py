from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_db
from app.schemas import QuestionPublic
from app.security import get_current_user
from app.serializers import question_public

router = APIRouter()


def _oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except InvalidId:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.get("", response_model=list[QuestionPublic])
async def list_questions(current_user: dict = Depends(get_current_user)):
    db = get_db()
    me = current_user["_id"]
    questions = await db.questions.find({}).sort("created_at", -1).to_list(length=200)
    return [
        question_public(q, following=me in (q.get("followers", []) or []))
        for q in questions
    ]


@router.post("/{question_id}/follow", response_model=QuestionPublic)
async def toggle_follow(
    question_id: str, current_user: dict = Depends(get_current_user)
):
    db = get_db()
    oid = _oid(question_id)
    me = current_user["_id"]
    question = await db.questions.find_one({"_id": oid})
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Question not found"
        )

    followers = question.get("followers", []) or []
    if me in followers:
        await db.questions.update_one({"_id": oid}, {"$pull": {"followers": me}})
    else:
        await db.questions.update_one({"_id": oid}, {"$addToSet": {"followers": me}})

    fresh = await db.questions.find_one({"_id": oid})
    return question_public(
        fresh, following=me in (fresh.get("followers", []) or [])
    )
