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
  transferencias: ["orientador", "coordenacao"],
  "registration-requests": ["coordenacao"],
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
  profileUnavailable?: boolean;
}

export function getPrivateRouteRedirect({
  currentPage,
  loading,
  role,
  profileUnavailable = false,
}: RouteGuardState): PageId | null {
  if (loading) return null;

  // Sessão Firebase válida, mas perfil indisponível (GET /auth/me falhou): não é
  // logout. Suprime o redirect para que AppContent renderize o estado degradado.
  if (profileUnavailable) return null;

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
  const { currentPage, currentUser, loading, profileUnavailable, setCurrentPage } = useApp();
  const redirectPage = getPrivateRouteRedirect({
    currentPage,
    loading,
    role: currentUser?.role ?? null,
    profileUnavailable,
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
