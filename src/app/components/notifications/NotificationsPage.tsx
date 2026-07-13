import { useState } from "react";
import {
  AlertTriangle,
  Bell,
  CheckCheck,
  CheckCircle,
  Clock,
  Info,
} from "lucide-react";

import { useNotifications, type Notification } from "@/hooks/useNotifications";

const TIPO_MAP: Record<string, { icon: JSX.Element; color: string; bg: string; label: string }> = {
  progresso_task: { icon: <Info size={16} />, color: "#3b82f6", bg: "#dbeafe", label: "Progresso" },
  atividade_validada: { icon: <CheckCircle size={16} />, color: "#1F8A70", bg: "#dcfce7", label: "Validação" },
  prorrogacao_aprovada: { icon: <CheckCircle size={16} />, color: "#1F8A70", bg: "#dcfce7", label: "Prorrogação" },
  prazo_critico: { icon: <AlertTriangle size={16} />, color: "#dc2626", bg: "#fee2e2", label: "Prazo crítico" },
  atividade_submetida: { icon: <Clock size={16} />, color: "#D4A017", bg: "#fef9c3", label: "Submissão" },
};

const TIPO_FALLBACK = { icon: <Info size={16} />, color: "#94a3b8", bg: "#f1f5f9", label: "Notificação" };

function formatTimestamp(value: Date | null): string {
  if (!value) return "";
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(value);
}

function NotifCard({
  notif,
  onMarkRead,
}: {
  notif: Notification;
  onMarkRead: (id: string) => void;
}) {
  const tipo = TIPO_MAP[notif.tipo] ?? TIPO_FALLBACK;
  return (
    <div
      className="flex items-start gap-3 p-4 rounded-2xl mb-2"
      style={{
        background: `${tipo.color}08`,
        border: `1px solid ${tipo.color}30`,
        boxShadow: `0 2px 8px ${tipo.color}12`,
      }}
    >
      <div
        className="rounded-xl flex items-center justify-center flex-shrink-0"
        style={{ width: 34, height: 34, background: tipo.bg, color: tipo.color }}
      >
        {tipo.icon}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1 flex-wrap">
          <p style={{ fontSize: "13px", fontWeight: 700, color: "var(--foreground)", lineHeight: 1.3 }}>
            {notif.titulo}
          </p>
          <span
            className="px-1.5 py-0.5 rounded"
            style={{ background: tipo.bg, color: tipo.color, fontSize: "9px", fontWeight: 600 }}
          >
            {tipo.label}
          </span>
        </div>
        <p style={{ fontSize: "12px", color: "var(--muted-foreground)", lineHeight: 1.5, wordBreak: "break-word" }}>
          {notif.mensagem}
        </p>
        {notif.timestamp && (
          <p style={{ fontSize: "10px", color: "var(--muted-foreground)", marginTop: "4px" }}>
            {formatTimestamp(notif.timestamp)}
          </p>
        )}
      </div>

      <button
        onClick={() => onMarkRead(notif.id)}
        className="flex items-center gap-1 rounded-lg px-2 py-1.5 flex-shrink-0"
        style={{ color: "var(--tint-teal-text)", fontSize: "11px", fontWeight: 600 }}
        title="Marcar como lida"
        aria-label="Marcar como lida"
      >
        <CheckCheck size={14} />
      </button>
    </div>
  );
}

export function NotificationsPage() {
  const { notifications, unreadCount, markAsRead, loading } = useNotifications();
  const [working, setWorking] = useState(false);

  async function markOne(id: string): Promise<void> {
    await markAsRead(id);
  }

  async function markAll(): Promise<void> {
    setWorking(true);
    try {
      await Promise.all(notifications.map((n) => markAsRead(n.id)));
    } finally {
      setWorking(false);
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4 md:mb-6 gap-2">
        <div className="flex items-center gap-3 min-w-0">
          <h1 style={{ color: "var(--foreground)" }}>Notificações</h1>
          {unreadCount > 0 && (
            <span
              className="px-2 py-0.5 rounded-full flex-shrink-0"
              style={{ background: "#D4A017", color: "#fff", fontSize: "12px", fontWeight: 700 }}
            >
              {unreadCount}
            </span>
          )}
        </div>
        {unreadCount > 0 && (
          <button
            onClick={markAll}
            disabled={working}
            className="flex items-center gap-2 rounded-xl px-3 py-2 flex-shrink-0"
            style={{
              background: "var(--card)",
              border: "1px solid var(--border)",
              color: "var(--foreground)",
              fontSize: "12px",
              fontWeight: 600,
              opacity: working ? 0.6 : 1,
            }}
          >
            <CheckCheck size={14} />
            <span className="hidden sm:inline">Marcar todas lidas</span>
            <span className="sm:hidden">Todas lidas</span>
          </button>
        )}
      </div>

      {loading ? (
        <div
          className="rounded-2xl p-12 text-center"
          style={{ background: "var(--card)", border: "1px solid var(--border)", color: "var(--muted-foreground)", fontSize: "14px" }}
        >
          Carregando…
        </div>
      ) : notifications.length === 0 ? (
        <div className="rounded-2xl p-12 text-center" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
          <Bell size={40} style={{ color: "var(--muted-foreground)", margin: "0 auto 12px" }} />
          <p style={{ color: "var(--muted-foreground)", fontSize: "15px", fontWeight: 600 }}>Nenhuma notificação</p>
          <p style={{ color: "var(--muted-foreground)", fontSize: "13px" }}>Você está em dia!</p>
        </div>
      ) : (
        <div>
          {notifications.map((notif) => (
            <NotifCard key={notif.id} notif={notif} onMarkRead={markOne} />
          ))}
        </div>
      )}
    </div>
  );
}
