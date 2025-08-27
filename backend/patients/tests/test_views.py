from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.test import APIClient
from ..models import Patient, EmergencyContact
from ..serializers import PatientSerializer, CreatePatientRequestSerializer, EmergencyContactSerializer
from common.enums import Gender
import io

User = get_user_model()

class PatientViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="testuser@example.com",
            phone="1234567890",
            password="testpass123",
            role="P"
        )
        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            phone="9876543210",
            password="adminpass123",
            role="A"
        )
        self.client.force_authenticate(user=self.user)
        self.patient_data = {
            'email': 'newuser@example.com',
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
        self.patient = Patient.objects.create(
            user=self.user,
            identity_number="123456789",
            insurance_number="INS123456",
            first_name="John",
            last_name="Doe",
            birthday="1990-01-01",
            gender=Gender.MALE.value
        )

    def test_create_patient(self):
        """Test creating a new patient"""
        url = reverse('patient-list')
        self.patient_data['email'] = 'uniqueuser@example.com'
        self.patient_data['phone'] = '1234567899'
        self.patient_data['identity_number'] = '123456788'
        self.patient_data['insurance_number'] = 'INS123457'
        response = self.client.post(url, self.patient_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, f"Failed with errors: {response.data}")
        self.assertEqual(response.data['first_name'], "John")

    def test_create_patient_invalid_data(self):
        """Test creating patient with invalid data"""
        url = reverse('patient-list')
        invalid_data = self.patient_data.copy()
        invalid_data.pop('email')
        response = self.client.post(url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_list_patients(self):
        """Test listing all patients"""
        url = reverse('patient-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['first_name'], "John")

    def test_list_patients_by_user_id(self):
        """Test listing patients by user_id"""
        url = f"{reverse('patient-list')}?user_id={self.user.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], "John")

    def test_list_patients_invalid_user_id(self):
        """Test listing patients with invalid user_id"""
        url = f"{reverse('patient-list')}?user_id=999"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['error'], str(_("Không tìm thấy bệnh nhân với user_id này")))

    def test_retrieve_patient(self):
        """Test retrieving a single patient"""
        url = reverse('patient-detail', kwargs={'pk': self.patient.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], "John")

    def test_update_patient(self):
        """Test updating patient data"""
        url = reverse('patient-detail', kwargs={'pk': self.patient.id})
        updated_data = {'first_name': 'Johnny'}
        response = self.client.patch(url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], "Johnny")

    def test_update_patient_unauthorized(self):
        """Test updating patient as unauthorized user"""
        other_user = User.objects.create_user(
            email="other@example.com",
            phone="1112223333",
            password="testpass123",
            role="P"
        )
        self.client.force_authenticate(user=other_user)
        url = reverse('patient-detail', kwargs={'pk': self.patient.id})
        updated_data = {'first_name': 'Johnny'}
        response = self.client.patch(url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['error'], str(_("Không có quyền cập nhật")))

    def test_update_patient_as_admin(self):
        """Test updating patient as admin"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('patient-detail', kwargs={'pk': self.patient.id})
        updated_data = {'first_name': 'Johnny'}
        response = self.client.patch(url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], "Johnny")

    def test_delete_patient(self):
        """Test deleting a patient"""
        url = reverse('patient-detail', kwargs={'pk': self.patient.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], str(_("Bệnh nhân được xóa thành công")))
        self.assertFalse(Patient.objects.filter(id=self.patient.id).exists())

    def test_get_current_patient(self):
        """Test retrieving current authenticated patient's data"""
        url = reverse('patient-list') + 'me/'  # Adjust based on action URL
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], "John")

    def test_get_current_patient_no_patient(self):
        """Test retrieving current patient when none exists"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('patient-list') + 'me/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['error'], str(_("Không tìm thấy bệnh nhân")))

    def test_upload_avatar_no_file(self):
        """Test uploading avatar without file"""
        url = reverse('patient-upload-avatar', kwargs={'pk': self.patient.id})
        response = self.client.post(url, {}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], str(_("Thiếu file avatar")))

    def test_upload_avatar_unauthorized(self):
        """Test uploading avatar as unauthorized user"""
        other_user = User.objects.create_user(
            email="other@example.com",
            phone="1112223333",
            password="testpass123",
            role="P"
        )
        self.client.force_authenticate(user=other_user)
        url = reverse('patient-upload-avatar', kwargs={'pk': self.patient.id})
        mock_file = io.BytesIO(b"fake image data")
        mock_file.name = "test_image.jpg"
        response = self.client.post(url, {'avatar': mock_file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['error'], str(_("Không có quyền cập nhật")))

    def test_delete_avatar(self):
        """Test deleting an avatar"""
        url = reverse('patient-delete-avatar', kwargs={'pk': self.patient.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('avatar', response.data)

    def test_delete_avatar_unauthorized(self):
        """Test deleting avatar as unauthorized user"""
        other_user = User.objects.create_user(
            email="other@example.com",
            phone="1112223333",
            password="testpass123",
            role="P"
        )
        self.client.force_authenticate(user=other_user)
        url = reverse('patient-delete-avatar', kwargs={'pk': self.patient.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['error'], str(_("Không có quyền xóa")))

    def test_get_contacts(self):
        """Test retrieving emergency contacts"""
        url = reverse('patient-contacts', kwargs={'pk': self.patient.id})
        EmergencyContact.objects.create(
            patient=self.patient,
            contact_name="Jane Doe",
            contact_phone="0987654321",
            relationship="Sister"
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['contact_name'], "Jane Doe")

    def test_create_contact(self):
        """Test creating an emergency contact"""
        url = reverse('patient-contacts', kwargs={'pk': self.patient.id})
        contact_data = {
            'contact_name': 'Jane Doe',
            'contact_phone': '0987654321',
            'relationship': 'Sister'
        }
        response = self.client.post(url, contact_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['contact_name'], "Jane Doe")

    def test_update_contact(self):
        """Test updating an emergency contact"""
        contact = EmergencyContact.objects.create(
            patient=self.patient,
            contact_name="Jane Doe",
            contact_phone="0987654321",
            relationship="Sister"
        )
        url = reverse('patient-update-contact', kwargs={'pk': self.patient.id, 'contact_id': contact.id})
        updated_data = {'contact_name': 'Janet Doe'}
        response = self.client.patch(url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['contact_name'], "Janet Doe")

    def test_delete_contact(self):
        """Test deleting an emergency contact"""
        contact = EmergencyContact.objects.create(
            patient=self.patient,
            contact_name="Jane Doe",
            contact_phone="0987654321",
            relationship="Sister"
        )
        url = reverse('patient-contact-detail', kwargs={'pk': self.patient.id, 'contact_id': contact.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], str(_("Liên hệ được xóa thành công")))
        self.assertFalse(EmergencyContact.objects.filter(id=contact.id).exists())
