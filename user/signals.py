from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from user.models import Patient

User = get_user_model()

@receiver(post_save, sender=User)
def create_patient_profile(sender, instance, created, **kwargs):
    if created:
        Patient.objects.create(user=instance)

@receiver(post_delete, sender=Patient)
def delete_user_with_patient(sender, instance, **kwargs):
    if instance.user:
        instance.user.delete()
