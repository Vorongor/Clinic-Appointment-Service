from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from user.models import Patient

User = get_user_model()

@receiver(post_save, sender=User)
def create_patient_profile(sender, instance, created, **kwargs):
    if created:
        Patient.objects.create(user=instance)
