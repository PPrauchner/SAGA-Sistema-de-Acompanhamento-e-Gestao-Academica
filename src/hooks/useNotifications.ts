/**
 * Hook React para notificações em tempo real via Firestore onSnapshot (aspecto A05).
 *
 * Responsabilidades:
 * - Assinar a query Firestore: collection 'notifications', where destinatario_id ==
 *   currentUser.uid, where lida == false, orderBy timestamp desc — a única leitura direta
 *   do Firestore permitida no frontend.
 * - Expor: { notifications, unreadCount, markAsRead, loading }.
 * - `notifications`: notificações não lidas do usuário, ordenadas da mais recente.
 * - `unreadCount`: número de não lidas — alimenta o badge no layout.
 * - `markAsRead(id)`: chama PATCH /api/v1/notifications/{id}/read; o backend marca lida=true
 *   e o onSnapshot remove a notificação da lista automaticamente (deixa de casar com o filtro).
 * - Geradas pelo aspecto A05 (@trigger_alerts) em validações, progresso de tasks,
 *   prorrogações e alertas de prazo.
 */

import { useCallback, useEffect, useState } from "react";
import { collection, onSnapshot, orderBy, query, where } from "firebase/firestore";

import { API_URL } from "@/api/authApi";
import { db } from "@/lib/firebase";
import { useAuth } from "@/hooks/useAuth";

export interface Notification {
  id: string;
  tipo: string;
  titulo: string;
  mensagem: string;
  destinatario_id: string;
  entidade_tipo?: string | null;
  entidade_id?: string | null;
  lida: boolean;
  timestamp: Date | null;
  programa_id?: string | null;
}

interface UseNotificationsResult {
  notifications: Notification[];
  unreadCount: number;
  markAsRead: (id: string) => Promise<void>;
  loading: boolean;
}

export function useNotifications(): UseNotificationsResult {
  const { currentUser, token } = useAuth();
  const uid = currentUser?.uid ?? null;

  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!uid) {
      setNotifications([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    const q = query(
      collection(db, "notifications"),
      where("destinatario_id", "==", uid),
      where("lida", "==", false),
      orderBy("timestamp", "desc"),
    );

    const unsubscribe = onSnapshot(
      q,
      (snapshot) => {
        setNotifications(
          snapshot.docs.map((doc) => {
            const data = doc.data();
            return {
              id: doc.id,
              tipo: data.tipo,
              titulo: data.titulo,
              mensagem: data.mensagem,
              destinatario_id: data.destinatario_id,
              entidade_tipo: data.entidade_tipo ?? null,
              entidade_id: data.entidade_id ?? null,
              lida: Boolean(data.lida),
              timestamp: data.timestamp?.toDate?.() ?? null,
              programa_id: data.programa_id ?? null,
            };
          }),
        );
        setLoading(false);
      },
      (err) => {
        console.error("useNotifications onSnapshot", err);
        setLoading(false);
      },
    );

    return unsubscribe;
  }, [uid]);

  const markAsRead = useCallback(
    async (id: string): Promise<void> => {
      if (!token) return;
      const response = await fetch(`${API_URL}/api/v1/notifications/${id}/read`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });
      if (!response.ok) {
        throw new Error(`markAsRead falhou: ${response.status}`);
      }
    },
    [token],
  );

  return {
    notifications,
    unreadCount: notifications.length,
    markAsRead,
    loading,
  };
}
