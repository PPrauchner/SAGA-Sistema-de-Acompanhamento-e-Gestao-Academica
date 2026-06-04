/**
 * Hook React para notificações em tempo real via Firestore onSnapshot.
 *
 * Responsabilidades:
 * - Assinar a query Firestore: collection 'notifications', where destinatario_id ==
 *   currentUser.uid, where lida == false, orderBy timestamp desc.
 * - Expor: { notifications, unreadCount, markAsRead }.
 * - `notifications`: array de documentos Notification ordenados por timestamp.
 * - `unreadCount`: número de notificações não lidas — alimenta o badge no layout.
 * - `markAsRead(notificationId)`: chama PATCH /api/v1/notifications/{id}/read para
 *   marcar a notificação como lida no backend e refletir imediatamente na UI via
 *   atualização do onSnapshot.
 * - Geradas pelo aspecto A05 (@trigger_alerts) em operações de validação, progresso de
 *   tasks, prorrogações e alertas de prazo.
 */
