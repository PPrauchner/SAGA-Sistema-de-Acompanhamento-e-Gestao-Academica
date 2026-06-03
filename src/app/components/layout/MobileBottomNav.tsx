import { type ReactNode } from "react";
import { useApp } from "../../context/AppContext";
import { LayoutDashboard, CheckSquare, BookOpen, Bell, Menu } from "lucide-react";
import type { PageId, UserRole } from "../../context/AppContext";

interface BottomNavItem {
  id: PageId | "menu";
  label: string;
  icon: ReactNode;
  roles: UserRole[];
  badge?: boolean;
}

const BOTTOM_ITEMS: BottomNavItem[] = [
  { id: "dashboard", label: "Início", icon: <LayoutDashboard size={20} />, roles: ["aluno", "orientador", "coordenacao"] },
  { id: "checklist", label: "Checklist", icon: <CheckSquare size={20} />, roles: ["aluno", "orientador", "coordenacao"] },
  { id: "atividades", label: "Atividades", icon: <BookOpen size={20} />, roles: ["aluno", "orientador", "coordenacao"] },
  { id: "notificacoes", label: "Avisos", icon: <Bell size={20} />, roles: ["aluno", "orientador", "coordenacao"], badge: true },
  { id: "menu", label: "Menu", icon: <Menu size={20} />, roles: ["aluno", "orientador", "coordenacao"] },
];

export function MobileBottomNav() {
  const { currentPage, setCurrentPage, currentUser, notificationCount, mobileMenuOpen, setMobileMenuOpen } = useApp();

  if (!currentUser) return null;

  const visibleItems = BOTTOM_ITEMS.filter(item => item.roles.includes(currentUser.role));

  return (
    <nav
      className="md:hidden fixed bottom-0 left-0 right-0 z-40 flex items-stretch"
      style={{
        background: "linear-gradient(180deg, #0d2d5e 0%, #123C7A 100%)",
        borderTop: "1px solid rgba(255,255,255,0.12)",
        boxShadow: "0 -4px 20px rgba(0,0,0,0.25)",
        paddingBottom: "env(safe-area-inset-bottom)",
        height: "64px",
      }}
    >
      {visibleItems.map((item) => {
        const isMenu = item.id === "menu";
        const isActive = isMenu ? mobileMenuOpen : currentPage === item.id;

        return (
          <button
            key={item.id}
            onClick={() => {
              if (isMenu) {
                setMobileMenuOpen(!mobileMenuOpen);
              } else {
                setCurrentPage(item.id as PageId);
                setMobileMenuOpen(false);
              }
            }}
            className="flex-1 flex flex-col items-center justify-center gap-1 transition-all relative"
            style={{ color: isActive ? "#D4A017" : "rgba(255,255,255,0.55)" }}
          >
            {/* Active indicator */}
            {isActive && (
              <div
                className="absolute top-0 left-1/2"
                style={{
                  transform: "translateX(-50%)",
                  width: 32,
                  height: 3,
                  background: "#D4A017",
                  borderRadius: "0 0 4px 4px",
                }}
              />
            )}

            {/* Icon with badge */}
            <div className="relative">
              {item.icon}
              {item.badge && notificationCount > 0 && (
                <span
                  className="absolute flex items-center justify-center rounded-full"
                  style={{
                    top: -5,
                    right: -6,
                    minWidth: 16,
                    height: 16,
                    background: "#D4A017",
                    color: "#fff",
                    fontSize: "9px",
                    fontWeight: 700,
                    padding: "0 3px",
                  }}
                >
                  {notificationCount}
                </span>
              )}
            </div>

            <span style={{ fontSize: "10px", fontWeight: isActive ? 700 : 400 }}>
              {item.label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
