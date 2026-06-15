import { useState } from "react";
import { useApp, PageId } from "../../context/AppContext";
import { Search, Bell, Sun, Moon, ChevronRight, Home, LogOut, Settings, UserCircle, Menu, GraduationCap, X } from "lucide-react";

const PAGE_LABELS: Record<PageId, string> = {
  login: "Login",
  register: "Cadastro",
  "password-recovery": "Recuperar Senha",
  "first-access": "Primeiro Acesso",
  dashboard: "Dashboard",
  alunos: "Alunos",
  "aluno-detail": "Detalhes do Aluno",
  orientadores: "Orientadores",
  "orientador-detail": "Detalhes do Orientador",
  "plano-trabalho": "Plano de Trabalho",
  atividades: "Atividades Creditáveis",
  producoes: "Produções Científicas",
  checklist: "Checklist de Conclusão",
  prorrogacoes: "Prorrogações",
  relatorios: "Relatórios",
  inferencia: "Inferência Acadêmica",
  auditoria: "Auditoria",
  notificacoes: "Notificações",
  configuracoes: "Configurações",
};

export function TopBar() {
  const { currentUser, currentPage, setCurrentPage, darkMode, toggleDarkMode, notificationCount, logout, mobileMenuOpen, setMobileMenuOpen } = useApp();
  const [searchValue, setSearchValue] = useState("");
  const [profileOpen, setProfileOpen] = useState(false);
  const [mobileSearchOpen, setMobileSearchOpen] = useState(false);

  if (!currentUser) return null;

  return (
    <header
      className="flex items-center gap-2 md:gap-4 px-3 md:px-6 h-14 md:h-16 border-b flex-shrink-0 relative"
      style={{
        background: "var(--card)",
        borderColor: "var(--border)",
        boxShadow: "0 2px 8px rgba(0,0,0,0.05)",
      }}
    >
      {/* Mobile: Hamburger */}
      <button
        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        className="md:hidden flex items-center justify-center rounded-lg flex-shrink-0"
        style={{
          width: 38,
          height: 38,
          color: "var(--foreground)",
          background: "var(--input-background)",
          border: "1px solid var(--border)",
        }}
        aria-label="Abrir menu"
      >
        {mobileMenuOpen ? <X size={18} /> : <Menu size={18} />}
      </button>

      {/* Mobile: Logo center */}
      <div className="md:hidden flex items-center gap-2 flex-1 justify-center">
        <div
          className="flex items-center justify-center rounded-lg"
          style={{ width: 28, height: 28, background: "#123C7A" }}
        >
          <GraduationCap size={15} color="#fff" />
        </div>
        <div>
          <p style={{ color: "var(--foreground)", fontSize: "13px", fontWeight: 700, lineHeight: 1.2 }}>SAGA</p>
          <p style={{ color: "var(--muted-foreground)", fontSize: "9px", lineHeight: 1 }}>
            {PAGE_LABELS[currentPage] || "Sistema"}
          </p>
        </div>
      </div>

      {/* Desktop: Breadcrumb */}
      <nav className="hidden md:flex items-center gap-1 flex-1 min-w-0">
        <button
          onClick={() => setCurrentPage("dashboard")}
          className="flex items-center gap-1 transition-colors"
          style={{ color: "var(--muted-foreground)", fontSize: "13px" }}
          onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.color = "var(--primary)"; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.color = "var(--muted-foreground)"; }}
        >
          <Home size={14} />
          <span>Início</span>
        </button>
        {currentPage !== "dashboard" && (
          <>
            <ChevronRight size={12} style={{ color: "var(--muted-foreground)" }} />
            <span style={{ color: "var(--foreground)", fontSize: "13px", fontWeight: 500 }}>
              {PAGE_LABELS[currentPage] || currentPage}
            </span>
          </>
        )}
      </nav>

      {/* Desktop: Search */}
      <div className="relative hidden md:flex items-center">
        <Search
          size={15}
          className="absolute left-3"
          style={{ color: "var(--muted-foreground)" }}
        />
        <input
          type="text"
          placeholder="Buscar..."
          value={searchValue}
          onChange={(e) => setSearchValue(e.target.value)}
          className="rounded-lg pl-9 pr-4 py-2 outline-none transition-all"
          style={{
            background: "var(--input-background)",
            border: "1px solid var(--border)",
            color: "var(--foreground)",
            fontSize: "13px",
            width: "220px",
          }}
          onFocus={(e) => { e.currentTarget.style.borderColor = "#123C7A"; e.currentTarget.style.width = "260px"; }}
          onBlur={(e) => { e.currentTarget.style.borderColor = "var(--border)"; e.currentTarget.style.width = "220px"; }}
        />
      </div>

      {/* Mobile: Search toggle */}
      {mobileSearchOpen && (
        <div className="md:hidden absolute top-full left-0 right-0 z-30 p-3"
          style={{ background: "var(--card)", borderBottom: "1px solid var(--border)", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }}>
          <div className="relative flex items-center">
            <Search size={15} className="absolute left-3" style={{ color: "var(--muted-foreground)" }} />
            <input
              type="text"
              placeholder="Buscar..."
              autoFocus
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              className="w-full rounded-xl pl-9 pr-4 py-2.5 outline-none"
              style={{
                background: "var(--input-background)",
                border: "1px solid #123C7A",
                color: "var(--foreground)",
                fontSize: "14px",
              }}
            />
            <button onClick={() => setMobileSearchOpen(false)} className="absolute right-3" style={{ color: "var(--muted-foreground)" }}>
              <X size={16} />
            </button>
          </div>
        </div>
      )}

      {/* Notifications */}
      <button
        onClick={() => setCurrentPage("notificacoes")}
        className="relative flex items-center justify-center rounded-lg transition-colors flex-shrink-0"
        style={{
          width: 38,
          height: 38,
          color: "var(--muted-foreground)",
          background: "var(--input-background)",
          border: "1px solid var(--border)",
        }}
        title="Notificações"
        onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--muted)"; }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--input-background)"; }}
      >
        <Bell size={17} />
        {notificationCount > 0 && (
          <span
            className="absolute flex items-center justify-center rounded-full"
            style={{
              top: -4,
              right: -4,
              minWidth: 18,
              height: 18,
              background: "#D4A017",
              color: "#fff",
              fontSize: "10px",
              fontWeight: 700,
              padding: "0 3px",
            }}
          >
            {notificationCount}
          </span>
        )}
      </button>

      {/* Dark mode toggle */}
      <button
        onClick={toggleDarkMode}
        className="hidden md:flex items-center justify-center rounded-lg transition-colors flex-shrink-0"
        style={{
          width: 38,
          height: 38,
          color: "var(--muted-foreground)",
          background: "var(--input-background)",
          border: "1px solid var(--border)",
        }}
        title={darkMode ? "Modo Claro" : "Modo Escuro"}
        onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--muted)"; }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--input-background)"; }}
      >
        {darkMode ? <Sun size={17} /> : <Moon size={17} />}
      </button>

      {/* Profile */}
      <div className="relative">
        <button
          onClick={() => setProfileOpen(!profileOpen)}
          className="flex items-center gap-2 rounded-lg px-1.5 py-1.5 md:px-2 transition-colors"
          style={{
            background: profileOpen ? "var(--muted)" : "transparent",
            border: "1px solid transparent",
          }}
          onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--muted)"; }}
          onMouseLeave={(e) => { if (!profileOpen) (e.currentTarget as HTMLElement).style.background = "transparent"; }}
        >
          <div
            className="rounded-full flex items-center justify-center flex-shrink-0"
            style={{
              width: 32,
              height: 32,
              background: "#123C7A",
              color: "#fff",
              fontSize: "13px",
              fontWeight: 700,
            }}
          >
            {currentUser.name.charAt(0)}
          </div>
          <div className="hidden md:block text-left">
            <p style={{ fontSize: "12px", fontWeight: 600, color: "var(--foreground)", lineHeight: 1.3 }}>
              {currentUser.name.split(" ").slice(0, 2).join(" ")}
            </p>
            <p style={{ fontSize: "10px", color: "var(--muted-foreground)", lineHeight: 1.3 }}>
              {currentUser.email}
            </p>
          </div>
        </button>

        {profileOpen && (
          <div
            className="absolute right-0 top-full mt-2 rounded-xl overflow-hidden z-50"
            style={{
              width: 220,
              background: "var(--card)",
              border: "1px solid var(--border)",
              boxShadow: "0 8px 30px rgba(0,0,0,0.12)",
            }}
          >
            <div className="p-4 border-b" style={{ borderColor: "var(--border)", background: "var(--input-background)" }}>
              <p style={{ fontWeight: 600, fontSize: "13px", color: "var(--foreground)" }}>{currentUser.name}</p>
              <p style={{ fontSize: "11px", color: "var(--muted-foreground)" }}>{currentUser.email}</p>
            </div>
            <div className="py-1">
              {[
                { icon: <UserCircle size={15} />, label: "Meu Perfil", action: () => { setCurrentPage("configuracoes"); setProfileOpen(false); } },
                { icon: <Settings size={15} />, label: "Configurações", action: () => { setCurrentPage("configuracoes"); setProfileOpen(false); } },
                { icon: <LogOut size={15} />, label: "Sair", action: logout, danger: true },
              ].map((item) => (
                <button
                  key={item.label}
                  onClick={item.action}
                  className="w-full flex items-center gap-3 px-4 py-3 transition-colors"
                  style={{
                    fontSize: "13px",
                    color: item.danger ? "#dc2626" : "var(--foreground)",
                    background: "transparent",
                  }}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--muted)"; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "transparent"; }}
                >
                  {item.icon}
                  {item.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
