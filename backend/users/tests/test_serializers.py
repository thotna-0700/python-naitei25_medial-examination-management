from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.utils.translation import gettext as _
from users.serializers import (
    UserRequestSerializer, UserUpdateRequestSerializer, UserResponseSerializer,
    PagedResponseSerializer, ChangePasswordRequestSerializer, RegisterRequestSerializer,
    RegisterVerifyRequestSerializer, LoginFlexibleRequestSerializer,
    ResetPasswordRequestSerializer, ForgotPasswordEmailRequestSerializer,
    ResendOtpRequestSerializer, VerifyOtpRequestSerializer, LoginResponseSerializer
)
from common.enums import UserRole, Gender
from common.constants import USER_LENGTH, COMMON_LENGTH, REGEX_PATTERNS
from datetime import date, datetime

User = get_user_model()

class SerializerTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='test@example.com',
            phone='0987654321',
            password='TestPass123!',
            role=UserRole.PATIENT.value
        )

    def test_user_request_serializer_valid(self):
        data = {
            'email': 'newuser@example.com',
            'phone': '0123456789',
            'password': 'NewPass123!',
            'role': UserRole.DOCTOR.value
        }
        serializer = UserRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data, data)

    def test_user_request_serializer_missing_email_and_phone(self):
        data = {
            'password': 'TestPass123!'
        }
        serializer = UserRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
        self.assertIn('phone', serializer.errors)
        self.assertEqual(serializer.errors['email'][0], _("Phải cung cấp email hoặc số điện thoại"))
        self.assertEqual(serializer.errors['phone'][0], _("Phải cung cấp email hoặc số điện thoại"))

    def test_user_request_serializer_missing_password(self):
        data = {
            'email': 'newuser@example.com'
        }
        serializer = UserRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)
        self.assertEqual(serializer.errors['password'][0], _("Trường này là bắt buộc."))

    def test_user_request_serializer_invalid_phone(self):
        data = {
            'email': 'newuser@example.com',
            'phone': 'invalid_phone',
            'password': 'TestPass123!'
        }
        serializer = UserRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('phone', serializer.errors)
        self.assertEqual(serializer.errors['phone'][0], _("Số điện thoại không hợp lệ"))

    def test_user_update_request_serializer_valid(self):
        data = {
            'email': 'updated@example.com',
            'phone': '0123456780',
            'password': 'UpdatedPass123!',
            'role': UserRole.ADMIN.value,
            'is_active': False,
            'is_verified': True
        }
        serializer = UserUpdateRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data, data)

    def test_user_update_request_serializer_partial(self):
        data = {
            'email': 'partial@example.com'
        }
        serializer = UserUpdateRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data, data)

    def test_user_response_serializer(self):
        serializer = UserResponseSerializer(instance=self.user)
        expected_data = {
            'id': self.user.id,
            'created_at': self.user.created_at,
            'updated_at': self.user.updated_at,
            'email': 'test@example.com',
            'password': self.user.password,  # Hashed password
            'phone': '0987654321',
            'role': UserRole.PATIENT.value,
            'is_active': True,
            'is_verified': False,
            'is_deleted': False,
            'deleted_at': None
        }
        self.assertEqual(serializer.data['id'], expected_data['id'])
        self.assertEqual(serializer.data['email'], expected_data['email'])
        self.assertEqual(serializer.data['phone'], expected_data['phone'])
        self.assertEqual(serializer.data['role'], expected_data['role'])
        self.assertEqual(serializer.data['is_active'], expected_data['is_active'])
        self.assertEqual(serializer.data['is_verified'], expected_data['is_verified'])
        self.assertEqual(serializer.data['is_deleted'], expected_data['is_deleted'])

    def test_paged_response_serializer(self):
        instance = {
            "content": [self.user],
            "page": 1,
            "size": 10,
            "totalElements": 1,
            "totalPages": 1,
            "last": True,
        }
        serializer = PagedResponseSerializer(instance)
        result = serializer.data

        self.assertEqual(result["page"], 1)
        self.assertEqual(result["size"], 10)
        self.assertEqual(result["totalElements"], 1)
        self.assertEqual(result["totalPages"], 1)
        self.assertTrue(result["last"])
        self.assertEqual(len(result["content"]), 1)
        self.assertEqual(result["content"][0]["id"], self.user.id)

    def test_change_password_request_serializer_valid(self):
        data = {
            'oldPassword': 'TestPass123!',
            'newPassword': 'NewPass123!',
            'adminReset': False
        }
        serializer = ChangePasswordRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data, data)

    def test_change_password_request_serializer_missing_new_password(self):
        data = {
            'oldPassword': 'TestPass123!',
            'adminReset': False
        }
        serializer = ChangePasswordRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('newPassword', serializer.errors)
        self.assertEqual(serializer.errors['newPassword'][0], _("Trường này là bắt buộc."))

    def test_register_request_serializer_valid(self):
        data = {
            'password': 'TestPass123!',
            'email': 'register@example.com',
            'phone': '0123456789',
            'fullName': 'Test User',
            'identityNumber': '123456789012',
            'insuranceNumber': 'INS123456',
            'birthday': '1990-01-01',
            'gender': Gender.MALE.value,
            'address': '123 Main St'
        }
        serializer = RegisterRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        validated_data = serializer.validated_data
        self.assertEqual(validated_data['password'], data['password'])
        self.assertEqual(validated_data['email'], data['email'])
        self.assertEqual(validated_data['phone'], data['phone'])
        self.assertEqual(validated_data['fullName'], data['fullName'])
        self.assertEqual(validated_data['identityNumber'], data['identityNumber'])
        self.assertEqual(validated_data['insuranceNumber'], data['insuranceNumber'])
        self.assertEqual(validated_data['gender'], data['gender'])
        self.assertEqual(validated_data['address'], data['address'])
        self.assertEqual(validated_data['birthday'].isoformat(), data['birthday'])

    def test_register_request_serializer_invalid_identity_number(self):
        data = {
            'password': 'TestPass123!',
            'email': 'register@example.com',
            'fullName': 'Test User',
            'identityNumber': 'invalid_id',
            'insuranceNumber': 'INS123456',
            'birthday': '1990-01-01',
            'gender': Gender.MALE.value,
            'address': '123 Main St'
        }
        serializer = RegisterRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('identityNumber', serializer.errors)
        self.assertEqual(serializer.errors['identityNumber'][0], _("CCCD phải có đúng 12 chữ số"))

    def test_register_verify_request_serializer_valid(self):
        data = {
            'email': 'register@example.com',
            'otp': '123456'
        }
        serializer = RegisterVerifyRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data, data)

    def test_register_verify_request_serializer_missing_fields(self):
        data = {}
        serializer = RegisterVerifyRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
        self.assertIn('otp', serializer.errors)
        self.assertEqual(serializer.errors['email'][0], _("Trường này là bắt buộc."))
        self.assertEqual(serializer.errors['otp'][0], _("Trường này là bắt buộc."))

    def test_login_flexible_request_serializer_valid_email(self):
        data = {
            'email': 'login@example.com',
            'password': 'LoginPass123!'
        }
        serializer = LoginFlexibleRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data, data)

    def test_login_flexible_request_serializer_valid_phone(self):
        data = {
            'phone': '0123456789',
            'password': 'LoginPass123!'
        }
        serializer = LoginFlexibleRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data, data)

    def test_login_flexible_request_serializer_missing_email_and_phone(self):
        data = {
            'password': 'LoginPass123!'
        }
        serializer = LoginFlexibleRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
        self.assertIn('phone', serializer.errors)
        self.assertEqual(serializer.errors['email'][0], _("Phải cung cấp email hoặc số điện thoại"))
        self.assertEqual(serializer.errors['phone'][0], _("Phải cung cấp email hoặc số điện thoại"))

    def test_reset_password_request_serializer_valid(self):
        data = {
            'resetToken': 'abc123',
            'password': 'NewPass123!'
        }
        serializer = ResetPasswordRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data, data)

    def test_reset_password_request_serializer_missing_fields(self):
        data = {}
        serializer = ResetPasswordRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('resetToken', serializer.errors)
        self.assertIn('password', serializer.errors)
        self.assertEqual(serializer.errors['resetToken'][0], _("Trường này là bắt buộc."))
        self.assertEqual(serializer.errors['password'][0], _("Trường này là bắt buộc."))

    def test_forgot_password_email_request_serializer_valid(self):
        data = {
            'email': 'forgot@example.com'
        }
        serializer = ForgotPasswordEmailRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data, data)

    def test_forgot_password_email_request_serializer_missing_email(self):
        data = {}
        serializer = ForgotPasswordEmailRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
        self.assertEqual(serializer.errors['email'][0], _("Trường này là bắt buộc."))

    def test_resend_otp_request_serializer_valid(self):
        data = {
            'email': 'resend@example.com'
        }
        serializer = ResendOtpRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data, data)

    def test_resend_otp_request_serializer_missing_email(self):
        data = {}
        serializer = ResendOtpRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
        self.assertEqual(serializer.errors['email'][0], _("Trường này là bắt buộc."))

    def test_verify_otp_request_serializer_valid(self):
        data = {
            'email': 'verify@example.com',
            'otp': '123456'
        }
        serializer = VerifyOtpRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data, data)

    def test_verify_otp_request_serializer_missing_fields(self):
        data = {}
        serializer = VerifyOtpRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
        self.assertIn('otp', serializer.errors)
        self.assertEqual(serializer.errors['email'][0], _("Trường này là bắt buộc."))
        self.assertEqual(serializer.errors['otp'][0], _("Trường này là bắt buộc."))

    def test_login_response_serializer_valid(self):
        data = {
            'token': 'jwt_token_string'
        }
        serializer = LoginResponseSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data, data)
