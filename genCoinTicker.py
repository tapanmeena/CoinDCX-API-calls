from sqlite3 import Timestamp
import time
from tracemalloc import start
from xml.etree.ElementTree import PI
import requests
from datetime import datetime

CoinPair = "I-BTC_INR"
BUY_THRESHOLD = -0.02
SELL_THRESHOLD = 0.02

intervals = [300, 600, 900, 1200, 1500, 1800]
# def checkPrice(timestamp)


def checkMarketMovement(coinPair, printValue = False):
    global CoinPair
    timeStamp = int(round(time.time() * 1000))
    currenTimeStamp = int(round(time.time() * 1000))
    # desired market pair.
    url = "https://public.coindcx.com/market_data/candles?pair={1}&interval=1m&startTime={0}".format(
        timeStamp, coinPair)
    # print(url)
    try:
        response = requests.get(url)
        market_data = response.json()
    except:
        time.sleep(30)
        return
    currentPrice = float(market_data[0]['close'])

    for timeMargin in intervals:
        timeStamp = int(round(int((time.time() - timeMargin)) * 1000))
        url = "https://public.coindcx.com/market_data/candles?pair={1}&interval=1m&startTime={0}&endTime={2}".format(timeStamp, coinPair, currenTimeStamp)
        # print(url)
        try:
            response = requests.get(url)
            market_data = response.json()
        except:
            time.sleep(30)
            return
        previousPrice = float(market_data[len(market_data)-1]['close'])
        priceMovement = (currentPrice - previousPrice)/currentPrice
        if printValue:
            print("Interval {3}\tCurrentPrice-> {0}\t PreviousPrice-> {1}\t PriceMovement-> {2}\t".format(
            "₹{:,}".format(currentPrice),"₹{:,}".format(previousPrice), round(priceMovement * 100,5), timeMargin))
        if priceMovement <= BUY_THRESHOLD:
            print("\t\t\tBUYING THE FUCKING BTC\t\t\t")
        elif priceMovement >= SELL_THRESHOLD:
            print("\t\t\SELL THE FUCKING BTC\t\t\t")
        # break

start = time.time()
while(True):
    checkMarketMovement(CoinPair)
    time.sleep(60)
    current = time.time()
    if (current - start)>900:
        checkMarketMovement(CoinPair, True)
        start = time.time()
        print("\n")