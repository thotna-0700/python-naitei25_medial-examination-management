from django.test import TestCase
from django.contrib.auth import get_user_model
from ..models import Patient, EmergencyContact
from ..serializers import PatientSerializer, CreatePatientRequestSerializer, EmergencyContactSerializer
from common.enums import Gender, UserRole
from common.constants import PATIENT_LENGTH, COMMON_LENGTH, USER_LENGTH
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

User = get_user_model()

class PatientSerializerTest(TestCase):
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
            blood_type="A+",
            avatar="avatar.jpg"
        )
        self.emergency_contact = EmergencyContact.objects.create(
            patient=self.patient,
            contact_name="Jane Doe",
            contact_phone="0987654321",
            relationship="Sister"
        )

    def test_patient_serializer(self):
        serializer = PatientSerializer(self.patient)
        data = serializer.data
        self.assertEqual(data['id'], self.patient.id)
        self.assertEqual(data['email'], "testuser@example.com")
        self.assertEqual(data['phone'], "1234567890")
        self.assertEqual(data['first_name'], "John")
        self.assertEqual(data['last_name'], "Doe")
        self.assertEqual(data['identity_number'], "123456789")
        self.assertEqual(data['insurance_number'], "INS123456")
        self.assertEqual(data['birthday'], "1990-01-01")
        self.assertEqual(data['gender'], Gender.MALE.value)
        self.assertEqual(data['address'], "123 Main St")
        self.assertEqual(data['allergies'], "Peanuts")
        self.assertEqual(data['height'], 175)
        self.assertEqual(data['weight'], 70)
        self.assertEqual(data['blood_type'], "A+")
        self.assertEqual(data['avatar'], "avatar.jpg")
        self.assertEqual(len(data['emergency_contacts']), 1)
        self.assertEqual(data['emergency_contacts'][0]['contact_name'], "Jane Doe")
        self.assertEqual(data['emergency_contacts'][0]['contact_phone'], "0987654321")
        self.assertEqual(data['emergency_contacts'][0]['relationship'], "Sister")

    def test_emergency_contacts_empty(self):
        self.user = User.objects.create(
            email="testuser2@example.com",
            phone="1234567891",
            password="testpass123",
            role=UserRole.PATIENT.value
        )
        patient_no_contacts = Patient.objects.create(
            user=self.user,
            identity_number="987654322",
            insurance_number="INS987654",
            first_name="Alice",
            last_name="Smith",
            birthday="1985-05-05",
            gender=Gender.FEMALE.value
        )
        serializer = PatientSerializer(patient_no_contacts)
        self.assertEqual(len(serializer.data['emergency_contacts']), 0)

class CreatePatientRequestSerializerTest(TestCase):
    def setUp(self):
        self.valid_data = {
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
            ],
            'avatar': 'avatar.jpg'
        }

    def test_valid_serializer(self):
        serializer = CreatePatientRequestSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['email'], 'testuser@example.com')
        self.assertEqual(serializer.validated_data['first_name'], 'John')
        self.assertEqual(serializer.validated_data['last_name'], 'Doe')
        self.assertEqual(serializer.validated_data['gender'], Gender.MALE.value)
        self.assertEqual(len(serializer.validated_data['emergencyContactDtos']), 1)
        self.assertEqual(serializer.validated_data['emergencyContactDtos'][0]['contact_name'], 'Jane Doe')

    def test_invalid_serializer_missing_fields(self):
        invalid_data = self.valid_data.copy()
        for field in ['email', 'phone', 'password', 'identity_number', 'insurance_number', 
                     'first_name', 'last_name', 'birthday', 'gender']:
            data = self.valid_data.copy()
            data.pop(field)
            serializer = CreatePatientRequestSerializer(data=data)
            self.assertFalse(serializer.is_valid())
            self.assertIn(field, serializer.errors)
            self.assertEqual(str(serializer.errors[field][0]), str(_("Trường này là bắt buộc.")))

    def test_optional_fields(self):
        data = self.valid_data.copy()
        optional_fields = ['address', 'allergies', 'height', 'weight', 'blood_type', 'emergencyContactDtos', 'avatar']
        for field in optional_fields:
            data.pop(field)
        serializer = CreatePatientRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        for field in optional_fields:
            self.assertNotIn(field, serializer.validated_data)

    def test_invalid_email_format(self):
        invalid_data = self.valid_data.copy()
        invalid_data['email'] = 'invalid_email'
        serializer = CreatePatientRequestSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
        self.assertEqual(str(serializer.errors['email'][0]), 'Nhập một địa chỉ email hợp lệ.')

    def test_invalid_gender(self):
        invalid_data = self.valid_data.copy()
        invalid_data['gender'] = 'INVALID'
        serializer = CreatePatientRequestSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('gender', serializer.errors)
        self.assertEqual(str(serializer.errors['gender'][0]), '"INVALID" is not a valid choice.')

    def test_field_length_validation(self):
        invalid_data = self.valid_data.copy()
        invalid_data['phone'] = '1' * (USER_LENGTH['PHONE'] + 1)
        invalid_data['first_name'] = 'A' * (COMMON_LENGTH['NAME'] + 1)
        invalid_data['identity_number'] = '1' * (PATIENT_LENGTH['IDENTITY'] + 1)
        serializer = CreatePatientRequestSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('phone', serializer.errors)
        self.assertIn('first_name', serializer.errors)
        self.assertIn('identity_number', serializer.errors)

    def test_emergency_contact_validation(self):
        invalid_data = self.valid_data.copy()
        invalid_data['emergencyContactDtos'] = [
            {'contact_name': '', 'contact_phone': '0987654321', 'relationship': 'Sister'}
        ]
        serializer = CreatePatientRequestSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('emergencyContactDtos', serializer.errors)

class EmergencyContactSerializerTest(TestCase):
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
        self.emergency_contact_data = {
            'contact_name': 'Jane Doe',
            'contact_phone': '0987654321',
            'relationship': 'Sister',
            'patient_id': self.patient.id
        }

    def test_valid_emergency_contact_serializer(self):
        serializer = EmergencyContactSerializer(data=self.emergency_contact_data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['contact_name'], 'Jane Doe')
        self.assertEqual(serializer.validated_data['contact_phone'], '0987654321')
        self.assertEqual(serializer.validated_data['relationship'], 'Sister')

    def test_missing_required_emergency_contact_fields(self):
        invalid_data = self.emergency_contact_data.copy()
        invalid_data.pop('contact_name')
        serializer = EmergencyContactSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('contact_name', serializer.errors)
