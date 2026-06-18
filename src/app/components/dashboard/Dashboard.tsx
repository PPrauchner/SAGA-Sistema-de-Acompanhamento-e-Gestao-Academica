import { lazy } from "react";

import { useApp } from "../../context/AppContext";

// Cada dashboard de papel vira um chunk próprio: o usuário baixa só o do seu
// papel, em vez dos três juntos (cada um ~1.000 linhas + recharts). O carregamento
// sob demanda é coberto pelo <Suspense> que envolve o PageRouter em App.tsx.
const AlunoDashboard = lazy(() => import("./AlunoDashboard").then((m) => ({ default: m.AlunoDashboard })));
const OrientadorDashboard = lazy(() => import("./OrientadorDashboard").then((m) => ({ default: m.OrientadorDashboard })));
const CoordDashboard = lazy(() => import("./CoordDashboard").then((m) => ({ default: m.CoordDashboard })));

export function Dashboard() {
  const { currentUser } = useApp();

  return (
    <div>
      {currentUser?.role === "coordenacao" && <CoordDashboard />}
      {currentUser?.role === "orientador" && <OrientadorDashboard />}
      {currentUser?.role === "aluno" && <AlunoDashboard />}
    </div>
  );
}
