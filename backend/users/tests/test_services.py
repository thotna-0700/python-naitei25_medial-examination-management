from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.mail import send_mail
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import AccessToken
from unittest.mock import patch
from datetime import datetime, timedelta, date
from users.services import JwtService, AuthService, ResetTokenService, OtpService, UserService
from patients.models import Patient
from doctors.models import Doctor
from common.enums import UserRole, Gender
from common.constants import COMMON_LENGTH

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

class ServicesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='test@example.com',
            phone='0987654321',
            password='TestPass123!',
            role=UserRole.PATIENT.value
        )
        cls.patient = Patient.objects.create(
            user=cls.user,
            first_name='Test',
            last_name='Patient',
            identity_number='123456789012',
            insurance_number='INS123456',
            birthday=date(1990, 1, 1),
            gender=Gender.MALE.value,
            address='123 Main St'
        )
        cls.admin_user = User.objects.create_user(
            email='admin@example.com',
            phone='0123456789',
            password='AdminPass123!',
            role=UserRole.ADMIN.value
        )
        cls.service = UserService()

    def setUp(self):
        AuthService.pending_registrations = {}
        AuthService.pending_expirations = {}
        OtpService.otp_storage = {}
        ResetTokenService.reset_tokens = {}

    def test_jwt_service_generate_token(self):
        token_data = JwtService.generate_token(self.user)
        self.assertIn('access', token_data)
        self.assertIn('refresh', token_data)
        refresh = AccessToken(token_data['access'])
        self.assertEqual(refresh['role'], self.user.role)
        self.assertEqual(refresh['userId'], str(self.user.id))

    @patch('users.services.send_mail', new=MockEmailSend())
    def test_auth_service_pre_register_valid(self):
        data = {
            'email': 'newuser@example.com',
            'phone': '0112233445',
            'password': 'NewPass123!',
            'fullName': 'New User',
            'identityNumber': '987654321012',
            'insuranceNumber': 'INS654321',
            'birthday': date(1995, 5, 5),
            'gender': Gender.FEMALE.value,
            'address': '456 Elm St'
        }
        message = AuthService().pre_register(data)
        self.assertEqual(message, _("Mã OTP đã được gửi đến email của bạn"))
        self.assertIn('newuser@example.com', AuthService.pending_registrations)
        self.assertEqual(AuthService.pending_registrations['newuser@example.com'], data)
        self.assertTrue(AuthService.pending_expirations['newuser@example.com'] > datetime.now())
        self.assertEqual(len(OtpService.otp_storage), 1)
        self.assertIn('newuser@example.com', OtpService.otp_storage)

    @patch('users.services.send_mail', new=MockEmailSend())
    def test_auth_service_pre_register_duplicate_email(self):
        data = {
            'email': 'test@example.com',  # Existing email
            'phone': '0112233445',
            'password': 'NewPass123!',
            'fullName': 'New User',
            'identityNumber': '987654321012',
            'insuranceNumber': 'INS654321',
            'birthday': date(1995, 5, 5),
            'gender': Gender.FEMALE.value,
            'address': '456 Elm St'
        }
        with self.assertRaisesMessage(ValidationError, _("Email đã được sử dụng")):
            AuthService().pre_register(data)

    @patch('users.services.send_mail', new=MockEmailSend())
    def test_auth_service_pre_register_duplicate_phone(self):
        data = {
            'email': 'newuser@example.com',
            'phone': '0987654321',  # Existing phone
            'password': 'NewPass123!',
            'fullName': 'New User',
            'identityNumber': '987654321012',
            'insuranceNumber': 'INS654321',
            'birthday': date(1995, 5, 5),
            'gender': Gender.FEMALE.value,
            'address': '456 Elm St'
        }
        with self.assertRaisesMessage(ValidationError, _("Số điện thoại đã được sử dụng")):
            AuthService().pre_register(data)

    @patch('users.services.send_mail', new=MockEmailSend())
    def test_auth_service_pre_register_invalid_gender(self):
        data = {
            'email': 'newuser@example.com',
            'phone': '0112233445',
            'password': 'NewPass123!',
            'fullName': 'New User',
            'identityNumber': '987654321012',
            'insuranceNumber': 'INS654321',
            'birthday': date(1995, 5, 5),
            'gender': 'X',  # Invalid gender
            'address': '456 Elm St'
        }
        with self.assertRaisesMessage(ValidationError, _("Giới tính không hợp lệ. Chỉ chấp nhận: M, F, O")):
            AuthService().pre_register(data)

    @patch('users.services.send_mail', new=MockEmailSend())
    def test_auth_service_complete_registration_valid(self):
        data = {
            'email': 'newuser@example.com',
            'phone': '0112233445',
            'password': 'NewPass123!',
            'fullName': 'New User',
            'identityNumber': '987654321012',
            'insuranceNumber': 'INS654321',
            'birthday': date(1995, 5, 5),
            'gender': Gender.FEMALE.value,
            'address': '456 Elm St'
        }
        AuthService().pre_register(data)
        complete_data = {
            'email': 'newuser@example.com',
            'otp': OtpService.otp_storage['newuser@example.com']['otp']
        }
        result = AuthService.complete_registration(complete_data)
        self.assertEqual(result['role'], UserRole.PATIENT.value)
        user = User.objects.get(email='newuser@example.com')
        self.assertTrue(user.is_verified)
        self.assertEqual(user.phone, '0112233445')
        patient = Patient.objects.get(user=user)
        self.assertEqual(patient.first_name, 'New')
        self.assertEqual(patient.last_name, 'User')
        self.assertEqual(patient.identity_number, '987654321012')
        self.assertEqual(patient.gender, Gender.FEMALE.value)
        self.assertNotIn('newuser@example.com', AuthService.pending_registrations)
        self.assertNotIn('newuser@example.com', OtpService.otp_storage)

    @patch('users.services.send_mail', new=MockEmailSend())
    def test_auth_service_complete_registration_invalid_otp(self):
        data = {
            'email': 'newuser@example.com',
            'phone': '0112233445',
            'password': 'NewPass123!',
            'fullName': 'New User',
            'identityNumber': '987654321012',
            'insuranceNumber': 'INS654321',
            'birthday': date(1995, 5, 5),
            'gender': Gender.FEMALE.value,
            'address': '456 Elm St'
        }
        AuthService().pre_register(data)
        complete_data = {
            'email': 'newuser@example.com',
            'otp': 'wrong_otp'
        }
        with self.assertRaisesMessage(ValidationError, _("Mã OTP không đúng")):
            AuthService.complete_registration(complete_data)

    @patch('users.services.send_mail', new=MockEmailSend())
    def test_auth_service_complete_registration_expired(self):
        data = {
            'email': 'newuser@example.com',
            'phone': '0112233445',
            'password': 'NewPass123!',
            'fullName': 'New User',
            'identityNumber': '987654321012',
            'insuranceNumber': 'INS654321',
            'birthday': date(1995, 5, 5),
            'gender': Gender.FEMALE.value,
            'address': '456 Elm St'
        }
        AuthService().pre_register(data)
        AuthService.pending_expirations['newuser@example.com'] = datetime.now() - timedelta(minutes=1)
        complete_data = {
            'email': 'newuser@example.com',
            'otp': OtpService.otp_storage['newuser@example.com']['otp']
        }
        with self.assertRaisesMessage(ValidationError, _("Thông tin đăng ký không tìm thấy hoặc đã hết hạn")):
            AuthService.complete_registration(complete_data)

    def test_auth_service_cleanup_expired_registrations(self):
        data = {
            'email': 'newuser@example.com',
            'phone': '0112233445',
            'password': 'NewPass123!',
            'fullName': 'New User',
            'identityNumber': '987654321012',
            'insuranceNumber': 'INS654321',
            'birthday': date(1995, 5, 5),
            'gender': Gender.FEMALE.value,
            'address': '456 Elm St'
        }
        AuthService().pre_register(data)
        AuthService.pending_expirations['newuser@example.com'] = datetime.now() - timedelta(minutes=1)
        AuthService._cleanup_expired_registrations()
        self.assertNotIn('newuser@example.com', AuthService.pending_registrations)
        self.assertNotIn('newuser@example.com', AuthService.pending_expirations)

    def test_auth_service_login_valid_email(self):
        data = {
            'email': 'test@example.com',
            'password': 'TestPass123!'
        }
        result = AuthService().login(data)
        self.assertIn('token', result)
        access_token = AccessToken(result['token'])
        self.assertEqual(str(access_token['userId']), str(self.user.id))
        self.assertEqual(access_token['role'], self.user.role)

    def test_auth_service_login_valid_phone(self):
        data = {
            'phone': '0987654321',
            'password': 'TestPass123!'
        }
        result = AuthService().login(data)
        self.assertIn('token', result)
        access_token = AccessToken(result['token'])
        self.assertEqual(str(access_token['userId']), str(self.user.id))
        self.assertEqual(access_token['role'], self.user.role)

    def test_auth_service_login_invalid_credentials(self):
        data = {
            'email': 'test@example.com',
            'password': 'WrongPass123!'
        }
        with self.assertRaisesMessage(ValidationError, _("Email/Số điện thoại hoặc mật khẩu không chính xác")):
            AuthService().login(data)

    def test_auth_service_login_missing_identifier(self):
        data = {
            'password': 'TestPass123!'
        }
        with self.assertRaisesMessage(ValidationError, _("Vui lòng cung cấp email hoặc số điện thoại")):
            AuthService().login(data)

    @patch('users.services.send_mail', new=MockEmailSend())
    def test_auth_service_send_reset_password_email(self):
        result = AuthService().send_reset_password_email('test@example.com')
        self.assertEqual(result['message'], _("Email đặt lại mật khẩu đã được gửi"))
        self.assertEqual(len(ResetTokenService.reset_tokens), 1)
        token = list(ResetTokenService.reset_tokens.keys())[0]
        token_data = ResetTokenService.reset_tokens[token]
        self.assertEqual(token_data['user_id'], self.user.id)
        self.assertTrue(token_data['expires'] > datetime.now())

    @patch('users.services.send_mail', new=MockEmailSend())
    def test_auth_service_send_reset_password_email_nonexistent_user(self):
        with self.assertRaises(Http404):
            AuthService().send_reset_password_email('nonexistent@example.com')

    @patch('users.services.send_mail', new=MockEmailSend())
    def test_auth_service_send_reset_password_otp(self):
        result = AuthService().send_reset_password_otp('test@example.com')
        self.assertEqual(result['message'], _("Mã OTP đã được gửi đến email của bạn"))
        self.assertIn('test@example.com', OtpService.otp_storage)

    @patch('users.services.send_mail', new=MockEmailSend())
    def test_auth_service_send_reset_password_otp_nonexistent_user(self):
        with self.assertRaises(Http404):
            AuthService().send_reset_password_otp('nonexistent@example.com')

    @patch('users.services.send_mail', new=MockEmailSend())
    def test_auth_service_resend_otp(self):
        data = {
            'email': 'newuser@example.com',
            'phone': '0112233445',
            'password': 'NewPass123!',
            'fullName': 'New User',
            'identityNumber': '987654321012',
            'insuranceNumber': 'INS654321',
            'birthday': date(1995, 5, 5),
            'gender': Gender.FEMALE.value,
            'address': '456 Elm St'
        }
        AuthService().pre_register(data)
        message = AuthService().resend_otp('newuser@example.com')
        self.assertEqual(message, _("Mã OTP đã được gửi lại đến email của bạn"))
        self.assertIn('newuser@example.com', OtpService.otp_storage)

    @patch('users.services.send_mail', new=MockEmailSend())
    def test_auth_service_resend_otp_no_pending_registration(self):
        with self.assertRaisesMessage(ValidationError, _("Không tìm thấy thông tin đăng ký hoặc đã hết hạn")):
            AuthService().resend_otp('newuser@example.com')

    @patch('users.services.send_mail', new=MockEmailSend())
    def test_auth_service_reset_password_valid(self):
        token = ResetTokenService.generate_reset_token(self.user)
        data = {
            'resetToken': token,
            'password': 'NewPass123!'
        }
        result = AuthService().reset_password(data)
        self.assertEqual(result['message'], _("Đặt lại mật khẩu thành công"))
        user = User.objects.get(id=self.user.id)
        self.assertTrue(user.check_password('NewPass123!'))
        self.assertNotIn(token, ResetTokenService.reset_tokens)

    def test_auth_service_reset_password_invalid_token(self):
        data = {
            'resetToken': 'invalid_token',
            'password': 'NewPass123!'
        }
        with self.assertRaisesMessage(ValidationError, _("Mã đặt lại mật khẩu không hợp lệ hoặc đã hết hạn")):
            AuthService().reset_password(data)

    def test_reset_token_service_generate_reset_token(self):
        token = ResetTokenService.generate_reset_token(self.user)
        self.assertIn(token, ResetTokenService.reset_tokens)
        self.assertEqual(ResetTokenService.reset_tokens[token]['user_id'], self.user.id)
        self.assertTrue(ResetTokenService.reset_tokens[token]['expires'] > datetime.now())

    def test_reset_token_service_validate_reset_token_valid(self):
        token = ResetTokenService.generate_reset_token(self.user)
        user = ResetTokenService.validate_reset_token(token)
        self.assertEqual(user.id, self.user.id)

    def test_reset_token_service_validate_reset_token_expired(self):
        token = ResetTokenService.generate_reset_token(self.user)
        ResetTokenService.reset_tokens[token]['expires'] = datetime.now() - timedelta(minutes=1)
        user = ResetTokenService.validate_reset_token(token)
        self.assertIsNone(user)
        self.assertNotIn(token, ResetTokenService.reset_tokens)

    def test_reset_token_service_remove_reset_token(self):
        token = ResetTokenService.generate_reset_token(self.user)
        ResetTokenService.remove_reset_token(token)
        self.assertNotIn(token, ResetTokenService.reset_tokens)

    @patch('users.services.send_mail', new=MockEmailSend())
    def test_otp_service_generate_and_send_otp(self):
        OtpService.send_otp_to_email('test@example.com')
        self.assertIn('test@example.com', OtpService.otp_storage)
        otp_data = OtpService.otp_storage['test@example.com']
        self.assertEqual(len(otp_data['otp']), 6)
        self.assertTrue(otp_data['expires'] > datetime.now())

    def test_otp_service_validate_otp_valid(self):
        OtpService.send_otp_to_email('test@example.com')
        otp = OtpService.otp_storage['test@example.com']['otp']
        result = OtpService.validate_otp_by_email('test@example.com', otp)
        self.assertEqual(result['resetToken'], 'SUCCESS')
        self.assertNotIn('test@example.com', OtpService.otp_storage)

    def test_otp_service_validate_otp_invalid(self):
        OtpService.send_otp_to_email('test@example.com')
        result = OtpService.validate_otp_by_email('test@example.com', 'wrong_otp')
        self.assertEqual(result['resetToken'], _("Mã OTP không đúng"))

    def test_otp_service_cleanup_expired_otps(self):
        OtpService.send_otp_to_email('test@example.com')
        OtpService.otp_storage['test@example.com']['expires'] = datetime.now() - timedelta(minutes=1)
        OtpService._cleanup_expired_otps()
        self.assertNotIn('test@example.com', OtpService.otp_storage)

    def test_user_service_get_all_users(self):
        result = self.service.get_all_users(page=0, size=10)
        self.assertEqual(len(result['content']), 2)
        self.assertEqual(result['page'], 0)
        self.assertEqual(result['size'], 10)
        self.assertEqual(result['totalElements'], 2)
        self.assertEqual(result['totalPages'], 1)
        self.assertTrue(result['last'])
        self.assertEqual(result['content'][0]['id'], self.admin_user.id)  # Ordered by -created_at

    def test_user_service_get_user_by_id(self):
        result = self.service.get_user_by_id(self.user.id)
        self.assertEqual(result['id'], self.user.id)
        self.assertEqual(result['email'], 'test@example.com')
        self.assertEqual(result['role'], UserRole.PATIENT.value)

    def test_user_service_get_user_by_id_not_found(self):
        with self.assertRaises(Http404):
            self.service.get_user_by_id(999)

    def test_user_service_add_user_valid(self):
        data = {
            'email': 'newuser@example.com',
            'phone': '0112233445',
            'password': 'NewPass123!',
            'role': UserRole.DOCTOR.value
        }
        result = self.service.add_user(data)
        user = User.objects.get(email='newuser@example.com')
        self.assertEqual(result['email'], 'newuser@example.com')
        self.assertEqual(result['phone'], '0112233445')
        self.assertEqual(result['role'], UserRole.DOCTOR.value)
        self.assertTrue(user.check_password('NewPass123!'))

    def test_user_service_add_user_duplicate_email(self):
        data = {
            'email': 'test@example.com',
            'phone': '0112233445',
            'password': 'NewPass123!',
            'role': UserRole.PATIENT.value
        }
        with self.assertRaisesMessage(ValidationError, _("Email đã được sử dụng")):
            self.service.add_user(data)

    def test_user_service_edit_user_valid(self):
        data = {
            'email': 'updated@example.com',
            'phone': '0112233447',
            'role': UserRole.DOCTOR.value
        }
        result = self.service.edit_user(self.user.id, data)
        user = User.objects.get(id=self.user.id)
        self.assertEqual(result['email'], 'updated@example.com')
        self.assertEqual(user.email, 'updated@example.com')
        self.assertEqual(user.phone, '0112233447')
        self.assertEqual(user.role, UserRole.DOCTOR.value)

    def test_user_service_edit_user_duplicate_email(self):
        User.objects.create_user(
            email='other@example.com',
            password='OtherPass123!',
            role=UserRole.PATIENT.value
        )
        data = {
            'email': 'other@example.com'
        }
        with self.assertRaisesMessage(ValidationError, _("Email đã được sử dụng")):
            self.service.edit_user(self.user.id, data)

    def test_user_service_edit_user_password(self):
        data = {
            'password': 'UpdatedPass123!'
        }
        result = self.service.edit_user(self.user.id, data)
        user = User.objects.get(id=self.user.id)
        self.assertTrue(user.check_password('UpdatedPass123!'))
        self.assertEqual(result['id'], self.user.id)

    def test_user_service_delete_user_with_patient(self):
        with self.assertRaisesMessage(ValidationError, _("Không thể xóa người dùng này vì còn liên kết với: Bệnh nhân")):
            self.service.delete_user(self.user.id)

    def test_user_service_delete_user_no_relations(self):
        user = User.objects.create_user(
            email='norel@example.com',
            password='NoRelPass123!',
            role=UserRole.PATIENT.value
        )
        result = self.service.delete_user(user.id)
        user.refresh_from_db()
        self.assertTrue(user.is_deleted)
        self.assertFalse(user.is_active)
        self.assertIsNotNone(user.deleted_at)
        self.assertEqual(result['message'], _("Xóa người dùng thành công (soft delete)"))

    def test_user_service_force_delete_user(self):
        user = User.objects.create_user(
            email='force_delete@example.com',
            phone='0112233446',
            password='ForcePass123!',
            role=UserRole.PATIENT.value
        )
        result = self.service.force_delete_user(user.id)
        self.assertEqual(result['message'], _("Xóa người dùng thành công (soft delete)"))
        user = User.objects.all_with_deleted().get(id=user.id)
        self.assertTrue(user.is_deleted)
        self.assertFalse(user.is_active)
        self.assertIsNotNone(user.deleted_at)

    def test_user_service_restore_user_not_deleted(self):
        with self.assertRaises(Http404):
            self.service.restore_user(self.user.id)

    def test_user_service_change_password_self(self):
        data = {
            'oldPassword': 'TestPass123!',
            'newPassword': 'NewPass123!',
            'adminReset': False
        }
        self.service.change_password(self.user.id, data, UserRole.PATIENT.value, self.user.id)
        user = User.objects.get(id=self.user.id)
        self.assertTrue(user.check_password('NewPass123!'))
        self.assertFalse(user.check_password('TestPass123!'))

    def test_user_service_change_password_admin_reset(self):
        data = {
            'newPassword': 'NewPass123!',
            'adminReset': True
        }
        self.service.change_password(self.user.id, data, UserRole.ADMIN.value, self.admin_user.id)
        user = User.objects.get(id=self.user.id)
        self.assertTrue(user.check_password('NewPass123!'))

    def test_user_service_change_password_invalid_old_password(self):
        data = {
            'oldPassword': 'WrongPass123!',
            'newPassword': 'NewPass123!',
            'adminReset': False
        }
        with self.assertRaisesMessage(ValidationError, _("Mật khẩu cũ không đúng")):
            self.service.change_password(self.user.id, data, UserRole.PATIENT.value, self.user.id)

    def test_user_service_change_password_no_old_password(self):
        data = {
            'newPassword': 'NewPass123!',
            'adminReset': False
        }
        with self.assertRaisesMessage(ValidationError, _("Mật khẩu cũ không được để trống")):
            self.service.change_password(self.user.id, data, UserRole.PATIENT.value, self.user.id)

    def test_user_service_change_password_unauthorized(self):
        other_user = User.objects.create_user(
            email='other@example.com',
            password='OtherPass123!',
            role=UserRole.PATIENT.value
        )
        data = {
            'newPassword': 'NewPass123!',
            'adminReset': False
        }
        with self.assertRaisesMessage(ValidationError, _("Không có quyền thực hiện thao tác này")):
            self.service.change_password(self.user.id, data, UserRole.PATIENT.value, other_user.id)
