# test_models.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from ..models import Patient, EmergencyContact
from common.enums import Gender, UserRole

User = get_user_model()

class PatientModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            email="testuser@example.com",
            phone="1234567890",
            password="testpass123",
            role=UserRole.PATIENT.value
        )
        self.patient = Patient.objects.create(
            user=self.user,
            identity_number="123456789",
            insurance_number="INS123456",
            first_name="John",
            last_name="Doe",
            birthday="1990-01-01",
            gender=Gender.MALE.value,
            address="123 Main St",
            allergies="Peanuts",
            height=175,
            weight=70,
            blood_type="A+"
        )

    def test_patient_str(self):
        self.assertEqual(str(self.patient), "John Doe")

    def test_patient_creation(self):
        self.assertEqual(self.patient.first_name, "John")
        self.assertEqual(self.patient.last_name, "Doe")
        self.assertEqual(self.patient.identity_number, "123456789")
        self.assertEqual(self.patient.user.email, "testuser@example.com")

class EmergencyContactModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            email="testuser@example.com",
            phone="1234567890",
            password="testpass123",
            role=UserRole.PATIENT.value
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
        self.emergency_contact = EmergencyContact.objects.create(
            patient=self.patient,
            contact_name="Jane Doe",
            contact_phone="0987654321",
            relationship="Sister"
        )

    def test_emergency_contact_str(self):
        self.assertEqual(str(self.emergency_contact), "Jane Doe (Sister)")

    def test_emergency_contact_creation(self):
        self.assertEqual(self.emergency_contact.contact_name, "Jane Doe")
        self.assertEqual(self.emergency_contact.relationship, "Sister")
        self.assertEqual(self.emergency_contact.patient, self.patient)
