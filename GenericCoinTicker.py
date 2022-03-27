import time
import api
import json

BUY_THRESHOLD = -0.015
SELL_THRESHOLD = 0.02

intervals = [300, 600, 900, 1200, 1500, 1800, 2700, 3600]

def ImportFile(filename):
    file = open(filename)
    data = json.load(file)
    file.close()
    data = [item for item in data if item['active'] == 'true']
    return data

def checkMarketMovement(coinPair, printValue = False):
    timeStamp = time.time()
    currentTimeStamp = time.time()
    market_data = api.GetMarketHistory(coinPair,"1m",timeStamp)
    try:
        currentPrice = float(market_data[0]['close'])
    except:
        return
    for timeMargin in intervals:
        timeStamp = time.time() - timeMargin
        market_data = api.GetMarketHistory(coinPair, "1m", timeStamp, currentTimeStamp)
        try:
            previousPrice = float(market_data[len(market_data)-1]['close'])
        except:
            continue
        priceMovement = (currentPrice - previousPrice)/currentPrice
        
        if printValue:
            print("Coin-> {4}\tInterval {3}\tCurrentPrice-> {0}\t PreviousPrice-> {1}\t PriceMovement-> {2}\t".format(
            "₹{:,}".format(currentPrice),"₹{:,}".format(previousPrice), round(priceMovement * 100,5), timeMargin, coinPair))
        if priceMovement <= BUY_THRESHOLD:
            print("\t\t\tBUYING THE FUCKING {0}\t\t\t".format(coinPair))
        elif priceMovement >= SELL_THRESHOLD:
            print("\t\t\SELL THE FUCKING {0}\t\t\t".format(coinPair))

data = ImportFile('CoinPairs.json')
startTime = time.time()
while(True):
    for item in data:
        checkMarketMovement(item['pair'])
    time.sleep(30)
    current = time.time()
    if (current - startTime)>900:
        for item in data:
            checkMarketMovement(item['pair'], True)
        startTime = time.time()
        print("\n")