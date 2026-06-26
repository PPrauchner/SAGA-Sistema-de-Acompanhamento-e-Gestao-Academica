import React, { createContext, useContext, useEffect, useState, ReactNode } from "react";

import { useAuth } from "@/hooks/useAuth";
import { useNotifications } from "@/hooks/useNotifications";

export type UserRole = "aluno" | "orientador" | "coordenacao";
export type ActiveView = "aluno" | "orientador" | "coordenador";

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
  | "configuracoes";

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
  token: string | null;
  profileUnavailable: boolean;
  activeView: ActiveView;
  isMultiRoleAdvisor: boolean;
  retryProfile: () => Promise<void>;
  login: (email: string, senha: string) => Promise<void>;
  setActiveView: (view: ActiveView) => void;
  setCurrentPage: (page: PageId) => void;
  setSelectedStudentId: (id: string | null) => void;
  setSidebarCollapsed: (v: boolean) => void;
  toggleDarkMode: () => void;
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
    logout: signOut,
    loading,
    retryProfile,
  } = useAuth();

  const { unreadCount } = useNotifications();

  const [currentPage, setCurrentPage] = useState<PageId>("login");
  const [selectedStudentId, setSelectedStudentId] = useState<string | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [activeView, setActiveViewState] = useState<ActiveView>("aluno");

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

  const toggleDarkMode = () => {
    setDarkMode((d) => {
      const next = !d;
      document.documentElement.classList.toggle("dark", next);
      return next;
    });
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
        token,
        profileUnavailable,
        activeView,
        isMultiRoleAdvisor,
        retryProfile,
        login,
        setActiveView,
        setCurrentPage,
        setSelectedStudentId,
        setSidebarCollapsed,
        toggleDarkMode,
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
