import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, API_BASE_URL, type ActivityCreate, type SolveRequest } from "./client";

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: async () => {
      const res = await api.me();
      if (!res.ok) return null;
      return (await res.json()) as { email: string; name: string };
    },
  });
}

export function useSchoolYears() {
  return useQuery({ queryKey: ["schoolYears"], queryFn: api.schoolYears.list });
}

export function useTeachers() {
  return useQuery({ queryKey: ["teachers"], queryFn: api.teachers.list });
}

export function useCreateTeacher() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ initials, fullName }: { initials: string; fullName: string }) =>
      api.teachers.create(initials, fullName),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["teachers"] }),
  });
}

export function useDeleteTeacher() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.teachers.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["teachers"] }),
  });
}

export function useTeacherUnavailabilities(teacherId: number) {
  return useQuery({
    queryKey: ["teacherUnavailabilities", teacherId],
    queryFn: () => api.teachers.unavailabilities(teacherId),
  });
}

export function useUpdateTeacher() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, initials, fullName }: { id: number; initials: string; fullName: string }) =>
      api.teachers.update(id, initials, fullName),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["teachers"] }),
  });
}

export function useAddTeacherUnavailability(teacherId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Parameters<typeof api.teachers.addUnavailability>[0]) =>
      api.teachers.addUnavailability(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["teacherUnavailabilities", teacherId] }),
  });
}

export function useRemoveTeacherUnavailability(teacherId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.teachers.removeUnavailability(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["teacherUnavailabilities", teacherId] }),
  });
}

export function useTeacherQualifications(teacherId: number) {
  return useQuery({
    queryKey: ["teacherQualifications", teacherId],
    queryFn: () => api.teachers.qualifications(teacherId),
  });
}

export function useAddTeacherQualification(teacherId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ subjectId, weeklyHours }: { subjectId: number; weeklyHours: number | null }) =>
      api.teachers.addQualification(teacherId, subjectId, weeklyHours),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["teacherQualifications", teacherId] }),
  });
}

export function useUpdateTeacherQualification(teacherId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, weeklyHours }: { id: number; weeklyHours: number | null }) =>
      api.teachers.updateQualification(id, weeklyHours),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["teacherQualifications", teacherId] }),
  });
}

export function useRemoveTeacherQualification(teacherId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.teachers.removeQualification(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["teacherQualifications", teacherId] }),
  });
}

export function useSubjects(schoolYearId: number | undefined) {
  return useQuery({
    queryKey: ["subjects", schoolYearId],
    queryFn: () => api.subjects.list(schoolYearId as number),
    enabled: schoolYearId !== undefined,
  });
}

export function useActivities(schoolYearId: number | undefined) {
  return useQuery({
    queryKey: ["activities", schoolYearId],
    queryFn: () => api.activities.list(schoolYearId as number),
    enabled: schoolYearId !== undefined,
  });
}

export function useCreateActivity() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ActivityCreate) => api.activities.create(payload),
    onSuccess: (_data, payload) =>
      qc.invalidateQueries({ queryKey: ["activities", payload.school_year_id] }),
  });
}

export function useSolve() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: SolveRequest) => api.solve.run(payload),
    onSuccess: (_data, payload) =>
      qc.invalidateQueries({ queryKey: ["activeTimetable", payload.school_year_id] }),
  });
}

export function useActivateVariant(schoolYearId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (generatedTimetableId: number) => api.solve.activateVariant(generatedTimetableId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["activeTimetable", schoolYearId] }),
  });
}

export function useActiveTimetable(schoolYearId: number | undefined) {
  return useQuery({
    queryKey: ["activeTimetable", schoolYearId],
    queryFn: () => api.solve.active(schoolYearId as number),
    enabled: schoolYearId !== undefined,
    retry: false,
  });
}

export interface ClassGroupInfo {
  id: number;
  label: string;
  className: string;
  trinnLevel: number;
}

/** All class-groups across every class for a school year, with a
 * human-readable label (e.g. "9A" for the whole class, "9A (half1)" for a
 * split group) -- shared by ActivitiesPage and TimetableGridPage. */
export function useAllClassGroups(schoolYearId: number | undefined) {
  return useQuery({
    queryKey: ["allClassGroups", schoolYearId],
    queryFn: async (): Promise<ClassGroupInfo[]> => {
      const trinnList = await api.trinn.list(schoolYearId as number);
      const classesByTrinn = await Promise.all(trinnList.map((t) => api.classes.list(t.id)));
      const classEntries = trinnList.flatMap((t, i) => classesByTrinn[i].map((c) => ({ t, c })));
      const groupsByClass = await Promise.all(
        classEntries.map(({ c }) =>
          fetch(`${API_BASE_URL}/api/class-groups?school_class_id=${c.id}`, {
            credentials: "include",
          }).then((r) => r.json() as Promise<{ id: number; label: string }[]>),
        ),
      );
      return classEntries.flatMap(({ t, c }, i) =>
        groupsByClass[i].map((g) => ({
          id: g.id,
          label: g.label === "whole" ? c.name : `${c.name} (${g.label})`,
          className: c.name,
          trinnLevel: t.level,
        })),
      );
    },
    enabled: schoolYearId !== undefined,
  });
}
