import websockets
import asyncio
import aiohttp
import json
import os
from dotenv import load_dotenv

from core.base_parser import BaseParser
from core.filter import Item, ItemsDatabase, ItemFilterEXP

load_dotenv()
API_KEY = os.getenv("LISSKINS_API_KEY")
URI = "wss://ws.lis-skins.com/connection/websocket?cf_ws_frame_ping_pong=true"

class LisSkins(BaseParser):
    async def get_ws_token(self):
        """Получает временный токен для подключения к вебсокету."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'https://api.lis-skins.com/v1/user/get-ws-token', 
                headers={"Authorization": f"Bearer {API_KEY}"}
            ) as response:
                if response.status != 200:
                    self.logger.error(f"Ошибка получения токена LIS-SKINS: {response.status}")
                    raise Exception(f"Ошибка получения токена LIS-SKINS: {response.status}")
                data = await response.json()
                return data['data']['token']

    async def main(self):
        """Основной метод, который запускает прослушивание вебсокета."""
        items_db_instance = ItemsDatabase(self.items_manager.items)
        item_filter_instance = ItemFilterEXP(items_db_instance, logger=self.logger)
        
        while True:
            try:
                token = await self.get_ws_token()
                self.logger.info(f"Получен токен LIS-SKINS, подключаюсь к вебсокету...")
                
                async with websockets.connect(URI) as ws:
                    # Connect
                    connect_payload = {"connect": {"token": token, "name": "js"}, "id": 1}
                    await ws.send(json.dumps(connect_payload))
                    await ws.recv()

                    # Subscribe
                    sub_payload = {"subscribe": {"channel": "public:obtained-skins"}, "id": 2}
                    await ws.send(json.dumps(sub_payload))
                    await ws.recv()

                    self.logger.info("LIS-SKINS: Подписка подтверждена, начинаю слушать...")

                    while True:
                        msg = await ws.recv()
                        await self.process_message(msg, item_filter_instance)

            except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK) as e:
                self.logger.error(f"LIS-SKINS: Соединение с вебсокетом закрыто: {e}. Переподключаюсь через 5 секунд...")
                await asyncio.sleep(5)
            except Exception as e:
                self.logger.error(f"LIS-SKINS: Глобальная ошибка в main loop: {e}. Переподключаюсь через 15 секунд...")
                await asyncio.sleep(15)

    async def process_message(self, msg, item_filter: ItemFilterEXP):
        """Обрабатывает входящее сообщение от вебсокета, которое может содержать несколько JSON объектов."""

        json_strings = msg.replace('}{', '}\n{').split('\n')

        for json_str in json_strings:
            try:
                data = json.loads(json_str)
                pub = data.get("push", {}).get("pub", {})
                event_data = pub.get("data", {})
                event_type = event_data.get("event")

                if event_type == "obtained_skin_added":
                    hash_name = event_data['name']
                    price = float(event_data['price'])
                    item_float_str = event_data.get('item_float')
                    item_float = float(item_float_str) if item_float_str is not None else None
                    item_id = event_data.get('id')

                    self.logger.info(f"Новый скин на LISSKINS: {hash_name} за {price}$")

                    tier = self.items_manager.get_tier(hash_name)

                    item_obj = Item(
                        hash_name=hash_name,
                        price=price,
                        item_float=item_float,
                        item_id=item_id,
                        market=self.market,
                        tier=tier
                    )

                    item_filter.filter_item(item_obj)

                    if item_obj.notify:
                        self.logger.info(f"NOTIFY: {item_obj.hash_name} прошел фильтр!")
                        
                        image_url = self.items_manager.get_item_image(hash_name)
                        
                        market_link = self.links.make_lisskins_link(hash_name)
                        csmarket_link = self.links.make_csmarket_link(hash_name)
                        buff_link = self.links.make_buff_link(hash_name)

                        message_text = await self.bot_utils.format_tg_message(item_obj, market_link, self.items_manager.items)
                        
                        await self.bot_utils.send_telegram(
                            bot=self.bot,
                            tg_chat_id=self.tg_chat_id,
                            market=self.market,
                            text=message_text,
                            image_url=image_url,
                            market_link=market_link,
                            csmarket_link=csmarket_link,
                            buff_link=buff_link
                        )

            except json.JSONDecodeError:
                self.logger.warning(f"LIS-SKINS: Не удалось декодировать часть JSON: {json_str}")
            except Exception as e:
                self.logger.error(f"LIS-SKINS: Ошибка при обработке сообщения: {e}\nСообщение: {json_str}")