import { useState } from "react";
import { AlertCircle, CheckCircle2, ChevronRight, Eye, EyeOff, Loader2, Lock, Mail, Shield } from "lucide-react";

import { useApp } from "../../context/AppContext";
import { AuthLayout } from "./AuthLayout";

type FormState = "idle" | "loading" | "success" | "error";

export function LoginPage() {
  const { login, setCurrentPage } = useApp();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [formState, setFormState] = useState<FormState>("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const validate = () => {
    if (!email.trim()) return "Informe o e-mail institucional.";
    if (!/\S+@\S+\.\S+/.test(email)) return "E-mail invalido.";
    if (!password) return "Informe a senha.";
    if (password.length < 6) return "Senha deve ter pelo menos 6 caracteres.";
    return "";
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const err = validate();
    if (err) {
      setErrorMsg(err);
      return;
    }
    setErrorMsg("");
    setFormState("loading");
    try {
      await login(email, password);
      // O AppContext redireciona para a area do papel quando o perfil chega de /auth/me.
      setFormState("success");
    } catch {
      setFormState("idle");
      setErrorMsg("E-mail ou senha invalidos.");
    }
  };

  const isLoading = formState === "loading";
  const isSuccess = formState === "success";

  return (
    <AuthLayout>
      <div className="mb-8">
        <h2 style={{ fontSize: "26px", fontWeight: 800, color: "#0f172a", lineHeight: 1.2, marginBottom: "6px" }}>
          Acesse sua conta
        </h2>
        <p style={{ fontSize: "14px", color: "#64748b", lineHeight: 1.5 }}>
          Entre com suas credenciais institucionais para continuar.
        </p>
      </div>

      <form onSubmit={handleSubmit} noValidate>
        <div className="mb-4">
          <label
            htmlFor="email"
            style={{ fontSize: "13px", fontWeight: 600, color: "#374151", display: "block", marginBottom: "6px" }}
          >
            E-mail Institucional
          </label>
          <div className="relative">
            <Mail
              size={15}
              className="absolute top-1/2 -translate-y-1/2 left-3.5"
              style={{ color: "#94a3b8", pointerEvents: "none" }}
            />
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                setErrorMsg("");
              }}
              placeholder="nome@unipampa.edu.br"
              autoComplete="email"
              disabled={isLoading || isSuccess}
              className="w-full rounded-xl pl-10 pr-4 py-3 outline-none transition-all duration-150"
              style={{
                border: errorMsg && !password ? "2px solid #ef4444" : "2px solid #e2e8f0",
                background: "#f8fafc",
                fontSize: "14px",
                color: "#0f172a",
              }}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = "#123C7A";
                e.currentTarget.style.background = "#fff";
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = "#e2e8f0";
                e.currentTarget.style.background = "#f8fafc";
              }}
            />
          </div>
        </div>

        <div className="mb-4">
          <div className="flex items-center justify-between mb-1.5">
            <label htmlFor="password" style={{ fontSize: "13px", fontWeight: 600, color: "#374151" }}>
              Senha
            </label>
            <button
              type="button"
              onClick={() => setCurrentPage("password-recovery")}
              style={{ fontSize: "12px", color: "#123C7A", fontWeight: 600, background: "none", border: "none" }}
              className="hover:underline"
            >
              Esqueci minha senha
            </button>
          </div>
          <div className="relative">
            <Lock
              size={15}
              className="absolute top-1/2 -translate-y-1/2 left-3.5"
              style={{ color: "#94a3b8", pointerEvents: "none" }}
            />
            <input
              id="password"
              type={showPw ? "text" : "password"}
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setErrorMsg("");
              }}
              placeholder="********"
              autoComplete="current-password"
              disabled={isLoading || isSuccess}
              className="w-full rounded-xl pl-10 pr-12 py-3 outline-none transition-all duration-150"
              style={{
                border: "2px solid #e2e8f0",
                background: "#f8fafc",
                fontSize: "14px",
                color: "#0f172a",
              }}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = "#123C7A";
                e.currentTarget.style.background = "#fff";
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = "#e2e8f0";
                e.currentTarget.style.background = "#f8fafc";
              }}
            />
            <button
              type="button"
              onClick={() => setShowPw(!showPw)}
              className="absolute top-1/2 -translate-y-1/2 right-3.5 p-1 rounded transition-colors"
              style={{ color: "#94a3b8" }}
              aria-label={showPw ? "Ocultar senha" : "Mostrar senha"}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = "#123C7A";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = "#94a3b8";
              }}
            >
              {showPw ? <EyeOff size={17} /> : <Eye size={17} />}
            </button>
          </div>
        </div>

        <div className="flex items-center gap-2.5 mb-5">
          <button
            type="button"
            onClick={() => setRememberMe(!rememberMe)}
            className="flex items-center justify-center rounded-md flex-shrink-0 transition-all"
            style={{
              width: 18,
              height: 18,
              background: rememberMe ? "#123C7A" : "#f1f5f9",
              border: `2px solid ${rememberMe ? "#123C7A" : "#cbd5e1"}`,
            }}
            aria-checked={rememberMe}
            role="checkbox"
          >
            {rememberMe && (
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                <path d="M2 5L4 7L8 3" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            )}
          </button>
          <span style={{ fontSize: "13px", color: "#374151" }}>Manter conectado(a)</span>
        </div>

        {errorMsg && (
          <div className="flex items-start gap-2.5 rounded-xl p-3 mb-4" style={{ background: "#fef2f2", border: "1px solid #fecaca" }}>
            <AlertCircle size={15} style={{ color: "#dc2626", flexShrink: 0, marginTop: 1 }} />
            <p style={{ fontSize: "13px", color: "#dc2626", lineHeight: 1.4 }}>{errorMsg}</p>
          </div>
        )}

        {isSuccess && (
          <div className="flex items-center gap-2.5 rounded-xl p-3 mb-4" style={{ background: "#f0fdf4", border: "1px solid #bbf7d0" }}>
            <CheckCircle2 size={16} style={{ color: "#16a34a", flexShrink: 0 }} />
            <p style={{ fontSize: "13px", color: "#16a34a", fontWeight: 600 }}>Autenticado! Redirecionando...</p>
          </div>
        )}

        <button
          type="submit"
          disabled={isLoading || isSuccess}
          className="w-full rounded-xl py-3.5 flex items-center justify-center gap-2.5 transition-all duration-200"
          style={{
            background: isSuccess ? "linear-gradient(135deg,#1F8A70,#16a34a)" : isLoading ? "#93a7c0" : "linear-gradient(135deg,#0d2d5e,#123C7A)",
            color: "#fff",
            fontSize: "15px",
            fontWeight: 700,
            boxShadow: isLoading || isSuccess ? "none" : "0 4px 16px rgba(18,60,122,0.35)",
            cursor: isLoading || isSuccess ? "not-allowed" : "pointer",
          }}
          onMouseEnter={(e) => {
            if (!isLoading && !isSuccess) {
              e.currentTarget.style.boxShadow = "0 6px 22px rgba(18,60,122,0.45)";
              e.currentTarget.style.transform = "translateY(-1px)";
            }
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.boxShadow = "0 4px 16px rgba(18,60,122,0.35)";
            e.currentTarget.style.transform = "none";
          }}
        >
          {isLoading ? (
            <>
              <Loader2 size={18} className="animate-spin" />
              Verificando credenciais...
            </>
          ) : isSuccess ? (
            <>
              <CheckCircle2 size={18} />
              Acesso autorizado
            </>
          ) : (
            <>
              Entrar no Sistema
              <ChevronRight size={18} />
            </>
          )}
        </button>
      </form>

      <div className="flex items-center gap-3 my-6">
        <div className="flex-1 h-px" style={{ background: "#e2e8f0" }} />
        <span style={{ fontSize: "12px", color: "#94a3b8" }}>ou</span>
        <div className="flex-1 h-px" style={{ background: "#e2e8f0" }} />
      </div>

      <p style={{ fontSize: "14px", color: "#64748b", textAlign: "center" }}>
        Nao tem acesso?{" "}
        <button
          type="button"
          onClick={() => setCurrentPage("register")}
          style={{ color: "#123C7A", fontWeight: 700, background: "none", border: "none" }}
          className="hover:underline"
        >
          Solicitar cadastro
        </button>
      </p>

      <p style={{ fontSize: "13px", color: "#94a3b8", textAlign: "center", marginTop: "8px" }}>
        Primeiro acesso?{" "}
        <button
          type="button"
          onClick={() => setCurrentPage("first-access")}
          style={{ color: "#1F8A70", fontWeight: 600, background: "none", border: "none" }}
          className="hover:underline"
        >
          Configure sua conta aqui
        </button>
      </p>

      <div className="mt-8 rounded-xl p-3.5" style={{ background: "#f8fafc", border: "1px solid #e2e8f0" }}>
        <div className="flex items-start gap-2.5">
          <Shield size={13} style={{ color: "#94a3b8", flexShrink: 0, marginTop: 1 }} />
          <p style={{ fontSize: "11px", color: "#94a3b8", lineHeight: 1.5 }}>
            <strong style={{ color: "#64748b" }}>Aviso de seguranca:</strong> Este sistema e de uso exclusivo de membros vinculados ao programa.
            Acessos nao autorizados sao registrados.
          </p>
        </div>
      </div>
    </AuthLayout>
  );
}
