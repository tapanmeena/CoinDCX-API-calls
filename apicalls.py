import time
import hmac
import hashlib
import json
import requests

PUBLIC_HOST = 'https://public.coindcx.com'
API_HOST = 'https://api.coindcx.com'
CANDLES = '/market_data/candles'
VERSION = 'v1'
EXCHANGE_BASE = API_HOST + '/exchange/' + VERSION


def SendGetRequest(url):
    try:
        response = requests.get(url)
        data = response.json()
        return data
    except:
        return None


def SendPostRequest(url, data, headers):
    try:
        response = requests.post(url, data=data, headers=headers)
        data = response.json()
        return data
    except:
        return None


def GenerateHeaders(key, secret_bytes, json_body):
    signature = hmac.new(secret_bytes, json_body.encode(),
                         hashlib.sha256).hexdigest()
    headers = {
        'Content-Type': 'application/json',
        'X-AUTH-APIKEY': key,
        'X-AUTH-SIGNATURE': signature
    }

    return headers


def GetMarketHistory(pair, interval, startTime=time.time()-300, endTime=time.time()):
    """
    function returns last 5 minutes Market history for provided coinpair
    for detailed Market history, use startTime and endTime parameter

    pair = 
    interval = m -> minutes, h -> hours, d -> days, w -> weeks, M -> months

    """
    startTime = str(round(startTime - 300) * 1000)
    endTime = str(round(endTime) * 1000)

    url = PUBLIC_HOST + CANDLES + "?pair=" + pair + "&interval=" + \
        interval + "&startTime=" + startTime + "&endTime=" + endTime
    data = SendGetRequest(url)

    return data


def GetUserBalance(key, secret_bytes, coin_name=None):
    # Generating a timestamp
    timeStamp = int(round(time.time() * 1000))
    body = {
        "timestamp": timeStamp
    }

    json_body = json.dumps(body, separators=(',', ':'))

    signature = hmac.new(secret_bytes, json_body.encode(),
                         hashlib.sha256).hexdigest()

    headers = {
        'Content-Type': 'application/json',
        'X-AUTH-APIKEY': key,
        'X-AUTH-SIGNATURE': signature
    }

    url = EXCHANGE_BASE+"/users/balances"
    data = SendPostRequest(url, json_body, headers)

    if data is None:
        return {"quantity": 0, "availableBalance": 0}

    # return all coin balances
    if coin_name is None:
        return data

    for item in data:
        if item['currency'] == coin_name:
            return item


def CreateOrder(key, secret_bytes, side, orderType, coinPair, pricePerUnit, quantity):
    # Generating a timestamp.
    timeStamp = int(round(time.time() * 1000))

    body = {
        "side": side,
        "order_type": orderType,
        "market": coinPair,
        "price_per_unit": pricePerUnit,
        "total_quantity": quantity,
        "timestamp": timeStamp
    }
    json_body = json.dumps(body, separators=(',', ':'))
    url = EXCHANGE_BASE + '/orders/create'

    headers = GenerateHeaders(key, secret_bytes, json_body)
    data = SendPostRequest(url, json_body, headers)

    # check if order executed or not
    if data.get('orders') is not None:
        return data
    else:
        print(data)
        return