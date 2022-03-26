import time
import apicalls

CoinPair = "I-BTC_INR"
BUY_THRESHOLD = -0.015
SELL_THRESHOLD = 0.02

intervals = [300, 600, 900, 1200, 1500, 1800, 2700, 3600]

def checkMarketMovement(coinPair, printValue = False):
    timeStamp = time.time()
    currentTimeStamp = time.time()
    market_data = apicalls.GetMarketHistory(coinPair,"1m",timeStamp)
  
    currentPrice = float(market_data[0]['close'])
    for timeMargin in intervals:
        timeStamp = time.time() - timeMargin
        market_data = apicalls.GetMarketHistory(coinPair, "1m", timeStamp, currentTimeStamp)
        previousPrice = float(market_data[len(market_data)-1]['close'])
        priceMovement = (currentPrice - previousPrice)/currentPrice
        
        if printValue:
            print("Interval {3}\tCurrentPrice-> {0}\t PreviousPrice-> {1}\t PriceMovement-> {2}\t".format(
            "₹{:,}".format(currentPrice),"₹{:,}".format(previousPrice), round(priceMovement * 100,5), timeMargin))
        if priceMovement <= BUY_THRESHOLD:
            print("\t\t\tBUYING THE FUCKING BTC\t\t\t")
        elif priceMovement >= SELL_THRESHOLD:
            print("\t\t\SELL THE FUCKING BTC\t\t\t")

startTime = time.time()
while(True):
    checkMarketMovement(CoinPair)
    time.sleep(30)
    current = time.time()
    if (current - startTime)>900:
        checkMarketMovement(CoinPair, True)
        startTime = time.time()
        print("\n")