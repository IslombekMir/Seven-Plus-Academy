import requests
import time


class EskizClient:
    BASE_URL = "https://notify.eskiz.uz/api"

    _token = None
    _token_time = 0
    _ttl = 60 * 60  # 1 hour cache

    def __init__(self, email, password):
        self.email = email
        self.password = password

    def _login(self):
        url = f"{self.BASE_URL}/auth/login"

        data = {
            "email": self.email,
            "password": self.password
        }

        response = requests.post(url, data=data)
        result = response.json()

        if "data" not in result:
            raise Exception(f"Eskiz login failed: {result}")

        return result["data"]["token"]

    def _get_token(self):
        now = time.time()

        if self._token and (now - self._token_time) < self._ttl:
            return self._token

        self._token = self._login()
        self._token_time = now

        return self._token

    def send_sms(self, phone, message):
        url = f"{self.BASE_URL}/message/sms/send"

        headers = {
            "Authorization": f"Bearer {self._get_token()}"
        }

        data = {
            "mobile_phone": phone,
            "message": message,
            "from": "4546",
        }

        response = requests.post(url, headers=headers, data=data)

        return response.json()