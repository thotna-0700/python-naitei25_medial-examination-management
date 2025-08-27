from django.test import TestCase
from django.utils import timezone
from datetime import date, time, datetime
from rest_framework.exceptions import ValidationError
from appointments.serializers import (
    DoctorSerializer, ServiceSerializer, ServiceOrderSerializer,
    ScheduleSerializer, AppointmentCreateSerializer, AppointmentUpdateSerializer,
    AppointmentNoteSerializer, AvailableSlotSerializer, ScheduleTimeSerializer,
    AppointmentSerializer, AppointmentDetailSerializer, AppointmentDoctorViewSerializer,
    AppointmentPatientViewSerializer, AppointmentFilterSerializer,
    AppointmentPatientFilterSerializer, CancelAppointmentRequestSerializer
)
from patients.serializers import PatientSerializer
from appointments.models import Appointment, AppointmentNote, Service, ServiceOrder
from doctors.models import Doctor, Department, Schedule, ExaminationRoom
from patients.models import Patient
from users.models import User
from common.enums import (
    ServiceType, Gender, AppointmentStatus, NoteType, OrderStatus,
    AcademicDegree, DoctorType, RoomType, Shift, UserRole
)
from common.constants import SERVICE_LENGTH, DECIMAL_MAX_DIGITS, DECIMAL_DECIMAL_PLACES, ENUM_LENGTH, SCHEDULE_DEFAULTS

class DoctorSerializerTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            role=UserRole.DOCTOR.value
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
            price=100.00,
            avatar="https://example.com/avatar.jpg"
        )

    def test_serialize_doctor(self):
        serializer = DoctorSerializer(self.doctor)
        expected_data = {
            'id': self.doctor.id,
            'fullName': "John Doe",
            'academicDegree': AcademicDegree.BS_CKI.value,
            'specialization': "Cardiologist",
            'price': "100.00"
        }
        self.assertEqual(serializer.data, expected_data)

class ServiceSerializerTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.service = Service.objects.create(
            service_name="Blood Test",
            service_type=ServiceType.TEST.value,
            price=50.00
        )

    def test_serialize_service(self):
        serializer = ServiceSerializer(self.service)
        expected_data = {
            'service_id': self.service.id,
            'service_name': "Blood Test",
            'service_type': ServiceType.TEST.value,
            'price': "50.00",
            'created_at': self.service.created_at.strftime("%Y-%m-%d %H:%M:%S.%f+00:00"),
            'service_orders': []
        }
        self.assertEqual(serializer.data, expected_data)

    def test_create_service(self):
        data = {
            'service_name': "X-Ray",
            'service_type': ServiceType.IMAGING.value,
            'price': "75.00"
        }
        serializer = ServiceSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        service = serializer.save()
        self.assertEqual(service.service_name, "X-Ray")
        self.assertEqual(service.service_type, ServiceType.IMAGING.value)
        self.assertEqual(service.price, 75.00)

    def test_required_fields_validation(self):
        data = {'price': "50.00"}  # Missing service_name and service_type
        serializer = ServiceSerializer(data=data)
        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)

class ServiceOrderSerializerTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            role=UserRole.PATIENT.value
        )
        cls.patient = Patient.objects.create(
            user=cls.user,
            first_name="Test",
            last_name="Patient",
            identity_number="111222333",
            insurance_number="INS123456",
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
            status="AVAILABLE"
        )
        cls.appointment = Appointment.objects.create(
            doctor=cls.doctor,
            patient=cls.patient,
            schedule=cls.schedule,
            status=AppointmentStatus.CONFIRMED.value
        )
        cls.service = Service.objects.create(
            service_name="Blood Test",
            service_type=ServiceType.TEST.value,
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
            result_file_url="/results/result.pdf",
            result_file_public_id="public_id_123"
        )

    def test_serialize_service_order(self):
        serializer = ServiceOrderSerializer(self.service_order, context={'request': None})
        expected_data = {
            'order_id': self.service_order.id,
            'appointment_id': self.appointment.id,
            'room_id': self.room.id,
            'service_id': self.service.id,
            'service_name': "Blood Test",
            'price': 50.0,
            'order_status': OrderStatus.ORDERED.value,
            'result': "Pending results",
            'number': 1,
            'order_time': self.service_order.order_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            'result_time': self.service_order.result_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            'created_at': self.service_order.created_at.strftime("%Y-%m-%d %H:%M:%S.%f+00:00"),
            'result_file_url': "/results/result.pdf",
            'result_file_public_id': "public_id_123"
        }
        self.assertEqual(serializer.data, expected_data)

    def test_create_service_order(self):
        data = {
            'appointment_id': self.appointment.id,
            'room_id': self.room.id,
            'service_id': self.service.id,
            'order_status': OrderStatus.COMPLETED.value,
            'result': "Normal results",
            'number': 2,
            'order_time': timezone.now(),
            'result_time': timezone.now() + timezone.timedelta(hours=2)
        }
        serializer = ServiceOrderSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        service_order = serializer.save()
        self.assertEqual(service_order.appointment, self.appointment)
        self.assertEqual(service_order.room, self.room)
        self.assertEqual(service_order.service, self.service)
        self.assertEqual(service_order.status, OrderStatus.COMPLETED.value)
        self.assertEqual(service_order.result, "Normal results")
        self.assertEqual(service_order.number, 2)

    def test_required_fields_validation(self):
        data = {'result': "Test result"}  # Missing appointment_id, room_id, service_id
        serializer = ServiceOrderSerializer(data=data)
        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)

class ScheduleSerializerTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            role=UserRole.DOCTOR.value
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
            note="Room 101",
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

    def test_serialize_schedule(self):
        serializer = ScheduleSerializer(self.schedule)
        expected_data = {
            'scheduleId': self.schedule.id,
            'id': self.schedule.id,
            'doctorId': self.doctor.id,
            'doctor': self.doctor.id,
            'doctorName': "John Doe",
            'workDate': "2025-08-26",
            'work_date': "2025-08-26",
            'startTime': "08:00:00",
            'start_time': "08:00:00",
            'endTime': "12:00:00",
            'end_time': "12:00:00",
            'shift': Shift.MORNING.value,
            'roomId': self.room.id,
            'room': self.room.id,
            'departmentName': "Cardiology",
            'maxPatients': SCHEDULE_DEFAULTS["MAX_PATIENTS"],
            'currentPatients': SCHEDULE_DEFAULTS["CURRENT_PATIENTS"],
            'status': "AVAILABLE",
            'defaultAppointmentDurationMinutes': SCHEDULE_DEFAULTS["APPOINTMENT_DURATION_MINUTES"],
            'floor': 1,
            'building': "A"
        }
        self.assertEqual(serializer.data, expected_data)

class AppointmentCreateSerializerTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            role=UserRole.PATIENT.value
        )
        cls.patient = Patient.objects.create(
            user=cls.user,
            first_name="Test",
            last_name="Patient",
            identity_number="111222333",
            insurance_number="INS123456",
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
            floor=1
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
            status="AVAILABLE"
        )

    def test_create_appointment(self):
        data = {
            'doctor': self.doctor.id,
            'patient': self.patient.id,
            'schedule': self.schedule.id,
            'symptoms': "Fever",
            'note': "Initial consultation",
            'slot_start': "08:00:00",
            'slot_end': "08:30:00"
        }
        serializer = AppointmentCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        appointment = serializer.save()
        self.assertEqual(appointment.doctor, self.doctor)
        self.assertEqual(appointment.patient, self.patient)
        self.assertEqual(appointment.schedule, self.schedule)
        self.assertEqual(appointment.symptoms, "Fever")
        self.assertEqual(appointment.note, "Initial consultation")
        self.assertEqual(appointment.slot_start, time(8, 0))
        self.assertEqual(appointment.slot_end, time(8, 30))

class AppointmentUpdateSerializerTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            role=UserRole.PATIENT.value
        )
        cls.patient = Patient.objects.create(
            user=cls.user,
            first_name="Test",
            last_name="Patient",
            identity_number="111222333",
            insurance_number="INS123456",
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
            floor=1
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
            status="AVAILABLE"
        )
        cls.appointment = Appointment.objects.create(
            doctor=cls.doctor,
            patient=cls.patient,
            schedule=cls.schedule,
            status=AppointmentStatus.CONFIRMED.value
        )

    def test_update_appointment(self):
        data = {
            'symptoms': "Headache",
            'note': "Follow-up",
            'status': AppointmentStatus.PENDING.value,
            'slot_start': "09:00:00",
            'slot_end': "09:30:00"
        }
        serializer = AppointmentUpdateSerializer(instance=self.appointment, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        appointment = serializer.save()
        self.assertEqual(appointment.symptoms, "Headache")
        self.assertEqual(appointment.note, "Follow-up")
        self.assertEqual(appointment.status, AppointmentStatus.PENDING.value)
        self.assertEqual(appointment.slot_start, time(9, 0))
        self.assertEqual(appointment.slot_end, time(9, 30))

class AppointmentNoteSerializerTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            role=UserRole.PATIENT.value
        )
        cls.patient = Patient.objects.create(
            user=cls.user,
            first_name="Test",
            last_name="Patient",
            identity_number="111222333",
            insurance_number="INS123456",
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
            floor=1
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
            status="AVAILABLE"
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

    def test_serialize_appointment_note(self):
        serializer = AppointmentNoteSerializer(self.note)
        expected_data = {
            'id': self.note.id,
            'appointmentId': self.appointment.id,
            'note_type': NoteType.DOCTOR.value,
            'content': "Patient diagnosed with flu",
            'created_at': self.note.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        }
        self.assertEqual(serializer.data, expected_data)

class AvailableSlotSerializerTest(TestCase):
    def test_serialize_available_slot(self):
        data = {
            'slot_start': "08:00:00",
            'slot_end': "08:30:00",
            'available': True,
            'scheduleId': 1
        }
        serializer = AvailableSlotSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        expected_data = {
            'slot_start': "08:00:00",
            'slot_end': "08:30:00",
            'available': True,
            'scheduleId': 1
        }
        self.assertEqual(serializer.data, expected_data)

class ScheduleTimeSerializerTest(TestCase):
    def test_serialize_schedule_time(self):
        data = {
            'schedule_id': 1,
            'start_time': "08:00:00",
            'end_time': "12:00:00"
        }
        serializer = ScheduleTimeSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        expected_data = {
            'schedule_id': 1,
            'start_time': "08:00:00",
            'end_time': "12:00:00"
        }
        self.assertEqual(serializer.data, expected_data)

class AppointmentSerializerTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            role=UserRole.PATIENT.value
        )
        cls.patient = Patient.objects.create(
            user=cls.user,
            first_name="Test",
            last_name="Patient",
            identity_number="111222333",
            insurance_number="INS123456",
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
            note="Room 101",
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
            status="AVAILABLE"
        )
        cls.appointment = Appointment.objects.create(
            doctor=cls.doctor,
            patient=cls.patient,
            schedule=cls.schedule,
            symptoms="Fever",
            note="Initial consultation",
            slot_start=time(8, 0),
            slot_end=time(8, 30),
            status=AppointmentStatus.CONFIRMED.value
        )
        cls.note = AppointmentNote.objects.create(
            appointment=cls.appointment,
            note_type=NoteType.DOCTOR.value,
            note_text="Patient diagnosed with flu"
        )
        cls.service = Service.objects.create(
            service_name="Blood Test",
            service_type=ServiceType.TEST.value,
            price=50.00
        )
        cls.service_order = ServiceOrder.objects.create(
            appointment=cls.appointment,
            room=cls.room,
            service=cls.service,
            status=OrderStatus.ORDERED.value
        )

    def test_serialize_appointment(self):
        serializer = AppointmentSerializer(self.appointment)
        expected_data = {
            'appointmentId': self.appointment.id,
            'doctorId': self.doctor.id,
            'patientId': self.patient.id,
            'schedule': ScheduleSerializer(self.schedule).data,
            'symptoms': "Fever",
            'note': "Initial consultation",
            'slotStart': "08:00:00",
            'slotEnd': "08:30:00",
            'appointmentStatus': AppointmentStatus.CONFIRMED.value,
            'createdAt': self.appointment.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            'patientInfo': PatientSerializer(self.patient).data,
            'doctorInfo': DoctorSerializer(self.doctor).data,
            'appointment_notes': [AppointmentNoteSerializer(self.note).data],  
            'id': self.appointment.id,
            'doctor': self.doctor.id,
            'patient': self.patient.id,
            'slot_start': "08:00:00",
            'slot_end': "08:30:00",
            'status': AppointmentStatus.CONFIRMED.value,
            'created_at': self.appointment.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        }
        self.assertEqual(serializer.data, expected_data)

class AppointmentDetailSerializerTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            role=UserRole.PATIENT.value
        )
        cls.patient = Patient.objects.create(
            user=cls.user,
            first_name="Test",
            last_name="Patient",
            identity_number="111222333",
            insurance_number="INS123456",
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
            note="Room 101",
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
            status="AVAILABLE"
        )
        cls.appointment = Appointment.objects.create(
            doctor=cls.doctor,
            patient=cls.patient,
            schedule=cls.schedule,
            symptoms="Fever",
            status=AppointmentStatus.CONFIRMED.value
        )
        cls.note = AppointmentNote.objects.create(
            appointment=cls.appointment,
            note_type=NoteType.DOCTOR.value,
            note_text="Patient diagnosed with flu"
        )

    def test_serialize_appointment_detail(self):
        serializer = AppointmentDetailSerializer(self.appointment)
        expected_data = {
            'id': self.appointment.id,
            'doctor': self.doctor.id,
            'schedule': ScheduleSerializer(self.schedule).data,
            'symptoms': "Fever",
            'note': None,
            'slot_start': None,
            'slot_end': None,
            'status': AppointmentStatus.CONFIRMED.value,
            'created_at': self.appointment.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            'patientInfo': PatientSerializer(self.patient).data,
            'doctorInfo': DoctorSerializer(self.doctor).data,
            'appointmentNotes': [AppointmentNoteSerializer(self.note).data]
        }
        self.assertEqual(serializer.data, expected_data)

class AppointmentDoctorViewSerializerTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            role=UserRole.DOCTOR.value
        )
        cls.patient = Patient.objects.create(
            user=cls.user,
            first_name="Test",
            last_name="Patient",
            identity_number="111222333",
            insurance_number="INS123456",
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
            floor=1
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
            status="AVAILABLE"
        )
        cls.appointment = Appointment.objects.create(
            doctor=cls.doctor,
            patient=cls.patient,
            schedule=cls.schedule,
            symptoms="Fever",
            status=AppointmentStatus.CONFIRMED.value
        )

    def test_serialize_appointment_doctor_view(self):
        serializer = AppointmentDoctorViewSerializer(self.appointment)
        expected_data = {
            'id': self.appointment.id,
            'patient_id': self.patient.id,
            'patientInfo': PatientSerializer(self.patient).data,
            'symptoms': "Fever",
            'note': None,
            'schedule': ScheduleSerializer(self.schedule).data,
            'status': AppointmentStatus.CONFIRMED.value,
            'created_at': self.appointment.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        }
        self.assertEqual(serializer.data, expected_data)

class AppointmentPatientViewSerializerTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            role=UserRole.PATIENT.value
        )
        cls.patient = Patient.objects.create(
            user=cls.user,
            first_name="Test",
            last_name="Patient",
            identity_number="111222333",
            insurance_number="INS123456",
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
            floor=1
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
            status="AVAILABLE"
        )
        cls.appointment = Appointment.objects.create(
            doctor=cls.doctor,
            patient=cls.patient,
            schedule=cls.schedule,
            symptoms="Fever",
            slot_start=time(8, 0),
            slot_end=time(8, 30),
            status=AppointmentStatus.CONFIRMED.value
        )

    def test_serialize_appointment_patient_view(self):
        serializer = AppointmentPatientViewSerializer(self.appointment)
        expected_data = {
            'id': self.appointment.id,
            'doctorId': self.doctor.id,
            'doctorInfo': DoctorSerializer(self.doctor).data,
            'schedule': ScheduleSerializer(self.schedule).data,
            'symptoms': "Fever",
            'note': None,
            'slot_start': "08:00:00",
            'slot_end': "08:30:00",
            'status': AppointmentStatus.CONFIRMED.value,
            'createdAt': self.appointment.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            'prescriptionId': None
        }
        self.assertEqual(serializer.data, expected_data)

class AppointmentFilterSerializerTest(TestCase):
    def test_serialize_appointment_filter(self):
        data = {
            'shift': Shift.MORNING.value,
            'workDate': "2025-08-26",
            'appointmentStatus': AppointmentStatus.CONFIRMED.value,
            'roomId': 1,
            'pageNo': 1,
            'pageSize': 10
        }
        serializer = AppointmentFilterSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        expected_data = {
            'shift': Shift.MORNING.value,
            'workDate': "2025-08-26",
            'appointmentStatus': AppointmentStatus.CONFIRMED.value,
            'roomId': 1,
            'pageNo': 1,
            'pageSize': 10
        }
        self.assertEqual(serializer.data, expected_data)

class AppointmentPatientFilterSerializerTest(TestCase):
    def test_serialize_appointment_patient_filter(self):
        data = {
            'pageNo': 1,
            'pageSize': 10,
            'status': AppointmentStatus.CONFIRMED.value
        }
        serializer = AppointmentPatientFilterSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        expected_data = {
            'pageNo': 1,
            'pageSize': 10,
            'status': AppointmentStatus.CONFIRMED.value
        }
        self.assertEqual(serializer.data, expected_data)

class CancelAppointmentRequestSerializerTest(TestCase):
    def test_serialize_cancel_appointment_request(self):
        data = {'appointment_id': 1}
        serializer = CancelAppointmentRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        expected_data = {'appointment_id': 1}
        self.assertEqual(serializer.data, expected_data)

    def test_required_fields_validation(self):
        data = {}  # Missing appointment_id
        serializer = CancelAppointmentRequestSerializer(data=data)
        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)
