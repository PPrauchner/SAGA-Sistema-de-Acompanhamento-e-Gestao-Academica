/**
 * Hook para fechar modais/diálogos artesanais com a tecla ESC (issue #316).
 *
 * Os overlays do app são divs posicionadas (fixed inset-0) sem gestão de foco;
 * este hook ouve keydown global enquanto o modal está aberto e dispara o
 * fechamento — mesmo comportamento dos componentes ui/* (Radix), que já tratam
 * ESC nativamente.
 */
import { useEffect } from "react";

export function useEscapeClose(active: boolean, onClose: () => void): void {
  useEffect(() => {
    if (!active) return;
    function handleKeyDown(event: KeyboardEvent): void {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [active, onClose]);
}
