import { useEffect, type ReactNode } from "react";

import { useApp, type PageId, type UserRole } from "../context/AppContext";

export const AUTH_PAGES: PageId[] = [
  "login",
  "register",
  "password-recovery",
  "first-access",
];

const ALL_ROLES: UserRole[] = ["aluno", "orientador", "coordenacao"];

export const PAGE_ROLES: Partial<Record<PageId, UserRole[]>> = {
  alunos: ["orientador", "coordenacao"],
  "aluno-detail": ["orientador", "coordenacao"],
  orientadores: ["coordenacao"],
  "orientador-detail": ["coordenacao"],
  relatorios: ["orientador", "coordenacao"],
  inferencia: ["orientador", "coordenacao"],
  auditoria: ["coordenacao"],
  solicitacoes: ["aluno", "orientador", "coordenacao"],
  "registration-requests": ["coordenacao"],
  departamentos: ["adm"],
};

export function isAuthPage(page: PageId): boolean {
  return AUTH_PAGES.includes(page);
}

export function getAllowedRoles(page: PageId): UserRole[] {
  return PAGE_ROLES[page] ?? ALL_ROLES;
}

// "adm" não tem dashboard (ADR-0001, issue #336): sem esta exceção, o fallback
// hardcoded "dashboard" abaixo cairia num redirect-loop, já que "dashboard" não
// está em PAGE_ROLES e herda o fallback ALL_ROLES (que não inclui "adm").
export function getDefaultPageForRole(role: UserRole | null): PageId {
  return role === "adm" ? "departamentos" : "dashboard";
}

interface RouteGuardState {
  currentPage: PageId;
  loading: boolean;
  role: UserRole | null;
  profileUnavailable?: boolean;
  profileLoading?: boolean;
  isAuthenticated?: boolean;
}

export function getPrivateRouteRedirect({
  currentPage,
  loading,
  role,
  profileUnavailable = false,
  profileLoading = false,
  isAuthenticated = false,
}: RouteGuardState): PageId | null {
  if (loading) return null;

  // Sessão Firebase válida, mas perfil indisponível (GET /auth/me falhou): não é
  // logout. Suprime o redirect para que AppContent renderize o estado degradado.
  if (profileUnavailable) return null;

  const onAuthPage = isAuthPage(currentPage);

  if (!isAuthenticated) {
    return onAuthPage ? null : "login";
  }

  if (profileLoading) {
    return null;
  }

  if (onAuthPage) {
    return getDefaultPageForRole(role);
  }

  return role && getAllowedRoles(currentPage).includes(role) ? null : getDefaultPageForRole(role);
}

interface PrivateRouteProps {
  children: ReactNode;
  loadingFallback?: ReactNode;
}

export function PrivateRoute({ children, loadingFallback = null }: PrivateRouteProps) {
  const { currentPage, currentUser, loading, profileUnavailable, profileLoading, isAuthenticated, setCurrentPage } = useApp();
  const redirectPage = getPrivateRouteRedirect({
    currentPage,
    loading,
    role: currentUser?.role ?? null,
    profileUnavailable,
    profileLoading,
    isAuthenticated,
  });

  useEffect(() => {
    if (redirectPage && redirectPage !== currentPage) {
      setCurrentPage(redirectPage);
    }
  }, [currentPage, redirectPage, setCurrentPage]);

  if (loading) return <>{loadingFallback}</>;
  if (redirectPage) return null;

  return <>{children}</>;
}
