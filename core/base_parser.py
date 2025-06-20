import asyncio
from core.logger import Logger
from core.bot import TelegramBot
from core.bot_utils import TelegramBotUtils
from core.filter import ItemsDatabase, ItemFilterEXP
from core.initialize_session import InitializeSession
from core.items_manager import ItemsManager
from core.links import Links

class BaseParser:
    def __init__(self, url, market, token_env_var: str, chat_id_env_var: str, proxy_file="proxy-list.txt", log_file="parser.log", items_manager=None):
        self.url = url
        self.market = market
        self.proxy_file = proxy_file
        self.log_file = log_file

        self.logger = Logger.setup_logger(log_file=self.log_file)
        self.items_manager = items_manager or ItemsManager(logger=self.logger)

        self.tg_bot = TelegramBot(token_env_var=token_env_var, chat_id_env_var=chat_id_env_var)
        self.bot = self.tg_bot.get_bot()
        self.dp = self.tg_bot.get_dispatcher()
        self.tg_chat_id = self.tg_bot.get_chat_id()
        self.bot_utils = TelegramBotUtils()
        self.used_proxies = set()
        self.failed_proxies = set()
        self.links = Links(self.items_manager)
        self.session_initializer = InitializeSession(URL=self.url)

    async def parse_worker(self, worker_id, proxy, seen_ids, seen_lock, item_filter):
        raise NotImplementedError("Реализуй этот метод в дочернем классе!")      
      
    async def run_workers(self, item_filter_instance, num_workers=1, max_attempts=3):
        for attempt in range(max_attempts):
            try:
                working_proxies = await self.session_initializer.initialize_workers(
                    num_workers, proxy_file=self.proxy_file
                )
                if not working_proxies:
                    self.logger.error(f"Не удалось получить рабочие прокси. Попытка {attempt + 1}/{max_attempts}")
                    if attempt == max_attempts - 1:
                        self.logger.error("Все попытки исчерпаны, не удалось получить прокси.")
                        return
                    await asyncio.sleep(5)
                    continue

                seen_ids = set()
                seen_lock = asyncio.Lock()
                parse_tasks = [
                    self.parse_worker(worker_id, proxy, seen_ids, seen_lock, item_filter_instance)
                    for worker_id, proxy in working_proxies.items()
                ]
                await asyncio.gather(*parse_tasks)
                break

            except Exception as e:
                self.logger.error(f"Попытка {attempt + 1}/{max_attempts} не удалась: {e}")
                if attempt == max_attempts - 1:
                    self.logger.error("Все попытки исчерпаны")
                    raise
                await asyncio.sleep(10)

    async def main(self):
        items_db_instance = ItemsDatabase(self.items_manager.items)
        item_filter_instance = ItemFilterEXP(items_db_instance, logger=self.logger)
        await self.run_workers(item_filter_instance)