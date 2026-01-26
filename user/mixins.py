from django.db import transaction
from rest_framework.exceptions import ValidationError


class UserLogicMixin:
    def perform_user_update(self, serializer):
        try:
            with transaction.atomic():
                instance = serializer.save()
                password = self.request.data.get("password")
                if password:
                    instance.set_password(password)
                    instance.save()
        except Exception as e:
            raise ValidationError({
                "detail": f"Failed to update user data. Error: {str(e)}"
            })

    def perform_patient_create(self, serializer):
        try:
            with transaction.atomic():
                serializer.save(user=self.request.user)
        except Exception as e:
            raise ValidationError({
                "detail": f"Patient profile creation failed. Error: {str(e)}"
            })
