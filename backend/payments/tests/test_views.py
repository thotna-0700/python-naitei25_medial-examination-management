from rest_framework.test import APITestCase
from unittest.mock import patch, MagicMock
from django.urls import reverse
from django.utils import timezone
from datetime import date, time
from decimal import Decimal
from payments.models import Bill, BillDetail, Transaction
from appointments.models import Appointment, Service, ServiceOrder
from patients.models import Patient
from users.models import User
from doctors.models import Doctor, Department, ExaminationRoom, Schedule
from common.enums import PaymentStatus, PaymentMethod, TransactionStatus, ServiceType, Gender, AcademicDegree, UserRole, OrderStatus, RoomType, Shift, AppointmentStatus, DoctorType
from common.constants import SCHEDULE_DEFAULTS
from rest_framework import status
from rest_framework.exceptions import ValidationError
from django.http import Http404

class BaseTestCase(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            role=UserRole.PATIENT.value
        )
        cls.patient = Patient.objects.create(
            user=cls.user,
            first_name='Test',
            last_name='Patient',
            identity_number='111222333',
            insurance_number='INS123456',
            birthday=date(1990, 1, 1),
            gender=Gender.FEMALE.value
        )
        cls.department = Department.objects.create(department_name="Cardiology")
        cls.doctor = Doctor.objects.create(
            user=cls.user,
            first_name="John",
            last_name="Doe",
            identity_number="123456789",
            birthday=date(1980, 1, 1),
            gender=Gender.MALE.value,
            academic_degree=AcademicDegree.BS_CKI.value,
            specialization="Cardiologist",
            type=DoctorType.EXAMINATION.value,
            department=cls.department,
            price=Decimal('100.00')
        )
        cls.room = ExaminationRoom.objects.create(
            department=cls.department,
            type=RoomType.EXAMINATION.value,
            building="A",
            floor=1,
            note="Room 101"
        )
        cls.schedule = Schedule.objects.create(
            doctor=cls.doctor,
            room=cls.room,
            work_date=date(2025, 8, 26),
            start_time=time(8, 0),
            end_time=time(12, 0),
            shift=Shift.MORNING.value,
            max_patients=SCHEDULE_DEFAULTS["MAX_PATIENTS"],
            current_patients=SCHEDULE_DEFAULTS["CURRENT_PATIENTS"],
            status="AVAILABLE",
            default_appointment_duration_minutes=SCHEDULE_DEFAULTS["APPOINTMENT_DURATION_MINUTES"]
        )
        cls.appointment = Appointment.objects.create(
            doctor=cls.doctor,
            patient=cls.patient,
            schedule=cls.schedule,
            symptoms="Fever and cough",
            note="Initial consultation",
            slot_start=time(8, 0),
            slot_end=time(8, 30),
            status=AppointmentStatus.CONFIRMED.value
        )
        cls.service = Service.objects.create(
            service_name="Blood Test",
            service_type=ServiceType.CONSULTATION.value,
            price=Decimal('50.00')
        )
        cls.service_order = ServiceOrder.objects.create(
            appointment=cls.appointment,
            room=cls.room,
            service=cls.service,
            status=OrderStatus.ORDERED.value,
            number=1,
            order_time=timezone.now(),
        )
        cls.bill_unpaid = Bill.objects.create(
            appointment=cls.appointment,
            patient=cls.patient,
            total_cost=Decimal('200.00'),
            insurance_discount=Decimal('50.00'),
            amount=Decimal('150.00'),
            status=PaymentStatus.UNPAID.value
        )
        cls.bill_booking_paid = Bill.objects.create(
            appointment=cls.appointment,
            patient=cls.patient,
            total_cost=Decimal('200.00'),
            insurance_discount=Decimal('50.00'),
            amount=Decimal('150.00'),
            status=PaymentStatus.BOOKING_PAID.value
        )
        cls.bill_paid = Bill.objects.create(
            appointment=cls.appointment,
            patient=cls.patient,
            total_cost=Decimal('200.00'),
            insurance_discount=Decimal('50.00'),
            amount=Decimal('150.00'),
            status=PaymentStatus.PAID.value
        )
        cls.bill_detail = BillDetail.objects.create(
            bill=cls.bill_unpaid,
            item_type=ServiceType.CONSULTATION.value,
            quantity=2,
            unit_price=Decimal('100.00'),
            insurance_discount=Decimal('20.00'),
            total_price=Decimal('200.00')
        )
        cls.transaction_pending = Transaction.objects.create(
            bill=cls.bill_unpaid,
            amount=Decimal('150.00'),
            payment_method=PaymentMethod.ONLINE_BANKING.value,
            transaction_date=timezone.now(),
            status=TransactionStatus.PENDING.value
        )

    def setUp(self):
        self.client.force_authenticate(self.user)

class BillViewSetTest(BaseTestCase):
    def test_list_invalid_page(self):
        url = reverse('bill-list')
        response = self.client.get(url, {'page': 0, 'size': 10})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create(self):
        url = reverse('bill-list')
        data = {
            'appointment_id': self.appointment.id,
            'patient_id': self.patient.id,
            'total_cost': Decimal('300.00'),
            'insurance_discount': Decimal('50.00'),
            'amount': float('250.00'),
            'status': PaymentStatus.UNPAID.value,
            'bill_details': [
                {
                    'item_type': ServiceType.CONSULTATION.value,
                    'quantity': 1,
                    'unit_price': Decimal('100.00'),
                    'insurance_discount': Decimal('0.00')
                }
            ]
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Bill.objects.count(), 4)  # 3 from setup + 1 new

    def test_create_invalid(self):
        url = reverse('bill-list')
        data = {
            'appointment_id': 999,  # invalid
            'patient_id': self.patient.id,
            'total_cost': Decimal('300.00'),
            'insurance_discount': Decimal('50.00'),
            'amount': float('250.00'),
            'status': PaymentStatus.UNPAID.value
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_not_found(self):
        url = reverse('bill-detail', kwargs={'pk': 999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_not_found(self):
        url = reverse('bill-detail', kwargs={'pk': 999})
        data = {
            'status': PaymentStatus.PAID.value
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_destroy(self):
        url = reverse('bill-detail', kwargs={'pk': self.bill_paid.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Bill.objects.filter(id=self.bill_paid.id).exists())

    def test_destroy_not_found(self):
        url = reverse('bill-detail', kwargs={'pk': 999})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_bill_details_not_found(self):
        url = reverse('bill-create-bill-details', kwargs={'pk': 999})
        data = []
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_bill_details(self):
        url = reverse('bill-get-bill-details', kwargs={'pk': self.bill_unpaid.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # from setup

    def test_get_bill_details_not_found(self):
        url = reverse('bill-get-bill-details', kwargs={'pk': 999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_bills_by_patient_id(self):
        url = reverse('bill-get-bills-by-patient-id', kwargs={'patient_id': self.patient.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

class MockPaymentResponse:
    def __init__(self, url):
        self.checkoutUrl = url

class TransactionViewSetTest(BaseTestCase):
    @patch('payos.PayOS.createPaymentLink')
    def test_create_payment(self, mock_create):
        mock_create.return_value = MockPaymentResponse('https://pay.test.com')
        url = reverse('transaction-create-payment', kwargs={'bill_id': self.bill_unpaid.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertEqual(response.data['data'], 'https://pay.test.com')

    @patch('payos.PayOS.createPaymentLink')
    def test_create_payment_error(self, mock_create):
        mock_create.side_effect = Exception('Test error')
        url = reverse('transaction-create-payment', kwargs={'bill_id': self.bill_unpaid.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_process_cash_payment_unpaid(self):
        url = reverse('transaction-process-cash-payment', kwargs={'bill_id': self.bill_unpaid.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_process_cash_payment_paid(self):
        url = reverse('transaction-process-cash-payment', kwargs={'bill_id': self.bill_paid.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('payments.services.PayOSService.handle_payment_callback')
    def test_handle_payment_webhook(self, mock_handle):
        mock_handle.return_value = None
        self.client.force_authenticate(None)  # no auth
        url = reverse('transaction-handle-payment-webhook')
        data = {'signature': 'test', 'data': {}}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('payos.PayOS.cancelPaymentLink')
    def test_cancel_payment(self, mock_cancel):
        mock_cancel.return_value = {'status': 'CANCELLED'}
        url = reverse('transaction-cancel-payment', kwargs={'order_id': 123})
        response = self.client.put(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)

    def test_handle_payment_success(self):
        url = reverse('transaction-handle-payment-success', kwargs={'order_id': self.bill_unpaid.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.transaction_pending.refresh_from_db()
        self.assertEqual(self.transaction_pending.status, TransactionStatus.SUCCESS.value)
        self.bill_unpaid.refresh_from_db()
        self.assertEqual(self.bill_unpaid.status, PaymentStatus.PAID.value)  # bill has details, so PAID

    def test_handle_payment_cancel(self):
        url = reverse('transaction-handle-payment-cancel', kwargs={'order_id': self.bill_unpaid.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.transaction_pending.refresh_from_db()
        self.assertEqual(self.transaction_pending.status, TransactionStatus.FAILED.value)

    def test_get_transactions_by_bill_id(self):
        url = reverse('transaction-get-transactions-by-bill-id', kwargs={'bill_id': self.bill_unpaid.id})
        response = self.client.get(url, {'sort_by': 'transaction_date', 'sort_order': 'desc'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertGreaterEqual(len(response.data['data']), 1)

    def test_get_transactions_by_bill_id_not_found(self):
        url = reverse('transaction-get-transactions-by-bill-id', kwargs={'bill_id': 999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
