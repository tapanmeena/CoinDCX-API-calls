import time
import hmac
import hashlib
import json
import requests

class CoinDCX:
    PUBLIC_HOST = 'https://public.coindcx.com'
    API_HOST = 'https://api.coindcx.com'
    CANDLES = '/market_data/candles'
    VERSION = 'v1'
    EXCHANGE_BASE = API_HOST + '/exchange/' + VERSION

    def __init__(self, key = None, secret_bytes = None):
        self.key = key
        self.secret_bytes = secret_bytes


    def SendGetRequest(self, url):
        try:
            response = requests.get(url)
            data = response.json()
            return data
        except:
            return None


    def SendPostRequest(self, url, data, headers):
        try:
            response = requests.post(url, data=data, headers=headers)
            data = response.json()
            return data
        except:
            return None


    def GenerateHeaders(self, json_body):
        signature = hmac.new(self.secret_bytes, json_body.encode(),
                            hashlib.sha256).hexdigest()
        headers = {
            'Content-Type': 'application/json',
            'X-AUTH-APIKEY': self.key,
            'X-AUTH-SIGNATURE': signature
        }

        return headers


    def GetMarketHistory(self, pair, interval, startTime="", endTime=""):
        """
        function returns last 5 minutes Market history for provided coinpair
        for detailed Market history, use startTime and endTime parameter

        pair = 
        interval = m -> minutes, h -> hours, d -> days, w -> weeks, M -> months

        """
        if startTime != "":
            startTime = str(round(startTime - 300) * 1000)
        if endTime != "":
            endTime = str(round(endTime) * 1000)

        url = self.PUBLIC_HOST + self.CANDLES + "?pair=" + pair + "&interval=" + interval + "&startTime=" + startTime + "&endTime=" + endTime
        data = self.SendGetRequest(url)

        return data


    def GetMarketDetails(self):
        url = self.EXCHANGE_BASE + "/markets_details"
        data = self.SendGetRequest(url)
        return data


    def GetUserBalance(self, coin_name=None):
        # Generating a timestamp
        timeStamp = int(round(time.time() * 1000))
        body = {
            "timestamp": timeStamp
        }
        json_body = json.dumps(body, separators=(',', ':'))
        headers = self.GenerateHeaders(json_body)
        url = self.EXCHANGE_BASE+"/users/balances"
        data = self.SendPostRequest(url, json_body, headers)

        if data is None:
            return {"quantity": 0, "availableBalance": 0}

        # return all coin balances
        if coin_name is None:
            return data

        for item in data:
            if item['currency'] == coin_name:
                return item


    def GetTradeHistory(self, limit = 500):
        timeStamp = int(round(time.time() * 1000))
        url = self.EXCHANGE_BASE + "/orders/trade_history"
        body = {
            "timestamp": timeStamp,
            "sort": "desc",
            "limit": limit
        }
        json_body = json.dumps(body, separators = (',', ':'))
        headers = self.GenerateHeaders(json_body)
        data = self.SendPostRequest(url, json_body, headers)
        return data


    def CreateOrder(self, side, orderType, coinPair, pricePerUnit, quantity):
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
        url = self.EXCHANGE_BASE + '/orders/create'
        headers = self.GenerateHeaders(json_body)
        data = self.SendPostRequest(url, json_body, headers)

        # check if order executed or not
        if data.get('orders') is not None:
            return data
        else:
            print(data)
            return


    def CancelOrders(self, pair_name, side = None):
        # Generating a timestamp.
        timeStamp = int(round(time.time() * 1000))

        body = {
            "market": pair_name,
            "timestamp": timeStamp
        }

        if side is not None:
            body["side"] = side

        json_body = json.dumps(body, separators=(',', ':'))
        url = self.EXCHANGE_BASE + '/orders/cancel_all'

        headers = self.GenerateHeaders(json_body)
        data = self.SendPostRequest(url, json_body, headers)

        # check if order executed or not
        if data.get('orders') is not None:
            return data
        else:
            print(data)
            return


    def GetActiveOrders(self):
        # Generating a timestamp.
        timeStamp = int(round(time.time() * 1000))
        body = {
            "timestamp": timeStamp
        }
        json_body = json.dumps(body, separators = (',', ':'))
        url = self.EXCHANGE_BASE + "/orders/active_orders"
        headers = self.GenerateHeaders(json_body)

        response = requests.post(url, data = json_body, headers = headers)
        data = response.json()
        return data

    def PlaceMarginOrder(self, side, orderType, coinPair, pricePerUnit, quantity, ecode, leverage):
        # Generating a timestamp.
        timeStamp = int(round(time.time() * 1000))

        body = {
            "side": side,
            "order_type": orderType,
            "market": coinPair,
            "price": pricePerUnit,
            "quantity": quantity,
            "ecode": ecode,
            "leverage": leverage,
            "timestamp": timeStamp
        }
        json_body = json.dumps(body, separators=(',', ':'))
        url = self.EXCHANGE_BASE + '/margin/create'
        headers = self.GenerateHeaders(json_body)
        data = self.SendPostRequest(url, json_body, headers)

        # check if order executed or not
        if data.get('orders') is not None:
            return data
        else:
            print(data)
            return

    def CancelMarginOrder(self, id):
        # Generating a timestamp.
        timeStamp = int(round(time.time() * 1000))

        body = {
            "id": id,
            "timestamp": timeStamp
        }
        json_body = json.dumps(body, separators=(',', ':'))
        url = self.EXCHANGE_BASE + '/margin/cancel'
        headers = self.GenerateHeaders(json_body)
        data = self.SendPostRequest(url, json_body, headers)

        # check if order executed or not
        if data.get('orders') is not None:
            return data
        else:
            print(data)
            return
    
    def ExitMarginOrder(self, id):
        # Generating a timestamp.
        timeStamp = int(round(time.time() * 1000))

        body = {
            "id": id,
            "timestamp": timeStamp
        }
        json_body = json.dumps(body, separators=(',', ':'))
        url = self.EXCHANGE_BASE + '/margin/exit'
        headers = self.GenerateHeaders(json_body)
        data = self.SendPostRequest(url, json_body, headers)

        # check if order executed or not
        if data.get('orders') is not None:
            return data
        else:
            print(data)
            return
    