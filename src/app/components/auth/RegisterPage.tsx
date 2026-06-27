import { type FormEvent, useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, ChevronRight, Loader2, Mail, User, UserCheck } from "lucide-react";

import {
  registrationRequestsApi,
  type PublicAdvisor,
} from "@/api/registrationRequestsApi";
import { useApp } from "../../context/AppContext";
import { AuthLayout } from "./AuthLayout";

type FormState = "idle" | "loading" | "success";

interface FormData {
  nome: string;
  email: string;
  advisor_id: string;
}

const EMPTY_FORM: FormData = {
  nome: "",
  email: "",
  advisor_id: "",
};

function FieldInput({
  label,
  id,
  type = "text",
  value,
  onChange,
  placeholder,
  icon,
  required,
}: {
  label: string;
  id: string;
  type?: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  icon?: React.ReactNode;
  required?: boolean;
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
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          className="w-full rounded-xl py-2.5 outline-none transition-all"
          style={{
            border: "2px solid #e2e8f0",
            background: "#f8fafc",
            fontSize: "13px",
            color: "#0f172a",
            paddingLeft: icon ? "38px" : "14px",
            paddingRight: "14px",
          }}
          onFocus={(event) => {
            event.currentTarget.style.borderColor = "#123C7A";
            event.currentTarget.style.background = "#fff";
          }}
          onBlur={(event) => {
            event.currentTarget.style.borderColor = "#e2e8f0";
            event.currentTarget.style.background = "#f8fafc";
          }}
        />
      </div>
    </div>
  );
}

function getFriendlyError(error: unknown): string {
  const message = error instanceof Error ? error.message : "Falha ao enviar solicitação de cadastro.";
  const normalized = message.toLowerCase();

  if (
    normalized.includes("duplic") ||
    normalized.includes("already") ||
    normalized.includes("existe") ||
    normalized.includes("e-mail") ||
    normalized.includes("email")
  ) {
    return "Já existe uma solicitação utilizando este e-mail.";
  }

  return message;
}

export function RegisterPage() {
  const { setCurrentPage } = useApp();
  const [formState, setFormState] = useState<FormState>("idle");
  const [form, setForm] = useState<FormData>(EMPTY_FORM);
  const [errors, setErrors] = useState<Partial<Record<keyof FormData, string>>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [advisors, setAdvisors] = useState<PublicAdvisor[]>([]);
  const [advisorsLoading, setAdvisorsLoading] = useState(true);
  const [advisorsError, setAdvisorsError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadAdvisors(): Promise<void> {
      setAdvisorsLoading(true);
      setAdvisorsError(null);
      try {
        const data = await registrationRequestsApi.listActiveAdvisors();
        if (active) setAdvisors(data);
      } catch (error) {
        if (active) {
          setAdvisorsError(error instanceof Error ? error.message : "Falha ao carregar orientadores.");
        }
      } finally {
        if (active) setAdvisorsLoading(false);
      }
    }

    void loadAdvisors();
    return () => {
      active = false;
    };
  }, []);

  const set = (key: keyof FormData) => (value: string) => {
    setForm((current) => ({ ...current, [key]: value }));
    setErrors((current) => ({ ...current, [key]: undefined }));
    setSubmitError(null);
  };

  function validate(): boolean {
    const nextErrors: typeof errors = {};
    if (!form.nome.trim()) nextErrors.nome = "Nome obrigatório";
    if (!form.email.trim() || !/\S+@\S+\.\S+/.test(form.email)) {
      nextErrors.email = "E-mail válido obrigatório";
    }
    if (!form.advisor_id) nextErrors.advisor_id = "Selecione um orientador";

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!validate()) return;

    setFormState("loading");
    setSubmitError(null);
    try {
      await registrationRequestsApi.create({
        nome: form.nome.trim(),
        email: form.email.trim(),
        advisor_id: form.advisor_id,
      });
      setForm(EMPTY_FORM);
      setFormState("success");
    } catch (error) {
      setSubmitError(getFriendlyError(error));
      setFormState("idle");
    }
  }

  if (formState === "success") {
    return (
      <AuthLayout>
        <div className="text-center py-8">
          <div
            className="flex items-center justify-center mx-auto mb-6 rounded-full"
            style={{ width: 80, height: 80, background: "#dcfce7", border: "3px solid #bbf7d0" }}
          >
            <CheckCircle2 size={40} style={{ color: "#16a34a" }} />
          </div>
          <h2 style={{ fontSize: "24px", fontWeight: 800, color: "#0f172a", marginBottom: "12px" }}>
            Solicitação enviada
          </h2>
          <p style={{ fontSize: "14px", color: "#64748b", lineHeight: 1.65, marginBottom: "28px" }}>
            Sua solicitação foi enviada com sucesso. Aguarde o contato e a aprovação da coordenação para prosseguir com o cadastro.
          </p>
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

  return (
    <AuthLayout>
      <div className="mb-7">
        <h2 style={{ fontSize: "24px", fontWeight: 800, color: "#0f172a", lineHeight: 1.2, marginBottom: "4px" }}>
          Solicitar Cadastro
        </h2>
        <p style={{ fontSize: "14px", color: "#64748b" }}>
          Envie seus dados para análise da coordenação.
        </p>
      </div>

      <form onSubmit={handleSubmit} noValidate>
        <div className="space-y-4">
          <FieldInput
            label="Nome"
            id="nome"
            value={form.nome}
            onChange={set("nome")}
            placeholder="Seu nome completo"
            icon={<User size={14} />}
            required
          />
          {errors.nome && <p style={{ fontSize: "11px", color: "#ef4444", marginTop: "-8px" }}>{errors.nome}</p>}

          <FieldInput
            label="E-mail"
            id="email"
            type="email"
            value={form.email}
            onChange={set("email")}
            placeholder="seu.email@exemplo.com"
            icon={<Mail size={14} />}
            required
          />
          {errors.email && <p style={{ fontSize: "11px", color: "#ef4444", marginTop: "-8px" }}>{errors.email}</p>}

          <div>
            <label htmlFor="advisor_id" style={{ fontSize: "12px", fontWeight: 600, color: "#374151", display: "block", marginBottom: "5px" }}>
              Orientador desejado <span style={{ color: "#ef4444" }}>*</span>
            </label>
            <div className="relative">
              <span className="absolute top-1/2 -translate-y-1/2 left-3.5" style={{ color: "#94a3b8", pointerEvents: "none" }}>
                <UserCheck size={14} />
              </span>
              <select
                id="advisor_id"
                value={form.advisor_id}
                onChange={(event) => set("advisor_id")(event.target.value)}
                disabled={advisorsLoading || advisors.length === 0}
                className="w-full rounded-xl py-2.5 outline-none transition-all"
                style={{
                  border: "2px solid #e2e8f0",
                  background: "#f8fafc",
                  fontSize: "13px",
                  color: form.advisor_id ? "#0f172a" : "#94a3b8",
                  paddingLeft: "38px",
                  paddingRight: "14px",
                  opacity: advisorsLoading ? 0.75 : 1,
                }}
              >
                <option value="">
                  {advisorsLoading ? "Carregando orientadores..." : "Selecione um orientador"}
                </option>
                {advisors.map((advisor) => (
                  <option key={advisor.id} value={advisor.id}>
                    {advisor.nome}
                  </option>
                ))}
              </select>
            </div>
            {errors.advisor_id && <p style={{ fontSize: "11px", color: "#ef4444", marginTop: "4px" }}>{errors.advisor_id}</p>}
            {advisorsError && (
              <p style={{ fontSize: "11px", color: "#ef4444", marginTop: "4px" }}>
                {advisorsError}
              </p>
            )}
          </div>

          {submitError && (
            <div className="rounded-2xl p-4" style={{ background: "#fee2e2", border: "1px solid #fecaca" }}>
              <div className="flex items-start gap-3">
                <AlertCircle size={18} style={{ color: "#dc2626", flexShrink: 0, marginTop: 1 }} />
                <p style={{ fontSize: "12px", color: "#991b1b", lineHeight: 1.5 }}>{submitError}</p>
              </div>
            </div>
          )}
        </div>

        <button
          type="submit"
          disabled={formState === "loading" || advisorsLoading}
          className="w-full flex items-center justify-center gap-2.5 rounded-xl py-3 mt-7 transition-all duration-200"
          style={{
            background: "linear-gradient(135deg,#0d2d5e,#123C7A)",
            color: "#fff",
            fontWeight: 700,
            fontSize: "14px",
            boxShadow: "0 4px 14px rgba(18,60,122,0.3)",
            cursor: formState === "loading" || advisorsLoading ? "not-allowed" : "pointer",
            opacity: formState === "loading" || advisorsLoading ? 0.75 : 1,
          }}
        >
          {formState === "loading" ? (
            <>
              <Loader2 size={16} className="animate-spin" /> Enviando...
            </>
          ) : (
            <>
              Enviar Solicitação <ChevronRight size={16} />
            </>
          )}
        </button>
      </form>

      <p style={{ fontSize: "13px", color: "#94a3b8", textAlign: "center", marginTop: "20px" }}>
        Já tem acesso?{" "}
        <button
          type="button"
          onClick={() => setCurrentPage("login")}
          style={{ color: "#123C7A", fontWeight: 700, background: "none", border: "none" }}
          className="hover:underline"
        >
          Fazer login
        </button>
      </p>
    </AuthLayout>
  );
}
