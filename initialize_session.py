import asyncio
import logging
from async_tls_client import AsyncSession

URL = "https://aim.market/en/buy?auto_update=true&order_column=createdAt"

class InitializeSession:

    def get_proxy_list(self, proxy_file=None):
        with open(proxy_file, 'r') as f:
            return [line.strip() for line in f if line.strip()]

    async def find_new_proxy(self, worker_id, old_proxy, used_proxies, failed_proxies, proxy_file=None):
        proxy_list = self.get_proxy_list(proxy_file)
        failed_proxies = set(failed_proxies)
        failed_proxies.add(old_proxy)
        for candidate in proxy_list:
            if candidate in failed_proxies or candidate in used_proxies:
                continue
            try:
                session = AsyncSession(
                    client_identifier='chrome_133',
                    random_tls_extension_order=True
                )
                resp = await session.get(URL, proxy=f"http://{candidate}")
                if resp.status_code == 200:
                    used_proxies.add(candidate)
                    print(f"[Worker {worker_id}] Новый прокси готов: {candidate}")
                    logging.info(f"[Worker {worker_id}] Новый прокси готов: {candidate}")
                    return candidate
            except Exception as e:
                print(f"[Worker {worker_id}] [{candidate}] Ошибка при проверке: {e}")
                logging.error(f"[Worker {worker_id}] [{candidate}] Ошибка при проверке: {e}")
                failed_proxies.add(candidate)
        return None
    async def test_worker(self, worker_id, delay, proxy_list, ready_event, ready_counter, total_workers, failed_proxies, used_proxies):
        """Инициализирует сессию для воркера и возвращает рабочий прокси"""
        await asyncio.sleep(delay)
        proxy = None
        session = AsyncSession(
            client_identifier='chrome_133',
            random_tls_extension_order=True
        )

        start_idx = worker_id - 1
        proxy_count = len(proxy_list)

        for i in range(proxy_count):
            candidate = proxy_list[(start_idx + i) % proxy_count]
            if candidate in failed_proxies or candidate in used_proxies:
                continue
            try:
                resp = await session.get(URL, proxy=f"http://{candidate}")
                if resp.status_code == 200:
                    async with ready_counter['lock']:
                        if candidate not in used_proxies:
                            proxy = candidate
                            used_proxies.add(proxy)
                            print(f"[Worker {worker_id}] Прокси готов: {proxy}")
                            logging.info(f"[Worker {worker_id}] Прокси готов: {proxy}")
                            ready_counter['count'] += 1
                            print(f"[Worker {worker_id}] Готов ({ready_counter['count']}/{total_workers})")
                            logging.info(f"[Worker {worker_id}] Готов ({ready_counter['count']}/{total_workers})")
                            if ready_counter['count'] == total_workers:
                                print("Все воркеры готовы! Начинаем парсинг!")
                                logging.info("Все воркеры готовы! Начинаем парсинг!")
                                ready_event.set()
                            return proxy
                else:
                    print(f"[Worker {worker_id}] [{candidate}] Статус: {resp.status_code} (не рабочий)")
                    logging.warning(f"[Worker {worker_id}] [{candidate}] Статус: {resp.status_code} (не рабочий)")
                    failed_proxies.add(candidate)
            except Exception as e:
                print(f"[Worker {worker_id}] [{candidate}] Ошибка: {e}")
                logging.error(f"[Worker {worker_id}] [{candidate}] Ошибка: {e}")
                failed_proxies.add(candidate)
        
        print(f"[Worker {worker_id}] Не найден рабочий прокси! Завершаю.")
        logging.error(f"[Worker {worker_id}] Не найден рабочий прокси! Завершаю.")
        return None

    async def initialize_workers(self, num_workers, proxy_file=None):
        """Инициализирует все воркеры и возвращает словарь рабочих прокси"""
        proxy_list = self.get_proxy_list(proxy_file)
        ready_event = asyncio.Event()
        ready_counter = {'count': 0, 'lock': asyncio.Lock()}
        failed_proxies = set()
        used_proxies = set()
        working_proxies = {}
        
        init_tasks = []
        for i in range(num_workers):
            task = self.test_worker(
                i+1,
                delay=0.05*i,
                proxy_list=proxy_list,
                ready_event=ready_event,
                ready_counter=ready_counter,
                total_workers=num_workers,
                failed_proxies=failed_proxies,
                used_proxies=used_proxies
            )
            init_tasks.append(task)

        results = await asyncio.gather(*init_tasks)

        for worker_id, proxy in enumerate(results, 1):
            if proxy:
                working_proxies[worker_id] = proxy
        
        if len(working_proxies) == num_workers:
            await ready_event.wait()
            return working_proxies
        else:
            logging.error(f"Не удалось инициализировать всеx воркерov! Готово {len(working_proxies)}/{num_workers}")
            raise Exception(f"Не удалось инициализировать всеx воркерov! Готово {len(working_proxies)}/{num_workers}")
