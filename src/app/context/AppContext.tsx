import React, { createContext, useContext, useState, ReactNode } from "react";

export type UserRole = "aluno" | "orientador" | "coordenacao";

export type PageId =
  | "login" | "register" | "password-recovery" | "change-password" | "first-access"
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
  setCurrentUser: (user: User | null) => void;
  setCurrentPage: (page: PageId) => void;
  setSelectedStudentId: (id: string | null) => void;
  setSidebarCollapsed: (v: boolean) => void;
  toggleDarkMode: () => void;
  logout: () => void;
  setMobileMenuOpen: (v: boolean) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

const DEMO_USERS: Record<UserRole, User> = {
  coordenacao: {
    id: "1",
    name: "Prof. Dr. Roberto Almeida",
    email: "roberto.almeida@ppg.ufx.br",
    role: "coordenacao",
    departamento: "Ciência da Computação",
    programa: "PPGCC - Programa de Pós-Graduação em Ciência da Computação",
  },
  orientador: {
    id: "2",
    name: "Profa. Dra. Carla Mendes",
    email: "carla.mendes@ppg.ufx.br",
    role: "orientador",
    departamento: "Ciência da Computação",
    programa: "PPGCC",
  },
  aluno: {
    id: "3",
    name: "Lucas Ferreira Silva",
    email: "lucas.silva@pos.ufx.br",
    role: "aluno",
    student_id: "aluno_risco",
    matricula: "2023001",
    programa: "PPGCC - Doutorado",
    orientador: "Profa. Dra. Carla Mendes",
  },
};

export function AppProvider({ children }: { children: ReactNode }) {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [currentPage, setCurrentPage] = useState<PageId>("login");
  const [selectedStudentId, setSelectedStudentId] = useState<string | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [notificationCount] = useState(5);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const toggleDarkMode = () => {
    setDarkMode((d) => {
      const next = !d;
      document.documentElement.classList.toggle("dark", next);
      return next;
    });
  };

  const logout = () => {
    setCurrentUser(null);
    setCurrentPage("login");
    setMobileMenuOpen(false);
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
        setCurrentUser,
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

export { DEMO_USERS };
