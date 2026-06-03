import { useApp } from "../../context/AppContext";
import { AlunoDashboard } from "./AlunoDashboard";
import { OrientadorDashboard } from "./OrientadorDashboard";
import { CoordDashboard } from "./CoordDashboard";

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
