import { api } from "../../../shared/services/api";
import { DepartmentFromAPI } from "../types/department";
import type { Doctor } from "../types/doctor";

export interface DepartmentDto {
  department_name: string;
  description: string;
  location?: string;
  head?: string;
}

export const departmentService = {
  async getAllDepartments(): Promise<DepartmentFromAPI[]> {
    const response = await api.get<DepartmentFromAPI[]>("/departments/");
    return response.data;
  },

  async getDepartmentById(departmentId: number): Promise<DepartmentFromAPI> {
    const response = await api.get<DepartmentFromAPI>(
      `/departments/${departmentId}/`
    );
    return response.data;
  },

  async createDepartment(
    departmentData: DepartmentDto
  ): Promise<DepartmentFromAPI> {
    const response = await api.post<DepartmentFromAPI>(
      "/departments/",
      departmentData
    );
    return response.data;
  },

  async updateDepartment(
    departmentId: number,
    departmentData: DepartmentDto
  ): Promise<DepartmentFromAPI> {
    const response = await api.put<DepartmentFromAPI>(
      `/departments/${departmentId}/`,
      departmentData
    );
    return response.data;
  },

  async deleteDepartment(departmentId: number): Promise<string> {
    const response = await api.delete<string>(`/departments/${departmentId}/`);
    return response.data;
  },

  // Changed return type to Doctor[]
  async getDoctorsByDepartmentId(departmentId: number): Promise<Doctor[]> {
    const response = await api.get<Doctor[]>(
      `/departments/${departmentId}/doctors/`
    );
    return response.data;
  },

  async getDepartmentStatistics(departmentId: number): Promise<{
    totalPatients: number;
    todayPatients: number;
    occupancyRate: number;
    serviceCount: number;
  }> {
    const response = await api.get(
      `/departments/${departmentId}/statistics/`
    );
    return response.data;
  },
  
  async addDoctorToDepartment(departmentId: number, doctorId: number): Promise<Doctor> {
    const response = await api.post<Doctor>(`/departments/${departmentId}/add_doctor/`, {
      doctor_id: doctorId,
    });
    return response.data;
  },

  async removeDoctorFromDepartment(departmentId: number, doctorId: number): Promise<{ message: string }> {
    const response = await api.delete<{ message: string }>(
      `/departments/${departmentId}/remove_doctor/${doctorId}/`
    );
    return response.data;
  },
};
