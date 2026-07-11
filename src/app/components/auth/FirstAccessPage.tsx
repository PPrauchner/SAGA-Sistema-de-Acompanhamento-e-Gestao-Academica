import { useState } from "react";
import { signInWithEmailAndPassword } from "firebase/auth";
import { useApp, UserRole } from "../../context/AppContext";
import { auth } from "@/lib/firebase";
import { activateFirstAccess } from "@/api/authApi";
import { AuthLayout } from "./AuthLayout";
import { PasswordStrength, calcPasswordStrength } from "./PasswordStrength";
import {
  Sparkles, User, Mail, Lock, Eye, EyeOff, CheckCircle2, AlertCircle,
  Loader2, GraduationCap, UserCheck, Shield, ChevronRight, ChevronLeft,
  Bell, Palette, Languages,
} from "lucide-react";

type Step = 1 | 2 | 3 | 4;
type FormState = "idle" | "loading" | "success";

const STEP_META: Record<Step, { icon: React.ReactNode; title: string; sub: string }> = {
  1: { icon: <User size={26} />, title: "Verificar Identidade", sub: "Confirme suas informações de acesso" },
  2: { icon: <Lock size={26} />, title: "Definir Senha", sub: "Crie uma senha forte e segura" },
  3: { icon: <Bell size={26} />, title: "Preferências", sub: "Configure como prefere ser notificado" },
  4: { icon: <Sparkles size={26} />, title: "Pronto!", sub: "Seu acesso foi configurado" },
};

const ROLES_META: Record<UserRole, { label: string; desc: string; icon: React.ReactNode; color: string; bg: string }> = {
  aluno: { label: "Aluno(a)", desc: "Visualize e atue como aluno do programa", icon: <GraduationCap size={14} />, color: "var(--brand-gold)", bg: "var(--tint-gold-bg)" },
  orientador: { label: "Orientador(a)", desc: "Acompanhe e oriente seus alunos", icon: <UserCheck size={14} />, color: "var(--brand-teal)", bg: "var(--tint-teal-bg)" },
  coordenacao: { label: "Coordenação", desc: "Administre o programa completo", icon: <Shield size={14} />, color: "var(--brand-blue)", bg: "var(--tint-blue-bg)" },
};

const NOTIF_OPTIONS = [
  { id: "email_atividades", label: "Atividades e Tarefas", desc: "Novos prazos, atualizações e pendências", default: true },
  { id: "email_producoes", label: "Produções Científicas", desc: "Aprovações e comentários nas produções", default: true },
  { id: "email_relatorios", label: "Relatórios Periódicos", desc: "Resumo semanal das atividades", default: false },
  { id: "email_sistema", label: "Comunicados do Sistema", desc: "Manutenções e novas funcionalidades", default: false },
];

const THEME_OPTIONS = [
  { id: "claro", label: "Claro", preview: ["#f0f4fa", "#fff", "#123C7A"] },
  { id: "escuro", label: "Escuro", preview: ["#0f1729", "#1a2540", "#2a5aad"] },
  { id: "auto", label: "Automático", preview: ["linear-gradient(135deg,#f0f4fa 50%,#0f1729 50%)", "#fff", "#123C7A"] },
];

export function FirstAccessPage() {
  const { setCurrentPage } = useApp();
  const [step, setStep] = useState<Step>(1);
  const [formState, setFormState] = useState<FormState>("idle");
  const [apiError, setApiError] = useState("");

  // Step 1 — identity. O papel NÃO é escolhido aqui: vem do convite e é
  // retornado por /first-access; o e-mail também vem da resposta da API.
  const [token, setToken] = useState("");
  const [role, setRole] = useState<UserRole>("aluno");
  const [activatedEmail, setActivatedEmail] = useState("");
  const [tokenError, setTokenError] = useState("");

  // Step 2 — password
  const [senha, setSenha] = useState("");
  const [confirmSenha, setConfirmSenha] = useState("");
  const [showSenha, setShowSenha] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [senhaError, setSenhaError] = useState("");

  // Step 3 — prefs
  const [notifs, setNotifs] = useState<Record<string, boolean>>(
    Object.fromEntries(NOTIF_OPTIONS.map((n) => [n.id, n.default]))
  );
  const [theme, setTheme] = useState("claro");
  const [language, setLanguage] = useState("pt-BR");

  const strength = calcPasswordStrength(senha);

  const next = async () => {
    if (step === 1) {
      if (token.trim().length < 4) { setTokenError("Informe o código de primeiro acesso enviado por e-mail."); return; }
      setTokenError("");
    }
    if (step === 2) {
      if (strength.score < 3) { setSenhaError("Escolha uma senha mais forte."); return; }
      if (senha !== confirmSenha) { setSenhaError("As senhas não coincidem."); return; }
      setSenhaError("");
    }
    if (step === 3) {
      // Ativa a conta no backend: cria o usuário no Firebase Auth e define os
      // custom claims a partir do convite. O papel real volta na resposta.
      setFormState("loading");
      setApiError("");
      try {
        const result = await activateFirstAccess(token, senha);
        setRole(result.role);
        setActivatedEmail(result.email);
        setFormState("idle");
        setStep(4);
      } catch (err) {
        setFormState("idle");
        setApiError(err instanceof Error ? err.message : "Falha ao ativar a conta.");
      }
      return;
    }
    setStep((s) => (s < 4 ? s + 1 : s) as Step);
  };

  const handleComplete = async () => {
    // Faz o primeiro login com a senha recém-definida; o AppContext redireciona
    // para a área do papel quando o perfil chega.
    setFormState("loading");
    setApiError("");
    try {
      await signInWithEmailAndPassword(auth, activatedEmail, senha);
    } catch {
      setFormState("idle");
      setApiError("Conta ativada, mas o login automático falhou. Faça login manualmente.");
    }
  };

  const { icon, title, sub } = STEP_META[step];
  const roleInfo = ROLES_META[role];

  return (
    <AuthLayout step={step <= 3 ? step : undefined} totalSteps={3}>
      {/* Icon + heading */}
      <div className="text-center mb-8">
        <div className="flex items-center justify-center mx-auto mb-5 rounded-2xl"
          style={{ width: 68, height: 68, background: "var(--tint-blue-bg)", border: "2px solid var(--tint-blue-border)", color: "var(--brand-blue)" }}>
          {icon}
        </div>
        <h2 style={{ fontSize: "24px", fontWeight: 800, color: "var(--foreground)", marginBottom: "4px", lineHeight: 1.2 }}>
          {step === 1 && "Bem-vindo(a) ao SAGA"}
          {step === 2 && title}
          {step === 3 && title}
          {step === 4 && "Configuração Concluída!"}
        </h2>
        <p style={{ fontSize: "14px", color: "var(--muted-foreground)", lineHeight: 1.5 }}>{sub}</p>
      </div>

      {/* ── STEP 1 — Identity ── */}
      {step === 1 && (
        <div className="space-y-5">
          {/* Access token */}
          <div>
            <label htmlFor="token"
              style={{ fontSize: "13px", fontWeight: 600, color: "var(--foreground)", display: "block", marginBottom: "6px" }}>
              Código de Primeiro Acesso <span style={{ color: "var(--destructive)" }}>*</span>
            </label>
            <input
              id="token"
              type="text"
              value={token}
              onChange={(e) => { setToken(e.target.value); setTokenError(""); }}
              placeholder="Cole o token recebido por e-mail"
              className="w-full rounded-xl px-4 py-3 outline-none transition-all"
              style={{
                border: `2px solid ${tokenError ? "var(--destructive)" : "var(--border)"}`,
                background: "var(--input-background)",
                fontSize: "14px",
                color: "var(--foreground)",
                fontWeight: 600,
              }}
              onFocus={(e) => { e.currentTarget.style.borderColor = tokenError ? "var(--destructive)" : "var(--ring)"; e.currentTarget.style.background = "var(--card)"; }}
              onBlur={(e) => { e.currentTarget.style.borderColor = tokenError ? "var(--destructive)" : "var(--border)"; e.currentTarget.style.background = "var(--input-background)"; }}
            />
            {tokenError && (
              <div className="flex items-center gap-1.5 mt-1.5">
                <AlertCircle size={13} style={{ color: "var(--destructive)", flexShrink: 0 }} />
                <p style={{ fontSize: "12px", color: "var(--destructive)" }}>{tokenError}</p>
              </div>
            )}
            <p style={{ fontSize: "11px", color: "var(--muted-foreground)", marginTop: "6px" }}>
              O código foi enviado pela coordenação ao e-mail institucional cadastrado.
            </p>
          </div>

          <button onClick={next}
            className="w-full rounded-xl py-3.5 flex items-center justify-center gap-2.5 transition-all"
            style={{
              background: "linear-gradient(135deg,#0d2d5e,#123C7A)",
              color: "#fff",
              fontWeight: 700,
              fontSize: "15px",
              boxShadow: "0 4px 14px rgba(18,60,122,0.3)",
            }}>
            Confirmar e Continuar <ChevronRight size={18} />
          </button>
        </div>
      )}

      {/* ── STEP 2 — Password ── */}
      {step === 2 && (
        <div className="space-y-5">
          <div>
            <label htmlFor="fs-senha"
              style={{ fontSize: "13px", fontWeight: 600, color: "var(--foreground)", display: "block", marginBottom: "6px" }}>
              Nova Senha <span style={{ color: "var(--destructive)" }}>*</span>
            </label>
            <div className="relative">
              <Lock size={15} className="absolute top-1/2 -translate-y-1/2 left-3.5"
                style={{ color: "var(--muted-foreground)", pointerEvents: "none" }} />
              <input
                id="fs-senha"
                type={showSenha ? "text" : "password"}
                value={senha}
                onChange={(e) => { setSenha(e.target.value); setSenhaError(""); }}
                placeholder="Crie uma senha forte"
                autoComplete="new-password"
                className="w-full rounded-xl pl-10 pr-12 py-3 outline-none transition-all"
                style={{ border: `2px solid ${senhaError ? "var(--destructive)" : "var(--border)"}`, background: "var(--input-background)", fontSize: "14px", color: "var(--foreground)" }}
                onFocus={(e) => { e.currentTarget.style.borderColor = senhaError ? "var(--destructive)" : "var(--ring)"; e.currentTarget.style.background = "var(--card)"; }}
                onBlur={(e) => { e.currentTarget.style.borderColor = senhaError ? "var(--destructive)" : "var(--border)"; e.currentTarget.style.background = "var(--input-background)"; }}
              />
              <button type="button" onClick={() => setShowSenha(!showSenha)}
                className="absolute top-1/2 -translate-y-1/2 right-3.5"
                style={{ color: "var(--muted-foreground)", background: "none", border: "none" }}>
                {showSenha ? <EyeOff size={17} /> : <Eye size={17} />}
              </button>
            </div>
            <PasswordStrength password={senha} />
          </div>

          <div>
            <label htmlFor="fs-confirm"
              style={{ fontSize: "13px", fontWeight: 600, color: "var(--foreground)", display: "block", marginBottom: "6px" }}>
              Confirmar Senha <span style={{ color: "var(--destructive)" }}>*</span>
            </label>
            <div className="relative">
              <Lock size={15} className="absolute top-1/2 -translate-y-1/2 left-3.5"
                style={{ color: "var(--muted-foreground)", pointerEvents: "none" }} />
              <input
                id="fs-confirm"
                type={showConfirm ? "text" : "password"}
                value={confirmSenha}
                onChange={(e) => { setConfirmSenha(e.target.value); setSenhaError(""); }}
                placeholder="Repita a senha"
                autoComplete="new-password"
                className="w-full rounded-xl pl-10 pr-12 py-3 outline-none transition-all"
                style={{
                  border: `2px solid ${confirmSenha && senha === confirmSenha ? "var(--status-active)" : confirmSenha && senha !== confirmSenha ? "var(--destructive)" : "var(--border)"}`,
                  background: "var(--input-background)", fontSize: "14px", color: "var(--foreground)",
                }}
                onFocus={(e) => { e.currentTarget.style.borderColor = "var(--ring)"; e.currentTarget.style.background = "var(--card)"; }}
                onBlur={(e) => {
                  e.currentTarget.style.borderColor = confirmSenha && senha === confirmSenha ? "var(--status-active)" : confirmSenha && senha !== confirmSenha ? "var(--destructive)" : "var(--border)";
                  e.currentTarget.style.background = "var(--input-background)";
                }}
              />
              <button type="button" onClick={() => setShowConfirm(!showConfirm)}
                className="absolute top-1/2 -translate-y-1/2 right-3.5"
                style={{ color: "var(--muted-foreground)", background: "none", border: "none" }}>
                {showConfirm ? <EyeOff size={17} /> : <Eye size={17} />}
              </button>
            </div>
            {confirmSenha && (
              <div className="flex items-center gap-1.5 mt-1.5">
                {senha === confirmSenha
                  ? <><CheckCircle2 size={13} style={{ color: "var(--tint-teal-text)" }} /><span style={{ fontSize: "12px", color: "var(--tint-teal-text)", fontWeight: 600 }}>As senhas coincidem</span></>
                  : <><AlertCircle size={13} style={{ color: "var(--destructive)" }} /><span style={{ fontSize: "12px", color: "var(--destructive)" }}>As senhas não coincidem</span></>}
              </div>
            )}
          </div>

          {senhaError && (
            <div className="flex items-start gap-2 rounded-xl p-3"
              style={{ background: "var(--tint-danger-bg)", border: "1px solid var(--tint-danger-border)" }}>
              <AlertCircle size={14} style={{ color: "var(--tint-danger-text)", flexShrink: 0, marginTop: 1 }} />
              <p style={{ fontSize: "13px", color: "var(--tint-danger-text)" }}>{senhaError}</p>
            </div>
          )}

          <div className="flex gap-3">
            <button onClick={() => setStep(1)}
              className="flex items-center gap-2 rounded-xl px-5 py-3"
              style={{ background: "var(--muted)", color: "var(--foreground)", fontWeight: 600, fontSize: "14px", border: "2px solid var(--border)" }}>
              <ChevronLeft size={16} /> Voltar
            </button>
            <button onClick={next}
              className="flex-1 rounded-xl py-3 flex items-center justify-center gap-2.5"
              style={{ background: "linear-gradient(135deg,#0d2d5e,#123C7A)", color: "#fff", fontWeight: 700, fontSize: "14px" }}>
              Continuar <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}

      {/* ── STEP 3 — Preferences ── */}
      {step === 3 && (
        <div className="space-y-5">
          {/* Theme */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Palette size={14} style={{ color: "var(--brand-blue)" }} />
              <p style={{ fontSize: "12px", fontWeight: 700, color: "var(--foreground)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                Tema da Interface
              </p>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {THEME_OPTIONS.map((opt) => (
                <button key={opt.id} type="button" onClick={() => setTheme(opt.id)}
                  className="rounded-xl p-2.5 border-2 transition-all"
                  style={{ borderColor: theme === opt.id ? "var(--brand-blue)" : "var(--border)", background: theme === opt.id ? "var(--tint-blue-bg)" : "var(--input-background)" }}>
                  <div className="rounded-lg mb-2 overflow-hidden" style={{ height: 36, background: opt.preview[0] }}>
                    <div className="flex h-full">
                      <div style={{ width: 20, background: opt.preview[2] }} />
                      <div className="flex-1 p-1.5">
                        <div className="rounded h-1.5 mb-1" style={{ background: opt.preview[1], width: "75%", opacity: 0.8 }} />
                        <div className="rounded h-1.5" style={{ background: opt.preview[1], width: "55%", opacity: 0.5 }} />
                      </div>
                    </div>
                  </div>
                  <p style={{ fontSize: "11px", fontWeight: 600, color: theme === opt.id ? "var(--brand-blue)" : "var(--muted-foreground)", textAlign: "center" }}>
                    {opt.label}
                  </p>
                </button>
              ))}
            </div>
          </div>

          {/* Language */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Languages size={14} style={{ color: "var(--brand-blue)" }} />
              <p style={{ fontSize: "12px", fontWeight: 700, color: "var(--foreground)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                Idioma
              </p>
            </div>
            <select value={language} onChange={(e) => setLanguage(e.target.value)}
              className="w-full rounded-xl px-4 py-2.5 outline-none"
              style={{ border: "2px solid var(--border)", background: "var(--input-background)", fontSize: "13px", color: "var(--foreground)" }}
              onFocus={(e) => { e.currentTarget.style.borderColor = "var(--ring)"; }}
              onBlur={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }}>
              <option value="pt-BR">🇧🇷 Português (Brasil)</option>
              <option value="en-US">🇺🇸 English (US)</option>
              <option value="es">🇪🇸 Español</option>
            </select>
          </div>

          {/* Notifications */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Bell size={14} style={{ color: "var(--brand-blue)" }} />
              <p style={{ fontSize: "12px", fontWeight: 700, color: "var(--foreground)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                Notificações por E-mail
              </p>
            </div>
            <div className="space-y-2">
              {NOTIF_OPTIONS.map((opt) => (
                <label key={opt.id}
                  className="flex items-center justify-between rounded-xl p-3 cursor-pointer transition-colors"
                  style={{ background: notifs[opt.id] ? "var(--tint-blue-bg)" : "var(--input-background)", border: `1px solid ${notifs[opt.id] ? "var(--tint-blue-border)" : "var(--border)"}` }}>
                  <div>
                    <p style={{ fontSize: "13px", fontWeight: 600, color: notifs[opt.id] ? "var(--brand-blue)" : "var(--foreground)" }}>{opt.label}</p>
                    <p style={{ fontSize: "11px", color: "var(--muted-foreground)" }}>{opt.desc}</p>
                  </div>
                  <button type="button"
                    onClick={() => setNotifs((prev) => ({ ...prev, [opt.id]: !prev[opt.id] }))}
                    className="relative flex-shrink-0 rounded-full transition-all"
                    style={{
                      width: 42, height: 24,
                      background: notifs[opt.id] ? "var(--brand-blue)" : "var(--switch-background)",
                      marginLeft: 12,
                    }}
                    role="switch"
                    aria-checked={notifs[opt.id]}>
                    <div className="absolute top-1 rounded-full transition-all"
                      style={{
                        width: 16, height: 16, background: "#fff",
                        left: notifs[opt.id] ? 22 : 4,
                        boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
                      }} />
                  </button>
                </label>
              ))}
            </div>
          </div>

          {apiError && (
            <div className="flex items-start gap-2 rounded-xl p-3"
              style={{ background: "var(--tint-danger-bg)", border: "1px solid var(--tint-danger-border)" }}>
              <AlertCircle size={14} style={{ color: "var(--tint-danger-text)", flexShrink: 0, marginTop: 1 }} />
              <p style={{ fontSize: "13px", color: "var(--tint-danger-text)" }}>{apiError}</p>
            </div>
          )}

          <div className="flex gap-3">
            <button onClick={() => setStep(2)}
              className="flex items-center gap-2 rounded-xl px-5 py-3"
              style={{ background: "var(--muted)", color: "var(--foreground)", fontWeight: 600, fontSize: "14px", border: "2px solid var(--border)" }}>
              <ChevronLeft size={16} /> Voltar
            </button>
            <button onClick={next} disabled={formState === "loading"}
              className="flex-1 rounded-xl py-3 flex items-center justify-center gap-2.5"
              style={{ background: "linear-gradient(135deg,#0d2d5e,#123C7A)", color: "#fff", fontWeight: 700, fontSize: "14px" }}>
              {formState === "loading"
                ? <><Loader2 size={16} className="animate-spin" /> Ativando conta…</>
                : <>Finalizar Configuração <ChevronRight size={16} /></>}
            </button>
          </div>
        </div>
      )}

      {/* ── STEP 4 — Done ── */}
      {step === 4 && (
        <div className="text-center">
          <div className="flex items-center justify-center mx-auto mb-6 rounded-full"
            style={{ width: 88, height: 88, background: "var(--tint-teal-bg)", border: "3px solid var(--tint-teal-border)" }}>
            <CheckCircle2 size={44} style={{ color: "var(--tint-teal-text)" }} />
          </div>

          <div className="mb-8 space-y-3">
            {[
              { icon: "✅", label: "Identidade verificada" },
              { icon: "🔐", label: "Senha criada com sucesso" },
              { icon: "🔔", label: "Preferências salvas" },
              { icon: "🎓", label: "Perfil configurado como " + roleInfo.label },
            ].map((item) => (
              <div key={item.label}
                className="flex items-center gap-3 rounded-xl px-4 py-2.5"
                style={{ background: "var(--tint-teal-bg)", border: "1px solid var(--tint-teal-border)" }}>
                <span style={{ fontSize: "16px" }}>{item.icon}</span>
                <p style={{ fontSize: "13px", color: "var(--tint-teal-text)", fontWeight: 600 }}>{item.label}</p>
              </div>
            ))}
          </div>

          <div className="rounded-2xl p-4 mb-8"
            style={{ background: "var(--tint-blue-bg)", border: "1px solid var(--tint-blue-border)" }}>
            <p style={{ fontSize: "12px", color: "var(--foreground)", lineHeight: 1.6 }}>
              Bem-vindo(a) ao <strong style={{ color: "var(--brand-blue)" }}>SAGA</strong>!
              Sua conta foi configurada como <strong style={{ color: roleInfo.color }}>{roleInfo.label}</strong>.
              Você já pode acessar todas as funcionalidades disponíveis para o seu perfil.
            </p>
          </div>

          {apiError && (
            <div className="flex items-start gap-2 rounded-xl p-3 mb-4 text-left"
              style={{ background: "var(--tint-danger-bg)", border: "1px solid var(--tint-danger-border)" }}>
              <AlertCircle size={14} style={{ color: "var(--tint-danger-text)", flexShrink: 0, marginTop: 1 }} />
              <p style={{ fontSize: "13px", color: "var(--tint-danger-text)" }}>{apiError}</p>
            </div>
          )}

          <button
            onClick={handleComplete}
            disabled={formState === "loading"}
            className="w-full rounded-xl py-3.5 flex items-center justify-center gap-2.5 transition-all"
            style={{
              background: "linear-gradient(135deg,#145a32,#1F8A70)",
              color: "#fff",
              fontWeight: 700,
              fontSize: "15px",
              boxShadow: "0 4px 14px rgba(31,138,112,0.35)",
            }}>
            {formState === "loading"
              ? <><Loader2 size={18} className="animate-spin" /> Entrando…</>
              : <><Sparkles size={18} /> Acessar o Sistema</>}
          </button>
        </div>
      )}

      {step <= 3 && (
        <p style={{ fontSize: "13px", color: "var(--muted-foreground)", textAlign: "center", marginTop: "20px" }}>
          <button type="button" onClick={() => setCurrentPage("login")}
            style={{ color: "var(--brand-blue)", fontWeight: 700, background: "none", border: "none" }}
            className="hover:underline">
            ← Voltar ao Login
          </button>
        </p>
      )}
    </AuthLayout>
  );
}
