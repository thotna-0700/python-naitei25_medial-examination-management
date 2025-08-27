from django.test import TestCase
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext as _
from unittest.mock import patch
from datetime import datetime, timedelta, date
from users.models import User
from users.services import UserService, AuthService, OtpService, ResetTokenService
from patients.models import Patient
from common.enums import UserRole, Gender
from common.constants import PAGE_NO_DEFAULT, PAGE_SIZE_DEFAULT

User = get_user_model()

class MockEmailSend:
    def __init__(self):
        self.sent_emails = []

    def __call__(self, subject, message, from_email, recipient_list, fail_silently=False):
        self.sent_emails.append({
            'subject': subject,
            'message': message,
            'from_email': from_email,
            'recipient_list': recipient_list,
            'fail_silently': fail_silently
        })
        return 1

class UserViewSetTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        # Create users for testing
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            phone='0123456789',
            password='AdminPass123!',
            role=UserRole.ADMIN.value,
            is_active=True,
            is_verified=True
        )
        self.doctor_user = User.objects.create_user(
            email='doctor@example.com',
            phone='0987654321',
            password='DoctorPass123!',
            role=UserRole.DOCTOR.value,
            is_active=True,
            is_verified=True
        )
        self.patient_user = User.objects.create_user(
            email='patient@example.com',
            phone='0112233445',
            password='PatientPass123!',
            role=UserRole.PATIENT.value,
            is_active=True,
            is_verified=True
        )
        self.deleted_user = User.objects.create_user(
            email='deleted@example.com',
            phone='0555555555',
            password='DeletedPass123!',
            role=UserRole.PATIENT.value,
            is_active=True,
            is_verified=True
        )
        self.deleted_user.soft_delete()
        self.patient = Patient.objects.create(
            user=self.patient_user,
            first_name='Test',
            last_name='Patient',
            identity_number='123456789012',
            insurance_number='INS123456',
            birthday=date(1990, 1, 1),
            gender=Gender.MALE.value,
            address='123 Main St'
        )

    def authenticate_client(self, user):
        self.client.force_authenticate(user=user)

    def test_retrieve_as_admin(self):
        self.authenticate_client(self.admin_user)
        response = self.client.get(f'/api/v1/users/{self.patient_user.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'patient@example.com')

    def test_retrieve_as_doctor(self):
        self.authenticate_client(self.doctor_user)
        response = self.client.get(f'/api/v1/users/{self.patient_user.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'patient@example.com')

    def test_retrieve_unauthenticated(self):
        response = self.client.get(f'/api/v1/users/{self.patient_user.id}/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_current_user(self):
        self.authenticate_client(self.patient_user)
        response = self.client.get('/api/v1/users/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'patient@example.com')

    def test_get_current_user_unauthenticated(self):
        response = self.client.get('/api/v1/users/me/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_all_users_as_admin(self):
        self.authenticate_client(self.admin_user)
        response = self.client.get(f'/api/v1/users/all/?page={PAGE_NO_DEFAULT}&size={PAGE_SIZE_DEFAULT}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['content']), 3)  # admin, doctor, patient
        self.assertEqual(response.data['page'], PAGE_NO_DEFAULT)
        self.assertEqual(response.data['size'], PAGE_SIZE_DEFAULT)

    def test_get_all_users_non_admin(self):
        self.authenticate_client(self.patient_user)
        response = self.client.get(f'/api/v1/users/all/?page={PAGE_NO_DEFAULT}&size={PAGE_SIZE_DEFAULT}')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_user_by_id_as_admin(self):
        self.authenticate_client(self.admin_user)
        response = self.client.get(f'/api/v1/users/{self.patient_user.id}/get_user_by_id/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'patient@example.com')

    def test_get_user_by_id_as_doctor(self):
        self.authenticate_client(self.doctor_user)
        response = self.client.get(f'/api/v1/users/{self.patient_user.id}/get_user_by_id/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'patient@example.com')

    def test_get_user_by_id_unauthenticated(self):
        response = self.client.get(f'/api/v1/users/{self.patient_user.id}/get_user_by_id/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_add_user_as_admin(self):
        self.authenticate_client(self.admin_user)
        data = {
            'email': 'newuser@example.com',
            'phone': '0999999999',
            'password': 'NewPass123!',
            'role': UserRole.PATIENT.value
        }
        response = self.client.post('/api/v1/users/add/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['email'], 'newuser@example.com')

    def test_add_user_non_admin(self):
        self.authenticate_client(self.patient_user)
        data = {
            'email': 'newuser@example.com',
            'phone': '0999999999',
            'password': 'NewPass123!',
            'role': UserRole.PATIENT.value
        }
        response = self.client.post('/api/v1/users/add/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_edit_user_as_owner(self):
        self.authenticate_client(self.patient_user)
        data = {
            'email': 'updated@example.com',
            'phone': '0777777777'
        }
        response = self.client.put(f'/api/v1/users/{self.patient_user.id}/edit_user/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'updated@example.com')

    def test_edit_user_as_admin(self):
        self.authenticate_client(self.admin_user)
        data = {
            'email': 'updated@example.com',
            'phone': '0777777777'
        }
        response = self.client.put(f'/api/v1/users/{self.patient_user.id}/edit_user/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'updated@example.com')

    def test_edit_user_unauthorized(self):
        self.authenticate_client(self.doctor_user)
        data = {
            'email': 'updated@example.com'
        }
        response = self.client.put(f'/api/v1/users/{self.patient_user.id}/edit_user/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_user_with_relations(self):
        self.authenticate_client(self.admin_user)
        response = self.client.delete(f'/api/v1/users/{self.patient_user.id}/delete_user/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn(_('Không thể xóa người dùng này vì còn liên kết với: Bệnh nhân'), response.data['error'])

    def test_delete_user_no_relations(self):
        user = User.objects.create_user(
            email='norel@example.com',
            phone='0666666666',
            password='NoRelPass123!',
            role=UserRole.PATIENT.value
        )
        self.authenticate_client(self.admin_user)
        response = self.client.delete(f'/api/v1/users/{user.id}/delete_user/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], _('Xóa người dùng thành công (soft delete)'))

    def test_force_delete_user(self):
        self.authenticate_client(self.admin_user)
        response = self.client.delete(f'/api/v1/users/{self.patient_user.id}/force-delete/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], _('Xóa người dùng thành công (soft delete)'))

    def test_restore_user_unauthorized(self):
        self.authenticate_client(self.doctor_user)
        response = self.client.post(f'/api/v1/users/{self.deleted_user.id}/restore/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_change_password_self(self):
        self.authenticate_client(self.patient_user)
        data = {
            'oldPassword': 'PatientPass123!',
            'newPassword': 'NewPass123!',
            'adminReset': False
        }
        response = self.client.put(f'/api/v1/users/{self.patient_user.id}/change-password/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = User.objects.get(id=self.patient_user.id)
        self.assertTrue(user.check_password('NewPass123!'))

    def test_change_password_admin(self):
        self.authenticate_client(self.admin_user)
        data = {
            'newPassword': 'NewPass123!',
            'adminReset': True
        }
        response = self.client.put(f'/api/v1/users/{self.patient_user.id}/change-password/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = User.objects.get(id=self.patient_user.id)
        self.assertTrue(user.check_password('NewPass123!'))

    def test_change_password_invalid_old_password(self):
        self.authenticate_client(self.patient_user)
        data = {
            'oldPassword': 'WrongPass123!',
            'newPassword': 'NewPass123!',
            'adminReset': False
        }
        response = self.client.put(f'/api/v1/users/{self.patient_user.id}/change-password/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(str(response.data[0]), _('Mật khẩu cũ không đúng'))
    
    def test_register(self):
        data = {
            'email': 'newuser@example.com',
            'phone': '0999999999',
            'password': 'NewPass123!',
            'fullName': 'New User',
            'identityNumber': '987654321012',
            'insuranceNumber': 'INS654321',
            'birthday': '1995-05-05',
            'gender': Gender.FEMALE.value,
            'address': '456 Elm St'
        }
        response = self.client.post('/api/v1/auth/register/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], _('OTP đã được gửi tới %(email)s') % {'email': 'newuser@example.com'})

    def test_register_duplicate_email(self):
        data = {
            'email': 'patient@example.com',
            'phone': '0999999999',
            'password': 'NewPass123!',
            'fullName': 'New User',
            'identityNumber': '987654321012',
            'insuranceNumber': 'INS654321',
            'birthday': '1995-05-05',
            'gender': Gender.FEMALE.value,
            'address': '456 Elm St'
        }
        response = self.client.post('/api/v1/auth/register/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(str(response.data[0]), _('Email đã được sử dụng'))

    def test_verify_registration(self):
        data = {
            'email': 'newuser@example.com',
            'phone': '0999999999',
            'password': 'NewPass123!',
            'fullName': 'New User',
            'identityNumber': '987654321012',
            'insuranceNumber': 'INS654321',
            'birthday': '1995-05-05',
            'gender': Gender.FEMALE.value,
            'address': '456 Elm St'
        }
        with patch('users.services.send_mail', new=MockEmailSend()):
            response = self.client.post('/api/v1/auth/register/', data, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        otp = OtpService.otp_storage['newuser@example.com']['otp']
        verify_data = {
            'email': 'newuser@example.com',
            'otp': otp
        }
        response = self.client.post('/api/v1/auth/register/verify/', verify_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['role'], UserRole.PATIENT.value)

    def test_verify_invalid_otp(self):
        data = {
            'email': 'newuser@example.com',
            'phone': '0999999999',
            'password': 'NewPass123!',
            'fullName': 'New User',
            'identityNumber': '987654321012',
            'insuranceNumber': 'INS654321',
            'birthday': '1995-05-05',
            'gender': Gender.FEMALE.value,
            'address': '456 Elm St'
        }
        with patch('users.services.send_mail', new=MockEmailSend()):
            response = self.client.post('/api/v1/auth/register/', data, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        verify_data = {
            'email': 'newuser@example.com',
            'otp': 'wrong_otp'
        }
        response = self.client.post('/api/v1/auth/verify-otp/', verify_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_email(self):
        data = {
            'email': 'patient@example.com',
            'password': 'PatientPass123!'
        }
        response = self.client.post('/api/v1/auth/login/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_login_phone(self):
        data = {
            'phone': '0112233445',
            'password': 'PatientPass123!'
        }
        response = self.client.post('/api/v1/auth/login/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_login_invalid_credentials(self):
        data = {
            'email': 'patient@example.com',
            'password': 'WrongPass123!'
        }
        response = self.client.post('/api/v1/auth/login/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(str(response.data[0]), _('Email/Số điện thoại hoặc mật khẩu không chính xác'))

    @patch('users.services.send_mail', new=MockEmailSend())
    def test_forgot_password_email(self):
        data = {
            'email': 'patient@example.com'
        }
        response = self.client.post('/api/v1/auth/forgot-password/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], _('Mã OTP đã được gửi đến email của bạn'))

    def test_forgot_password_email_nonexistent(self):
        data = {
            'email': 'nonexistent@example.com'
        }
        response = self.client.post('/api/v1/auth/forgot-password/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('users.services.send_mail', new=MockEmailSend())
    def test_forgot_password_otp(self):
        data = {
            'email': 'patient@example.com'
        }
        response = self.client.post('/api/v1/auth/forgot-password/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], _('Mã OTP đã được gửi đến email của bạn'))

    @patch('users.services.send_mail', new=MockEmailSend())
    def test_resend_otp(self):
        data = {
            'email': 'newuser@example.com',
            'phone': '0999999999',
            'password': 'NewPass123!',
            'fullName': 'New User',
            'identityNumber': '987654321012',
            'insuranceNumber': 'INS654321',
            'birthday': '1995-05-05',
            'gender': Gender.FEMALE.value,
            'address': '456 Elm St'
        }
        with patch('users.services.send_mail', new=MockEmailSend()):
            response = self.client.post('/api/v1/auth/register/', data, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        resend_data = {
            'email': 'newuser@example.com'
        }
        response = self.client.post('/api/v1/auth/register/resend-otp/', resend_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], _('OTP đã được gửi lại tới %(email)s') % {'email': 'newuser@example.com'})

    @patch('users.services.send_mail', new=MockEmailSend())
    def test_verify_otp(self):
        data = {
            'email': 'patient@example.com'
        }
        response = self.client.post('/api/v1/auth/forgot-password/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        otp = OtpService.otp_storage['patient@example.com']['otp']
        verify_data = {
            'email': 'patient@example.com',
            'otp': otp
        }
        response = self.client.post('/api/v1/auth/verify-otp/', verify_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], _('Xác minh OTP thành công'))
        self.assertIn('resetToken', response.data)

    @patch('users.services.send_mail', new=MockEmailSend())
    def test_verify_otp_invalid(self):
        data = {
            'email': 'patient@example.com'
        }
        response = self.client.post('/api/v1/auth/forgot-password/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], _('Mã OTP đã được gửi đến email của bạn'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        verify_data = {
            'email': 'patient@example.com',
            'otp': 'wrong_otp'
        }
        response = self.client.post('/api/v1/auth/verify-otp/', verify_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
