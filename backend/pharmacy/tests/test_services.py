from django.test import TestCase
from django.shortcuts import get_object_or_404
from django.db import transaction, IntegrityError
from django.utils.translation import gettext as _
from decimal import Decimal
from datetime import date, time
from io import BytesIO
from pharmacy.services import PharmacyService
from pharmacy.models import Medicine, Prescription, PrescriptionDetail
from patients.models import Patient
from appointments.models import Appointment
from doctors.models import Doctor, Department, Schedule, ExaminationRoom
from users.models import User
from common.enums import AppointmentStatus, Gender, AcademicDegree, DoctorType, RoomType, Shift, UserRole
from common.constants import SCHEDULE_DEFAULTS, PHARMACY_LENGTH, COMMON_LENGTH, MIN_VALUE

class PharmacyServiceTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.service = PharmacyService()
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
            manufactor="PharmaCorp",
            category="Pain Relief",
            description="Relieves mild pain",
            usage="Take 1-2 tablets every 4-6 hours",
            unit="Tablet",
            is_insurance_covered=True,
            insurance_discount_percent=50,
            price=Decimal('10.00'),
            quantity=100,
            side_effects="May cause drowsiness"
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

    def test_create_prescription(self):
        new_appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            schedule=self.schedule,
            symptoms="Cough",
            slot_start=time(8, 30),
            slot_end=time(9, 0),
            status=AppointmentStatus.CONFIRMED.value
        )
        data = {
            'appointment_id': new_appointment.id,  # use the new appointment
            'patient_id': self.patient.id,
            'follow_up_date': date(2025, 9, 3),
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
                    'dosage': "1000mg",
                    'frequency': "Every 8 hours",
                    'duration': "7 days",
                    'prescription_notes': "Take with water",
                    'quantity': 21
                }
            ]
        }
        prescription = self.service.create_prescription(data)
        self.assertEqual(prescription.diagnosis, "Bacterial infection")
        self.assertEqual(prescription.prescription_details.count(), 1)
        detail = prescription.prescription_details.first()
        self.assertEqual(detail.dosage, "1000mg")
        self.assertEqual(detail.quantity, 21)

    def test_update_prescription(self):
        data = {
            'follow_up_date': date(2025, 9, 4),
            'diagnosis': "Updated diagnosis",
            'prescription_details': [
                {
                    'medicine_id': self.medicine.id,
                    'dosage': "750mg",
                    'frequency': "Every 12 hours",
                    'duration': "10 days",
                    'prescription_notes': "Updated note",
                    'quantity': 30
                }
            ]
        }
        updated_prescription = self.service.update_prescription(self.prescription.id, data)
        self.assertEqual(updated_prescription.follow_up_date, date(2025, 9, 4))
        self.assertEqual(updated_prescription.diagnosis, "Updated diagnosis")
        self.assertEqual(updated_prescription.prescription_details.count(), 1)
        detail = updated_prescription.prescription_details.first()
        self.assertEqual(detail.dosage, "750mg")
        self.assertEqual(detail.quantity, 30)

    def test_delete_prescription(self):
        deleted_prescription = self.service.delete_prescription(self.prescription.id)
        self.assertTrue(deleted_prescription.is_deleted)

    def test_add_medicine_to_prescription(self):
        data = {
            'prescription_id': self.prescription.id,
            'medicine_id': self.medicine.id,
            'dosage': "250mg",
            'frequency': "Every 4 hours",
            'duration': "3 days",
            'prescription_notes': "New addition",
            'quantity': 15
        }
        detail = self.service.add_medicine_to_prescription(data)
        self.assertEqual(detail.dosage, "250mg")
        self.assertEqual(detail.quantity, 15)
        self.assertEqual(self.prescription.prescription_details.count(), 2)

    def test_update_prescription_detail(self):
        data = {
            'dosage': "750mg",
            'quantity': 30
        }
        updated_detail = self.service.update_prescription_detail(self.prescription_detail.id, data)
        self.assertEqual(updated_detail.dosage, "750mg")
        self.assertEqual(updated_detail.quantity, 30)

    def test_delete_prescription_detail(self):
        self.service.delete_prescription_detail(self.prescription_detail.id)
        self.assertEqual(self.prescription.prescription_details.count(), 0)

    def test_get_prescriptions_by_patient_id(self):
        prescriptions = self.service.get_prescriptions_by_patient_id(self.patient.id)
        self.assertEqual(prescriptions.count(), 1)
        self.assertEqual(prescriptions.first().id, self.prescription.id)

    def test_get_prescriptions_by_appointment_id(self):
        prescriptions = self.service.get_prescriptions_by_appointment_id(self.appointment.id)
        self.assertEqual(prescriptions.count(), 1)
        self.assertEqual(prescriptions.first().id, self.prescription.id)

    def test_get_prescription_by_id(self):
        prescription = self.service.get_prescription_by_id(self.prescription.id)
        self.assertEqual(prescription.id, self.prescription.id)

    def test_get_prescription_detail_by_id(self):
        detail = self.service.get_prescription_detail_by_id(self.prescription_detail.id)
        self.assertEqual(detail.id, self.prescription_detail.id)

    def test_add_new_medicine(self):
        data = {
            'medicine_name': "Ibuprofen",
            'manufactor': "HealthCorp",
            'category': "Anti-inflammatory",
            'description': "Relieves inflammation",
            'usage': "Take 1 tablet every 6-8 hours",
            'unit': "Tablet",
            'is_insurance_covered': False,
            'insurance_discount_percent': 20,
            'side_effects': "May cause stomach irritation",
            'price': Decimal('15.00'),
            'quantity': 50
        }
        medicine = self.service.add_new_medicine(data)
        self.assertEqual(medicine.medicine_name, "Ibuprofen")
        self.assertEqual(medicine.price, Decimal('15.00'))
        self.assertEqual(medicine.insurance_discount, Decimal('3.00'))

    def test_add_new_medicine_invalid_discount(self):
        data = {
            'medicine_name': "Ibuprofen",
            'category': "Anti-inflammatory",
            'usage': "Take 1 tablet every 6-8 hours",
            'unit': "Tablet",
            'insurance_discount_percent': 150,
            'price': Decimal('15.00')
        }
        with self.assertRaises(ValueError):
            self.service.add_new_medicine(data)

    def test_get_all_medicines(self):
        medicines = self.service.get_all_medicines()
        self.assertEqual(medicines.count(), 1)
        self.assertEqual(medicines.first().id, self.medicine.id)

    def test_get_medicine_by_id(self):
        medicine = self.service.get_medicine_by_id(self.medicine.id)
        self.assertEqual(medicine.id, self.medicine.id)

    def test_search_medicine(self):
        medicines = self.service.search_medicine(name="Paracetamol", category="Pain Relief")
        self.assertEqual(medicines.count(), 1)
        self.assertEqual(medicines.first().id, self.medicine.id)

        medicines = self.service.search_medicine(name="Nonexistent")
        self.assertEqual(medicines.count(), 0)

    def test_update_medicine(self):
        data = {
            'medicine_name': "Updated Paracetamol",
            'price': Decimal('12.00'),
            'insurance_discount_percent': 30
        }
        updated_medicine = self.service.update_medicine(self.medicine.id, data)
        self.assertEqual(updated_medicine.medicine_name, "Updated Paracetamol")
        self.assertEqual(updated_medicine.price, Decimal('12.00'))
        self.assertEqual(updated_medicine.insurance_discount, Decimal('3.60'))

    def test_update_medicine_invalid_discount(self):
        data = {
            'insurance_discount_percent': 150
        }
        with self.assertRaises(ValueError):
            self.service.update_medicine(self.medicine.id, data)

    def test_delete_medicine(self):
        new_medicine = Medicine.objects.create(
            medicine_name="Deletable Medicine",
            category="Test",
            usage="Test usage",
            unit="Test unit",
            price=Decimal('5.00'),
            quantity=10
        )
        self.service.delete_medicine(new_medicine.id)
        with self.assertRaises(Exception):
            get_object_or_404(Medicine, pk=new_medicine.id)

    def test_delete_medicine_with_prescription(self):
        with self.assertRaises(ValueError):
            self.service.delete_medicine(self.medicine.id)

    def test_generate_prescription_pdf(self):
        buffer = self.service.generate_prescription_pdf(self.prescription.id)
        self.assertIsInstance(buffer, BytesIO)
        self.assertGreater(buffer.getbuffer().nbytes, 0)
