import json
from typing import Any, Dict, Optional
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")
API_URL = os.getenv("API_URL")

class ItemsManager:
    def __init__(self, logger=None, items_file: str = "items.json"):
        self.items: Dict[str, Any] = {}
        self.logger = logger
        self.items_file = items_file

    async def fetch_and_save(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(API_URL) as resp:
                    data = await resp.json()
                    with open(self.items_file, "w", encoding="utf-8") as f:
                        json.dump(data.get("data", {}), f, ensure_ascii=False, indent=2)
            self.logger.info(f"Данные успешно получены и сохранены в {self.items_file}")
        except Exception as e:
            self.logger.error(f"Ошибка при получении данных: {e}")

        if not os.path.exists(self.items_file):
            with open(self.items_file, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
            self.logger.warning(f"Создан пустой файл {self.items_file}")

    async def update(self):
        """
        Перечитывает items из файла.
        """
        try:
            with open(self.items_file, "r", encoding="utf-8") as f:
                self.items = json.load(f)
            self.logger.info(f"{self.items_file} перечитан в память!")
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении items: {e}")

    async def refresh(self):
        """
        Скачивает новые данные и перечитывает их в память.
        """
        await self.fetch_and_save()
        await self.update()

    def get_item(self, hash_name: str) -> Optional[dict]:
        return self.items.get(hash_name)