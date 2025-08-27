from django.test import TestCase
from django.contrib.auth import get_user_model
from users.managers import ActiveUserManager, AllUserManager

User = get_user_model()

class ActiveUserManagerTests(TestCase):
    def setUp(self):
        self.manager = ActiveUserManager()
        self.manager.model = User

    def test_get_queryset(self):
        # Create test users
        user1 = self.manager.create_user(email="test1@example.com", password="Test123!@#")
        user2 = self.manager.create_user(email="test2@example.com", password="Test123!@#", is_deleted=True)
        
        queryset = self.manager.get_queryset()
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first().email, "test1@example.com")

    def test_create_user_with_email(self):
        user = self.manager.create_user(email="Test@Example.com", password="Test123!@#")
        self.assertEqual(user.email, "test@example.com")  # Check email normalization
        self.assertTrue(user.check_password("Test123!@#"))
        self.assertFalse(user.is_deleted)

    def test_create_user_with_phone(self):
        user = self.manager.create_user(phone="1234567890", password="Test123!@#")
        self.assertEqual(user.phone, "1234567890")
        self.assertTrue(user.check_password("Test123!@#"))
        self.assertFalse(user.is_deleted)

    def test_create_user_no_email_or_phone(self):
        with self.assertRaisesMessage(ValueError, "Email hoặc số điện thoại là bắt buộc"):
            self.manager.create_user()

    def test_normalize_email(self):
        email = "  Test@Example.COM  "
        normalized = self.manager.normalize_email(email)
        self.assertEqual(normalized, "test@example.com")

    def test_normalize_empty_email(self):
        self.assertIsNone(self.manager.normalize_email(None))

class AllUserManagerTests(TestCase):
    def setUp(self):
        self.manager = AllUserManager()
        self.manager.model = User

    def test_get_queryset(self):
        # Create test users
        user1 = self.manager.model.objects.create_user(email="test1@example.com", password="Test123!@#")
        user2 = self.manager.model.objects.create_user(email="test2@example.com", password="Test123!@#", is_deleted=True)
        
        queryset = self.manager.get_queryset()
        self.assertEqual(queryset.count(), 2)
        emails = [user.email for user in queryset]
        self.assertIn("test1@example.com", emails)
        self.assertIn("test2@example.com", emails)
