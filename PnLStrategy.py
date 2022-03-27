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
include fee amount calculation in PnL logic
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

    bought_coin_array = []
    for coin in bought_coin_pairs:
        for item in data:
            if item['symbol'].startswith(coin['currency']):
                bought_coin_array.append({"symbol": item['symbol'], "bought_price": item['price'], "quantity":coin['balance']})

    return bought_coin_array


def checkMarketForSell(bought_array, previous_change):
    data = api.GetMarketDetails()
    coin_symbol_list = [coin['symbol'] for coin in bought_array]
    data = [item for item in data if item['coindcx_name'] in coin_symbol_list]

    previous = datetime.now() - timedelta(minutes=5)
    previous = datetime.timestamp(previous)
    previous = int(round(previous * 1000))

    for coin in bought_array:
        for item in data:
            if coin['symbol'] == item['coindcx_name']:
                market_data = api.GetMarketHistory(item['pair'], "1m", previous)

                currentPrice = float(market_data[0]['high'])
                boughtPrice = float(coin['bought_price'])
                ChangeInPrice = (currentPrice - boughtPrice)/currentPrice
                temp_previous_change = previous_change

                for pItem in previous_change:
                    if pItem['symbol'] == coin['symbol'] and pItem['bought_price'] != market_data[0]['high']:
                        currenTime = datetime.today()
                        print ("Change at {0}".format(currenTime.strftime("%H:%M:%S")))
                        print ("{0} coin currently at {1}, bought at {3}, previous price was {4} and change is {2}\n".format(coin['symbol'], currentPrice, ChangeInPrice*100, boughtPrice, round(float(pItem['bought_price']),2)))
                        temp_previous_change.remove(pItem)
                        temp_previous_change.append({'symbol':coin['symbol'],"bought_price":market_data[0]['high']})
                        break
                previous_change = temp_previous_change

                if ChangeInPrice >= STOP_PROFIT or ChangeInPrice <= STOP_LOSS:
                    balancePair = checkUserBalance(secret_bytes, item['target_currency_short_name'], 0, True)
                    api.CreateOrder(key, secret_bytes, "sell", "limit_order", item['coindcx_name'], currentPrice, balancePair['quantity'])
                    print ("----------------------Please sell {0} coin at {1} because currect percentage increase is {2}----------------------".format(coin['symbol'], currentPrice, ChangeInPrice*100))
                break
    return previous_change


def ImportFile(filename):
    file = open(filename)
    data = json.load(file)
    file.close()
    data = [item for item in data if item['active'] == 'true']
    return data


coin_pairs = ImportFile("CoinPairs.json")
start_time = time.time()
end_time = start_time
while(True):
    balancePair = checkUserBalance(secret_bytes, "INR", 150)
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
            api.CreateOrder(key, secret_bytes, "buy", "limit_order", selectedCoinPair["name"], pricePerUnitToBuy, quantityToBuy)

    if end_time - start_time >= 900 or start_time == end_time:
        boughtArray = GenerateBoughtPairArray(coin_pairs)
        previousChange = boughtArray

    previousChange = checkMarketForSell(boughtArray, previousChange)

    end_time = time.time()
    time.sleep(60)