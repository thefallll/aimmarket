from core.filter import Item, ItemsDatabase, ItemFilterEXP 
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

class TelegramBotUtils:
    async def format_tg_message(self, item_obj: Item, href: str, items) -> dict:
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
    

    async def send_telegram(self, bot, tg_chat_id, market, text, image_url=None, market_link=None, csmarket_link=None, buff_link=None):

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=market, url=market_link),
                InlineKeyboardButton(text="MARKET", url=csmarket_link),
                InlineKeyboardButton(text="BUFF163", url=buff_link),
            ]
        ])
        if image_url:
            await bot.send_photo(
                tg_chat_id,
                photo=image_url,
                caption=text,
                reply_markup=keyboard
            )
        else:
            await bot.send_message(
                tg_chat_id,
                text,
                reply_markup=keyboard
            )