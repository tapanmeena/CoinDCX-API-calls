"""
In this strategy,
By default we're only picking INR pairs
The bot checks if the any coin has gone up by more than 5% in the last 5 minutes
The bot will sell at 3% profit or 2% loss
"""
from dataclasses import dataclass
from operator import truediv
from random import randint, random
import time
from urllib import request
from xml.etree.ElementTree import PI
from decouple import config
from math import trunc
from tabnanny import check
import datetime
import requests
from datetime import datetime,timedelta
import hmac
import hashlib
import json

# Enter your API Key and Secret here. If you don't have one, you can generate it from the website.
key = config('key',default='')
secret = config('secret',default='')
STOP_LOSS = -0.03
STOP_PROFIT = 0.01
DELTA_CHANGE = 0.03

secret_bytes = bytes(secret, encoding='utf-8')
boughtArray = [{'symbol': 'KSMINR', 'price': 12440}, {'symbol': 'ALICEINR', 'price': 540.31},{'symbol': 'LRCINR', 'price': 84.906}, {'symbol': 'AAVEINR', 'price': 11953.8}, {'price': 960.33, 'symbol': 'NEARINR'}, {'price': 9715.51, 'symbol': 'QNTINR'}]
previousChange = boughtArray

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

    url = "https://api.coindcx.com/exchange/v1/users/balances"
    try:
        response = requests.post(url, data = json_body, headers = headers)
        data = response.json()
    except:
        time.sleep(30)
        return {"quantity":0,"availableBalance":0}

    for i in data:
        if i['currency'] == currency and float(i['balance']) > threshold:
            if printAmount:
                print ("{0} is {1}".format(currency, i['balance']))
            return {"quantity":i['balance'],"availableBalance":float(i['balance'])}
    
    return {"quantity":0,"availableBalance":0}

def createOrder(quantity, orderType, market, pricePerUnit):
    global boughtArray, previousChange
    # Generating a timestamp.
    timeStamp = int(round(time.time() * 1000))

    body = {
    "side": orderType,    #Toggle between 'buy' or 'sell'.
    "order_type": "limit_order", #Toggle between a 'market_order' or 'limit_order'.
    "market": market, #Replace 'SNTBTC' with your desired market pair.
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
        time.sleep(30)
        print ("No internet while ",market)
        return
    if data.get('orders') is not None:
        if orderType == "buy":
            print(data)
            # print (boughtArray)
            print ("{0} order at {1} for {2}\n".format(orderType,datetime.now(), quantity))
            boughtArray.append({'price': data['orders'][0]['price_per_unit'], 'symbol': data['orders'][0]['market']})
            previousChange.append({'price': data['orders'][0]['price_per_unit'], 'symbol': data['orders'][0]['market']})
            print (boughtArray)
        elif orderType == "sell":
            print ("SOLD    ",data['orders'][0]['market'])
            print (boughtArray)
            ind = 0
            tempArray = boughtArray
            for item in boughtArray:
                if item['symbol'] == market:
                    tempArray.pop(ind)
                ind += 1
            ind = 0
            boughtArray = tempArray
            tempArray = previousChange
            for item in previousChange:
                if item['symbol'] == market:
                    tempArray.pop(ind)
                    ind += 1
            previousChange = tempArray

def checkMarketForBuy():
    url = "https://api.coindcx.com/exchange/v1/markets_details" #retrieves all pairs
    try:
        response = requests.get(url)
        data = response.json()
    except:
        time.sleep(30)
        print ("no internet while checking market for current prices")
        return coinArray
    previous = datetime.now()- timedelta(minutes=5)
    previous = datetime.timestamp(previous)
    previous = int(round(previous * 1000))
    totalcoins = 0
    coinArray = []
    for item in data:
        if item['coindcx_name'].endswith('INR'):
            tempURL = "https://public.coindcx.com/market_data/candles?pair={1}&interval=1m&startTime={0}".format(previous, item['pair']) #desired market pair.
            try:
                response = requests.get(tempURL)
                market_data = response.json()
            except:
                time.sleep(30)
                return coinArray
            # print(tempURL)
            currentIntervalMax = market_data[0]['high']
            currentIntervalMin = market_data[len(market_data)-1]['high']
            delta = (currentIntervalMax - currentIntervalMin)/ currentIntervalMax
            if delta >= DELTA_CHANGE:
                totalcoins+=1
                coinArray.append({"name":item['coindcx_name'],"max":currentIntervalMax,"min":currentIntervalMin, "delta": delta, "target_precision":item['target_currency_precision']})
    lines = sorted(coinArray, key=lambda k: k['delta'], reverse=True)
    # print (lines)
    # print ("Total Coins:" ,totalcoins)
    return lines

def checkMarketForSell(previousPrice):
    global boughtArray
    url = "https://api.coindcx.com/exchange/v1/markets_details" #retrieves all pairs

    try:
        response = requests.get(url)
        data = response.json()
    except:
        time.sleep(30)
        return previousPrice
    previous = datetime.now()- timedelta(minutes=5)
    previous = datetime.timestamp(previous)
    previous = int(round(previous * 1000))

    for coin in boughtArray:
        for item in data:
            if item['coindcx_name'] == coin['symbol']:
                tempURL = "https://public.coindcx.com/market_data/candles?pair={1}&interval=1m&startTime={0}".format(previous, item['pair']) #desired market pair.
                try:
                    response = requests.get(tempURL)
                    market_data = response.json()
                except:
                    return previousPrice
                currentPrice = float(market_data[0]['high'])
                boughtPrice = float(coin['price'])
                ChangeInPrice = (currentPrice - boughtPrice)/currentPrice
                tempPreviousPrice = previousPrice
                for pItem in previousPrice:
                    if pItem['symbol'] == coin['symbol'] and pItem['price'] != market_data[0]['high']:
                        currenTime = datetime.today()
                        print ("Change at {0}".format(currenTime.strftime("%H:%M:%S")))
                        print ("Coin\tCurrent Price\tPrevious Price\tBought at\tChange")
                        print("{0}\t{1}\t{2}\t{3}\t{4}".format(coin['symbol'],currentPrice,round(float(pItem['price']),2), boughtPrice, ChangeInPrice*100))
                        print ("{0} coin currently at {1}, bought at {3}, previous price was {4} and change is {2}\n".format(coin['symbol'], currentPrice, ChangeInPrice*100, boughtPrice, round(float(pItem['price']),2)))
                        tempPreviousPrice.remove(pItem)
                        tempPreviousPrice.append({'symbol':coin['symbol'],"price":market_data[0]['high']})
                        break
                # print(tempPreviousPrice)
                previousPrice = tempPreviousPrice
                if ChangeInPrice >= STOP_PROFIT:
                    balancePair = checkUserBalance(secret_bytes, item['target_currency_short_name'], 0, True)
                    # print(balancePair)
                    createOrder(balancePair['quantity'],"sell",item['coindcx_name'], currentPrice)
                    print ("----------------------Please sell {0} coin at {1} because currect percentage increase is {2}----------------------".format(coin['symbol'], currentPrice, ChangeInPrice*100))
                elif ChangeInPrice <= STOP_LOSS:
                    balancePair = checkUserBalance(secret_bytes, item['target_currency_short_name'], 0, True)
                    # print(balancePair)
                    createOrder(balancePair['quantity'],"sell",item['coindcx_name'], currentPrice)
                    print ("----------------------Please sell {0} coin at {1} because currect percentage increase is {2}----------------------".format(coin['symbol'], currentPrice, ChangeInPrice*100))
    return previousPrice

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

def buyPair(coin):
    url = "https://api.coindcx.com/exchange/v1/markets_details" #retrieves all pairs

    try:
        response = requests.get(url)
        data = response.json()
    except:
        time.sleep(30)
        return 0
    previous = datetime.now()- timedelta(minutes=5)
    previous = datetime.timestamp(previous)
    previous = int(round(previous * 1000))
    for item in data:
        # print (item)
        if item['coindcx_name'] == coin['name']:
            tempURL = "https://public.coindcx.com/market_data/candles?pair={1}&interval=1m&startTime={0}".format(previous, item['pair']) #desired market pair.
            try:
                response = requests.get(tempURL)
                market_data = response.json()
            except:
                time.sleep(30)
                return 0
            currentPrice = float(market_data[0]['high'])
            return currentPrice

while(True):
    balancePair = checkUserBalance(secret_bytes, "INR", 200)
    if balancePair['availableBalance']:
        suggestedBuyingArray = checkMarketForBuy()
        buyingIndex = randint(0, len(suggestedBuyingArray)-1)
        selectedCoinPair = suggestedBuyingArray[buyingIndex]
        pricePerUnitToBuy = buyPair(selectedCoinPair)
        if balancePair['availableBalance'] >= 500:
            buyingAmount = 500
        else:
            buyingAmount = balancePair['availableBalance']
        quantityToBuy = truncate(float(buyingAmount)/pricePerUnitToBuy,selectedCoinPair['target_precision'])
        print (buyingAmount, pricePerUnitToBuy, quantityToBuy, selectedCoinPair["name"])
        # # print(quantityToBuy)
        createOrder(quantityToBuy, "buy", selectedCoinPair["name"],pricePerUnitToBuy)
    previousChange = checkMarketForSell(previousChange)
    time.sleep(60)