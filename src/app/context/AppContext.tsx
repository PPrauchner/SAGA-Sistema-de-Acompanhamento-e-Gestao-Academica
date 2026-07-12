import React, { createContext, useContext, useEffect, useLayoutEffect, useState, ReactNode } from "react";

import { useAuth } from "@/hooks/useAuth";
import { useNotifications } from "@/hooks/useNotifications";

export type UserRole = "aluno" | "orientador" | "coordenacao" | "adm";
export type ActiveView = "aluno" | "orientador" | "coordenador";
export type FontSizePreference = "small" | "normal" | "large";
export interface NotificationPreferences {
  email: boolean;
  in_app: boolean;
  work_plan: boolean;
  transfers: boolean;
  activities: boolean;
  extensions: boolean;
}

const FONT_SIZE_STORAGE_KEY = "saga:fontSizePreference";
const FONT_SIZE_SCALES: Record<FontSizePreference, string> = {
  small: "0.875",
  normal: "1",
  large: "1.125",
};

function isFontSizePreference(value: string | null): value is FontSizePreference {
  return value === "small" || value === "normal" || value === "large";
}

function getInitialFontSizePreference(): FontSizePreference {
  if (typeof window === "undefined") return "normal";

  try {
    const stored = window.localStorage.getItem(FONT_SIZE_STORAGE_KEY);
    return isFontSizePreference(stored) ? stored : "normal";
  } catch {
    return "normal";
  }
}

function applyFontSizePreference(preference: FontSizePreference): void {
  if (typeof document === "undefined") return;

  document.documentElement.style.setProperty(
    "--app-font-scale",
    FONT_SIZE_SCALES[preference],
  );
  document.documentElement.dataset.fontSize = preference;
}

export type PageId =
  | "login" | "register" | "password-recovery" | "first-access"
  | "dashboard"
  | "alunos" | "aluno-detail"
  | "orientadores" | "orientador-detail"
  | "plano-trabalho"
  | "atividades"
  | "producoes"
  | "checklist"
  | "solicitacoes"
  | "prorrogacoes"
  | "transferencias"
  | "registration-requests"
  | "relatorios"
  | "inferencia"
  | "auditoria"
  | "notificacoes"
  | "configuracoes"
  | "departamentos";

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  avatar?: string;
  student_id?: string;
  advisor_id?: string;
  programa_id?: string;
  matricula?: string;
  programa?: string;
  orientador?: string;
  departamento?: string;
  notificationPreferences: NotificationPreferences;
}

interface AppContextType {
  currentUser: User | null;
  currentPage: PageId;
  selectedStudentId: string | null;
  sidebarCollapsed: boolean;
  darkMode: boolean;
  notificationCount: number;
  mobileMenuOpen: boolean;
  loading: boolean;
  profileLoading: boolean;
  isAuthenticated: boolean;
  token: string | null;
  profileUnavailable: boolean;
  activeView: ActiveView;
  isMultiRoleAdvisor: boolean;
  fontSizePreference: FontSizePreference;
  retryProfile: () => Promise<void>;
  login: (email: string, senha: string) => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  setActiveView: (view: ActiveView) => void;
  setCurrentPage: (page: PageId) => void;
  setSelectedStudentId: (id: string | null) => void;
  setSidebarCollapsed: (v: boolean) => void;
  toggleDarkMode: () => void;
  setFontSizePreference: (preference: FontSizePreference) => void;
  logout: () => void;
  setMobileMenuOpen: (v: boolean) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: ReactNode }) {
  const {
    currentUser: firebaseUser,
    profile,
    profileError,
    token,
    login,
    loginWithGoogle,
    logout: signOut,
    loading,
    profileLoading,
    retryProfile,
  } = useAuth();

  const { unreadCount } = useNotifications();

  const [currentPage, setCurrentPage] = useState<PageId>("login");
  const [selectedStudentId, setSelectedStudentId] = useState<string | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [activeView, setActiveViewState] = useState<ActiveView>("aluno");
  const [fontSizePreference, setFontSizePreferenceState] = useState<FontSizePreference>(
    getInitialFontSizePreference,
  );

  // O perfil vem do backend (GET /auth/me) via useAuth; mapeamos para o formato
  // de exibicao consumido pelo layout. Campos sem origem no backend ficam vazios.
  const currentUser: User | null = profile
    ? {
        id: profile.uid,
        name: profile.nome,
        email: profile.email,
        role: profile.role,
        programa: profile.programaId,
        programa_id: profile.programaId,
        departamento: profile.departamento ?? undefined,
        matricula: profile.matricula ?? undefined,
        student_id: profile.studentId ?? undefined,
        advisor_id: profile.advisorId ?? undefined,
        notificationPreferences: profile.notificationPreferences,
      }
    : null;

  const defaultView: ActiveView =
    profile?.role === "coordenacao"
      ? "coordenador"
      : profile?.role === "orientador"
        ? "orientador"
        : "aluno";

  const isMultiRoleAdvisor = currentUser?.role === "coordenacao" && Boolean(currentUser.advisor_id);

  useEffect(() => {
    setActiveViewState(defaultView);
  }, [defaultView, profile?.uid]);

  const setActiveView = (view: ActiveView) => {
    if (!currentUser) return;

    if (currentUser.role === "coordenacao") {
      const canUseAdvisorView = view === "orientador" && isMultiRoleAdvisor;
      const canUseCoordinatorView = view === "coordenador";

      setActiveViewState(canUseAdvisorView || canUseCoordinatorView ? view : "coordenador");
      return;
    }

    if (currentUser.role === "orientador") {
      setActiveViewState("orientador");
      return;
    }

    setActiveViewState("aluno");
  };

  // Sessao Firebase valida, mas perfil indisponivel (GET /auth/me falhou). Distinto
  // de "deslogado": o usuario permanece na app em estado degradado, com retry. A guarda
  // de rota vive no PrivateRoute, que suprime o redirect quando profileUnavailable e true.
  const profileUnavailable = !!firebaseUser && profileError && !profile;

  // Sessao Firebase ativa: o PrivateRoute redireciona da pagina de login para o dashboard
  // assim que existe sessao, mostrando o skeleton enquanto profileLoading e true.
  const isAuthenticated = !!firebaseUser;

  const toggleDarkMode = () => {
    setDarkMode((d) => {
      const next = !d;
      document.documentElement.classList.toggle("dark", next);
      return next;
    });
  };

  useLayoutEffect(() => {
    applyFontSizePreference(fontSizePreference);
    try {
      window.localStorage.setItem(FONT_SIZE_STORAGE_KEY, fontSizePreference);
    } catch {
      // A preferencia visual ainda funciona na sessao atual mesmo sem storage.
    }
  }, [fontSizePreference]);

  const setFontSizePreference = (preference: FontSizePreference) => {
    setFontSizePreferenceState(preference);
  };

  const logout = () => {
    void signOut();
    setMobileMenuOpen(false);
    // PrivateRoute redireciona para "login" quando o perfil e limpo.
  };

  return (
    <AppContext.Provider
      value={{
        currentUser,
        currentPage,
        selectedStudentId,
        sidebarCollapsed,
        darkMode,
        notificationCount: unreadCount,
        mobileMenuOpen,
        loading,
        profileLoading,
        token,
        isAuthenticated,
        profileUnavailable,
        activeView,
        isMultiRoleAdvisor,
        fontSizePreference,
        retryProfile,
        login,
        loginWithGoogle,
        setActiveView,
        setCurrentPage,
        setSelectedStudentId,
        setSidebarCollapsed,
        toggleDarkMode,
        setFontSizePreference,
        logout,
        setMobileMenuOpen,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}
