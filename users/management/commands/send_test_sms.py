import requests
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Send test SMS via Eskiz"

    def add_arguments(self, parser):
        parser.add_argument("phone", type=str)

    def handle(self, *args, **options):
        phone = options["phone"]

        # 1. LOGIN
        login_url = "https://notify.eskiz.uz/api/auth/login"

        login_data = {
            "email": "mirsalimovislombek9@gmail.com",
            "password": "I84dilRXHrcAmteA27nGIae9RWz7nTgDrckvAoUL"
        }

        login_response = requests.post(login_url, data=login_data)
        token = login_response.json()["data"]["token"]

        self.stdout.write(f"Token OK: {token[:20]}...")

        # 2. SEND SMS
        sms_url = "https://notify.eskiz.uz/api/message/sms/send"

        headers = {
            "Authorization": f"Bearer {token}"
        }

        data = {
            "mobile_phone": phone,
            "message": "This is test from Eskiz",
            "from": "4546"
        }

        response = requests.post(sms_url, headers=headers, data=data)

        self.stdout.write(str(response.json()))