import React, { useState, useEffect, useRef } from "react"
import { Modal, Input, Button, Table, Spin, message, App } from "antd"
import { SearchOutlined, DeleteOutlined } from "@ant-design/icons"
import type { Doctor } from "../../../types/doctor"
import { doctorService } from "../../../services/doctorService"
import { departmentService } from "../../../services/departmentService"
import { useTranslation } from "react-i18next"
import { appointmentService } from "../../../services/appointmentService"
import { AppointmentStatus } from "../../../types/appointment"
import { scheduleService } from "../../../services/scheduleService"
import dayjs from "dayjs"
import isSameOrAfter from "dayjs/plugin/isSameOrAfter"
dayjs.extend(isSameOrAfter)

interface Props {
    isOpen: boolean
    onClose: () => void
    departmentId: number
    onSuccess: () => void
}

export const DoctorSelectModal: React.FC<Props> = ({
    isOpen,
    onClose,
    departmentId,
    onSuccess,
}) => {
    const { t } = useTranslation()
    const { modal } = App.useApp();
    const [searchInput, setSearchInput] = useState("")
    const [searchLoading, setSearchLoading] = useState(false)
    const [filteredDoctors, setFilteredDoctors] = useState<Doctor[]>([])
    const [selectedDoctors, setSelectedDoctors] = useState<Doctor[]>([])
    const [showSearchResults, setShowSearchResults] = useState(false)
    const [saving, setSaving] = useState(false)
    const [allDoctors, setAllDoctors] = useState<Doctor[]>([])
    const [warning, setWarning] = useState<{ open: boolean, date?: string }>({ open: false });
    const getDepartmentName = (d: any) => d?.department?.department_name ?? ""

    const searchContainerRef = useRef<HTMLDivElement>(null)

    const getId = (d: any) => d?.doctorId ?? d?.id
    const getFullName = (d: any) =>
        (d?.fullName ?? `${d?.first_name ?? ""} ${d?.last_name ?? ""}`)?.trim()
    const getSpecialization = (d: any) => d?.specialization ?? d?.specialty

    const searchDoctors = async (term: string) => {
        try {
            setSearchLoading(true)
            const results = await doctorService.getAllDoctors()
            const q = term.toLowerCase()
            return results.filter((d: any) => getFullName(d).toLowerCase().includes(q))
        } catch (err) {
            console.error("Search doctors failed", err)
            return []
        } finally {
            setSearchLoading(false)
        }
    }

    useEffect(() => {
        if (isOpen) {
            doctorService.getAllDoctors().then((res) => {
                setAllDoctors(res)
                setFilteredDoctors(res)
            })
        }
    }, [isOpen])

    useEffect(() => {
        const timeout = setTimeout(() => {
            const alreadySelectedIds = new Set(selectedDoctors.map((d) => getId(d)))

            if (searchInput.trim()) {
                const q = searchInput.toLowerCase()
                setFilteredDoctors(
                    allDoctors.filter(
                        (d) =>
                            getFullName(d).toLowerCase().includes(q) &&
                            !alreadySelectedIds.has(getId(d))
                    ) as Doctor[]
                )
            } else {
                setFilteredDoctors(allDoctors.filter((d) => !alreadySelectedIds.has(getId(d))) as Doctor[])
            }
        }, 200)
        return () => clearTimeout(timeout)
    }, [searchInput, selectedDoctors, allDoctors])


    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (searchContainerRef.current && !searchContainerRef.current.contains(e.target as Node)) {
                setShowSearchResults(false)
            }
        }
        document.addEventListener("mousedown", handleClickOutside)
        return () => document.removeEventListener("mousedown", handleClickOutside)
    }, [])

    const addDoctor = async (doctor: Doctor) => {
        try {
            const today = dayjs().startOf("day");
            const schedules = await scheduleService.getSchedulesByDoctorId(getId(doctor));

            const futureSchedules = schedules.filter((s: any) =>
                dayjs(s.work_date).isSameOrAfter(today)
            );

            if (futureSchedules.length > 0) {
                const nearest = futureSchedules.sort((a: any, b: any) =>
                    dayjs(a.work_date).diff(dayjs(b.work_date))
                )[0];

                setWarning({
                    open: true,
                    date: dayjs(nearest.work_date).format("DD/MM/YYYY"),
                });
                return;
            }

            setSelectedDoctors([...selectedDoctors, doctor]);
            setSearchInput("");
            setFilteredDoctors([]);
            setShowSearchResults(false);
        } catch (err) {
            console.error("Error checking doctor schedules:", err);
            message.error("Không thể kiểm tra lịch làm việc của bác sĩ");
        }
    }

    const handleDelete = (index: number) => {
        setSelectedDoctors(selectedDoctors.filter((_, i) => i !== index))
    }

    const handleSave = async () => {
        if (selectedDoctors.length === 0) {
            message.warning("Hãy chọn ít nhất một bác sĩ")
            return
        }
        try {
            setSaving(true)
            for (const doctor of selectedDoctors) {
                await departmentService.addDoctorToDepartment(departmentId, (doctor as any).doctorId ?? (doctor as any).id)
            }
            message.success("Thêm bác sĩ thành công")
            onClose()
            onSuccess()
        } catch (err) {
            console.error(err)
            message.error("Không thể thêm bác sĩ")
        } finally {
            setSaving(false)
        }
    }

    const columns = [
        {
            title: "Họ tên",
            key: "fullName",
            render: (d: any) => getFullName(d),
        },
        { title: "Học vị", dataIndex: "academicDegree", key: "academicDegree" },
        { title: "Khoa hiện tại", key: "department", render: (d: any) => getDepartmentName(d) },
        {
            title: "",
            key: "action",
            render: (_: any, __: Doctor, index: number) => (
                <Button icon={<DeleteOutlined />} onClick={() => handleDelete(index)} danger />
            ),
        },
    ]

    return (
        <Modal title="Thêm bác sĩ vào khoa" open={isOpen} onCancel={onClose} footer={null} width={800} destroyOnClose>
            <div className="p-4">
                <div className="relative flex-1 max-w-md mb-4" ref={searchContainerRef}>
                    <Input
                        placeholder="Tìm kiếm bác sĩ..."
                        prefix={<SearchOutlined />}
                        value={searchInput}
                        onChange={(e) => setSearchInput(e.target.value)}
                        onFocus={() => setShowSearchResults(true)}
                        suffix={searchLoading ? <Spin size="small" /> : null}
                    />
                    {showSearchResults && (
                        <div className="absolute top-full left-0 right-0 bg-white border rounded-md shadow-lg z-50 max-h-60 overflow-y-auto">
                            {filteredDoctors.length > 0 ? (
                                filteredDoctors.map((doctor: any) => (
                                    <div
                                        key={getId(doctor)}
                                        className="p-3 hover:bg-gray-50 cursor-pointer border-b last:border-b-0"
                                        onClick={() => addDoctor(doctor)}
                                    >
                                        <div className="font-medium">{getFullName(doctor)}</div>
                                        <div className="text-xs text-gray-400">{getDepartmentName(doctor) || "Chưa cập nhật"}</div>
                                    </div>
                                ))
                            ) : (
                                <div className="p-3 text-sm text-gray-500">Đang tải...</div>
                            )}
                        </div>
                    )}
                </div>

                <Table
                    columns={columns as any}
                    dataSource={selectedDoctors}
                    rowKey={(r: any) => getId(r)}
                    pagination={false}
                    className="mb-6"
                />

                <div className="flex justify-end space-x-3">
                    <Button onClick={onClose}>Cancel</Button>
                    <Button type="primary" onClick={handleSave} loading={saving}>
                        Save
                    </Button>
                </div>

                <Modal
                    open={warning.open}
                    onCancel={() => setWarning({ open: false })}
                    footer={[
                        <Button key="ok" type="primary" onClick={() => setWarning({ open: false })}>
                            Đã hiểu
                        </Button>
                    ]}
                    centered
                    width={400}
                >
                    <h3 style={{ fontWeight: 600, fontSize: "16px", marginBottom: "8px" }}>
                        Không thể chuyển khoa
                    </h3>
                    <p>Bác sĩ có lịch làm việc vào ngày {warning.date}</p>
                </Modal>

            </div>
        </Modal>
    )
}
