interface StrengthLevel {
  score: number;
  label: string;
  color: string;
  bg: string;
  hint: string;
}

export function calcPasswordStrength(password: string): StrengthLevel {
  if (!password) return { score: 0, label: "", color: "#cbd5e1", bg: "#f1f5f9", hint: "" };

  let score = 0;
  const checks = {
    length8: password.length >= 8,
    length12: password.length >= 12,
    upper: /[A-Z]/.test(password),
    lower: /[a-z]/.test(password),
    number: /\d/.test(password),
    special: /[^A-Za-z0-9]/.test(password),
  };

  if (checks.length8) score++;
  if (checks.length12) score++;
  if (checks.upper && checks.lower) score++;
  if (checks.number) score++;
  if (checks.special) score++;

  const levels: StrengthLevel[] = [
    { score: 0, label: "", color: "#cbd5e1", bg: "#f1f5f9", hint: "" },
    { score: 1, label: "Muito fraca", color: "#ef4444", bg: "#fee2e2",
      hint: "Use pelo menos 8 caracteres" },
    { score: 2, label: "Fraca", color: "#f97316", bg: "#ffedd5",
      hint: "Adicione letras maiúsculas e números" },
    { score: 3, label: "Moderada", color: "#eab308", bg: "#fef9c3",
      hint: "Adicione caracteres especiais (!@#$%)" },
    { score: 4, label: "Forte", color: "#22c55e", bg: "#dcfce7",
      hint: "Senha boa! Quase perfeita" },
    { score: 5, label: "Muito forte", color: "#16a34a", bg: "#bbf7d0",
      hint: "Excelente! Senha muito segura" },
  ];

  const idx = Math.min(score, 5);
  return levels[idx];
}

interface PasswordStrengthProps {
  password: string;
}

export function PasswordStrength({ password }: PasswordStrengthProps) {
  const strength = calcPasswordStrength(password);

  if (!password) return null;

  const checks = [
    { label: "Mínimo 8 caracteres", ok: password.length >= 8 },
    { label: "Letra maiúscula (A–Z)", ok: /[A-Z]/.test(password) },
    { label: "Número (0–9)", ok: /\d/.test(password) },
    { label: "Caractere especial (!@#$%)", ok: /[^A-Za-z0-9]/.test(password) },
  ];

  return (
    <div className="mt-2 space-y-2">
      {/* Strength bar */}
      <div className="flex items-center gap-2">
        <div className="flex gap-1 flex-1">
          {[1, 2, 3, 4, 5].map((level) => (
            <div
              key={level}
              className="flex-1 rounded-full transition-all duration-300"
              style={{
                height: 5,
                background: strength.score >= level ? strength.color : "#e2e8f0",
              }}
            />
          ))}
        </div>
        {strength.label && (
          <span
            className="rounded-lg px-2 py-0.5 flex-shrink-0"
            style={{
              fontSize: "11px",
              fontWeight: 700,
              color: strength.color,
              background: strength.bg,
              minWidth: 80,
              textAlign: "center",
            }}
          >
            {strength.label}
          </span>
        )}
      </div>

      {/* Checklist */}
      <div className="grid grid-cols-2 gap-1">
        {checks.map((check) => (
          <div key={check.label} className="flex items-center gap-1.5">
            <div
              className="rounded-full flex-shrink-0 flex items-center justify-center"
              style={{
                width: 14,
                height: 14,
                background: check.ok ? "#dcfce7" : "#f1f5f9",
                border: `1.5px solid ${check.ok ? "#22c55e" : "#cbd5e1"}`,
                transition: "all 0.2s",
              }}
            >
              {check.ok && (
                <svg width="8" height="8" viewBox="0 0 8 8" fill="none">
                  <path d="M1.5 4L3 5.5L6.5 2" stroke="#16a34a" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )}
            </div>
            <span style={{
              fontSize: "11px",
              color: check.ok ? "#16a34a" : "#94a3b8",
              fontWeight: check.ok ? 600 : 400,
              transition: "color 0.2s",
            }}>
              {check.label}
            </span>
          </div>
        ))}
      </div>

      {strength.hint && (
        <p style={{ fontSize: "11px", color: strength.color, fontWeight: 500 }}>
          💡 {strength.hint}
        </p>
      )}
    </div>
  );
}
