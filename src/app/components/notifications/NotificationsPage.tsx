import { useState, useRef } from "react";
import { Bell, CheckCheck, Trash2, AlertTriangle, CheckCircle, Info, Clock, Settings } from "lucide-react";

const NOTIFICATIONS_INIT = [
  { id: "1", tipo: "urgente", titulo: "Prazo de entrega vencendo", mensagem: "Carlos Eduardo Lima tem relatório semestral vencendo em 3 dias", timestamp: "há 10 min", lido: false, modulo: "relatorios", avatar: "C" },
  { id: "2", tipo: "aprovacao", titulo: "Prorrogação aprovada", mensagem: "Sua solicitação de prorrogação de prazo foi aprovada pela coordenação", timestamp: "há 1 hora", lido: false, modulo: "prorrogacoes", avatar: "S" },
  { id: "3", tipo: "info", titulo: "Nova publicação registrada", mensagem: "Fernanda Souza registrou nova publicação no Qualis A1: IEEE Transactions", timestamp: "há 2 horas", lido: false, modulo: "producoes", avatar: "F" },
  { id: "4", tipo: "atencao", titulo: "Aluno em situação de atenção", mensagem: "O motor de inferência classificou Marcos Oliveira como risco alto", timestamp: "há 3 horas", lido: false, modulo: "inferencia", avatar: "M" },
  { id: "5", tipo: "info", titulo: "Relatório submetido", mensagem: "Ana Paula Costa submeteu o relatório semestral para avaliação", timestamp: "há 4 horas", lido: true, modulo: "relatorios", avatar: "A" },
  { id: "6", tipo: "sistema", titulo: "Atualização do sistema", mensagem: "SAGA foi atualizado para a versão 2.4.1. Novos recursos disponíveis.", timestamp: "ontem", lido: true, modulo: "sistema", avatar: null },
  { id: "7", tipo: "aprovacao", titulo: "Atividade aprovada", mensagem: "Sua atividade creditável 'Participação SBRC 2024' foi aprovada pelo orientador", timestamp: "ontem", lido: true, modulo: "atividades", avatar: "S" },
  { id: "8", tipo: "prazo", titulo: "Lembrete: Reunião de orientação", mensagem: "Reunião com Profa. Dra. Carla Mendes agendada para amanhã às 14h", timestamp: "ontem", lido: true, modulo: "agenda", avatar: null },
];

const TIPO_MAP: Record<string, { icon: React.ReactNode; color: string; bg: string; label: string }> = {
  urgente: { icon: <AlertTriangle size={16} />, color: "#dc2626", bg: "#fee2e2", label: "Urgente" },
  atencao: { icon: <AlertTriangle size={16} />, color: "#D4A017", bg: "#fef9c3", label: "Atenção" },
  aprovacao: { icon: <CheckCircle size={16} />, color: "#1F8A70", bg: "#dcfce7", label: "Aprovação" },
  info: { icon: <Info size={16} />, color: "#3b82f6", bg: "#dbeafe", label: "Informação" },
  sistema: { icon: <Settings size={16} />, color: "#94a3b8", bg: "#f1f5f9", label: "Sistema" },
  prazo: { icon: <Clock size={16} />, color: "#D4A017", bg: "#fef9c3", label: "Prazo" },
};

const FILTERS = [
  { key: "todas", label: "Todas" },
  { key: "nao-lidas", label: "Não lidas" },
  { key: "urgente", label: "Urgentes" },
  { key: "aprovacao", label: "Aprovações" },
  { key: "info", label: "Informações" },
  { key: "sistema", label: "Sistema" },
];

// Swipeable notification card with left=mark read / right=delete actions
function SwipeableNotifCard({
  notif,
  onMarkRead,
  onDelete,
}: {
  notif: (typeof NOTIFICATIONS_INIT)[0];
  onMarkRead: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  const tipo = TIPO_MAP[notif.tipo] || TIPO_MAP.info;
  const startX = useRef(0);
  const [offset, setOffset] = useState(0);
  const [action, setAction] = useState<"read" | "delete" | null>(null);

  const onTouchStart = (e: React.TouchEvent) => {
    startX.current = e.touches[0].clientX;
  };

  const onTouchMove = (e: React.TouchEvent) => {
    const dx = e.touches[0].clientX - startX.current;
    setOffset(Math.max(-90, Math.min(90, dx)));
    setAction(dx < -30 ? "delete" : dx > 30 ? "read" : null);
  };

  const onTouchEnd = () => {
    if (offset < -60) {
      onDelete(notif.id);
    } else if (offset > 60) {
      onMarkRead(notif.id);
      setOffset(0);
      setAction(null);
    } else {
      setOffset(0);
      setAction(null);
    }
  };

  return (
    <div className="relative overflow-hidden rounded-2xl mb-2" style={{ minHeight: "72px" }}>
      {/* Left action (mark read) */}
      <div className="absolute inset-y-0 left-0 flex items-center px-5 rounded-l-2xl"
        style={{ background: "#1F8A70", opacity: action === "read" ? 1 : 0.6, minWidth: 80 }}>
        <CheckCheck size={20} color="#fff" />
      </div>
      {/* Right action (delete) */}
      <div className="absolute inset-y-0 right-0 flex items-center px-5 rounded-r-2xl"
        style={{ background: "#dc2626", opacity: action === "delete" ? 1 : 0.6, minWidth: 80 }}>
        <Trash2 size={20} color="#fff" />
      </div>

      {/* Card */}
      <div
        style={{
          transform: `translateX(${offset}px)`,
          transition: offset === 0 ? "transform 0.2s ease" : "none",
          position: "relative",
          zIndex: 1,
        }}
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
      >
        <div
          className="flex items-start gap-3 p-4 rounded-2xl"
          style={{
            background: notif.lido ? "var(--card)" : `${tipo.color}08`,
            border: `1px solid ${notif.lido ? "var(--border)" : `${tipo.color}30`}`,
            boxShadow: notif.lido ? "none" : `0 2px 8px ${tipo.color}12`,
          }}
        >
          <div className="rounded-xl flex items-center justify-center flex-shrink-0"
            style={{ width: 34, height: 34, background: tipo.bg, color: tipo.color }}>
            {tipo.icon}
          </div>

          <div className="flex-1 min-w-0" onClick={() => onMarkRead(notif.id)} style={{ cursor: "pointer" }}>
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <p style={{ fontSize: "13px", fontWeight: notif.lido ? 500 : 700, color: "var(--foreground)", lineHeight: 1.3 }}>
                {notif.titulo}
              </p>
              {!notif.lido && <div className="rounded-full flex-shrink-0" style={{ width: 8, height: 8, background: tipo.color }} />}
              <span className="hidden md:inline px-1.5 py-0.5 rounded" style={{ background: tipo.bg, color: tipo.color, fontSize: "9px", fontWeight: 600 }}>
                {tipo.label}
              </span>
            </div>
            <p style={{ fontSize: "12px", color: "var(--muted-foreground)", lineHeight: 1.5, wordBreak: "break-word" }}>{notif.mensagem}</p>
            <p style={{ fontSize: "10px", color: "var(--muted-foreground)", marginTop: "4px" }}>{notif.timestamp}</p>
          </div>

          {/* Desktop action buttons */}
          <div className="hidden md:flex items-center gap-1 flex-shrink-0 self-start">
            {!notif.lido && (
              <button onClick={() => onMarkRead(notif.id)}
                className="p-1.5 rounded-lg transition-colors"
                style={{ color: "var(--tint-teal-text)", width: 28, height: 28 }} title="Marcar como lida"
                aria-label="Marcar como lida"
                onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--tint-teal-bg)"; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "transparent"; }}>
                <CheckCheck size={13} />
              </button>
            )}
            <button onClick={() => onDelete(notif.id)}
              className="p-1.5 rounded-lg transition-colors"
              style={{ color: "var(--muted-foreground)", width: 28, height: 28 }} title="Remover"
              aria-label="Remover"
              onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--tint-danger-bg)"; (e.currentTarget as HTMLElement).style.color = "var(--tint-danger-text)"; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "transparent"; (e.currentTarget as HTMLElement).style.color = "var(--muted-foreground)"; }}>
              <Trash2 size={13} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export function NotificationsPage() {
  const [notifications, setNotifications] = useState(NOTIFICATIONS_INIT);
  const [filter, setFilter] = useState("todas");

  const unreadCount = notifications.filter(n => !n.lido).length;

  const markRead = (id: string) => {
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, lido: true } : n));
  };

  const markAllRead = () => {
    setNotifications(prev => prev.map(n => ({ ...n, lido: true })));
  };

  const deleteNotif = (id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  };

  const filtered = filter === "todas" ? notifications
    : filter === "nao-lidas" ? notifications.filter(n => !n.lido)
    : notifications.filter(n => n.tipo === filter);

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-4 md:mb-6 gap-2">
        <div className="flex items-center gap-3 min-w-0">
          <h1 style={{ color: "var(--foreground)" }}>Notificações</h1>
          {unreadCount > 0 && (
            <span className="px-2 py-0.5 rounded-full flex-shrink-0"
              style={{ background: "#D4A017", color: "#fff", fontSize: "12px", fontWeight: 700 }}>
              {unreadCount}
            </span>
          )}
        </div>
        {unreadCount > 0 && (
          <button onClick={markAllRead}
            className="flex items-center gap-2 rounded-xl px-3 py-2 flex-shrink-0"
            style={{ background: "var(--card)", border: "1px solid var(--border)", color: "var(--foreground)", fontSize: "12px", fontWeight: 600 }}>
            <CheckCheck size={14} />
            <span className="hidden sm:inline">Marcar todas lidas</span>
            <span className="sm:hidden">Todas lidas</span>
          </button>
        )}
      </div>

      {/* Mobile swipe hint */}
      <div className="md:hidden rounded-xl px-3 py-2 mb-3 flex items-center gap-2"
        style={{ background: "var(--tint-blue-bg)", border: "1px solid var(--tint-blue-border)" }}>
        <span style={{ fontSize: "11px", color: "var(--tint-blue-text)" }}>
          💡 Deslize para a direita para marcar como lida · para a esquerda para remover
        </span>
      </div>

      {/* Filter tabs — horizontal scroll on mobile */}
      <div className="flex gap-2 mb-4 overflow-x-auto pb-1" style={{ scrollbarWidth: "none" }}>
        {FILTERS.map((tab) => {
          const count = tab.key === "nao-lidas" ? unreadCount
            : tab.key === "todas" ? notifications.length
            : notifications.filter(n => n.tipo === tab.key).length;
          return (
            <button key={tab.key} onClick={() => setFilter(tab.key)}
              className="px-3 py-2 rounded-xl transition-all flex-shrink-0 flex items-center gap-1.5"
              style={{
                background: filter === tab.key ? "var(--primary)" : "var(--card)",
                color: filter === tab.key ? "var(--primary-foreground)" : "var(--muted-foreground)",
                fontSize: "12px", fontWeight: 600,
                border: "1px solid var(--border)",
                minHeight: "40px",
              }}>
              <span>{tab.label}</span>
              {count > 0 && (
                <span className="rounded-full px-1.5 py-0.5 text-center"
                  style={{
                    background: filter === tab.key ? "rgba(255,255,255,0.25)" : "var(--muted)",
                    fontSize: "10px",
                    fontWeight: 700,
                    minWidth: 18,
                  }}>
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Empty state */}
      {filtered.length === 0 ? (
        <div className="rounded-2xl p-12 text-center" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
          <Bell size={40} style={{ color: "var(--muted-foreground)", margin: "0 auto 12px" }} />
          <p style={{ color: "var(--muted-foreground)", fontSize: "15px", fontWeight: 600 }}>Nenhuma notificação</p>
          <p style={{ color: "var(--muted-foreground)", fontSize: "13px" }}>Você está em dia!</p>
        </div>
      ) : (
        <div>
          {/* Group by read/unread on mobile */}
          {unreadCount > 0 && filtered.some(n => !n.lido) && (
            <p style={{ fontSize: "11px", fontWeight: 700, color: "var(--muted-foreground)", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: "8px", marginTop: "4px" }}>
              Não lidas ({filtered.filter(n => !n.lido).length})
            </p>
          )}
          {filtered.filter(n => !n.lido).map(notif => (
            <SwipeableNotifCard key={notif.id} notif={notif} onMarkRead={markRead} onDelete={deleteNotif} />
          ))}

          {filtered.some(n => n.lido) && filtered.some(n => !n.lido) && (
            <p style={{ fontSize: "11px", fontWeight: 700, color: "var(--muted-foreground)", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: "8px", marginTop: "12px" }}>
              Lidas ({filtered.filter(n => n.lido).length})
            </p>
          )}
          {filtered.filter(n => n.lido).map(notif => (
            <SwipeableNotifCard key={notif.id} notif={notif} onMarkRead={markRead} onDelete={deleteNotif} />
          ))}
        </div>
      )}
    </div>
  );
}
