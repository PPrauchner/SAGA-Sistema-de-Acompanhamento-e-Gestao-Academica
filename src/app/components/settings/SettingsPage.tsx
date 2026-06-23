import { useState, useEffect } from "react";
import { useApp } from "../../context/AppContext";
import { useAuth } from "../../../hooks/useAuth";
import { User, Bell, Shield, Palette, Globe, Key, Save, Camera, Mail, Phone, Building, Plus, CheckCircle2, XCircle, Edit, ArrowRightLeft, Send, Ban } from "lucide-react";
import { programsApi } from "../../../api/programsApi";
import { activityTypesApi } from "../../../api/activityTypesApi";
import { getAdvisors, type Advisor } from "../../../api/advisorsApi";
import { coordinationTransfersApi, type CoordinationTransfer } from "../../../api/coordinationTransfersApi";
import { toast } from "sonner";

export interface ProgramConfig {
  id?: string;
  creditos_grupo_basico_min: number;
  creditos_grupo_especifico_min: number;
  creditos_grupo_tecnologico_max: number;
  creditos_total_min: number;
  meses_ate_qualificacao: number;
}

// Base usada quando o usuário edita antes de a API retornar a config.
const DEFAULT_PROGRAM_CONFIG: ProgramConfig = {
  creditos_grupo_basico_min: 0,
  creditos_grupo_especifico_min: 0,
  creditos_grupo_tecnologico_max: 0,
  creditos_total_min: 0,
  meses_ate_qualificacao: 0,
};

export interface ActivityType {
  id?: string;
  nome: string;
  categoria: string;
  pontuacao_base: number;
  exige_comprovante?: boolean;
  limite_maximo_creditos?: number | null;
  permite_multiplas?: boolean;
  ativo?: boolean;
  programa_id?: string;
}

export interface VehicleLevel {
  id: string;
  nivel: string;
  peso: number;
}

const BASE_TABS = [
  { id: "perfil", label: "Perfil", icon: <User size={16} /> },
  { id: "notificacoes", label: "Notificações", icon: <Bell size={16} /> },
  { id: "seguranca", label: "Segurança", icon: <Shield size={16} /> },
  { id: "aparencia", label: "Aparência", icon: <Palette size={16} /> },
  { id: "sistema", label: "Sistema", icon: <Globe size={16} /> },
];

export function SettingsPage() {
  const { currentUser, darkMode, toggleDarkMode } = useApp();
  const { token } = useAuth();
  const [activeTab, setActiveTab] = useState("perfil");
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(false);

  // Program Config State
  const [programConfig, setProgramConfig] = useState<ProgramConfig | null>(null);
  const [activityTypes, setActivityTypes] = useState<ActivityType[]>([]);
  const [vehicleLevels, setVehicleLevels] = useState<VehicleLevel[]>([]);
  const [advisors, setAdvisors] = useState<Advisor[]>([]);
  const [transfers, setTransfers] = useState<CoordinationTransfer[]>([]);
  const [selectedSuccessorUid, setSelectedSuccessorUid] = useState("");

  // Modal States
  const [isActivityModalOpen, setIsActivityModalOpen] = useState(false);
  const [currentActivity, setCurrentActivity] = useState<ActivityType | null>(null);
  
  const [isVehicleModalOpen, setIsVehicleModalOpen] = useState(false);
  const [currentVehicle, setCurrentVehicle] = useState<VehicleLevel | null>(null);

  useEffect(() => {
    if (activeTab === "programa" && currentUser?.role === "coordenacao") {
      fetchProgramData();
    }
  }, [activeTab, currentUser?.role]);

  useEffect(() => {
    if (activeTab === "transferencia" && token && (currentUser?.role === "coordenacao" || currentUser?.role === "orientador")) {
      fetchTransferData();
    }
  }, [activeTab, token, currentUser?.role]);

  const fetchProgramData = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const [config, types, vLevels] = await Promise.all([
        programsApi.getProgramConfig(token),
        activityTypesApi.getActivityTypes(token),
        programsApi.getVehicleLevels(token)
      ]);
      setProgramConfig(config);
      setActivityTypes(types);
      setVehicleLevels(vLevels);
    } catch (error) {
      toast.error("Erro ao carregar dados do programa");
    } finally {
      setLoading(false);
    }
  };

  const fetchTransferData = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const transferList = await coordinationTransfersApi.list(token);
      setTransfers(transferList);
      if (currentUser?.role === "coordenacao") {
        const advisorList = await getAdvisors(token);
        const sameProgram = advisorList.filter((advisor) => advisor.programa_id === currentUser.programa);
        setAdvisors(sameProgram);
        setSelectedSuccessorUid((current) => current || sameProgram.find((advisor) => advisor.uid)?.uid || "");
      }
    } catch (error) {
      toast.error("Erro ao carregar transferências");
    } finally {
      setLoading(false);
    }
  };

  const handleSaveConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setLoading(true);
    try {
      await programsApi.updateProgramConfig(token, programConfig);
      setSaved(true);
      toast.success("Configurações atualizadas");
      setTimeout(() => setSaved(false), 2000);
    } catch (error) {
      toast.error("Erro ao salvar configurações");
    } finally {
      setLoading(false);
    }
  };

  const handleToggleActivity = async (id: string) => {
    if (!token) return;
    try {
      await activityTypesApi.toggleActivityType(token, id);
      setActivityTypes(activityTypes.map(t => t.id === id ? { ...t, ativo: !t.ativo } : t));
      toast.success("Status atualizado");
    } catch (error) {
      toast.error("Erro ao atualizar status");
    }
  };

  const handleSaveActivity = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !currentActivity) return;
    try {
      if (currentActivity.id) {
        await activityTypesApi.updateActivityType(token, currentActivity.id, currentActivity);
        setActivityTypes(activityTypes.map(t => t.id === currentActivity.id ? currentActivity : t));
        toast.success("Tipo de atividade atualizado!");
      } else {
        const created = await activityTypesApi.createActivityType(token, currentActivity);
        setActivityTypes([...activityTypes, { ...currentActivity, id: created.id }]);
        toast.success("Tipo de atividade criado!");
      }
      setIsActivityModalOpen(false);
    } catch (error) {
      toast.error("Erro ao salvar tipo de atividade");
    }
  };

  const handleSaveVehicle = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !currentVehicle) return;
    try {
      await programsApi.updateVehicleLevel(token, currentVehicle.id, {
        nivel: currentVehicle.nivel,
        peso: currentVehicle.peso
      });
      setVehicleLevels(vehicleLevels.map(v => v.id === currentVehicle.id ? currentVehicle : v));
      toast.success("Nível de veículo atualizado!");
      setIsVehicleModalOpen(false);
    } catch (error) {
      toast.error("Erro ao salvar nível de veículo");
    }
  };

  const openNewActivityModal = () => {
    setCurrentActivity({ nome: "", categoria: "tecnologico", pontuacao_base: 10, exige_comprovante: true, limite_maximo_creditos: null, programa_id: currentUser?.programa });
    setIsActivityModalOpen(true);
  };

  const openEditActivityModal = (type: ActivityType) => {
    setCurrentActivity({ ...type });
    setIsActivityModalOpen(true);
  };

  const openEditVehicleModal = (level: VehicleLevel) => {
    setCurrentVehicle({ ...level });
    setIsVehicleModalOpen(true);
  };

  const transferTab = { id: "transferencia", label: "Transferência", icon: <ArrowRightLeft size={16} /> };
  const tabs = currentUser?.role === "coordenacao"
    ? [...BASE_TABS, transferTab, { id: "programa", label: "Regras do Programa", icon: <Building size={16} /> }]
    : currentUser?.role === "orientador"
      ? [...BASE_TABS, transferTab]
      : BASE_TABS;

  const pendingTransfer = transfers.find((transfer) => transfer.status === "pendente");

  const handleStartTransfer = async () => {
    if (!token || !selectedSuccessorUid) return;
    setLoading(true);
    try {
      await coordinationTransfersApi.start(token, selectedSuccessorUid);
      toast.success("Transferência iniciada");
      await fetchTransferData();
    } catch (error) {
      const status = (error as Error & { status?: number }).status;
      toast.error(status === 409 ? "Já existe transferência pendente no programa" : "Erro ao iniciar transferência");
    } finally {
      setLoading(false);
    }
  };

  const handleAcceptTransfer = async (transferId: string) => {
    if (!token) return;
    setLoading(true);
    try {
      await coordinationTransfersApi.accept(token, transferId);
      toast.success("Transferência aceita");
      await fetchTransferData();
    } catch (error) {
      toast.error("Erro ao aceitar transferência");
    } finally {
      setLoading(false);
    }
  };

  const handleRejectTransfer = async (transferId: string) => {
    if (!token) return;
    setLoading(true);
    try {
      await coordinationTransfersApi.reject(token, transferId);
      toast.success("Transferência rejeitada");
      await fetchTransferData();
    } catch (error) {
      toast.error("Erro ao rejeitar transferência");
    } finally {
      setLoading(false);
    }
  };

  const handleCancelTransfer = async (transferId: string) => {
    if (!token) return;
    setLoading(true);
    try {
      await coordinationTransfersApi.cancel(token, transferId);
      toast.success("Transferência cancelada");
      await fetchTransferData();
    } catch (error) {
      toast.error("Erro ao cancelar transferência");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div>
      <div className="mb-6">
        <h1 style={{ color: "var(--foreground)", marginBottom: "4px" }}>Configurações</h1>
        <p style={{ color: "var(--muted-foreground)", fontSize: "14px" }}>Gerencie suas preferências e dados da conta</p>
      </div>

      {/* Mobile horizontal tab bar */}
      <div className="md:hidden flex gap-2 overflow-x-auto pb-2 mb-4" style={{ scrollbarWidth: "none" }}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className="flex items-center gap-1.5 rounded-xl px-3 py-2 flex-shrink-0 transition-all"
            style={{
              background: activeTab === tab.id ? "#123C7A" : "var(--card)",
              color: activeTab === tab.id ? "#fff" : "var(--muted-foreground)",
              fontSize: "12px", fontWeight: 600,
              border: `1px solid ${activeTab === tab.id ? "#123C7A" : "var(--border)"}`,
              minHeight: "40px",
            }}>
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex flex-col md:flex-row gap-6">
        {/* Sidebar — desktop only */}
        <div className="hidden md:block w-56 flex-shrink-0">
          <div className="rounded-2xl p-3 sticky top-0" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className="w-full flex items-center gap-3 rounded-xl px-3 py-2.5 mb-1 transition-all text-left"
                style={{
                  background: activeTab === tab.id ? "#eef3fc" : "transparent",
                  color: activeTab === tab.id ? "#123C7A" : "var(--muted-foreground)",
                  fontWeight: activeTab === tab.id ? 600 : 400,
                  fontSize: "13px",
                }}
                onMouseEnter={(e) => { if (activeTab !== tab.id) (e.currentTarget as HTMLElement).style.background = "var(--muted)"; }}
                onMouseLeave={(e) => { if (activeTab !== tab.id) (e.currentTarget as HTMLElement).style.background = "transparent"; }}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {activeTab === "perfil" && (
            <div className="rounded-2xl p-6" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
              <h2 style={{ fontSize: "17px", fontWeight: 700, color: "var(--foreground)", marginBottom: "24px" }}>Informações do Perfil</h2>

              {/* Avatar */}
              <div className="flex items-center gap-6 mb-8 pb-8" style={{ borderBottom: "1px solid var(--border)" }}>
                <div className="relative">
                  <div className="rounded-2xl flex items-center justify-center" style={{ width: 72, height: 72, background: "#123C7A", color: "#fff", fontSize: "26px", fontWeight: 800 }}>
                    {currentUser?.name.charAt(0)}
                  </div>
                  <button className="absolute -bottom-1 -right-1 rounded-full flex items-center justify-center" style={{ width: 26, height: 26, background: "#D4A017", color: "#fff" }}>
                    <Camera size={13} />
                  </button>
                </div>
                <div>
                  <p style={{ fontSize: "16px", fontWeight: 700, color: "var(--foreground)" }}>{currentUser?.name}</p>
                  <p style={{ fontSize: "13px", color: "var(--muted-foreground)" }}>{currentUser?.email}</p>
                  <button className="mt-2 px-3 py-1.5 rounded-lg text-sm" style={{ background: "var(--muted)", color: "var(--foreground)", fontWeight: 600, fontSize: "12px" }}>
                    Alterar foto
                  </button>
                </div>
              </div>

              {/* Form fields */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 md:gap-6">
                {[
                  { label: "Nome Completo", value: currentUser?.name || "", icon: <User size={14} /> },
                  { label: "E-mail Institucional", value: currentUser?.email || "", icon: <Mail size={14} /> },
                  { label: "Telefone", value: "(11) 99999-0000", icon: <Phone size={14} /> },
                  { label: "Departamento", value: currentUser?.departamento || "", icon: <Building size={14} /> },
                  { label: "Programa", value: currentUser?.programa || "", icon: <Building size={14} /> },
                  ...(currentUser?.matricula ? [{ label: "Matrícula", value: currentUser.matricula, icon: <Key size={14} /> }] : []),
                ].map((field) => (
                  <div key={field.label}>
                    <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", display: "block", marginBottom: "6px" }}>{field.label}</label>
                    <div className="relative">
                      <div className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--muted-foreground)" }}>
                        {field.icon}
                      </div>
                      <input
                        defaultValue={field.value}
                        className="w-full rounded-xl pl-9 pr-4 py-2.5 outline-none"
                        style={{ border: "1px solid var(--border)", background: "var(--input-background)", fontSize: "13px", color: "var(--foreground)" }}
                        onFocus={(e) => { e.currentTarget.style.borderColor = "#123C7A"; }}
                        onBlur={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }}
                      />
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-6 flex gap-3">
                <button onClick={handleSave} className="flex items-center gap-2 rounded-xl px-5 py-2.5" style={{ background: saved ? "#1F8A70" : "#123C7A", color: "#fff", fontWeight: 600, fontSize: "14px", transition: "background 0.3s" }}>
                  <Save size={15} /> {saved ? "Salvo!" : "Salvar Alterações"}
                </button>
              </div>
            </div>
          )}

          {activeTab === "notificacoes" && (
            <div className="rounded-2xl p-6" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
              <h2 style={{ fontSize: "17px", fontWeight: 700, color: "var(--foreground)", marginBottom: "24px" }}>Preferências de Notificação</h2>
              <div className="space-y-4">
                {[
                  { label: "Notificações por E-mail", desc: "Receber resumos de atividades por e-mail", enabled: true },
                  { label: "Alertas de Prazo", desc: "Aviso antecipado de vencimentos de prazo", enabled: true },
                  { label: "Novas Submissões", desc: "Quando alunos submetem documentos", enabled: true },
                  { label: "Aprovações Pendentes", desc: "Itens aguardando sua aprovação", enabled: true },
                  { label: "Relatórios do Sistema", desc: "Relatórios automáticos semanais", enabled: false },
                  { label: "Atualizações do Sistema", desc: "Novas versões e manutenções", enabled: false },
                ].map((pref) => (
                  <div key={pref.label} className="flex items-center justify-between py-3" style={{ borderBottom: "1px solid var(--border)" }}>
                    <div>
                      <p style={{ fontSize: "14px", fontWeight: 600, color: "var(--foreground)" }}>{pref.label}</p>
                      <p style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>{pref.desc}</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input type="checkbox" defaultChecked={pref.enabled} className="sr-only" />
                      <div
                        className="rounded-full transition-all"
                        style={{ width: 44, height: 24, background: pref.enabled ? "#123C7A" : "var(--muted)", cursor: "pointer" }}
                      >
                        <div
                          className="rounded-full transition-all"
                          style={{ width: 18, height: 18, background: "#fff", margin: "3px", marginLeft: pref.enabled ? "23px" : "3px", boxShadow: "0 1px 3px rgba(0,0,0,0.2)" }}
                        />
                      </div>
                    </label>
                  </div>
                ))}
              </div>
              <button onClick={handleSave} className="mt-6 flex items-center gap-2 rounded-xl px-5 py-2.5" style={{ background: "#123C7A", color: "#fff", fontWeight: 600, fontSize: "14px" }}>
                <Save size={15} /> Salvar Preferências
              </button>
            </div>
          )}

          {activeTab === "seguranca" && (
            <div className="rounded-2xl p-6" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
              <h2 style={{ fontSize: "17px", fontWeight: 700, color: "var(--foreground)", marginBottom: "24px" }}>Segurança da Conta</h2>
              <div className="space-y-6">
                <div className="p-4 rounded-xl" style={{ background: "var(--muted)" }}>
                  <h3 style={{ fontSize: "14px", fontWeight: 700, color: "var(--foreground)", marginBottom: "16px" }}>Alterar Senha</h3>
                  <div className="space-y-3">
                    {["Senha Atual", "Nova Senha", "Confirmar Nova Senha"].map((label) => (
                      <div key={label}>
                        <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", display: "block", marginBottom: "6px" }}>{label}</label>
                        <input type="password" placeholder="••••••••" className="w-full rounded-xl px-4 py-2.5 outline-none" style={{ border: "1px solid var(--border)", background: "var(--card)", fontSize: "13px" }} onFocus={(e) => { e.currentTarget.style.borderColor = "#123C7A"; }} onBlur={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }} />
                      </div>
                    ))}
                    <button className="rounded-xl px-4 py-2.5" style={{ background: "#123C7A", color: "#fff", fontWeight: 600, fontSize: "13px" }}>
                      Atualizar Senha
                    </button>
                  </div>
                </div>

                <div className="p-4 rounded-xl" style={{ background: "var(--muted)" }}>
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 style={{ fontSize: "14px", fontWeight: 700, color: "var(--foreground)" }}>Autenticação de Dois Fatores</h3>
                      <p style={{ fontSize: "12px", color: "var(--muted-foreground)", marginTop: "4px" }}>Adicione uma camada extra de segurança</p>
                    </div>
                    <button className="px-4 py-2 rounded-xl" style={{ background: "#1F8A70", color: "#fff", fontWeight: 600, fontSize: "13px" }}>
                      Ativar 2FA
                    </button>
                  </div>
                </div>

                <div className="p-4 rounded-xl" style={{ background: "#fef9c3", border: "1px solid #D4A01730" }}>
                  <h3 style={{ fontSize: "14px", fontWeight: 700, color: "#D4A017", marginBottom: "8px" }}>⚠️ Zona de Perigo</h3>
                  <p style={{ fontSize: "12px", color: "#64748b", marginBottom: "12px" }}>Ações irreversíveis que afetam permanentemente sua conta.</p>
                  <button className="px-4 py-2 rounded-xl" style={{ background: "#fee2e2", color: "#dc2626", fontWeight: 600, fontSize: "13px" }}>
                    Solicitar Exclusão da Conta
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeTab === "aparencia" && (
            <div className="rounded-2xl p-6" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
              <h2 style={{ fontSize: "17px", fontWeight: 700, color: "var(--foreground)", marginBottom: "24px" }}>Aparência</h2>
              <div className="space-y-6">
                <div>
                  <label style={{ fontSize: "13px", fontWeight: 600, color: "var(--foreground)", display: "block", marginBottom: "12px" }}>Tema do Sistema</label>
                  <div className="grid grid-cols-2 gap-3">
                    {[
                      { label: "Claro", value: false, preview: "#f4f6f9" },
                      { label: "Escuro", value: true, preview: "#0f1729" },
                    ].map((theme) => (
                      <button
                        key={theme.label}
                        onClick={() => { if (darkMode !== theme.value) toggleDarkMode(); }}
                        className="rounded-xl p-4 border-2 transition-all"
                        style={{
                          borderColor: darkMode === theme.value ? "#123C7A" : "var(--border)",
                          background: darkMode === theme.value ? "#eef3fc" : "var(--muted)",
                        }}
                      >
                        <div className="rounded-lg mb-3 overflow-hidden" style={{ height: 60, background: theme.preview }}>
                          <div className="flex h-full">
                            <div style={{ width: 30, background: theme.value ? "#0d1f3c" : "#123C7A" }} />
                            <div className="flex-1 p-2">
                              <div className="rounded h-2 mb-1.5" style={{ background: theme.value ? "#1a2540" : "#e2e8f0", width: "80%" }} />
                              <div className="rounded h-2" style={{ background: theme.value ? "#1a2540" : "#e2e8f0", width: "60%" }} />
                            </div>
                          </div>
                        </div>
                        <p style={{ fontSize: "13px", fontWeight: 600, color: darkMode === theme.value ? "#123C7A" : "var(--foreground)" }}>
                          {theme.label} {darkMode === theme.value ? "✓" : ""}
                        </p>
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label style={{ fontSize: "13px", fontWeight: 600, color: "var(--foreground)", display: "block", marginBottom: "12px" }}>Tamanho da Fonte</label>
                  <div className="flex gap-3">
                    {["Pequena", "Normal", "Grande"].map((size) => (
                      <button key={size} className="px-4 py-2 rounded-xl border-2 transition-all" style={{ borderColor: size === "Normal" ? "#123C7A" : "var(--border)", background: size === "Normal" ? "#eef3fc" : "var(--muted)", color: size === "Normal" ? "#123C7A" : "var(--foreground)", fontWeight: 600, fontSize: "13px" }}>
                        {size}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "sistema" && (
            <div className="rounded-2xl p-6" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
              <h2 style={{ fontSize: "17px", fontWeight: 700, color: "var(--foreground)", marginBottom: "24px" }}>Configurações do Sistema</h2>
              <div className="space-y-4">
                {[
                  { label: "Idioma do Sistema", options: ["Português (BR)", "English", "Español"], current: "Português (BR)" },
                  { label: "Fuso Horário", options: ["America/Sao_Paulo", "America/Manaus", "America/Belem"], current: "America/Sao_Paulo" },
                  { label: "Formato de Data", options: ["DD/MM/AAAA", "MM/DD/AAAA", "AAAA-MM-DD"], current: "DD/MM/AAAA" },
                ].map((setting) => (
                  <div key={setting.label} className="flex items-center justify-between py-3" style={{ borderBottom: "1px solid var(--border)" }}>
                    <p style={{ fontSize: "14px", fontWeight: 600, color: "var(--foreground)" }}>{setting.label}</p>
                    <select defaultValue={setting.current} className="rounded-xl px-3 py-2 outline-none" style={{ border: "1px solid var(--border)", background: "var(--input-background)", fontSize: "13px", color: "var(--foreground)" }}>
                      {setting.options.map(o => <option key={o} value={o}>{o}</option>)}
                    </select>
                  </div>
                ))}
              </div>

              <div className="mt-6 p-4 rounded-xl" style={{ background: "var(--muted)" }}>
                <p style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>
                  <strong style={{ color: "var(--foreground)" }}>Versão do Sistema:</strong> SAGA v2.4.1 · Build 2025.03.01
                </p>
              </div>
            </div>
          )}

          {activeTab === "transferencia" && (currentUser?.role === "coordenacao" || currentUser?.role === "orientador") && (
            <div className="rounded-2xl p-6" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
              <h2 style={{ fontSize: "17px", fontWeight: 700, color: "var(--foreground)", marginBottom: "20px" }}>Transferir coordenação</h2>

              {currentUser?.role === "coordenacao" && (
                <div className="space-y-5">
                  {pendingTransfer ? (
                    <div className="p-4 rounded-xl bg-[var(--muted)] border border-[var(--border)]">
                      <p className="text-sm font-bold text-[var(--foreground)]">Transferência pendente</p>
                      <p className="text-xs text-[var(--muted-foreground)] mt-1">
                        Convite enviado para {advisors.find((advisor) => advisor.uid === pendingTransfer.successor_uid)?.nome ?? pendingTransfer.successor_uid}.
                      </p>
                      <button
                        type="button"
                        disabled={loading}
                        onClick={() => handleCancelTransfer(pendingTransfer.id)}
                        className="mt-4 inline-flex items-center gap-2 rounded-xl px-4 py-2 bg-red-50 text-red-700 font-semibold text-sm disabled:opacity-60"
                      >
                        <Ban size={15} /> Cancelar transferência
                      </button>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 lg:grid-cols-[1fr_auto] gap-3 items-end">
                      <div>
                        <label className="block text-xs font-semibold mb-1.5 text-[var(--muted-foreground)]">Orientador sucessor</label>
                        <select
                          value={selectedSuccessorUid}
                          onChange={(event) => setSelectedSuccessorUid(event.target.value)}
                          className="w-full rounded-xl px-4 py-2.5 bg-[var(--input-background)] border border-[var(--border)] text-sm outline-none"
                        >
                          <option value="">Selecione um orientador</option>
                          {advisors.filter((advisor) => advisor.uid).map((advisor) => (
                            <option key={advisor.id} value={advisor.uid ?? ""}>
                              {advisor.nome} · {advisor.email}
                            </option>
                          ))}
                        </select>
                      </div>
                      <button
                        type="button"
                        disabled={loading || !selectedSuccessorUid}
                        onClick={handleStartTransfer}
                        className="inline-flex items-center justify-center gap-2 rounded-xl px-5 py-2.5 bg-[#123C7A] text-white font-semibold text-sm disabled:opacity-60"
                      >
                        <Send size={15} /> Iniciar
                      </button>
                    </div>
                  )}

                  <div className="space-y-3">
                    {transfers.map((transfer) => (
                      <div key={transfer.id} className="flex items-center justify-between p-3 rounded-xl bg-[var(--muted)] border border-[var(--border)]">
                        <div>
                          <p className="text-sm font-bold text-[var(--foreground)]">{transfer.status}</p>
                          <p className="text-xs text-[var(--muted-foreground)]">Sucessor: {advisors.find((advisor) => advisor.uid === transfer.successor_uid)?.nome ?? transfer.successor_uid}</p>
                        </div>
                        <span className="text-xs text-[var(--muted-foreground)]">{new Date(transfer.created_at).toLocaleDateString("pt-BR")}</span>
                      </div>
                    ))}
                    {!loading && transfers.length === 0 && (
                      <p className="text-sm text-[var(--muted-foreground)]">Nenhuma transferência registrada.</p>
                    )}
                  </div>
                </div>
              )}

              {currentUser?.role === "orientador" && (
                <div className="space-y-3">
                  {transfers.map((transfer) => (
                    <div key={transfer.id} className="p-4 rounded-xl bg-[var(--muted)] border border-[var(--border)]">
                      <p className="text-sm font-bold text-[var(--foreground)]">Convite pendente</p>
                      <p className="text-xs text-[var(--muted-foreground)] mt-1">Você foi convidado para assumir a coordenação deste programa.</p>
                      <div className="mt-4 flex flex-wrap gap-3">
                        <button
                          type="button"
                          disabled={loading}
                          onClick={() => handleAcceptTransfer(transfer.id)}
                          className="inline-flex items-center gap-2 rounded-xl px-4 py-2 bg-[#1F8A70] text-white font-semibold text-sm disabled:opacity-60"
                        >
                          <CheckCircle2 size={15} /> Aceitar
                        </button>
                        <button
                          type="button"
                          disabled={loading}
                          onClick={() => handleRejectTransfer(transfer.id)}
                          className="inline-flex items-center gap-2 rounded-xl px-4 py-2 bg-red-50 text-red-700 font-semibold text-sm disabled:opacity-60"
                        >
                          <XCircle size={15} /> Rejeitar
                        </button>
                      </div>
                    </div>
                  ))}
                  {!loading && transfers.length === 0 && (
                    <p className="text-sm text-[var(--muted-foreground)]">Nenhum convite pendente.</p>
                  )}
                </div>
              )}
            </div>
          )}

          {activeTab === "programa" && currentUser?.role === "coordenacao" && (
            <div className="space-y-6">
              <div className="rounded-2xl p-6" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
                <h2 style={{ fontSize: "17px", fontWeight: 700, color: "var(--foreground)", marginBottom: "24px" }}>Regras Acadêmicas do Programa</h2>
                
                {loading && !programConfig ? (
                  <p>Carregando...</p>
                ) : (
                  <form onSubmit={handleSaveConfig} className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                    <div>
                      <label className="block text-xs font-semibold mb-1.5 opacity-70">Mínimo Créditos Básicos</label>
                      <input 
                        type="number"
                        value={programConfig?.creditos_grupo_basico_min || 0}
                        onChange={e => setProgramConfig(prev => ({...(prev ?? DEFAULT_PROGRAM_CONFIG), creditos_grupo_basico_min: parseInt(e.target.value)}))}
                        className="w-full rounded-xl px-4 py-2.5 bg-[var(--muted)] border border-[var(--border)]"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold mb-1.5 opacity-70">Mínimo Créditos Específicos</label>
                      <input 
                        type="number"
                        value={programConfig?.creditos_grupo_especifico_min || 0}
                        onChange={e => setProgramConfig(prev => ({...(prev ?? DEFAULT_PROGRAM_CONFIG), creditos_grupo_especifico_min: parseInt(e.target.value)}))}
                        className="w-full rounded-xl px-4 py-2.5 bg-[var(--muted)] border border-[var(--border)]"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold mb-1.5 opacity-70">Máximo Créditos Tecnológicos</label>
                      <input 
                        type="number"
                        value={programConfig?.creditos_grupo_tecnologico_max || 0}
                        onChange={e => setProgramConfig(prev => ({...(prev ?? DEFAULT_PROGRAM_CONFIG), creditos_grupo_tecnologico_max: parseInt(e.target.value)}))}
                        className="w-full rounded-xl px-4 py-2.5 bg-[var(--muted)] border border-[var(--border)]"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold mb-1.5 opacity-70">Mínimo Total de Créditos</label>
                      <input 
                        type="number"
                        value={programConfig?.creditos_total_min || 0}
                        onChange={e => setProgramConfig(prev => ({...(prev ?? DEFAULT_PROGRAM_CONFIG), creditos_total_min: parseInt(e.target.value)}))}
                        className="w-full rounded-xl px-4 py-2.5 bg-[var(--muted)] border border-[var(--border)]"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold mb-1.5 opacity-70">Meses até Qualificação</label>
                      <input 
                        type="number"
                        value={programConfig?.meses_ate_qualificacao || 0}
                        onChange={e => setProgramConfig(prev => ({...(prev ?? DEFAULT_PROGRAM_CONFIG), meses_ate_qualificacao: parseInt(e.target.value)}))}
                        className="w-full rounded-xl px-4 py-2.5 bg-[var(--muted)] border border-[var(--border)]"
                      />
                    </div>
                    
                    <div className="col-span-full">
                      <button type="submit" disabled={loading} className="flex items-center gap-2 rounded-xl px-5 py-2.5 bg-[#123C7A] text-white font-semibold text-sm">
                        <Save size={15} /> {saved ? "Salvo!" : "Salvar Regras"}
                      </button>
                    </div>
                  </form>
                )}
              </div>

              <div className="rounded-2xl p-6" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
                <div className="flex items-center justify-between mb-6">
                  <h2 style={{ fontSize: "17px", fontWeight: 700, color: "var(--foreground)" }}>Níveis de Veículo</h2>
                </div>

                <div className="space-y-3">
                  {vehicleLevels.map((level) => (
                    <div key={level.id} className="flex items-center justify-between p-3 rounded-xl bg-[var(--muted)] border border-[var(--border)]">
                      <div>
                        <p className="text-sm font-bold">{level.nivel}</p>
                        <p className="text-xs opacity-60">Peso Multiplicador: {level.peso}</p>
                      </div>
                      <div className="flex items-center gap-3">
                        <button type="button" onClick={() => openEditVehicleModal(level)} title="Editar Peso">
                          <Edit size={16} className="text-blue-600" />
                        </button>
                      </div>
                    </div>
                  ))}
                  {vehicleLevels.length === 0 && (
                    <p className="text-sm opacity-60">Nenhum nível de veículo configurado.</p>
                  )}
                </div>
              </div>

              <div className="rounded-2xl p-6" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
                <div className="flex items-center justify-between mb-6">
                  <h2 style={{ fontSize: "17px", fontWeight: 700, color: "var(--foreground)" }}>Tipos de Atividade</h2>
                  <button onClick={openNewActivityModal} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#D4A017] text-white text-xs font-bold">
                    <Plus size={14} /> Novo Tipo
                  </button>
                </div>

                <div className="space-y-3">
                  {activityTypes.map(type => (
                    <div key={type.id} className="flex items-center justify-between p-3 rounded-xl bg-[var(--muted)] border border-[var(--border)]">
                      <div>
                        <p className="text-sm font-bold">{type.nome}</p>
                        <p className="text-xs opacity-60">{type.categoria} · {type.pontuacao_base} pts</p>
                      </div>
                      <div className="flex items-center gap-3">
                        <button onClick={() => openEditActivityModal(type)} title="Editar">
                          <Edit size={16} className="text-blue-600" />
                        </button>
                        <button onClick={() => type.id && handleToggleActivity(type.id)} title={type.ativo ? "Desativar" : "Ativar"}>
                          {type.ativo ? <CheckCircle2 size={18} className="text-green-600" /> : <XCircle size={18} className="text-red-500" />}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* MODAL TIPOS DE ATIVIDADE */}
      {isActivityModalOpen && currentActivity && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-[var(--card)] rounded-2xl w-full max-w-md p-6 border border-[var(--border)] shadow-xl relative">
            <h2 className="text-lg font-bold mb-4">{currentActivity.id ? "Editar Tipo de Atividade" : "Novo Tipo de Atividade"}</h2>
            <form onSubmit={handleSaveActivity} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold mb-1.5">Nome da Atividade</label>
                <input required type="text" value={currentActivity.nome} onChange={e => setCurrentActivity({...currentActivity, nome: e.target.value})} className="w-full rounded-xl px-4 py-2 border border-[var(--border)] bg-[var(--input-background)]" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold mb-1.5">Categoria</label>
                  <select required value={currentActivity.categoria} onChange={e => setCurrentActivity({...currentActivity, categoria: e.target.value})} className="w-full rounded-xl px-4 py-2 border border-[var(--border)] bg-[var(--input-background)]">
                    <option value="basico">Básico</option>
                    <option value="especifico">Específico</option>
                    <option value="tecnologico">Tecnológico</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold mb-1.5">Pontuação Base</label>
                  <input required type="number" step="0.1" value={currentActivity.pontuacao_base} onChange={e => setCurrentActivity({...currentActivity, pontuacao_base: parseFloat(e.target.value)})} className="w-full rounded-xl px-4 py-2 border border-[var(--border)] bg-[var(--input-background)]" />
                </div>
              </div>
              <div className="flex gap-4 mt-6">
                <button type="button" onClick={() => setIsActivityModalOpen(false)} className="flex-1 px-4 py-2 rounded-xl bg-[var(--muted)] text-[var(--foreground)] font-semibold">Cancelar</button>
                <button type="submit" className="flex-1 px-4 py-2 rounded-xl bg-[#123C7A] text-white font-semibold">Salvar</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL NÍVEIS DE VEÍCULO */}
      {isVehicleModalOpen && currentVehicle && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-[var(--card)] rounded-2xl w-full max-w-sm p-6 border border-[var(--border)] shadow-xl relative">
            <h2 className="text-lg font-bold mb-4">Editar Peso: Nível {currentVehicle.nivel}</h2>
            <form onSubmit={handleSaveVehicle} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold mb-1.5">Multiplicador de Peso</label>
                <input required type="number" step="0.1" value={currentVehicle.peso} onChange={e => setCurrentVehicle({...currentVehicle, peso: parseFloat(e.target.value)})} className="w-full rounded-xl px-4 py-2 border border-[var(--border)] bg-[var(--input-background)]" />
                <p className="text-xs text-[var(--muted-foreground)] mt-2">
                  Ex: Um peso de 1.5 aplicará 50% de bônus na pontuação base da atividade para produções neste veículo.
                </p>
              </div>
              <div className="flex gap-4 mt-6">
                <button type="button" onClick={() => setIsVehicleModalOpen(false)} className="flex-1 px-4 py-2 rounded-xl bg-[var(--muted)] text-[var(--foreground)] font-semibold">Cancelar</button>
                <button type="submit" className="flex-1 px-4 py-2 rounded-xl bg-[#123C7A] text-white font-semibold">Salvar</button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
