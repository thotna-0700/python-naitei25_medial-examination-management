from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse
from django.contrib.auth.models import Group
from django.utils import timezone
from django.utils.translation import gettext as _
from django.contrib.auth import get_user_model
from rest_framework import status
from pharmacy.models import Medicine, Prescription, PrescriptionDetail
from patients.models import Patient
from appointments.models import Appointment
from doctors.models import Doctor, Department, Schedule, ExaminationRoom
from common.enums import AppointmentStatus, Gender, AcademicDegree, DoctorType, RoomType, Shift, UserRole
from common.constants import SCHEDULE_DEFAULTS
from decimal import Decimal
from datetime import date, time, datetime

User = get_user_model()

class PharmacyViewSetTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()
        cls.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='adminpass123',
            role=UserRole.ADMIN.value,
            phone="1234567890"
        )
        cls.doctor_user = User.objects.create_user(
            email='doctor@example.com',
            password='doctorpass123',
            role=UserRole.DOCTOR.value,
            phone="0987654321"
        )
        cls.patient_user = User.objects.create_user(
            email='patient@example.com',
            password='patientpass123',
            role=UserRole.PATIENT.value,
            phone="1122334455"
        )
        cls.patient = Patient.objects.create(
            user=cls.patient_user,
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
            user=cls.doctor_user,
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
            status=AppointmentStatus.CONFIRMED.value
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
            insurance_discount=Decimal('5.00'),
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
            note="Follow-up in one week",
            created_at=timezone.make_aware(datetime(2025, 8, 26))
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

    def setUp(self):
        self.client = APIClient()

    def test_list_prescriptions_unauthenticated(self):
        response = self.client.get(reverse('prescription-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_prescriptions_authenticated(self):
        self.client.force_authenticate(user=self.patient_user)
        response = self.client.get(reverse('prescription-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.prescription.id)

    def test_retrieve_prescription(self):
        self.client.force_authenticate(user=self.patient_user)
        response = self.client.get(reverse('prescription-detail', kwargs={'pk': self.prescription.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.prescription.id)
        self.assertEqual(response.data['diagnosis'], "Viral infection")

    def test_retrieve_prescription_nonexistent(self):
        self.client.force_authenticate(user=self.patient_user)
        response = self.client.get(reverse('prescription-detail', kwargs={'pk': 9999}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_prescription(self):
        self.client.force_authenticate(user=self.doctor_user)
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
            'appointment_id': new_appointment.id,
            'patient_id': self.patient.id,
            'follow_up_date': None,
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
        response = self.client.post(reverse('prescription-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['diagnosis'], "Bacterial infection")
        self.assertEqual(len(response.data['prescription_details']), 1)

    def test_create_prescription_unauthorized(self):
        self.client.force_authenticate(user=self.patient_user)
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
                    'dosage': "1000mg",
                    'frequency': "Every 8 hours",
                    'duration': "7 days",
                    'prescription_notes': "Take with water",
                    'quantity': 21
                }
            ]
        }
        response = self.client.post(reverse('prescription-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_prescription_invalid_data(self):
        self.client.force_authenticate(user=self.doctor_user)
        data = {
            'appointment_id': self.appointment.id,
            'patient_id': self.patient.id,
            'follow_up_date': "2025-09-03",
            'is_follow_up': True,
            'diagnosis': "Bacterial infection",
            'systolic_blood_pressure': -1,
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
        response = self.client.post(reverse('prescription-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('systolic_blood_pressure', response.data)

    def test_update_prescription(self):
        self.client.force_authenticate(user=self.doctor_user)
        data = {
            'follow_up_date': "2025-09-04",
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
        response = self.client.put(reverse('prescription-detail', kwargs={'pk': self.prescription.id}), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['diagnosis'], "Updated diagnosis")
        self.assertEqual(len(response.data['prescription_details']), 1)

    def test_update_prescription_unauthorized(self):
        self.client.force_authenticate(user=self.patient_user)
        data = {
            'diagnosis': "Updated diagnosis"
        }
        response = self.client.put(reverse('prescription-detail', kwargs={'pk': self.prescription.id}), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_destroy_prescription(self):
        self.client.force_authenticate(user=self.doctor_user)
        response = self.client.delete(reverse('prescription-detail', kwargs={'pk': self.prescription.id}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.data['message'], _("Prescription deleted successfully"))

    def test_destroy_prescription_nonexistent(self):
        self.client.force_authenticate(user=self.doctor_user)
        response = self.client.delete(reverse('prescription-detail', kwargs={'pk': 9999}))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], _("No Prescription matches the given query."))

    def test_add_medicine_to_prescription(self):
        self.client.force_authenticate(user=self.doctor_user)
        data = {
            'prescription_id': self.prescription.id,
            'medicine_id': self.medicine.id,
            'dosage': "250mg",
            'frequency': "Every 4 hours",
            'duration': "3 days",
            'prescription_notes': "New addition",
            'quantity': 15
        }
        response = self.client.post(reverse('prescription-add-medicine-to-prescription'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['dosage'], "250mg")
        self.assertEqual(response.data['quantity'], 15)

    def test_get_prescription_details(self):
        self.client.force_authenticate(user=self.patient_user)
        response = self.client.get(reverse('prescription-get-prescription-details', kwargs={'pk': self.prescription.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.prescription_detail.id)

    def test_delete_prescription_detail(self):
        self.client.force_authenticate(user=self.doctor_user)
        response = self.client.delete(
            reverse('prescription-delete-prescription-detail', kwargs={'pk': self.prescription.id, 'detail_id': self.prescription_detail.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], _("Chi tiết đơn thuốc được xóa thành công"))

    def test_get_prescriptions_by_patient_id(self):
        self.client.force_authenticate(user=self.patient_user)
        response = self.client.get(reverse('prescription-get-prescriptions-by-patient-id', kwargs={'patient_id': self.patient.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.prescription.id)

    def test_get_prescriptions_by_appointment_id(self):
        self.client.force_authenticate(user=self.patient_user)
        new_appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            schedule=self.schedule,
            symptoms="Headache",
            slot_start=time(9, 0),
            slot_end=time(9, 30),
            status=AppointmentStatus.CONFIRMED.value
        )
        new_prescription = Prescription.objects.create(
            appointment=new_appointment,
            patient=self.patient,
            diagnosis="Migraine"
        )
        
        response = self.client.get(
            reverse('prescription-get-prescriptions-by-appointment-id', kwargs={'appointment_id': new_appointment.id})
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_prescription_pdf(self):
        self.client.force_authenticate(user=self.patient_user)
        response = self.client.get(reverse('prescription-get-prescription-pdf', kwargs={'pk': self.prescription.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn(f'prescription_{self.prescription.id}.pdf', response['Content-Disposition'])

class MedicineViewSetTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()

        cls.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='adminpass123',
            role=UserRole.ADMIN.value,
        )

        cls.doctor_user = User.objects.create_user(
            email='doctor@example.com',
            password='doctorpass123',
            role=UserRole.DOCTOR.value,
        )
        cls.patient_user = User.objects.create_user(
            email='patient@example.com',
            password='patientpass123',
            role=UserRole.PATIENT.value
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
            insurance_discount=Decimal('5.00'),
            price=Decimal('10.00'),
            quantity=100,
            side_effects="May cause drowsiness"
        )

    def setUp(self):
        self.client = APIClient()

    def test_list_medicines_unauthenticated(self):
        response = self.client.get(reverse('medicine-list'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_medicines_authenticated(self):
        self.client.force_authenticate(user=self.patient_user)
        response = self.client.get(reverse('medicine-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.medicine.id)

    def test_retrieve_medicine(self):
        self.client.force_authenticate(user=self.patient_user)
        response = self.client.get(reverse('medicine-detail', kwargs={'pk': self.medicine.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.medicine.id)
        self.assertEqual(response.data['medicine_name'], "Paracetamol")

    def test_retrieve_medicine_nonexistent(self):
        self.client.force_authenticate(user=self.patient_user)
        response = self.client.get(reverse('medicine-detail', kwargs={'pk': 9999}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_medicine(self):
        self.client.force_authenticate(user=self.doctor_user)
        data = {
            'medicine_name': "Ibuprofen",
            'manufactor': "HealthCorp",
            'category': "Anti-inflammatory",
            'description': "Relieves inflammation",
            'usage': "Take 1 tablet every 6-8 hours",
            'unit': "Tablet",
            'is_insurance_covered': False,
            'insurance_discount_percent': 0,
            'side_effects': "May cause stomach irritation",
            'price': "15.00",
            'quantity': 50
        }
        response = self.client.post(reverse('medicine-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['medicine_name'], "Ibuprofen")
        self.assertEqual(response.data['price'], "15.00")

    def test_create_medicine_unauthenticated(self):
        data = {
            'medicine_name': "Ibuprofen",
            'category': "Anti-inflammatory",
            'usage': "Take 1 tablet every 6-8 hours",
            'unit': "Tablet",
            'price': "15.00"
        }
        response = self.client.post(reverse('medicine-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_medicine_invalid_data(self):
        self.client.force_authenticate(user=self.doctor_user)
        data = {
            'medicine_name': "Ibuprofen",
            'category': "Anti-inflammatory",
            'usage': "Take 1 tablet every 6-8 hours",
            'unit': "Tablet",
            'price': "-15.00"
        }
        response = self.client.post(reverse('medicine-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('price', response.data)

    def test_update_medicine(self):
        self.client.force_authenticate(user=self.doctor_user)
        data = {
            'medicine_name': "Updated Paracetamol",
            'category': "Pain Relief",
            'price': "12.00",
            'quantity': 75
        }
        response = self.client.put(reverse('medicine-detail', kwargs={'pk': self.medicine.id}), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['medicine_name'], "Updated Paracetamol")
        self.assertEqual(response.data['price'], "12.00")

    def test_update_medicine_unauthenticated(self):
        data = {
            'medicine_name': "Updated Paracetamol",
            'price': "12.00"
        }
        response = self.client.put(reverse('medicine-detail', kwargs={'pk': self.medicine.id}), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_search_medicine(self):
        self.client.force_authenticate(user=self.patient_user)
        response = self.client.get(reverse('medicine-search-medicine') + '?name=Paracetamol&category=Pain%20Relief')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.medicine.id)

    def test_search_medicine_no_results(self):
        self.client.force_authenticate(user=self.patient_user)
        response = self.client.get(reverse('medicine-search-medicine') + '?name=Nonexistent')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)
