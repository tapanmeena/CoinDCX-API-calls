
import hmac
import hashlib
import base64
import json
import time
import requests
from decouple import config

# Enter your API Key and Secret here. If you don't have one, you can generate it from the website.
key = config('key',default='')
secret = config('secret',default='')

# python3
secret_bytes = bytes(secret, encoding='utf-8')

# Generating a timestamp.
timeStamp = int(round(time.time() * 1000))

body = {
#   "id": "ead19992-43fd-11e8-b027-bb815bcb14ed", # Enter your Order ID here.
  # "client_order_id": "2022.02.14-btcinr_1", # Enter your Client Order ID here.
  "timestamp": timeStamp
}

json_body = json.dumps(body, separators = (',', ':'))

signature = hmac.new(secret_bytes, json_body.encode(), hashlib.sha256).hexdigest()

url = "https://api.coindcx.com/exchange/v1/orders/status"

headers = {
    'Content-Type': 'application/json',
    'X-AUTH-APIKEY': key,
    'X-AUTH-SIGNATURE': signature
}

response = requests.post(url, data = json_body, headers = headers)
data = response.json()
print(data)