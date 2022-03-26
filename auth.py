from decouple import config
import hmac
import hashlib
import json
from math import trunc
from tabnanny import check
import time
import datetime
import requests

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
    # Generating a timestamp
    timeStamp = int(round(time.time() * 1000))

    body = {
        "timestamp": timeStamp
    }

    json_body = json.dumps(body, separators = (',', ':'))

    signature = hmac.new(secret_bytes, json_body.encode(), hashlib.sha256).hexdigest()
    # get user balances

    headers = {
        'Content-Type': 'application/json',
        'X-AUTH-APIKEY': key,
        'X-AUTH-SIGNATURE': signature
    }
    try:
        url = "https://api.coindcx.com/exchange/v1/users/balances"
        response = requests.post(url, data = json_body, headers = headers)
        data = response.json()
    except:
        return {"quantity":0,"availableBalance":0}
    for i in data:
        if i['currency'] == currency and float(i['balance']) > threshold:
            # print (i)
            if printAmount:
                print ("{0} is {1}".format(currency, i['balance']))
            return {"quantity":i['balance'],"availableBalance":float(i['balance'])}
    
    return {"quantity":0,"availableBalance":0}

def createOrder(pricePerUnit, quantity, orderType):
    # Generating a timestamp.
    timeStamp = int(round(time.time() * 1000))
    # print ()
    body = {
    "side": orderType,    #Toggle between 'buy' or 'sell'.
    "order_type": "limit_order", #Toggle between a 'market_order' or 'limit_order'.
    "market": "BTCINR", #Replace 'SNTBTC' with your desired market pair.
    "price_per_unit": pricePerUnit, #This parameter is only required for a 'limit_order'
    "total_quantity": quantity, #Replace this with the quantity you want
    "timestamp": timeStamp
    }

    json_body = json.dumps(body, separators = (',', ':'))

    signature = hmac.new(secret_bytes, json_body.encode(), hashlib.sha256).hexdigest()

    url = "https://api.coindcx.com/exchange/v1/orders/create"

    headers = {
        'Content-Type': 'application/json',
        'X-AUTH-APIKEY': key,
        'X-AUTH-SIGNATURE': signature
    }
    try:
        response = requests.post(url, data = json_body, headers = headers)
        data = response.json()
    except:
        return
    print(data)
    print ("{0} order at {1} for {2} at {3}\n".format(orderType,datetime.datetime.now(), quantity, pricePerUnit))

while(True):
    # print (datetime.datetime.now())
    pricePerUnitToBuy = 3315000
    pricePerUnitToSell = 3335000
    reduceBalance = 50

    balancePair = checkUserBalance(secret_bytes, "INR", 150)
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