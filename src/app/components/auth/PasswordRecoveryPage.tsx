import { useState } from "react";
import { sendPasswordResetEmail } from "firebase/auth";
import { useApp } from "../../context/AppContext";
import { auth } from "@/lib/firebase";
import { AuthLayout } from "./AuthLayout";
import { Mail, ArrowLeft, CheckCircle2, Loader2, Shield, AlertCircle } from "lucide-react";

type Stage = "email" | "sent";
type FormState = "idle" | "loading";

export function PasswordRecoveryPage() {
  const { setCurrentPage } = useApp();
  const [stage, setStage] = useState<Stage>("email");
  const [formState, setFormState] = useState<FormState>("idle");
  const [email, setEmail] = useState("");
  const [emailError, setEmailError] = useState("");

  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !/\S+@\S+\.\S+/.test(email)) {
      setEmailError("Informe um e-mail institucional válido.");
      return;
    }
    setEmailError("");
    setFormState("loading");
    try {
      // Firebase envia um link de redefinição; a troca de senha ocorre na
      // página de ação do Firebase, fora do app.
      await sendPasswordResetEmail(auth, email);
      setStage("sent");
    } catch (error) {
      // Loga o código do Firebase (ex: auth/invalid-email) para diagnóstico;
      // a mensagem ao usuário permanece genérica por segurança.
      console.error("Falha ao enviar e-mail de redefinição:", (error as { code?: string }).code);
      setEmailError("Não foi possível enviar o e-mail de redefinição. Tente novamente.");
    } finally {
      setFormState("idle");
    }
  };

  const maskedEmail = email.replace(/(.{2})(.*)(@.*)/, (_, a, b, c) => a + b.replace(/./g, "•") + c);

  return (
    <AuthLayout>
      {/* Back button */}
      <button
        type="button"
        onClick={() => setCurrentPage("login")}
        className="flex items-center gap-2 mb-8 rounded-xl px-3 py-2 transition-all"
        style={{ background: "#f1f5f9", color: "#374151", fontSize: "13px", fontWeight: 600, border: "none" }}
        onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "#e2e8f0"; }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "#f1f5f9"; }}
      >
        <ArrowLeft size={15} />
        Voltar ao Login
      </button>

      {/* ── EMAIL STAGE ── */}
      {stage === "email" && (
        <>
          {/* Icon header */}
          <div className="mb-7">
            <div className="flex items-center justify-center mb-5 rounded-2xl mx-auto"
              style={{ width: 68, height: 68, background: "#eef3fc", border: "2px solid #c7d9f5" }}>
              <Mail size={30} style={{ color: "#123C7A" }} />
            </div>
            <h2 style={{ fontSize: "24px", fontWeight: 800, color: "#0f172a", marginBottom: "6px", textAlign: "center" }}>
              Recuperar Senha
            </h2>
            <p style={{ fontSize: "14px", color: "#64748b", textAlign: "center", lineHeight: 1.6 }}>
              Informe seu e-mail institucional e enviaremos um link para redefinir sua senha.
            </p>
          </div>

          <form onSubmit={handleEmailSubmit} noValidate>
            <div className="mb-5">
              <label htmlFor="email-recovery"
                style={{ fontSize: "13px", fontWeight: 600, color: "#374151", display: "block", marginBottom: "6px" }}>
                E-mail Institucional
              </label>
              <div className="relative">
                <Mail size={15} className="absolute top-1/2 -translate-y-1/2 left-3.5"
                  style={{ color: "#94a3b8", pointerEvents: "none" }} />
                <input
                  id="email-recovery"
                  type="email"
                  value={email}
                  onChange={(e) => { setEmail(e.target.value); setEmailError(""); }}
                  placeholder="seu.nome@ppg.ufx.br"
                  autoComplete="email"
                  className="w-full rounded-xl pl-10 pr-4 py-3 outline-none transition-all"
                  style={{
                    border: `2px solid ${emailError ? "#ef4444" : "#e2e8f0"}`,
                    background: "#f8fafc",
                    fontSize: "14px",
                    color: "#0f172a",
                  }}
                  onFocus={(e) => { e.currentTarget.style.borderColor = emailError ? "#ef4444" : "#123C7A"; e.currentTarget.style.background = "#fff"; }}
                  onBlur={(e) => { e.currentTarget.style.borderColor = emailError ? "#ef4444" : "#e2e8f0"; e.currentTarget.style.background = "#f8fafc"; }}
                />
              </div>
              {emailError && (
                <div className="flex items-center gap-1.5 mt-1.5">
                  <AlertCircle size={13} style={{ color: "#ef4444", flexShrink: 0 }} />
                  <p style={{ fontSize: "12px", color: "#ef4444" }}>{emailError}</p>
                </div>
              )}
            </div>

            <button
              type="submit"
              disabled={formState === "loading"}
              className="w-full rounded-xl py-3.5 flex items-center justify-center gap-2.5 transition-all"
              style={{
                background: "linear-gradient(135deg,#0d2d5e,#123C7A)",
                color: "#fff",
                fontWeight: 700,
                fontSize: "15px",
                boxShadow: "0 4px 14px rgba(18,60,122,0.3)",
                cursor: formState === "loading" ? "not-allowed" : "pointer",
              }}
            >
              {formState === "loading" ? (
                <><Loader2 size={17} className="animate-spin" /> Enviando link…</>
              ) : (
                "Enviar Link de Redefinição"
              )}
            </button>
          </form>

          {/* Info box */}
          <div className="mt-6 rounded-xl p-3.5" style={{ background: "#f0f9ff", border: "1px solid #bae6fd" }}>
            <div className="flex items-start gap-2">
              <Shield size={13} style={{ color: "#0284c7", flexShrink: 0, marginTop: 2 }} />
              <p style={{ fontSize: "11px", color: "#0369a1", lineHeight: 1.5 }}>
                Por segurança, o link expira em algumas horas. Se não receber o e-mail,
                verifique a pasta de spam ou entre em contato com a secretaria.
              </p>
            </div>
          </div>
        </>
      )}

      {/* ── SENT STAGE ── */}
      {stage === "sent" && (
        <div className="text-center py-4">
          <div className="flex items-center justify-center mx-auto mb-6 rounded-full"
            style={{ width: 80, height: 80, background: "#dcfce7", border: "3px solid #bbf7d0" }}>
            <CheckCircle2 size={40} style={{ color: "#16a34a" }} />
          </div>
          <h2 style={{ fontSize: "24px", fontWeight: 800, color: "#0f172a", marginBottom: "12px" }}>
            E-mail Enviado!
          </h2>
          <p style={{ fontSize: "14px", color: "#64748b", lineHeight: 1.65, marginBottom: "8px" }}>
            Se houver uma conta associada a <strong style={{ color: "#123C7A" }}>{maskedEmail}</strong>,
            você receberá um link para redefinir sua senha.
          </p>
          <p style={{ fontSize: "13px", color: "#94a3b8", lineHeight: 1.6, marginBottom: "32px" }}>
            Abra o link no e-mail para criar uma nova senha e depois retorne para fazer login.
          </p>
          <button
            onClick={() => setCurrentPage("login")}
            className="w-full rounded-xl py-3.5 flex items-center justify-center gap-2.5 transition-all"
            style={{
              background: "linear-gradient(135deg,#0d2d5e,#123C7A)",
              color: "#fff",
              fontWeight: 700,
              fontSize: "15px",
              boxShadow: "0 4px 14px rgba(18,60,122,0.3)",
            }}
          >
            Voltar ao Login
          </button>
        </div>
      )}
    </AuthLayout>
  );
}
