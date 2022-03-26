import time
from xml.etree.ElementTree import PI
import requests
from datetime import datetime

CoinPair = "I-BTC_INR"
buyPrice = 3300000
sellPrice = 3350000
counter = 0 # 0 means INR in wallet, 1 means btc in wallet
PNLtillnow = 0
moneyInWallet = 237000
btcInWallet = 0
investedAmount = moneyInWallet

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

def checkMarketPrice(coinPair, price, pnl, money):
    global moneyInWallet, PNLtillnow, btcInWallet, counter
    timeStamp = int(round(time.time() * 1000))
    url = "https://public.coindcx.com/market_data/candles?pair={1}&interval=1m&startTime={0}".format(timeStamp, coinPair) #desired market pair.
    try:
        response = requests.get(url)
        market_data = response.json()
    except:
        time.sleep(30)
        return
    currentPrice = float(market_data[0]['high'])
    # currentPrice = tp
    # print ("Current price {0}, requested price {1}".format(currentPrice, price))
    if price >= currentPrice and counter == 0:
        print ("Bought BTCINR at {0} at time {1}".format(price,datetime.now()))
        btcInWallet = float(moneyInWallet)/ float(price)         
        moneyInWallet = 0
        counter = 1
        print ("Money in wallet ",moneyInWallet)
        print ("BTC in wallet ",btcInWallet)
        print("\n")
    elif counter == 1 and price <= currentPrice:
        print ("Sold BTCINR at {0} at time {1}".format(price,datetime.now()))
        moneyInWallet = btcInWallet * float(price)
        btcInWallet = 0
        counter = 0
        print ("Money in wallet ",moneyInWallet)
        print ("BTC in wallet ",btcInWallet)
        print("\n")


start = time.time()
while(True):
    # testprice = int(input())
    if counter == 0:
        checkMarketPrice(CoinPair, buyPrice, PNLtillnow, moneyInWallet)#, testprice)
    else: 
        checkMarketPrice(CoinPair, sellPrice, PNLtillnow, moneyInWallet)#, testprice)
    end = time.time()
    timeElapsed = end - start
    if timeElapsed >= 900:
        start = time.time()
        currentPrice = getCurrentPrice()
        currentValue = (float(currentPrice) * float(btcInWallet)) + moneyInWallet
        print ("PNL at {0} is {1} at price of {2} and wallet value is {3}".format(datetime.now(),currentValue - investedAmount, currentPrice, currentValue))
    time.sleep(60)
