import asyncio
from tortoise import Tortoise, run_async
from app.models.fr import WordlistFr
from app.utils.textnorm import normalize_text
from settings import TORTOISE_ORM

async def main():
    await Tortoise.init(config=TORTOISE_ORM)
    async for w in WordlistFr.all().only("id", "text", "search_text"):  # type: WordlistFr
        want = normalize_text(w.text)
        if w.search_text != want:
            w.search_text = want
            await w.save(update_fields=["search_text"])
    await Tortoise.close_connections()

if __name__ == "__main__":
    run_async(main())