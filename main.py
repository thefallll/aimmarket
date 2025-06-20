import asyncio
from parsers.aimmarket import Aimmarket
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
    )
    bot = aimmarket_app.bot
    dp = aimmarket_app.dp

    @dp.message()
    async def status_handler(message):
        if message.chat.type != "private":
            return
        try:
            with open(aimmarket_app.log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()[-10:]
            logs = "".join(lines)
            await message.answer(f"✅ Чекай!\n\nПоследние 10 логов:\n\n<pre>{logs}</pre>", parse_mode="HTML")
        except Exception as e:
            await message.answer(f"❌ Ошибка: {e}")

    async def runner():

        auto_refresh_task = asyncio.create_task(items_manager.auto_refresh_items())

        parser_task = asyncio.create_task(aimmarket_app.main())

        polling_task = asyncio.create_task(dp.start_polling(bot))
        await asyncio.gather(parser_task, auto_refresh_task, polling_task)

    await runner()

if __name__ == "__main__":
    asyncio.run(main())