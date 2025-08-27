from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.utils import timezone
from datetime import date, time, timedelta
from unittest.mock import patch
from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile
from appointments.models import Appointment, AppointmentNote, Service, ServiceOrder
from doctors.models import Doctor, Department, Schedule, ExaminationRoom
from patients.models import Patient
from users.models import User
from common.enums import AppointmentStatus, NoteType, OrderStatus, ServiceType, Gender, AcademicDegree, DoctorType, RoomType, Shift, UserRole
from common.constants import PAGE_NO_DEFAULT, PAGE_SIZE_DEFAULT, SCHEDULE_DEFAULTS

class AppointmentViewSetTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            role=UserRole.DOCTOR.value
        )
        cls.patient_user = User.objects.create_user(
            email='patientuser@example.com',
            password='testpass123',
            role=UserRole.PATIENT.value
        )
        cls.patient = Patient.objects.create(
            user=cls.patient_user,
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
        cls.note = AppointmentNote.objects.create(
            appointment=cls.appointment,
            note_type=NoteType.DOCTOR.value,
            note_text="Patient diagnosed with flu"
        )

    def test_list_appointments(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('appointment-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['content']), 1)

    def test_retrieve_appointment(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('appointment-detail', kwargs={'pk': self.appointment.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.appointment.id)

    def test_create_appointment(self):
        self.client.force_authenticate(user=self.user)
        data = {
            'doctor': self.doctor.id,
            'patient': self.patient.id,
            'schedule': self.schedule.id,
            'symptoms': "Headache",
            'note': "Follow-up",
            'slot_start': "09:00:00",
            'slot_end': "09:30:00"
        }
        response = self.client.post(reverse('appointment-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Appointment.objects.count(), 2)

    def test_update_appointment(self):
        self.client.force_authenticate(user=self.user)
        data = {
            'symptoms': "Updated symptoms",
            'note': "Updated note",
            'status': AppointmentStatus.PENDING.value
        }
        response = self.client.patch(reverse('appointment-detail', kwargs={'pk': self.appointment.pk}), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.symptoms, "Updated symptoms")
        self.assertEqual(self.appointment.status, AppointmentStatus.PENDING.value)

    def test_get_by_doctor(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('appointment-get-by-doctor', kwargs={'doctor_id': self.doctor.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['content']), 1)

    def test_get_by_patient(self):
        self.client.force_authenticate(user=self.patient_user)
        response = self.client.get(reverse('appointment-get-by-patient', kwargs={'patient_id': self.patient.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['content']), 1)

    def test_available_slots(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('appointment-available-slots')
        response = self.client.post(url, {'schedule_id': self.schedule.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 8)  # Assuming 8 slots

    def test_add_note(self):
        self.client.force_authenticate(user=self.user)
        data = {
            'note_type': NoteType.DOCTOR.value,
            'content': "Prescribed antibiotics"
        }
        response = self.client.post(reverse('appointment-note-create-note', kwargs={'appointment_id': self.appointment.pk}), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AppointmentNote.objects.count(), 2)

    def test_cancel_appointment(self):
        self.client.force_authenticate(user=self.user)
        data = {'appointment_id': self.appointment.id}
        response = self.client.post(reverse('appointment-cancel-appointment', kwargs={'pk': self.appointment.pk}), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, AppointmentStatus.CANCELLED.value)

class ServiceOrderViewSetTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            role=UserRole.DOCTOR.value
        )
        cls.patient_user = User.objects.create_user(
            email='patientuser@example.com',
            password='testpass123',
            role=UserRole.PATIENT.value
        )
        cls.patient = Patient.objects.create(
            user=cls.patient_user,
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
            result_time=timezone.now() + timedelta(hours=1),
            result_file_url="/results/result.pdf",
            result_file_public_id="public_id_123"
        )

    def test_list_service_orders(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('service-order-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_retrieve_service_order(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('service-order-detail', kwargs={'pk': self.service_order.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['order_id'], self.service_order.id)

    def test_create_service_order(self):
        self.client.force_authenticate(user=self.user)
        data = {
            'appointment_id': self.appointment.id,
            'room_id': self.room.id,
            'service_id': self.service.id,
            'order_status': OrderStatus.COMPLETED.value,
            'result': "Normal results",
            'number': 2,
            'order_time': timezone.now().isoformat(),
            'result_time': (timezone.now() + timedelta(hours=2)).isoformat()
        }
        response = self.client.post(reverse('service-order-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(ServiceOrder.objects.count(), 2)

    def test_update_service_order(self):
        self.client.force_authenticate(user=self.user)
        data = {'order_status': OrderStatus.COMPLETED.value, 'result': "Updated results"}
        response = self.client.put(reverse('service-order-detail', kwargs={'pk': self.service_order.pk}), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.service_order.refresh_from_db()
        self.assertEqual(self.service_order.status, OrderStatus.COMPLETED.value)
        self.assertEqual(self.service_order.result, "Updated results")

    def test_destroy_service_order(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(reverse('service-order-detail', kwargs={'pk': self.service_order.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(ServiceOrder.objects.count(), 0)

    def test_by_appointment(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('service-order-by-appointment', kwargs={'appointment_id': self.appointment.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_by_room(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('service-order-by-room', kwargs={'room_id': self.room.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    @patch('appointments.services.ServiceOrderService.upload_test_result')
    def test_upload_result(self, mock_upload):
        mock_upload.return_value = self.service_order
        self.client.force_authenticate(user=self.user)
        file_content = b"Dummy PDF content"
        uploaded_file = SimpleUploadedFile("test.pdf", file_content, content_type="application/pdf")
        data = {'file': uploaded_file}
        response = self.client.post(reverse('service-order-upload-result', kwargs={'pk': self.service_order.pk}), data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

class ServiceViewSetTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            role=UserRole.DOCTOR.value
        )
        cls.service = Service.objects.create(
            service_name="Blood Test",
            service_type=ServiceType.TEST.value,
            price=50.00
        )

    def test_list_services(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('service-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_retrieve_service(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('service-detail', kwargs={'pk': self.service.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['service_id'], self.service.id)

    def test_create_service(self):
        self.client.force_authenticate(user=self.user)
        data = {
            'service_name': "X-Ray",
            'service_type': ServiceType.IMAGING.value,
            'price': "75.00"
        }
        response = self.client.post(reverse('service-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Service.objects.count(), 2)

    def test_update_service(self):
        self.client.force_authenticate(user=self.user)
        data = {
            'service_name': "Updated Blood Test",
            'service_type': ServiceType.TEST.value,
            'price': "50.00"
        }
        response = self.client.put(reverse('service-detail', kwargs={'pk': self.service.pk}), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.service.refresh_from_db()
        self.assertEqual(self.service.service_name, "Updated Blood Test")

    def test_destroy_service(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(reverse('service-detail', kwargs={'pk': self.service.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Service.objects.count(), 0)
