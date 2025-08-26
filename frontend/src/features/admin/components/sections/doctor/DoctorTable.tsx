import React, { useEffect, useState } from "react";
import DoctorCard from "./DoctorCard";
import SearchInput from "../../common/SearchInput";
import { Pagination } from "../../ui/Pagination";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { doctorService } from "../../../services/doctorService";
import type { Doctor } from "../../../types/doctor";
const PAGE_SIZE = 5;

const DoctorTable: React.FC = () => {
  const { t } = useTranslation();
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [filteredDoctors, setFilteredDoctors] = useState<Doctor[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  
  // Enhanced filter and sort state
  const [genderFilter, setGenderFilter] = useState<string>("");
  const [degreeFilter, setDegreeFilter] = useState<string>("");
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [departmentFilter, setDepartmentFilter] = useState<string>("");
  const [sortBy, setSortBy] = useState<"name" | "degree" | "specialization" | "department" | "createdAt">("name");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");
  const [searchField, setSearchField] = useState<"all" | "name" | "specialization" | "identity" | "department">("all");
  const navigate = useNavigate();

  useEffect(() => {
    doctorService
      .getAllDoctors()
      .then((data) => {
        console.log("👉 Dữ liệu từ backend:", data); 
        setDoctors(data);
        setFilteredDoctors(data);
      })
      .finally(() => setLoading(false));
  }, []);

  // Apply comprehensive filters and sorting
  const applyFiltersAndSort = () => {
    let filtered = [...doctors];
    
    // Search filter
    if (searchTerm.trim()) {
      const searchLower = searchTerm.toLowerCase();
      filtered = filtered.filter(doctor => {
        switch (searchField) {
          case "name":
            return doctor.fullName?.toLowerCase().includes(searchLower);
          case "specialization":
            return doctor.specialization?.toLowerCase().includes(searchLower);
          case "identity":
            return doctor.identityNumber?.includes(searchTerm);
          case "department":
            return doctor.departmentName?.toLowerCase().includes(searchLower);
          default: // "all"
            return (
              doctor.fullName?.toLowerCase().includes(searchLower) ||
              doctor.doctorId?.toString().includes(searchTerm) ||
              doctor.identityNumber?.includes(searchTerm) ||
              doctor.specialization?.toLowerCase().includes(searchLower) ||
              doctor.departmentName?.toLowerCase().includes(searchLower)
            );
        }
      });
    }
    
    // Gender filter
    if (genderFilter) {
      filtered = filtered.filter(doctor => doctor.gender === genderFilter);
    }
    
    // Academic degree filter
    if (degreeFilter) {
      filtered = filtered.filter(doctor => doctor.academicDegree === degreeFilter);
    }
    
    // Type filter
    if (typeFilter) {
      filtered = filtered.filter(doctor => doctor.type === typeFilter);
    }
    
    // Department filter
    if (departmentFilter) {
      filtered = filtered.filter(doctor => doctor.departmentName === departmentFilter);
    }
    
    // Sort
    filtered.sort((a, b) => {
      let compareValue = 0;
      if (sortBy === "name") {
        compareValue = (a.fullName || "").localeCompare(b.fullName || "");
      } else if (sortBy === "degree") {
        compareValue = a.academicDegree.localeCompare(b.academicDegree);
      } else if (sortBy === "specialization") {
        compareValue = (a.specialization || "").localeCompare(b.specialization || "");
      } else if (sortBy === "department") {
        compareValue = (a.departmentName || "").localeCompare(b.departmentName || "");
      } else if (sortBy === "createdAt") {
        compareValue = new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
      }
      return sortOrder === "asc" ? compareValue : -compareValue;
    });
    
    setFilteredDoctors(filtered);
    setCurrentPage(1); // Reset to first page when filters change
  };

  // Apply filters whenever any filter criteria changes
  useEffect(() => {
    applyFiltersAndSort();
  }, [doctors, searchTerm, searchField, genderFilter, degreeFilter, typeFilter, departmentFilter, sortBy, sortOrder]);

  const handleSearch = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(event.target.value);
  };

  const totalItems = filteredDoctors.length;
  const totalPages = Math.ceil(totalItems / PAGE_SIZE);

  const paginatedData = filteredDoctors.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE
  );

  const handleViewSchedule = (doctorId: number | undefined) => {
    if (doctorId !== undefined) {
      navigate(`/admin/doctors/schedule/${doctorId}`);
    }
  };

  const handleViewDetail = (doctorId: number | undefined) => {
    if (doctorId !== undefined) {
      navigate(`/admin/doctors/detail/${doctorId}`);
    }
  };

  return (
    <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white px-4 pb-3 pt-4 dark:border-gray-800 dark:bg-white/[0.03] sm:px-6">
      <div className="flex flex-col gap-2 mb-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex justify-start items-center pt-5">
          <h2 className="text-lg font-semibold text-gray-800 dark:text-white/90">
            {t("doctors.filters.title")}
          </h2>
          <span className="ml-5 text-sm bg-base-600/20 text-base-600 py-1 px-4 rounded-full font-bold">
            {totalItems} {t("doctors.filters.count")}
          </span>
        </div>
      </div>
      
      {/* Enhanced Search and Filter Controls */}
      <div className="p-4 space-y-4">
        {/* Search Controls */}
        <div className="flex flex-wrap gap-4 items-end">
          <div className="flex-1 min-w-[300px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t("doctors.filters.search.label")}
            </label>
            <SearchInput
              placeholder={t("doctors.filters.search.placeholder")}
              value={searchTerm}
              onChange={handleSearch}
            />
          </div>
          
          <div className="min-w-[150px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t("doctors.filters.search.fieldLabel")}
            </label>
            <select
              value={searchField}
              onChange={(e) => setSearchField(e.target.value as typeof searchField)}
              className="w-full h-11 px-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">{t("doctors.filters.search.allFields")}</option>
              <option value="name">{t("doctors.filters.search.name")}</option>
              <option value="specialization">{t("doctors.filters.search.specialization")}</option>
              <option value="identity">{t("doctors.filters.search.identity")}</option>
              <option value="department">{t("doctors.filters.search.department")}</option>
            </select>
          </div>
        </div>
        
        {/* Filter and Sort Controls */}
        <div className="flex flex-wrap gap-4 items-center bg-gray-50 p-3 rounded-lg">
          {/* Gender Filter */}
          <div className="min-w-[120px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t("doctors.filters.gender.label")}
            </label>
            <select
              value={genderFilter}
              onChange={(e) => setGenderFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">{t("doctors.filters.gender.all")}</option>
              <option value="MALE">{t("doctors.filters.gender.male")}</option>
              <option value="FEMALE">{t("doctors.filters.gender.female")}</option>
              <option value="OTHER">{t("doctors.filters.gender.other")}</option>
            </select>
          </div>
          
          {/* Academic Degree Filter */}
          <div className="min-w-[140px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t("doctors.filters.degree.label")}
            </label>
            <select
              value={degreeFilter}
              onChange={(e) => setDegreeFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">{t("doctors.filters.degree.all")}</option>
              <option value="BS">BS</option>
              <option value="BS_CKI">BS CKI</option>
              <option value="BS_CKII">BS CKII</option>
              <option value="THS_BS">ThS.BS</option>
              <option value="TS_BS">TS.BS</option>
              <option value="PGS_TS_BS">PGS.TS.BS</option>
              <option value="GS_TS_BS">GS.TS.BS</option>
            </select>
          </div>
          
          {/* Type Filter */}
          <div className="min-w-[120px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t("doctors.filters.type.label")}
            </label>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">{t("doctors.filters.type.all")}</option>
              <option value="EXAMINATION">{t("doctors.filters.type.examination")}</option>
              <option value="SERVICE">{t("doctors.filters.type.service")}</option>
            </select>
          </div>
          
          {/* Department Filter */}
          <div className="min-w-[140px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t("doctors.filters.department.label")}
            </label>
            <select
              value={departmentFilter}
              onChange={(e) => setDepartmentFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">{t("doctors.filters.department.all")}</option>
              {[...new Set(doctors.map(d => d.departmentName))].map(dept => (
                <option key={dept} value={dept}>{dept}</option>
              ))}
            </select>
          </div>
          
          {/* Sort By */}
          <div className="min-w-[140px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t("doctors.filters.sort.label")}
            </label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="name">{t("doctors.filters.sort.name")}</option>
              <option value="degree">{t("doctors.filters.sort.degree")}</option>
              <option value="specialization">{t("doctors.filters.sort.specialization")}</option>
              <option value="department">{t("doctors.filters.sort.department")}</option>
              <option value="createdAt">{t("doctors.filters.sort.createdAt")}</option>
            </select>
          </div>
          
          {/* Sort Order */}
          <div className="flex gap-2">
            <button
              onClick={() => setSortOrder("asc")}
              className={`px-3 py-2 text-sm rounded-md transition-colors ${
                sortOrder === "asc"
                  ? "bg-blue-500 text-white"
                  : "bg-gray-200 text-gray-700 hover:bg-gray-300"
              }`}
            >
              {t("doctors.filters.sort.ascending")}
            </button>
            <button
              onClick={() => setSortOrder("desc")}
              className={`px-3 py-2 text-sm rounded-md transition-colors ${
                sortOrder === "desc"
                  ? "bg-blue-500 text-white"
                  : "bg-gray-200 text-gray-700 hover:bg-gray-300"
              }`}
            >
              {t("doctors.filters.sort.descending")}
            </button>
          </div>
          
          {/* Clear Filters */}
          <button
            onClick={() => {
              setSearchTerm("");
              setSearchField("all");
              setGenderFilter("");
              setDegreeFilter("");
              setTypeFilter("");
              setDepartmentFilter("");
              setSortBy("name");
              setSortOrder("asc");
            }}
            className="px-3 py-2 text-sm text-gray-600 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
          >
            {t("doctors.filters.actions.clearFilters")}
          </button>
        </div>
        
        {/* Results Summary */}
        {(searchTerm || genderFilter || degreeFilter || typeFilter || departmentFilter) && (
          <div className="text-sm text-gray-600">
            {t("doctors.filters.results.showing", { filtered: filteredDoctors.length, total: doctors.length })}
            {searchTerm && (
              <span className="ml-2 px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs">
                {t("doctors.filters.results.searchTag", { term: searchTerm })}
              </span>
            )}
            {genderFilter && (
              <span className="ml-2 px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs">
                {t("doctors.filters.results.genderTag", { 
                  gender: genderFilter === "MALE" ? t("doctors.filters.gender.male") : 
                          genderFilter === "FEMALE" ? t("doctors.filters.gender.female") : 
                          t("doctors.filters.gender.other")
                })}
              </span>
            )}
            {degreeFilter && (
              <span className="ml-2 px-2 py-1 bg-purple-100 text-purple-800 rounded-full text-xs">
                {t("doctors.filters.results.degreeTag", { degree: degreeFilter })}
              </span>
            )}
            {typeFilter && (
              <span className="ml-2 px-2 py-1 bg-orange-100 text-orange-800 rounded-full text-xs">
                {t("doctors.filters.results.typeTag", { 
                  type: typeFilter === "EXAMINATION" ? t("doctors.filters.type.examination") : t("doctors.filters.type.service")
                })}
              </span>
            )}
            {departmentFilter && (
              <span className="ml-2 px-2 py-1 bg-indigo-100 text-indigo-800 rounded-full text-xs">
                {t("doctors.filters.results.departmentTag", { department: departmentFilter })}
              </span>
            )}
          </div>
        )}
      </div>

      <div className="flex flex-col gap-4">
        {loading ? (
          <div className="text-center py-10">
            <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-base-600 mx-auto mb-4"></div>
            <p className="text-gray-600 dark:text-gray-400">
              {t("common.loading")}
            </p>
          </div>
        ) : paginatedData.length === 0 ? (
          <div className="text-center py-10 text-gray-500">
            {t("common.noResults")}
          </div>
        ) : (
          paginatedData.map((doctor) => (
            <DoctorCard
              key={doctor.doctorId}
              doctor={doctor}
              onViewSchedule={() => handleViewSchedule(doctor.doctorId)}
              onViewDetail={() => handleViewDetail(doctor.doctorId)}
            />
          ))
        )}
      </div>

      {/* Pagination */}
      {filteredDoctors.length > PAGE_SIZE && (
        <div className="px-4 py-4">
          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            itemsPerPage={PAGE_SIZE}
            totalItems={totalItems}
            onPageChange={setCurrentPage}
          />
        </div>
      )}
    </div>
  );
};

export default DoctorTable;
