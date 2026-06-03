import { useState } from "react";
import { useApp } from "../../context/AppContext";
import { AuthLayout } from "./AuthLayout";
import { PasswordStrength, calcPasswordStrength } from "./PasswordStrength";
import {
  Lock, Eye, EyeOff, CheckCircle2, AlertCircle, Loader2, ShieldCheck, KeyRound,
} from "lucide-react";

type FormState = "idle" | "loading" | "success" | "error";

interface FormErrors {
  senha?: string;
  confirmSenha?: string;
}

export function ChangePasswordPage() {
  const { setCurrentPage } = useApp();
  const [senha, setSenha] = useState("");
  const [confirmSenha, setConfirmSenha] = useState("");
  const [showSenha, setShowSenha] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [formState, setFormState] = useState<FormState>("idle");
  const [errors, setErrors] = useState<FormErrors>({});

  const strength = calcPasswordStrength(senha);

  const validate = (): boolean => {
    const errs: FormErrors = {};
    if (senha.length < 8) errs.senha = "A senha deve ter pelo menos 8 caracteres.";
    else if (strength.score < 3) errs.senha = "A senha escolhida é muito fraca.";
    if (!confirmSenha) errs.confirmSenha = "Confirme a nova senha.";
    else if (senha !== confirmSenha) errs.confirmSenha = "As senhas não coincidem.";
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    setFormState("loading");
    await new Promise((r) => setTimeout(r, 1300));
    setFormState("success");
  };

  if (formState === "success") {
    return (
      <AuthLayout>
        <div className="text-center py-8">
          <div className="flex items-center justify-center mx-auto mb-6 rounded-full"
            style={{ width: 88, height: 88, background: "#dcfce7", border: "3px solid #bbf7d0" }}>
            <ShieldCheck size={44} style={{ color: "#16a34a" }} />
          </div>
          <h2 style={{ fontSize: "26px", fontWeight: 800, color: "#0f172a", marginBottom: "10px" }}>
            Senha Atualizada!
          </h2>
          <p style={{ fontSize: "14px", color: "#64748b", lineHeight: 1.65, marginBottom: "10px" }}>
            Sua senha foi alterada com sucesso. Utilize a nova senha no próximo acesso ao sistema.
          </p>
          <p style={{ fontSize: "13px", color: "#94a3b8", marginBottom: "36px" }}>
            Por segurança, todas as sessões ativas foram encerradas.
          </p>
          <div className="rounded-2xl p-4 mb-8" style={{ background: "#f0f9ff", border: "1px solid #bae6fd" }}>
            <p style={{ fontSize: "12px", color: "#0284c7", lineHeight: 1.5 }}>
              🔔 Se você não solicitou esta alteração, entre em contato com a secretaria
              imediatamente em <strong>ppgcc@ufx.br</strong>.
            </p>
          </div>
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
            <CheckCircle2 size={18} />
            Ir para o Login
          </button>
        </div>
      </AuthLayout>
    );
  }

  const passwordsMatch = senha && confirmSenha && senha === confirmSenha;
  const passwordsMismatch = confirmSenha && senha !== confirmSenha;

  return (
    <AuthLayout>
      {/* Header */}
      <div className="mb-8 text-center">
        <div className="flex items-center justify-center mb-5 rounded-2xl mx-auto"
          style={{ width: 68, height: 68, background: "#eef3fc", border: "2px solid #c7d9f5" }}>
          <KeyRound size={30} style={{ color: "#123C7A" }} />
        </div>
        <h2 style={{ fontSize: "26px", fontWeight: 800, color: "#0f172a", lineHeight: 1.2, marginBottom: "6px" }}>
          Criar Nova Senha
        </h2>
        <p style={{ fontSize: "14px", color: "#64748b", lineHeight: 1.6 }}>
          Escolha uma senha forte e segura para proteger seu acesso ao SAGA.
        </p>
      </div>

      <form onSubmit={handleSubmit} noValidate>

        {/* Nova senha */}
        <div className="mb-5">
          <label htmlFor="nova-senha"
            style={{ fontSize: "13px", fontWeight: 600, color: "#374151", display: "block", marginBottom: "6px" }}>
            Nova Senha <span style={{ color: "#ef4444" }}>*</span>
          </label>
          <div className="relative">
            <Lock size={15} className="absolute top-1/2 -translate-y-1/2 left-3.5"
              style={{ color: "#94a3b8", pointerEvents: "none" }} />
            <input
              id="nova-senha"
              type={showSenha ? "text" : "password"}
              value={senha}
              onChange={(e) => { setSenha(e.target.value); setErrors((prev) => ({ ...prev, senha: undefined })); }}
              placeholder="Crie uma senha segura"
              autoComplete="new-password"
              className="w-full rounded-xl pl-10 pr-12 py-3 outline-none transition-all"
              style={{
                border: `2px solid ${errors.senha ? "#ef4444" : "#e2e8f0"}`,
                background: "#f8fafc",
                fontSize: "14px",
                color: "#0f172a",
              }}
              onFocus={(e) => { e.currentTarget.style.borderColor = errors.senha ? "#ef4444" : "#123C7A"; e.currentTarget.style.background = "#fff"; }}
              onBlur={(e) => { e.currentTarget.style.borderColor = errors.senha ? "#ef4444" : "#e2e8f0"; e.currentTarget.style.background = "#f8fafc"; }}
            />
            <button
              type="button"
              onClick={() => setShowSenha(!showSenha)}
              className="absolute top-1/2 -translate-y-1/2 right-3.5 p-1 rounded"
              style={{ color: "#94a3b8", background: "none", border: "none" }}
              aria-label={showSenha ? "Ocultar senha" : "Mostrar senha"}
              onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.color = "#123C7A"; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.color = "#94a3b8"; }}
            >
              {showSenha ? <EyeOff size={17} /> : <Eye size={17} />}
            </button>
          </div>

          {errors.senha && (
            <div className="flex items-center gap-1.5 mt-1.5">
              <AlertCircle size={13} style={{ color: "#ef4444", flexShrink: 0 }} />
              <p style={{ fontSize: "12px", color: "#ef4444" }}>{errors.senha}</p>
            </div>
          )}

          {/* Password strength */}
          <PasswordStrength password={senha} />
        </div>

        {/* Confirm */}
        <div className="mb-6">
          <label htmlFor="confirm-senha"
            style={{ fontSize: "13px", fontWeight: 600, color: "#374151", display: "block", marginBottom: "6px" }}>
            Confirmar Nova Senha <span style={{ color: "#ef4444" }}>*</span>
          </label>
          <div className="relative">
            <Lock size={15} className="absolute top-1/2 -translate-y-1/2 left-3.5"
              style={{ color: "#94a3b8", pointerEvents: "none" }} />
            <input
              id="confirm-senha"
              type={showConfirm ? "text" : "password"}
              value={confirmSenha}
              onChange={(e) => { setConfirmSenha(e.target.value); setErrors((prev) => ({ ...prev, confirmSenha: undefined })); }}
              placeholder="Repita a senha"
              autoComplete="new-password"
              className="w-full rounded-xl pl-10 pr-12 py-3 outline-none transition-all"
              style={{
                border: `2px solid ${errors.confirmSenha ? "#ef4444" : passwordsMatch ? "#22c55e" : "#e2e8f0"}`,
                background: "#f8fafc",
                fontSize: "14px",
                color: "#0f172a",
              }}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = errors.confirmSenha ? "#ef4444" : passwordsMatch ? "#22c55e" : "#123C7A";
                e.currentTarget.style.background = "#fff";
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = errors.confirmSenha ? "#ef4444" : passwordsMatch ? "#22c55e" : "#e2e8f0";
                e.currentTarget.style.background = "#f8fafc";
              }}
            />
            <button
              type="button"
              onClick={() => setShowConfirm(!showConfirm)}
              className="absolute top-1/2 -translate-y-1/2 right-3.5 p-1 rounded"
              style={{ color: "#94a3b8", background: "none", border: "none" }}
              aria-label={showConfirm ? "Ocultar senha" : "Mostrar senha"}
              onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.color = "#123C7A"; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.color = "#94a3b8"; }}
            >
              {showConfirm ? <EyeOff size={17} /> : <Eye size={17} />}
            </button>
          </div>

          {confirmSenha && (
            <div className="flex items-center gap-1.5 mt-1.5">
              {passwordsMatch ? (
                <><CheckCircle2 size={13} style={{ color: "#16a34a" }} />
                  <span style={{ fontSize: "12px", color: "#16a34a", fontWeight: 600 }}>As senhas coincidem ✓</span></>
              ) : passwordsMismatch ? (
                <><AlertCircle size={13} style={{ color: "#ef4444" }} />
                  <span style={{ fontSize: "12px", color: "#ef4444" }}>As senhas não coincidem</span></>
              ) : null}
            </div>
          )}
          {errors.confirmSenha && !confirmSenha && (
            <div className="flex items-center gap-1.5 mt-1.5">
              <AlertCircle size={13} style={{ color: "#ef4444", flexShrink: 0 }} />
              <p style={{ fontSize: "12px", color: "#ef4444" }}>{errors.confirmSenha}</p>
            </div>
          )}
        </div>

        {/* Security tips */}
        <div className="rounded-2xl p-4 mb-6" style={{ background: "#f8fafc", border: "1px solid #e2e8f0" }}>
          <p style={{ fontSize: "12px", fontWeight: 700, color: "#374151", marginBottom: "8px" }}>
            🔐 Dicas para uma senha segura:
          </p>
          <ul className="space-y-1.5">
            {[
              "Use pelo menos 12 caracteres",
              "Combine letras maiúsculas, minúsculas, números e símbolos",
              "Evite informações pessoais (nome, CPF, data de nascimento)",
              "Não reutilize senhas de outros sistemas",
            ].map((tip) => (
              <li key={tip} className="flex items-start gap-2">
                <div className="w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0" style={{ background: "#123C7A" }} />
                <span style={{ fontSize: "11px", color: "#64748b" }}>{tip}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={formState === "loading"}
          className="w-full rounded-xl py-3.5 flex items-center justify-center gap-2.5 transition-all duration-200"
          style={{
            background: formState === "loading"
              ? "#93a7c0"
              : "linear-gradient(135deg,#0d2d5e,#123C7A)",
            color: "#fff",
            fontWeight: 700,
            fontSize: "15px",
            boxShadow: formState === "loading" ? "none" : "0 4px 14px rgba(18,60,122,0.3)",
            cursor: formState === "loading" ? "not-allowed" : "pointer",
          }}
          onMouseEnter={(e) => {
            if (formState !== "loading") {
              (e.currentTarget as HTMLElement).style.boxShadow = "0 6px 22px rgba(18,60,122,0.42)";
              (e.currentTarget as HTMLElement).style.transform = "translateY(-1px)";
            }
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLElement).style.boxShadow = "0 4px 14px rgba(18,60,122,0.3)";
            (e.currentTarget as HTMLElement).style.transform = "none";
          }}
        >
          {formState === "loading" ? (
            <><Loader2 size={18} className="animate-spin" /> Salvando nova senha…</>
          ) : (
            <><ShieldCheck size={18} /> Salvar Nova Senha</>
          )}
        </button>
      </form>

      <p style={{ fontSize: "13px", color: "#94a3b8", textAlign: "center", marginTop: "20px" }}>
        Lembrou a senha?{" "}
        <button type="button" onClick={() => setCurrentPage("login")}
          style={{ color: "#123C7A", fontWeight: 700, background: "none", border: "none" }}
          className="hover:underline">
          Voltar ao Login
        </button>
      </p>
    </AuthLayout>
  );
}
