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
};

export function isAuthPage(page: PageId): boolean {
  return AUTH_PAGES.includes(page);
}

export function getAllowedRoles(page: PageId): UserRole[] {
  return PAGE_ROLES[page] ?? ALL_ROLES;
}

interface RouteGuardState {
  currentPage: PageId;
  loading: boolean;
  role: UserRole | null;
}

export function getPrivateRouteRedirect({
  currentPage,
  loading,
  role,
}: RouteGuardState): PageId | null {
  if (loading) return null;

  const onAuthPage = isAuthPage(currentPage);

  if (!role) {
    return onAuthPage ? null : "login";
  }

  if (onAuthPage) {
    return "dashboard";
  }

  return getAllowedRoles(currentPage).includes(role) ? null : "dashboard";
}

interface PrivateRouteProps {
  children: ReactNode;
  loadingFallback?: ReactNode;
}

export function PrivateRoute({ children, loadingFallback = null }: PrivateRouteProps) {
  const { currentPage, currentUser, loading, setCurrentPage } = useApp();
  const redirectPage = getPrivateRouteRedirect({
    currentPage,
    loading,
    role: currentUser?.role ?? null,
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
