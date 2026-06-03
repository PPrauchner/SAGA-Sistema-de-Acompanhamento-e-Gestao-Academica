import { useState } from "react";
import { Search, Plus, Users, BookOpen, Award, Eye } from "lucide-react";

const ADVISORS = [
  { id: "1", name: "Prof. Dr. Roberto Almeida", email: "roberto.almeida@ufx.br", departamento: "Ciência da Computação", titulacao: "Doutor", lattes: "http://lattes.cnpq.br/123", orientandos: 8, producoes: 42, areas: ["Inteligência Artificial", "Visão Computacional"], qualis: "A1", ativo: true },
  { id: "2", name: "Profa. Dra. Carla Mendes", email: "carla.mendes@ufx.br", departamento: "Engenharia de Software", titulacao: "Doutora", lattes: "http://lattes.cnpq.br/456", orientandos: 6, producoes: 31, areas: ["Engenharia de Software", "Qualidade de Software"], qualis: "A2", ativo: true },
  { id: "3", name: "Prof. Dr. João Batista", email: "joao.batista@ufx.br", departamento: "Redes de Computadores", titulacao: "Doutor", lattes: "http://lattes.cnpq.br/789", orientandos: 5, producoes: 28, areas: ["Redes de Computadores", "IoT"], qualis: "B1", ativo: true },
  { id: "4", name: "Profa. Dra. Márcia Santos", email: "marcia.santos@ufx.br", departamento: "Banco de Dados", titulacao: "Doutora", lattes: "http://lattes.cnpq.br/321", orientandos: 4, producoes: 19, areas: ["Banco de Dados", "Big Data"], qualis: "A2", ativo: true },
  { id: "5", name: "Prof. Dr. Fernando Lima", email: "fernando.lima@ufx.br", departamento: "Segurança da Informação", titulacao: "Doutor", lattes: "http://lattes.cnpq.br/654", orientandos: 3, producoes: 15, areas: ["Segurança", "Criptografia"], qualis: "B1", ativo: false },
];

const QUALIS_COLORS: Record<string, { color: string; bg: string }> = {
  A1: { color: "#123C7A", bg: "#eef3fc" },
  A2: { color: "#1F8A70", bg: "#dcfce7" },
  B1: { color: "#D4A017", bg: "#fef9c3" },
  B2: { color: "#8b5cf6", bg: "#ede9fe" },
};

export function AdvisorsPage() {
  const [search, setSearch] = useState("");
  const [showForm, setShowForm] = useState(false);

  const filtered = ADVISORS.filter((a) =>
    a.name.toLowerCase().includes(search.toLowerCase()) ||
    a.departamento.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 style={{ color: "var(--foreground)", marginBottom: "4px" }}>Orientadores</h1>
          <p style={{ color: "var(--muted-foreground)", fontSize: "14px" }}>{ADVISORS.length} orientadores cadastrados</p>
        </div>
        <button onClick={() => setShowForm(true)} className="flex items-center gap-2 rounded-xl px-4 py-2.5" style={{ background: "#123C7A", color: "#fff", fontWeight: 600, fontSize: "14px" }}>
          <Plus size={16} /> Novo Orientador
        </button>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="rounded-2xl p-4" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
          <p style={{ fontSize: "28px", fontWeight: 800, color: "#123C7A" }}>{ADVISORS.filter(a => a.ativo).length}</p>
          <p style={{ fontSize: "13px", color: "var(--muted-foreground)" }}>Ativos</p>
        </div>
        <div className="rounded-2xl p-4" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
          <p style={{ fontSize: "28px", fontWeight: 800, color: "#1F8A70" }}>{ADVISORS.reduce((s, a) => s + a.orientandos, 0)}</p>
          <p style={{ fontSize: "13px", color: "var(--muted-foreground)" }}>Orientandos</p>
        </div>
        <div className="rounded-2xl p-4" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
          <p style={{ fontSize: "28px", fontWeight: 800, color: "#D4A017" }}>{ADVISORS.reduce((s, a) => s + a.producoes, 0)}</p>
          <p style={{ fontSize: "13px", color: "var(--muted-foreground)" }}>Produções Totais</p>
        </div>
      </div>

      {/* Search */}
      <div className="relative mb-4">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--muted-foreground)" }} />
        <input
          placeholder="Buscar orientador..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full max-w-sm rounded-xl pl-9 pr-4 py-2.5 outline-none"
          style={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: "13px", color: "var(--foreground)" }}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {filtered.map((advisor) => {
          const qualis = QUALIS_COLORS[advisor.qualis] || QUALIS_COLORS.B2;
          return (
            <div key={advisor.id} className="rounded-2xl p-5 transition-all" style={{ background: "var(--card)", border: "1px solid var(--border)", boxShadow: "0 2px 8px rgba(0,0,0,0.04)" }}>
              <div className="flex items-start gap-4 mb-4">
                <div className="rounded-2xl flex items-center justify-center flex-shrink-0" style={{ width: 52, height: 52, background: "#eef3fc" }}>
                  <span style={{ color: "#123C7A", fontSize: "20px", fontWeight: 800 }}>
                    {advisor.name.split(" ").slice(-1)[0].charAt(0)}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p style={{ fontSize: "15px", fontWeight: 700, color: "var(--foreground)" }}>{advisor.name}</p>
                      <p style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>{advisor.departamento}</p>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <span className="px-2 py-0.5 rounded-lg" style={{ background: qualis.bg, color: qualis.color, fontSize: "11px", fontWeight: 700 }}>
                        Qualis {advisor.qualis}
                      </span>
                      <span
                        className="w-2 h-2 rounded-full flex-shrink-0"
                        style={{ background: advisor.ativo ? "#1F8A70" : "#94a3b8" }}
                        title={advisor.ativo ? "Ativo" : "Inativo"}
                      />
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex gap-2 flex-wrap mb-4">
                {advisor.areas.map((area) => (
                  <span key={area} className="px-2 py-1 rounded-lg" style={{ background: "var(--muted)", color: "var(--muted-foreground)", fontSize: "11px" }}>
                    {area}
                  </span>
                ))}
              </div>

              <div className="grid grid-cols-3 gap-3 pt-4" style={{ borderTop: "1px solid var(--border)" }}>
                <div className="text-center">
                  <div className="flex items-center justify-center gap-1 mb-1">
                    <Users size={13} style={{ color: "#123C7A" }} />
                    <p style={{ fontSize: "16px", fontWeight: 800, color: "#123C7A" }}>{advisor.orientandos}</p>
                  </div>
                  <p style={{ fontSize: "10px", color: "var(--muted-foreground)" }}>Orientandos</p>
                </div>
                <div className="text-center">
                  <div className="flex items-center justify-center gap-1 mb-1">
                    <BookOpen size={13} style={{ color: "#1F8A70" }} />
                    <p style={{ fontSize: "16px", fontWeight: 800, color: "#1F8A70" }}>{advisor.producoes}</p>
                  </div>
                  <p style={{ fontSize: "10px", color: "var(--muted-foreground)" }}>Produções</p>
                </div>
                <div className="text-center">
                  <button
                    className="flex items-center justify-center gap-1 mx-auto px-3 py-1.5 rounded-lg transition-colors"
                    style={{ background: "#eef3fc", color: "#123C7A", fontSize: "12px", fontWeight: 600 }}
                    onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "#123C7A"; (e.currentTarget as HTMLElement).style.color = "#fff"; }}
                    onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "#eef3fc"; (e.currentTarget as HTMLElement).style.color = "#123C7A"; }}
                  >
                    <Eye size={13} /> Perfil
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.4)" }}>
          <div className="rounded-2xl p-6 w-full max-w-lg mx-4" style={{ background: "var(--card)" }}>
            <div className="flex justify-between items-center mb-6">
              <h2 style={{ fontSize: "18px", fontWeight: 700, color: "var(--foreground)" }}>Cadastrar Orientador</h2>
              <button onClick={() => setShowForm(false)} style={{ color: "var(--muted-foreground)", fontSize: "20px" }}>✕</button>
            </div>
            <div className="grid grid-cols-2 gap-4">
              {[
                { label: "Nome Completo", col: "col-span-2" },
                { label: "E-mail", col: "" },
                { label: "Departamento", col: "" },
                { label: "Titulação", col: "" },
                { label: "Maior Qualis", col: "" },
                { label: "Lattes URL", col: "col-span-2" },
                { label: "Áreas de Atuação", col: "col-span-2" },
              ].map((f) => (
                <div key={f.label} className={f.col}>
                  <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", display: "block", marginBottom: "6px" }}>{f.label}</label>
                  <input className="w-full rounded-xl px-3 py-2.5 outline-none" style={{ border: "1px solid var(--border)", background: "var(--input-background)", fontSize: "13px" }} onFocus={(e) => { e.currentTarget.style.borderColor = "#123C7A"; }} onBlur={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }} />
                </div>
              ))}
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={() => setShowForm(false)} className="flex-1 rounded-xl py-2.5" style={{ background: "var(--muted)", color: "var(--foreground)", fontWeight: 600 }}>Cancelar</button>
              <button onClick={() => setShowForm(false)} className="flex-1 rounded-xl py-2.5" style={{ background: "#123C7A", color: "#fff", fontWeight: 600 }}>Cadastrar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
