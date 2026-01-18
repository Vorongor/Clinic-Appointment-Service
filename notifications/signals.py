from django.db.models.signals import post_save, pre_save
from django.db import transaction
from django.dispatch import receiver
from dataclasses import dataclass

from appointment.models import Appointment
from payment.models import Payment
from .tasks import notify_admin_task


@dataclass
class AppointmentDTO:
    id_: int
    status: str
    doctor_name: str
    patient_name: str
    slot_time: str
    price: str

    def to_message(self, event_type: str) -> str:
        headers = {
            "created": "🆕 **Новий запис**",
            "updated": "🔄 **Зміна статусу**",
        }
        return (
            f"{headers.get(event_type, '🔔 Повідомлення')}\n"
            f"🆔 Номер запису: #{self.id_}\n"
            f"👤 Пацієнт: {self.patient_name}\n"
            f"👨‍⚕️ Лікар: {self.doctor_name}\n"
            f"📅 Час: {self.slot_time}\n"
            f"💰 Сума: ${self.price}\n"
            f"🚩 Статус: {self.status}"
        )


@receiver(pre_save, sender=Appointment)
def capture_old_status(sender, instance, **kwargs):
    """
    Capture old status from DB before save
    """
    if instance.pk:
        try:
            old_obj = sender.objects.get(pk=instance.pk)
            instance._old_status = old_obj.status
        except sender.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Appointment)
def appointment_notification_signal(sender, instance, created, **kwargs):
    if created:
        send_appointment_msg(instance, "created")
        return

    old_status = getattr(instance, "_old_status", None)

    if old_status != instance.status:
        send_appointment_msg(instance, "updated")
    else:
        pass


def send_appointment_msg(instance, event):
    dto = AppointmentDTO(
        id_=instance.id,
        status=instance.get_status_display(),
        doctor_name=str(instance.doctor_slot.doctor),
        patient_name=f"{instance.patient.first_name} "
                     f"{instance.patient.last_name}",
        slot_time=instance.doctor_slot.start.strftime("%Y-%m-%d %H:%M"),
        price=str(instance.price)
    )
    notify_admin_task.delay(dto.to_message(event))


@receiver(post_save, sender=Payment)
def payment_notification_signal(sender, instance, created, **kwargs):
    """
        The signal reacts to a change in the payment status.
        We use transaction.on_commit so that the message is sent only
        after the status is actually committed to the database.
        """

    if instance.status == Payment.Status.PAID:
        status_type = "success"
    elif instance.status == Payment.Status.EXPIRED:
        status_type = "failed"
    else:
        return

    icon = "✅" if status_type == "success" else "❌"
    msg_title = ("Оплата отримана" if status_type == "success"
                 else "Оплата відмінена")

    patient_name = (f"{instance.appointment.patient.first_name} "
                    f"{instance.appointment.patient.last_name}")

    message = (
        f"{icon} **{msg_title}**\n"
        f"🆔 Номер запису: #{instance.appointment.id}\n"
        f"👤 Пацієнт: {patient_name}\n"
        f"💰 Сума: ${instance.money_to_pay}\n"
        f"🚩 Тип: {instance.get_payment_type_display()}"
    )

    transaction.on_commit(lambda: notify_admin_task.delay(message))
