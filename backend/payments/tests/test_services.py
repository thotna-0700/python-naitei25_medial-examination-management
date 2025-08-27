from django.test import TestCase
from unittest.mock import patch, MagicMock
from django.http import Http404
from django.utils import timezone
from datetime import date, time
from decimal import Decimal
from payments.services import BillService, PayOSService, TransactionService
from payments.models import Bill, BillDetail, Transaction
from appointments.models import Appointment, Service, ServiceOrder
from patients.models import Patient
from users.models import User
from doctors.models import Doctor, Department, ExaminationRoom, Schedule
from common.enums import DoctorType, PaymentStatus, PaymentMethod, TransactionStatus, ServiceType, Gender, AcademicDegree, UserRole, AppointmentStatus, OrderStatus, RoomType, Shift
from common.constants import DECIMAL_MAX_DIGITS, DECIMAL_DECIMAL_PLACES, SCHEDULE_DEFAULTS
import logging

class BillServiceTest(TestCase):
    @classmethod
    def setUpTestData(cls):
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
            status=AppointmentStatus.PENDING.value,
        )
        cls.bill = Bill.objects.create(
            appointment=cls.appointment,
            patient=cls.patient,
            total_cost=Decimal('200.00'),
            insurance_discount=Decimal('50.00'),
            amount=Decimal('150.00'),
            status=PaymentStatus.UNPAID.value
        )
        cls.appointment2 = Appointment.objects.create(
            doctor=cls.doctor,
            patient=cls.patient,
            schedule=cls.schedule,
            symptoms="Headache",
            note="Follow-up",
            slot_start=time(9, 0),
            slot_end=time(9, 30),
            status=AppointmentStatus.PENDING.value,
        )
        cls.bill2 = Bill.objects.create(
            appointment=cls.appointment2,
            patient=cls.patient,
            total_cost=Decimal('300.00'),
            insurance_discount=Decimal('0.00'),
            amount=Decimal('300.00'),
            status=PaymentStatus.PAID.value
        )

    def test_get_all_bills(self):
        service = BillService()
        bills = service.get_all_bills(1, 10, 'created_at', 'desc')
        self.assertEqual(len(bills), 2)
        bills = service.get_all_bills(1, 10, 'total_cost', 'asc')
        self.assertEqual(bills[0].id, self.bill.id)
        bills = service.get_all_bills(1, 10, 'invalid', 'desc')
        self.assertEqual(len(bills), 2)
        bills = service.get_all_bills(2, 1, 'created_at', 'desc')
        self.assertEqual(len(bills), 1)
        with self.assertRaises(ValueError):
            service.get_all_bills(0, 10)
        bills = service.get_all_bills(1, 200, 'created_at', 'desc')
        self.assertEqual(len(bills), 2)

    def test_create_bill_with_details(self):
        data = {
            'appointment_id': self.appointment.id,
            'patient_id': self.patient.id,
            'insurance_discount': Decimal('0.00'),
            'status': PaymentStatus.UNPAID.value,
            'bill_details': [
                {'item_type': ServiceType.CONSULTATION.value, 'quantity': 2, 'unit_price': Decimal('50.00'), 'insurance_discount': Decimal('5.00')}
            ]
        }
        service = BillService()
        bill = service.create_bill(data)
        self.assertEqual(bill.total_cost, Decimal('100.00'))
        self.assertEqual(bill.insurance_discount, Decimal('5.00'))
        self.assertEqual(bill.amount, Decimal('95.00'))
        self.assertEqual(bill.details.count(), 1)

    def test_create_bill_without_details(self):
        data = {
            'appointment_id': self.appointment.id,
            'patient_id': self.patient.id,
            'insurance_discount': Decimal('0.00'),
            'status': PaymentStatus.UNPAID.value,
        }
        service = BillService()
        bill = service.create_bill(data)
        self.assertEqual(bill.total_cost, Decimal('100.00'))  # doctor.price
        self.assertEqual(bill.insurance_discount, Decimal('0.00'))
        self.assertEqual(bill.amount, Decimal('100.00'))

    def test_update_bill(self):
        service = BillService()
        updated_bill = service.update_bill(self.bill.id, {'status': PaymentStatus.PAID.value})
        self.assertEqual(updated_bill.status, PaymentStatus.PAID.value)
        with self.assertRaises(Http404):
            service.update_bill(999, {'status': PaymentStatus.PAID.value})

    def test_get_bill_by_id(self):
        service = BillService()
        bill = service.get_bill_by_id(self.bill.id)
        self.assertEqual(bill.id, self.bill.id)
        with self.assertRaises(Http404):
            service.get_bill_by_id(999)

    def test_delete_bill(self):
        service = BillService()
        service.delete_bill(self.bill.id)
        self.assertFalse(Bill.objects.filter(id=self.bill.id).exists())
        with self.assertRaises(Http404):
            service.delete_bill(999)

    def test_create_bill_detail(self):
        data = [
            {'item_type': ServiceType.IMAGING.value, 'quantity': 1, 'unit_price': Decimal('200.00'), 'insurance_discount': Decimal('20.00')}
        ]
        service = BillService()
        bill = service.create_bill_detail(self.bill.id, data)
        self.assertEqual(bill.total_cost, Decimal('200.00'))
        self.assertEqual(bill.insurance_discount, Decimal('20.00'))
        self.assertEqual(bill.amount, Decimal('180.00'))
        self.assertEqual(bill.details.count(), 1)
        with self.assertRaises(Http404):
            service.create_bill_detail(999, data)

    def test_get_detail_by_bill(self):
        # First add detail
        BillDetail.objects.create(
            bill=self.bill,
            item_type=ServiceType.CONSULTATION.value,
            quantity=1,
            unit_price=Decimal('100.00'),
            insurance_discount=Decimal('0.00'),
            total_price=Decimal('100.00')
        )
        service = BillService()
        details = service.get_detail_by_bill(self.bill.id)
        self.assertEqual(len(details), 1)
        # Create bill with no details
        bill_no_detail = Bill.objects.create(
            appointment=self.appointment,
            patient=self.patient,
            total_cost=Decimal('0.00'),
            insurance_discount=Decimal('0.00'),
            amount=Decimal('0.00'),
            status=PaymentStatus.UNPAID.value
        )
        with self.assertRaises(ValueError):
            service.get_detail_by_bill(bill_no_detail.id)
        with self.assertRaises(Http404):
            service.get_detail_by_bill(999)

    def test_get_bills_by_patient_id(self):
        service = BillService()
        bills = service.get_bills_by_patient_id(self.patient.id)
        self.assertEqual(len(bills), 2)
        bills = service.get_bills_by_patient_id(999)
        self.assertEqual(len(bills), 0)

class PayOSServiceTest(TestCase):
    @classmethod
    def setUpTestData(cls):
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
        cls.department = Department.objects.create(
            department_name="Cardiology"
        )
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
            status=AppointmentStatus.PENDING.value
        )
        cls.bill = Bill.objects.create(
            appointment=cls.appointment,
            patient=cls.patient,
            total_cost=Decimal('200.00'),
            insurance_discount=Decimal('50.00'),
            amount=Decimal('150.00'),
            status=PaymentStatus.UNPAID.value
        )

    @patch('payments.services.payos.PayOS')
    def test_create_payment_link(self, mock_payos_class):
        mock_payos = mock_payos_class.return_value
        mock_response = MagicMock()
        mock_response.checkoutUrl = 'http://test.url'
        mock_payos.createPaymentLink.return_value = mock_response
        service = PayOSService()
        url = service.create_payment_link(self.bill.id)
        self.assertEqual(url, 'http://test.url')
        mock_payos.createPaymentLink.assert_called_once()
        # Test paid bill
        self.bill.status = PaymentStatus.PAID.value
        self.bill.save()
        with self.assertRaises(ValueError):
            service.create_payment_link(self.bill.id)

    @patch('payments.services.payos.PayOS')
    def test_cancel_payment(self, mock_payos_class):
        mock_payos = mock_payos_class.return_value
        mock_response = MagicMock(orderCode=123, status='CANCELLED')
        mock_payos.cancelPaymentLink.return_value = mock_response
        service = PayOSService()
        result = service.cancel_payment(123)
        self.assertEqual(result['status'], 'CANCELLED')

class TransactionServiceTest(TestCase):
    @classmethod
    def setUpTestData(cls):
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
            type="EXAMINATION",
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
            status=AppointmentStatus.PENDING.value,
        )
        cls.bill = Bill.objects.create(
            appointment=cls.appointment,
            patient=cls.patient,
            total_cost=Decimal('200.00'),
            insurance_discount=Decimal('50.00'),
            amount=Decimal('150.00'),
            status=PaymentStatus.BOOKING_PAID.value
        )
        cls.service = Service.objects.create(
            service_name="Test Service",
            service_type=ServiceType.CONSULTATION.value,
            price=Decimal('50.00')
        )
        cls.service_order = ServiceOrder.objects.create(
            appointment=cls.appointment,
            room=cls.room,
            service=cls.service,
            status=OrderStatus.ORDERED.value
        )
        cls.transaction = Transaction.objects.create(
            bill=cls.bill,
            amount=Decimal('50.00'),
            payment_method=PaymentMethod.ONLINE_BANKING.value,
            transaction_date=timezone.now(),
            status=TransactionStatus.PENDING.value
        )

    @patch('payments.services.PayOSService')
    def test_create_payment_link(self, mock_payos_service_class):
        mock_payos_service = mock_payos_service_class.return_value
        mock_payos_service.create_payment_link.return_value = 'http://test.url'
        service = TransactionService()
        url = service.create_payment_link(self.bill.id)
        self.assertEqual(url, 'http://test.url')
        mock_payos_service.create_payment_link.assert_called_once_with(self.bill.id)

    def test_process_cash_payment(self):
        service = TransactionService()
        # Set to BOOKING_PAID
        self.bill.status = PaymentStatus.BOOKING_PAID.value
        self.bill.save()
        updated_bill = service.process_cash_payment(self.bill.id)
        self.assertEqual(updated_bill.status, PaymentStatus.PAID.value)
        transactions = Transaction.objects.filter(bill=self.bill, payment_method=PaymentMethod.CASH.value)
        self.assertTrue(transactions.exists())
        self.assertEqual(transactions.first().amount, Decimal('50.00'))  # service_fee
        # Test UNPAID
        self.bill.status = PaymentStatus.UNPAID.value
        self.bill.save()
        with self.assertRaises(ValueError):
            service.process_cash_payment(self.bill.id)
        # Test PAID
        self.bill.status = PaymentStatus.PAID.value
        self.bill.save()
        with self.assertRaises(ValueError):
            service.process_cash_payment(self.bill.id)
        # Test no service_fee
        ServiceOrder.objects.filter(appointment=self.appointment).delete()
        self.bill.status = PaymentStatus.BOOKING_PAID.value
        self.bill.save()
        with self.assertRaises(ValueError):
            service.process_cash_payment(self.bill.id)
        # Test invalid status
        self.bill.status = 'INVALID'
        self.bill.save()
        with self.assertRaises(ValueError):
            service.process_cash_payment(self.bill.id)

    def test_handle_payment_success(self):
        service = TransactionService()
        BillDetail.objects.filter(bill=self.bill).delete()  # Ensure no details
        self.bill.amount = Decimal('100.00')
        self.bill.save()
        self.transaction.amount = Decimal('100.00')
        self.transaction.status = TransactionStatus.PENDING.value
        self.transaction.save()
        service.handle_payment_success(self.bill.id * 1000)
        self.bill.refresh_from_db()
        self.assertEqual(self.bill.status, PaymentStatus.BOOKING_PAID.value)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, AppointmentStatus.CONFIRMED.value)
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.status, TransactionStatus.SUCCESS.value)

        BillDetail.objects.create(
            bill=self.bill,
            item_type=ServiceType.CONSULTATION.value,
            quantity=1,
            unit_price=Decimal('150.00'),
            insurance_discount=Decimal('0.00'),
            total_price=Decimal('150.00')
        )
        self.bill.amount = Decimal('150.00')
        self.bill.save()
        self.transaction.amount = Decimal('150.00')
        self.transaction.status = TransactionStatus.PENDING.value
        self.transaction.save()
        service.handle_payment_success(self.bill.id * 1000)
        self.bill.refresh_from_db()
        self.assertEqual(self.bill.status, PaymentStatus.PAID.value)
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.status, TransactionStatus.SUCCESS.value)

        self.transaction.status = TransactionStatus.SUCCESS.value
        self.transaction.save()
        with patch('payments.services.logger.warning') as mock_logger:
            service.handle_payment_success(self.bill.id * 1000)
            mock_logger.assert_called()

    def test_handle_payment_cancel(self):
        service = TransactionService()
        self.transaction.status = TransactionStatus.PENDING.value
        self.transaction.save()
        service.handle_payment_cancel(self.bill.id)
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.status, TransactionStatus.FAILED.value)
        # Not pending
        self.transaction.status = TransactionStatus.SUCCESS.value
        self.transaction.save()
        service.handle_payment_cancel(self.bill.id)
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.status, TransactionStatus.SUCCESS.value)  # no change

    def test_get_transactions_by_bill_id(self):
        service = TransactionService()
        transactions = service.get_transactions_by_bill_id(self.bill.id, 'transaction_date', 'desc')
        self.assertIsInstance(transactions, list)
        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0]['id'], self.transaction.id)
        # Sort asc
        transactions = service.get_transactions_by_bill_id(self.bill.id, 'transaction_date', 'asc')
        self.assertEqual(len(transactions), 1)
        # Invalid sort, default
        transactions = service.get_transactions_by_bill_id(self.bill.id, 'invalid', 'desc')
        self.assertEqual(len(transactions), 1)
        # No bill
        with self.assertRaises(Http404):
            service.get_transactions_by_bill_id(999)
