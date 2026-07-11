/**
 * Tela de estado degradado: sessão Firebase válida, mas o perfil (GET /auth/me)
 * está indisponível — backend fora do ar, lento ou em cold start.
 *
 * Diferente da tela de login: o usuário NÃO está deslogado. Oferece um caminho de
 * recuperação (retry) que recarrega o perfil quando o backend volta, mantendo a
 * sessão. Como alternativa, permite encerrar a sessão e voltar ao login.
 */

import { useState } from "react";
import { useApp } from "../../context/AppContext";
import { AuthLayout } from "./AuthLayout";
import { CloudOff, Loader2, RefreshCw } from "lucide-react";

export function ProfileUnavailablePage() {
  const { retryProfile, logout } = useApp();
  const [retrying, setRetrying] = useState(false);

  const handleRetry = async () => {
    setRetrying(true);
    try {
      // Em sucesso, a guarda de rota do AppContext redireciona para a área do papel.
      await retryProfile();
    } finally {
      setRetrying(false);
    }
  };

  return (
    <AuthLayout>
      <div className="flex flex-col items-center text-center">
        <div className="flex items-center justify-center rounded-2xl mb-6"
          style={{ width: 64, height: 64, background: "var(--tint-gold-bg)" }}>
          <CloudOff size={30} style={{ color: "var(--brand-gold)" }} />
        </div>

        <h2 style={{ fontSize: "24px", fontWeight: 800, color: "var(--foreground)", lineHeight: 1.2, marginBottom: "8px" }}>
          Perfil indisponível no momento
        </h2>
        <p style={{ fontSize: "14px", color: "var(--muted-foreground)", lineHeight: 1.6, maxWidth: 360, marginBottom: "28px" }}>
          Sua sessão continua ativa, mas não foi possível carregar seu perfil — o servidor
          pode estar reiniciando ou temporariamente indisponível. Tente novamente em instantes.
        </p>

        <button
          type="button"
          onClick={handleRetry}
          disabled={retrying}
          className="w-full rounded-xl py-3.5 flex items-center justify-center gap-2.5 transition-all duration-200"
          style={{
            background: retrying ? "#93a7c0" : "linear-gradient(135deg,#0d2d5e,#123C7A)",
            color: "#fff",
            fontSize: "15px",
            fontWeight: 700,
            boxShadow: retrying ? "none" : "0 4px 16px rgba(18,60,122,0.35)",
            cursor: retrying ? "not-allowed" : "pointer",
          }}
        >
          {retrying ? (
            <>
              <Loader2 size={18} className="animate-spin" />
              Tentando reconectar…
            </>
          ) : (
            <>
              <RefreshCw size={18} />
              Tentar novamente
            </>
          )}
        </button>

        <button
          type="button"
          onClick={() => logout()}
          disabled={retrying}
          style={{ fontSize: "13px", color: "var(--muted-foreground)", fontWeight: 600, background: "none", border: "none", marginTop: "16px" }}
          className="hover:underline"
        >
          Sair e voltar ao login
        </button>
      </div>
    </AuthLayout>
  );
}
