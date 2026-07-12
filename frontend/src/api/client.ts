import type { components } from "../types/domain";

// Empty string in local dev: Vite's dev-server proxy forwards relative
// /api and /auth paths to the backend (see vite.config.ts). In production
// the frontend (Vercel) and backend (Render) are different origins, so
// this must be set to the deployed backend's absolute URL at build time.
export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? "";

export type SchoolYear = components["schemas"]["SchoolYearRead"];
export type Subject = components["schemas"]["SubjectRead"];
export type SubjectCreate = components["schemas"]["SubjectCreate"];
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
export type SubjectHourAllocationCreate = components["schemas"]["SubjectHourAllocationCreate"];
export type PeriodDefinition = components["schemas"]["PeriodDefinitionRead"];
export type PeriodDefinitionCreate = components["schemas"]["PeriodDefinitionCreate"];
export type TeacherUnavailability = components["schemas"]["TeacherUnavailabilityRead"];
export type TeacherUnavailabilityCreate = components["schemas"]["TeacherUnavailabilityCreate"];
export type TeacherSubjectQualification = components["schemas"]["TeacherSubjectQualificationRead"];
export type DayOfWeek = TeacherUnavailabilityCreate["day_of_week"];

export interface ZoneSummary {
  id: number;
  name: string;
  role: "owner" | "member";
}

export interface ZoneMember {
  user_id: number;
  email: string;
  name: string;
  role: "owner" | "member";
  joined_at: string;
}

export interface ZoneInvitation {
  id: number;
  email: string;
  status: "pending" | "accepted" | "revoked";
  created_at: string;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

// The zone the frontend is currently "switched into" -- attached as a
// header to every request by request() below, rather than threaded
// through every hook's arguments, since it's a cross-cutting transport
// concern (like credentials: "include" already is) rather than page
// business logic. Most backend routes actually derive the zone from a
// resource id they already receive (school_year_id, teacher_id, ...) and
// ignore this header entirely -- see backend/app/api/deps.py. Only the
// handful of "root" endpoints with no such id (list/create school-years,
// list/create teachers) require it.
let _activeZoneId: number | null = null;

export function setActiveZoneId(id: number | null) {
  _activeZoneId = id;
}

export function getActiveZoneId(): number | null {
  return _activeZoneId;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };
  if (_activeZoneId != null) headers["X-Zone-Id"] = String(_activeZoneId);

  const res = await fetch(`${API_BASE_URL}/api${path}`, {
    ...init,
    credentials: "include",
    headers,
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
    update: (id: number, label: string) =>
      request<SchoolYear>(`/school-years/${id}`, { method: "PATCH", body: JSON.stringify({ label }) }),
    remove: (id: number) => request<void>(`/school-years/${id}`, { method: "DELETE" }),
  },
  trinn: {
    list: (schoolYearId: number) => request<Trinn[]>(`/trinn?school_year_id=${schoolYearId}`),
    create: (schoolYearId: number, level: number) =>
      request<Trinn>("/trinn", { method: "POST", body: JSON.stringify({ school_year_id: schoolYearId, level }) }),
    update: (id: number, schoolYearId: number, level: number) =>
      request<Trinn>(`/trinn/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ school_year_id: schoolYearId, level }),
      }),
    remove: (id: number) => request<void>(`/trinn/${id}`, { method: "DELETE" }),
  },
  classes: {
    list: (trinnId: number) => request<SchoolClass[]>(`/classes?trinn_id=${trinnId}`),
    create: (trinnId: number, name: string) =>
      request<SchoolClass>("/classes", { method: "POST", body: JSON.stringify({ trinn_id: trinnId, name }) }),
    update: (id: number, trinnId: number, name: string) =>
      request<SchoolClass>(`/classes/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ trinn_id: trinnId, name }),
      }),
    remove: (id: number) => request<void>(`/classes/${id}`, { method: "DELETE" }),
  },
  classGroups: {
    list: (schoolClassId: number) => request<ClassGroup[]>(`/class-groups?school_class_id=${schoolClassId}`),
    create: (schoolClassId: number, label: string) =>
      request<ClassGroup>("/class-groups", {
        method: "POST",
        body: JSON.stringify({ school_class_id: schoolClassId, label }),
      }),
    update: (id: number, schoolClassId: number, label: string) =>
      request<ClassGroup>(`/class-groups/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ school_class_id: schoolClassId, label }),
      }),
    remove: (id: number) => request<void>(`/class-groups/${id}`, { method: "DELETE" }),
  },
  periods: {
    list: (schoolYearId: number) => request<PeriodDefinition[]>(`/periods?school_year_id=${schoolYearId}`),
    create: (payload: PeriodDefinitionCreate) =>
      request<PeriodDefinition>("/periods", { method: "POST", body: JSON.stringify(payload) }),
    update: (id: number, payload: PeriodDefinitionCreate) =>
      request<PeriodDefinition>(`/periods/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
    remove: (id: number) => request<void>(`/periods/${id}`, { method: "DELETE" }),
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
    create: (payload: SubjectCreate) =>
      request<Subject>("/subjects", { method: "POST", body: JSON.stringify(payload) }),
    update: (id: number, payload: SubjectCreate) =>
      request<Subject>(`/subjects/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
    remove: (id: number) => request<void>(`/subjects/${id}`, { method: "DELETE" }),
    hourAllocations: (subjectId: number) =>
      request<SubjectHourAllocation[]>(`/subject-hour-allocations?subject_id=${subjectId}`),
    createHourAllocation: (payload: SubjectHourAllocationCreate) =>
      request<SubjectHourAllocation>("/subject-hour-allocations", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    updateHourAllocation: (id: number, payload: SubjectHourAllocationCreate) =>
      request<SubjectHourAllocation>(`/subject-hour-allocations/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    removeHourAllocation: (id: number) => request<void>(`/subject-hour-allocations/${id}`, { method: "DELETE" }),
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

  zones: {
    rename: (name: string) =>
      request<{ id: number; name: string }>("/zones/current", { method: "PATCH", body: JSON.stringify({ name }) }),
    members: {
      list: () => request<ZoneMember[]>("/zones/current/members"),
      remove: (userId: number) => request<void>(`/zones/current/members/${userId}`, { method: "DELETE" }),
    },
    invitations: {
      list: () => request<ZoneInvitation[]>("/zones/current/invitations"),
      create: (email: string) =>
        request<ZoneInvitation>("/zones/current/invitations", { method: "POST", body: JSON.stringify({ email }) }),
      revoke: (id: number) => request<void>(`/zones/current/invitations/${id}`, { method: "DELETE" }),
    },
  },
};
