/**
 * Seção de configuração dos pesos Qualis versionados (coordenação).
 *
 * Permite ao coordenador definir o peso de cada nível Qualis (A1–A8 + SC) do próprio
 * programa. Salvar cria uma nova versão (não sobrescreve a anterior) e exibe o histórico
 * de versões — quem alterou e quando (US-VQ02/VQ03, ADR-0003).
 */

import { useEffect, useState } from "react";
import { Save, History } from "lucide-react";
import { toast } from "sonner";

import { useAuth } from "@/hooks/useAuth";
import {
  qualisWeightsApi,
  QUALIS_LEVELS,
  type QualisWeights,
  type QualisWeightsVersion,
} from "@/api/qualisWeightsApi";

function _emptyWeights(): QualisWeights {
  return Object.fromEntries(QUALIS_LEVELS.map((nivel) => [nivel, 0]));
}

function _formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString("pt-BR");
}

export function QualisWeightsSection() {
  const { token } = useAuth();
  const [weights, setWeights] = useState<QualisWeights>(_emptyWeights);
  const [history, setHistory] = useState<QualisWeightsVersion[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!token) return;
    let active = true;
    setLoading(true);
    Promise.all([qualisWeightsApi.getActive(token), qualisWeightsApi.getHistory(token)])
      .then(([active_weights, versions]) => {
        if (!active) return;
        setWeights({ ..._emptyWeights(), ...active_weights });
        setHistory(versions);
      })
      .catch(() => toast.error("Erro ao carregar pesos Qualis"))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [token]);

  const handleChange = (nivel: string, value: string) => {
    setWeights((prev) => ({ ...prev, [nivel]: parseFloat(value) || 0 }));
  };

  const handleSave = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!token) return;
    setSaving(true);
    try {
      await qualisWeightsApi.setWeights(token, weights);
      const versions = await qualisWeightsApi.getHistory(token);
      setHistory(versions);
      toast.success("Nova versão de pesos publicada");
    } catch {
      toast.error("Erro ao salvar pesos Qualis");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-2xl p-6" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
      <h2 style={{ fontSize: "17px", fontWeight: 700, color: "var(--foreground)", marginBottom: "8px" }}>
        Pesos Qualis (versionados)
      </h2>
      <p style={{ fontSize: "13px", color: "var(--muted-foreground)", marginBottom: "20px" }}>
        Peso de cada nível usado na pontuação ponderada de produções (RL05). Salvar cria uma
        nova versão; produções já publicadas mantêm o peso vigente na data de publicação.
      </p>

      {loading ? (
        <p style={{ color: "var(--muted-foreground)" }}>Carregando...</p>
      ) : (
        <form onSubmit={handleSave}>
          <div className="grid grid-cols-3 sm:grid-cols-5 gap-4">
            {QUALIS_LEVELS.map((nivel) => (
              <div key={nivel}>
                <label className="block text-xs font-semibold mb-1.5 opacity-70">{nivel}</label>
                <input
                  type="number"
                  step="0.05"
                  min="0"
                  value={weights[nivel] ?? 0}
                  onChange={(e) => handleChange(nivel, e.target.value)}
                  className="w-full rounded-xl px-3 py-2 bg-[var(--muted)] border border-[var(--border)]"
                />
              </div>
            ))}
          </div>
          <button
            type="submit"
            disabled={saving}
            className="mt-6 flex items-center gap-2 rounded-xl px-5 py-2.5 bg-[#123C7A] text-white font-semibold text-sm disabled:opacity-60"
          >
            <Save size={15} /> {saving ? "Salvando..." : "Salvar nova versão"}
          </button>
        </form>
      )}

      <div className="mt-8">
        <div className="flex items-center gap-2 mb-4">
          <History size={16} className="text-[var(--muted-foreground)]" />
          <h3 style={{ fontSize: "14px", fontWeight: 700, color: "var(--foreground)" }}>Histórico de versões</h3>
        </div>
        <div className="space-y-3">
          {history.map((version) => (
            <div key={version.id} className="p-3 rounded-xl bg-[var(--muted)] border border-[var(--border)]">
              <div className="flex items-center justify-between">
                <p className="text-sm font-bold text-[var(--foreground)]">
                  Vigente desde {_formatDate(version.vigente_desde)}
                </p>
                <span className="text-xs text-[var(--muted-foreground)]">
                  por {version.alterado_por} · {_formatDate(version.alterado_em)}
                </span>
              </div>
              <p className="text-xs text-[var(--muted-foreground)] mt-1">
                {QUALIS_LEVELS.map((nivel) => `${nivel} ${version.pesos[nivel] ?? "—"}`).join(" · ")}
              </p>
            </div>
          ))}
          {!loading && history.length === 0 && (
            <p className="text-sm text-[var(--muted-foreground)]">Nenhuma versão registrada ainda.</p>
          )}
        </div>
      </div>
    </div>
  );
}
