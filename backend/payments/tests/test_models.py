from django.test import TestCase
from django.utils import timezone
from datetime import date, time
from decimal import Decimal
from payments.models import Bill, BillDetail, Transaction
from appointments.models import Appointment
from patients.models import Patient
from users.models import User
from doctors.models import Doctor, Department, ExaminationRoom, Schedule
from common.enums import PaymentStatus, PaymentMethod, RoomType, Shift, TransactionStatus, ServiceType, Gender, AcademicDegree, UserRole
from common.constants import DECIMAL_MAX_DIGITS, DECIMAL_DECIMAL_PLACES, ENUM_LENGTH, PAYMENT_LENGTH, SCHEDULE_DEFAULTS
from django.db import IntegrityError

class BillModelTest(TestCase):
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
            status="CONFIRMED",
        )
        cls.bill = Bill.objects.create(
            appointment=cls.appointment,
            patient=cls.patient,
            total_cost=Decimal('200.00'),
            insurance_discount=Decimal('50.00'),
            amount=Decimal('150.00'),
            status=PaymentStatus.UNPAID.value
        )

    def test_create_bill(self):
        bill = Bill.objects.create(
            appointment=self.appointment,
            patient=self.patient,
            total_cost=Decimal('300.00'),
            insurance_discount=Decimal('75.00'),
            amount=Decimal('225.00'),
            status=PaymentStatus.UNPAID.value
        )
        self.assertEqual(bill.appointment, self.appointment)
        self.assertEqual(bill.patient, self.patient)
        self.assertEqual(bill.total_cost, Decimal('300.00'))
        self.assertEqual(bill.insurance_discount, Decimal('75.00'))
        self.assertEqual(bill.amount, Decimal('225.00'))
        self.assertEqual(bill.status, PaymentStatus.UNPAID.value)
        self.assertIsNotNone(bill.created_at)
        self.assertIsNotNone(bill.updated_at)

    def test_str_method(self):
        self.assertEqual(str(self.bill), f"Bill {self.bill.pk}")

    def test_required_fields(self):
        with self.assertRaises(IntegrityError):
            Bill.objects.create(
                total_cost=Decimal('200.00'),
                amount=Decimal('150.00'),
                status=PaymentStatus.UNPAID.value
            )

    def test_status_choices(self):
        self.assertIn(self.bill.status, [status.value for status in PaymentStatus])

    def test_decimal_field_validation(self):
        self.assertEqual(self.bill._meta.get_field('total_cost').max_digits, DECIMAL_MAX_DIGITS)
        self.assertEqual(self.bill._meta.get_field('total_cost').decimal_places, DECIMAL_DECIMAL_PLACES)
        self.assertEqual(self.bill._meta.get_field('insurance_discount').max_digits, DECIMAL_MAX_DIGITS)
        self.assertEqual(self.bill._meta.get_field('insurance_discount').decimal_places, DECIMAL_DECIMAL_PLACES)
        self.assertEqual(self.bill._meta.get_field('amount').max_digits, DECIMAL_MAX_DIGITS)
        self.assertEqual(self.bill._meta.get_field('amount').decimal_places, DECIMAL_DECIMAL_PLACES)

class BillDetailModelTest(TestCase):
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
            status="CONFIRMED",
        )
        cls.bill = Bill.objects.create(
            appointment=cls.appointment,
            patient=cls.patient,
            total_cost=Decimal('200.00'),
            insurance_discount=Decimal('50.00'),
            amount=Decimal('150.00'),
            status=PaymentStatus.UNPAID.value
        )
        cls.bill_detail = BillDetail.objects.create(
            bill=cls.bill,
            item_type=ServiceType.CONSULTATION.value,
            quantity=2,
            unit_price=Decimal('100.00'),
            insurance_discount=Decimal('20.00'),
            total_price=Decimal('200.00')
        )

    def test_create_bill_detail(self):
        bill_detail = BillDetail.objects.create(
            bill=self.bill,
            item_type=ServiceType.IMAGING.value,
            quantity=3,
            unit_price=Decimal('150.00'),
            insurance_discount=Decimal('30.00'),
            total_price=Decimal('450.00')
        )
        self.assertEqual(bill_detail.bill, self.bill)
        self.assertEqual(bill_detail.item_type, ServiceType.IMAGING.value)
        self.assertEqual(bill_detail.quantity, 3)
        self.assertEqual(bill_detail.unit_price, Decimal('150.00'))
        self.assertEqual(bill_detail.insurance_discount, Decimal('30.00'))
        self.assertEqual(bill_detail.total_price, Decimal('450.00'))
        self.assertIsNotNone(bill_detail.created_at)
        self.assertIsNotNone(bill_detail.updated_at)

    def test_str_method(self):
        self.assertEqual(str(self.bill_detail), f"BillDetail {self.bill_detail.pk}")

    def test_required_fields(self):
        with self.assertRaises(IntegrityError):
            BillDetail.objects.create(
                quantity=2,
                unit_price=Decimal('100.00'),
                total_price=Decimal('200.00')
            )

    def test_item_type_length(self):
        self.assertTrue(len(self.bill_detail.item_type) <= PAYMENT_LENGTH["ITEM_TYPE"])

    def test_decimal_field_validation(self):
        self.assertEqual(self.bill_detail._meta.get_field('unit_price').max_digits, DECIMAL_MAX_DIGITS)
        self.assertEqual(self.bill_detail._meta.get_field('unit_price').decimal_places, DECIMAL_DECIMAL_PLACES)
        self.assertEqual(self.bill_detail._meta.get_field('insurance_discount').max_digits, DECIMAL_MAX_DIGITS)
        self.assertEqual(self.bill_detail._meta.get_field('insurance_discount').decimal_places, DECIMAL_DECIMAL_PLACES)
        self.assertEqual(self.bill_detail._meta.get_field('total_price').max_digits, DECIMAL_MAX_DIGITS)
        self.assertEqual(self.bill_detail._meta.get_field('total_price').decimal_places, DECIMAL_DECIMAL_PLACES)

class TransactionModelTest(TestCase):
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
            status="CONFIRMED",
        )
        cls.bill = Bill.objects.create(
            appointment=cls.appointment,
            patient=cls.patient,
            total_cost=Decimal('200.00'),
            insurance_discount=Decimal('50.00'),
            amount=Decimal('150.00'),
            status=PaymentStatus.UNPAID.value
        )
        cls.transaction = Transaction.objects.create(
            bill=cls.bill,
            amount=Decimal('150.00'),
            payment_method=PaymentMethod.CASH.value,
            transaction_date=timezone.now(),
            status=TransactionStatus.SUCCESS.value
        )

    def test_create_transaction(self):
        transaction = Transaction.objects.create(
            bill=self.bill,
            amount=Decimal('200.00'),
            payment_method=PaymentMethod.ONLINE_BANKING.value,
            transaction_date=timezone.now(),
            status=TransactionStatus.PENDING.value
        )
        self.assertEqual(transaction.bill, self.bill)
        self.assertEqual(transaction.amount, Decimal('200.00'))
        self.assertEqual(transaction.payment_method, PaymentMethod.ONLINE_BANKING.value)
        self.assertEqual(transaction.status, TransactionStatus.PENDING.value)
        self.assertIsNotNone(transaction.transaction_date)
        self.assertIsNotNone(transaction.created_at)
        self.assertIsNotNone(transaction.updated_at)

    def test_str_method(self):
        self.assertEqual(str(self.transaction), f"Transaction {self.transaction.pk}")

    def test_required_fields(self):
        with self.assertRaises(IntegrityError):
            Transaction.objects.create(
                amount=Decimal('150.00'),
                payment_method=PaymentMethod.CASH.value,
                transaction_date=timezone.now(),
                status=TransactionStatus.SUCCESS.value
            )

    def test_enum_choices(self):
        self.assertIn(self.transaction.payment_method, [method.value for method in PaymentMethod])
        self.assertIn(self.transaction.status, [status.value for status in TransactionStatus])
        self.assertTrue(len(self.transaction.payment_method) <= ENUM_LENGTH["DEFAULT"])
        self.assertTrue(len(self.transaction.status) <= ENUM_LENGTH["DEFAULT"])

    def test_decimal_field_validation(self):
        self.assertEqual(self.transaction._meta.get_field('amount').max_digits, DECIMAL_MAX_DIGITS)
        self.assertEqual(self.transaction._meta.get_field('amount').decimal_places, DECIMAL_DECIMAL_PLACES)
