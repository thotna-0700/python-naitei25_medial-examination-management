from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext as _
from common.enums import UserRole
from common.constants import REGEX_PATTERNS

User = get_user_model()

class UserModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_data = {
            'email': 'test@example.com',
            'phone': '0987654321',
            'password': 'TestPass123!',
            'role': UserRole.PATIENT.value
        }
        cls.user = User.objects.create_user(
            email=cls.user_data['email'],
            phone=cls.user_data['phone'],
            password=cls.user_data['password'],
            role=cls.user_data['role']
        )

    def test_create_user_with_email_and_phone(self):
        user = User.objects.create_user(
            email='newuser@example.com',
            phone='0123456789',
            password='NewPass123!',
            role=UserRole.DOCTOR.value
        )
        self.assertEqual(user.email, 'newuser@example.com')
        self.assertEqual(user.phone, '0123456789')
        self.assertTrue(user.check_password('NewPass123!'))
        self.assertEqual(user.role, UserRole.DOCTOR.value)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_verified)
        self.assertFalse(user.is_deleted)

    def test_create_user_with_email_only(self):
        user = User.objects.create_user(
            email='emailonly@example.com',
            password='EmailPass123!',
            role=UserRole.PATIENT.value
        )
        self.assertEqual(user.email, 'emailonly@example.com')
        self.assertIsNone(user.phone)
        self.assertTrue(user.check_password('EmailPass123!'))
        self.assertEqual(user.role, UserRole.PATIENT.value)

    def test_create_user_with_phone_only(self):
        user = User.objects.create_user(
            phone='0112233445',
            password='PhonePass123!',
            role=UserRole.PATIENT.value
        )
        self.assertIsNone(user.email)
        self.assertEqual(user.phone, '0112233445')
        self.assertTrue(user.check_password('PhonePass123!'))
        self.assertEqual(user.role, UserRole.PATIENT.value)

    def test_create_user_no_email_or_phone(self):
        with self.assertRaisesMessage(ValueError, _('Email hoặc số điện thoại là bắt buộc')):
            User.objects.create_user(password='NoIdentifier123!')

    def test_email_normalization(self):
        user = User.objects.create_user(
            email='  TESTAAA@EXAMPLE.COM  ',
            password='TestPass123!',
            role=UserRole.PATIENT.value
        )
        self.assertEqual(user.email, 'testaaa@example.com')

    def test_unique_email_constraint(self):
        with self.assertRaises(Exception) as context:
            User.objects.create_user(
                email='test@example.com',  # Duplicate email
                phone='0123456780',
                password='AnotherPass123!'
            )
        self.assertTrue('UNIQUE constraint failed' in str(context.exception) or 'duplicate key value' in str(context.exception))

    def test_unique_phone_constraint(self):
        with self.assertRaises(Exception) as context:
            User.objects.create_user(
                email='another@example.com',
                phone='0987654321',  # Duplicate phone
                password='AnotherPass123!'
            )
        self.assertTrue('UNIQUE constraint failed' in str(context.exception) or 'duplicate key value' in str(context.exception))

    def test_invalid_phone_format(self):
        user = User(
            email='invalidphone@example.com',
            phone='invalid_phone',
            password='TestPass123!'
        )
        with self.assertRaisesMessage(ValidationError, _('Số điện thoại không hợp lệ')):
            user.full_clean()

    def test_set_password(self):
        user = User.objects.get(email='test@example.com')
        user.set_password('NewPass123!')
        user.save()
        self.assertTrue(user.check_password('NewPass123!'))
        self.assertFalse(user.check_password('TestPass123!'))

    def test_check_password(self):
        user = User.objects.get(email='test@example.com')
        self.assertTrue(user.check_password('TestPass123!'))
        self.assertFalse(user.check_password('WrongPass123!'))

    def test_soft_delete(self):
        user = User.objects.get(email='test@example.com')
        user.soft_delete()
        self.assertTrue(user.is_deleted)
        self.assertFalse(user.is_active)
        self.assertIsNotNone(user.deleted_at)
        self.assertFalse(User.objects.filter(email='test@example.com').exists())
        self.assertTrue(User.objects.all_with_deleted().filter(email='test@example.com').exists())

    def test_restore(self):
        user = User.objects.get(email='test@example.com')
        user.soft_delete()
        user.restore()
        self.assertFalse(user.is_deleted)
        self.assertTrue(user.is_active)
        self.assertIsNone(user.deleted_at)
        self.assertTrue(User.objects.filter(email='test@example.com').exists())

    def test_user_manager_get_queryset(self):
        user = User.objects.get(email='test@example.com')
        user.soft_delete()
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(User.objects.all_with_deleted().count(), 1)

    def test_is_staff_property(self):
        admin_user = User.objects.create_user(
            email='admin@example.com',
            password='AdminPass123!',
            role=UserRole.ADMIN.value
        )
        doctor_user = User.objects.create_user(
            email='doctor@example.com',
            password='DoctorPass123!',
            role=UserRole.DOCTOR.value
        )
        patient_user = User.objects.create_user(
            email='patient@example.com',
            password='PatientPass123!',
            role=UserRole.PATIENT.value
        )
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(doctor_user.is_staff)
        self.assertFalse(patient_user.is_staff)

    def test_is_superuser_property(self):
        admin_user = User.objects.create_user(
            email='admin@example.com',
            password='AdminPass123!',
            role=UserRole.ADMIN.value
        )
        doctor_user = User.objects.create_user(
            email='doctor@example.com',
            password='DoctorPass123!',
            role=UserRole.DOCTOR.value
        )
        self.assertTrue(admin_user.is_superuser)
        self.assertFalse(doctor_user.is_superuser)

    def test_is_authenticated_property(self):
        user = User.objects.get(email='test@example.com')
        self.assertTrue(user.is_authenticated)
        self.assertFalse(user.is_anonymous)

    def test_username_property(self):
        user = User.objects.get(email='test@example.com')
        self.assertEqual(user.username, 'test@example.com')
        phone_user = User.objects.create_user(
            phone='0123456780',
            password='PhonePass123!'
        )
        self.assertEqual(phone_user.username, '0123456780')

    def test_get_username(self):
        user = User.objects.get(email='test@example.com')
        self.assertEqual(user.get_username(), 'test@example.com')

    def test_natural_key(self):
        user = User.objects.get(email='test@example.com')
        self.assertEqual(user.natural_key(), ('test@example.com',))
        phone_user = User.objects.create_user(
            phone='0123456780',
            password='PhonePass123!'
        )
        self.assertEqual(phone_user.natural_key(), ('0123456780',))

    def test_get_by_natural_key(self):
        user = User.objects.get_by_natural_key('test@example.com')
        self.assertEqual(user.email, 'test@example.com')

    def test_has_perm(self):
        user = User.objects.get(email='test@example.com')
        self.assertTrue(user.has_perm('some_perm'))

    def test_has_module_perms(self):
        user = User.objects.get(email='test@example.com')
        self.assertTrue(user.has_module_perms('some_app'))

    def test_str_representation(self):
        user = User.objects.get(email='test@example.com')
        self.assertEqual(str(user), 'test@example.com')
        phone_user = User.objects.create_user(
            phone='0123456780',
            password='PhonePass123!'
        )
        self.assertEqual(str(phone_user), '0123456780')

    def test_indexes(self):
        # Verify that indexes exist by checking the Meta class
        indexes = User._meta.indexes
        index_fields = [index.fields for index in indexes]
        expected_indexes = [
            ['is_deleted'],
            ['deleted_at'],
            ['email', 'is_deleted'],
            ['phone', 'is_deleted']
        ]
        for expected in expected_indexes:
            self.assertIn(expected, index_fields)
