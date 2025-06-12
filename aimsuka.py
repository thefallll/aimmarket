import re
import json
import os
import logging
import time

from async_tls_client import AsyncSession

import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram import types

from dotenv import load_dotenv

from initialize_session import InitializeSession
from filter import Item, ItemsDatabase, ItemFilterEXP 
from json_db import fetch_and_save

from urllib.parse import quote

load_dotenv()
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

bot = Bot(token=TG_TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()

PROXY_FILE = 'list_resident_proxyseller (4).txt'
LOG_FILE = "aimmarket.log"

logging.Formatter.converter = time.gmtime
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s UTC [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

WEAPON_TYPE_MAP = {
    # Rifles
    "AK-47": "Rifle", "M4A4": "Rifle", "M4A1-S": "Rifle", "FAMAS": "Rifle", "Galil AR": "Rifle", "AUG": "Rifle", "SG 553": "Rifle",
    # SMG
    "P90": "SMG", "UMP-45": "SMG", "MP7": "SMG", "MP5-SD": "SMG", "MP9": "SMG", "MAC-10": "SMG", "PP-Bizon": "SMG",
    # Sniper Rifles
    "AWP": "Sniper Rifle", "SSG 08": "Sniper Rifle", "SCAR-20": "Sniper Rifle", "G3SG1": "Sniper Rifle",
    # Pistols
    "Glock-18": "Pistol", "USP-S": "Pistol", "P2000": "Pistol", "P250": "Pistol", "Five-SeveN": "Pistol", "Tec-9": "Pistol", "CZ75-Auto": "Pistol", "Dual Berettas": "Pistol", "Desert Eagle": "Pistol", "R8 Revolver": "Pistol",
    # Shotguns
    "Nova": "Shotgun", "XM1014": "Shotgun", "MAG-7": "Shotgun", "Sawed-Off": "Shotgun",
    # Heavy (Machineguns)
    "M249": "Machinegun", "Negev": "Machinegun",
    # Grenades
    "HE Grenade": "Grenade", "Flashbang": "Grenade", "Smoke Grenade": "Grenade", "Decoy Grenade": "Grenade", "Molotov": "Grenade", "Incendiary Grenade": "Grenade",
    # Knives
    "★": "Knife",
    "Bayonet": "Knife", "Bowie Knife": "Knife", "Butterfly Knife": "Knife", "Classic Knife": "Knife", "Falchion Knife": "Knife",
    "Flip Knife": "Knife", "Gut Knife": "Knife", "Huntsman Knife": "Knife", "Karambit": "Knife", "M9 Bayonet": "Knife",
    "Navaja Knife": "Knife", "Nomad Knife": "Knife", "Paracord Knife": "Knife", "Shadow Daggers": "Knife", "Skeleton Knife": "Knife",
    "Stiletto Knife": "Knife", "Survival Knife": "Knife", "Talon Knife": "Knife", "Ursus Knife": "Knife", "Stock Knife": "Knife",
    # Gloves
    "Gloves": "Gloves", "Hydra Gloves": "Gloves", "Sport Gloves": "Gloves", "Moto Gloves": "Gloves", "Specialist Gloves": "Gloves",
    "Hand Wraps": "Gloves", "Driver Gloves": "Gloves", "Bloodhound Gloves": "Gloves",
    # Cases
    "Case": "Case", "Fever Case": "Case", "Snakebite Case": "Case", "Recoil Case": "Case", "Fracture Case": "Case", "Clutch Case": "Case",
    "Prisma Case": "Case", "Prisma 2 Case": "Case", "Danger Zone Case": "Case", "Horizon Case": "Case", "Spectrum Case": "Case", "Spectrum 2 Case": "Case",
    "Glove Case": "Case", "Chroma Case": "Case", "Chroma 2 Case": "Case", "Chroma 3 Case": "Case", "Gamma Case": "Case", "Gamma 2 Case": "Case",
    "Operation Broken Fang Case": "Case", "Operation Riptide Case": "Case", "Operation Shattered Web Case": "Case", "Operation Hydra Case": "Case",
    # Stickers
    "Sticker": "Sticker",
    # Agents
    "Agent": "Agent",
    # Patches
    "Patch": "Patch",
    # Graffiti
    "Graffiti": "Graffiti",
    # Music Kits
    "Music Kit": "Music Kit",
    # Other (fallbacks)
    "Souvenir Package": "Package", "Capsule": "Capsule", "Pin": "Pin", "Collectible": "Collectible"
}

class Aimmarket:
    def __init__(self):
        self.session_initializer = InitializeSession()
        self.used_proxies = set()
        self.failed_proxies = set()

    def get_proxy_list(self):
        with open(PROXY_FILE, 'r') as f:
            return [line.strip() for line in f if line.strip()]

    def format_skin_name(self, name, quality, exterior):
        stattrak = ""
        if quality and "StatTrak" in quality and "StatTrak" not in name:
            stattrak = "StatTrak™"
        star = "★" if name and name.startswith("★") and "★" not in name[1:] else ""
        name_without_star = name.lstrip("★").strip() if name else ""
        condition = f"({exterior})" if exterior and f"({exterior})" not in name else ""
        return " ".join(filter(None, [star, stattrak, name_without_star, condition])).strip()

    def extract_weapon_and_type(self, hash_name):
        name = hash_name
        if name.startswith("Souvenir "):
            name = name[len("Souvenir "):]
        if name.startswith("StatTrak™ "):
            name = name[len("StatTrak™ "):]
        for weapon, weapon_type in WEAPON_TYPE_MAP.items():
            if name.startswith("★"):
                if weapon in name:
                    return weapon_type, weapon
            else:
                if name.startswith(weapon):
                    return weapon_type, weapon
        return None, None

    def make_aimmarket_link(self, hash_name):
        encoded_name = quote(hash_name)
        return f"https://aim.market/en/buy/csgo/{encoded_name}"

    def make_csmarket_link(self, hash_name):
        is_souvenir = hash_name.startswith("Souvenir ")
        weapon_type, weapon_name = self.extract_weapon_and_type(hash_name)
        if weapon_type and weapon_name:
            encoded_type = quote(weapon_type)
            encoded_name = quote(weapon_name)
            encoded_hash = quote(hash_name)
            return f"https://market.csgo.com/ru/{encoded_type}/{encoded_name}/{encoded_hash}"
        else:
            encoded_hash = quote(hash_name)
            return f"https://market.csgo.com/ru/search?query={encoded_hash}"

    def make_buff_link(self, hash_name):
        good_id = items.get(hash_name, {}).get('buff', {}).get('good_id')
        if good_id:
            return f"https://buff.163.com/goods/{good_id}"
        else:
            # fallback 
            encoded_name = quote(hash_name)
            return f"https://buff.163.com/market/csgo#search={encoded_name}"

    def format_tg_message(self, item_obj: Item, href: str):
        lines = []
        item_current_price = item_obj.price

        item_full_data = items.get(item_obj.hash_name, {})
        buff_data = item_full_data.get('buff', {})
        csmarket_data = item_full_data.get('csmarket', {})

        lines.append(f"{'💚' if item_obj.autobuy else '🔴'} {item_obj.hash_name}")
        lines.append(f"Тир: {item_obj.tier if item_obj.tier else 'N/A'}")
        lines.append("")
        float_str = f"*{item_obj.float:.6f}*" if item_obj.float and item_obj.float > 0 else "*N/A*"
        lines.append(float_str)
        lines.append("")
        lines.append(f"💰 Цена: *{item_current_price:.2f}$*")

        for cond in item_obj.conditions:
            lines.append(f"{cond.name} - *{cond.price:.2f}$\n({cond.procent}%)*")

        lines.append("")

        trends_data = csmarket_data.get('trend', {})
        trend_values = []
        for days_key in ['7days', '14days', '30days', '60days']:
            trend_val = trends_data.get(days_key)
            if trend_val is not None:
                try:
                    trend_values.append(f"*{float(trend_val):+.2f}%*")
                except Exception:
                    trend_values.append(f"*{trend_val}%*")
        if trend_values:
            lines.append(f"Тренды: {' | '.join(trend_values)}")
        else:
            lines.append("Тренды: N/A")

        lines.append("")

        autobuy_status = "ДА ✅" if item_obj.autobuy else "НИ ЗА ЧТО"
        lines.append(f"Автобай: *{autobuy_status}*")

        lines.append("")

        return "\n".join(lines)

    async def send_telegram(self, text, image_url=None, aim_link=None, market_link=None, buff_link=None):

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="AIMMARKET", url=aim_link),
                InlineKeyboardButton(text="MARKET", url=market_link),
                InlineKeyboardButton(text="BUFF163", url=buff_link),
            ]
        ])
        if image_url:
            await bot.send_photo(
                TG_CHAT_ID,
                photo=image_url,
                caption=text,
                reply_markup=keyboard
            )
        else:
            await bot.send_message(
                TG_CHAT_ID,
                text,
                reply_markup=keyboard
            )


    async def parse_worker(self, worker_id, proxy, seen_ids, seen_lock, item_filter):
        url = 'https://aim.market/en/buy?auto_update=true&order_column=createdAt'
        session = AsyncSession(client_identifier='chrome_133', random_tls_extension_order=True)
        
        while True:
            try:
                r = await session.get(url, proxy=f"http://{proxy}")
                print(f"[Worker {worker_id}] [{proxy}] Получен ответ: {r.status_code}, длина: {len(r.text)}")
                logging.info(f"[Worker {worker_id}] [{proxy}] Получен ответ: {r.status_code}, длина: {len(r.text)}")
                if r.status_code != 200 or "Internal Server Error" in r.text:
                    print(f"[Worker {worker_id}] [{proxy}] БАН или плохой ответ ({r.status_code})")
                    logging.error(f"[Worker {worker_id}] [{proxy}] БАН или плохой ответ ({r.status_code})")
                    new_proxy = await self.session_initializer.find_new_proxy(worker_id, proxy, self.used_proxies, self.failed_proxies, PROXY_FILE)
                    if new_proxy:
                        print(f"[Worker {worker_id}] Переключаюсь на новый прокси: {new_proxy}")
                        logging.info(f"[Worker {worker_id}] Переключаюсь на новый прокси: {new_proxy}")
                        proxy = new_proxy
                        session = AsyncSession(client_identifier='chrome_133', random_tls_extension_order=True)
                        continue
                    else:
                        print(f"[Worker {worker_id}] Не удалось найти новый прокси, воркер завершает работу.")
                        logging.error(f"[Worker {worker_id}] Не удалось найти новый прокси, воркер завершает работу.")
                        break
                
                html = r.text
                m = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', html, re.DOTALL)
                if not m:
                    print(f"[Worker {worker_id}] [{proxy}] Не найден INITIAL_STATE, пропускаю итерацию.")
                    logging.warning(f"[Worker {worker_id}] [{proxy}] Не найден INITIAL_STATE, пропускаю итерацию.")
                    await asyncio.sleep(1) 
                    continue

                state = json.loads(m.group(1))
                apollo_raw = state.get("cache", {}).get("apolloState")
                if not apollo_raw:
                    print(f"[Worker {worker_id}] [{proxy}] Не найден apolloState, пропускаю итерацию.")
                    logging.warning(f"[Worker {worker_id}] [{proxy}] Не найден apolloState, пропускаю итерацию.")
                    await asyncio.sleep(1)
                    continue

                apollo = json.loads(apollo_raw)
                scraped_items_on_page = [v for k, v in apollo.items() if k.startswith("BotSteamItem:")]

                async with seen_lock:
                    for scraped_item_data in scraped_items_on_page:
                        item_id = scraped_item_data.get('id')
                        if not item_id or item_id in seen_ids:
                            continue
                        seen_ids.add(item_id)

                        name = scraped_item_data.get("marketHashName", "Не найдено")
                        price_str = scraped_item_data.get("price", {}).get("sellPrice", "Не найдено")
                        float_value_str = scraped_item_data.get("float", None)
                        
                        current_price_on_aim = float(price_str) if price_str != "Не найдено" else 0
                        current_float_on_aim = float(float_value_str) if float_value_str is not None else 0.0

                        exterior = scraped_item_data.get("exterior", "")
                        quality = scraped_item_data.get("quality", "")

                        href = f"https://aim.market/item/{item_id}"

                        item_obj = Item(
                            hash_name=name,
                            price=current_price_on_aim,
                            item_float=current_float_on_aim,
                            item_id=item_id,
                            market="aimmarket",
                            tier=items.get(name, {}).get("asset", {}).get("tier", 0)
                        )
                        
                        item_filter.filter_item(item_obj) 

                        if item_obj.notify:
                            image_path_from_json = items.get(name, {}).get("asset", {}).get("image_url")
                            image_to_send = None

                            if image_path_from_json:
                                if image_path_from_json.startswith("http://") or image_path_from_json.startswith("https://"):
                                    image_to_send = image_path_from_json
                                else:
                                    image_to_send = f"https://steamcommunity-a.akamaihd.net/economy/image/{image_path_from_json}"
                            
                            msg = self.format_tg_message(item_obj, href)

                            aimmarket_link = self.make_aimmarket_link(item_obj.hash_name)
                            csmarket_link = self.make_csmarket_link(item_obj.hash_name)
                            buff_link = self.make_buff_link(item_obj.hash_name)

                            await self.send_telegram(msg, 
                                                    image_url=image_to_send,
                                                    aim_link=aimmarket_link,
                                                    market_link=csmarket_link,
                                                    buff_link=buff_link)
                        
                        formatted_name_console = self.format_skin_name(name, quality, exterior)
                        if float_value_str is None:
                            print(f"[Worker {worker_id}] 🆕 Новый скин: {name}")
                            logging.info(f"[Worker {worker_id}] 🆕 Новый скин: {name}")
                        else:
                            print(f"[Worker {worker_id}] 🆕 Новый скин: {formatted_name_console}\n🎯 Float: {current_float_on_aim}")
                            logging.info(f"[Worker {worker_id}] 🆕 Новый скин: {formatted_name_console}\n🎯 Float: {current_float_on_aim}")
                        print(f"[Worker {worker_id}] 💸 Цена: {current_price_on_aim}")
                        logging.info(f"[Worker {worker_id}] 💸 Цена: {current_price_on_aim}")
                        print(f"[Worker {worker_id}] 🔗 Ссылка: {href}")
                        logging.info(f"[Worker {worker_id}] 🔗 Ссылка: {href}")
                        print(f"[Worker {worker_id}] ------------------------------")
                        logging.info(f"[Worker {worker_id}] ------------------------------")
                await asyncio.sleep(5)

            except json.JSONDecodeError as e:
                print(f"[Worker {worker_id}] [{proxy}] Ошибка декодирования JSON: {e}. Пропускаю итерацию.")
                logging.error(f"[Worker {worker_id}] [{proxy}] Ошибка декодирования JSON: {e}. Пропускаю итерацию.")
                await asyncio.sleep(5)
                continue 
            except Exception as e:
                print(f"[Worker {worker_id}] [{proxy}] Ошибка: {e}")
                logging.error(f"[Worker {worker_id}] [{proxy}] Ошибка: {e}")
                new_proxy = await self.session_initializer.find_new_proxy(worker_id, proxy, self.used_proxies, self.failed_proxies, PROXY_FILE)
                if new_proxy:
                    print(f"[Worker {worker_id}] Переключаюсь на новый прокси после ошибки: {new_proxy}")
                    logging.info(f"[Worker {worker_id}] Переключаюсь на новый прокси после ошибки: {new_proxy}")
                    proxy = new_proxy
                    session = AsyncSession(client_identifier='chrome_133', random_tls_extension_order=True)
                    continue
                else:
                    print(f"[Worker {worker_id}] Не удалось найти новый прокси, воркер завершает работу.")
                    logging.error(f"[Worker {worker_id}] Не удалось найти новый прокси, воркер завершает работу.")
                    break
    
    async def main(self):
        num_workers = 1
        max_attempts = 3

        items_db_instance = ItemsDatabase(items)
        item_filter_instance = ItemFilterEXP(items_db_instance)

        for attempt in range(max_attempts):
            try:
                working_proxies = await self.session_initializer.initialize_workers(num_workers, proxy_file=PROXY_FILE)
                if not working_proxies:
                    print("Не удалось получить рабочие прокси. Попытка {attempt + 1}/{max_attempts}")
                    logging.error(f"Не удалось получить рабочие прокси. Попытка {attempt + 1}/{max_attempts}")
                    if attempt == max_attempts -1:
                        print("Все попытки исчерпаны, не удалось получить прокси.")
                        logging.error("Все попытки исчерпаны, не удалось получить прокси.")
                        return 
                    await asyncio.sleep(5)
                    continue

                seen_ids = set()
                seen_lock = asyncio.Lock()
                parse_tasks = []
                
                for worker_id, proxy in working_proxies.items():
                    parse_tasks.append(self.parse_worker(worker_id, proxy, seen_ids, seen_lock, item_filter_instance))
                
                await asyncio.gather(*parse_tasks)
                break
                
            except Exception as e:
                print(f"Попытка {attempt + 1}/{max_attempts} не удалась: {e}")
                logging.error(f"Попытка {attempt + 1}/{max_attempts} не удалась: {e}")
                if attempt == max_attempts - 1:
                    print("Все попытки исчерпаны")
                    logging.error("Все попытки исчерпаны")
                    raise 
                await asyncio.sleep(10)

async def periodic_items_update():
    global items
    while True:
        try:
            print("Обновляю items.json ...")
            logging.info("Обновляю items.json ...")
            await fetch_and_save()
            with open("items.json", "r", encoding="utf-8") as f:
                items = json.load(f)
            print("items.json обновлён и перечитан в память!\nНекст обновление через 3 часа.")
            logging.info("items.json обновлён и перечитан в память!\nНекст обновление через 3 часа.")
        except Exception as e:
            print(f"Ошибка при обновлении items.json: {e}")
            logging.error(f"Ошибка при обновлении items.json: {e}")
        await asyncio.sleep(3 * 60 * 60)

@dp.message()
async def status_handler(message: types.Message):
    if message.chat.type != "private":
        return
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()[-10:]
            logs = "".join(lines)
        else:
            logs = "Лог-файл не найден."
        await message.answer(f"✅ Чекай!\n\nПоследние 10 логов:\n\n<pre>{logs}</pre>", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    aimmarket_app = Aimmarket()
    async def runner():
        print("Первичная загрузка items.json ...")
        logging.info("Первичная загрузка items.json ...")
        await fetch_and_save()
        global items
        with open("items.json", "r", encoding="utf-8") as f:
            items = json.load(f)
        print("Первичная загрузка items.json завершена!")
        logging.info("Первичная загрузка items.json завершена!")
        asyncio.create_task(periodic_items_update())

        # Запускаем aiogram polling параллельно с парсером
        parser_task = asyncio.create_task(aimmarket_app.main())
        polling_task = asyncio.create_task(dp.start_polling(bot))
        await asyncio.gather(parser_task, polling_task)

    asyncio.run(runner())