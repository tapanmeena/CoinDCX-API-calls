from decouple import config
import api

# Enter your API Key and Secret here. If you don't have one, you can generate it from the website.
key = config('key',default='')
secret = config('secret',default='')
secret_bytes = bytes(secret, encoding='utf-8')

dcx = api.CoinDCX(key, secret_bytes)


side = "buy"
price = "0.109"
total_quantity = 3934
leverage = 5

pair = "B-PEOPLE_USDT"
order_type = "limit_order"

dcx.PlaceFutureOrder(side, pair, price, order_type, total_quantity, leverage, notification="email_notification", time_in_force="good_till_cancel")