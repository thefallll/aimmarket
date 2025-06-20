import asyncio
from functools import partial
from aiogram.filters import Command
from parsers.aimmarket import Aimmarket
from parsers.lisskins import LisSkins
from core.items_manager import ItemsManager

async def main():
    items_manager = ItemsManager(log_file="items_update.log")
    await items_manager.refresh()

    aimmarket_app = Aimmarket(
        url="https://aim.market/en/buy?auto_update=true&order_column=createdAt",
        market="AIMMARKET",
        proxy_file="proxy-list.txt",
        log_file="aimmarket.log",
        items_manager=items_manager,
        token_env_var="AIMMARKET_TG_TOKEN",
        chat_id_env_var="AIMMARKET_TG_CHAT_ID"
    )

    lisskins_app = LisSkins(
        url=None,
        market="LISSKINS",
        log_file="lisskins.log",
        items_manager=items_manager,
        token_env_var="LISSKINS_TG_TOKEN",
        chat_id_env_var="LISSKINS_TG_CHAT_ID"
    )

    parsers = [aimmarket_app ,lisskins_app]

    async def status_handler(message, parser_instance):
        if message.chat.type != "private":
            return
        try:
            with open(parser_instance.log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()[-10:]
            logs = "".join(lines)
            await message.answer(f"✅ Чекай!\n\nПоследние 10 логов для {parser_instance.market}:\n\n<pre>{logs}</pre>", parse_mode="HTML")
        except Exception as e:
            await message.answer(f"❌ Ошибка: {e}")

    for parser in parsers:
        handler_with_context = partial(status_handler, parser_instance=parser)
        parser.dp.message.register(handler_with_context)

    async def runner():
        auto_refresh_task = asyncio.create_task(items_manager.auto_refresh_items())

        parser_tasks = [asyncio.create_task(p.main()) for p in parsers]

        polling_tasks = [asyncio.create_task(p.dp.start_polling(p.bot)) for p in parsers]

        all_tasks = parser_tasks + polling_tasks + [auto_refresh_task]
        await asyncio.gather(*all_tasks)

    await runner()

if __name__ == "__main__":
    asyncio.run(main())