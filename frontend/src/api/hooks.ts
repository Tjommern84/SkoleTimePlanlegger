import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  api,
  type ActivityCreate,
  type PeriodDefinitionCreate,
  type SolveRequest,
  type SubjectCreate,
  type SubjectHourAllocationCreate,
  type ZoneSummary,
} from "./client";

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: async () => {
      const res = await api.me();
      if (!res.ok) return null;
      return (await res.json()) as { email: string; name: string; zones: ZoneSummary[] };
    },
  });
}

export function useZoneMembers() {
  return useQuery({ queryKey: ["zoneMembers"], queryFn: api.zones.members.list });
}

export function useZoneInvitations(enabled: boolean = true) {
  return useQuery({ queryKey: ["zoneInvitations"], queryFn: api.zones.invitations.list, enabled });
}

export function useCreateInvitation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (email: string) => api.zones.invitations.create(email),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["zoneInvitations"] }),
  });
}

export function useRevokeInvitation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.zones.invitations.revoke(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["zoneInvitations"] }),
  });
}

export function useRemoveMember() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (userId: number) => api.zones.members.remove(userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["zoneMembers"] }),
  });
}

export function useRenameZone() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => api.zones.rename(name),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me"] }),
  });
}

export function useSchoolYears() {
  return useQuery({ queryKey: ["schoolYears"], queryFn: api.schoolYears.list });
}

export function useCreateSchoolYear() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (label: string) => api.schoolYears.create(label),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["schoolYears"] }),
  });
}

export function useUpdateSchoolYear() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, label }: { id: number; label: string }) => api.schoolYears.update(id, label),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["schoolYears"] }),
  });
}

export function useDeleteSchoolYear() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.schoolYears.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["schoolYears"] }),
  });
}

export function useTrinn(schoolYearId: number | undefined) {
  return useQuery({
    queryKey: ["trinn", schoolYearId],
    queryFn: () => api.trinn.list(schoolYearId as number),
    enabled: schoolYearId !== undefined,
  });
}

export function useCreateTrinn() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ schoolYearId, level }: { schoolYearId: number; level: number }) =>
      api.trinn.create(schoolYearId, level),
    onSuccess: (_data, { schoolYearId }) => qc.invalidateQueries({ queryKey: ["trinn", schoolYearId] }),
  });
}

export function useUpdateTrinn() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, schoolYearId, level }: { id: number; schoolYearId: number; level: number }) =>
      api.trinn.update(id, schoolYearId, level),
    onSuccess: (_data, { schoolYearId }) => qc.invalidateQueries({ queryKey: ["trinn", schoolYearId] }),
  });
}

export function useDeleteTrinn() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.trinn.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["trinn"] }),
  });
}

export function useClasses(trinnId: number | undefined) {
  return useQuery({
    queryKey: ["classes", trinnId],
    queryFn: () => api.classes.list(trinnId as number),
    enabled: trinnId !== undefined,
  });
}

export function useCreateClass() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ trinnId, name }: { trinnId: number; name: string }) => api.classes.create(trinnId, name),
    onSuccess: (_data, { trinnId }) => qc.invalidateQueries({ queryKey: ["classes", trinnId] }),
  });
}

export function useUpdateClass() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, trinnId, name }: { id: number; trinnId: number; name: string }) =>
      api.classes.update(id, trinnId, name),
    onSuccess: (_data, { trinnId }) => qc.invalidateQueries({ queryKey: ["classes", trinnId] }),
  });
}

export function useDeleteClass() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.classes.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["classes"] }),
  });
}

export function useClassGroups(schoolClassId: number | undefined) {
  return useQuery({
    queryKey: ["classGroups", schoolClassId],
    queryFn: () => api.classGroups.list(schoolClassId as number),
    enabled: schoolClassId !== undefined,
  });
}

export function useCreateClassGroup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ schoolClassId, label }: { schoolClassId: number; label: string }) =>
      api.classGroups.create(schoolClassId, label),
    onSuccess: (_data, { schoolClassId }) => qc.invalidateQueries({ queryKey: ["classGroups", schoolClassId] }),
  });
}

export function useUpdateClassGroup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, schoolClassId, label }: { id: number; schoolClassId: number; label: string }) =>
      api.classGroups.update(id, schoolClassId, label),
    onSuccess: (_data, { schoolClassId }) => qc.invalidateQueries({ queryKey: ["classGroups", schoolClassId] }),
  });
}

export function useDeleteClassGroup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.classGroups.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["classGroups"] }),
  });
}

export function usePeriods(schoolYearId: number | undefined) {
  return useQuery({
    queryKey: ["periods", schoolYearId],
    queryFn: () => api.periods.list(schoolYearId as number),
    enabled: schoolYearId !== undefined,
  });
}

export function useCreatePeriod() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: PeriodDefinitionCreate) => api.periods.create(payload),
    onSuccess: (_data, payload) => qc.invalidateQueries({ queryKey: ["periods", payload.school_year_id] }),
  });
}

export function useUpdatePeriod() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: PeriodDefinitionCreate }) =>
      api.periods.update(id, payload),
    onSuccess: (_data, { payload }) => qc.invalidateQueries({ queryKey: ["periods", payload.school_year_id] }),
  });
}

export function useDeletePeriod() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.periods.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["periods"] }),
  });
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

export function useCreateSubject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: SubjectCreate) => api.subjects.create(payload),
    onSuccess: (_data, payload) => qc.invalidateQueries({ queryKey: ["subjects", payload.school_year_id] }),
  });
}

export function useUpdateSubject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: SubjectCreate }) => api.subjects.update(id, payload),
    onSuccess: (_data, { payload }) => qc.invalidateQueries({ queryKey: ["subjects", payload.school_year_id] }),
  });
}

export function useDeleteSubject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.subjects.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["subjects"] }),
  });
}

export function useSubjectHourAllocations(subjectId: number | undefined) {
  return useQuery({
    queryKey: ["subjectHourAllocations", subjectId],
    queryFn: () => api.subjects.hourAllocations(subjectId as number),
    enabled: subjectId !== undefined,
  });
}

export function useCreateSubjectHourAllocation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: SubjectHourAllocationCreate) => api.subjects.createHourAllocation(payload),
    onSuccess: (_data, payload) =>
      qc.invalidateQueries({ queryKey: ["subjectHourAllocations", payload.subject_id] }),
  });
}

export function useUpdateSubjectHourAllocation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: SubjectHourAllocationCreate }) =>
      api.subjects.updateHourAllocation(id, payload),
    onSuccess: (_data, { payload }) =>
      qc.invalidateQueries({ queryKey: ["subjectHourAllocations", payload.subject_id] }),
  });
}

export function useDeleteSubjectHourAllocation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.subjects.removeHourAllocation(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["subjectHourAllocations"] }),
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

export function useDeleteActivity() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id }: { id: number; schoolYearId: number }) => api.activities.remove(id),
    onSuccess: (_data, { schoolYearId }) => qc.invalidateQueries({ queryKey: ["activities", schoolYearId] }),
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
      const groupsByClass = await Promise.all(classEntries.map(({ c }) => api.classGroups.list(c.id)));
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
