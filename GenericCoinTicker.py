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


def checkMarketMovement(obj, coinPair, printValue=False):
    timeStamp = time.time()
    currentTimeStamp = time.time()
    market_data = obj.GetMarketHistory(coinPair, "1m", timeStamp)
    try:
        currentPrice = float(market_data[0]['close'])
    except:
        return
    for timeMargin in intervals:
        timeStamp = time.time() - timeMargin
        market_data = obj.GetMarketHistory(
            coinPair, "1m", timeStamp, currentTimeStamp)
        try:
            previousPrice = float(market_data[len(market_data)-1]['close'])
        except:
            continue
        priceMovement = (currentPrice - previousPrice)/currentPrice

        found = False
        if priceMovement <= BUY_THRESHOLD:
            print("\t\t\tBUYING THE FUCKING {0}\t\t\t".format(coinPair))
            found = True
        elif priceMovement >= SELL_THRESHOLD:
            print("\t\t\tSELL THE FUCKING {0}\t\t\t".format(coinPair))
            found = True
           
        if printValue or found:
            print("Coin-> {4}\tInterval {3}\tCurrentPrice-> {0}\tPreviousPrice-> {1}\tPriceMovement-> {2}\t".format(
                "₹{:,}".format(currentPrice), "₹{:,}".format(previousPrice), round(priceMovement * 100, 5), timeMargin, coinPair))


data = ImportFile('CoinPairs.json')
dcx = api.CoinDCX()
while(True):
    for item in data:
        checkMarketMovement(dcx, item['pair'])
