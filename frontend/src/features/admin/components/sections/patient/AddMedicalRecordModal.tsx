"use client";

import type React from "react";

import { useState, useEffect } from "react";
import { Modal } from "../../ui/modal";
import type {
  CreatePrescriptionRequest,
  PrescriptionDetailRequest,
  Medicine,
} from "../../../types/pharmacy";
import { pharmacyService } from "../../../services/pharmacyService";
import { appointmentService } from "../../../services/appointmentService";
import type { AppointmentResponse } from "../../../types/appointment";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import { Calendar } from "lucide-react";
import { useTranslation } from "react-i18next";

interface AddMedicalRecordModalProps {
  isOpen: boolean;
  onClose: () => void;
  // onSubmit: (data: CreatePrescriptionRequest) => Promise<void>
  onSubmit: (appointmentId: number, prescriptionData: any) => Promise<void>;
  patientId: number;
  appointmentId?: number;
}

export default function AddMedicalRecordModal({
  isOpen,
  onClose,
  onSubmit,
  patientId,
  appointmentId,
}: AddMedicalRecordModalProps) {
  const [form, setForm] = useState<CreatePrescriptionRequest>({
    appointment_id: appointmentId || 0,
    patient_id: patientId,
    follow_up_date: "",
    is_follow_up: false,
    diagnosis: "",
    systolic_blood_pressure: 120,
    diastolic_blood_pressure: 80,
    heart_rate: 70,
    blood_sugar: 90,
    note: "",
    prescription_details: [],
  });
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [medicines, setMedicines] = useState<Medicine[]>([]);
  const [appointments, setAppointments] = useState<AppointmentResponse[]>([]);
  const [loadingAppointments, setLoadingAppointments] = useState(false);
  const { t } = useTranslation();
  const [frequencyInputs, setFrequencyInputs] = useState<{
    [key: number]: { times: string; unit: string };
  }>({});
  const [appointmentsWithPrescription, setAppointmentsWithPrescription] =
    useState<number[]>([]);

  const checkDuplicateMedicine = (
    prescriptionDetails: PrescriptionDetailRequest[],
    medicineId: number,
    excludeIndex?: number
  ): boolean => {
    return prescriptionDetails.some((detail, index) => {
      // Bỏ qua chính nó khi đang edit (excludeIndex được truyền vào)
      if (excludeIndex !== undefined && index === excludeIndex) return false;

      // Bỏ qua các thuốc đã bị cancel (cho EditModal)
      if ((detail as any).status === "cancel") return false;

      return detail.medicine_id === medicineId && medicineId !== 0;
    });
  };

  // Load medicines and appointments on component mount
  useEffect(() => {
    const loadData = async () => {
      try {
        const medicineList = await pharmacyService.getAllMedicines();
        setMedicines(medicineList || []);
      } catch (error) {
        console.error("Error loading medicines:", error);
        setMedicines([]);
      }

      if (patientId) {
        try {
          setLoadingAppointments(true);
          const appointmentData =
            await appointmentService.getAppointmentsByPatientId(
              patientId,
              1,
              50
            );
          const appointmentsArray = Array.isArray(appointmentData)
            ? appointmentData
            : appointmentData.content || [];
          setAppointments(appointmentsArray);

          // Lấy danh sách tất cả các prescription để check appointment nào đã có đơn thuốc
          const prescriptionData =
            await pharmacyService.getPrescriptionHistoryByPatientId(patientId);

          // Lọc ra các appointment_id đã có prescription (status không phải "cancel")
          const withPrescription = prescriptionData
            .filter(
              (prescription: any) =>
                prescription.status !== "cancel" && prescription.appointment_id
            )
            .map((prescription: any) => Number(prescription.appointment_id));

          console.log("Appointments with prescription:", withPrescription);
          setAppointmentsWithPrescription(withPrescription);
        } catch (error) {
          console.error("Error loading appointments:", error);
          setAppointments([]);
          setAppointmentsWithPrescription([]);
        } finally {
          setLoadingAppointments(false);
        }
      }
    };

    if (isOpen) {
      // Chỉ load data khi modal mở
      loadData();
    }
  }, [patientId, isOpen]);

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!form.appointment_id || form.appointment_id === 0) {
      newErrors.appointment_id = t("medicalRecord.error.selectAppointment");
    }

    if (!form.diagnosis.trim()) {
      newErrors.diagnosis = t("medicalRecord.error.diagnosisRequired");
    }

    if (
      form.systolic_blood_pressure < 80 ||
      form.systolic_blood_pressure > 200
    ) {
      newErrors.systolic_blood_pressure = t(
        "medicalRecord.error.systolicRange"
      );
    }

    if (
      form.diastolic_blood_pressure < 40 ||
      form.diastolic_blood_pressure > 120
    ) {
      newErrors.diastolic_blood_pressure = t(
        "medicalRecord.error.diastolicRange"
      );
    }

    if (form.heart_rate < 40 || form.heart_rate > 200) {
      newErrors.heart_rate = t("medicalRecord.error.heartRateRange");
    }

    if (form.blood_sugar < 50 || form.blood_sugar > 500) {
      newErrors.blood_sugar = t("medicalRecord.error.bloodSugarRange");
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleChange = (
    e: React.ChangeEvent<
      HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
    >
  ) => {
    const target = e.target as HTMLInputElement | HTMLSelectElement;
    const { name, value, type } = target;

    // Clear error for this field when user starts typing
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: "" }));
    }

    if (name === "appointment_id") {
      const appointmentId = Number(value);
      setForm((prev) => ({
        ...prev,
        appointment_id: appointmentId,
      }));
      return;
    }

    setForm((prev) => ({
      ...prev,
      [name]:
        type === "checkbox" ? (target as HTMLInputElement).checked : value,
    }));
  };

  const validatePrescriptionDetails = (): boolean => {
    if (!form.prescription_details || form.prescription_details.length === 0) {
      return true; // Cho phép đơn thuốc không có thuốc
    }

    // Lọc bỏ thuốc đã cancel (cho EditModal)
    const activeDetails = form.prescription_details.filter(
      (detail) => (detail as any).status !== "cancel"
    );

    // Kiểm tra thuốc trùng lặp
    const medicineIds = activeDetails
      .map((detail) => detail.medicine_id)
      .filter((id) => id !== 0);

    const uniqueMedicineIds = new Set(medicineIds);

    if (medicineIds.length !== uniqueMedicineIds.size) {
      alert(
        "Đơn thuốc không được chứa thuốc trùng lặp. Vui lòng kiểm tra lại."
      );
      return false;
    }

    // Các validation khác...
    const invalidDetails = activeDetails.filter(
      (detail) =>
        detail.medicine_id === 0 ||
        detail.quantity < 1 ||
        !detail.dosage ||
        !detail.frequency ||
        !detail.duration
    );

    if (invalidDetails.length > 0) {
      alert("Vui lòng điền đầy đủ thông tin cho tất cả thuốc trong đơn");
      return false;
    }

    return true;
  };

  const getMedicineSelectOptions = (currentIndex: number) => {
    const selectedMedicineIds =
      form.prescription_details
        ?.filter((detail, index) => {
          // Bỏ qua chính nó và thuốc đã cancel
          return index !== currentIndex && (detail as any).status !== "cancel";
        })
        .map((detail) => detail.medicine_id)
        .filter((id) => id !== 0) || [];

    return medicines.map((med) => ({
      ...med,
      isSelected: selectedMedicineIds.includes(med.medicineId),
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm() || !validatePrescriptionDetails()) {
      return;
    }

    if (appointmentsWithPrescription.includes(form.appointment_id)) {
      alert(t("medicalRecord.alreadyHasPrescription"));
      return;
    }

    // Kiểm tra appointment có tồn tại và có status phù hợp không
    const selectedAppointment = appointments.find(
      (app) => app.id === form.appointment_id
    );
    if (!selectedAppointment) {
      alert("Cuộc hẹn không tồn tại!");
      return;
    }

    // Có thể thêm validation cho status của appointment
    if (
      selectedAppointment.status !== "completed" &&
      selectedAppointment.status !== "confirmed"
    ) {
      alert(
        "Chỉ có thể tạo đơn thuốc cho cuộc hẹn đã hoàn thành hoặc đã xác nhận!"
      );
      return;
    }

    console.log("Form data before submission:", form);
    console.log("Prescription details:", form.prescription_details);

    const cleanedForm = {
      ...form,
      prescription_details: form.prescription_details.map((detail) => {
        const quantity =
          typeof detail.quantity === "number"
            ? detail.quantity
            : Number.parseInt(String(detail.quantity)) || 1;
        const medicine_id =
          typeof detail.medicine_id === "number"
            ? detail.medicine_id
            : Number.parseInt(String(detail.medicine_id)) || 0;

        console.log(
          `Processing prescription detail - Medicine ID: ${medicine_id}, Quantity: ${quantity}`
        );

        return {
          ...detail,
          quantity: Math.max(1, quantity),
          medicine_id: medicine_id,
        };
      }),
    };

    const invalidDetails = cleanedForm.prescription_details.filter(
      (detail) =>
        detail.medicine_id === 0 ||
        detail.quantity < 1 ||
        !detail.dosage ||
        !detail.frequency ||
        !detail.duration
    );

    if (invalidDetails.length > 0) {
      console.error("Invalid prescription details found:", invalidDetails);
      alert("Vui lòng điền đầy đủ thông tin cho tất cả thuốc trong đơn");
      return;
    }

    console.log("Cleaned form data:", cleanedForm);

    try {
      setLoading(true);

      await Promise.resolve(
        onSubmit(form.appointment_id, {
          ...cleanedForm,
          follow_up_date: cleanedForm.follow_up_date?.trim()
            ? cleanedForm.follow_up_date
            : null,
        })
      );

      setForm({
        appointment_id: appointmentId || 0,
        patient_id: patientId,
        follow_up_date: "",
        is_follow_up: false,
        diagnosis: "",
        systolic_blood_pressure: 120,
        diastolic_blood_pressure: 80,
        heart_rate: 70,
        blood_sugar: 90,
        note: "",
        prescription_details: [],
      });
      setFrequencyInputs({});
      setErrors({});

      setTimeout(() => {
        onClose();
      }, 100);
    } catch (error) {
      console.error("Error creating medical record:", error);
      alert("Thêm bệnh án thất bại! Vui lòng kiểm tra lại thông tin.");
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setErrors({});
    onClose();
  };

  const addPrescriptionDetail = () => {
    const newDetail: PrescriptionDetailRequest = {
      medicine_id: 0,
      dosage: "",
      frequency: "",
      duration: "",
      quantity: 1,
      prescription_notes: "",
    };
    const newIndex = form.prescription_details.length;

    console.log(
      `Adding new prescription detail at index ${newIndex}:`,
      newDetail
    );

    setFrequencyInputs((prev) => ({
      ...prev,
      [newIndex]: { times: "", unit: "ngày" },
    }));

    setForm((prev) => {
      const updatedForm = {
        ...prev,
        prescription_details: [...prev.prescription_details, newDetail],
      };
      console.log(
        "Updated form after adding detail:",
        updatedForm.prescription_details
      );
      return updatedForm;
    });
  };

  const updatePrescriptionDetail = (
    index: number,
    field: keyof PrescriptionDetailRequest,
    value: any
  ) => {
    const updatedDetails = [...form.prescription_details];

    if (field === "medicine_id") {
      const medicineId = Number.parseInt(value) || 0;

      // Kiểm tra thuốc trùng lặp
      if (medicineId !== 0) {
        const isDuplicate = checkDuplicateMedicine(
          form.prescription_details,
          medicineId,
          index // Bỏ qua chính thuốc đang edit
        );

        if (isDuplicate) {
          const selectedMedicine = medicines.find(
            (m) => m.medicineId === medicineId
          );
          alert(
            `Thuốc "${
              selectedMedicine?.medicineName || "này"
            }" đã có trong đơn thuốc. Vui lòng chọn thuốc khác.`
          );
          return; // Không cập nhật nếu trùng lặp
        }
      }

      updatedDetails[index][field] = medicineId;
    } else if (field === "quantity") {
      updatedDetails[index][field] = Number.parseInt(value) || 1;
    } else {
      updatedDetails[index][field] = value;
    }

    setForm({ ...form, prescription_details: updatedDetails });
  };

  const removePrescriptionDetail = (index: number) => {
    const updatedDetails = form.prescription_details.filter(
      (_, i) => i !== index
    );
    setForm({ ...form, prescription_details: updatedDetails });
  };

  const updateFrequencyTimes = (index: number, times: string) => {
    const currentFreq = frequencyInputs[index] || { times: "", unit: "ngày" };
    const newFreq = { ...currentFreq, times };
    setFrequencyInputs((prev) => ({ ...prev, [index]: newFreq }));

    const frequencyString =
      times && newFreq.unit ? `${times} lần/${newFreq.unit}` : "";
    updatePrescriptionDetail(index, "frequency", frequencyString);
  };

  const updateFrequencyUnit = (index: number, unit: string) => {
    const currentFreq = frequencyInputs[index] || { times: "", unit: "ngày" };
    const newFreq = { ...currentFreq, unit };
    setFrequencyInputs((prev) => ({ ...prev, [index]: newFreq }));

    const frequencyString =
      currentFreq.times && unit ? `${currentFreq.times} lần/${unit}` : "";
    updatePrescriptionDetail(index, "frequency", frequencyString);
  };

  const getFrequencyTimes = (index: number) => {
    return frequencyInputs[index]?.times || "";
  };

  const getFrequencyUnit = (index: number) => {
    return frequencyInputs[index]?.unit || "ngày";
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      className="max-w-[700px] lg:p-8 mt-[5vh] mb-8 max-h-[90vh] overflow-y-auto"
    >
      <div className="flex flex-col h-full">
        <div className="flex-shrink-0 px-2 pb-4">
          <h5 className="mb-4 font-semibold text-gray-800 text-xl lg:text-2xl">
            {t("medicalRecord.addNew")}
          </h5>
        </div>

        <div className="flex-1 px-2">
          <form
            id="medical-record-form"
            onSubmit={handleSubmit}
            className="space-y-4"
          >
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("medicalRecord.selectAppointment")}{" "}
                <span className="text-red-500">*</span>
              </label>
              <select
                name="appointment_id"
                value={form.appointment_id}
                onChange={handleChange}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-0"
                required
                disabled={loadingAppointments}
              >
                <option value={0}>
                  {loadingAppointments
                    ? t("common.loading")
                    : t("medicalRecord.selectAppointment")}
                </option>
                {appointments
                  .filter(
                    (appointment) =>
                      // Chỉ hiển thị appointments chưa có prescription và có status phù hợp
                      !appointmentsWithPrescription.includes(appointment.id) &&
                      (appointment.status === "completed" ||
                        appointment.status === "confirmed")
                  )
                  .map((appointment, index) => (
                    <option
                      key={appointment.id || index}
                      value={appointment.id}
                    >
                      {`${appointment.schedule?.workDate || "N/A"} - ${
                        appointment.slot_start
                      } đến ${appointment.slot_end} - ${
                        appointment.doctorInfo?.fullName || "N/A"
                      }`}
                    </option>
                  ))}
              </select>

              {errors.appointment_id && (
                <p className="mt-1 text-sm text-red-600">
                  {errors.appointment_id}
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("medicalRecord.diagnosis")}{" "}
                <span className="text-red-500">*</span>
              </label>
              <input
                name="diagnosis"
                value={form.diagnosis}
                onChange={handleChange}
                type="text"
                placeholder={t("medicalRecord.diagnosisPlaceholder")}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-0"
                title={t("medicalRecord.diagnosisPlaceholder")}
                required
              />
              {errors.diagnosis && (
                <p className="mt-1 text-sm text-red-600">{errors.diagnosis}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("medicalRecord.reason")}
              </label>
              <textarea
                name="note"
                value={form.note}
                onChange={handleChange}
                placeholder={t("medicalRecord.reasonPlaceholder")}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-0 min-h-[80px] resize-none"
                title={t("medicalRecord.reasonPlaceholder")}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t("medicalRecord.systolic")}{" "}
                  <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  name="systolic_blood_pressure"
                  value={form.systolic_blood_pressure}
                  onChange={handleChange}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-0"
                  min={80}
                  max={200}
                  title="Nhập huyết áp tâm thu (mmHg)"
                  placeholder="120"
                  required
                />
                {errors.systolic_blood_pressure && (
                  <p className="mt-1 text-sm text-red-600">
                    {errors.systolic_blood_pressure}
                  </p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t("medicalRecord.diastolic")}{" "}
                  <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  name="diastolic_blood_pressure"
                  value={form.diastolic_blood_pressure}
                  onChange={handleChange}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-0"
                  min={40}
                  max={120}
                  title="Nhập huyết áp tâm trương (mmHg)"
                  placeholder="80"
                  required
                />
                {errors.diastolic_blood_pressure && (
                  <p className="mt-1 text-sm text-red-600">
                    {errors.diastolic_blood_pressure}
                  </p>
                )}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t("medicalRecord.heartRate")}{" "}
                  <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  name="heart_rate"
                  value={form.heart_rate}
                  onChange={handleChange}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-0"
                  min={40}
                  max={200}
                  title="Nhập nhịp tim (bpm)"
                  placeholder="70"
                  required
                />
                {errors.heart_rate && (
                  <p className="mt-1 text-sm text-red-600">
                    {errors.heart_rate}
                  </p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t("medicalRecord.bloodSugar")}{" "}
                  <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  name="blood_sugar"
                  value={form.blood_sugar}
                  onChange={handleChange}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-0"
                  min={50}
                  max={500}
                  title="Nhập nồng độ đường huyết (mg/dL)"
                  placeholder="90"
                  required
                />
                {errors.blood_sugar && (
                  <p className="mt-1 text-sm text-red-600">
                    {errors.blood_sugar}
                  </p>
                )}
              </div>
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                name="is_follow_up"
                checked={form.is_follow_up}
                onChange={handleChange}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label className="ml-2 block text-sm text-gray-900">
                {t("medicalRecord.needFollowUp")}
              </label>
            </div>

            {form.is_follow_up && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t("medicalRecord.followUpDate")}
                </label>
                <div className="relative w-full">
                  <DatePicker
                    selected={
                      form.follow_up_date ? new Date(form.follow_up_date) : null
                    }
                    onChange={(date: Date | null) =>
                      setForm({
                        ...form,
                        follow_up_date: date
                          ? date.toISOString().split("T")[0]
                          : "",
                      })
                    }
                    dateFormat="yyyy-MM-dd"
                    className="w-full p-3 pr-10 border border-gray-300 rounded-lg 
                    focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-0"
                    placeholderText="Chọn ngày"
                    wrapperClassName="w-full"
                  />
                  <Calendar className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5 pointer-events-none" />
                </div>
              </div>
            )}

            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="block text-sm font-medium text-gray-700">
                  {t("medicalRecord.prescriptionDetails")}
                </label>
                <button
                  type="button"
                  onClick={addPrescriptionDetail}
                  className="px-3 py-2 text-sm font-medium text-white bg-base-600 rounded-lg hover:bg-base-800"
                >
                  + {t("medicalRecord.addMedicine")}
                </button>
              </div>
              {form.prescription_details.map((detail, index) => {
                console.log(
                  `Rendering detail ${index}:`,
                  detail,
                  `quantity: ${detail.quantity}`
                );
                return (
                  <div
                    key={index}
                    className="p-4 mb-4 bg-gray-50 rounded-lg border"
                  >
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          {t("medicalRecord.medicine")}
                        </label>
                        <select
                          value={detail.medicine_id}
                          onChange={(e) =>
                            updatePrescriptionDetail(
                              index,
                              "medicine_id",
                              Number(e.target.value)
                            )
                          }
                          className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-0"
                          title="Chọn thuốc từ danh sách"
                        >
                          <option value={0}>
                            {t("medicalRecord.selectMedicine")}
                          </option>
                          {medicines &&
                          Array.isArray(medicines) &&
                          medicines.length > 0 ? (
                            getMedicineSelectOptions(index).map((med) => {
                              const isSelected = med.isSelected;
                              return (
                                <option
                                  key={med.medicineId}
                                  value={med.medicineId}
                                  disabled={isSelected}
                                  style={{
                                    color: isSelected ? "#999" : "inherit",
                                    backgroundColor: isSelected
                                      ? "#f5f5f5"
                                      : "inherit",
                                  }}
                                >
                                  {med.medicineName ||
                                    "Tên thuốc không xác định"}
                                  {isSelected ? " (Đã chọn)" : ""}
                                </option>
                              );
                            })
                          ) : (
                            <option value={0} disabled>
                              {medicines === null || medicines === undefined
                                ? t("medicalRecord.loadingMedicines")
                                : t("medicalRecord.noMedicines")}
                            </option>
                          )}
                        </select>
                        {(!medicines || medicines.length === 0) && (
                          <p className="mt-1 text-sm text-amber-600">
                            {medicines === null || medicines === undefined
                              ? t("medicalRecord.loadingMedicines")
                              : t("medicalRecord.noMedicinesInSystem")}
                          </p>
                        )}
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          {t("medicalRecord.dosage")}
                        </label>
                        <input
                          type="text"
                          value={detail.dosage}
                          onChange={(e) =>
                            updatePrescriptionDetail(
                              index,
                              "dosage",
                              e.target.value
                            )
                          }
                          className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-0"
                          placeholder="VD: 500mg"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-4 gap-4 mt-2">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          {t("medicalRecord.frequencyTimes")}
                        </label>
                        <input
                          type="number"
                          value={getFrequencyTimes(index)}
                          onChange={(e) =>
                            updateFrequencyTimes(index, e.target.value)
                          }
                          className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-0"
                          placeholder="VD: 2"
                          title="Nhập số lần sử dụng thuốc"
                          min={1}
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          {t("medicalRecord.frequencyUnit")}
                        </label>
                        <select
                          value={getFrequencyUnit(index)}
                          onChange={(e) =>
                            updateFrequencyUnit(index, e.target.value)
                          }
                          className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-0"
                          title="Chọn đơn vị thời gian"
                        >
                          <option value="ngày">
                            {t("medicalRecord.units.day")}
                          </option>
                          <option value="tuần">
                            {t("medicalRecord.units.week")}
                          </option>
                          <option value="tháng">
                            {t("medicalRecord.units.month")}
                          </option>
                          <option value="giờ">
                            {t("medicalRecord.units.hour")}
                          </option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          {t("medicalRecord.duration")}
                        </label>
                        <input
                          type="text"
                          value={detail.duration}
                          onChange={(e) =>
                            updatePrescriptionDetail(
                              index,
                              "duration",
                              e.target.value
                            )
                          }
                          className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-0"
                          placeholder="VD: 7 ngày"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          {t("medicalRecord.quantity")}{" "}
                          <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="number"
                          value={detail.quantity || 1}
                          onChange={(e) => {
                            const inputValue = e.target.value;
                            const quantity =
                              inputValue === ""
                                ? 1
                                : Math.max(
                                    1,
                                    Number.parseInt(inputValue, 10) || 1
                                  );
                            console.log(
                              `Updating quantity for detail ${index}: input="${inputValue}" -> quantity=${quantity}`
                            );
                            updatePrescriptionDetail(
                              index,
                              "quantity",
                              quantity
                            );
                          }}
                          className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-0"
                          min={1}
                          step={1}
                          title="Nhập số lượng thuốc (tối thiểu 1)"
                          placeholder="1"
                          required
                        />
                      </div>
                    </div>
                    <div className="mt-2">
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        {t("medicalRecord.notes")}
                      </label>
                      <textarea
                        value={detail.prescription_notes}
                        onChange={(e) =>
                          updatePrescriptionDetail(
                            index,
                            "prescription_notes",
                            e.target.value
                          )
                        }
                        className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-0 resize-none"
                        placeholder="Nhập ghi chú cho đơn thuốc"
                      />
                    </div>
                    <div className="flex justify-end gap-2 mt-4">
                      <button
                        type="button"
                        onClick={() => removePrescriptionDetail(index)}
                        className="px-3 py-2 text-sm font-medium text-red-600 bg-red-100 rounded-lg hover:bg-red-200"
                      >
                        {t("medicalRecord.removeMedicine")}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </form>
        </div>

        <div className="flex-shrink-0 px-2 pt-4 border-t border-gray-200 bg-white">
          <div className="flex justify-end gap-3">
            <button
              type="button"
              className="px-4 py-2.5 text-sm font-medium text-gray-800 bg-gray-200 rounded-lg hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={handleClose}
              disabled={loading}
            >
              {t("common.cancel")}
            </button>
            <button
              type="submit"
              form="medical-record-form"
              className="px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={loading}
            >
              {loading ? t("common.saving") : t("medicalRecord.save")}
            </button>
          </div>
        </div>
      </div>
    </Modal>
  );
}
