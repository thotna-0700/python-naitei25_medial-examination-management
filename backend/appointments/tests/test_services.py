from django.test import TestCase
from django.utils import timezone
from datetime import date, time, datetime, timedelta
from unittest.mock import patch
from appointments.services import AppointmentService, AppointmentNoteService, ServiceOrderService, ServicesService
from appointments.models import Appointment, AppointmentNote, Service, ServiceOrder
from doctors.models import Doctor, Department, Schedule, ExaminationRoom
from patients.models import Patient
from users.models import User
from common.enums import AppointmentStatus, NoteType, OrderStatus, ServiceType, Gender, AcademicDegree, DoctorType, RoomType, Shift, UserRole
from common.constants import PAGE_NO_DEFAULT, PAGE_SIZE_DEFAULT, SCHEDULE_DEFAULTS, DECIMAL_MAX_DIGITS, DECIMAL_DECIMAL_PLACES
from django.core.files.uploadedfile import UploadedFile

class AppointmentServiceTest(TestCase):
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
            floor=1
        )
        cls.schedule = Schedule.objects.create(
            doctor=cls.doctor,
            room=cls.room,
            work_date=date(2025, 8, 26),
            start_time=time(8, 0),
            end_time=time(12, 0),
            shift=Shift.MORNING.value,
            max_patients=10,
            current_patients=0,
            status="AVAILABLE",
            default_appointment_duration_minutes=30
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

    def test_get_appointments_by_doctor_id_optimized(self):
        result = AppointmentService.get_appointments_by_doctor_id_optimized(
            doctor_id=self.doctor.id,
            page_no=PAGE_NO_DEFAULT,
            page_size=PAGE_SIZE_DEFAULT
        )
        self.assertEqual(result['totalElements'], 1)
        self.assertEqual(result['results'][0].id, self.appointment.id)
        self.assertEqual(result['pageNo'], PAGE_NO_DEFAULT)
        self.assertEqual(result['pageSize'], PAGE_SIZE_DEFAULT)
        self.assertEqual(result['totalPages'], 1)
        self.assertTrue(result['last'])

    def test_get_appointments_by_patient_id_optimized(self):
        result = AppointmentService.get_appointments_by_patient_id_optimized(
            patient_id=self.patient.id,
            page_no=PAGE_NO_DEFAULT,
            page_size=PAGE_SIZE_DEFAULT,
            appointment_type="all"
        )
        self.assertEqual(result['totalElements'], 1)
        self.assertEqual(result['results'][0].id, self.appointment.id)

    def test_get_all_appointments(self):
        page = AppointmentService.get_all_appointments(page_no=PAGE_NO_DEFAULT, page_size=PAGE_SIZE_DEFAULT)
        self.assertEqual(len(page), 1)
        self.assertEqual(page[0].id, self.appointment.id)

    def test_get_appointments_by_doctor(self):
        qs = AppointmentService.get_appointments_by_doctor(self.doctor.id)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().id, self.appointment.id)

    def test_get_appointments_by_patient(self):
        qs = AppointmentService.get_appointments_by_patient(self.patient.id)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().id, self.appointment.id)

    def test_get_appointments_by_doctor_and_date(self):
        qs = AppointmentService.get_appointments_by_doctor_and_date(self.doctor.id, date(2025, 8, 26))
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().id, self.appointment.id)

    def test_count_by_schedule_and_slot_start(self):
        count = AppointmentService.count_by_schedule_and_slot_start(self.schedule.id, time(8, 0))
        self.assertEqual(count, 1)

    def test_get_appointments_by_schedule_ordered(self):
        qs = AppointmentService.get_appointments_by_schedule_ordered(self.schedule.id)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().id, self.appointment.id)

    def test_get_appointments_by_doctor_and_schedules(self):
        page = AppointmentService.get_appointments_by_doctor_and_schedules(self.doctor.id, [self.schedule.id])
        self.assertEqual(len(page.object_list), 1)
        self.assertEqual(page[0].id, self.appointment.id)

    def test_get_available_time_slots(self):
        slots = AppointmentService.get_available_time_slots(self.schedule.id)
        self.assertEqual(len(slots), 8)  # 240 min / 30 min = 8 slots
        self.assertEqual(slots[0]['slot_start'], "08:00:00")
        self.assertEqual(slots[0]['slot_end'], "08:30:00")
        self.assertFalse(slots[0]['available'])  # Booked

    def test_create_appointment(self):
        data = {
            'doctor': self.doctor,
            'patient': self.patient,
            'schedule': self.schedule,
            'symptoms': "Headache",
            'slot_start': time(9, 0),
            'slot_end': time(9, 30)
        }
        appointment = AppointmentService.create_appointment(data)
        self.assertEqual(appointment.symptoms, "Headache")
        self.assertEqual(appointment.status, AppointmentStatus.PENDING.value)
        self.schedule.refresh_from_db()
        self.assertEqual(self.schedule.current_patients, 1)

    def test_create_appointment_full_schedule(self):
        self.schedule.max_patients = 1
        self.schedule.current_patients = 1
        self.schedule.save()
        data = {
            'doctor': self.doctor,
            'patient': self.patient,
            'schedule': self.schedule,
            'symptoms': "Headache",
            'slot_start': time(9, 0),
            'slot_end': time(9, 30)
        }
        with self.assertRaises(ValueError):
            AppointmentService.create_appointment(data)

    def test_create_appointment_booked_slot(self):
        data = {
            'doctor': self.doctor,
            'patient': self.patient,
            'schedule': self.schedule,
            'symptoms': "Headache",
            'slot_start': time(8, 0),
            'slot_end': time(8, 30)
        }
        with self.assertRaises(ValueError):
            AppointmentService.create_appointment(data)

    def test_update_appointment(self):
        data = {'status': AppointmentStatus.CANCELLED.value}
        updated_appointment = AppointmentService.update_appointment(self.appointment.id, data)
        self.assertEqual(updated_appointment.status, AppointmentStatus.CANCELLED.value)
        self.schedule.refresh_from_db()
        self.assertEqual(self.schedule.current_patients, 0)
        self.assertEqual(self.schedule.status, "AVAILABLE")

    def test_cancel_appointment(self):
        cancelled_appointment = AppointmentService.cancel_appointment(self.appointment.id)
        self.assertEqual(cancelled_appointment.status, AppointmentStatus.CANCELLED.value)
        self.schedule.refresh_from_db()
        self.assertEqual(self.schedule.current_patients, 0)
        self.assertEqual(self.schedule.status, "AVAILABLE")

    def test_cancel_appointment_already_cancelled(self):
        self.appointment.status = AppointmentStatus.CANCELLED.value
        self.appointment.save()
        with self.assertRaises(ValueError):
            AppointmentService.cancel_appointment(self.appointment.id)

class AppointmentNoteServiceTest(TestCase):
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
            floor=1
        )
        cls.schedule = Schedule.objects.create(
            doctor=cls.doctor,
            room=cls.room,
            work_date=date(2025, 8, 26),
            start_time=time(8, 0),
            end_time=time(12, 0),
            shift=Shift.MORNING.value,
            max_patients=10,
            current_patients=0,
            status="AVAILABLE",
            default_appointment_duration_minutes=30
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
        cls.service = AppointmentNoteService()

    def test_get_notes_by_appointment_id(self):
        notes = self.service.get_notes_by_appointment_id(self.appointment.id)
        self.assertEqual(notes.count(), 1)
        self.assertEqual(notes.first().id, self.note.id)

    def test_update_note(self):
        data = {'content': "Updated diagnosis"}
        updated_note = self.service.update_note(self.note.id, data)
        self.assertEqual(updated_note.note_text, "Updated diagnosis")

    def test_delete_note(self):
        self.service.delete_note(self.note.id)
        self.assertFalse(AppointmentNote.objects.filter(id=self.note.id).exists())

class ServiceOrderServiceTest(TestCase):
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
            floor=1
        )
        cls.schedule = Schedule.objects.create(
            doctor=cls.doctor,
            room=cls.room,
            work_date=date(2025, 8, 26),
            start_time=time(8, 0),
            end_time=time(12, 0),
            shift=Shift.MORNING.value,
            max_patients=10,
            current_patients=0,
            status="AVAILABLE",
            default_appointment_duration_minutes=30
        )
        cls.appointment = Appointment.objects.create(
            doctor=cls.doctor,
            patient=cls.patient,
            schedule=cls.schedule,
            status=AppointmentStatus.CONFIRMED.value
        )
        cls.service_model = Service.objects.create(
            service_name="Blood Test",
            service_type=ServiceType.TEST.value,
            price=50.00
        )
        cls.service_order = ServiceOrder.objects.create(
            appointment=cls.appointment,
            room=cls.room,
            service=cls.service_model,
            status=OrderStatus.ORDERED.value,
            result="Pending results",
            number=1,
            order_time=timezone.now(),
            result_time=timezone.now() + timezone.timedelta(hours=1),
            result_file_url="/results/result.pdf",
            result_file_public_id="public_id_123"
        )
        cls.service = ServiceOrderService()

    def test_get_all_orders(self):
        orders = self.service.get_all_orders()
        self.assertEqual(orders.count(), 1)
        self.assertEqual(orders.first().id, self.service_order.id)

    def test_get_order_by_id(self):
        order = self.service.get_order_by_id(self.service_order.id)
        self.assertEqual(order.id, self.service_order.id)

    def test_create_order(self):
        data = {
            'appointment': self.appointment,
            'room': self.room,
            'service': self.service_model,  # ✅ use model instance
            'status': OrderStatus.COMPLETED.value,
            'result': "Normal results",
            'number': 2,
            'order_time': timezone.now(),
            'result_time': timezone.now() + timezone.timedelta(hours=2)
        }
        order = self.service.create_order(data)
        self.assertEqual(order.status, OrderStatus.COMPLETED.value)
        self.assertEqual(order.result, "Normal results")
        self.assertEqual(order.number, 2)

    def test_update_order(self):
        data = {'order_status': OrderStatus.COMPLETED.value, 'result': "Updated results"}
        updated_order = self.service.update_order(self.service_order.id, data)
        self.assertEqual(updated_order.status, OrderStatus.COMPLETED.value)
        self.assertEqual(updated_order.result, "Updated results")

    def test_delete_order(self):
        self.service.delete_order(self.service_order.id)
        self.assertFalse(ServiceOrder.objects.filter(id=self.service_order.id).exists())

    def test_get_orders_by_appointment_id(self):
        orders = self.service.get_orders_by_appointment_id(self.appointment.id)
        self.assertEqual(orders.count(), 1)
        self.assertEqual(orders.first().id, self.service_order.id)

    def test_get_orders_by_room_and_status_and_date(self):
        orders = self.service.get_orders_by_room_and_status_and_date(
            room_id=self.room.id,
            status=OrderStatus.ORDERED.value,
            order_date=date.today()
        )
        self.assertEqual(orders.count(), 1)
        self.assertEqual(orders.first().id, self.service_order.id)

    @patch('django.core.files.storage.default_storage.save')
    @patch('django.core.files.storage.default_storage.url')
    def test_upload_test_result(self, mock_url, mock_save):
        mock_save.return_value = "stored_path"
        mock_url.return_value = "https://example.com/result.pdf"
        file = UploadedFile(name="result.pdf", content_type="application/pdf")
        updated_order = self.service.upload_test_result(self.service_order.id, file)
        self.assertEqual(updated_order.result_file_url, "https://example.com/result.pdf")
        self.assertEqual(updated_order.result_file_public_id, "stored_path")
        self.assertEqual(updated_order.result, "https://example.com/result.pdf")
        self.assertIsNotNone(updated_order.result_time)

class ServicesServiceTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a service record in DB for testing
        cls.service_obj = Service.objects.create(
            service_name="Blood Test",
            service_type=ServiceType.TEST.value,
            price=50.00
        )
        # Initialize service layer
        cls.service_service = ServicesService()

    def test_get_all_services(self):
        services = self.service_service.get_all_services()
        self.assertEqual(services.count(), 1)
        self.assertEqual(services.first().id, self.service_obj.id)

    def test_get_service_by_id(self):
        service = self.service_service.get_service_by_id(self.service_obj.pk)
        self.assertEqual(service.id, self.service_obj.pk)

    def test_create_service(self):
        data = {
            "service_name": "X-Ray",
            "service_type": ServiceType.IMAGING.value,
            "price": 75.00,
        }
        service = self.service_service.create_service(data)
        self.assertEqual(service.service_name, "X-Ray")
        self.assertEqual(service.service_type, ServiceType.IMAGING.value)
        self.assertEqual(service.price, 75.00)
        # Check DB persisted
        self.assertTrue(Service.objects.filter(id=service.id).exists())

    def test_update_service(self):
        data = {"service_name": "Updated Blood Test"}
        updated_service = self.service_service.update_service(self.service_obj.id, data)
        self.assertEqual(updated_service.service_name, "Updated Blood Test")
        # Ensure DB record updated
        self.service_obj.refresh_from_db()
        self.assertEqual(self.service_obj.service_name, "Updated Blood Test")

    def test_delete_service(self):
        self.service_service.delete_service(self.service_obj.id)
        self.assertFalse(Service.objects.filter(id=self.service_obj.id).exists())
