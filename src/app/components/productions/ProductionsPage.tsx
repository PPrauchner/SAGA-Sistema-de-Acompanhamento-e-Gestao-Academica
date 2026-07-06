import { useEffect, useMemo, useState } from "react";
import { Plus, ExternalLink, BookOpen, FileText, X, Check } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { validateReasonableDate } from "@/lib/dateValidation";
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
  artigo: { label: "Artigo", icon: <FileText size={16} />, color: "var(--tint-blue-text)", bg: "var(--tint-blue-bg)" },
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
  A2: { color: "#fff", bg: "#1A56A0" },
  A3: { color: "#fff", bg: "#2C6FB5" },
  A4: { color: "#fff", bg: "#4A89C8" },
  A5: { color: "#fff", bg: "#6AA3D8" },
  A6: { color: "#fff", bg: "#D4A017" },
  A7: { color: "#fff", bg: "#E0B84D" },
  A8: { color: "#fff", bg: "#B89230" },
  SC: { color: "#fff", bg: "#94a3b8" },
};

const NIVEIS = ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "SC"];

const NIVEL_LABELS: Record<string, string> = {
  A1: "Nível A1",
  A2: "Nível A2",
  A3: "Nível A3",
  A4: "Nível A4",
  A5: "Nível A5",
  A6: "Nível A6",
  A7: "Nível A7",
  A8: "Nível A8",
  SC: "Sem Classificação",
};

const emptyForm = {
  titulo: "",
  veiculo_id: "",
  tipo_producao: "artigo" as TipoProducao,
  status_publicacao: "publicado" as StatusPublicacao,
  doi: "",
  data_realizacao: "",
};

export function ProductionsPage() {
  const { token, role } = useAuth();
  const [productions, setProductions] = useState<Production[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [submitting, setSubmitting] = useState(false);
  const [dateError, setDateError] = useState<string | null>(null);

  const [filterTipo, setFilterTipo] = useState("todos");
  const [filterNivel, setFilterNivel] = useState("todos");
  const [filterAluno, setFilterAluno] = useState("todos");

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

  // Na visão da coordenação cada produção pode ser de um aluno diferente; oferecer filtro.
  const isCoordenacao = role === "coordenacao";
  const canRegisterProduction = role === "aluno";

  const alunos = useMemo(() => {
    const byId = new Map<string, string>();
    productions.forEach((p) => byId.set(p.aluno_id, p.aluno_nome));
    return Array.from(byId, ([id, nome]) => ({ id, nome })).sort((a, b) =>
      a.nome.localeCompare(b.nome),
    );
  }, [productions]);

  const filtered = useMemo(
    () =>
      productions.filter((p) => {
        const matchTipo = filterTipo === "todos" || p.tipo_producao === filterTipo;
        const matchNivel = filterNivel === "todos" || p.nivel_veiculo === filterNivel;
        const matchAluno = filterAluno === "todos" || p.aluno_id === filterAluno;
        return matchTipo && matchNivel && matchAluno;
      }),
    [productions, filterTipo, filterNivel, filterAluno],
  );

  const totalPublicados = productions.filter((p) => p.status_publicacao === "publicado").length;
  const nivelA1A2 = productions.filter((p) => p.nivel_veiculo === "A1" || p.nivel_veiculo === "A2").length;
  const pontuacaoTotal = productions.reduce((sum, p) => sum + (p.pontuacao_calculada ?? 0), 0);

  async function handleSubmit() {
    if (!canRegisterProduction || !token || !form.veiculo_id || !form.titulo || !form.data_realizacao) return;
    const dataInvalida = validateReasonableDate(form.data_realizacao, { allowFuture: false });
    if (dataInvalida) {
      setDateError(dataInvalida);
      return;
    }
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
      setDateError(null);
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
        {canRegisterProduction && (
          <button onClick={() => { setDateError(null); setShowForm(true); }} className="flex items-center gap-2 rounded-xl px-4 py-2.5" style={{ background: "#123C7A", color: "#fff", fontWeight: 600, fontSize: "14px" }}>
            <Plus size={16} /> Registrar Produção
          </button>
        )}
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
          {NIVEIS.map((n) => <option key={n} value={n}>{NIVEL_LABELS[n]}</option>)}
        </select>
        {isCoordenacao && (
          <select
            value={filterAluno}
            onChange={(e) => setFilterAluno(e.target.value)}
            className="rounded-xl px-3 py-2 outline-none"
            style={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: "13px", color: "var(--foreground)" }}
          >
            <option value="todos">Todos os Alunos</option>
            {alunos.map((a) => <option key={a.id} value={a.id}>{a.nome}</option>)}
          </select>
        )}
        <span style={{ fontSize: "13px", color: "var(--muted-foreground)" }}>{filtered.length} resultado(s)</span>
      </div>

      {loading ? (
        <p style={{ color: "var(--muted-foreground)", fontSize: "14px" }}>Carregando produções…</p>
      ) : (
        <div className="space-y-3">
          {filtered.map((prod) => {
            const tipo = TIPO_MAP[prod.tipo_producao] ?? TIPO_MAP.artigo;
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
                      <span style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>👤 {prod.aluno_nome}</span>
                      <span style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>📰 {prod.veiculo_nome}</span>
                      {prod.autores && prod.autores.length > 1 && (
                        <span style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>✍️ {prod.autores.length} autores</span>
                      )}
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

      {canRegisterProduction && showForm && (
        <div
          className="fixed inset-0 z-50 flex items-end md:items-center justify-center md:p-4"
          style={{ background: "rgba(0,0,0,0.5)", backdropFilter: "blur(2px)" }}
          onClick={() => setShowForm(false)}
        >
          <div
            className="w-full md:max-w-2xl rounded-t-2xl md:rounded-2xl flex flex-col"
            style={{ background: "var(--card)", boxShadow: "0 -8px 40px rgba(0,0,0,0.2)", maxHeight: "92vh" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="md:hidden flex justify-center pt-3 pb-1">
              <div style={{ width: 36, height: 4, borderRadius: 2, background: "var(--border)" }} />
            </div>
            <div className="flex items-center justify-between p-4 md:p-6 pb-4" style={{ borderBottom: "1px solid var(--border)" }}>
              <div className="flex items-center gap-3">
                <div className="rounded-xl p-2" style={{ background: "#eef3fc" }}><Plus size={16} style={{ color: "#123C7A" }} /></div>
                <h2 style={{ fontSize: 16, fontWeight: 700, color: "var(--foreground)" }}>Registrar Produção</h2>
              </div>
              <button onClick={() => setShowForm(false)} className="rounded-xl p-2" style={{ background: "var(--muted)", color: "var(--muted-foreground)" }}><X size={16} /></button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-5">
              {/* Tipo */}
              <div>
                <label style={{ fontSize: 11, fontWeight: 700, color: "var(--muted-foreground)", display: "block", marginBottom: 8 }}>TIPO DE PRODUÇÃO *</label>
                <div className="grid grid-cols-3 gap-2">
                  {(Object.keys(TIPO_MAP) as TipoProducao[]).map((t) => {
                    const cfg = TIPO_MAP[t];
                    const selected = form.tipo_producao === t;
                    return (
                      <button
                        key={t}
                        onClick={() => setForm({ ...form, tipo_producao: t })}
                        className="flex flex-col items-center gap-1.5 rounded-xl p-3 transition-all"
                        style={{ background: selected ? cfg.bg : "var(--muted)", border: `2px solid ${selected ? cfg.color : "transparent"}`, color: selected ? cfg.color : "var(--muted-foreground)" }}
                      >
                        <span style={{ color: selected ? cfg.color : "var(--muted-foreground)" }}>{cfg.icon}</span>
                        <span style={{ fontSize: 11, fontWeight: 700 }}>{cfg.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Título */}
              <FInput label="TÍTULO *" value={form.titulo} onChange={(v) => setForm({ ...form, titulo: v })} placeholder="Título completo da produção" />

              {/* Veículo */}
              <div>
                <label style={{ fontSize: 11, fontWeight: 700, color: "var(--muted-foreground)", display: "block", marginBottom: 6 }}>VEÍCULO DE PUBLICAÇÃO *</label>
                <select
                  value={form.veiculo_id}
                  onChange={(e) => setForm({ ...form, veiculo_id: e.target.value })}
                  className="w-full rounded-xl px-3 py-2.5 outline-none"
                  style={{ border: "1px solid var(--border)", background: "var(--muted)", fontSize: 12, color: "var(--foreground)" }}
                >
                  <option value="">Selecione um veículo…</option>
                  {vehicles.map((v) => <option key={v.id} value={v.id}>{v.nome} · Nível {v.nivel} (peso {v.peso})</option>)}
                </select>
              </div>

              {/* Status de Publicação */}
              <div>
                <label style={{ fontSize: 11, fontWeight: 700, color: "var(--muted-foreground)", display: "block", marginBottom: 6 }}>STATUS DE PUBLICAÇÃO</label>
                <div className="flex flex-wrap gap-1.5">
                  {(Object.keys(STATUS_MAP) as StatusPublicacao[]).map((s) => {
                    const cfg = STATUS_MAP[s];
                    const selected = form.status_publicacao === s;
                    return (
                      <button
                        key={s}
                        onClick={() => setForm({ ...form, status_publicacao: s })}
                        className="rounded-lg px-2.5 py-1 transition-all"
                        style={{ background: selected ? cfg.bg : "var(--muted)", color: selected ? cfg.color : "var(--muted-foreground)", border: `1px solid ${selected ? cfg.color + "60" : "var(--border)"}`, fontSize: 11, fontWeight: 700 }}
                      >
                        {cfg.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Data / DOI */}
              <div className="grid grid-cols-2 gap-4">
                <FInput label="DATA DE REALIZAÇÃO *" type="date" value={form.data_realizacao} onChange={(v) => { setForm({ ...form, data_realizacao: v }); if (dateError) setDateError(null); }} onBlur={(v) => setDateError(validateReasonableDate(v, { allowFuture: false }))} error={dateError} />
                <FInput label="DOI (OPCIONAL)" value={form.doi} onChange={(v) => setForm({ ...form, doi: v })} placeholder="10.xxxx/xxxxx" />
              </div>
            </div>

            <div className="flex gap-3 p-6 pt-0">
              <button onClick={() => setShowForm(false)} className="px-5 rounded-xl py-2.5" style={{ background: "var(--muted)", color: "var(--foreground)", fontWeight: 700, fontSize: 13 }}>Cancelar</button>
              <button
                onClick={handleSubmit}
                disabled={submitting || !form.veiculo_id || !form.titulo || !form.data_realizacao}
                className="flex-1 flex items-center justify-center gap-2 rounded-xl py-2.5"
                style={{
                  background: submitting || !form.veiculo_id || !form.titulo || !form.data_realizacao ? "#e5e7eb" : "#123C7A",
                  color: submitting || !form.veiculo_id || !form.titulo || !form.data_realizacao ? "#9ca3af" : "#fff",
                  fontWeight: 700,
                  fontSize: 13,
                }}
              >
                <Check size={14} /> {submitting ? "Registrando…" : "Registrar"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function FInput({ label, value, onChange, placeholder, type = "text", onBlur, error }: { label: string; value: string; onChange: (v: string) => void; placeholder?: string; type?: string; onBlur?: (v: string) => void; error?: string | null }) {
  return (
    <div>
      <label style={{ fontSize: 11, fontWeight: 700, color: "var(--muted-foreground)", display: "block", marginBottom: 6 }}>{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-xl px-3 py-2.5 outline-none"
        style={{ border: `1px solid ${error ? "#dc2626" : "var(--border)"}`, background: "var(--muted)", fontSize: 12, color: "var(--foreground)" }}
        onFocus={(e) => (e.currentTarget.style.borderColor = "#123C7A")}
        onBlur={(e) => {
          e.currentTarget.style.borderColor = error ? "#dc2626" : "var(--border)";
          onBlur?.(e.target.value);
        }}
      />
      {error && <p style={{ fontSize: 11, color: "#dc2626", marginTop: 6 }}>{error}</p>}
    </div>
  );
}
