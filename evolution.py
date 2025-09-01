import requests

class EvolutionApi:
    def __init__(self, instance, api_key):
        self.instance = instance
        self.api_key = api_key

    def send_message(self, number, text):
        url = f"http://localhost:8080/message/sendText/{self.instance}"
        payload = {
            "number": number,
            "text": text
        }
        headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }
        response = requests.post(url, json=payload, headers=headers)
        print(response.text)
        return response.text