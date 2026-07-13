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
 * - Quando GET /auth/me falha por indisponibilidade transitória (backend fora/lento/cold
 *   start — 5xx ou erro de rede) mas a sessão Firebase é válida, capturar o erro em
 *   `profileError` em vez de propagá-lo: o usuário continua autenticado (`currentUser`
 *   setado) e a app oferece estado degradado + retry via `retryProfile()`, sem ir ao login.
 * - Quando a falha é 4xx (token inválido, claims ausentes ou perfil inexistente —
 *   401/403/404), encerrar a sessão: é falha permanente e o usuário deve ir ao login.
 * - Expor: { currentUser, profile, profileError, role, programaId, studentId, advisorId,
 *   token, login, logout, retryProfile, loading }.
 * - `token`: string retornada por user.getIdToken() — incluída no header
 *   Authorization: Bearer <token> em todas as chamadas à API do backend.
 * - `login(email, senha)`: chama Firebase Auth signInWithEmailAndPassword.
 * - `logout()`: chama Firebase Auth signOut e limpa estado local.
 * - `loading`: true enquanto onIdTokenChanged ainda não resolveu o estado inicial
 *   (evita flash de tela de login para usuários já autenticados).
 */

import { useCallback, useEffect, useState, useRef } from "react";
import {
  GoogleAuthProvider,
  onIdTokenChanged,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut,
  type User as FirebaseUser,
} from "firebase/auth";

import { auth } from "@/lib/firebase";
import { getMe, activateGoogleFirstAccess, type AuthProfile } from "@/api/authApi";
import { ApiError } from "@/api/http";
import type { UserRole } from "@/app/context/AppContext";

/** Valor exposto pelo hook useAuth. */
interface UseAuthResult {
  currentUser: FirebaseUser | null;
  profile: AuthProfile | null;
  profileError: boolean;
  role: UserRole | null;
  programaId: string | null;
  studentId: string | null;
  advisorId: string | null;
  token: string | null;
  login: (email: string, senha: string) => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  logout: () => Promise<void>;
  retryProfile: () => Promise<void>;
  loading: boolean;
  profileLoading: boolean;
}

export function useAuth(): UseAuthResult {
  const [currentUser, setCurrentUser] = useState<FirebaseUser | null>(null);
  const [profile, setProfile] = useState<AuthProfile | null>(null);
  const [profileError, setProfileError] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [profileLoading, setProfileLoading] = useState(false);
  const isActivatingRef = useRef(false);

  /**
   * Carrega o perfil via GET /auth/me com o ID token dado.
   *
   * Distingue dois tipos de falha pelo status HTTP:
   * - 4xx (token inválido, claims ausentes, perfil inexistente — 401/403/404): falha
   *   permanente que o retry não resolve. Encerra a sessão Firebase para que a guarda de
   *   rota envie o usuário ao login.
   * - 5xx ou erro de rede (backend fora/lento/cold start): indisponibilidade transitória.
   *   Sinaliza `profileError` sem propagar a exceção nem apagar um perfil já carregado — o
   *   usuário permanece na app em estado degradado, com retry.
   */
  const loadProfile = useCallback(async (idToken: string): Promise<void> => {
    setProfileLoading(true);
    try {
      setProfile(await getMe(idToken));
      setProfileError(false);
    } catch (err) {
      if (err instanceof ApiError && err.status < 500) {
        if (!isActivatingRef.current) {
          await signOut(auth);
        }
        return;
      }
      setProfileError(true);
    } finally {
      setProfileLoading(false);
    }
  }, []);

  useEffect(() => {
    const unsubscribe = onIdTokenChanged(auth, async (user) => {
      try {
        if (user) {
          const idToken = await user.getIdToken();
          setCurrentUser(user);
          setToken(idToken);
          setLoading(false);
          await loadProfile(idToken);
        } else {
          setCurrentUser(null);
          setToken(null);
          setProfile(null);
          setProfileError(false);
          setLoading(false);
        }
      } catch (e) {
        setLoading(false);
      }
    });
    return unsubscribe;
  }, [loadProfile]);

  const login = useCallback(async (email: string, senha: string): Promise<void> => {
    // onIdTokenChanged dispara em seguida e carrega o perfil.
    await signInWithEmailAndPassword(auth, email, senha);
  }, []);

  /**
   * Autentica via Google e verifica se o email pertence a uma conta ativa no SAGA.
   *
   * Se o usuário não existir no SAGA (claims ausentes → GET /auth/me retorna 4xx),
   * encerra a sessão e lança um erro com mensagem de negócio para exibição na UI.
   * O onIdTokenChanged também dispara após signInWithPopup e pode chamar loadProfile
   * em paralelo — ambos são idempotentes neste cenário.
   */
  const loginWithGoogle = useCallback(async (): Promise<void> => {
    isActivatingRef.current = true;
    try {
      const result = await signInWithPopup(auth, new GoogleAuthProvider());
      const idToken = await result.user.getIdToken();
      try {
        const p = await getMe(idToken);
        setProfile(p);
        setProfileError(false);
      } catch (err) {
        const isUnknownAccount = err instanceof ApiError && err.status < 500;
        if (isUnknownAccount) {
          try {
            await activateGoogleFirstAccess(idToken);
            // Sucesso: forçar refresh do token para pegar as novas claims
            const refreshedToken = await result.user.getIdToken(true);
            const newProfile = await getMe(refreshedToken);
            setProfile(newProfile);
            setProfileError(false);
            return;
          } catch (activationErr) {
            // signInWithPopup provisiona uma identidade no pool do Firebase Auth mesmo sem
            // conta no SAGA, e signOut não a remove. Apagamos a identidade órfã enquanto a
            // credencial está fresca (sem reauth). Best-effort: não bloqueia o erro de negócio.
            await result.user.delete().catch(() => undefined);
            await signOut(auth);
            throw new Error((activationErr as Error).message ?? "E-mail sem convite; procure a coordenação");
          }
        }
        await signOut(auth);
        throw new Error("Falha ao verificar sua conta. Tente novamente.");
      }
    } finally {
      isActivatingRef.current = false;
    }
  }, []);

  const logout = useCallback(async (): Promise<void> => {
    await signOut(auth);
  }, []);

  /** Recarrega o perfil sob a sessão Firebase atual (caminho de recuperação do estado degradado). */
  const retryProfile = useCallback(async (): Promise<void> => {
    const user = auth.currentUser;
    if (!user) return;
    const idToken = await user.getIdToken();
    setToken(idToken);
    await loadProfile(idToken);
  }, [loadProfile]);

  return {
    currentUser,
    profile,
    profileError,
    role: profile?.role ?? null,
    programaId: profile?.programaId ?? null,
    studentId: profile?.studentId ?? null,
    advisorId: profile?.advisorId ?? null,
    token,
    login,
    loginWithGoogle,
    logout,
    retryProfile,
    loading,
    profileLoading,
  };
}
