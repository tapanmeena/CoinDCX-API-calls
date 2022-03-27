"""
In this strategy,
By default we're only picking INR pairs
The bot checks if the any coin has gone up by more than 5% in the last 5 minutes
The bot will sell at 1% profit or 3% loss
"""
from random import randint
import time
from decouple import config
from math import trunc
import datetime
from datetime import datetime,timedelta
import api

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
    data = api.GetUserBalance(key, secret_bytes, currency)

    if float(data['balance']) > threshold:
        if printAmount:
            print ("{0} is {1}".format(currency, data['balance']))
        return {"quantity":data['balance'],"availableBalance":float(data['balance'])}
    return {"quantity":0,"availableBalance":0}

def createOrder(quantity, orderType, market, pricePerUnit):
    global boughtArray, previousChange
    
    try:
        data = api.CreateOrder(key, secret_bytes, orderType, "limit_order", market, pricePerUnit, quantity)
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
    try:
        data = api.GetMarketDetails()
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
            market_data = api.GetMarketHistory(item['pair'], "1m", previous)
            # print(tempURL)
            currentIntervalMax = market_data[0]['high']
            currentIntervalMin = market_data[len(market_data)-1]['high']
            delta = (currentIntervalMax - currentIntervalMin)/ currentIntervalMax
            if delta >= DELTA_CHANGE:
                totalcoins += 1
                coinArray.append({"name":item['coindcx_name'],"max":currentIntervalMax,"min":currentIntervalMin, "delta": delta, "target_precision":item['target_currency_precision']})
    lines = sorted(coinArray, key=lambda k: k['delta'], reverse=True)
    # print (lines)
    # print ("Total Coins:" ,totalcoins)
    return lines

def checkMarketForSell(previousPrice):
    global boughtArray
    data = api.GetMarketDetails()

    previous = datetime.now()- timedelta(minutes=5)
    previous = datetime.timestamp(previous)
    previous = int(round(previous * 1000))

    for coin in boughtArray:
        for item in data:
            if item['coindcx_name'] == coin['symbol']:
                market_data = api.GetMarketHistory(item['pair'], "1m", previous)

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
    data = api.GetMarketDetails()
    previous = datetime.now()- timedelta(minutes=5)
    previous = datetime.timestamp(previous)
    previous = int(round(previous * 1000))
    for item in data:
        # print (item)
        if item['coindcx_name'] == coin['name']:
            market_data = api.GetMarketHistory(item['pair'], "1m", previous)
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