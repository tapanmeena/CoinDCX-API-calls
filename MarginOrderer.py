from decouple import config
from math import trunc
import time
import datetime
import api
import TelegramApi

# Enter your API Key and Secret here. If you don't have one, you can generate it from the website.
key = config('key',default='')
secret = config('secret',default='')

#Enter your Telegram token here
token = config('telegramtoken',default='')
chatid = -707344100

secret_bytes = bytes(secret, encoding='utf-8')

def truncate(number, decimals=0):
    """
    Returns a value truncated to a specific number of decimal places.
    """
    if not isinstance(decimals, int):
        raise TypeError("decimal places must be an integer.")
    elif decimals < 0:
        raise ValueError("decimal places has to be 0 or more.")
    elif decimals == 0:
        return trunc(number)

    factor = 10.0 ** decimals
    return trunc(number * factor) / factor

def checkUserBalance(obj,currency, threshold, printAmount = False):
    data = obj.GetUserBalance(currency)
    
    if float(data['balance']) > threshold:
        if printAmount:
            print ("{0} is {1}".format(currency, data['balance']))
        return {"quantity":data['balance'],"availableBalance":float(data['balance'])}
    return {"quantity":0,"availableBalance":0}

# coinpair = input("Enter CoinPair: ")
# pricePerUnitToBuy = float(input("Price per unit to buy at: "))
# pricePerUnitToSell = float(input("Price per unit to sell at: "))
# leverage = float(input("Leverage: "))
coinpair = "MATICUSDT"
pricePerUnitToBuy = 1.04
pricePerUnitToSell = 1.05
leverage = 10
reduceBalance = 10
startTime = time.time()
dcx = api.CoinDCX(key, secret_bytes)
messaingClient = TelegramApi.Telegram(token, chatid)
liveReduceBalance = 0
while(True):
    balancePair = checkUserBalance(dcx, "USDT", 1, True)
    if balancePair['availableBalance']:
        totalAmount = float((balancePair['availableBalance'] - reduceBalance) * leverage)
        availableAmount = float(totalAmount - float(totalAmount * 0.001)) - liveReduceBalance
        quantityToBuy = truncate(float(availableAmount/pricePerUnitToBuy), 1)
        if quantityToBuy > 0.01:
            print(quantityToBuy)
            data = dcx.PlaceMarginOrder(coinpair, quantityToBuy, pricePerUnitToBuy, leverage, "buy", "limit_order", pricePerUnitToSell, "B")
            if data['message'] is not None:
                if data['message'] == "Insufficient funds":
                    liveReduceBalance += 10
                    continue
            else:
                liveReduceBalance = 0
                messaingClient.SendMessage("Placed long order of {}".format(coinpair))
                time.sleep(300)