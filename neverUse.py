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
        # print (data)
    except:
        return {"quantity":0,"availableBalance":0}
    for i in data:
        if i['currency'] == currency and float(i['balance']) > threshold:
            # print (i)
            if printAmount:
                print ("{0} is {1}".format(currency, i['balance']))
            return {"quantity":i['balance'],"availableBalance":float(i['balance'])}
    
    return {"quantity":0,"availableBalance":0}

def createOrder(quantity, orderType):
    # Generating a timestamp.
    timeStamp = int(round(time.time() * 1000))
    # print ()
    body = {
    "side": orderType,    #Toggle between 'buy' or 'sell'.
    "order_type": "market_order", #Toggle between a 'market_order' or 'limit_order'.
    "market": "BTCINR", #Replace 'SNTBTC' with your desired market pair.
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

def getCurrentPrice():
    timeStamp = int(round(time.time() * 1000))
    try:
        url = "https://public.coindcx.com/market_data/candles?pair=I-BTC_INR&interval=1m&startTime={0}".format(timeStamp) #desired market pair.
        response = requests.get(url)
        market_data = response.json()
    except:
        time.sleep(30)
        return 0
    currentPrice = float(market_data[0]['high'])
    return currentPrice

starting_balance = 2989.48
while(True):
    try:
        print (datetime.datetime.now())

        # create buy order
        pricePerUnit = getCurrentPrice()
        reduceBalance = 50
        balancePair = checkUserBalance(secret_bytes, "INR", 0)
        quantityToBuy = truncate(float(balancePair['availableBalance'] - reduceBalance)/pricePerUnit,5)
        createOrder(quantityToBuy, "buy")
        time.sleep(1800)

        # create sell order
        balancePair = checkUserBalance(secret_bytes, "BTC", 0.00001, True)
        print (balancePair)
        quantity = truncate(float(balancePair['quantity']),5)
        createOrder(quantity,"sell")

        # calculate PNL
        balancePair = checkUserBalance(secret_bytes, "INR", 0)
        currentBalance = float(balancePair['availableBalance'])
        print ("PNL is {0}".format(currentBalance-starting_balance))
        time.sleep(600)
    except:
        time.sleep(10)