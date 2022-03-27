from decouple import config
from math import trunc
import time
import datetime
import api

# Enter your API Key and Secret here. If you don't have one, you can generate it from the website.
key = config('key',default='')
secret = config('secret',default='')

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

def checkUserBalance(secret_bytes, currency, threshold, printAmount = False):
    data = api.GetUserBalance(key, secret_bytes, currency)
    
    if float(data['balance']) > threshold:
        if printAmount:
            print ("{0} is {1}".format(currency, data['balance']))
        return {"quantity":data['balance'],"availableBalance":float(data['balance'])}
    return {"quantity":0,"availableBalance":0}

def createOrder(pricePerUnit, quantity, orderType):
    data = api.CreateOrder(key, secret_bytes, orderType, "limit_order", "BTCINR", pricePerUnit, round(float(quantity),5))
    print(data)
    print ("{0} order at {1} for {2} at {3}\n".format(orderType,datetime.datetime.now(), quantity, pricePerUnit))

while(True):
    # print (datetime.datetime.now())
    pricePerUnitToBuy = 3437000
    pricePerUnitToSell = 3464800
    reduceBalance = 50

    balancePair = checkUserBalance(secret_bytes, "INR", 50)
    # print("{0} present in wallet: {1}".format("INR",balancePair['availableBalance']>150))

    if balancePair['availableBalance']:
        quantityToBuy = truncate(float(balancePair['availableBalance'] - reduceBalance)/pricePerUnitToBuy,5)
        # print(quantityToBuy)
        createOrder(pricePerUnitToBuy, quantityToBuy, "buy")

    balancePair = checkUserBalance(secret_bytes, "BTC", 0.00001, True)
    # print("{0} present in wallet: {1}".format("BTC",balancePair['availableBalance']>0))

    if balancePair['availableBalance']:
        createOrder(pricePerUnitToSell,balancePair['quantity'],"sell")
    # print("\n")
    time.sleep(30)