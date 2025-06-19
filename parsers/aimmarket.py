import re
import json
import asyncio
from async_tls_client import AsyncSession
from core.base_parser import BaseParser
from core.filter import Item

class Aimmarket(BaseParser):

    async def parse_worker(self, worker_id, proxy, seen_ids, seen_lock, item_filter):

        session = AsyncSession(client_identifier='chrome_133', random_tls_extension_order=True)

        while True:
            try:
                r = await session.get(self.url, proxy=f"http://{proxy}")
                self.logger.info(f"[Worker {worker_id}] [{proxy}] Получен ответ: {r.status_code}, длина: {len(r.text)}")
                if r.status_code != 200 or "Internal Server Error" in r.text:
                    new_proxy = await self.session_initializer.find_new_proxy(
                        worker_id, proxy, self.used_proxies, self.failed_proxies, self.proxy_file
                    )
                    if new_proxy:
                        proxy = new_proxy
                        session = AsyncSession(client_identifier='chrome_133', random_tls_extension_order=True)
                        continue
                    else:
                        break

                m = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', r.text, re.DOTALL)
                if not m:
                    await asyncio.sleep(1)
                    continue

                state = json.loads(m.group(1))
                apollo_raw = state.get("cache", {}).get("apolloState")
                if not apollo_raw:
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
                        price_str = scraped_item_data.get("price", {}).get("sellPrice", "0")
                        float_value_str = scraped_item_data.get("float", None)
                        current_price_on_aim = float(price_str) if price_str else 0
                        current_float_on_aim = float(float_value_str) if float_value_str is not None else 0.0
                        exterior = scraped_item_data.get("exterior", "")
                        quality = scraped_item_data.get("quality", "")

                        item_obj = Item(
                            hash_name=name,
                            price=current_price_on_aim,
                            item_float=current_float_on_aim,
                            item_id=item_id,
                            market=self.market,
                            tier=self.items_manager.items.get(name, {}).get("asset", {}).get("tier", 0)
                        )

                        item_filter.filter_item(item_obj)
                        self.logger.info(f"[Worker {worker_id}] Проверка notify: {item_obj.notify, item_obj.hash_name, item_obj.price}")
                        
                        if item_obj.notify:
                            image_path = self.items_manager.items.get(name, {}).get("asset", {}).get("image_url")
                            image_to_send = None
                            if image_path:
                                if image_path.startswith("http"):
                                    image_to_send = image_path
                                else:
                                    image_to_send = f"https://steamcommunity-a.akamaihd.net/economy/image/{image_path}"

                            msg = await self.bot_utils.format_tg_message(item_obj, f"https://aim.market/item/{item_id}", self.items_manager.items)
                            aimmarket_link = self.links.make_aimmarket_link(item_obj.hash_name, item_id=item_obj.id)
                            csmarket_link = self.links.make_csmarket_link(item_obj.hash_name)
                            buff_link = self.links.make_buff_link(item_obj.hash_name)

                            await self.bot_utils.send_telegram(
                                bot=self.bot,
                                tg_chat_id=self.tg_chat_id,
                                market=self.market,
                                text=msg,
                                image_url=image_to_send,
                                market_link=aimmarket_link,
                                csmarket_link=csmarket_link,
                                buff_link=buff_link
                            )
                            self.logger.info(f"[ОТПРАВИЛ СМСКУ В ТЕЛЕГРАМ!] {item_obj.hash_name} - {item_obj.price}$ - {aimmarket_link}")

                await asyncio.sleep(5)

            except Exception as e:
                self.logger.error(f"[Worker {worker_id}] [{proxy}] Ошибка: {e}")
                new_proxy = await self.session_initializer.find_new_proxy(
                    worker_id, proxy, self.used_proxies, self.failed_proxies, self.proxy_file
                )
                if new_proxy:
                    proxy = new_proxy
                    session = AsyncSession(client_identifier='chrome_133', random_tls_extension_order=True)
                    continue
                else:
                    break