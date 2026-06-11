import { AppProvider, useApp } from "./context/AppContext";
import { AppLayout } from "./components/layout/AppLayout";
import { LoginPage } from "./components/auth/LoginPage";
import { RegisterPage } from "./components/auth/RegisterPage";
import { PasswordRecoveryPage } from "./components/auth/PasswordRecoveryPage";
import { ChangePasswordPage } from "./components/auth/ChangePasswordPage";
import { FirstAccessPage } from "./components/auth/FirstAccessPage";
import { Dashboard } from "./components/dashboard/Dashboard";
import { StudentsPage } from "./components/students/StudentsPage";
import { AdvisorsPage } from "./components/advisors/AdvisorsPage";
import { WorkPlanPage } from "./components/workplan/WorkPlanPage";
import { ActivitiesPage } from "./components/activities/ActivitiesPage";
import { ProductionsPage } from "./components/productions/ProductionsPage";
import { ChecklistPage } from "./components/checklist/ChecklistPage";
import { ExtensionsPage } from "./components/extensions/ExtensionsPage";
import { ReportsPage } from "./components/reports/ReportsPage";
import { InferencePage } from "./components/inference/InferencePage";
import { AuditPage } from "./components/audit/AuditPage";
import { NotificationsPage } from "./components/notifications/NotificationsPage";
import { SettingsPage } from "./components/settings/SettingsPage";

function StudentDetailPage() {
  const { setCurrentPage, selectedStudentId } = useApp();
  return (
    <div>
      <button
        onClick={() => setCurrentPage("alunos")}
        className="flex items-center gap-2 mb-6 px-4 py-2 rounded-xl"
        style={{ background: "var(--card)", border: "1px solid var(--border)", color: "var(--foreground)", fontSize: "13px", fontWeight: 600 }}
      >
        ← Voltar para Alunos
      </button>
      <div className="rounded-2xl p-6" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
        <h1 style={{ color: "var(--foreground)", marginBottom: "8px" }}>Detalhes do Aluno</h1>
        <p style={{ color: "var(--muted-foreground)" }}>ID: {selectedStudentId}</p>
        <div className="mt-6 grid grid-cols-2 gap-4">
          {[
            { label: "Plano de Trabalho", color: "#123C7A" },
            { label: "Atividades Creditáveis", color: "#1F8A70" },
            { label: "Produções Científicas", color: "#D4A017" },
            { label: "Checklist de Conclusão", color: "#8b5cf6" },
          ].map((item) => (
            <div key={item.label} className="rounded-xl p-4" style={{ background: `${item.color}10`, border: `1px solid ${item.color}30` }}>
              <p style={{ fontWeight: 600, color: item.color }}>{item.label}</p>
              <p style={{ fontSize: "12px", color: "var(--muted-foreground)", marginTop: "4px" }}>Clique para visualizar</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function PageRouter() {
  const { currentPage } = useApp();
  switch (currentPage) {
    case "dashboard": return <Dashboard />;
    case "alunos": return <StudentsPage />;
    case "aluno-detail": return <StudentDetailPage />;
    case "orientadores": return <AdvisorsPage />;
    case "plano-trabalho": return <WorkPlanPage />;
    case "atividades": return <ActivitiesPage />;
    case "producoes": return <ProductionsPage />;
    case "checklist": return <ChecklistPage />;
    case "prorrogacoes": return <ExtensionsPage />;
    case "relatorios": return <ReportsPage />;
    case "inferencia": return <InferencePage />;
    case "auditoria": return <AuditPage />;
    case "notificacoes": return <NotificationsPage />;
    case "configuracoes": return <SettingsPage />;
    default: return <Dashboard />;
  }
}

function AppContent() {
  const { currentPage, loading } = useApp();

  // Enquanto o estado de autenticação inicial não resolve, evita o flash da
  // tela de login para usuários já autenticados.
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen"
        style={{ background: "var(--background)", color: "var(--muted-foreground)", fontSize: "14px" }}>
        Carregando…
      </div>
    );
  }

  const isAuthPage = ["login", "register", "password-recovery", "change-password", "first-access"].includes(currentPage);

  if (isAuthPage) {
    switch (currentPage) {
      case "login": return <LoginPage />;
      case "register": return <RegisterPage />;
      case "password-recovery": return <PasswordRecoveryPage />;
      case "change-password": return <ChangePasswordPage />;
      case "first-access": return <FirstAccessPage />;
      default: return <LoginPage />;
    }
  }

  return (
    <AppLayout>
      <PageRouter />
    </AppLayout>
  );
}

export default function App() {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
}
