/**
 * Validação de intervalo de datas no frontend (issue #197).
 *
 * Espelha os validators Pydantic do backend para dar feedback imediato:
 * - Mínimo: ano 2000 (datas anteriores são consideradas irreais).
 * - Máximo: depende da semântica do campo (ver `allowFuture`).
 */

const ANO_MINIMO = 2000;
const ANOS_MAXIMOS_FUTURO = 10;

export interface DateRangeOptions {
  /**
   * `true` para campos que descrevem uma data futura (ex.: novo prazo de
   * prorrogação) — aceita até hoje + 10 anos.
   * `false` para eventos já ocorridos (ex.: data de realização de atividade
   * ou produção) — o máximo é a data de hoje, sem futuro.
   */
  allowFuture: boolean;
}

/**
 * Converte o valor de um `<input type="date">` ("YYYY-MM-DD") em `Date` local
 * ao meio-dia, evitando deslocamento de dia por fuso horário. Retorna `null`
 * para formato inválido (ex.: ano com 5 dígitos) ou data impossível
 * (ex.: 31/02), que o construtor `Date` silenciosamente "rolaria".
 */
function parseInputDate(value: string): Date | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return null;
  const ano = Number(match[1]);
  const mes = Number(match[2]);
  const dia = Number(match[3]);
  const data = new Date(ano, mes - 1, dia, 12, 0, 0);
  if (data.getFullYear() !== ano || data.getMonth() !== mes - 1 || data.getDate() !== dia) {
    return null;
  }
  return data;
}

/**
 * Retorna uma mensagem de erro se a data estiver fora do intervalo aceito, ou
 * `null` se for válida. Valor vazio retorna `null` — a obrigatoriedade do campo
 * é responsabilidade da validação de submit, não desta função.
 */
export function validateReasonableDate(value: string, options: DateRangeOptions): string | null {
  if (!value) return null;
  const data = parseInputDate(value);
  if (!data) return "Data inválida.";
  if (data.getFullYear() < ANO_MINIMO) {
    return `Data não pode ser anterior a ${ANO_MINIMO}.`;
  }
  const hoje = new Date();
  hoje.setHours(12, 0, 0, 0);
  if (options.allowFuture) {
    const maximo = new Date(hoje);
    maximo.setFullYear(hoje.getFullYear() + ANOS_MAXIMOS_FUTURO);
    if (data > maximo) {
      return `Data não pode ser mais de ${ANOS_MAXIMOS_FUTURO} anos no futuro.`;
    }
  } else if (data > hoje) {
    return "Data não pode estar no futuro.";
  }
  return null;
}
