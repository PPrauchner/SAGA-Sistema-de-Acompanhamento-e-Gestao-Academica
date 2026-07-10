import { lazy, Suspense } from "react";

import { AppProvider, useApp } from "./context/AppContext";
import { PrivateRoute, isAuthPage } from "./router/PrivateRoute";
import { AppLayout } from "./components/layout/AppLayout";
import { LoginPage } from "./components/auth/LoginPage";
import { RegisterPage } from "./components/auth/RegisterPage";
import { PasswordRecoveryPage } from "./components/auth/PasswordRecoveryPage";
import { FirstAccessPage } from "./components/auth/FirstAccessPage";
import { ProfileUnavailablePage } from "./components/auth/ProfileUnavailablePage";

// Páginas autenticadas carregadas sob demanda: cada uma vira um chunk próprio,
// mantendo o recharts (puxado pelo Dashboard) e o restante fora do bundle
// inicial de login. As páginas usam named exports, daí o .then(...) mapeando
// para o `default` que o React.lazy espera.
const Dashboard = lazy(() => import("./components/dashboard/Dashboard").then((m) => ({ default: m.Dashboard })));
const StudentsPage = lazy(() => import("./components/students/StudentsPage").then((m) => ({ default: m.StudentsPage })));
const StudentDetailPage = lazy(() => import("./components/students/StudentDetailPage").then((m) => ({ default: m.StudentDetailPage })));
const AdvisorsPage = lazy(() => import("./components/advisors/AdvisorsPage").then((m) => ({ default: m.AdvisorsPage })));
const WorkPlanPage = lazy(() => import("./components/workplan/WorkPlanPage").then((m) => ({ default: m.WorkPlanPage })));
const ActivitiesPage = lazy(() => import("./components/activities/ActivitiesPage").then((m) => ({ default: m.ActivitiesPage })));
const ProductionsPage = lazy(() => import("./components/productions/ProductionsPage").then((m) => ({ default: m.ProductionsPage })));
const ChecklistPage = lazy(() => import("./components/checklist/ChecklistPage").then((m) => ({ default: m.ChecklistPage })));
const SolicitacoesPage = lazy(() => import("./components/solicitacoes/SolicitacoesPage").then((m) => ({ default: m.SolicitacoesPage })));
const RequestsPage = lazy(() => import("./components/requests/RequestsPage").then((m) => ({ default: m.RequestsPage })));
const RegistrationRequestsPage = lazy(() => import("./components/registration-requests/RegistrationRequestsPage").then((m) => ({ default: m.RegistrationRequestsPage })));

const ReportsPage = lazy(() => import("./components/reports/ReportsPage").then((m) => ({ default: m.ReportsPage })));
const InferencePage = lazy(() => import("./components/inference/InferencePage").then((m) => ({ default: m.InferencePage })));
const AuditPage = lazy(() => import("./components/audit/AuditPage").then((m) => ({ default: m.AuditPage })));
const NotificationsPage = lazy(() => import("./components/notifications/NotificationsPage").then((m) => ({ default: m.NotificationsPage })));
const SettingsPage = lazy(() => import("./components/settings/SettingsPage").then((m) => ({ default: m.SettingsPage })));

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
    case "solicitacoes": return <RequestsPage />;
    case "prorrogacoes": return <SolicitacoesPage />;
    case "registration-requests": return <RegistrationRequestsPage />;
    case "relatorios": return <ReportsPage />;
    case "inferencia": return <InferencePage />;
    case "auditoria": return <AuditPage />;
    case "notificacoes": return <NotificationsPage />;
    case "configuracoes": return <SettingsPage />;
    default: return <Dashboard />;
  }
}

// Fallback exibido enquanto o chunk da página sob demanda é baixado.
function PageLoading() {
  return (
    <div
      className="flex items-center justify-center py-24"
      style={{ color: "var(--muted-foreground)", fontSize: "14px" }}
    >
      Carregando…
    </div>
  );
}

function FullPageLoading() {
  return (
    <div className="flex items-center justify-center min-h-screen"
      style={{ background: "var(--background)", color: "var(--muted-foreground)", fontSize: "14px" }}>
      Carregando…
    </div>
  );
}

function PageLoadingSkeleton() {
  return (
    <div className="p-2 md:p-0 animate-pulse">
      <div className="h-8 rounded w-1/4 mb-6" style={{ background: "var(--border)" }}></div>
      <div className="rounded-2xl p-6" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
        <div className="h-6 rounded w-1/3 mb-4" style={{ background: "var(--border)" }}></div>
        <div className="h-4 rounded w-1/2 mb-8" style={{ background: "var(--border)" }}></div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-24 rounded-xl" style={{ background: "var(--border)" }}></div>
          ))}
        </div>
      </div>
    </div>
  );
}

function AppContent() {
  const { currentPage, profileUnavailable, profileLoading } = useApp();

  // Sessão válida, mas perfil indisponível (GET /auth/me falhou): estado degradado
  // com retry. Precede a checagem de página de auth para não cair no login mesmo que
  // currentPage ainda seja "login". O PrivateRoute suprime o redirect neste estado.
  if (profileUnavailable) {
    return <ProfileUnavailablePage />;
  }

  if (isAuthPage(currentPage)) {
    switch (currentPage) {
      case "login": return <LoginPage />;
      case "register": return <RegisterPage />;
      case "password-recovery": return <PasswordRecoveryPage />;
      case "first-access": return <FirstAccessPage />;
      default: return <LoginPage />;
    }
  }

  return (
    <AppLayout>
      {profileLoading ? (
        <PageLoadingSkeleton />
      ) : (
        <Suspense fallback={<PageLoading />}>
          <PageRouter />
        </Suspense>
      )}
    </AppLayout>
  );
}

export default function App() {
  return (
    <AppProvider>
      <PrivateRoute loadingFallback={<FullPageLoading />}>
        <AppContent />
      </PrivateRoute>
    </AppProvider>
  );
}
