import json
import requests

class Telegram:
    API_HOST = 'https://api.telegram.org/bot'

    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id

    def SendMessage(self, message):
        """Sends message via Telegram"""
        url = self.API_HOST + self.token + "/sendMessage"
        data = {
           "chat_id": self.chat_id,
           "text": message
        }

        try:
            response = requests.request("POST", url, params= data)
            telegram_data = json.loads(response.text)
        except Exception as e:
            print("An error occurred in sending the alert message via Telegram")
            print(e)