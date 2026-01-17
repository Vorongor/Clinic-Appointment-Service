from django.db.models.signals import post_save
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
            f"🆔 Номер: #{self.id_}\n"
            f"👤 Пацієнт: {self.patient_name}\n"
            f"👨‍⚕️ Лікар: {self.doctor_name}\n"
            f"📅 Час: {self.slot_time}\n"
            f"💰 Сума: ${self.price}\n"
            f"🚩 Статус: {self.status}"
        )


@receiver(post_save, sender=Appointment)
def appointment_notification_signal(sender, instance, created, **kwargs):
    dto = AppointmentDTO(
        id_=instance.id,
        status=instance.get_status_display(),
        doctor_name=str(instance.doctor_slot.doctor),
        patient_name=f"{instance.patient.first_name} "
                     f"{instance.patient.last_name}",
        slot_time=instance.doctor_slot.start.strftime("%Y-%m-%d %H:%M"),
        price=str(instance.price)
    )

    event = "created" if created else "updated"
    notify_admin_task.delay(dto.to_message(event))


@receiver(post_save, sender=Payment)
def payment_notification_signal(sender, instance, created, **kwargs):
    if instance.status == Payment.Status.PAID:
        message = (
            f"💳 **Оплата отримана!**\n"
            f"💰 Сума: ${instance.money_to_pay}\n"
            f"📄 Тип: {instance.get_payment_type_display()}\n"
            f"🔗 Для запису: #{instance.appointment_id}"
        )
        notify_admin_task.delay(message)
