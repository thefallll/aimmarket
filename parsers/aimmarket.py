import re
import json
import os

from async_tls_client import AsyncSession

import asyncio
from aiogram import types

from core.initialize_session import InitializeSession
from core.filter import Item, ItemsDatabase, ItemFilterEXP 
from core.logger import Logger
from core.bot_utils import TelegramBotUtils
from core.bot import TelegramBot
from core.json_db import fetch_and_save
from core.items_manager import ItemsManager
from core.links import MarketLinksMixin

from urllib.parse import quote


PROXY_FILE = 'proxy-list.txt'

class Aimmarket:
    def __init__(self, url, market, log_file):
        self.session_initializer = InitializeSession(URL=url)
        self.market = market
        self.log_file = log_file
        self.logger = Logger.setup_logger(log_file=self.log_file)
        self.tg_bot = TelegramBot()
        self.bot = self.tg_bot.get_bot()
        self.dp = self.tg_bot.get_dispatcher()
        self.tg_chat_id = self.tg_bot.get_chat_id()
        self.tg_token = self.tg_bot.get_token()
        self.bot_utils = TelegramBotUtils()
        self.used_proxies = set()
        self.failed_proxies = set()
        self.items_manager = ItemsManager()
        MarketLinksMixin.__init__(self, self.items_manager)

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

    async def parse_worker(self, worker_id, proxy, seen_ids, seen_lock, item_filter):
        url = 'https://aim.market/en/buy?auto_update=true&order_column=createdAt'
        session = AsyncSession(client_identifier='chrome_133', random_tls_extension_order=True)
        
        while True:
            try:
                r = await session.get(url, proxy=f"http://{proxy}")
                print(f"[Worker {worker_id}] [{proxy}] Получен ответ: {r.status_code}, длина: {len(r.text)}")
                self.logger.info(f"[Worker {worker_id}] [{proxy}] Получен ответ: {r.status_code}, длина: {len(r.text)}")
                if r.status_code != 200 or "Internal Server Error" in r.text:
                    print(f"[Worker {worker_id}] [{proxy}] БАН или плохой ответ ({r.status_code})")
                    self.logger.error(f"[Worker {worker_id}] [{proxy}] БАН или плохой ответ ({r.status_code})")
                    new_proxy = await self.session_initializer.find_new_proxy(worker_id, proxy, self.used_proxies, self.failed_proxies, PROXY_FILE)
                    if new_proxy:
                        print(f"[Worker {worker_id}] Переключаюсь на новый прокси: {new_proxy}")
                        self.logger.info(f"[Worker {worker_id}] Переключаюсь на новый прокси: {new_proxy}")
                        proxy = new_proxy
                        session = AsyncSession(client_identifier='chrome_133', random_tls_extension_order=True)
                        continue
                    else:
                        print(f"[Worker {worker_id}] Не удалось найти новый прокси, воркер завершает работу.")
                        self.logger.error(f"[Worker {worker_id}] Не удалось найти новый прокси, воркер завершает работу.")
                        break
                
                html = r.text
                m = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', html, re.DOTALL)
                if not m:
                    print(f"[Worker {worker_id}] [{proxy}] Не найден INITIAL_STATE, пропускаю итерацию.")
                    self.logger.warning(f"[Worker {worker_id}] [{proxy}] Не найден INITIAL_STATE, пропускаю итерацию.")
                    await asyncio.sleep(1) 
                    continue

                state = json.loads(m.group(1))
                apollo_raw = state.get("cache", {}).get("apolloState")
                if not apollo_raw:
                    print(f"[Worker {worker_id}] [{proxy}] Не найден apolloState, пропускаю итерацию.")
                    self.logger.warning(f"[Worker {worker_id}] [{proxy}] Не найден apolloState, пропускаю итерацию.")
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
                            market=self.market,
                            tier=self.items_manager.items.get(name, {}).get("asset", {}).get("tier", 0)
                        )
                        
                        item_filter.filter_item(item_obj) 

                        if item_obj.notify:
                            image_path_from_json = self.items_manager.items.get(name, {}).get("asset", {}).get("image_url")
                            image_to_send = None

                            if image_path_from_json:
                                if image_path_from_json.startswith("http://") or image_path_from_json.startswith("https://"):
                                    image_to_send = image_path_from_json
                                else:
                                    image_to_send = f"https://steamcommunity-a.akamaihd.net/economy/image/{image_path_from_json}"
                            
                            msg = self.bot_utils.format_tg_message(item_obj, href, self.items_manager.items)

                            aimmarket_link = self.make_aimmarket_link(item_obj.hash_name)
                            csmarket_link = self.make_csmarket_link(item_obj.hash_name)
                            buff_link = self.make_buff_link(item_obj.hash_name)

                            print("[AIMMARKET LINK]:", aimmarket_link)

                            await self.bot_utils.send_telegram(
                                                    bot=self.bot,
                                                    tg_chat_id = self.tg_chat_id,
                                                    market=self.market,
                                                    text = msg,                                                     
                                                    image_url=image_to_send,
                                                    market_link=aimmarket_link,
                                                    csmarket_link=csmarket_link,
                                                    buff_link=buff_link)
                        
                        formatted_name_console = self.format_skin_name(name, quality, exterior)
                        if float_value_str is None:
                            print(f"[Worker {worker_id}] 🆕 Новый скин: {name}")
                            self.logger.info(f"[Worker {worker_id}] 🆕 Новый скин: {name}")
                        else:
                            print(f"[Worker {worker_id}] 🆕 Новый скин: {formatted_name_console}\n🎯 Float: {current_float_on_aim}")
                            self.logger.info(f"[Worker {worker_id}] 🆕 Новый скин: {formatted_name_console}\n🎯 Float: {current_float_on_aim}")
                        print(f"[Worker {worker_id}] 💸 Цена: {current_price_on_aim}")
                        self.logger.info(f"[Worker {worker_id}] 💸 Цена: {current_price_on_aim}")
                        print(f"[Worker {worker_id}] 🔗 Ссылка: {href}")
                        self.logger.info(f"[Worker {worker_id}] 🔗 Ссылка: {href}")
                        print(f"[Worker {worker_id}] ------------------------------")
                        self.logger.info(f"[Worker {worker_id}] ------------------------------")
                await asyncio.sleep(5)

            except json.JSONDecodeError as e:
                print(f"[Worker {worker_id}] [{proxy}] Ошибка декодирования JSON: {e}. Пропускаю итерацию.")
                self.logger.error(f"[Worker {worker_id}] [{proxy}] Ошибка декодирования JSON: {e}. Пропускаю итерацию.")
                await asyncio.sleep(5)
                continue 
            except Exception as e:
                print(f"[Worker {worker_id}] [{proxy}] Ошибка: {e}")
                self.logger.error(f"[Worker {worker_id}] [{proxy}] Ошибка: {e}")
                new_proxy = await self.session_initializer.find_new_proxy(worker_id, proxy, self.used_proxies, self.failed_proxies, PROXY_FILE)
                if new_proxy:
                    print(f"[Worker {worker_id}] Переключаюсь на новый прокси после ошибки: {new_proxy}")
                    self.logger.info(f"[Worker {worker_id}] Переключаюсь на новый прокси после ошибки: {new_proxy}")
                    proxy = new_proxy
                    session = AsyncSession(client_identifier='chrome_133', random_tls_extension_order=True)
                    continue
                else:
                    print(f"[Worker {worker_id}] Не удалось найти новый прокси, воркер завершает работу.")
                    self.logger.error(f"[Worker {worker_id}] Не удалось найти новый прокси, воркер завершает работу.")
                    break
    
    async def main(self):
        num_workers = 1
        max_attempts = 3

        items_db_instance = ItemsDatabase(self.items_manager.items)
        item_filter_instance = ItemFilterEXP(items_db_instance)

        for attempt in range(max_attempts):
            try:
                working_proxies = await self.session_initializer.initialize_workers(num_workers, proxy_file=PROXY_FILE)
                if not working_proxies:
                    print("Не удалось получить рабочие прокси. Попытка {attempt + 1}/{max_attempts}")
                    self.logger.error(f"Не удалось получить рабочие прокси. Попытка {attempt + 1}/{max_attempts}")
                    if attempt == max_attempts -1:
                        print("Все попытки исчерпаны, не удалось получить прокси.")
                        self.logger.error("Все попытки исчерпаны, не удалось получить прокси.")
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
                self.logger.error(f"Попытка {attempt + 1}/{max_attempts} не удалась: {e}")
                if attempt == max_attempts - 1:
                    print("Все попытки исчерпаны")
                    self.logger.error("Все попытки исчерпаны")
                    raise 
                await asyncio.sleep(10)


if __name__ == "__main__":
    aimmarket_app = Aimmarket(
        url="https://aim.market/en/buy?auto_update=true&order_column=createdAt", 
        market="AIMMARKET", 
        log_file="aimmarket.log")
    
    bot = aimmarket_app.bot
    dp = aimmarket_app.dp

    @dp.message()
    async def status_handler(message: types.Message):
        if message.chat.type != "private":
            return
        try:
            if os.path.exists(aimmarket_app.log_file):
                with open(aimmarket_app.log_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()[-10:]
                logs = "".join(lines)
            else:
                logs = "Лог-файл не найден."
            await message.answer(f"✅ Чекай!\n\nПоследние 10 логов:\n\n<pre>{logs}</pre>", parse_mode="HTML")
        except Exception as e:
            await message.answer(f"❌ Ошибка: {e}")

    async def runner(aimmarket_app, bot, dp):
        parser_task = asyncio.create_task(aimmarket_app.main())
        polling_task = asyncio.create_task(dp.start_polling(bot))
        await asyncio.gather(parser_task, polling_task)

    asyncio.run(runner(aimmarket_app=aimmarket_app, dp=dp, bot=bot))