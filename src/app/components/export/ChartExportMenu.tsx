import { useState, type RefObject } from "react";
import { Download, FileBadge, FileImage, FileSpreadsheet, Loader2, Table } from "lucide-react";
import { exportChartAsPdf, exportChartAsPng } from "@/utils/exportChart";
import { downloadBlob, sanitizeFileName, toCsv, toXlsx, type ExportColumn } from "@/utils/exportData";

type ExportFormat = "png" | "pdf" | "csv" | "xlsx";

interface ChartExportMenuProps<T> {
  title: string;
  fileName?: string;
  chartRef: RefObject<HTMLElement>;
  data: T[];
  columns: ExportColumn<T>[];
}

const OPTIONS: Array<{ format: ExportFormat; label: string; icon: typeof FileImage }> = [
  { format: "png", label: "PNG", icon: FileImage },
  { format: "pdf", label: "PDF", icon: FileBadge },
  { format: "csv", label: "CSV", icon: Table },
  { format: "xlsx", label: "Excel", icon: FileSpreadsheet },
];

export function ChartExportMenu<T>({ title, fileName, chartRef, data, columns }: ChartExportMenuProps<T>) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState<ExportFormat | null>(null);
  const [error, setError] = useState<string | null>(null);
  const baseName = sanitizeFileName(fileName || title);

  async function handleExport(format: ExportFormat) {
    setBusy(format);
    setError(null);
    try {
      if (data.length === 0) throw new Error("Não há dados disponíveis para exportação.");
      if (format === "png" || format === "pdf") {
        const element = chartRef.current;
        if (!element) throw new Error("Gráfico indisponível para exportação.");
        if (format === "png") await exportChartAsPng(element, `${baseName}.png`);
        else await exportChartAsPdf(element, title, `${baseName}.pdf`);
      } else if (format === "csv") {
        downloadBlob(new Blob([toCsv(data, columns)], { type: "text/csv;charset=utf-8" }), `${baseName}.csv`);
      } else {
        downloadBlob(toXlsx(data, columns, title), `${baseName}.xlsx`);
      }
      setOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel exportar o grafico.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="relative" data-html2canvas-ignore="true">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 transition-colors"
        style={{ fontSize: "11px", fontWeight: 700, color: "#123C7A", background: "#eef3fc", border: "1px solid #c7d9f5" }}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Exportar ${title}`}
        disabled={busy !== null}
      >
        {busy ? <Loader2 size={12} className="animate-spin" /> : <Download size={12} />}
        Exportar
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 z-20 mt-2 min-w-36 rounded-xl p-1 shadow-lg"
          style={{ background: "var(--card)", border: "1px solid var(--border)" }}
        >
          {OPTIONS.map(({ format, label, icon: Icon }) => (
            <button
              key={format}
              type="button"
              role="menuitem"
              onClick={() => void handleExport(format)}
              disabled={busy !== null}
              className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left transition-colors hover:bg-muted disabled:opacity-60"
              style={{ fontSize: "12px", color: "var(--foreground)" }}
            >
              {busy === format ? <Loader2 size={14} className="animate-spin" /> : <Icon size={14} />}
              {label}
            </button>
          ))}
          {error && (
            <p className="px-2.5 py-1.5" style={{ fontSize: "11px", color: "var(--tint-danger-text)" }}>
              {error}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
