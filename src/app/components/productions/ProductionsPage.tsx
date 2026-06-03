import { useState } from "react";
import { Plus, ExternalLink, BookOpen, FileText, Award, Users, Filter } from "lucide-react";

const PRODUCTIONS = [
  { id: "1", titulo: "Deep Learning Approaches for Medical Image Segmentation: A Comprehensive Review", tipo: "artigo", qualis: "A1", veiculo: "IEEE Transactions on Medical Imaging", ano: 2024, autores: ["Ana Paula Costa", "Roberto Almeida", "Fernanda Souza"], status: "publicado", doi: "10.1109/TMI.2024.001" },
  { id: "2", titulo: "Efficient Graph Neural Networks for Social Network Analysis", tipo: "artigo", qualis: "A2", veiculo: "ACM Computing Surveys", ano: 2024, autores: ["Carlos Eduardo Lima", "Carla Mendes"], status: "publicado", doi: "10.1145/ACM.2024.002" },
  { id: "3", titulo: "Sistemas de Recomendação baseados em Transformers para Educação", tipo: "artigo", qualis: "B1", veiculo: "Revista Brasileira de Informática na Educação", ano: 2024, autores: ["Juliana Martins", "Roberto Almeida"], status: "submetido", doi: null },
  { id: "4", titulo: "Avaliação de Modelos de Linguagem Natural em Português Brasileiro", tipo: "conferencia", qualis: "A2", veiculo: "BRACIS 2024", ano: 2024, autores: ["Marcos Oliveira", "Carla Mendes"], status: "publicado", doi: "10.1007/BRACIS.2024" },
  { id: "5", titulo: "Inteligência Artificial Aplicada ao Diagnóstico Precoce de Doenças", tipo: "livro", qualis: null, veiculo: "Editora UFMG", ano: 2024, autores: ["Roberto Almeida", "Ana Paula Costa", "João Batista"], status: "publicado", doi: null },
  { id: "6", titulo: "Algoritmos Evolutivos para Otimização Multi-objetivo", tipo: "artigo", qualis: "A1", veiculo: "Evolutionary Computation", ano: 2025, autores: ["Fernanda Souza", "João Batista"], status: "em_revisao", doi: null },
  { id: "7", titulo: "Defesa de Dissertação: Aprendizado por Reforço em Robótica Colaborativa", tipo: "dissertacao", qualis: null, veiculo: "PPGCC - UFX", ano: 2025, autores: ["Pedro Henrique", "Roberto Almeida"], status: "publicado", doi: null },
];

const TIPO_MAP: Record<string, { label: string; icon: React.ReactNode; color: string; bg: string }> = {
  artigo: { label: "Artigo", icon: <FileText size={16} />, color: "var(--tint-blue-text)", bg: "var(--tint-blue-bg)" },
  conferencia: { label: "Conferência", icon: <Users size={16} />, color: "var(--tint-violet-text)", bg: "var(--tint-violet-bg)" },
  livro: { label: "Livro/Capítulo", icon: <BookOpen size={16} />, color: "var(--tint-teal-text)", bg: "var(--tint-teal-bg)" },
  dissertacao: { label: "Dissertação", icon: <Award size={16} />, color: "var(--tint-gold-text)", bg: "var(--tint-gold-bg)" },
  tese: { label: "Tese", icon: <Award size={16} />, color: "var(--tint-danger-text)", bg: "var(--tint-danger-bg)" },
};

const STATUS_MAP = {
  publicado: { label: "Publicado", color: "var(--tint-teal-text)", bg: "var(--tint-teal-bg)" },
  submetido: { label: "Submetido", color: "var(--tint-gold-text)", bg: "var(--tint-gold-bg)" },
  em_revisao: { label: "Em Revisão", color: "var(--tint-blue-text)", bg: "var(--tint-blue-bg)" },
  rejeitado: { label: "Rejeitado", color: "var(--tint-danger-text)", bg: "var(--tint-danger-bg)" },
};

const QUALIS_COLORS: Record<string, { color: string; bg: string }> = {
  A1: { color: "#fff", bg: "#123C7A" },
  A2: { color: "#fff", bg: "#1F8A70" },
  B1: { color: "#fff", bg: "#D4A017" },
  B2: { color: "#fff", bg: "#8b5cf6" },
  C: { color: "#fff", bg: "#94a3b8" },
};

export function ProductionsPage() {
  const [showForm, setShowForm] = useState(false);
  const [filterTipo, setFilterTipo] = useState("todos");
  const [filterQualis, setFilterQualis] = useState("todos");

  const filtered = PRODUCTIONS.filter((p) => {
    const matchTipo = filterTipo === "todos" || p.tipo === filterTipo;
    const matchQualis = filterQualis === "todos" || p.qualis === filterQualis;
    return matchTipo && matchQualis;
  });

  const totalPublicados = PRODUCTIONS.filter(p => p.status === "publicado").length;
  const qualisA1A2 = PRODUCTIONS.filter(p => p.qualis === "A1" || p.qualis === "A2").length;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 style={{ color: "var(--foreground)", marginBottom: "4px" }}>Produções Científicas</h1>
          <p style={{ color: "var(--muted-foreground)", fontSize: "14px" }}>{PRODUCTIONS.length} produções registradas</p>
        </div>
        <button onClick={() => setShowForm(true)} className="flex items-center gap-2 rounded-xl px-4 py-2.5" style={{ background: "#123C7A", color: "#fff", fontWeight: 600, fontSize: "14px" }}>
          <Plus size={16} /> Registrar Produção
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[
          { label: "Total de Produções", value: PRODUCTIONS.length, color: "var(--tint-blue-text)", bg: "var(--tint-blue-bg)", border: "var(--tint-blue-border)" },
          { label: "Publicadas", value: totalPublicados, color: "var(--tint-teal-text)", bg: "var(--tint-teal-bg)", border: "var(--tint-teal-border)" },
          { label: "Qualis A1/A2", value: qualisA1A2, color: "var(--tint-gold-text)", bg: "var(--tint-gold-bg)", border: "var(--tint-gold-border)" },
          { label: "Em Revisão", value: PRODUCTIONS.filter(p => p.status === "em_revisao").length, color: "var(--tint-violet-text)", bg: "var(--tint-violet-bg)", border: "var(--tint-violet-border)" },
        ].map((stat) => (
          <div key={stat.label} className="rounded-2xl p-4" style={{ background: stat.bg, border: `1px solid ${stat.border}` }}>
            <p style={{ fontSize: "26px", fontWeight: 800, color: stat.color }}>{stat.value}</p>
            <p style={{ fontSize: "12px", color: stat.color, fontWeight: 600 }}>{stat.label}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <select
          value={filterTipo}
          onChange={(e) => setFilterTipo(e.target.value)}
          className="rounded-xl px-3 py-2 outline-none"
          style={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: "13px", color: "var(--foreground)" }}
        >
          <option value="todos">Todos os Tipos</option>
          {Object.entries(TIPO_MAP).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
        </select>
        <select
          value={filterQualis}
          onChange={(e) => setFilterQualis(e.target.value)}
          className="rounded-xl px-3 py-2 outline-none"
          style={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: "13px", color: "var(--foreground)" }}
        >
          <option value="todos">Todos os Qualis</option>
          {["A1", "A2", "B1", "B2", "C"].map(q => <option key={q} value={q}>Qualis {q}</option>)}
        </select>
        <span style={{ fontSize: "13px", color: "var(--muted-foreground)" }}>{filtered.length} resultado(s)</span>
      </div>

      <div className="space-y-3">
        {filtered.map((prod) => {
          const tipo = TIPO_MAP[prod.tipo] || TIPO_MAP.artigo;
          const status = STATUS_MAP[prod.status as keyof typeof STATUS_MAP];
          const qualis = prod.qualis ? QUALIS_COLORS[prod.qualis] : null;
          return (
            <div
              key={prod.id}
              className="saga-card p-5 transition-all"
            >
              <div className="flex items-start gap-4">
                <div className="rounded-xl flex items-center justify-center flex-shrink-0" style={{ width: 44, height: 44, background: tipo.bg, color: tipo.color }}>
                  {tipo.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <p style={{ fontSize: "14px", fontWeight: 700, color: "var(--foreground)", lineHeight: 1.4 }}>{prod.titulo}</p>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {qualis && (
                        <span className="rounded-lg px-2 py-0.5" style={{ background: qualis.bg, color: qualis.color, fontSize: "11px", fontWeight: 700 }}>
                          {prod.qualis}
                        </span>
                      )}
                      <span className="rounded-lg px-2 py-0.5" style={{ background: status.bg, color: status.color, fontSize: "11px", fontWeight: 600 }}>
                        {status.label}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className="px-2 py-0.5 rounded-lg" style={{ background: tipo.bg, color: tipo.color, fontSize: "10px", fontWeight: 600 }}>{tipo.label}</span>
                    <span style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>📰 {prod.veiculo}</span>
                    <span style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>📅 {prod.ano}</span>
                  </div>
                  <div className="flex items-center justify-between mt-3">
                    <p style={{ fontSize: "11px", color: "var(--muted-foreground)" }}>
                      Autores: {prod.autores.join(", ")}
                    </p>
                    {prod.doi && (
                      <a
                        href={`https://doi.org/${prod.doi}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1"
                        style={{ color: "#123C7A", fontSize: "11px", fontWeight: 600 }}
                      >
                        <ExternalLink size={11} /> DOI
                      </a>
                    )}
                  </div>
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
              <h2 style={{ fontSize: "18px", fontWeight: 700, color: "var(--foreground)" }}>Registrar Produção</h2>
              <button onClick={() => setShowForm(false)} style={{ color: "var(--muted-foreground)", fontSize: "20px" }}>✕</button>
            </div>
            <div className="space-y-4">
              <div>
                <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", display: "block", marginBottom: "6px" }}>Título</label>
                <input placeholder="Título completo da produção" className="w-full rounded-xl px-3 py-2.5 outline-none" style={{ border: "1px solid var(--border)", background: "var(--input-background)", fontSize: "13px" }} onFocus={(e) => { e.currentTarget.style.borderColor = "#123C7A"; }} onBlur={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", display: "block", marginBottom: "6px" }}>Tipo</label>
                  <select className="w-full rounded-xl px-3 py-2.5 outline-none" style={{ border: "1px solid var(--border)", background: "var(--input-background)", fontSize: "13px" }}>
                    {Object.entries(TIPO_MAP).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", display: "block", marginBottom: "6px" }}>Classificação Qualis</label>
                  <select className="w-full rounded-xl px-3 py-2.5 outline-none" style={{ border: "1px solid var(--border)", background: "var(--input-background)", fontSize: "13px" }}>
                    <option value="">N/A</option>
                    {["A1", "A2", "B1", "B2", "C"].map(q => <option key={q} value={q}>{q}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", display: "block", marginBottom: "6px" }}>Veículo de Publicação</label>
                <input placeholder="Revista, conferência ou editora" className="w-full rounded-xl px-3 py-2.5 outline-none" style={{ border: "1px solid var(--border)", background: "var(--input-background)", fontSize: "13px" }} onFocus={(e) => { e.currentTarget.style.borderColor = "#123C7A"; }} onBlur={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", display: "block", marginBottom: "6px" }}>Ano</label>
                  <input type="number" placeholder="2025" className="w-full rounded-xl px-3 py-2.5 outline-none" style={{ border: "1px solid var(--border)", background: "var(--input-background)", fontSize: "13px" }} onFocus={(e) => { e.currentTarget.style.borderColor = "#123C7A"; }} onBlur={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }} />
                </div>
                <div>
                  <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", display: "block", marginBottom: "6px" }}>DOI (opcional)</label>
                  <input placeholder="10.xxxx/xxxxx" className="w-full rounded-xl px-3 py-2.5 outline-none" style={{ border: "1px solid var(--border)", background: "var(--input-background)", fontSize: "13px" }} onFocus={(e) => { e.currentTarget.style.borderColor = "#123C7A"; }} onBlur={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }} />
                </div>
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={() => setShowForm(false)} className="flex-1 rounded-xl py-2.5" style={{ background: "var(--muted)", color: "var(--foreground)", fontWeight: 600 }}>Cancelar</button>
              <button onClick={() => setShowForm(false)} className="flex-1 rounded-xl py-2.5" style={{ background: "#123C7A", color: "#fff", fontWeight: 600 }}>Registrar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
