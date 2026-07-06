/**
 * Hook que centraliza a lógica de "qual studentId usar" nas páginas de Checklist
 * e Inferência, variando conforme o papel do usuário logado.
 *
 * - aluno: usa student_id do próprio currentUser (sem seletor exposto)
 * - orientador / coordenacao: busca a lista real via GET /api/v1/students
 *   (o backend já filtra pelo papel via A01 — orientador vê só seus orientandos,
 *   coordenação vê todos)
 */

import { useEffect, useState } from "react";
import { useApp } from "@/app/context/AppContext";
import { useAuth } from "@/hooks/useAuth";
import { getStudents } from "@/api/studentsApi";

export interface ChecklistStudent {
  id: string;
  label: string;
}

export interface UseChecklistStudentResult {
  studentId: string | null;
  students: ChecklistStudent[] | null;
  setStudentId: (id: string) => void;
}

/**
 * @param autoSelectFirst Quando não há seleção prévia, cai no primeiro aluno da lista.
 *   Padrão `true` (checklist/inferência, só leitura). Passe `false` em fluxos de edição
 *   (ex: plano de trabalho) onde nada deve ser aberto/alterado sem escolha explícita.
 */
export function useChecklistStudent(
  { autoSelectFirst = true }: { autoSelectFirst?: boolean } = {},
): UseChecklistStudentResult {
  const { currentUser, selectedStudentId, setSelectedStudentId } = useApp();
  const { token } = useAuth();
  const [students, setStudents] = useState<ChecklistStudent[]>([]);

  const isAluno = currentUser?.role === "aluno";

  useEffect(() => {
    if (isAluno || !token) return;
    getStudents(token)
      .then((list) =>
        setStudents(list.map((s) => ({ id: s.id, label: s.nome })))
      )
      .catch(() => setStudents([]));
  }, [isAluno, token]);

  if (isAluno) {
    return {
      studentId: currentUser.student_id ?? currentUser.id,
      students: null,
      setStudentId: () => {},
    };
  }

  const studentId = selectedStudentId ?? (autoSelectFirst ? students[0]?.id ?? null : null);

  return {
    studentId,
    students,
    setStudentId: (id: string) => setSelectedStudentId(id),
  };
}
