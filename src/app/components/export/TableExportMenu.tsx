import { useState } from "react";
import { Download, FileSpreadsheet, FileText, Loader2, Table } from "lucide-react";
import { downloadBlob, sanitizeFileName, toCsv, toXlsx, getCellValue, formatCell, type ExportColumn } from "@/utils/exportData";
import { PdfBuilder, formatDateTime } from "@/utils/exportChecklistPdf";

type ExportFormat = "pdf" | "csv" | "xlsx";

interface TableExportMenuProps<T> {
  title: string;
  fileName: string;
  rows: T[];
  columns: ExportColumn<T>[];
}

const OPTIONS: Array<{ format: ExportFormat; label: string; icon: typeof Table }> = [
  { format: "pdf", label: "PDF", icon: FileText as typeof Table },
  { format: "csv", label: "CSV", icon: Table },
  { format: "xlsx", label: "Excel", icon: FileSpreadsheet as typeof Table },
];

export function TableExportMenu<T>({ title, fileName, rows, columns }: TableExportMenuProps<T>) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState<ExportFormat | null>(null);
  const [error, setError] = useState<string | null>(null);
  const baseName = sanitizeFileName(fileName);

  function handleExport(format: ExportFormat): void {
    setBusy(format);
    setError(null);
    try {
      if (format === "csv") {
        downloadBlob(new Blob([toCsv(rows, columns)], { type: "text/csv;charset=utf-8" }), `${baseName}.csv`);
      } else if (format === "xlsx") {
        downloadBlob(toXlsx(rows, columns, title), `${baseName}.xlsx`);
      } else if (format === "pdf") {
        const pdf = new PdfBuilder();
        const generatedAt = new Date();
        
        pdf.text(title, 18, { bold: true, gapAfter: 2 });
        pdf.text(`Gerado em ${formatDateTime(generatedAt.toISOString())}`, 9, { gapAfter: 4 });
        pdf.rule();

        rows.forEach((row, index) => {
          pdf.text(`Item ${index + 1}`, 11, { bold: true, gapAfter: 1 });
          columns.forEach((col) => {
            const val = getCellValue(row, col);
            pdf.text(`${col.label}: ${formatCell(val)}`, 9, { indent: 12 });
          });
          pdf.gap(6);
        });

        downloadBlob(pdf.build(), `${baseName}.pdf`);
      }
      setOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel exportar a lista.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        disabled={busy !== null}
        className="inline-flex items-center gap-2 rounded-xl px-3 py-2.5 transition-opacity disabled:opacity-60"
        style={{ background: "#eef3fc", border: "1px solid #c7d9f5", color: "#123C7A", fontSize: "13px", fontWeight: 700 }}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Exportar ${title}`}
      >
        {busy ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
        Exportar
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 z-20 mt-2 min-w-32 rounded-xl p-1 shadow-lg"
          style={{ background: "var(--card)", border: "1px solid var(--border)" }}
        >
          {OPTIONS.map(({ format, label, icon: Icon }) => (
            <button
              key={format}
              type="button"
              role="menuitem"
              onClick={() => handleExport(format)}
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
