import type { ChecklistResponse, RequisitoStatus } from "@/api/checklistApi";
import { downloadBlob, sanitizeFileName } from "@/utils/exportData";

type RequirementRow = {
  nome: string;
  descricao: string;
  status: RequisitoStatus;
  atual: string;
  exigido: string;
  unidade?: string;
  comprovanteUrl?: string | null;
  observacoes?: string;
};

const PAGE_WIDTH = 595;
const PAGE_HEIGHT = 842;
const MARGIN = 42;
const CONTENT_WIDTH = PAGE_WIDTH - MARGIN * 2;
const LINE_HEIGHT = 14;

const STATUS_LABEL: Record<RequisitoStatus, string> = {
  cumprido: "Cumprido",
  pendente: "Pendente",
  em_risco: "Em risco",
};

function formatDateTime(value?: string | null): string {
  const date = value ? new Date(value) : new Date();
  if (Number.isNaN(date.getTime())) return value ?? "Nao informado";
  return date.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

function formatStatus(value?: string | null): string {
  if (!value) return "Nao informado";
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

// O status e a fonte de verdade: a coordenacao pode salvar a data sem aprovar o
// requisito, e nesse caso o relatorio nao pode declara-lo aprovado (issue #342).
function academicFactDetail(
  status: RequisitoStatus,
  date: string | null | undefined,
  labels: { cumprido: string; naoCumpridoComData: string; semData: string },
): string {
  if (status === "cumprido") return date ? `${labels.cumprido} em ${formatDateTime(date)}` : labels.cumprido;
  if (date) return `Registrada em ${formatDateTime(date)} - ${labels.naoCumpridoComData}`;
  return labels.semData;
}

function buildRequirements(data: ChecklistResponse): RequirementRow[] {
  const r = data.requisitos;
  return [
    {
      nome: "Creditos minimos totais",
      descricao: r.creditos_minimos.descricao,
      status: r.creditos_minimos.status,
      atual: String(r.creditos_minimos.obtidos),
      exigido: String(r.creditos_minimos.minimo),
      unidade: "creditos",
    },
    {
      nome: "Creditos - grupo basico",
      descricao: r.creditos_grupo_basico.descricao,
      status: r.creditos_grupo_basico.status,
      atual: String(r.creditos_grupo_basico.obtidos),
      exigido: String(r.creditos_grupo_basico.minimo),
      unidade: "creditos",
    },
    {
      nome: "Creditos - grupo especifico",
      descricao: r.creditos_grupo_especifico.descricao,
      status: r.creditos_grupo_especifico.status,
      atual: String(r.creditos_grupo_especifico.obtidos),
      exigido: String(r.creditos_grupo_especifico.minimo),
      unidade: "creditos",
    },
    {
      nome: "Creditos - grupo tecnologico",
      descricao: r.creditos_grupo_tecnologico.descricao,
      status: r.creditos_grupo_tecnologico.status,
      atual: String(r.creditos_grupo_tecnologico.obtidos),
      exigido: `max ${r.creditos_grupo_tecnologico.maximo}`,
      unidade: "creditos",
    },
    {
      nome: "Proficiencia",
      descricao: "Proficiencia em lingua estrangeira",
      status: r.proficiencia.status,
      atual: academicFactDetail(r.proficiencia.status, r.proficiencia.data_comprovacao, {
        cumprido: "Comprovada",
        naoCumpridoComData: "nao comprovada",
        semData: "Nao comprovada",
      }),
      exigido: "Comprovada",
      comprovanteUrl: r.proficiencia.comprovante_url,
    },
    {
      nome: "Qualificacao",
      descricao: "Aprovacao no exame de qualificacao",
      status: r.qualificacao.status,
      atual: academicFactDetail(r.qualificacao.status, r.qualificacao.data_aprovacao, {
        cumprido: "Aprovada",
        naoCumpridoComData: "nao aprovada",
        semData: "Pendente",
      }),
      exigido: "Aprovada",
      comprovanteUrl: r.qualificacao.comprovante_url,
    },
    {
      nome: "Producao bibliografica",
      descricao: "Producao bibliografica validada",
      status: r.producao_validada.status,
      atual: String(r.producao_validada.quantidade_aprovadas),
      exigido: "1 ou mais",
      unidade: "producao validada",
    },
    {
      nome: "Plano de trabalho",
      descricao: "Conclusao das etapas de nao-defesa",
      status: r.plano_concluido.status,
      atual: String(r.plano_concluido.tasks_concluidas),
      exigido: String(r.plano_concluido.tasks_total_nao_defesa),
      unidade: "etapas concluidas",
    },
  ];
}

function pdfText(value: string): string {
  return value
    .replace(/[“”]/g, '"')
    .replace(/[‘’]/g, "'")
    .replace(/[–—]/g, "-")
    .replace(/…/g, "...")
    .replace(/[^\x09\x0a\x0d\x20-\xff]/g, "");
}

function escapePdf(value: string): string {
  return pdfText(value).replace(/\\/g, "\\\\").replace(/\(/g, "\\(").replace(/\)/g, "\\)");
}

function wrapText(text: string, maxChars: number): string[] {
  const words = pdfText(text).split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let current = "";
  for (const word of words) {
    if (!current) {
      current = word;
    } else if (`${current} ${word}`.length <= maxChars) {
      current = `${current} ${word}`;
    } else {
      lines.push(current);
      current = word;
    }
  }
  if (current) lines.push(current);
  return lines.length ? lines : [""];
}

class PdfBuilder {
  private pages: string[] = [""];
  private y = PAGE_HEIGHT - MARGIN;

  private get pageIndex(): number {
    return this.pages.length - 1;
  }

  private ensureSpace(height: number): void {
    if (this.y - height < MARGIN) {
      this.pages.push("");
      this.y = PAGE_HEIGHT - MARGIN;
    }
  }

  private append(command: string): void {
    this.pages[this.pageIndex] += `${command}\n`;
  }

  text(value: string, size = 10, options: { bold?: boolean; indent?: number; gapAfter?: number } = {}): void {
    const maxChars = Math.max(28, Math.floor((CONTENT_WIDTH - (options.indent ?? 0)) / (size * 0.48)));
    const lines = wrapText(value, maxChars);
    this.ensureSpace(lines.length * LINE_HEIGHT + (options.gapAfter ?? 0));
    for (const line of lines) {
      this.append(`BT /${options.bold ? "F2" : "F1"} ${size} Tf ${MARGIN + (options.indent ?? 0)} ${this.y} Td (${escapePdf(line)}) Tj ET`);
      this.y -= LINE_HEIGHT;
    }
    this.y -= options.gapAfter ?? 0;
  }

  rule(): void {
    this.ensureSpace(12);
    this.append(`${MARGIN} ${this.y} m ${PAGE_WIDTH - MARGIN} ${this.y} l S`);
    this.y -= 12;
  }

  gap(value = 8): void {
    this.ensureSpace(value);
    this.y -= value;
  }

  build(): Blob {
    const objects: string[] = [
      "<< /Type /Catalog /Pages 2 0 R >>",
      `<< /Type /Pages /Kids [${this.pages.map((_, index) => `${3 + index * 2} 0 R`).join(" ")}] /Count ${this.pages.length} >>`,
    ];

    this.pages.forEach((content, index) => {
      const pageObjectId = 3 + index * 2;
      const contentObjectId = pageObjectId + 1;
      objects.push(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${PAGE_WIDTH} ${PAGE_HEIGHT}] /Resources << /Font << /F1 ${3 + this.pages.length * 2} 0 R /F2 ${4 + this.pages.length * 2} 0 R >> >> /Contents ${contentObjectId} 0 R >>`);
      objects.push(`<< /Length ${content.length} >>\nstream\n${content}endstream`);
    });

    objects.push("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>");
    objects.push("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>");

    let pdf = "%PDF-1.4\n";
    const offsets = [0];
    objects.forEach((object, index) => {
      offsets.push(pdf.length);
      pdf += `${index + 1} 0 obj\n${object}\nendobj\n`;
    });
    const xrefStart = pdf.length;
    pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
    for (let i = 1; i < offsets.length; i += 1) pdf += `${String(offsets[i]).padStart(10, "0")} 00000 n \n`;
    pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefStart}\n%%EOF`;

    const bytes = new Uint8Array(pdf.length);
    for (let i = 0; i < pdf.length; i += 1) bytes[i] = pdf.charCodeAt(i) & 0xff;
    return new Blob([bytes], { type: "application/pdf" });
  }
}

export function exportChecklistPdf(data: ChecklistResponse): void {
  const pdf = new PdfBuilder();
  const generatedAt = new Date();
  const requirements = buildRequirements(data);
  const risks = data.riscos_detectados.length > 0 ? data.riscos_detectados : ["Nenhum risco identificado."];

  pdf.text("SAGA - Checklist de Integralizacao", 18, { bold: true, gapAfter: 2 });
  pdf.text(`Gerado em ${formatDateTime(generatedAt.toISOString())}`, 9, { gapAfter: 4 });
  pdf.rule();

  pdf.text("Identificacao do aluno", 13, { bold: true });
  pdf.text(`Nome: ${data.student_nome}`);
  pdf.text(`Matricula/ID: ${data.student_id}`);
  pdf.text("Programa: Nao informado");
  pdf.text("Orientador: Nao informado", 10, { gapAfter: 8 });

  pdf.text("Situacao academica", 13, { bold: true });
  pdf.text(`Situacao registrada: ${formatStatus(data.situacao_registrada)}`);
  pdf.text(`Situacao inferida: ${formatStatus(data.situacao_inferida)}`);
  pdf.text(`Ultima atualizacao do checklist: ${formatDateTime(data.timestamp)}`);
  pdf.text(`Conflito de situacao: ${data.conflito_situacao ? "Sim" : "Nao"}`);
  pdf.text(`Apto para defesa: ${data.apto_defesa ? "Sim" : "Nao"}`, 10, { gapAfter: 8 });

  pdf.text("Requisitos", 13, { bold: true });
  requirements.forEach((requirement, index) => {
    pdf.text(`${index + 1}. ${requirement.nome}`, 11, { bold: true, gapAfter: 1 });
    pdf.text(`Descricao: ${requirement.descricao}`, 9, { indent: 12 });
    pdf.text(`Status: ${STATUS_LABEL[requirement.status]}`, 9, { indent: 12 });
    pdf.text(`Valor atual: ${requirement.atual}`, 9, { indent: 12 });
    pdf.text(`Valor exigido: ${requirement.exigido}`, 9, { indent: 12 });
    if (requirement.unidade) pdf.text(`Unidade: ${requirement.unidade}`, 9, { indent: 12 });
    if (requirement.comprovanteUrl) pdf.text(`Comprovante: ${requirement.comprovanteUrl}`, 9, { indent: 12 });
    if (requirement.observacoes) pdf.text(`Observacoes: ${requirement.observacoes}`, 9, { indent: 12 });
    pdf.gap(6);
  });

  pdf.text("Riscos academicos", 13, { bold: true });
  risks.forEach((risk) => pdf.text(`- ${formatStatus(risk)}`, 10, { indent: 8 }));

  const fileName = `checklist-integralizacao-${sanitizeFileName(data.student_nome)}.pdf`;
  downloadBlob(pdf.build(), fileName);
}
