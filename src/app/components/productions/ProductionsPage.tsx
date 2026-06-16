import { useEffect, useMemo, useState } from "react";
import { Plus, ExternalLink, BookOpen, FileText } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import {
  getProductions,
  getVehicles,
  createProduction,
  type Production,
  type Vehicle,
  type TipoProducao,
  type StatusPublicacao,
} from "@/api/productionsApi";

const TIPO_MAP: Record<TipoProducao, { label: string; icon: React.ReactNode; color: string; bg: string }> = {
  artigo_publicado: { label: "Artigo Publicado", icon: <FileText size={16} />, color: "var(--tint-blue-text)", bg: "var(--tint-blue-bg)" },
  artigo_submetido: { label: "Artigo Submetido", icon: <FileText size={16} />, color: "var(--tint-gold-text)", bg: "var(--tint-gold-bg)" },
  livro: { label: "Livro", icon: <BookOpen size={16} />, color: "var(--tint-teal-text)", bg: "var(--tint-teal-bg)" },
  capitulo: { label: "Capítulo", icon: <BookOpen size={16} />, color: "var(--tint-violet-text)", bg: "var(--tint-violet-bg)" },
};

const STATUS_MAP: Record<StatusPublicacao, { label: string; color: string; bg: string }> = {
  publicado: { label: "Publicado", color: "var(--tint-teal-text)", bg: "var(--tint-teal-bg)" },
  submetido: { label: "Submetido", color: "var(--tint-gold-text)", bg: "var(--tint-gold-bg)" },
  aceito: { label: "Aceito", color: "var(--tint-blue-text)", bg: "var(--tint-blue-bg)" },
};

const NIVEL_COLORS: Record<string, { color: string; bg: string }> = {
  A1: { color: "#fff", bg: "#123C7A" },
  A2: { color: "#fff", bg: "#1F8A70" },
  B: { color: "#fff", bg: "#D4A017" },
  C: { color: "#fff", bg: "#94a3b8" },
};

const NIVEIS = ["A1", "A2", "B", "C"];

const emptyForm = {
  titulo: "",
  veiculo_id: "",
  tipo_producao: "artigo_publicado" as TipoProducao,
  status_publicacao: "publicado" as StatusPublicacao,
  doi: "",
  data_realizacao: "",
};

export function ProductionsPage() {
  const { token } = useAuth();
  const [productions, setProductions] = useState<Production[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [submitting, setSubmitting] = useState(false);

  const [filterTipo, setFilterTipo] = useState("todos");
  const [filterNivel, setFilterNivel] = useState("todos");

  function reload() {
    if (!token) return;
    setLoading(true);
    Promise.all([getProductions(token), getVehicles(token)])
      .then(([prods, vehs]) => {
        setProductions(prods);
        setVehicles(vehs);
        setError(null);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(reload, [token]);

  const filtered = useMemo(
    () =>
      productions.filter((p) => {
        const matchTipo = filterTipo === "todos" || p.tipo_producao === filterTipo;
        const matchNivel = filterNivel === "todos" || p.nivel_veiculo === filterNivel;
        return matchTipo && matchNivel;
      }),
    [productions, filterTipo, filterNivel],
  );

  const totalPublicados = productions.filter((p) => p.status_publicacao === "publicado").length;
  const nivelA1A2 = productions.filter((p) => p.nivel_veiculo === "A1" || p.nivel_veiculo === "A2").length;
  const pontuacaoTotal = productions.reduce((sum, p) => sum + (p.pontuacao_calculada ?? 0), 0);

  async function handleSubmit() {
    if (!token || !form.veiculo_id || !form.titulo || !form.data_realizacao) return;
    setSubmitting(true);
    try {
      await createProduction(token, {
        titulo: form.titulo,
        veiculo_id: form.veiculo_id,
        tipo_producao: form.tipo_producao,
        status_publicacao: form.status_publicacao,
        doi: form.doi || null,
        data_realizacao: new Date(form.data_realizacao).toISOString(),
      });
      setForm(emptyForm);
      setShowForm(false);
      reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 style={{ color: "var(--foreground)", marginBottom: "4px" }}>Produções Científicas</h1>
          <p style={{ color: "var(--muted-foreground)", fontSize: "14px" }}>{productions.length} produções registradas</p>
        </div>
        <button onClick={() => setShowForm(true)} className="flex items-center gap-2 rounded-xl px-4 py-2.5" style={{ background: "#123C7A", color: "#fff", fontWeight: 600, fontSize: "14px" }}>
          <Plus size={16} /> Registrar Produção
        </button>
      </div>

      {error && (
        <div className="rounded-xl p-3 mb-4" style={{ background: "var(--tint-danger-bg)", color: "var(--tint-danger-text)", fontSize: "13px" }}>
          {error}
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[
          { label: "Total de Produções", value: productions.length, color: "var(--tint-blue-text)", bg: "var(--tint-blue-bg)", border: "var(--tint-blue-border)" },
          { label: "Publicadas", value: totalPublicados, color: "var(--tint-teal-text)", bg: "var(--tint-teal-bg)", border: "var(--tint-teal-border)" },
          { label: "Nível A1/A2", value: nivelA1A2, color: "var(--tint-gold-text)", bg: "var(--tint-gold-bg)", border: "var(--tint-gold-border)" },
          { label: "Pontuação Total", value: pontuacaoTotal.toFixed(1), color: "var(--tint-violet-text)", bg: "var(--tint-violet-bg)", border: "var(--tint-violet-border)" },
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
          value={filterNivel}
          onChange={(e) => setFilterNivel(e.target.value)}
          className="rounded-xl px-3 py-2 outline-none"
          style={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: "13px", color: "var(--foreground)" }}
        >
          <option value="todos">Todos os Níveis</option>
          {NIVEIS.map((n) => <option key={n} value={n}>Nível {n}</option>)}
        </select>
        <span style={{ fontSize: "13px", color: "var(--muted-foreground)" }}>{filtered.length} resultado(s)</span>
      </div>

      {loading ? (
        <p style={{ color: "var(--muted-foreground)", fontSize: "14px" }}>Carregando produções…</p>
      ) : (
        <div className="space-y-3">
          {filtered.map((prod) => {
            const tipo = TIPO_MAP[prod.tipo_producao] ?? TIPO_MAP.artigo_publicado;
            const status = STATUS_MAP[prod.status_publicacao];
            const nivel = prod.nivel_veiculo ? NIVEL_COLORS[prod.nivel_veiculo] : null;
            return (
              <div key={prod.id} className="saga-card p-5 transition-all">
                <div className="flex items-start gap-4">
                  <div className="rounded-xl flex items-center justify-center flex-shrink-0" style={{ width: 44, height: 44, background: tipo.bg, color: tipo.color }}>
                    {tipo.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <p style={{ fontSize: "14px", fontWeight: 700, color: "var(--foreground)", lineHeight: 1.4 }}>{prod.titulo}</p>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {nivel && (
                          <span className="rounded-lg px-2 py-0.5" style={{ background: nivel.bg, color: nivel.color, fontSize: "11px", fontWeight: 700 }}>
                            {prod.nivel_veiculo}
                          </span>
                        )}
                        {status && (
                          <span className="rounded-lg px-2 py-0.5" style={{ background: status.bg, color: status.color, fontSize: "11px", fontWeight: 600 }}>
                            {status.label}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-3 flex-wrap">
                      <span className="px-2 py-0.5 rounded-lg" style={{ background: tipo.bg, color: tipo.color, fontSize: "10px", fontWeight: 600 }}>{tipo.label}</span>
                      <span style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>📰 {prod.veiculo_nome}</span>
                      <span style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>⭐ {prod.pontuacao_calculada.toFixed(1)} pts (peso {prod.peso_aplicado})</span>
                    </div>
                    {prod.doi && (
                      <div className="flex items-center justify-end mt-3">
                        <a
                          href={`https://doi.org/${prod.doi}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1"
                          style={{ color: "#123C7A", fontSize: "11px", fontWeight: 600 }}
                        >
                          <ExternalLink size={11} /> DOI
                        </a>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
          {filtered.length === 0 && (
            <p style={{ color: "var(--muted-foreground)", fontSize: "14px" }}>Nenhuma produção encontrada.</p>
          )}
        </div>
      )}

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
                <input value={form.titulo} onChange={(e) => setForm({ ...form, titulo: e.target.value })} placeholder="Título completo da produção" className="w-full rounded-xl px-3 py-2.5 outline-none" style={{ border: "1px solid var(--border)", background: "var(--input-background)", fontSize: "13px" }} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", display: "block", marginBottom: "6px" }}>Tipo</label>
                  <select value={form.tipo_producao} onChange={(e) => setForm({ ...form, tipo_producao: e.target.value as TipoProducao })} className="w-full rounded-xl px-3 py-2.5 outline-none" style={{ border: "1px solid var(--border)", background: "var(--input-background)", fontSize: "13px" }}>
                    {Object.entries(TIPO_MAP).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", display: "block", marginBottom: "6px" }}>Status de Publicação</label>
                  <select value={form.status_publicacao} onChange={(e) => setForm({ ...form, status_publicacao: e.target.value as StatusPublicacao })} className="w-full rounded-xl px-3 py-2.5 outline-none" style={{ border: "1px solid var(--border)", background: "var(--input-background)", fontSize: "13px" }}>
                    {Object.entries(STATUS_MAP).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", display: "block", marginBottom: "6px" }}>Veículo de Publicação</label>
                <select value={form.veiculo_id} onChange={(e) => setForm({ ...form, veiculo_id: e.target.value })} className="w-full rounded-xl px-3 py-2.5 outline-none" style={{ border: "1px solid var(--border)", background: "var(--input-background)", fontSize: "13px" }}>
                  <option value="">Selecione um veículo…</option>
                  {vehicles.map((v) => <option key={v.id} value={v.id}>{v.nome} · Nível {v.nivel} (peso {v.peso})</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", display: "block", marginBottom: "6px" }}>Data de Realização</label>
                  <input type="date" value={form.data_realizacao} onChange={(e) => setForm({ ...form, data_realizacao: e.target.value })} className="w-full rounded-xl px-3 py-2.5 outline-none" style={{ border: "1px solid var(--border)", background: "var(--input-background)", fontSize: "13px" }} />
                </div>
                <div>
                  <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", display: "block", marginBottom: "6px" }}>DOI (opcional)</label>
                  <input value={form.doi} onChange={(e) => setForm({ ...form, doi: e.target.value })} placeholder="10.xxxx/xxxxx" className="w-full rounded-xl px-3 py-2.5 outline-none" style={{ border: "1px solid var(--border)", background: "var(--input-background)", fontSize: "13px" }} />
                </div>
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={() => setShowForm(false)} className="flex-1 rounded-xl py-2.5" style={{ background: "var(--muted)", color: "var(--foreground)", fontWeight: 600 }}>Cancelar</button>
              <button onClick={handleSubmit} disabled={submitting || !form.veiculo_id || !form.titulo || !form.data_realizacao} className="flex-1 rounded-xl py-2.5" style={{ background: "#123C7A", color: "#fff", fontWeight: 600, opacity: submitting ? 0.6 : 1 }}>
                {submitting ? "Registrando…" : "Registrar"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
