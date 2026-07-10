import React from "react";
import { useApp, UserRole, PageId } from "../../context/AppContext";
import { usePendingRequests } from "@/hooks/usePendingRequests";
import { useEscapeClose } from "@/hooks/useEscapeClose";
import {
  LayoutDashboard, Users, UserCheck, FileText, BookOpen,
  FlaskConical, CheckSquare, Clock, BarChart3, Brain,
  ShieldCheck, Settings, Bell, ChevronLeft, ChevronRight,
  GraduationCap, LogOut, X, ArrowRightLeft
} from "lucide-react";

interface NavItem {
  id: PageId;
  label: string;
  icon: React.ReactNode;
  roles: UserRole[];
  badge?: number;
}

const NAV_ITEMS: NavItem[] = [
  { id: "dashboard", label: "Dashboard", icon: <LayoutDashboard size={18} />, roles: ["aluno", "orientador", "coordenacao"] },
  { id: "alunos", label: "Alunos", icon: <Users size={18} />, roles: ["orientador", "coordenacao"] },
  { id: "orientadores", label: "Orientadores", icon: <UserCheck size={18} />, roles: ["coordenacao"] },
  { id: "plano-trabalho", label: "Plano de Trabalho", icon: <FileText size={18} />, roles: ["aluno", "orientador", "coordenacao"] },
  { id: "atividades", label: "Atividades Creditáveis", icon: <BookOpen size={18} />, roles: ["aluno", "orientador", "coordenacao"] },
  { id: "producoes", label: "Produções", icon: <FlaskConical size={18} />, roles: ["aluno", "orientador", "coordenacao"] },
  { id: "checklist", label: "Checklist", icon: <CheckSquare size={18} />, roles: ["aluno", "orientador", "coordenacao"] },
  { id: "solicitacoes", label: "Solicitações", icon: <Clock size={18} />, roles: ["aluno", "orientador", "coordenacao"] },
  { id: "relatorios", label: "Relatórios", icon: <BarChart3 size={18} />, roles: ["orientador", "coordenacao"] },
  { id: "inferencia", label: "Inferência Acadêmica", icon: <Brain size={18} />, roles: ["orientador", "coordenacao"] },
  { id: "registration-requests", label: "Cadastros Pendentes", icon: <UserCheck size={18} />, roles: ["coordenacao"] },
  { id: "auditoria", label: "Auditoria", icon: <ShieldCheck size={18} />, roles: ["coordenacao"] },
  { id: "configuracoes", label: "Configurações", icon: <Settings size={18} />, roles: ["aluno", "orientador", "coordenacao"] },
];

const ROLE_LABELS: Record<UserRole, string> = {
  aluno: "Aluno(a)",
  orientador: "Orientador(a)",
  coordenacao: "Coordenação",
};

const ROLE_COLORS: Record<UserRole, string> = {
  aluno: "#1F8A70",
  orientador: "#D4A017",
  coordenacao: "#e74c3c",
};

function SidebarContent({ collapsed, onNavigate }: { collapsed: boolean; onNavigate?: () => void }) {
  const { activeView, currentUser, currentPage, setCurrentPage, logout, notificationCount } = useApp();
  const { count: pendingCount } = usePendingRequests();

  if (!currentUser) return null;

  const visualRole: UserRole =
    currentUser.role === "coordenacao" && activeView === "orientador"
      ? "orientador"
      : currentUser.role;
  const visibleItems = NAV_ITEMS.filter((item) => item.roles.includes(visualRole));

  const navigate = (id: PageId) => {
    setCurrentPage(id);
    onNavigate?.();
  };

  const visibleItemsWithBadge = visibleItems.map(item => {
    if (item.id === "solicitacoes") {
      return { ...item, badge: pendingCount };
    }
    return item;
  });

  return (
    <>
      {/* User info */}
      {!collapsed && (
        <div
          className="mx-3 mt-4 mb-2 p-3 rounded-xl"
          style={{ background: "rgba(255,255,255,0.07)" }}
        >
          <div className="flex items-center gap-2">
            <div
              className="rounded-full flex items-center justify-center flex-shrink-0"
              style={{ width: 34, height: 34, background: ROLE_COLORS[currentUser.role], fontSize: "14px", fontWeight: 700, color: "#fff" }}
            >
              {currentUser.name.charAt(0)}
            </div>
            <div className="overflow-hidden">
              <p style={{ color: "#fff", fontSize: "12px", fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {currentUser.name.split(" ").slice(0, 2).join(" ")}
              </p>
              <span
                className="inline-block rounded px-1.5 py-0.5"
                style={{ background: ROLE_COLORS[currentUser.role], fontSize: "9px", color: "#fff", fontWeight: 600 }}
              >
                {currentUser.role === "coordenacao" && activeView === "orientador"
                  ? "Visao orientador"
                  : ROLE_LABELS[currentUser.role]}
              </span>
            </div>
          </div>
          {currentUser.matricula && (
            <p style={{ color: "rgba(255,255,255,0.5)", fontSize: "10px", marginTop: "4px" }}>
              Matrícula: {currentUser.matricula}
            </p>
          )}
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-2 px-2" style={{ scrollbarWidth: "none" }}>
        {!collapsed && (
          <p style={{ color: "rgba(255,255,255,0.4)", fontSize: "10px", fontWeight: 600, letterSpacing: "0.08em", padding: "8px 8px 4px", textTransform: "uppercase" }}>
            Menu Principal
          </p>
        )}
        {visibleItemsWithBadge.map((item) => {
          const isActive = currentPage === item.id;
          return (
            <button
              key={item.id}
              onClick={() => navigate(item.id)}
              className="w-full flex items-center gap-3 rounded-lg transition-all duration-150 mb-0.5"
              style={{
                padding: collapsed ? "10px" : "9px 12px",
                justifyContent: collapsed ? "center" : "flex-start",
                background: isActive ? "rgba(255,255,255,0.15)" : "transparent",
                borderLeft: isActive ? "3px solid #D4A017" : "3px solid transparent",
                color: isActive ? "#fff" : "rgba(255,255,255,0.7)",
                minHeight: "44px",
              }}
              title={collapsed ? item.label : undefined}
              onMouseEnter={(e) => {
                if (!isActive) {
                  (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.08)";
                  (e.currentTarget as HTMLElement).style.color = "#fff";
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  (e.currentTarget as HTMLElement).style.background = "transparent";
                  (e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.7)";
                }
              }}
            >
              <span style={{ flexShrink: 0 }}>{item.icon}</span>
              {!collapsed && (
                <>
                  <span style={{ fontSize: "13px", fontWeight: isActive ? 600 : 400, flex: 1, textAlign: "left" }}>
                    {item.label}
                  </span>
                  {item.id === "notificacoes" && notificationCount > 0 && (
                    <span
                      className="rounded-full flex items-center justify-center"
                      style={{ background: "#D4A017", color: "#fff", fontSize: "10px", fontWeight: 700, minWidth: 18, height: 18, padding: "0 4px" }}
                    >
                      {notificationCount}
                    </span>
                  )}
                  {item.id === "solicitacoes" && item.badge && item.badge > 0 && (
                    <span
                      className="rounded-full flex items-center justify-center"
                      style={{ background: "#e74c3c", color: "#fff", fontSize: "10px", fontWeight: 700, minWidth: 18, height: 18, padding: "0 4px" }}
                    >
                      {item.badge}
                    </span>
                  )}
                </>
              )}
            </button>
          );
        })}
      </nav>

      {/* Bottom actions */}
      <div className="p-3 border-t" style={{ borderColor: "rgba(255,255,255,0.1)" }}>
        <button
          onClick={() => navigate("notificacoes")}
          className="w-full flex items-center gap-3 rounded-lg mb-1 transition-all"
          style={{
            padding: collapsed ? "9px" : "9px 12px",
            justifyContent: collapsed ? "center" : "flex-start",
            color: "rgba(255,255,255,0.7)",
            minHeight: "44px",
          }}
          title="Notificações"
          onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.08)"; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "transparent"; }}
        >
          <div className="relative">
            <Bell size={18} />
            {notificationCount > 0 && (
              <span
                className="absolute rounded-full"
                style={{ width: 8, height: 8, background: "#D4A017", top: -2, right: -2 }}
              />
            )}
          </div>
          {!collapsed && <span style={{ fontSize: "13px" }}>Notificações</span>}
        </button>

        <button
          onClick={logout}
          className="w-full flex items-center gap-3 rounded-lg transition-all"
          style={{
            padding: collapsed ? "9px" : "9px 12px",
            justifyContent: collapsed ? "center" : "flex-start",
            color: "rgba(255,120,120,0.8)",
            minHeight: "44px",
          }}
          title="Sair"
          onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "rgba(220,50,50,0.15)"; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "transparent"; }}
        >
          <LogOut size={18} />
          {!collapsed && <span style={{ fontSize: "13px" }}>Sair</span>}
        </button>
      </div>
    </>
  );
}

function SidebarSkeletonContent({ collapsed }: { collapsed: boolean }) {
  return (
    <>
      {!collapsed && (
        <div className="mx-3 mt-4 mb-2 p-3 rounded-xl flex flex-col gap-2" style={{ background: "rgba(255,255,255,0.07)" }}>
          <div className="flex items-center gap-2">
            <div className="rounded-full animate-pulse flex-shrink-0" style={{ width: 34, height: 34, background: "rgba(255,255,255,0.2)" }} />
            <div className="flex-1 flex flex-col gap-1.5 overflow-hidden">
              <div className="h-2.5 rounded animate-pulse" style={{ background: "rgba(255,255,255,0.2)", width: "80%" }} />
              <div className="h-2 rounded animate-pulse" style={{ background: "rgba(255,255,255,0.2)", width: "50%" }} />
            </div>
          </div>
          <div className="h-2 rounded animate-pulse mt-1" style={{ background: "rgba(255,255,255,0.1)", width: "60%" }} />
        </div>
      )}
      <nav className="flex-1 overflow-y-auto py-2 px-2" style={{ scrollbarWidth: "none" }}>
        {!collapsed && (
          <div className="h-2 rounded animate-pulse mb-3 mt-2 ml-2" style={{ background: "rgba(255,255,255,0.1)", width: "30%" }} />
        )}
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="w-full flex items-center gap-3 rounded-lg mb-0.5"
            style={{
              padding: collapsed ? "10px" : "9px 12px",
              justifyContent: collapsed ? "center" : "flex-start",
              minHeight: "44px",
            }}
          >
            <div className="rounded-md animate-pulse flex-shrink-0" style={{ width: 18, height: 18, background: "rgba(255,255,255,0.2)" }} />
            {!collapsed && (
              <div className="h-2.5 rounded animate-pulse flex-1" style={{ background: "rgba(255,255,255,0.15)" }} />
            )}
          </div>
        ))}
      </nav>
      <div className="p-3 border-t" style={{ borderColor: "rgba(255,255,255,0.1)" }}>
        {Array.from({ length: 2 }).map((_, i) => (
          <div
            key={i}
            className="w-full flex items-center gap-3 rounded-lg mb-1"
            style={{
              padding: collapsed ? "9px" : "9px 12px",
              justifyContent: collapsed ? "center" : "flex-start",
              minHeight: "44px",
            }}
          >
            <div className="rounded-md animate-pulse flex-shrink-0" style={{ width: 18, height: 18, background: "rgba(255,255,255,0.2)" }} />
            {!collapsed && (
              <div className="h-2.5 rounded animate-pulse flex-1" style={{ background: "rgba(255,255,255,0.15)" }} />
            )}
          </div>
        ))}
      </div>
    </>
  );
}

export function Sidebar() {
  const { currentUser, sidebarCollapsed, setSidebarCollapsed, mobileMenuOpen, setMobileMenuOpen, profileLoading } = useApp();

  // ESC fecha o drawer mobile (issue #316).
  useEscapeClose(mobileMenuOpen, () => setMobileMenuOpen(false));

  if (!currentUser && !profileLoading) return null;

  const logoArea = (collapsed: boolean, onClose?: () => void) => (
    <div
      className="flex items-center gap-3 px-4 py-5 border-b flex-shrink-0"
      style={{ borderColor: "rgba(255,255,255,0.1)" }}
    >
      <div
        className="flex items-center justify-center rounded-xl flex-shrink-0"
        style={{ width: 36, height: 36, background: "#D4A017" }}
      >
        <GraduationCap size={20} color="#fff" />
      </div>
      {!collapsed && (
        <div className="flex-1 overflow-hidden">
          <p style={{ color: "#fff", fontSize: "13px", fontWeight: 700, lineHeight: 1.2, whiteSpace: "nowrap" }}>
            SAGA
          </p>
          <p style={{ color: "rgba(255,255,255,0.6)", fontSize: "10px", whiteSpace: "nowrap" }}>
            Pós-Graduação
          </p>
        </div>
      )}
      {onClose && (
        <button
          onClick={onClose}
          className="flex items-center justify-center rounded-lg ml-auto"
          style={{ width: 32, height: 32, color: "rgba(255,255,255,0.6)", background: "rgba(255,255,255,0.08)" }}
        >
          <X size={16} />
        </button>
      )}
    </div>
  );

  return (
    <>
      {/* Desktop Sidebar */}
      <aside
        className="hidden md:flex flex-col h-full transition-all duration-300 relative"
        style={{
          width: sidebarCollapsed ? "64px" : "256px",
          background: "linear-gradient(180deg, #0d2d5e 0%, #123C7A 40%, #1a4f9a 100%)",
          boxShadow: "4px 0 20px rgba(0,0,0,0.15)",
          flexShrink: 0,
        }}
      >
        {logoArea(sidebarCollapsed)}
        {profileLoading ? <SidebarSkeletonContent collapsed={sidebarCollapsed} /> : <SidebarContent collapsed={sidebarCollapsed} />}

        {/* Collapse toggle */}
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="absolute flex items-center justify-center rounded-full transition-all"
          style={{
            top: 68,
            right: -14,
            width: 28,
            height: 28,
            background: "#D4A017",
            color: "#fff",
            boxShadow: "0 2px 8px rgba(0,0,0,0.2)",
            zIndex: 10,
          }}
          title={sidebarCollapsed ? "Expandir menu" : "Recolher menu"}
        >
          {sidebarCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      </aside>

      {/* Mobile Drawer Overlay */}
      {mobileMenuOpen && (
        <div
          className="md:hidden fixed inset-0 z-50 flex"
          onClick={() => setMobileMenuOpen(false)}
        >
          {/* Backdrop */}
          <div
            className="absolute inset-0"
            style={{ background: "rgba(0,0,0,0.55)", backdropFilter: "blur(2px)" }}
          />

          {/* Drawer */}
          <aside
            className="relative flex flex-col h-full overflow-hidden"
            style={{
              width: "80vw",
              maxWidth: "300px",
              background: "linear-gradient(180deg, #0d2d5e 0%, #123C7A 40%, #1a4f9a 100%)",
              boxShadow: "8px 0 32px rgba(0,0,0,0.35)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {logoArea(false, () => setMobileMenuOpen(false))}
            {profileLoading ? <SidebarSkeletonContent collapsed={false} /> : <SidebarContent collapsed={false} onNavigate={() => setMobileMenuOpen(false)} />}
          </aside>
        </div>
      )}
    </>
  );
}
