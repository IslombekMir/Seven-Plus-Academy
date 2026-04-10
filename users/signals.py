from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, UserSettings
import requests

from django.conf import settings
from users.services.eskiz import EskizClient

@receiver(post_save, sender=User)
def create_user_settings(sender, instance, created, **kwargs):
    if created:
        UserSettings.objects.create(user=instance)




def get_eskiz_token():
    login_url = "https://notify.eskiz.uz/api/auth/login"

    data = {
        "email": "YOUR_EMAIL",
        "password": "YOUR_PASSWORD"
    }

    response = requests.post(login_url, data=data)
    result = response.json()

    if response.status_code != 200 or "data" not in result:
        print("Eskiz login error:", result)
        return None

    return result["data"]["token"]





@receiver(post_save, sender=User)
def send_user_sms(sender, instance, created, **kwargs):
    if not created:
        return

    if not instance.phone_number:
        return

    try:
        client = EskizClient(
            email=settings.ESKIZ_EMAIL,
            password=settings.ESKIZ_PASSWORD
        )

        message = f"Login: {instance.username} | Password: {instance.username}"

        client.send_sms(
            phone=instance.phone_number,
            message=message
        )

    except Exception as e:
        print(f"SMS failed: {e}")