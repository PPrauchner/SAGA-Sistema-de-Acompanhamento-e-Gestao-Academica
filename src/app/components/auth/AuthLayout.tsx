import { ReactNode } from "react";
import { useApp } from "../../context/AppContext";
import { AuthIllustration } from "./AuthIllustration";
import { GraduationCap, Shield, Lock, Users, BookOpen } from "lucide-react";

interface AuthLayoutProps {
  children: ReactNode;
  /** Which step indicator to highlight (1-based). undefined = no steps */
  step?: number;
  totalSteps?: number;
  /** Disable scroll on the right panel — use only on LoginPage where content fits the viewport */
  noScroll?: boolean;
}

const SECURITY_BADGES = [
  { icon: <Shield size={13} />, label: "Conexão segura HTTPS" },
  { icon: <Lock size={13} />, label: "Dados criptografados" },
  { icon: <Users size={13} />, label: "Acesso por perfil" },
];

export function AuthLayout({ children, step, totalSteps, noScroll }: AuthLayoutProps) {
  return (
    <div className="min-h-screen w-full flex" style={{ background: "#f0f4fa" }}>

      {/* ── LEFT PANEL ─────────────────────────────────────────────── */}
      <div
        className="hidden lg:flex flex-col relative overflow-hidden"
        style={{
          width: "45%",
          ...(noScroll ? { height: "100vh" } : { minHeight: "100vh" }),
          background: "linear-gradient(160deg, #0a1f3d 0%, #0d2d5e 35%, #123C7A 70%, #1a4f9a 100%)",
        }}
      >
        {/* Decorative blobs */}
        <div style={{
          position: "absolute", top: -80, right: -80, width: 320, height: 320,
          borderRadius: "50%", background: "rgba(212,160,23,0.06)", pointerEvents: "none",
        }} />
        <div style={{
          position: "absolute", bottom: -60, left: -60, width: 260, height: 260,
          borderRadius: "50%", background: "rgba(31,138,112,0.07)", pointerEvents: "none",
        }} />
        <div style={{
          position: "absolute", top: "40%", left: "60%", width: 140, height: 140,
          borderRadius: "50%", background: "rgba(255,255,255,0.03)", pointerEvents: "none",
        }} />

        {/* Inner content */}
        <div className="relative z-10 flex flex-col h-full px-10 py-10">

          {/* Logo */}
          <div className="flex items-center gap-3 mb-6">
            <div className="flex items-center justify-center rounded-2xl flex-shrink-0"
              style={{ width: 46, height: 46, background: "#D4A017", boxShadow: "0 4px 14px rgba(212,160,23,0.35)" }}>
              <GraduationCap size={24} color="#fff" />
            </div>
            <div>
              <p style={{ color: "#fff", fontSize: "16px", fontWeight: 800, lineHeight: 1.15 }}>SAGA</p>
              <p style={{ color: "rgba(255,255,255,0.55)", fontSize: "10px", letterSpacing: "0.06em" }}>
                SISTEMA ACADÊMICO
              </p>
            </div>
          </div>

          {/* Main headline */}
          <div className="flex-1 flex flex-col justify-center">
            <p style={{ color: "rgba(255,255,255,0.55)", fontSize: "12px", fontWeight: 600,
              textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "10px" }}>
              Bem-vindo(a) ao
            </p>
            <h1 style={{ color: "#fff", fontSize: "30px", fontWeight: 800, lineHeight: 1.25,
              marginBottom: "8px" }}>
              Sistema de Acompanhamento<br />
              <span style={{ color: "#D4A017" }}>Acadêmico</span> da<br />
              Pós-Graduação
            </h1>
            <p style={{ color: "rgba(255,255,255,0.6)", fontSize: "14px", lineHeight: 1.65,
              maxWidth: 340, marginBottom: "16px" }}>
              Gerencie alunos, orientadores e produções científicas
              com inteligência e eficiência.
            </p>

            {/* Illustration */}
            <div style={{ marginBottom: "16px", opacity: 0.92 }}>
              <AuthIllustration />
            </div>

            {/* Institution name */}
            <div className="rounded-2xl px-4 py-3 mb-3"
              style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)" }}>
              <div className="flex items-center gap-2 mb-1">
                <BookOpen size={13} style={{ color: "#D4A017", flexShrink: 0 }} />
                <p style={{ color: "rgba(255,255,255,0.5)", fontSize: "9px", fontWeight: 600,
                  textTransform: "uppercase", letterSpacing: "0.08em" }}>Programa</p>
              </div>
              <p style={{ color: "#fff", fontSize: "12px", fontWeight: 600 }}>
                PPGCC — Ciência da Computação
              </p>
              <p style={{ color: "rgba(255,255,255,0.45)", fontSize: "11px", marginTop: "2px" }}>
                Universidade Federal do Pampa — Campus de Alegrete
              </p>
            </div>
          </div>

          {/* Security badges */}
          <div className="flex flex-col gap-2">
            {SECURITY_BADGES.map((badge) => (
              <div key={badge.label} className="flex items-center gap-2">
                <span style={{ color: "#1F8A70" }}>{badge.icon}</span>
                <span style={{ color: "rgba(255,255,255,0.4)", fontSize: "11px" }}>{badge.label}</span>
              </div>
            ))}
          </div>

          <p style={{ color: "rgba(255,255,255,0.25)", fontSize: "10px", marginTop: "16px" }}>
            © {new Date().getFullYear()} Universidade Federal do Pampa — SAGA v2.4
          </p>
        </div>
      </div>

      {/* ── RIGHT PANEL ────────────────────────────────────────────── */}
      <div
        className="flex flex-1 flex-col items-center justify-center p-6 lg:p-10"
        style={noScroll
          ? { height: "100vh", overflowY: "hidden" }
          : { minHeight: "100vh", overflowY: "auto" }
        }>

        {/* Mobile-only logo */}
        <div className="flex lg:hidden items-center gap-3 mb-8">
          <div className="flex items-center justify-center rounded-xl flex-shrink-0"
            style={{ width: 40, height: 40, background: "#123C7A" }}>
            <GraduationCap size={22} color="#fff" />
          </div>
          <div>
            <p style={{ fontWeight: 800, color: "#123C7A", fontSize: "15px" }}>SAGA</p>
            <p style={{ fontSize: "10px", color: "#64748b" }}>Pós-Graduação</p>
          </div>
        </div>

        {/* Step dots */}
        {step && totalSteps && (
          <div className="flex items-center gap-2 mb-6">
            {Array.from({ length: totalSteps }, (_, i) => (
              <div key={i} className="rounded-full transition-all duration-300"
                style={{
                  width: i + 1 === step ? 24 : 8,
                  height: 8,
                  background: i + 1 <= step ? "#123C7A" : "#cbd5e1",
                }} />
            ))}
            <span style={{ fontSize: "11px", color: "#94a3b8", marginLeft: "4px" }}>
              {step} de {totalSteps}
            </span>
          </div>
        )}

        <div className="w-full" style={{ maxWidth: 440 }}>
          {children}
        </div>

        {/* Mobile security notice */}
        <div className="flex lg:hidden items-center gap-2 mt-6">
          <Shield size={12} style={{ color: "#94a3b8" }} />
          <p style={{ fontSize: "11px", color: "#94a3b8" }}>Conexão segura — dados criptografados</p>
        </div>
      </div>
    </div>
  );
}
