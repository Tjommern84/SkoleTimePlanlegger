import type { components } from "../types/domain";

// Empty string in local dev: Vite's dev-server proxy forwards relative
// /api and /auth paths to the backend (see vite.config.ts). In production
// the frontend (Vercel) and backend (Render) are different origins, so
// this must be set to the deployed backend's absolute URL at build time.
export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? "";

export type SchoolYear = components["schemas"]["SchoolYearRead"];
export type Subject = components["schemas"]["SubjectRead"];
export type Teacher = components["schemas"]["TeacherRead"];
export type Activity = components["schemas"]["ActivityRead"];
export type ActivityCreate = components["schemas"]["ActivityCreate"];
export type SolveRequest = components["schemas"]["SolveRequest"];
export type SolveResponse = components["schemas"]["SolveResponse"];
export type VariantSummary = components["schemas"]["VariantSummary"];
export type GeneratedTimetable = components["schemas"]["GeneratedTimetableRead"];
export type Trinn = components["schemas"]["TrinnRead"];
export type SchoolClass = components["schemas"]["SchoolClassRead"];
export type ClassGroup = components["schemas"]["ClassGroupRead"];
export type SubjectHourAllocation = components["schemas"]["SubjectHourAllocationRead"];
export type TeacherUnavailability = components["schemas"]["TeacherUnavailabilityRead"];
export type TeacherUnavailabilityCreate = components["schemas"]["TeacherUnavailabilityCreate"];
export type TeacherSubjectQualification = components["schemas"]["TeacherSubjectQualificationRead"];
export type DayOfWeek = TeacherUnavailabilityCreate["day_of_week"];

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}/api${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  health: () => request<{ status: string }>("/health"),
  me: () => fetch(`${API_BASE_URL}/auth/me`, { credentials: "include" }),

  schoolYears: {
    list: () => request<SchoolYear[]>("/school-years"),
    create: (label: string) => request<SchoolYear>("/school-years", { method: "POST", body: JSON.stringify({ label }) }),
  },
  trinn: {
    list: (schoolYearId: number) => request<Trinn[]>(`/trinn?school_year_id=${schoolYearId}`),
  },
  classes: {
    list: (trinnId: number) => request<SchoolClass[]>(`/classes?trinn_id=${trinnId}`),
  },
  teachers: {
    list: () => request<Teacher[]>("/teachers"),
    create: (initials: string, fullName: string) =>
      request<Teacher>("/teachers", { method: "POST", body: JSON.stringify({ initials, full_name: fullName }) }),
    update: (id: number, initials: string, fullName: string) =>
      request<Teacher>(`/teachers/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ initials, full_name: fullName }),
      }),
    remove: (id: number) => request<void>(`/teachers/${id}`, { method: "DELETE" }),
    unavailabilities: (teacherId: number) =>
      request<TeacherUnavailability[]>(`/teacher-unavailabilities?teacher_id=${teacherId}`),
    addUnavailability: (payload: TeacherUnavailabilityCreate) =>
      request<TeacherUnavailability>("/teacher-unavailabilities", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    removeUnavailability: (id: number) => request<void>(`/teacher-unavailabilities/${id}`, { method: "DELETE" }),
    qualifications: (teacherId: number) =>
      request<TeacherSubjectQualification[]>(`/teacher-subject-qualifications?teacher_id=${teacherId}`),
    addQualification: (teacherId: number, subjectId: number, weeklyHours: number | null) =>
      request<TeacherSubjectQualification>("/teacher-subject-qualifications", {
        method: "POST",
        body: JSON.stringify({ teacher_id: teacherId, subject_id: subjectId, weekly_hours: weeklyHours }),
      }),
    updateQualification: (id: number, weeklyHours: number | null) =>
      request<TeacherSubjectQualification>(`/teacher-subject-qualifications/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ weekly_hours: weeklyHours }),
      }),
    removeQualification: (id: number) => request<void>(`/teacher-subject-qualifications/${id}`, { method: "DELETE" }),
  },
  subjects: {
    list: (schoolYearId: number) => request<Subject[]>(`/subjects?school_year_id=${schoolYearId}`),
    hourAllocations: (subjectId: number) =>
      request<SubjectHourAllocation[]>(`/subject-hour-allocations?subject_id=${subjectId}`),
  },
  activities: {
    list: (schoolYearId: number) => request<Activity[]>(`/activities?school_year_id=${schoolYearId}`),
    create: (payload: ActivityCreate) =>
      request<Activity>("/activities", { method: "POST", body: JSON.stringify(payload) }),
    remove: (id: number) => request<void>(`/activities/${id}`, { method: "DELETE" }),
  },
  solve: {
    run: (payload: SolveRequest) => request<SolveResponse>("/solve", { method: "POST", body: JSON.stringify(payload) }),
    active: (schoolYearId: number) =>
      request<GeneratedTimetable>(`/school-years/${schoolYearId}/timetable/active`),
    activateVariant: (generatedTimetableId: number) =>
      request<VariantSummary>(`/generated-timetables/${generatedTimetableId}/activate`, { method: "POST" }),
  },
  exportUrl: (generatedTimetableId: number) =>
    `${API_BASE_URL}/api/generated-timetables/${generatedTimetableId}/export.xlsx`,
};
