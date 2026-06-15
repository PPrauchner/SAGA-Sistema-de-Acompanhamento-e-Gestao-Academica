/**
 * Hook React para autenticação Firebase e identidade do usuário logado.
 *
 * Responsabilidades:
 * - Assinar onIdTokenChanged do Firebase Auth para rastrear o estado de autenticação
 *   e manter o ID token sempre atual: o SDK renova o token automaticamente (~a cada
 *   1h) e re-dispara o listener, evitando 401 em chamadas à API após a expiração.
 * - Após login bem-sucedido, chamar GET /api/v1/auth/me para obter role, programa_id,
 *   student_id (se aluno) ou advisor_id (se orientador) — dados não disponíveis no
 *   token sem chamada à API.
 * - Expor: { currentUser, role, programaId, studentId, advisorId, token, login,
 *   logout, loading }.
 * - `token`: string retornada por user.getIdToken() — incluída no header
 *   Authorization: Bearer <token> em todas as chamadas à API do backend.
 * - `login(email, senha)`: chama Firebase Auth signInWithEmailAndPassword.
 * - `logout()`: chama Firebase Auth signOut e limpa estado local.
 * - `loading`: true enquanto onIdTokenChanged ainda não resolveu o estado inicial
 *   (evita flash de tela de login para usuários já autenticados).
 */

import { useCallback, useEffect, useState } from "react";
import {
  onIdTokenChanged,
  signInWithEmailAndPassword,
  signOut,
  type User as FirebaseUser,
} from "firebase/auth";

import { auth } from "@/lib/firebase";
import { getMe, type AuthProfile } from "@/api/authApi";
import type { UserRole } from "@/app/context/AppContext";

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

export function useAuth(): UseAuthResult {
  const [currentUser, setCurrentUser] = useState<FirebaseUser | null>(null);
  const [profile, setProfile] = useState<AuthProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = onIdTokenChanged(auth, async (user) => {
      try {
        if (user) {
          const idToken = await user.getIdToken();
          setCurrentUser(user);
          setToken(idToken);
          setProfile(await getMe(idToken));
        } else {
          setCurrentUser(null);
          setToken(null);
          setProfile(null);
        }
      } finally {
        // Garante que o gate de loading sempre resolva, mesmo se getMe falhar.
        setLoading(false);
      }
    });
    return unsubscribe;
  }, []);

  const login = useCallback(async (email: string, senha: string): Promise<void> => {
    // onIdTokenChanged dispara em seguida e carrega o perfil.
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
