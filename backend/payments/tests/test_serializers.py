from django.test import TestCase
from django.utils import timezone
from datetime import date, time
from decimal import Decimal
from payments.models import Bill, BillDetail, Transaction
from payments.serializers import (
    TransactionDTOSerializer,
    NewBillDetailRequestSerializer,
    NewBillRequestSerializer,
    UpdateBillRequestSerializer,
    BillDetailResponseSerializer,
    BillResponseSerializer,
    BillSerializer
)
from appointments.models import Appointment, Service, ServiceOrder, Schedule
from patients.models import Patient
from users.models import User
from doctors.models import Doctor, Department, ExaminationRoom
from common.enums import (
    AppointmentStatus, OrderStatus, PaymentStatus, PaymentMethod, TransactionStatus, ServiceType,
    Gender, AcademicDegree, UserRole, RoomType, Shift, DoctorType
)
from common.constants import DECIMAL_MAX_DIGITS, DECIMAL_DECIMAL_PLACES, SCHEDULE_DEFAULTS

class SerializerTestCase(TestCase):
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
            status=AppointmentStatus.CONFIRMED.value,
        )
        cls.service = Service.objects.create(
            service_name="Blood Test",
            service_type=ServiceType.TEST.value,
            price=Decimal('75.00')
        )
        cls.service_order = ServiceOrder.objects.create(
            appointment=cls.appointment,
            service=cls.service,
            room=cls.room,
            status=OrderStatus.ORDERED.value,
            number=1,
            order_time=timezone.now()
        )
        cls.bill = Bill.objects.create(
            appointment=cls.appointment,
            patient=cls.patient,
            total_cost=Decimal('200.00'),
            insurance_discount=Decimal('50.00'),
            amount=Decimal('150.00'),
            status=PaymentStatus.UNPAID.value
        )
        cls.bill_detail1 = BillDetail.objects.create(
            bill=cls.bill,
            item_type=ServiceType.CONSULTATION.value,
            quantity=1,
            unit_price=Decimal('100.00'),
            insurance_discount=Decimal('20.00'),
            total_price=Decimal('100.00')
        )
        cls.bill_detail2 = BillDetail.objects.create(
            bill=cls.bill,
            item_type=ServiceType.IMAGING.value,
            quantity=1,
            unit_price=Decimal('150.00'),
            insurance_discount=Decimal('30.00'),
            total_price=Decimal('150.00')
        )
        cls.transaction1 = Transaction.objects.create(
            bill=cls.bill,
            amount=Decimal('100.00'),
            payment_method=PaymentMethod.CASH.value,
            transaction_date=timezone.now(),
            status=TransactionStatus.SUCCESS.value
        )
        cls.transaction2 = Transaction.objects.create(
            bill=cls.bill,
            amount=Decimal('50.00'),
            payment_method=PaymentMethod.ONLINE_BANKING.value,
            transaction_date=timezone.now(),
            status=TransactionStatus.PENDING.value
        )

class TransactionDTOSerializerTest(SerializerTestCase):
    def test_transaction_dto_serializer(self):
        serializer = TransactionDTOSerializer(self.transaction1)
        data = serializer.data
        self.assertEqual(data['id'], self.transaction1.id)
        self.assertEqual(data['bill_id'], self.bill.id)
        self.assertEqual(Decimal(data['amount']), self.transaction1.amount)
        self.assertEqual(data['payment_method'], self.transaction1.payment_method)
        self.assertEqual(data['status'], self.transaction1.status)
        # Check timestamps if needed

class NewBillDetailRequestSerializerTest(SerializerTestCase):
    def test_valid_data(self):
        data = {
            'item_type': ServiceType.CONSULTATION.value,
            'quantity': 2,
            'unit_price': '100.00',
            'insurance_discount': '20.00'
        }
        serializer = NewBillDetailRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        validated = serializer.validated_data
        self.assertEqual(validated['item_type'], ServiceType.CONSULTATION.value)
        self.assertEqual(validated['quantity'], 2)
        self.assertEqual(validated['unit_price'], Decimal('100.00'))
        self.assertEqual(validated['insurance_discount'], Decimal('20.00'))

    def test_invalid_quantity(self):
        data = {
            'item_type': ServiceType.CONSULTATION.value,
            'quantity': 0,
            'unit_price': '100.00'
        }
        serializer = NewBillDetailRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('quantity', serializer.errors)

    def test_invalid_item_type(self):
        data = {
            'item_type': 'INVALID',
            'quantity': 1,
            'unit_price': '100.00'
        }
        serializer = NewBillDetailRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('item_type', serializer.errors)

class NewBillRequestSerializerTest(SerializerTestCase):
    def test_valid_data(self):
        data = {
            'appointment_id': self.appointment.id,
            'patient_id': self.patient.id,
            'total_cost': '200.00',
            'insurance_discount': '50.00',
            'amount': '150.00',
            'status': PaymentStatus.UNPAID.value,
            'bill_details': [
                {
                    'item_type': ServiceType.CONSULTATION.value,
                    'quantity': 1,
                    'unit_price': '100.00',
                    'insurance_discount': '20.00'
                }
            ]
        }
        serializer = NewBillRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        validated = serializer.validated_data
        self.assertEqual(validated['appointment_id'], self.appointment.id)
        self.assertEqual(validated['patient_id'], self.patient.id)
        self.assertEqual(validated['total_cost'], Decimal('200.00'))
        self.assertEqual(validated['insurance_discount'], Decimal('50.00'))
        self.assertEqual(validated['amount'], Decimal('150.00'))
        self.assertEqual(validated['status'], PaymentStatus.UNPAID.value)
        self.assertEqual(len(validated['bill_details']), 1)

    def test_invalid_status(self):
        data = {
            'appointment_id': self.appointment.id,
            'patient_id': self.patient.id,
            'total_cost': '200.00',
            'amount': '150.00',
            'status': 'INVALID'
        }
        serializer = NewBillRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('status', serializer.errors)

class UpdateBillRequestSerializerTest(SerializerTestCase):
    def test_valid_data(self):
        data = {
            'appointment_id': self.appointment.id,
            'status': PaymentStatus.PAID.value
        }
        serializer = UpdateBillRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        validated = serializer.validated_data
        self.assertEqual(validated['appointment_id'], self.appointment.id)
        self.assertEqual(validated['status'], PaymentStatus.PAID.value)

    def test_partial_data(self):
        data = {
            'status': PaymentStatus.PAID.value
        }
        serializer = UpdateBillRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['status'], PaymentStatus.PAID.value)
        self.assertNotIn('appointment_id', serializer.validated_data)

class BillDetailResponseSerializerTest(SerializerTestCase):
    def test_bill_detail_response_serializer(self):
        serializer = BillDetailResponseSerializer(self.bill_detail1)
        data = serializer.data
        self.assertEqual(data['id'], self.bill_detail1.id)
        self.assertEqual(data['bill_id'], self.bill.id)
        self.assertEqual(data['item_type'], self.bill_detail1.item_type)
        self.assertEqual(data['quantity'], self.bill_detail1.quantity)
        self.assertEqual(Decimal(data['unit_price']), self.bill_detail1.unit_price)
        self.assertEqual(Decimal(data['total_price']), self.bill_detail1.total_price)
        self.assertEqual(Decimal(data['insurance_discount']), self.bill_detail1.insurance_discount)
