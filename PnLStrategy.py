"""
In this strategy,
By default we're only picking INR pairs
The bot checks if the any coin has gone up by more than 5% in the last 5 minutes
The bot will sell at 1% profit or 3% loss
"""
from decouple import config
import api
import json
from random import randint
from datetime import timedelta, datetime
from math import trunc
import time

# Enter your API Key and Secret here. If you don't have one, you can generate it from the website.
key = config('key', default='')
secret = config('secret', default='')
secret_bytes = bytes(secret, encoding='utf-8')

STOP_LOSS = -0.03
STOP_PROFIT = 0.01
DELTA_CHANGE = 0.03
"""
TODO
Generate bought coin pair array - Done
Generate previous price coin pair array - for now make it same as bought coin array
check market for sell opportunity
include fee amount calculation in PNL logic
"""

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


def CheckMarketCoinPairs(coinPairs):
    data = api.GetMarketDetails()
    previous = datetime.now()- timedelta(minutes=5)
    previous = datetime.timestamp(previous)
    previous = int(round(previous * 1000))
    coinArray = []
    for pair in coinPairs:
        for item in data:
            if pair['coindcx_name'] == item['coindcx_name']:
                market_data = api.GetMarketHistory(item['pair'], "1m", previous)        
                currentIntervalMax = market_data[0]['high']
                currentIntervalMin = market_data[len(market_data)-1]['high']
                delta = (currentIntervalMax - currentIntervalMin)/ currentIntervalMax
                if delta >= DELTA_CHANGE:
                    coinArray.append({"name":item['coindcx_name'],"max":currentIntervalMax,"min":currentIntervalMin, "delta": delta, "target_precision":item['target_currency_precision'],"current_price":market_data[0]['close']})
                break
    return


def GenerateBoughtPairArray(coinPairs):
    data = api.GetTradeHistory(key, secret_bytes,100)
    coinSymbolList = [item['coindcx_name'] for item in coinPairs]
    data = [item for item in data if item['side'] == 'buy']
    data = [item for item in data if item['symbol'] in coinSymbolList]
    dataDup = []
    for item in data:
        found = False
        for i in dataDup:
            if i['symbol'] == item['symbol']:
                found = True
                break
        if not found:
            dataDup.append(item)
    data = dataDup

    bought_coin_pairs = api.GetUserBalance(key, secret_bytes)
    bought_coin_pairs = [item for item in bought_coin_pairs if item['currency'] != 'INR' and truncate(float(item['balance']), 5) > 0]
    bought_coin_pairs = [{'balance': '0.007', 'locked_balance': '0.0', 'currency': 'BTC'}]

    bought_coin_array = []
    for coin in bought_coin_pairs:
        for item in data:
            if item['symbol'].startswith(coin['currency']):
                bought_coin_array.append({"symbol": item['symbol'], "bought_price": item['price'], "quantity":coin['balance']})

    return bought_coin_array


def checkMarketForSell():
    return


def ImportFile(filename):
    file = open(filename)
    data = json.load(file)
    file.close()
    data = [item for item in data if item['active'] == 'true']
    return data


coin_pairs = ImportFile("CoinPairs.json")
print(GenerateBoughtPairArray(coin_pairs))
"""
while(True):
    balancePair = checkUserBalance(secret_bytes, "INR", 200)
    if balancePair['availableBalance']:
        suggestedBuyingArray = CheckMarketCoinPairs(coin_pairs)
        if len(suggestedBuyingArray)>0:
            buyingIndex = randint(0, len(suggestedBuyingArray)-1)
            selectedCoinPair = suggestedBuyingArray[buyingIndex]
            pricePerUnitToBuy = selectedCoinPair['current_price']
            if balancePair['availableBalance'] >= 500:
                buyingAmount = 500
            else:
                buyingAmount = balancePair['availableBalance'] - 50

            quantityToBuy = truncate(float(buyingAmount)/pricePerUnitToBuy, selectedCoinPair['target_precision'])
            # print (buyingAmount, pricePerUnitToBuy, quantityToBuy, selectedCoinPair["name"])
            # print(quantityToBuy)
            api.CreateOrder(key, secret_bytes, "buy", "limit_order", selectedCoinPair["name"], pricePerUnitToBuy, quantityToBuy)

    boughtArray = GenerateBoughtPairArray()
    previousChange = checkMarketForSell()
    time.sleep(60)
"""