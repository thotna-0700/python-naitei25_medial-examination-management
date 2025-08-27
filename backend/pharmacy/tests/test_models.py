import uuid
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from datetime import date, time
from django.contrib.auth import get_user_model
from pharmacy.models import Medicine, Prescription, PrescriptionDetail
from patients.models import Patient
from appointments.models import Appointment
from doctors.models import Doctor, Department, Schedule, ExaminationRoom
from users.models import User
from common.enums import Gender, AcademicDegree, DoctorType, RoomType, Shift, UserRole
from common.constants import COMMON_LENGTH, PHARMACY_LENGTH, DECIMAL_MAX_DIGITS, DECIMAL_DECIMAL_PLACES, SCHEDULE_DEFAULTS

User = get_user_model()

class MedicineModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.medicine = Medicine.objects.create(
            medicine_name="Paracetamol",
            manufactor="PharmaCorp",
            category="Pain Relief",
            description="Used to relieve mild to moderate pain",
            usage="Take 1-2 tablets every 4-6 hours as needed",
            unit="Tablet",
            is_insurance_covered=True,
            insurance_discount_percent=50,
            insurance_discount=Decimal('5.00'),
            price=Decimal('10.00'),
            quantity=100,
            side_effects="May cause drowsiness"
        )

    def test_create_medicine(self):
        medicine = Medicine.objects.create(
            medicine_name="Ibuprofen",
            manufactor="HealthCorp",
            category="Anti-inflammatory",
            description="Relieves pain and inflammation",
            usage="Take 1 tablet every 6-8 hours",
            unit="Tablet",
            is_insurance_covered=False,
            price=Decimal('15.00'),
            quantity=50,
            side_effects="May cause stomach irritation"
        )
        self.assertEqual(medicine.medicine_name, "Ibuprofen")
        self.assertEqual(medicine.manufactor, "HealthCorp")
        self.assertEqual(medicine.category, "Anti-inflammatory")
        self.assertEqual(medicine.description, "Relieves pain and inflammation")
        self.assertEqual(medicine.usage, "Take 1 tablet every 6-8 hours")
        self.assertEqual(medicine.unit, "Tablet")
        self.assertFalse(medicine.is_insurance_covered)
        self.assertEqual(medicine.price, Decimal('15.00'))
        self.assertEqual(medicine.quantity, 50)
        self.assertEqual(medicine.side_effects, "May cause stomach irritation")
        self.assertIsNotNone(medicine.created_at)

    def test_str_method(self):
        self.assertEqual(str(self.medicine), "Paracetamol")

    def test_required_fields(self):
        medicine = Medicine.objects.create(
            medicine_name="Aspirin",
            price=Decimal('8.00'),
            quantity=75
        )
        self.assertEqual(medicine.medicine_name, "Aspirin")
        self.assertEqual(medicine.price, Decimal('8.00'))
        self.assertEqual(medicine.quantity, 75)
        self.assertIsNotNone(medicine.created_at)

    def test_insurance_discount_calculation(self):
        self.assertEqual(self.medicine.insurance_discount, Decimal('5.00'))
        self.assertEqual(self.medicine.insurance_discount_percent, 50)

class PrescriptionModelTest(TestCase):
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
            symptoms="Fever",
            slot_start=time(8, 0),
            slot_end=time(8, 30),
            status="CONFIRMED"
        )
        cls.prescription = Prescription.objects.create(
            appointment=cls.appointment,
            patient=cls.patient,
            follow_up_date=date(2025, 9, 2),
            is_follow_up=True,
            diagnosis="Viral infection",
            systolic_blood_pressure=120,
            diastolic_blood_pressure=80,
            heart_rate=70,
            blood_sugar=90,
            note="Follow-up in one week"
        )

    def test_create_prescription(self):
    # Create a new appointment for this test
        new_appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            schedule=self.schedule,
            symptoms="Headache",
            slot_start=time(9, 0),  # Different time slot
            slot_end=time(9, 30),
            status="CONFIRMED"
        )
    
        prescription = Prescription.objects.create(
            appointment=new_appointment,  # Use the new appointment
            patient=self.patient,
            follow_up_date=date(2025, 9, 3),
            is_follow_up=False,
            diagnosis="Bacterial infection",
            systolic_blood_pressure=130,
            diastolic_blood_pressure=85,
            heart_rate=75,
            blood_sugar=95,
            note="Antibiotics prescribed"
        )
        self.assertEqual(prescription.appointment, new_appointment)
        self.assertEqual(prescription.patient, self.patient)
        self.assertEqual(prescription.follow_up_date, date(2025, 9, 3))
        self.assertFalse(prescription.is_follow_up)
        self.assertEqual(prescription.diagnosis, "Bacterial infection")
        self.assertEqual(prescription.systolic_blood_pressure, 130)
        self.assertEqual(prescription.diastolic_blood_pressure, 85)
        self.assertEqual(prescription.heart_rate, 75)
        self.assertEqual(prescription.blood_sugar, 95)
        self.assertEqual(prescription.note, "Antibiotics prescribed")
        self.assertFalse(prescription.is_deleted)
        self.assertIsNotNone(prescription.created_at)

    def test_str_method(self):
        self.assertEqual(str(self.prescription), f"Prescription {self.prescription.id} for Patient {self.prescription.patient.id}")

    def test_required_fields(self):
        with self.assertRaises(Exception):
            Prescription.objects.create(
                diagnosis="Test diagnosis",
                note="Test note"
            )

class PrescriptionDetailModelTest(TestCase):
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
            symptoms="Fever",
            slot_start=time(8, 0),
            slot_end=time(8, 30),
            status="CONFIRMED"
        )
        cls.medicine = Medicine.objects.create(
            medicine_name="Paracetamol",
            manufactor="PharmaCorp",
            category="Pain Relief",
            usage="Take 1-2 tablets every 4-6 hours",
            unit="Tablet",
            is_insurance_covered=True,
            insurance_discount_percent=50,
            price=Decimal('10.00'),
            quantity=100
        )
        cls.prescription = Prescription.objects.create(
            appointment=cls.appointment,
            patient=cls.patient,
            diagnosis="Viral infection"
        )
        cls.prescription_detail = PrescriptionDetail.objects.create(
            prescription=cls.prescription,
            medicine=cls.medicine,
            dosage="500mg",
            frequency="Every 6 hours",
            duration="5 days",
            quantity=20,
            prescription_notes="Take after meals"
        )

    def test_create_prescription_detail(self):
        prescription_detail = PrescriptionDetail.objects.create(
            prescription=self.prescription,
            medicine=self.medicine,
            dosage="1000mg",
            frequency="Every 8 hours",
            duration="7 days",
            quantity=21,
            prescription_notes="Take with water"
        )
        self.assertEqual(prescription_detail.prescription, self.prescription)
        self.assertEqual(prescription_detail.medicine, self.medicine)
        self.assertEqual(prescription_detail.dosage, "1000mg")
        self.assertEqual(prescription_detail.frequency, "Every 8 hours")
        self.assertEqual(prescription_detail.duration, "7 days")
        self.assertEqual(prescription_detail.quantity, 21)
        self.assertEqual(prescription_detail.prescription_notes, "Take with water")
        self.assertIsNotNone(prescription_detail.created_at)

    def test_str_method(self):
        self.assertEqual(str(self.prescription_detail), f"Detail {self.prescription_detail.id} for {self.medicine.medicine_name}")

    def test_required_fields(self):
        with self.assertRaises(Exception):
            PrescriptionDetail.objects.create(
                dosage="500mg",
                frequency="Every 6 hours",
                duration="5 days",
                quantity=10
            )
