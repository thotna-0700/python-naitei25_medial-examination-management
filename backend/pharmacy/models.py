from django.db import models
from core.models import BaseModel
from appointments.models import Appointment
from patients.models import Patient
from common.constants import PHARMACY_LENGTH, COMMON_LENGTH, DECIMAL_MAX_DIGITS, DECIMAL_DECIMAL_PLACES

class Medicine(BaseModel):
    medicine_name = models.CharField(max_length=COMMON_LENGTH["NAME"])
    manufactor = models.CharField(max_length=COMMON_LENGTH["NAME"], blank=True, null=True)
    category = models.CharField(max_length=PHARMACY_LENGTH["CATEGORY"])
    description = models.TextField(blank=True, null=True)
    usage = models.TextField()
    unit = models.CharField(max_length=PHARMACY_LENGTH["UNIT"])
    is_insurance_covered = models.BooleanField(default=False)
    insurance_discount_percent = models.FloatField(blank=True, null=True)
    insurance_discount = models.DecimalField(max_digits=DECIMAL_MAX_DIGITS, decimal_places=DECIMAL_DECIMAL_PLACES, blank=True, null=True)
    side_effects = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=DECIMAL_MAX_DIGITS, decimal_places=DECIMAL_DECIMAL_PLACES)
    quantity = models.IntegerField()
    avatar = models.CharField(max_length=COMMON_LENGTH["URL"], blank=True, null=True)

    def __str__(self):
        return self.medicine_name


class Prescription(BaseModel):
    appointment = models.ForeignKey(Appointment, on_delete=models.RESTRICT)
    patient = models.ForeignKey(Patient, on_delete=models.RESTRICT)
    follow_up_date = models.DateField(blank=True, null=True)
    is_follow_up = models.BooleanField(default=False)
    diagnosis = models.TextField()
    systolic_blood_pressure = models.IntegerField(blank=True, null=True)
    diastolic_blood_pressure = models.IntegerField(blank=True, null=True)
    heart_rate = models.IntegerField(blank=True, null=True)
    blood_sugar = models.IntegerField(blank=True, null=True)
    note = models.CharField(max_length=PHARMACY_LENGTH["PRESCRIPTION_NOTE"], blank=True, null=True)

    def __str__(self):
        return f"Prescription {self.pk}"


class PrescriptionDetail(BaseModel):
    prescription = models.ForeignKey(Prescription, on_delete=models.RESTRICT)
    medicine = models.ForeignKey(Medicine, on_delete=models.RESTRICT)
    dosage = models.CharField(max_length=PHARMACY_LENGTH["DOSAGE"])
    frequency = models.CharField(max_length=PHARMACY_LENGTH["FREQUENCY"])
    duration = models.CharField(max_length=PHARMACY_LENGTH["DURATION"])
    quantity = models.IntegerField()
    prescription_notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"PrescriptionDetail {self.pk}"
