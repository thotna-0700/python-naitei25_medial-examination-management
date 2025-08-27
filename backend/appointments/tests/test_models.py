from django.test import TestCase
from django.utils import timezone
from datetime import date, time, datetime
from appointments.models import Appointment, AppointmentNote, Service, ServiceOrder
from doctors.models import Doctor, Department, Schedule, ExaminationRoom
from patients.models import Patient
from users.models import User
from common.enums import AppointmentStatus, NoteType, OrderStatus, ServiceType, Gender, AcademicDegree, DoctorType, RoomType, Shift, UserRole
from common.constants import SERVICE_LENGTH, COMMON_LENGTH, DECIMAL_MAX_DIGITS, DECIMAL_DECIMAL_PLACES, ENUM_LENGTH, SCHEDULE_DEFAULTS

class AppointmentModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            role=UserRole.PATIENT.value
        )
        cls.patient = Patient.objects.create(
            user=cls.user,
            first_name='Test',
            last_name='Patient',
            identity_number='111222333',
            insurance_number='INS123456',
            birthday=date(1990, 1, 1),
            gender=Gender.FEMALE.value
        )
        cls.department = Department.objects.create(department_name="Cardiology")
        cls.doctor = Doctor.objects.create(
            user=cls.user,
            first_name="John",
            last_name="Doe",
            identity_number="123456789",
            birthday=date(1980, 1, 1),
            gender=Gender.MALE.value,
            academic_degree=AcademicDegree.BS_CKI.value,
            specialization="Cardiologist",
            type=DoctorType.EXAMINATION.value,
            department=cls.department,
            price=100.00
        )
        cls.room = ExaminationRoom.objects.create(
            department=cls.department,
            type=RoomType.EXAMINATION.value,
            building="A",
            floor=1,
            note="Room 101"
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
            symptoms="Fever and cough",
            note="Initial consultation",
            slot_start=time(8, 0),
            slot_end=time(8, 30),
            status=AppointmentStatus.CONFIRMED.value
        )

    def test_create_appointment(self):
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            schedule=self.schedule,
            symptoms="Headache",
            note="Follow-up",
            slot_start=time(9, 0),
            slot_end=time(9, 30),
            status=AppointmentStatus.PENDING.value
        )
        self.assertEqual(appointment.doctor, self.doctor)
        self.assertEqual(appointment.patient, self.patient)
        self.assertEqual(appointment.schedule, self.schedule)
        self.assertEqual(appointment.symptoms, "Headache")
        self.assertEqual(appointment.note, "Follow-up")
        self.assertEqual(appointment.slot_start, time(9, 0))
        self.assertEqual(appointment.slot_end, time(9, 30))
        self.assertEqual(appointment.status, AppointmentStatus.PENDING.value)
        self.assertIsNotNone(appointment.created_at)

    def test_str_method(self):
        self.assertEqual(str(self.appointment), f"Appointment {self.appointment.pk}")

    def test_required_fields(self):
        with self.assertRaises(Exception):  # IntegrityError for missing required fields
            Appointment.objects.create(
                symptoms="Test symptoms",
                note="Test note",
                slot_start=time(10, 0),
                slot_end=time(10, 30),
                status=AppointmentStatus.CONFIRMED.value
            )

    def test_status_choices(self):
        self.assertIn(self.appointment.status, [status.value for status in AppointmentStatus])

class AppointmentNoteModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            role=UserRole.PATIENT.value
        )
        cls.patient = Patient.objects.create(
            user=cls.user,
            first_name='Test',
            last_name='Patient',
            identity_number='111222333',
            insurance_number='INS123456',
            birthday=date(1990, 1, 1),
            gender=Gender.FEMALE.value
        )
        cls.department = Department.objects.create(department_name="Cardiology")
        cls.doctor = Doctor.objects.create(
            user=cls.user,
            first_name="John",
            last_name="Doe",
            identity_number="123456789",
            birthday=date(1980, 1, 1),
            gender=Gender.MALE.value,
            academic_degree=AcademicDegree.BS_CKI.value,
            specialization="Cardiologist",
            type=DoctorType.EXAMINATION.value,
            department=cls.department,
            price=100.00
        )
        cls.room = ExaminationRoom.objects.create(
            department=cls.department,
            type=RoomType.EXAMINATION.value,
            building="A",
            floor=1,
            note="Room 101"
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
            status=AppointmentStatus.CONFIRMED.value
        )
        cls.note = AppointmentNote.objects.create(
            appointment=cls.appointment,
            note_type=NoteType.DOCTOR.value,
            note_text="Patient diagnosed with flu"
        )

    def test_create_appointment_note(self):
        note = AppointmentNote.objects.create(
            appointment=self.appointment,
            note_type=NoteType.DOCTOR.value,
            note_text="Prescribed antibiotics"
        )
        self.assertEqual(note.appointment, self.appointment)
        self.assertEqual(note.note_type, NoteType.DOCTOR.value)
        self.assertEqual(note.note_text, "Prescribed antibiotics")
        self.assertIsNotNone(note.created_at)

    def test_str_method(self):
        self.assertEqual(str(self.note), f"Note {self.note.pk}")

    def test_required_fields(self):
        with self.assertRaises(Exception):  # IntegrityError for missing required fields
            AppointmentNote.objects.create(note_text="Missing appointment and note_type")

    def test_note_type_choices(self):
        self.assertIn(self.note.note_type, [note_type.value for note_type in NoteType])

class ServiceModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.service = Service.objects.create(
            service_name="Blood Test",
            service_type=ServiceType.CONSULTATION.value,
            price=50.00
        )

    def test_create_service(self):
        service = Service.objects.create(
            service_name="X-Ray",
            service_type=ServiceType.IMAGING.value,
            price=75.00
        )
        self.assertEqual(service.service_name, "X-Ray")
        self.assertEqual(service.service_type, ServiceType.IMAGING.value)
        self.assertEqual(service.price, 75.00)
        self.assertIsNotNone(service.created_at)

    def test_str_method(self):
        self.assertEqual(str(self.service), "Blood Test")

    def test_required_fields(self):
        service = Service.objects.create(price=50.00)  # No exception, fields default to empty strings
        self.assertEqual(service.service_name, '')  # Verify empty string for service_name
        self.assertEqual(service.service_type, '')  # Verify empty string for service_type
        self.assertEqual(service.price, 50.00)
        self.assertIsNotNone(service.created_at)

    def test_service_type_choices(self):
        self.assertIn(self.service.service_type, [service_type.value for service_type in ServiceType])

class ServiceOrderModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            role=UserRole.PATIENT.value
        )
        cls.patient = Patient.objects.create(
            user=cls.user,
            first_name='Test',
            last_name='Patient',
            identity_number='111222333',
            insurance_number='INS123456',
            birthday=date(1990, 1, 1),
            gender=Gender.FEMALE.value
        )
        cls.department = Department.objects.create(department_name="Cardiology")
        cls.doctor = Doctor.objects.create(
            user=cls.user,
            first_name="John",
            last_name="Doe",
            identity_number="123456789",
            birthday=date(1980, 1, 1),
            gender=Gender.MALE.value,
            academic_degree=AcademicDegree.BS_CKI.value,
            specialization="Cardiologist",
            type=DoctorType.EXAMINATION.value,
            department=cls.department,
            price=100.00
        )
        cls.room = ExaminationRoom.objects.create(
            department=cls.department,
            type=RoomType.EXAMINATION.value,
            building="A",
            floor=1,
            note="Room 101"
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
            status=AppointmentStatus.CONFIRMED.value
        )
        cls.service = Service.objects.create(
            service_name="Blood Test",
            service_type=ServiceType.CONSULTATION.value,
            price=50.00
        )
        cls.service_order = ServiceOrder.objects.create(
            appointment=cls.appointment,
            room=cls.room,
            service=cls.service,
            status=OrderStatus.ORDERED.value,
            result="Pending results",
            number=1,
            order_time=timezone.now(),
            result_time=timezone.now() + timezone.timedelta(hours=1),
            result_file_url="https://example.com/result.pdf",
            result_file_public_id="public_id_123"
        )

    def test_create_service_order(self):
        service_order = ServiceOrder.objects.create(
            appointment=self.appointment,
            room=self.room,
            service=self.service,
            status=OrderStatus.COMPLETED.value,
            result="Normal results",
            number=2,
            order_time=timezone.now(),
            result_time=timezone.now() + timezone.timedelta(hours=2),
            result_file_url="https://example.com/result2.pdf",
            result_file_public_id="public_id_456"
        )
        self.assertEqual(service_order.appointment, self.appointment)
        self.assertEqual(service_order.room, self.room)
        self.assertEqual(service_order.service, self.service)
        self.assertEqual(service_order.status, OrderStatus.COMPLETED.value)
        self.assertEqual(service_order.result, "Normal results")
        self.assertEqual(service_order.number, 2)
        self.assertIsNotNone(service_order.order_time)
        self.assertIsNotNone(service_order.result_time)
        self.assertEqual(service_order.result_file_url, "https://example.com/result2.pdf")
        self.assertEqual(service_order.result_file_public_id, "public_id_456")
        self.assertIsNotNone(service_order.created_at)

    def test_str_method(self):
        self.assertEqual(str(self.service_order), f"Order {self.service_order.pk}")

    def test_required_fields(self):
        with self.assertRaises(Exception):  # IntegrityError for missing required fields
            ServiceOrder.objects.create(
                result="Test result",
                number=3,
                order_time=timezone.now(),
                result_time=timezone.now(),
                result_file_url="https://example.com/test.pdf",
                result_file_public_id="test_id"
            )

    def test_status_choices(self):
        self.assertIn(self.service_order.status, [order_status.value for order_status in OrderStatus])
