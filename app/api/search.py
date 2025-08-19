from fastapi import APIRouter, Depends, HTTPException, Request

from app.models.fr import DefinitionFr
from app.utils.security import get_current_user

dict_search = APIRouter()


@dict_search.get("/search")
async def search(
    request: Request, lang_pref: str, query_word: str, user=Depends(get_current_user)
):
    word_content = await DefinitionFr.filter(
        word__icontains=query_word, lang_pref=lang_pref
    ).values("word", "part_of_speech", "meaning", "example")
    if not word_content:
        raise HTTPException(status_code=404, detail="Word not found")
    return word_content
