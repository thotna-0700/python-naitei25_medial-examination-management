import uuid
from decimal import Decimal
from datetime import date, time, datetime
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import serializers
from pharmacy.models import Medicine, Prescription, PrescriptionDetail
from pharmacy.serializers import (
    MedicineSerializer, PrescriptionSerializer, PrescriptionDetailSerializer,
    PrescriptionDetailInfoSerializer, PrescriptionPdfDtoSerializer,
    PrescriptionDetailRequestSerializer, CreatePrescriptionRequestSerializer,
    UpdatePrescriptionRequestSerializer, AddMedicineToPrescriptionRequestSerializer,
    UpdatePrescriptionDetailRequestSerializer, NewMedicineRequestSerializer,
    UpdateMedicineRequestSerializer
)
from patients.models import Patient
from appointments.models import Appointment
from doctors.models import Doctor, Department, Schedule, ExaminationRoom
from users.models import User
from common.enums import Gender, AcademicDegree, DoctorType, RoomType, Shift, UserRole
from common.constants import (
    COMMON_LENGTH, PHARMACY_LENGTH, DECIMAL_MAX_DIGITS, DECIMAL_DECIMAL_PLACES,
    SCHEDULE_DEFAULTS, USER_LENGTH, PATIENT_LENGTH, DOCTOR_LENGTH, MIN_VALUE
)

User = get_user_model()

class MedicineSerializerTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.medicine = Medicine.objects.create(
            medicine_name="Paracetamol",
            manufactor="PharmaCorp",
            category="Pain Relief",
            description="Relieves mild pain",
            usage="Take 1-2 tablets every 4-6 hours",
            unit="Tablet",
            is_insurance_covered=True,
            insurance_discount_percent=50,
            insurance_discount=Decimal('5.00'),
            price=Decimal('10.00'),
            quantity=100,
            side_effects="May cause drowsiness"
        )

    def test_serialize_medicine(self):
        serializer = MedicineSerializer(self.medicine)
        expected_data = {
            'id': self.medicine.id,
            'medicine_name': "Paracetamol",
            'manufactor': "PharmaCorp",
            'category': "Pain Relief",
            'description': "Relieves mild pain",
            'usage': "Take 1-2 tablets every 4-6 hours",
            'unit': "Tablet",
            'is_insurance_covered': True,
            'insurance_discount_percent': 50.0,
            'insurance_discount': '5.00',
            'side_effects': "May cause drowsiness",
            'price': '10.00',
            'quantity': 100,
            'created_at': self.medicine.created_at.isoformat().replace("+00:00", "Z"),
        }
        self.assertEqual(serializer.data, expected_data)

    def test_deserialize_valid_data(self):
        data = {
            'medicine_name': "Ibuprofen",
            'manufactor': "HealthCorp",
            'category': "Anti-inflammatory",
            'description': "Relieves inflammation",
            'usage': "Take 1 tablet every 6-8 hours",
            'unit': "Tablet",
            'is_insurance_covered': False,
            'insurance_discount_percent': None,
            'insurance_discount': None,
            'side_effects': "May cause stomach irritation",
            'price': "15.00",
            'quantity': 50
        }
        serializer = MedicineSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        medicine = serializer.save()
        self.assertEqual(medicine.medicine_name, "Ibuprofen")
        self.assertEqual(medicine.price, Decimal('15.00'))
        self.assertEqual(medicine.quantity, 50)

    def test_deserialize_invalid_data(self):
        data = {
            'medicine_name': "A" * (COMMON_LENGTH["NAME"] + 1),  # too long
            'category': "Anti-inflammatory",
            'usage': "Take 1 tablet",
            'unit': "Tablet",
            'price': "10.00",
            'quantity': 1
        }
        serializer = MedicineSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('medicine_name', serializer.errors)

class PrescriptionSerializerTest(TestCase):
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
            floor=1
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
            usage="Take 1-2 tablets every 4-6 hours",
            unit="Tablet",
            price=Decimal('10.00'),
            quantity=100
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
        cls.prescription_detail = PrescriptionDetail.objects.create(
            prescription=cls.prescription,
            medicine=cls.medicine,
            dosage="500mg",
            frequency="Every 6 hours",
            duration="5 days",
            quantity=20,
            prescription_notes="Take after meals"
        )

    def test_serialize_prescription(self):
        serializer = PrescriptionSerializer(self.prescription)
        expected_data = {
            'id': self.prescription.id,
            'patient': self.patient.id,
            'appointment': self.appointment.id,
            'follow_up_date': "2025-09-02",
            'is_follow_up': True,
            'diagnosis': "Viral infection",
            'systolic_blood_pressure': 120,
            'diastolic_blood_pressure': 80,
            'heart_rate': 70,
            'blood_sugar': 90,
            'note': "Follow-up in one week",
            'prescription_details': [
                {
                    'id': self.prescription_detail.id,
                    'prescription': self.prescription.id,
                    'medicine': {
                        'medicine_id': self.medicine.id,
                        'medicine_name': "Paracetamol",
                        'unit': "Tablet",
                        'price': 10.00
                    },
                    'dosage': "500mg",
                    'frequency': "Every 6 hours",
                    'duration': "5 days",
                    'prescription_notes': "Take after meals",
                    'quantity': 20,
                    'created_at': self.prescription_detail.created_at.isoformat().replace("+00:00", "Z")
                }
            ],
            'created_at': self.prescription.created_at.isoformat().replace("+00:00", "Z")
        }
        self.assertEqual(serializer.data, expected_data)

    def test_deserialize_valid_data(self):
        new_appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            schedule=self.schedule,
            symptoms="Cough",
            slot_start=time(8, 30),
            slot_end=time(9, 0),
            status="CONFIRMED"
        )
        data = {
            'appointment': new_appointment.id,
            'patient': self.patient.id,
            'follow_up_date': "2025-09-03",
            'is_follow_up': False,
            'diagnosis': "Bacterial infection",
            'systolic_blood_pressure': 130,
            'diastolic_blood_pressure': 85,
            'heart_rate': 75,
            'blood_sugar': 95,
            'note': "Antibiotics prescribed"
        }
        serializer = PrescriptionSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        prescription = serializer.save()
        self.assertEqual(prescription.diagnosis, "Bacterial infection")
        self.assertEqual(prescription.systolic_blood_pressure, 130)

class PrescriptionDetailSerializerTest(TestCase):
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
            floor=1
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
            usage="Take 1-2 tablets every 4-6 hours",
            unit="Tablet",
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

    def test_serialize_prescription_detail(self):
        serializer = PrescriptionDetailSerializer(self.prescription_detail)
        expected_data = {
            'id': self.prescription_detail.id,
            'prescription': self.prescription.id,
            'medicine': {
                'medicine_id': self.medicine.id,
                'medicine_name': "Paracetamol",
                'unit': "Tablet",
                'price': 10.00
            },
            'dosage': "500mg",
            'frequency': "Every 6 hours",
            'duration': "5 days",
            'prescription_notes': "Take after meals",
            'quantity': 20,
            'created_at': self.prescription_detail.created_at.isoformat().replace("+00:00", "Z")
        }
        self.assertEqual(serializer.data, expected_data)

    def test_get_medicine(self):
        serializer = PrescriptionDetailSerializer(self.prescription_detail)
        medicine_data = serializer.data['medicine']
        self.assertEqual(medicine_data['medicine_id'], self.medicine.id)
        self.assertEqual(medicine_data['medicine_name'], "Paracetamol")
        self.assertEqual(medicine_data['unit'], "Tablet")
        self.assertEqual(medicine_data['price'], 10.00)

class PrescriptionDetailInfoSerializerTest(TestCase):
    def test_serialize_valid_data(self):
        data = {
            'medicine_name': "Paracetamol",
            'unit': "Tablet",
            'dosage': "500mg",
            'frequency': "Every 6 hours",
            'duration': "5 days",
            'prescription_notes': "Take after meals",
            'quantity': 20
        }
        serializer = PrescriptionDetailInfoSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data, data)

    def test_invalid_data(self):
        data = {
            'medicine_name': "Paracetamol" * COMMON_LENGTH["NAME"],
            'unit': "Tablet",
            'dosage': "500mg",
            'frequency': "Every 6 hours",
            'duration': "5 days",
            'prescription_notes': "Take after meals",
            'quantity': 1
        }
        serializer = PrescriptionDetailInfoSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('medicine_name', serializer.errors)

class PrescriptionPdfDtoSerializerTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            role=UserRole.PATIENT.value,
            phone="1234567890"
        )
        cls.patient = Patient.objects.create(
            user=cls.user,
            first_name='Test',
            last_name='Patient',
            identity_number='111222333',
            insurance_number='INS123456',
            birthday=date(1990, 1, 1),
            gender=Gender.FEMALE.value,
            address="123 Main St"
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
            department=cls.department
        )
        cls.room = ExaminationRoom.objects.create(
            department=cls.department,
            type=RoomType.EXAMINATION.value,
            building="A",
            floor=1
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
            usage="Take 1-2 tablets every 4-6 hours",
            unit="Tablet",
            price=Decimal('10.00'),
            quantity=100
        )
        cls.prescription = Prescription.objects.create(
            appointment=cls.appointment,
            patient=cls.patient,
            diagnosis="Viral infection",
            created_at=timezone.make_aware(datetime(2025, 8, 26))
        )
        cls.prescription_detail = PrescriptionDetail.objects.create(
            prescription=cls.prescription,
            medicine=cls.medicine,
            dosage="500mg",
            frequency="Every 6 hours",
            duration="5 days",
            quantity=20
        )

    def test_serialize_valid_data(self):
        data = {
            'patient_id': self.patient.id,
            'patient_first_name': "Test",
            'patient_last_name': "Patient",
            'patient_gender': Gender.FEMALE.value,
            'patient_birthday': date(1990, 1, 1),
            'patient_phone': "1234567890",
            'patient_email': "testuser@example.com",
            'patient_address': "123 Main St",
            'patient_identity_number': "111222333",
            'patient_insurance_number': "INS123456",
            'doctor_first_name': "John",
            'doctor_last_name': "Doe",
            'doctor_specialization': "Cardiologist",
            'doctor_academic_degree': AcademicDegree.BS_CKI.value,
            'doctor_department': "Cardiology",
            'prescription_id': self.prescription.id,
            'prescription_date': date(2025, 8, 26),
            'diagnosis': "Viral infection",
            'systolic_blood_pressure': None,
            'diastolic_blood_pressure': None,
            'heart_rate': None,
            'blood_sugar': None,
            'note': "",
            'follow_up_date': None,
            'follow_up': False,
            'prescription_details': [
                {
                    'medicine_name': "Paracetamol",
                    'unit': "Tablet",
                    'dosage': "500mg",
                    'frequency': "Every 6 hours",
                    'duration': "5 days",
                    'prescription_notes': "",
                    'quantity': 20
                }
            ]
        }
        serializer = PrescriptionPdfDtoSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data, data)

    def test_invalid_data(self):
        data = {
            'patient_id': 1,
            'patient_first_name': "Test",
            'patient_last_name': "Patient",
            'patient_gender': Gender.FEMALE.value,
            'patient_birthday': date(1990, 1, 1),
            'patient_phone': "1234567890",
            'patient_email': "testuser@example.com",
            'patient_address': "123 Main St",
            'patient_identity_number': "111222333" * PATIENT_LENGTH["IDENTITY"],  # too long
            'patient_insurance_number': "INS123456",
            'doctor_first_name': "John",
            'doctor_last_name': "Doe",
            'doctor_specialization': "Cardiologist",
            'doctor_academic_degree': AcademicDegree.BS_CKI.value,
            'doctor_department': "Cardiology",
            'prescription_id': self.prescription.id,
            'prescription_date': date(2025, 8, 26),
            'diagnosis': "Viral infection",
            'systolic_blood_pressure': 120,
            'diastolic_blood_pressure': 80,
            'heart_rate': 70,
            'blood_sugar': 90,
            'note': "Follow-up in one week",
            'follow_up_date': date(2025, 9, 2),
            'follow_up': True,
            'prescription_details': [
                {
                    'medicine_name': "Paracetamol",
                    'unit': "Tablet",
                    'dosage': "500mg",
                    'frequency': "Every 6 hours",
                    'duration': "5 days",
                    'prescription_notes': "",
                    'quantity': 20
                }
            ]
        }
        serializer = PrescriptionPdfDtoSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('patient_identity_number', serializer.errors)

class PrescriptionDetailRequestSerializerTest(TestCase):
    def test_serialize_valid_data(self):
        data = {
            'medicine_id': 1,
            'dosage': "500mg",
            'frequency': "Every 6 hours",
            'duration': "5 days",
            'prescription_notes': "Take after meals",
            'quantity': 20
        }
        serializer = PrescriptionDetailRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data, data)

    def test_invalid_data(self):
        data = {
            'medicine_id': 1,
            'dosage': "500mg",
            'frequency': "Every 6 hours",
            'duration': "5 days",
            'prescription_notes': "Take after meals",
            'quantity': -1
        }
        serializer = PrescriptionDetailRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('quantity', serializer.errors)

class CreatePrescriptionRequestSerializerTest(TestCase):
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
            department=cls.department
        )
        cls.room = ExaminationRoom.objects.create(
            department=cls.department,
            type=RoomType.EXAMINATION.value,
            building="A",
            floor=1
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
            usage="Take 1-2 tablets every 4-6 hours",
            unit="Tablet",
            price=Decimal('10.00'),
            quantity=100
        )

    def test_serialize_valid_data(self):
        data = {
            'appointment_id': self.appointment.id,
            'patient_id': self.patient.id,
            'follow_up_date': "2025-09-03",
            'is_follow_up': False,
            'diagnosis': "Bacterial infection",
            'systolic_blood_pressure': 130,
            'diastolic_blood_pressure': 85,
            'heart_rate': 75,
            'blood_sugar': 95,
            'note': "Antibiotics prescribed",
            'prescription_details': [
                {
                    'medicine_id': self.medicine.id,
                    'dosage': "500mg",
                    'frequency': "Every 6 hours",
                    'duration': "5 days",
                    'prescription_notes': "Take after meals",
                    'quantity': 20
                }
            ]
        }
        serializer = CreatePrescriptionRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['diagnosis'], "Bacterial infection")
        self.assertEqual(len(serializer.validated_data['prescription_details']), 1)

    def test_invalid_data(self):
        data = {
            'appointment_id': 1,
            'patient_id': self.patient.id,
            'follow_up_date': "2025-09-03",
            'is_follow_up': False,
            'diagnosis': "Bacterial infection",
            'systolic_blood_pressure': -1,
            'diastolic_blood_pressure': 85,
            'heart_rate': 75,
            'blood_sugar': 95,
            'note': "Antibiotics prescribed",
            'prescription_details': [
                {
                    'medicine_id': self.medicine.id,
                    'dosage': "500mg",
                    'frequency': "Every 6 hours",
                    'duration': "5 days",
                    'prescription_notes': "Take after meals",
                    'quantity': 20
                }
            ]
        }
        serializer = CreatePrescriptionRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('systolic_blood_pressure', serializer.errors)

class UpdatePrescriptionRequestSerializerTest(TestCase):
    def test_serialize_valid_data(self):
        data = {
            'follow_up_date': "2025-09-03",
            'is_follow_up': True,
            'diagnosis': "Updated diagnosis",
            'systolic_blood_pressure': 140,
            'diastolic_blood_pressure': 90,
            'heart_rate': 80,
            'blood_sugar': 100,
            'note': "Updated note",
            'prescription_details': [
                {
                    'medicine_id': 1,
                    'dosage': "1000mg",
                    'frequency': "Every 8 hours",
                    'duration': "7 days",
                    'prescription_notes': "Take with water",
                    'quantity': 21
                }
            ]
        }
        serializer = UpdatePrescriptionRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['diagnosis'], "Updated diagnosis")
        self.assertEqual(len(serializer.validated_data['prescription_details']), 1)

class AddMedicineToPrescriptionRequestSerializerTest(TestCase):
    def test_serialize_valid_data(self):
        data = {
            'prescription_id': 1,
            'medicine_id': 1,
            'dosage': "500mg",
            'frequency': "Every 6 hours",
            'duration': "5 days",
            'prescription_notes': "Take after meals",
            'quantity': 20
        }
        serializer = AddMedicineToPrescriptionRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['dosage'], "500mg")
        self.assertEqual(serializer.validated_data['quantity'], 20)

class UpdatePrescriptionDetailRequestSerializerTest(TestCase):
    def test_serialize_valid_data(self):
        data = {
            'detail_id': 1,
            'dosage': "1000mg",
            'frequency': "Every 8 hours",
            'duration': "7 days",
            'prescription_notes': "Take with water",
            'quantity': 21
        }
        serializer = UpdatePrescriptionDetailRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['dosage'], "1000mg")
        self.assertEqual(serializer.validated_data['quantity'], 21)

class NewMedicineRequestSerializerTest(TestCase):
    def test_serialize_valid_data(self):
        data = {
            'medicine_name': "Ibuprofen",
            'manufactor': "HealthCorp",
            'category': "Anti-inflammatory",
            'description': "Relieves inflammation",
            'usage': "Take 1 tablet every 6-8 hours",
            'unit': "Tablet",
            'is_insurance_covered': False,
            'insurance_discount_percent': None,
            'insurance_discount': None,
            'side_effects': "May cause stomach irritation",
            'price': "15.00",
            'quantity': 50
        }
        serializer = NewMedicineRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['medicine_name'], "Ibuprofen")
        self.assertEqual(serializer.validated_data['price'], Decimal('15.00'))

class UpdateMedicineRequestSerializerTest(TestCase):
    def test_serialize_valid_data(self):
        data = {
            'medicine_name': "Ibuprofen",
            'category': "Anti-inflammatory",
            'price': "20.00",
            'quantity': 75
        }
        serializer = UpdateMedicineRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['medicine_name'], "Ibuprofen")
        self.assertEqual(serializer.validated_data['price'], Decimal('20.00'))
