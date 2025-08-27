# test_services.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from ..models import Patient, EmergencyContact
from ..services import PatientService, EmergencyContactService
from common.enums import Gender
from users.services import UserService
from unittest.mock import patch

User = get_user_model()

class PatientServiceTest(TestCase):
    def setUp(self):
        self.user_service = UserService()
        self.patient_service = PatientService()
        self.user_data = {
            'email': 'testuser@example.com',
            'phone': '1234567890',
            'password': 'testpass123',
            'role': 'P'
        }
        self.patient_data = {
            'email': 'testuser@example.com',
            'phone': '1234567890',
            'password': 'testpass123',
            'identity_number': '123456789',
            'insurance_number': 'INS123456',
            'first_name': 'John',
            'last_name': 'Doe',
            'birthday': '1990-01-01',
            'gender': Gender.MALE.value,
            'address': '123 Main St',
            'allergies': 'Peanuts',
            'height': 175,
            'weight': 70,
            'blood_type': 'A+',
            'emergencyContactDtos': [
                {'contact_name': 'Jane Doe', 'contact_phone': '0987654321', 'relationship': 'Sister'}
            ]
        }

    def test_create_patient(self):
        patient = self.patient_service.create_patient(self.patient_data)
        self.assertEqual(patient.first_name, "John")
        self.assertEqual(patient.last_name, "Doe")
        self.assertEqual(patient.emergencycontact_set.count(), 1)
        self.assertEqual(patient.emergencycontact_set.first().contact_name, "Jane Doe")

    @patch('cloudinary.uploader.upload')
    def test_upload_avatar(self, mock_upload):
        mock_upload.return_value = {'secure_url': 'http://example.com/avatar.jpg'}
        patient = self.patient_service.create_patient(self.patient_data)
        file = 'fake_file.jpg'
        updated_patient = self.patient_service.upload_avatar(patient, file)
        self.assertEqual(updated_patient.avatar, 'http://example.com/avatar.jpg')

    @patch('cloudinary.uploader.destroy')
    def test_delete_avatar(self, mock_destroy):
        patient = self.patient_service.create_patient(self.patient_data)
        patient.avatar = 'http://example.com/avatar.jpg'
        patient.save()
        updated_patient = self.patient_service.delete_avatar(patient)
        self.assertIsNone(updated_patient.avatar)
        mock_destroy.assert_called_once()

    def test_delete_patient(self):
        patient = self.patient_service.create_patient(self.patient_data)
        self.patient_service.delete_patient(patient)
        self.assertFalse(Patient.objects.filter(id=patient.id).exists())
        self.assertFalse(User.objects.filter(id=patient.user.id).exists())

class EmergencyContactServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            email="testuser@example.com",
            phone="1234567890",
            password="testpass123",
            role="P"
        )
        self.patient = Patient.objects.create(
            user=self.user,
            identity_number="123456789",
            insurance_number="INS123456",
            first_name="John",
            last_name="Doe",
            birthday="1990-01-01",
            gender=Gender.MALE.value
        )
        self.emergency_contact_service = EmergencyContactService()
        self.contact_data = {
            'contact_name': 'Jane Doe',
            'contact_phone': '0987654321',
            'relationship': 'Sister'
        }

    def test_create_emergency_contact(self):
        contact = self.emergency_contact_service.create_emergency_contact(self.patient.id, self.contact_data)
        self.assertEqual(contact.contact_name, "Jane Doe")
        self.assertEqual(contact.patient, self.patient)

    def test_get_all_emergency_contacts(self):
        EmergencyContact.objects.create(
            patient=self.patient,
            contact_name="Jane Doe",
            contact_phone="0987654321",
            relationship="Sister"
        )
        contacts = self.emergency_contact_service.get_all_emergency_contacts(self.patient.id)
        self.assertEqual(contacts.count(), 1)
        self.assertEqual(contacts[0].contact_name, "Jane Doe")
