import asyncio
from pathlib import Path

import pandas as pd
from tortoise import Tortoise

from app.models.fr import ProverbFr
from settings import TORTOISE_ORM

__xlsx_name = "../DictTable_20251029.xlsx"
__table_name = "法语谚语常用表达"


class FrProverb:
    def __init__(self, __xlsx_name, __table_name):
        self.__xlsx_name = __xlsx_name
        self.__table_name = __table_name

    async def get_proverb(self) -> None:
        df = pd.read_excel(Path(self.__xlsx_name), sheet_name=self.__table_name)
        df.columns = [col.strip() for col in df.columns]

        for row in df.itertuples():
            proverb = str(row.法语谚语常用表达).strip()
            chi_exp = str(row.中文释义).strip()

            cls_proverb, created = await ProverbFr.get_or_create(proverb=proverb, chi_exp=chi_exp)
            if not created:
                print(f"{proverb} 已存在！位于第{row.index}行")

    async def build_connection(self):
        pass


async def main():
    await Tortoise.init(config=TORTOISE_ORM)
    proverb = FrProverb(__xlsx_name, __table_name)
    await proverb.get_proverb()

if __name__ == '__main__':
    asyncio.run(main())