import { useState } from "react";
import { useApp, DEMO_USERS, UserRole } from "../../context/AppContext";
import { AuthLayout } from "./AuthLayout";
import {
  Eye, EyeOff, Mail, Lock, AlertCircle, CheckCircle2,
  GraduationCap, UserCheck, Shield, ChevronRight, Loader2,
} from "lucide-react";

interface RoleOption {
  value: UserRole;
  label: string;
  desc: string;
  color: string;
  bg: string;
  icon: React.ReactNode;
}

const ROLES: RoleOption[] = [
  { value: "coordenacao", label: "Coordenação", desc: "Gestão total do programa", color: "#123C7A", bg: "#eef3fc", icon: <Shield size={15} /> },
  { value: "orientador", label: "Orientador(a)", desc: "Acompanhar orientandos", color: "#1F8A70", bg: "#dcfce7", icon: <UserCheck size={15} /> },
  { value: "aluno", label: "Aluno(a)", desc: "Meu progresso acadêmico", color: "#D4A017", bg: "#fef9c3", icon: <GraduationCap size={15} /> },
];

const FIELD_DEFAULTS: Record<UserRole, { email: string }> = {
  coordenacao: { email: "roberto.almeida@ppg.ufx.br" },
  orientador: { email: "carla.mendes@ppg.ufx.br" },
  aluno: { email: "lucas.silva@pos.ufx.br" },
};

type FormState = "idle" | "loading" | "success" | "error";

export function LoginPage() {
  const { setCurrentUser, setCurrentPage } = useApp();
  const [role, setRole] = useState<UserRole>("coordenacao");
  const [email, setEmail] = useState(FIELD_DEFAULTS.coordenacao.email);
  const [password, setPassword] = useState("senha123");
  const [showPw, setShowPw] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [formState, setFormState] = useState<FormState>("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const handleRoleChange = (r: UserRole) => {
    setRole(r);
    setEmail(FIELD_DEFAULTS[r].email);
    setErrorMsg("");
  };

  const validate = () => {
    if (!email.trim()) return "Informe o e-mail institucional.";
    if (!/\S+@\S+\.\S+/.test(email)) return "E-mail inválido.";
    if (!password) return "Informe a senha.";
    if (password.length < 6) return "Senha deve ter pelo menos 6 caracteres.";
    return "";
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const err = validate();
    if (err) { setErrorMsg(err); return; }
    setErrorMsg("");
    setFormState("loading");
    await new Promise((r) => setTimeout(r, 1200));
    setFormState("success");
    await new Promise((r) => setTimeout(r, 600));
    setCurrentUser(DEMO_USERS[role]);
    setCurrentPage("dashboard");
  };

  const isLoading = formState === "loading";
  const isSuccess = formState === "success";

  return (
    <AuthLayout>
      {/* Heading */}
      <div className="mb-8">
        <h2 style={{ fontSize: "26px", fontWeight: 800, color: "#0f172a", lineHeight: 1.2, marginBottom: "6px" }}>
          Acesse sua conta
        </h2>
        <p style={{ fontSize: "14px", color: "#64748b", lineHeight: 1.5 }}>
          Entre com suas credenciais institucionais para continuar.
        </p>
      </div>

      {/* Role selector */}
      <div className="mb-6">
        <label style={{ fontSize: "11px", fontWeight: 700, color: "#64748b",
          textTransform: "uppercase", letterSpacing: "0.07em", display: "block", marginBottom: "10px" }}>
          Tipo de Acesso
        </label>
        <div className="grid grid-cols-3 gap-2">
          {ROLES.map((opt) => {
            const active = role === opt.value;
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => handleRoleChange(opt.value)}
                className="rounded-2xl p-3 text-left transition-all duration-200"
                style={{
                  background: active ? opt.bg : "#f8fafc",
                  border: `2px solid ${active ? opt.color : "#e2e8f0"}`,
                  boxShadow: active ? `0 4px 12px ${opt.color}20` : "none",
                  transform: active ? "translateY(-1px)" : "none",
                }}
              >
                <span style={{ color: active ? opt.color : "#94a3b8", display: "block", marginBottom: "5px" }}>
                  {opt.icon}
                </span>
                <p style={{ fontSize: "12px", fontWeight: 700,
                  color: active ? opt.color : "#374151", lineHeight: 1.2, marginBottom: "2px" }}>
                  {opt.label}
                </p>
                <p style={{ fontSize: "10px", color: active ? opt.color : "#94a3b8", lineHeight: 1.3 }}>
                  {opt.desc}
                </p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} noValidate>
        {/* Email */}
        <div className="mb-4">
          <label htmlFor="email"
            style={{ fontSize: "13px", fontWeight: 600, color: "#374151", display: "block", marginBottom: "6px" }}>
            E-mail Institucional
          </label>
          <div className="relative">
            <Mail size={15} className="absolute top-1/2 -translate-y-1/2 left-3.5"
              style={{ color: "#94a3b8", pointerEvents: "none" }} />
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => { setEmail(e.target.value); setErrorMsg(""); }}
              placeholder="seu.nome@ppg.ufx.br"
              autoComplete="email"
              disabled={isLoading || isSuccess}
              className="w-full rounded-xl pl-10 pr-4 py-3 outline-none transition-all duration-150"
              style={{
                border: errorMsg && !password ? "2px solid #ef4444" : "2px solid #e2e8f0",
                background: "#f8fafc",
                fontSize: "14px",
                color: "#0f172a",
              }}
              onFocus={(e) => { e.currentTarget.style.borderColor = "#123C7A"; e.currentTarget.style.background = "#fff"; }}
              onBlur={(e) => { e.currentTarget.style.borderColor = "#e2e8f0"; e.currentTarget.style.background = "#f8fafc"; }}
            />
          </div>
        </div>

        {/* Password */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-1.5">
            <label htmlFor="password"
              style={{ fontSize: "13px", fontWeight: 600, color: "#374151" }}>
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
            <Lock size={15} className="absolute top-1/2 -translate-y-1/2 left-3.5"
              style={{ color: "#94a3b8", pointerEvents: "none" }} />
            <input
              id="password"
              type={showPw ? "text" : "password"}
              value={password}
              onChange={(e) => { setPassword(e.target.value); setErrorMsg(""); }}
              placeholder="••••••••"
              autoComplete="current-password"
              disabled={isLoading || isSuccess}
              className="w-full rounded-xl pl-10 pr-12 py-3 outline-none transition-all duration-150"
              style={{
                border: "2px solid #e2e8f0",
                background: "#f8fafc",
                fontSize: "14px",
                color: "#0f172a",
              }}
              onFocus={(e) => { e.currentTarget.style.borderColor = "#123C7A"; e.currentTarget.style.background = "#fff"; }}
              onBlur={(e) => { e.currentTarget.style.borderColor = "#e2e8f0"; e.currentTarget.style.background = "#f8fafc"; }}
            />
            <button
              type="button"
              onClick={() => setShowPw(!showPw)}
              className="absolute top-1/2 -translate-y-1/2 right-3.5 p-1 rounded transition-colors"
              style={{ color: "#94a3b8" }}
              aria-label={showPw ? "Ocultar senha" : "Mostrar senha"}
              onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.color = "#123C7A"; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.color = "#94a3b8"; }}
            >
              {showPw ? <EyeOff size={17} /> : <Eye size={17} />}
            </button>
          </div>
        </div>

        {/* Remember me */}
        <div className="flex items-center gap-2.5 mb-5">
          <button
            type="button"
            onClick={() => setRememberMe(!rememberMe)}
            className="flex items-center justify-center rounded-md flex-shrink-0 transition-all"
            style={{
              width: 18, height: 18,
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

        {/* Error */}
        {errorMsg && (
          <div className="flex items-start gap-2.5 rounded-xl p-3 mb-4"
            style={{ background: "#fef2f2", border: "1px solid #fecaca" }}>
            <AlertCircle size={15} style={{ color: "#dc2626", flexShrink: 0, marginTop: 1 }} />
            <p style={{ fontSize: "13px", color: "#dc2626", lineHeight: 1.4 }}>{errorMsg}</p>
          </div>
        )}

        {/* Success state */}
        {isSuccess && (
          <div className="flex items-center gap-2.5 rounded-xl p-3 mb-4"
            style={{ background: "#f0fdf4", border: "1px solid #bbf7d0" }}>
            <CheckCircle2 size={16} style={{ color: "#16a34a", flexShrink: 0 }} />
            <p style={{ fontSize: "13px", color: "#16a34a", fontWeight: 600 }}>Autenticado! Redirecionando…</p>
          </div>
        )}

        {/* Submit button */}
        <button
          type="submit"
          disabled={isLoading || isSuccess}
          className="w-full rounded-xl py-3.5 flex items-center justify-center gap-2.5 transition-all duration-200"
          style={{
            background: isSuccess
              ? "linear-gradient(135deg,#1F8A70,#16a34a)"
              : isLoading
              ? "#93a7c0"
              : "linear-gradient(135deg,#0d2d5e,#123C7A)",
            color: "#fff",
            fontSize: "15px",
            fontWeight: 700,
            boxShadow: isLoading || isSuccess ? "none" : "0 4px 16px rgba(18,60,122,0.35)",
            cursor: isLoading || isSuccess ? "not-allowed" : "pointer",
          }}
          onMouseEnter={(e) => {
            if (!isLoading && !isSuccess) {
              (e.currentTarget as HTMLElement).style.boxShadow = "0 6px 22px rgba(18,60,122,0.45)";
              (e.currentTarget as HTMLElement).style.transform = "translateY(-1px)";
            }
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLElement).style.boxShadow = "0 4px 16px rgba(18,60,122,0.35)";
            (e.currentTarget as HTMLElement).style.transform = "none";
          }}
        >
          {isLoading ? (
            <>
              <Loader2 size={18} className="animate-spin" />
              Verificando credenciais…
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

      {/* Divider */}
      <div className="flex items-center gap-3 my-6">
        <div className="flex-1 h-px" style={{ background: "#e2e8f0" }} />
        <span style={{ fontSize: "12px", color: "#94a3b8" }}>ou</span>
        <div className="flex-1 h-px" style={{ background: "#e2e8f0" }} />
      </div>

      {/* Register link */}
      <p style={{ fontSize: "14px", color: "#64748b", textAlign: "center" }}>
        Não tem acesso?{" "}
        <button
          type="button"
          onClick={() => setCurrentPage("register")}
          style={{ color: "#123C7A", fontWeight: 700, background: "none", border: "none" }}
          className="hover:underline"
        >
          Solicitar cadastro
        </button>
      </p>

      {/* First access */}
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

      {/* Security notice */}
      <div className="mt-8 rounded-xl p-3.5"
        style={{ background: "#f8fafc", border: "1px solid #e2e8f0" }}>
        <div className="flex items-start gap-2.5">
          <Shield size={13} style={{ color: "#94a3b8", flexShrink: 0, marginTop: 1 }} />
          <p style={{ fontSize: "11px", color: "#94a3b8", lineHeight: 1.5 }}>
            <strong style={{ color: "#64748b" }}>Aviso de segurança:</strong> Este sistema é de uso exclusivo
            de membros vinculados ao programa. Acessos não autorizados são registrados e podem resultar
            em medidas disciplinares.
          </p>
        </div>
      </div>
    </AuthLayout>
  );
}
