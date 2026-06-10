/**
 * Hook React para autenticação Firebase e identidade do usuário logado.
 *
 * Responsabilidades:
 * - Assinar onAuthStateChanged do Firebase Auth para rastrear estado de autenticação.
 * - Após login bem-sucedido, chamar GET /api/v1/auth/me para obter role, programa_id,
 *   student_id (se aluno) ou advisor_id (se orientador) — dados não disponíveis no
 *   token sem chamada à API.
 * - Expor: { currentUser, role, programaId, studentId, advisorId, token, login,
 *   logout, loading }.
 * - `token`: string retornada por user.getIdToken() — incluída no header
 *   Authorization: Bearer <token> em todas as chamadas à API do backend.
 * - `login(email, senha)`: chama Firebase Auth signInWithEmailAndPassword.
 * - `logout()`: chama Firebase Auth signOut e limpa estado local.
 * - `loading`: true enquanto onAuthStateChanged ainda não resolveu o estado inicial
 *   (evita flash de tela de login para usuários já autenticados).
 */

import { useCallback, useEffect, useState } from "react";
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut,
  type User as FirebaseUser,
} from "firebase/auth";

import { auth } from "@/lib/firebase";
import type { UserRole } from "@/app/context/AppContext";

// Base da API do backend; em dev o FastAPI roda em http://localhost:8000.
const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

/** Perfil retornado por GET /api/v1/auth/me, já em camelCase. */
interface AuthProfile {
  uid: string;
  email: string;
  nome: string;
  role: UserRole;
  programaId: string;
  studentId: string | null;
  advisorId: string | null;
}

/** Valor exposto pelo hook useAuth. */
interface UseAuthResult {
  currentUser: FirebaseUser | null;
  profile: AuthProfile | null;
  role: UserRole | null;
  programaId: string | null;
  studentId: string | null;
  advisorId: string | null;
  token: string | null;
  login: (email: string, senha: string) => Promise<void>;
  logout: () => Promise<void>;
  loading: boolean;
}

async function fetchProfile(token: string): Promise<AuthProfile> {
  const response = await fetch(`${API_URL}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    throw new Error(`Falha ao carregar perfil (HTTP ${response.status})`);
  }
  const data = await response.json();
  return {
    uid: data.uid,
    email: data.email,
    nome: data.nome,
    role: data.role,
    programaId: data.programa_id,
    studentId: data.student_id ?? null,
    advisorId: data.advisor_id ?? null,
  };
}

export function useAuth(): UseAuthResult {
  const [currentUser, setCurrentUser] = useState<FirebaseUser | null>(null);
  const [profile, setProfile] = useState<AuthProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (user) {
        const idToken = await user.getIdToken();
        setCurrentUser(user);
        setToken(idToken);
        setProfile(await fetchProfile(idToken));
      } else {
        setCurrentUser(null);
        setToken(null);
        setProfile(null);
      }
      setLoading(false);
    });
    return unsubscribe;
  }, []);

  const login = useCallback(async (email: string, senha: string): Promise<void> => {
    // onAuthStateChanged dispara em seguida e carrega o perfil.
    await signInWithEmailAndPassword(auth, email, senha);
  }, []);

  const logout = useCallback(async (): Promise<void> => {
    await signOut(auth);
  }, []);

  return {
    currentUser,
    profile,
    role: profile?.role ?? null,
    programaId: profile?.programaId ?? null,
    studentId: profile?.studentId ?? null,
    advisorId: profile?.advisorId ?? null,
    token,
    login,
    logout,
    loading,
  };
}
