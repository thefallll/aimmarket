import aiohttp
import json
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")
API_URL = os.getenv("API_URL")

async def fetch_and_save():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL) as resp:
                data = await resp.json()
                with open("items.json", "w", encoding="utf-8") as f:
                    json.dump(data.get("data", {}), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка при получении данных: {e}")

    if not os.path.exists("items.json"):
        with open("items.json", "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)