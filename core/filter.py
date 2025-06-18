from copy import deepcopy


class PriceCondition:
    def __init__(self, name: str, procent: float, price: float):
        self.name = name #  название условия, например "📈 MARKET SELL"
        self.procent = procent # профит 
        self.price = price # buff order buff sell market sell market sold и тд

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'price': self.price,
            'procent': f"+{self.procent}" if self.procent >= 0 else f"{self.procent}",
        }

class Item:
    def __init__(self, hash_name: str, price: float, item_float: float, item_id: int, market: str, tier: int):
        self.hash_name = hash_name
        self.price = price
        self.float = item_float
        self.id = item_id
        self.market = market
        self.tier = tier
        self.notify = False
        self.autobuy = False

        self.conditions: list[PriceCondition] = []


    def add_condition(self, condition: PriceCondition) -> None:
        self.conditions.append(condition)


    def __repr__(self):
        return f"[{self.market}] [{self.id}] - {self.hash_name}"


class ItemsDatabase:
    def __init__(self, items: dict, history: bool = False):
        self._items = items
        self._history = history
    

    def get(self, hash_name: str) -> dict:
        return deepcopy(self._items.get(hash_name))


    def get_item_image(self, hash_name: str, size: int = 512) -> str:
        data = self._items[hash_name]
        if data['asset']['image_url']:
            return f"https://community.fastly.steamstatic.com/economy/image/{data['asset']['image_url']}/{size}fx{size}f"
        return "https://orthomoda.ru/bitrix/templates/.default/img/no-photo.jpg"


    def get_tier(self, hash_name: str) -> int:
        data = self._items.get(hash_name)
        if not data:
            return -1
        tier = data['asset']['tier']
        if tier is None:
            return -1
        return tier


def calculate_procent(first: float, second: float) -> float: # second - за скок можем толкнуть (считает профит)
    if not first or not second:
        return 0
    return round((first - second) / second * 100, 2)


class ItemFilterEXP:
    def __init__(self, db: ItemsDatabase):
        self._db = db

    
    def filter_item(self, item: Item, notify_sell_procent: int = 0) -> None:
        if item.price < 10:
            return

        data = self._db.get(item.hash_name)
        if not data:
            return

        price = item.price

        buff = data['buff']
        csmarket = data['csmarket']

        buff_sell = buff['sell_avg14'] # авг ордеров на продажу на баффе за 14 дней 
        buff_order = buff['order_avg14'] # авг ордеров на покупку на баффе за 14 дней

        market_sell = csmarket['sell_avg14'] # авг ордеров на продажу на маркете за 14 дней
        market_sold = csmarket['sold_avg14'] # авг проданных на маркете за 14 дней

        market_peak_7 = csmarket['sold_peak']['7days'] # пики выше авг прайса на маркете за 7 дней
        market_peak_14 = csmarket['sold_peak']['14days']
        market_peak_30 = csmarket['sold_peak']['30days']
        market_peak_60 = csmarket['sold_peak']['60days']

        market_peak_7_p = csmarket['sold_peak']['7days_proc'] 
        market_peak_14_p = csmarket['sold_peak']['14days_proc']
        market_peak_30_p = csmarket['sold_peak']['30days_proc']
        market_peak_60_p = csmarket['sold_peak']['60days_proc']

        trend_7 = csmarket['trend']['7days'] # направление тренда на маркете за 7 дней
        trend_14 = csmarket['trend']['14days']
        trend_30 = csmarket['trend']['30days']
        trend_60 = csmarket['trend']['60days']

        trend_7 = trend_7 if trend_7 else 0
        trend_14 = trend_14 if trend_14 else 0
        trend_30 = trend_30 if trend_30 else 0
        trend_60 = trend_60 if trend_60 else 0

        week_sales = csmarket['avg_week_sales'] # среднее кол-во продаж на маркете за неделю

        buff_order_condition = PriceCondition(
            name="📉 BUFF ORDER",
            procent=calculate_procent(buff_order, price),
            price=buff_order,
        )
        buff_sell_condition = PriceCondition(
            name="📈 BUFF SELL",
            procent=calculate_procent(buff_sell, price),
            price=buff_sell
        )
        market_sell_condition = PriceCondition(
            name="📈 MARKET SELL",
            procent=calculate_procent(market_sell, price),
            price=market_sell,
        )
        market_sold_condition = PriceCondition(
            name="📊 MARKET SOLD",
            procent=calculate_procent(market_sold, price),
            price=market_sold,
        )
        market_peak7_condition = PriceCondition(
            name=f"🛒 7 PEAK {int(market_peak_7_p)}%",
            procent=calculate_procent(market_peak_7, price),
            price=market_peak_7,
        )
        market_peak14_condition = PriceCondition(
            name=f"🛒 14 PEAK {int(market_peak_14_p)}%",
            procent=calculate_procent(market_peak_14, price),
            price=market_peak_14,
        )
        market_peak30_condition = PriceCondition(
            name=f"🛒 30 PEAK {int(market_peak_30_p)}%",
            procent=calculate_procent(market_peak_30, price),
            price=market_peak_30,
        )
        market_peak60_condition = PriceCondition(
            name=f"🛒 60 PEAK {int(market_peak_60_p)}%",
            procent=calculate_procent(market_peak_60, price),
            price=market_peak_60,
        )

        item.add_condition(buff_sell_condition)
        item.add_condition(buff_order_condition)
        item.add_condition(market_sell_condition)
        item.add_condition(market_sold_condition)
        item.add_condition(market_peak7_condition)
        item.add_condition(market_peak14_condition)
        item.add_condition(market_peak30_condition)
        item.add_condition(market_peak60_condition)

        if item.float:
            for fc in data['buff']['float_conditions']:
                if fc['min'] < item.float < fc['max']:
                    if not fc['order_avg14']:
                        break
                    float_condition = PriceCondition(
                        name='\n🐬 FLOAT ORDER',
                        procent=calculate_procent(fc['order_avg14'], item.price),
                        price=fc['order_avg14'],
                    )
                    item.add_condition(float_condition)
                    if float_condition.procent > 2:
                        item.notify = True
                    break

        if all([
            (market_peak14_condition.procent > 23 and market_peak_14_p > 38 and trend_14 > -10)
            or
            (market_peak30_condition.procent > 23 and market_peak_30_p > 38 and trend_30 > -10),
            market_sold_condition.procent > 21 and market_sell_condition.procent > 21
        ]):
            item.notify = True
