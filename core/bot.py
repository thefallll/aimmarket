import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram import types

from dotenv import load_dotenv
import os

load_dotenv()

class TelegramBot:
    def __init__(self, token_env_var: str, chat_id_env_var: str):
        self._tg_token = os.getenv(token_env_var)
        self._tg_chat_id = os.getenv(chat_id_env_var)

        if not self._tg_token or not self._tg_chat_id:
            raise ValueError(f"Переменные {token_env_var} и {chat_id_env_var} должны быть установлены в .env")

        self._bot = Bot(token=self._tg_token, default=DefaultBotProperties(parse_mode="Markdown"))
        self._dp = Dispatcher()

    def get_bot(self):
        return self._bot
    
    def get_dispatcher(self):
        return self._dp
    
    def get_token(self):
        return self._tg_token
    
    def get_chat_id(self):
        return self._tg_chat_id