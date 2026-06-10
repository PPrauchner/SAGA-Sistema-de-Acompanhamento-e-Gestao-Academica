/**
 * Hook que centraliza a lógica de "qual studentId usar" na ChecklistPage,
 * variando conforme o papel do usuário logado.
 *
 * - aluno: usa student_id do próprio currentUser (sem seletor exposto)
 * - orientador / coordenacao: usa selectedStudentId do AppContext com fallback
 *   para o primeiro aluno da lista de fixtures
 *
 * TODO: quando GET /api/v1/students estiver implementado, substituir
 * FIXTURE_STUDENTS por getStudents({ orientador_id }) / getStudents() aqui.
 * Nenhuma outra parte da ChecklistPage precisa mudar.
 */

import { useApp } from "@/app/context/AppContext";

export interface ChecklistStudent {
  id: string;
  label: string;
}

// Fixture até o endpoint real de discentes estar disponível (issue #41)
const FIXTURE_STUDENTS: ChecklistStudent[] = [
  { id: "aluno_apto", label: "Ana Apta" },
  { id: "aluno_risco", label: "Rui Risco" },
  { id: "aluno_regular", label: "Rita Regular" },
];

export interface UseChecklistStudentResult {
  studentId: string | null;
  students: ChecklistStudent[] | null;
  setStudentId: (id: string) => void;
}

export function useChecklistStudent(): UseChecklistStudentResult {
  const { currentUser, selectedStudentId, setSelectedStudentId } = useApp();

  if (currentUser?.role === "aluno") {
    return {
      studentId: currentUser.student_id ?? currentUser.id,
      students: null,
      setStudentId: (_id: string) => {},
    };
  }

  return {
    studentId: selectedStudentId ?? FIXTURE_STUDENTS[0].id,
    students: FIXTURE_STUDENTS,
    setStudentId: (id: string) => setSelectedStudentId(id),
  };
}
