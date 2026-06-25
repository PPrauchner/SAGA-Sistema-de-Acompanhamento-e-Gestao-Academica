import { useState } from "react";
import { useApp, UserRole } from "../../context/AppContext";
import { AuthLayout } from "./AuthLayout";
import {
  User, Mail, GraduationCap, UserCheck, Shield,
  CheckCircle2, ChevronRight, ChevronLeft, Loader2, Upload, Phone, AlertCircle,
} from "lucide-react";

type Step = 1 | 2 | 3;
type FormState = "idle" | "loading" | "success" | "error";

interface FormData {
  nome: string;
  email: string;
  cpf: string;
  telefone: string;
  role: UserRole;
  matricula: string;
  programa: string;
  nivel: string;
  orientador: string;
  termos: boolean;
}

const ROLES = [
  { value: "aluno" as UserRole, label: "Aluno(a)", desc: "Mestrando ou doutorando matriculado", icon: <GraduationCap size={16} />, color: "#D4A017", bg: "#fef9c3" },
  { value: "orientador" as UserRole, label: "Orientador(a)", desc: "Docente com orientandos no programa", icon: <UserCheck size={16} />, color: "#1F8A70", bg: "#dcfce7" },
  { value: "coordenacao" as UserRole, label: "Coordenação", desc: "Gestão e administração do programa", icon: <Shield size={16} />, color: "#123C7A", bg: "#eef3fc" },
];

const PROGRAMAS = [
  "PPGCC — Ciência da Computação",
  "PPGEI — Engenharia de Informação",
  "PPGMAT — Matemática",
  "PPGFIS — Física",
  "PPGBIO — Biotecnologia",
];

const STEP_TITLES: Record<Step, { title: string; sub: string }> = {
  1: { title: "Dados Pessoais", sub: "Informações de identificação" },
  2: { title: "Vínculo Acadêmico", sub: "Seu papel no programa" },
  3: { title: "Confirmação", sub: "Documentação e aceite dos termos" },
};

function FieldInput({
  label, id, type = "text", value, onChange, placeholder, icon, required, disabled,
}: {
  label: string; id: string; type?: string; value: string; onChange: (v: string) => void;
  placeholder?: string; icon?: React.ReactNode; required?: boolean; disabled?: boolean;
}) {
  return (
    <div>
      <label htmlFor={id} style={{ fontSize: "12px", fontWeight: 600, color: "#374151", display: "block", marginBottom: "5px" }}>
        {label} {required && <span style={{ color: "#ef4444" }}>*</span>}
      </label>
      <div className="relative">
        {icon && (
          <span className="absolute top-1/2 -translate-y-1/2 left-3.5" style={{ color: "#94a3b8", pointerEvents: "none" }}>
            {icon}
          </span>
        )}
        <input
          id={id}
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          className="w-full rounded-xl py-2.5 outline-none transition-all"
          style={{
            border: "2px solid #e2e8f0",
            background: "#f8fafc",
            fontSize: "13px",
            color: "#0f172a",
            paddingLeft: icon ? "38px" : "14px",
            paddingRight: "14px",
          }}
          onFocus={(e) => { e.currentTarget.style.borderColor = "#123C7A"; e.currentTarget.style.background = "#fff"; }}
          onBlur={(e) => { e.currentTarget.style.borderColor = "#e2e8f0"; e.currentTarget.style.background = "#f8fafc"; }}
        />
      </div>
    </div>
  );
}

export function RegisterPage() {
  const { setCurrentPage } = useApp();
  const [step, setStep] = useState<Step>(1);
  const [formState, setFormState] = useState<FormState>("idle");
  const [errors, setErrors] = useState<Partial<Record<keyof FormData, string>>>({});

  const [form, setForm] = useState<FormData>({
    nome: "", email: "", cpf: "", telefone: "",
    role: "aluno", matricula: "", programa: "", nivel: "mestrado", orientador: "",
    termos: false,
  });

  const set = (key: keyof FormData) => (value: string | boolean) =>
    setForm((f) => ({ ...f, [key]: value }));

  const validateStep = (s: Step): boolean => {
    const errs: typeof errors = {};
    if (s === 1) {
      if (!form.nome.trim()) errs.nome = "Nome obrigatório";
      if (!form.email.trim() || !/\S+@\S+\.\S+/.test(form.email)) errs.email = "E-mail inválido";
      if (!form.cpf.trim()) errs.cpf = "CPF obrigatório";
    }
    if (s === 2) {
      if (!form.programa) errs.programa = "Selecione o programa";
      if (form.role === "aluno" && !form.matricula) errs.matricula = "Matrícula obrigatória";
    }
    if (s === 3) {
      if (!form.termos) errs.termos = "Aceite os termos para continuar";
    }
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const next = () => {
    if (validateStep(step)) setStep((s) => Math.min(s + 1, 3) as Step);
  };

  const back = () => setStep((s) => Math.max(s - 1, 1) as Step);

  const [hasFile, setHasFile] = useState(false);
  const [fileName, setFileName] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateStep(3)) return;
    setFormState("loading");
    await new Promise((r) => setTimeout(r, 1400));
    setFormState("success");
  };

  if (formState === "success") {
    return (
      <AuthLayout>
        <div className="text-center py-8">
          <div className="flex items-center justify-center mx-auto mb-6 rounded-full"
            style={{ width: 80, height: 80, background: "#dcfce7", border: "3px solid #bbf7d0" }}>
            <CheckCircle2 size={40} style={{ color: "#16a34a" }} />
          </div>
          <h2 style={{ fontSize: "24px", fontWeight: 800, color: "#0f172a", marginBottom: "12px" }}>
            Solicitação Enviada!
          </h2>
          <p style={{ fontSize: "14px", color: "#64748b", lineHeight: 1.65, marginBottom: "8px" }}>
            Sua solicitação de cadastro foi registrada com sucesso.
          </p>
          <p style={{ fontSize: "14px", color: "#64748b", lineHeight: 1.65, marginBottom: "16px" }}>
            A <strong style={{ color: "#123C7A" }}>coordenação do programa</strong> irá analisar
            e confirmar seu acesso em até <strong>2 dias úteis</strong>. Você receberá um
            e-mail de confirmação em <strong>{form.email || "seu e-mail"}</strong>.
          </p>
          <p style={{ fontSize: "13px", color: "#64748b", lineHeight: 1.65, marginBottom: "28px" }}>
            Após aprovação, você receberá um <strong style={{ color: "#123C7A" }}>código de primeiro acesso</strong> para criar sua senha e ativar a conta.
          </p>
          <div className="rounded-2xl p-4 mb-8" style={{ background: "#f0f9ff", border: "1px solid #bae6fd" }}>
            <p style={{ fontSize: "12px", color: "#0284c7", lineHeight: 1.5 }}>
              📧 Caso não receba o e-mail em 2 dias úteis, entre em contato com a secretaria
              do programa pelo e-mail <strong>ppgcc@ufx.br</strong>
            </p>
          </div>
          <button
            onClick={() => setCurrentPage("login")}
            className="w-full rounded-xl py-3.5"
            style={{ background: "linear-gradient(135deg,#0d2d5e,#123C7A)", color: "#fff", fontWeight: 700, fontSize: "15px" }}
          >
            Voltar ao Login
          </button>
        </div>
      </AuthLayout>
    );
  }

  const { title, sub } = STEP_TITLES[step];
  const activeRole = ROLES.find((r) => r.value === form.role)!;

  return (
    <AuthLayout step={step} totalSteps={3}>
      <div className="mb-7">
        <h2 style={{ fontSize: "24px", fontWeight: 800, color: "#0f172a", lineHeight: 1.2, marginBottom: "4px" }}>
          {title}
        </h2>
        <p style={{ fontSize: "14px", color: "#64748b" }}>{sub}</p>
      </div>

      <form onSubmit={step < 3 ? (e) => { e.preventDefault(); next(); } : handleSubmit} noValidate>

        {/* ── STEP 1 ── */}
        {step === 1 && (
          <div className="space-y-4">
            <FieldInput label="Nome Completo" id="nome" value={form.nome} onChange={set("nome")}
              placeholder="Seu nome completo" icon={<User size={14} />} required />
            {errors.nome && <p style={{ fontSize: "11px", color: "#ef4444", marginTop: "-8px" }}>{errors.nome}</p>}

            <FieldInput label="E-mail Institucional" id="email" type="email" value={form.email}
              onChange={set("email")} placeholder="seu.nome@ppg.ufx.br" icon={<Mail size={14} />} required />
            {errors.email && <p style={{ fontSize: "11px", color: "#ef4444", marginTop: "-8px" }}>{errors.email}</p>}

            <div className="grid grid-cols-2 gap-3">
              <div>
                <FieldInput label="CPF" id="cpf" value={form.cpf} onChange={set("cpf")}
                  placeholder="000.000.000-00" required />
                {errors.cpf && <p style={{ fontSize: "11px", color: "#ef4444", marginTop: "2px" }}>{errors.cpf}</p>}
              </div>
              <FieldInput label="Telefone" id="telefone" value={form.telefone} onChange={set("telefone")}
                placeholder="(11) 99999-0000" icon={<Phone size={14} />} />
            </div>
          </div>
        )}

        {/* ── STEP 2 ── */}
        {step === 2 && (
          <div className="space-y-4">
            {/* Role picker */}
            <div>
              <p style={{ fontSize: "12px", fontWeight: 600, color: "#374151", marginBottom: "8px" }}>
                Tipo de Vínculo <span style={{ color: "#ef4444" }}>*</span>
              </p>
              <div className="space-y-2">
                {ROLES.map((opt) => {
                  const active = form.role === opt.value;
                  return (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => set("role")(opt.value)}
                      className="w-full flex items-center gap-3 rounded-xl p-3 text-left transition-all"
                      style={{
                        background: active ? opt.bg : "#f8fafc",
                        border: `2px solid ${active ? opt.color : "#e2e8f0"}`,
                      }}
                    >
                      <div className="rounded-lg flex items-center justify-center flex-shrink-0"
                        style={{ width: 34, height: 34, background: active ? opt.color : "#f1f5f9",
                          color: active ? "#fff" : "#94a3b8" }}>
                        {opt.icon}
                      </div>
                      <div className="flex-1">
                        <p style={{ fontSize: "13px", fontWeight: 700,
                          color: active ? opt.color : "#374151" }}>{opt.label}</p>
                        <p style={{ fontSize: "11px", color: active ? opt.color : "#94a3b8" }}>{opt.desc}</p>
                      </div>
                      {active && (
                        <div className="rounded-full flex items-center justify-center flex-shrink-0"
                          style={{ width: 18, height: 18, background: opt.color }}>
                          <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                            <path d="M2 5L4 7L8 3" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Program */}
            <div>
              <label htmlFor="programa" style={{ fontSize: "12px", fontWeight: 600, color: "#374151", display: "block", marginBottom: "5px" }}>
                Programa <span style={{ color: "#ef4444" }}>*</span>
              </label>
              <select
                id="programa"
                value={form.programa}
                onChange={(e) => set("programa")(e.target.value)}
                className="w-full rounded-xl px-4 py-2.5 outline-none transition-all"
                style={{ border: "2px solid #e2e8f0", background: "#f8fafc", fontSize: "13px", color: form.programa ? "#0f172a" : "#94a3b8" }}
                onFocus={(e) => { e.currentTarget.style.borderColor = "#123C7A"; }}
                onBlur={(e) => { e.currentTarget.style.borderColor = "#e2e8f0"; }}
              >
                <option value="">Selecione o programa…</option>
                {PROGRAMAS.map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
              {errors.programa && <p style={{ fontSize: "11px", color: "#ef4444", marginTop: "2px" }}>{errors.programa}</p>}
            </div>

            {form.role === "aluno" && (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <FieldInput label="Matrícula" id="matricula" value={form.matricula}
                    onChange={set("matricula")} placeholder="2024001" required />
                  {errors.matricula && <p style={{ fontSize: "11px", color: "#ef4444", marginTop: "2px" }}>{errors.matricula}</p>}
                </div>
                <div>
                  <label htmlFor="nivel" style={{ fontSize: "12px", fontWeight: 600, color: "#374151", display: "block", marginBottom: "5px" }}>Nível</label>
                  <select id="nivel" value={form.nivel} onChange={(e) => set("nivel")(e.target.value)}
                    className="w-full rounded-xl px-4 py-2.5 outline-none"
                    style={{ border: "2px solid #e2e8f0", background: "#f8fafc", fontSize: "13px" }}
                    onFocus={(e) => { e.currentTarget.style.borderColor = "#123C7A"; }}
                    onBlur={(e) => { e.currentTarget.style.borderColor = "#e2e8f0"; }}>
                    <option value="mestrado">Mestrado</option>
                    <option value="doutorado">Doutorado</option>
                    <option value="pos-doc">Pós-Doutorado</option>
                  </select>
                </div>
              </div>
            )}

            {form.role === "aluno" && (
              <FieldInput label="Orientador(a)" id="orientador" value={form.orientador}
                onChange={set("orientador")} placeholder="Nome do(a) orientador(a)"
                icon={<UserCheck size={14} />} />
            )}
          </div>
        )}

        {/* ── STEP 3 ── */}
        {step === 3 && (
          <div className="space-y-4">
            {/* Info banner */}
            <div className="rounded-2xl p-4" style={{ background: "#eef3fc", border: "1px solid #c7d9f5" }}>
              <div className="flex items-start gap-3">
                <AlertCircle size={18} style={{ color: "#123C7A", flexShrink: 0, marginTop: 1 }} />
                <div>
                  <p style={{ fontSize: "13px", fontWeight: 700, color: "#123C7A", marginBottom: "4px" }}>Criação de senha após aprovação</p>
                  <p style={{ fontSize: "12px", color: "#374151", lineHeight: 1.5 }}>
                    Por segurança, a senha de acesso será criada somente após a <strong>aprovação da matrícula</strong> pela coordenação.
                    Você receberá um código de primeiro acesso por e-mail.
                  </p>
                </div>
              </div>
            </div>

            {/* Document upload */}
            <div>
              <label style={{ fontSize: "12px", fontWeight: 600, color: "#374151", display: "block", marginBottom: "5px" }}>
                Documento de Vínculo <span style={{ fontSize: "11px", fontWeight: 400, color: "#94a3b8" }}>(opcional)</span>
              </label>
              {hasFile ? (
                <div className="flex items-center gap-3 rounded-xl px-4 py-3" style={{ background: "#dcfce7", border: "1px solid #86efac" }}>
                  <CheckCircle2 size={16} style={{ color: "#1F8A70" }} />
                  <span style={{ fontSize: "12px", fontWeight: 600, color: "#1F8A70", flex: 1 }}>{fileName || "documento.pdf"}</span>
                  <button type="button" onClick={() => setHasFile(false)} style={{ color: "#dc2626", background: "none", border: "none" }}>
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M2 2L10 10M10 2L2 10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/></svg>
                  </button>
                </div>
              ) : (
                <label
                  className="rounded-xl p-4 text-center cursor-pointer transition-all block"
                  style={{ border: "2px dashed #cbd5e1", background: "#f8fafc" }}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "#123C7A"; (e.currentTarget as HTMLElement).style.background = "#f0f4fa"; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "#cbd5e1"; (e.currentTarget as HTMLElement).style.background = "#f8fafc"; }}
                >
                  <Upload size={20} style={{ color: "#94a3b8", margin: "0 auto 6px" }} />
                  <p style={{ fontSize: "12px", color: "#64748b", fontWeight: 500 }}>Arraste ou clique para enviar</p>
                  <p style={{ fontSize: "10px", color: "#94a3b8" }}>PDF, JPG ou PNG — máx. 5 MB</p>
                  <input type="file" className="hidden" onChange={e => {
                    if (e.target.files?.[0]) { setHasFile(true); setFileName(e.target.files[0].name); }
                  }} />
                </label>
              )}
            </div>

            {/* Terms */}
            <div>
              <label className="flex items-start gap-2.5 cursor-pointer">
                <button
                  type="button"
                  onClick={() => set("termos")(!form.termos)}
                  className="flex items-center justify-center rounded-md flex-shrink-0 transition-all mt-0.5"
                  style={{
                    width: 18, height: 18,
                    background: form.termos ? "#123C7A" : "#f1f5f9",
                    border: `2px solid ${form.termos ? "#123C7A" : errors.termos ? "#ef4444" : "#cbd5e1"}`,
                  }}
                  aria-checked={form.termos}
                  role="checkbox"
                >
                  {form.termos && (
                    <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                      <path d="M2 5L4 7L8 3" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  )}
                </button>
                <span style={{ fontSize: "12px", color: "#374151", lineHeight: 1.5 }}>
                  Declaro que as informações fornecidas são verídicas e concordo com os{" "}
                  <span style={{ color: "#123C7A", fontWeight: 600 }}>Termos de Uso</span>{" "}
                  e a{" "}
                  <span style={{ color: "#123C7A", fontWeight: 600 }}>Política de Privacidade</span>{" "}
                  do SAGA.
                </span>
              </label>
              {errors.termos && (
                <p style={{ fontSize: "11px", color: "#ef4444", marginTop: "4px", marginLeft: "26px" }}>{errors.termos}</p>
              )}
            </div>
          </div>
        )}

        {/* Navigation buttons */}
        <div className={`flex gap-3 mt-7 ${step > 1 ? "justify-between" : ""}`}>
          {step > 1 && (
            <button
              type="button"
              onClick={back}
              className="flex items-center gap-2 rounded-xl px-5 py-3 transition-all"
              style={{ background: "#f1f5f9", color: "#374151", fontWeight: 600, fontSize: "14px", border: "2px solid #e2e8f0" }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "#e2e8f0"; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "#f1f5f9"; }}
            >
              <ChevronLeft size={16} />
              Voltar
            </button>
          )}
          <button
            type="submit"
            disabled={formState === "loading"}
            className="flex items-center justify-center gap-2.5 rounded-xl py-3 transition-all duration-200"
            style={{
              flex: step === 1 ? "1" : "unset",
              paddingLeft: "24px",
              paddingRight: "24px",
              background: "linear-gradient(135deg,#0d2d5e,#123C7A)",
              color: "#fff",
              fontWeight: 700,
              fontSize: "14px",
              boxShadow: "0 4px 14px rgba(18,60,122,0.3)",
              cursor: formState === "loading" ? "not-allowed" : "pointer",
            }}
          >
            {formState === "loading" ? (
              <><Loader2 size={16} className="animate-spin" /> Enviando…</>
            ) : step < 3 ? (
              <>Continuar <ChevronRight size={16} /></>
            ) : (
              <>Enviar Solicitação <ChevronRight size={16} /></>
            )}
          </button>
        </div>
      </form>

      <p style={{ fontSize: "13px", color: "#94a3b8", textAlign: "center", marginTop: "20px" }}>
        {step < 3 ? (
          <button
            type="button"
            onClick={() => setCurrentPage("login")}
            style={{ color: "#123C7A", fontWeight: 700, background: "none", border: "none" }}
            className="hover:underline"
          >
            ← Voltar ao Login
          </button>
        ) : (
          <>
            Já tem acesso?{" "}
            <button
              type="button"
              onClick={() => setCurrentPage("login")}
              style={{ color: "#123C7A", fontWeight: 700, background: "none", border: "none" }}
              className="hover:underline"
            >
              Fazer login
            </button>
          </>
        )}
      </p>
    </AuthLayout>
  );
}
