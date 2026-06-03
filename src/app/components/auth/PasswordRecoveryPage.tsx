import { useState, useRef } from "react";
import { useApp } from "../../context/AppContext";
import { AuthLayout } from "./AuthLayout";
import {
  Mail, ArrowLeft, CheckCircle2, Loader2, RefreshCw, Shield, AlertCircle,
} from "lucide-react";

type Stage = "email" | "otp" | "done";
type FormState = "idle" | "loading" | "error";

const OTP_LEN = 6;

export function PasswordRecoveryPage() {
  const { setCurrentPage } = useApp();
  const [stage, setStage] = useState<Stage>("email");
  const [formState, setFormState] = useState<FormState>("idle");
  const [email, setEmail] = useState("");
  const [emailError, setEmailError] = useState("");
  const [otp, setOtp] = useState<string[]>(Array(OTP_LEN).fill(""));
  const [otpError, setOtpError] = useState("");
  const [resendCountdown, setResendCountdown] = useState(0);
  const inputRefs = useRef<(HTMLInputElement | null)[]>(Array(OTP_LEN).fill(null));
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startCountdown = (secs = 60) => {
    setResendCountdown(secs);
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      setResendCountdown((c) => {
        if (c <= 1) { clearInterval(timerRef.current!); return 0; }
        return c - 1;
      });
    }, 1000);
  };

  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !/\S+@\S+\.\S+/.test(email)) {
      setEmailError("Informe um e-mail institucional válido.");
      return;
    }
    setEmailError("");
    setFormState("loading");
    await new Promise((r) => setTimeout(r, 1100));
    setFormState("idle");
    setStage("otp");
    startCountdown();
  };

  const handleOtpChange = (idx: number, val: string) => {
    if (!/^\d*$/.test(val)) return;
    const next = [...otp];
    next[idx] = val.slice(-1);
    setOtp(next);
    setOtpError("");
    if (val && idx < OTP_LEN - 1) inputRefs.current[idx + 1]?.focus();
  };

  const handleOtpKeyDown = (idx: number, e: React.KeyboardEvent) => {
    if (e.key === "Backspace" && !otp[idx] && idx > 0) {
      inputRefs.current[idx - 1]?.focus();
    }
    if (e.key === "ArrowLeft" && idx > 0) inputRefs.current[idx - 1]?.focus();
    if (e.key === "ArrowRight" && idx < OTP_LEN - 1) inputRefs.current[idx + 1]?.focus();
  };

  const handleOtpPaste = (e: React.ClipboardEvent) => {
    const text = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, OTP_LEN);
    if (text.length) {
      const next = [...otp];
      text.split("").forEach((ch, i) => { next[i] = ch; });
      setOtp(next);
      inputRefs.current[Math.min(text.length, OTP_LEN - 1)]?.focus();
      e.preventDefault();
    }
  };

  const handleOtpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (otp.some((d) => !d)) {
      setOtpError("Preencha todos os 6 dígitos do código.");
      return;
    }
    setFormState("loading");
    await new Promise((r) => setTimeout(r, 1000));
    setFormState("idle");
    setStage("done");
  };

  const handleResend = async () => {
    if (resendCountdown > 0) return;
    setFormState("loading");
    setOtp(Array(OTP_LEN).fill(""));
    await new Promise((r) => setTimeout(r, 800));
    setFormState("idle");
    startCountdown();
  };

  const maskedEmail = email.replace(/(.{2})(.*)(@.*)/, (_, a, b, c) => a + b.replace(/./g, "•") + c);

  return (
    <AuthLayout>
      {/* Back button */}
      <button
        type="button"
        onClick={() => stage === "otp" ? setStage("email") : setCurrentPage("login")}
        className="flex items-center gap-2 mb-8 rounded-xl px-3 py-2 transition-all"
        style={{ background: "#f1f5f9", color: "#374151", fontSize: "13px", fontWeight: 600, border: "none" }}
        onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "#e2e8f0"; }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "#f1f5f9"; }}
      >
        <ArrowLeft size={15} />
        {stage === "otp" ? "Tentar outro e-mail" : "Voltar ao Login"}
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
              Informe seu e-mail institucional e enviaremos um código de verificação de 6 dígitos.
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
                <><Loader2 size={17} className="animate-spin" /> Enviando código…</>
              ) : (
                "Enviar Código de Verificação"
              )}
            </button>
          </form>

          {/* Info box */}
          <div className="mt-6 rounded-xl p-3.5" style={{ background: "#f0f9ff", border: "1px solid #bae6fd" }}>
            <div className="flex items-start gap-2">
              <Shield size={13} style={{ color: "#0284c7", flexShrink: 0, marginTop: 2 }} />
              <p style={{ fontSize: "11px", color: "#0369a1", lineHeight: 1.5 }}>
                Por segurança, o código expira em <strong>10 minutos</strong>. Se não receber o e-mail,
                verifique a pasta de spam ou entre em contato com a secretaria.
              </p>
            </div>
          </div>
        </>
      )}

      {/* ── OTP STAGE ── */}
      {stage === "otp" && (
        <>
          <div className="mb-7">
            <div className="flex items-center justify-center mb-5 rounded-2xl mx-auto"
              style={{ width: 68, height: 68, background: "#dcfce7", border: "2px solid #bbf7d0" }}>
              <Mail size={30} style={{ color: "#16a34a" }} />
            </div>
            <h2 style={{ fontSize: "24px", fontWeight: 800, color: "#0f172a", marginBottom: "6px", textAlign: "center" }}>
              Código de Verificação
            </h2>
            <p style={{ fontSize: "14px", color: "#64748b", textAlign: "center", lineHeight: 1.6, marginBottom: "4px" }}>
              Enviamos um código de 6 dígitos para:
            </p>
            <p style={{ fontSize: "14px", fontWeight: 700, color: "#123C7A", textAlign: "center" }}>
              {maskedEmail}
            </p>
          </div>

          <form onSubmit={handleOtpSubmit} noValidate>
            {/* OTP inputs */}
            <div className="mb-2" onPaste={handleOtpPaste}>
              <div className="flex justify-center gap-2.5 mb-2">
                {otp.map((digit, idx) => (
                  <input
                    key={idx}
                    ref={(el) => { inputRefs.current[idx] = el; }}
                    type="text"
                    inputMode="numeric"
                    maxLength={1}
                    value={digit}
                    onChange={(e) => handleOtpChange(idx, e.target.value)}
                    onKeyDown={(e) => handleOtpKeyDown(idx, e)}
                    className="rounded-xl text-center outline-none transition-all duration-150"
                    style={{
                      width: 52,
                      height: 58,
                      fontSize: "22px",
                      fontWeight: 800,
                      color: "#0f172a",
                      background: digit ? "#f0f4fa" : "#f8fafc",
                      border: `2px solid ${otpError ? "#ef4444" : digit ? "#123C7A" : "#e2e8f0"}`,
                      boxShadow: digit ? "0 2px 8px rgba(18,60,122,0.1)" : "none",
                    }}
                    onFocus={(e) => { e.currentTarget.style.borderColor = "#123C7A"; e.currentTarget.style.background = "#fff"; }}
                    onBlur={(e) => { e.currentTarget.style.borderColor = digit ? "#123C7A" : "#e2e8f0"; e.currentTarget.style.background = digit ? "#f0f4fa" : "#f8fafc"; }}
                    aria-label={`Dígito ${idx + 1} do código`}
                  />
                ))}
              </div>
              {otpError && (
                <div className="flex items-center justify-center gap-1.5">
                  <AlertCircle size={13} style={{ color: "#ef4444" }} />
                  <p style={{ fontSize: "12px", color: "#ef4444", textAlign: "center" }}>{otpError}</p>
                </div>
              )}
            </div>

            {/* Resend */}
            <div className="flex items-center justify-center gap-1.5 mb-6">
              <p style={{ fontSize: "13px", color: "#64748b" }}>Não recebeu?</p>
              {resendCountdown > 0 ? (
                <span style={{ fontSize: "13px", color: "#94a3b8" }}>
                  Reenviar em <strong style={{ color: "#123C7A" }}>{resendCountdown}s</strong>
                </span>
              ) : (
                <button
                  type="button"
                  onClick={handleResend}
                  className="flex items-center gap-1.5"
                  style={{ fontSize: "13px", color: "#123C7A", fontWeight: 700, background: "none", border: "none" }}
                >
                  <RefreshCw size={13} />
                  Reenviar código
                </button>
              )}
            </div>

            <button
              type="submit"
              disabled={formState === "loading" || otp.some((d) => !d)}
              className="w-full rounded-xl py-3.5 flex items-center justify-center gap-2.5 transition-all"
              style={{
                background: otp.some((d) => !d)
                  ? "#94a3b8"
                  : "linear-gradient(135deg,#0d2d5e,#123C7A)",
                color: "#fff",
                fontWeight: 700,
                fontSize: "15px",
                boxShadow: otp.some((d) => !d) ? "none" : "0 4px 14px rgba(18,60,122,0.3)",
                cursor: formState === "loading" || otp.some((d) => !d) ? "not-allowed" : "pointer",
              }}
            >
              {formState === "loading" ? (
                <><Loader2 size={17} className="animate-spin" /> Verificando…</>
              ) : (
                "Verificar Código"
              )}
            </button>
          </form>

          <div className="mt-4 rounded-xl p-3" style={{ background: "#fffbeb", border: "1px solid #fde68a" }}>
            <p style={{ fontSize: "11px", color: "#92400e", textAlign: "center" }}>
              ⏱ O código expira em <strong>10 minutos</strong>
            </p>
          </div>
        </>
      )}

      {/* ── DONE STAGE ── */}
      {stage === "done" && (
        <div className="text-center py-4">
          <div className="flex items-center justify-center mx-auto mb-6 rounded-full"
            style={{ width: 80, height: 80, background: "#dcfce7", border: "3px solid #bbf7d0" }}>
            <CheckCircle2 size={40} style={{ color: "#16a34a" }} />
          </div>
          <h2 style={{ fontSize: "24px", fontWeight: 800, color: "#0f172a", marginBottom: "12px" }}>
            Identidade Confirmada!
          </h2>
          <p style={{ fontSize: "14px", color: "#64748b", lineHeight: 1.65, marginBottom: "32px" }}>
            Código verificado com sucesso. Agora você pode criar uma nova senha para sua conta.
          </p>
          <button
            onClick={() => setCurrentPage("change-password")}
            className="w-full rounded-xl py-3.5 flex items-center justify-center gap-2.5 transition-all"
            style={{
              background: "linear-gradient(135deg,#0d2d5e,#123C7A)",
              color: "#fff",
              fontWeight: 700,
              fontSize: "15px",
              boxShadow: "0 4px 14px rgba(18,60,122,0.3)",
            }}
          >
            Criar Nova Senha
          </button>
        </div>
      )}
    </AuthLayout>
  );
}
