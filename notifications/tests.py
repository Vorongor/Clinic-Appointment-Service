from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from unittest.mock import patch
from datetime import timedelta

from appointment.models import Appointment, DoctorSlot
from doctor.models import Doctor
from notifications.tasks import check_no_shows_daily

User = get_user_model()


class NotificationsTest(TestCase):
    def setUp(self):
        self.doctor = Doctor.objects.create(
            first_name="John",
            last_name="Doe",
            price_per_visit=100.00
        )

        self.user = User.objects.create(
            email="test_nik@example.com",
            first_name="Nik",
            last_name="Dem",
        )

        self.slot = DoctorSlot.objects.create(
            doctor=self.doctor,
            start=timezone.now() + timedelta(days=1),
            end=timezone.now() + timedelta(days=1, hours=1)
        )

    @patch("notifications.tasks.notify_admin_task.delay")
    def test_signal_create_appointment(self, mock_notify_task):
        Appointment.objects.create(
            doctor_slot=self.slot,
            patient=self.user,
            status=Appointment.Status.BOOKED
        )
        mock_notify_task.assert_called()

    @patch("notifications.tasks.notify_admin_task.delay")
    def test_signal_update_status_sends_notification(self, mock_notify_task):
        appt = Appointment.objects.create(
            doctor_slot=self.slot,
            patient=self.user,
            status=Appointment.Status.BOOKED
        )
        mock_notify_task.reset_mock()
        appt.status = Appointment.Status.COMPLETED
        appt.save()
        self.assertTrue(mock_notify_task.called)

    @patch("notifications.tasks.notify_admin_task.delay")
    def test_signal_no_notification_if_status_unchanged(self, mock_notify_task):
        appt = Appointment.objects.create(
            doctor_slot=self.slot,
            patient=self.user,
            status=Appointment.Status.BOOKED
        )
        mock_notify_task.reset_mock()
        appt.save()
        mock_notify_task.assert_not_called()

    @patch("notifications.tasks.send_telegram_message")
    @patch("notifications.tasks.notify_admin_task.apply_async")
    def test_check_no_shows_daily_task(self, mock_apply_async, mock_send_msg):

        past_slot = DoctorSlot.objects.create(
            doctor=self.doctor,
            start=timezone.now() - timedelta(hours=3),
            end=timezone.now() - timedelta(hours=2)
        )

        appt = Appointment.objects.create(
            doctor_slot=past_slot,
            patient=self.user,
            status=Appointment.Status.BOOKED
        )

        check_no_shows_daily()

        appt.refresh_from_db()
        self.assertEqual(appt.status, Appointment.Status.NO_SHOW)
        mock_send_msg.assert_called()
