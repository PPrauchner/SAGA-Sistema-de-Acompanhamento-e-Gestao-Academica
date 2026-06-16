import React, { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useAuth } from "@/hooks/useAuth";

export type UserRole = "aluno" | "orientador" | "coordenacao";

export type PageId =
  | "login" | "register" | "password-recovery" | "first-access"
  | "dashboard"
  | "alunos" | "aluno-detail"
  | "orientadores" | "orientador-detail"
  | "plano-trabalho"
  | "atividades"
  | "producoes"
  | "checklist"
  | "prorrogacoes"
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
  login: (email: string, senha: string) => Promise<void>;
  setCurrentPage: (page: PageId) => void;
  setSelectedStudentId: (id: string | null) => void;
  setSidebarCollapsed: (v: boolean) => void;
  toggleDarkMode: () => void;
  logout: () => void;
  setMobileMenuOpen: (v: boolean) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

// Páginas de autenticação (acessíveis sem sessão). Fora deste conjunto, toda
// página exige usuário autenticado.
const AUTH_PAGES: PageId[] = [
  "login", "register", "password-recovery", "first-access",
];

// Guarda de rota por papel — espelha os `roles` de NAV_ITEMS no Sidebar. Páginas
// ausentes deste mapa são liberadas para qualquer usuário autenticado.
const ALL_ROLES: UserRole[] = ["aluno", "orientador", "coordenacao"];
const PAGE_ROLES: Partial<Record<PageId, UserRole[]>> = {
  alunos: ["orientador", "coordenacao"],
  "aluno-detail": ["orientador", "coordenacao"],
  orientadores: ["coordenacao"],
  "orientador-detail": ["coordenacao"],
  relatorios: ["orientador", "coordenacao"],
  inferencia: ["orientador", "coordenacao"],
  auditoria: ["coordenacao"],
};

export function AppProvider({ children }: { children: ReactNode }) {
  const { profile, login, logout: signOut, loading } = useAuth();
  const [currentPage, setCurrentPage] = useState<PageId>("login");
  const [selectedStudentId, setSelectedStudentId] = useState<string | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [notificationCount] = useState(5);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // O perfil vem do backend (GET /auth/me) via useAuth; mapeamos para o formato
  // de exibição consumido pelo layout. Campos sem origem no backend ficam vazios.
  const currentUser: User | null = profile
    ? {
        id: profile.uid,
        name: profile.nome,
        email: profile.email,
        role: profile.role,
        programa: profile.programaId,
        student_id: profile.studentId ?? undefined,
      }
    : null;

  // Guarda de rota: redireciona conforme o estado de autenticação e o papel.
  useEffect(() => {
    if (loading) return;
    const onAuthPage = AUTH_PAGES.includes(currentPage);
    if (!profile) {
      if (!onAuthPage) setCurrentPage("login");
      return;
    }
    if (onAuthPage) {
      setCurrentPage("dashboard");
      return;
    }
    const allowed = PAGE_ROLES[currentPage] ?? ALL_ROLES;
    if (!allowed.includes(profile.role)) setCurrentPage("dashboard");
  }, [loading, profile, currentPage]);

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
    // O efeito de guarda redireciona para "login" quando o perfil é limpo.
  };

  return (
    <AppContext.Provider
      value={{
        currentUser,
        currentPage,
        selectedStudentId,
        sidebarCollapsed,
        darkMode,
        notificationCount,
        mobileMenuOpen,
        loading,
        login,
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
