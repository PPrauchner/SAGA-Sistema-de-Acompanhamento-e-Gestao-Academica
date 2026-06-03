import { useState } from "react";
import { CheckCircle2, Circle, Lock, ChevronDown, ChevronRight, ChevronUp } from "lucide-react";

interface CheckItem {
  id: string;
  label: string;
  desc: string;
  status: "concluido" | "pendente" | "bloqueado" | "em_andamento";
  obrigatorio: boolean;
  prazo?: string;
  responsavel: string;
}

interface CheckCategory {
  id: string;
  title: string;
  icon: string;
  items: CheckItem[];
}

const CHECKLIST: CheckCategory[] = [
  {
    id: "matricula",
    title: "Matrícula e Ingresso",
    icon: "📋",
    items: [
      { id: "1", label: "Matrícula Regularizada", desc: "Matrícula ativa no semestre corrente", status: "concluido", obrigatorio: true, responsavel: "Secretaria" },
      { id: "2", label: "Aprovação do Plano de Trabalho", desc: "Plano aprovado pelo orientador e coordenação", status: "concluido", obrigatorio: true, responsavel: "Orientador" },
      { id: "3", label: "Comprovante de Bolsa (se aplicável)", desc: "Contrato de bolsa CNPq/CAPES ativo", status: "concluido", obrigatorio: false, responsavel: "Aluno" },
    ],
  },
  {
    id: "creditos",
    title: "Créditos Acadêmicos",
    icon: "📚",
    items: [
      { id: "4", label: "Créditos em Disciplinas (mín. 24)", desc: "24 créditos em disciplinas obrigatórias/optativas", status: "concluido", obrigatorio: true, responsavel: "Aluno" },
      { id: "5", label: "Créditos em Atividades (mín. 12)", desc: "Participação em eventos, estágios e publicações", status: "em_andamento", obrigatorio: true, responsavel: "Aluno" },
      { id: "6", label: "Exame de Qualificação", desc: "Aprovação no exame de qualificação do programa", status: "concluido", obrigatorio: true, prazo: "2024-06-30", responsavel: "Aluno" },
    ],
  },
  {
    id: "idioma",
    title: "Proficiência em Idioma",
    icon: "🌐",
    items: [
      { id: "7", label: "Proficiência em Inglês", desc: "Certificação TOEFL, IELTS ou exame do programa", status: "concluido", obrigatorio: true, responsavel: "Aluno" },
      { id: "8", label: "Proficiência em 2º Idioma (doutorado)", desc: "Espanhol, Francês ou Alemão", status: "pendente", obrigatorio: true, prazo: "2025-12-31", responsavel: "Aluno" },
    ],
  },
  {
    id: "producao",
    title: "Produção Científica",
    icon: "📝",
    items: [
      { id: "9", label: "Mínimo de Publicações Obrigatórias", desc: "Conforme normas do programa (1 A1/A2 p/ doutorado)", status: "em_andamento", obrigatorio: true, responsavel: "Aluno" },
      { id: "10", label: "Registro no Lattes", desc: "Currículo Lattes atualizado com todas as produções", status: "concluido", obrigatorio: true, responsavel: "Aluno" },
    ],
  },
  {
    id: "defesa",
    title: "Procedimentos de Defesa",
    icon: "🎓",
    items: [
      { id: "11", label: "Submissão do Texto Final", desc: "Entrega da dissertação/tese ao orientador", status: "pendente", obrigatorio: true, prazo: "2026-04-30", responsavel: "Aluno" },
      { id: "12", label: "Aprovação pelo Orientador", desc: "Aval formal do orientador para defesa", status: "bloqueado", obrigatorio: true, responsavel: "Orientador" },
      { id: "13", label: "Composição da Banca", desc: "Aprovação dos membros da banca pela coordenação", status: "bloqueado", obrigatorio: true, responsavel: "Coordenação" },
      { id: "14", label: "Agendamento da Defesa", desc: "Data e local confirmados, divulgação realizada", status: "bloqueado", obrigatorio: true, responsavel: "Secretaria" },
      { id: "15", label: "Entrega da Versão Final", desc: "Versão corrigida pós-defesa no repositório", status: "bloqueado", obrigatorio: true, responsavel: "Aluno" },
      { id: "16", label: "Documentação de Conclusão", desc: "Ata, declarações e documentos finalizados", status: "bloqueado", obrigatorio: true, responsavel: "Secretaria" },
    ],
  },
];

const STATUS_ICONS = {
  concluido: <CheckCircle2 size={20} style={{ color: "#1F8A70" }} />,
  pendente: <Circle size={20} style={{ color: "#D4A017" }} />,
  em_andamento: <Circle size={20} style={{ color: "#123C7A" }} />,
  bloqueado: <Lock size={20} style={{ color: "#94a3b8" }} />,
};

const STATUS_CFG = {
  concluido: { label: "Concluído", color: "#1F8A70", bg: "#dcfce7", dot: "#1F8A70" },
  pendente: { label: "Pendente", color: "#D4A017", bg: "#fef9c3", dot: "#D4A017" },
  em_andamento: { label: "Em andamento", color: "#123C7A", bg: "#eef3fc", dot: "#123C7A" },
  bloqueado: { label: "Bloqueado", color: "#94a3b8", bg: "#f1f5f9", dot: "#94a3b8" },
};

export function ChecklistPage() {
  const [expandedCategories, setExpandedCategories] = useState<string[]>(["matricula", "creditos"]);
  const [expandedItem, setExpandedItem] = useState<string | null>(null);

  const allItems = CHECKLIST.flatMap(c => c.items);
  const total = allItems.length;
  const done = allItems.filter(i => i.status === "concluido").length;
  const mandatory = allItems.filter(i => i.obrigatorio);
  const mandatoryDone = mandatory.filter(i => i.status === "concluido").length;
  const blocked = allItems.filter(i => i.status === "bloqueado").length;

  const toggleCategory = (id: string) => {
    setExpandedCategories(prev =>
      prev.includes(id) ? prev.filter(c => c !== id) : [...prev, id]
    );
  };

  const toggleItem = (id: string) => {
    setExpandedItem(prev => prev === id ? null : id);
  };

  const overallPct = Math.round((done / total) * 100);

  return (
    <div>
      {/* Header */}
      <div className="mb-4 md:mb-6">
        <h1 style={{ color: "var(--foreground)", marginBottom: "4px" }}>Checklist de Conclusão</h1>
        <p style={{ color: "var(--muted-foreground)", fontSize: "14px" }}>Acompanhe todos os requisitos para a conclusão do curso</p>
      </div>

      {/* Overview cards — 1 col on mobile, 3 on md+ */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 md:gap-4 mb-4 md:mb-6">

        {/* Overall progress — full-width banner on mobile */}
        <div className="rounded-2xl p-4 md:p-5" style={{ background: "linear-gradient(135deg, #123C7A, #1a4f9a)" }}>
          <p style={{ color: "rgba(255,255,255,0.7)", fontSize: "13px", marginBottom: "4px" }}>Progresso Geral</p>
          <div className="flex items-end gap-2 mb-3">
            <span style={{ color: "#fff", fontSize: "32px", fontWeight: 800 }}>{done}</span>
            <span style={{ color: "rgba(255,255,255,0.6)", fontSize: "18px", marginBottom: "4px" }}>/{total} itens</span>
          </div>
          <div className="rounded-full overflow-hidden" style={{ height: 10, background: "rgba(255,255,255,0.2)" }}>
            <div className="h-full rounded-full transition-all" style={{ width: `${overallPct}%`, background: "#D4A017" }} />
          </div>
          <p style={{ color: "#D4A017", fontSize: "18px", fontWeight: 800, marginTop: "6px" }}>{overallPct}% completo</p>
        </div>

        {/* Mobile: side-by-side mini cards */}
        <div className="grid grid-cols-2 md:contents gap-3">
          <div className="rounded-2xl p-4 md:p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
            <p style={{ color: "var(--muted-foreground)", fontSize: "12px", marginBottom: "4px" }}>Obrigatórios</p>
            <p style={{ fontSize: "28px", fontWeight: 800, color: "#1F8A70" }}>{mandatoryDone}/{mandatory.length}</p>
            <p style={{ fontSize: "11px", color: "var(--muted-foreground)" }}>concluídos</p>
          </div>
          <div className="rounded-2xl p-4 md:p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
            <p style={{ color: "var(--muted-foreground)", fontSize: "12px", marginBottom: "4px" }}>Bloqueados</p>
            <p style={{ fontSize: "28px", fontWeight: 800, color: "#94a3b8" }}>{blocked}</p>
            <p style={{ fontSize: "11px", color: "var(--muted-foreground)" }}>aguardando etapas</p>
          </div>
        </div>
      </div>

      {/* Status legend — horizontal scroll on mobile */}
      <div className="flex gap-2 mb-4 overflow-x-auto pb-1" style={{ scrollbarWidth: "none" }}>
        {Object.entries(STATUS_CFG).map(([key, cfg]) => (
          <div key={key} className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 flex-shrink-0"
            style={{ background: cfg.bg, border: `1px solid ${cfg.color}30` }}>
            <div style={{ width: 8, height: 8, borderRadius: "50%", background: cfg.dot }} />
            <span style={{ fontSize: "11px", fontWeight: 600, color: cfg.color, whiteSpace: "nowrap" }}>{cfg.label}</span>
          </div>
        ))}
      </div>

      {/* Checklist categories */}
      <div className="space-y-3">
        {CHECKLIST.map((category) => {
          const isExpanded = expandedCategories.includes(category.id);
          const catDone = category.items.filter(i => i.status === "concluido").length;
          const catTotal = category.items.length;
          const catPct = Math.round((catDone / catTotal) * 100);

          return (
            <div key={category.id} className="rounded-2xl overflow-hidden" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>

              {/* Category header — large touch target */}
              <button
                className="w-full flex items-center gap-3 md:gap-4 p-4 text-left"
                onClick={() => toggleCategory(category.id)}
                style={{ background: isExpanded ? "var(--muted)" : "transparent", minHeight: "64px" }}
              >
                <span style={{ fontSize: "22px", flexShrink: 0 }}>{category.icon}</span>
                <div className="flex-1 min-w-0">
                  <p style={{ fontSize: "14px", fontWeight: 700, color: "var(--foreground)" }}>{category.title}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="rounded-full overflow-hidden" style={{ height: 4, background: "var(--border)", width: 80 }}>
                      <div className="h-full rounded-full" style={{ width: `${catPct}%`, background: catPct === 100 ? "#1F8A70" : "#123C7A" }} />
                    </div>
                    <span style={{ fontSize: "11px", color: "var(--muted-foreground)" }}>{catDone}/{catTotal}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className="px-2 py-1 rounded-lg"
                    style={{
                      background: catPct === 100 ? "#dcfce7" : catPct > 50 ? "#eef3fc" : "#fef9c3",
                      color: catPct === 100 ? "#1F8A70" : catPct > 50 ? "#123C7A" : "#D4A017",
                      fontSize: "12px", fontWeight: 700,
                    }}>
                    {catPct}%
                  </span>
                  {isExpanded
                    ? <ChevronUp size={18} style={{ color: "var(--muted-foreground)" }} />
                    : <ChevronDown size={18} style={{ color: "var(--muted-foreground)" }} />
                  }
                </div>
              </button>

              {/* Items */}
              {isExpanded && (
                <div className="border-t" style={{ borderColor: "var(--border)" }}>
                  {category.items.map((item, idx) => {
                    const sc = STATUS_CFG[item.status];
                    const isItemExpanded = expandedItem === item.id;

                    return (
                      <div key={item.id} style={{ borderBottom: idx < category.items.length - 1 ? "1px solid var(--border)" : "none" }}>
                        {/* Item row — touch-friendly */}
                        <button
                          className="w-full flex items-center gap-3 md:gap-4 px-4 py-3.5 text-left transition-all"
                          onClick={() => toggleItem(item.id)}
                          style={{
                            minHeight: "56px",
                            background: isItemExpanded ? `${sc.color}06` : "transparent",
                          }}
                        >
                          <div className="flex-shrink-0">{STATUS_ICONS[item.status]}</div>

                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <p style={{ fontSize: "13px", fontWeight: 600, color: item.status === "bloqueado" ? "var(--muted-foreground)" : "var(--foreground)" }}>
                                {item.label}
                              </p>
                              {item.obrigatorio && (
                                <span className="px-1.5 py-0.5 rounded" style={{ background: "#fee2e2", color: "#dc2626", fontSize: "9px", fontWeight: 700 }}>
                                  OBRIGATÓRIO
                                </span>
                              )}
                            </div>
                            {/* Show desc inline on mobile when not expanded */}
                            {!isItemExpanded && (
                              <p className="mt-0.5" style={{ fontSize: "11px", color: "var(--muted-foreground)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                                {item.desc}
                              </p>
                            )}
                          </div>

                          <div className="flex items-center gap-2 flex-shrink-0">
                            <span className="hidden md:inline-block" style={{ fontSize: "10px", color: "var(--muted-foreground)" }}>
                              {item.responsavel}
                            </span>
                            <span className="px-2 py-1 rounded-lg hidden md:inline-block"
                              style={{ background: sc.bg, color: sc.color, fontSize: "10px", fontWeight: 600 }}>
                              {sc.label}
                            </span>
                            {/* Mobile: colored dot */}
                            <div className="md:hidden rounded-full flex-shrink-0"
                              style={{ width: 10, height: 10, background: sc.dot }} />
                            <ChevronDown
                              size={16}
                              style={{ color: "var(--muted-foreground)", transform: isItemExpanded ? "rotate(180deg)" : "none", transition: "transform 0.2s" }}
                            />
                          </div>
                        </button>

                        {/* Expanded item detail */}
                        {isItemExpanded && (
                          <div className="px-4 pb-4" style={{ background: `${sc.color}04` }}>
                            <p style={{ fontSize: "13px", color: "var(--foreground)", lineHeight: 1.6, marginBottom: "10px" }}>
                              {item.desc}
                            </p>
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="px-2.5 py-1 rounded-lg"
                                style={{ background: sc.bg, color: sc.color, fontSize: "11px", fontWeight: 600 }}>
                                {sc.label}
                              </span>
                              <span className="px-2.5 py-1 rounded-lg"
                                style={{ background: "var(--muted)", color: "var(--muted-foreground)", fontSize: "11px" }}>
                                Responsável: {item.responsavel}
                              </span>
                              {item.prazo && item.status !== "concluido" && (
                                <span className="px-2.5 py-1 rounded-lg"
                                  style={{ background: "#fef9c3", color: "#D4A017", fontSize: "11px", fontWeight: 600 }}>
                                  ⏰ Prazo: {new Date(item.prazo).toLocaleDateString("pt-BR")}
                                </span>
                              )}
                              {item.obrigatorio && (
                                <span className="px-2.5 py-1 rounded-lg"
                                  style={{ background: "#fee2e2", color: "#dc2626", fontSize: "11px", fontWeight: 700 }}>
                                  Obrigatório
                                </span>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
