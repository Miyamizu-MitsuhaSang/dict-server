import asyncio
from pathlib import Path

import pandas as pd
from tortoise import Tortoise

from app.models import KangjiMapping
from settings import TORTOISE_ORM


class JapaneseIntro:
    kangji_mapping : Path = Path("./中日汉字映射表_自动扩充_约3000条.xlsx")

    @classmethod
    async def kangji_mapping_intro(cls):
        df = pd.read_excel(cls.kangji_mapping)
        df.columns = [col.strip() for col in df.columns]

        for row in df.itertuples():
            hanzi = row[1]
            kangji = row[2]
            note = row[4]

            mapping = await KangjiMapping.create(
                hanzi=hanzi,
                kangji=kangji,
                note=note,
            )
        print("导入完成")

async def main():
    await Tortoise.init(config=TORTOISE_ORM)
    await KangjiMapping.all().delete()
    await JapaneseIntro.kangji_mapping_intro()

if __name__ == '__main__':
    asyncio.run(main())