export type ExportCell = string | number | boolean | null | undefined | Date;

export type ExportColumn<T> = {
  key: keyof T | string;
  label: string;
  value?: (row: T) => ExportCell;
};

export function sanitizeFileName(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-zA-Z0-9-_]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .toLowerCase() || "grafico";
}

export function sanitizeSheetName(value: string): string {
  const clean = value.replace(/[\\/?*[\]:]/g, " ").trim() || "Grafico";
  return clean.slice(0, 31);
}

function getCellValue<T>(row: T, column: ExportColumn<T>): ExportCell {
  if (column.value) return column.value(row);
  const record = row as Record<string, ExportCell>;
  return record[String(column.key)];
}

function formatCell(value: ExportCell): string {
  if (value == null) return "";
  if (value instanceof Date) return value.toISOString();
  return String(value);
}

function escapeCsv(value: ExportCell): string {
  const text = formatCell(value);
  if (/[",\n\r;]/.test(text)) return `"${text.replace(/"/g, '""')}"`;
  return text;
}

export function toCsv<T>(rows: T[], columns: ExportColumn<T>[]): string {
  const header = columns.map((column) => escapeCsv(column.label)).join(";");
  const body = rows.map((row) => columns.map((column) => escapeCsv(getCellValue(row, column))).join(";"));
  return `\ufeff${[header, ...body].join("\r\n")}`;
}

function xmlEscape(value: ExportCell): string {
  return formatCell(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function columnName(index: number): string {
  let name = "";
  let current = index + 1;
  while (current > 0) {
    const rem = (current - 1) % 26;
    name = String.fromCharCode(65 + rem) + name;
    current = Math.floor((current - 1) / 26);
  }
  return name;
}

function worksheetXml<T>(rows: T[], columns: ExportColumn<T>[]): string {
  const headerCells = columns.map((column, index) => (
    `<c r="${columnName(index)}1" t="inlineStr"><is><t>${xmlEscape(column.label)}</t></is></c>`
  )).join("");

  const dataRows = rows.map((row, rowIndex) => {
    const rowNumber = rowIndex + 2;
    const cells = columns.map((column, columnIndex) => {
      const value = getCellValue(row, column);
      const ref = `${columnName(columnIndex)}${rowNumber}`;
      if (typeof value === "number" && Number.isFinite(value)) return `<c r="${ref}"><v>${value}</v></c>`;
      return `<c r="${ref}" t="inlineStr"><is><t>${xmlEscape(value)}</t></is></c>`;
    }).join("");
    return `<row r="${rowNumber}">${cells}</row>`;
  }).join("");

  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="1">${headerCells}</row>
    ${dataRows}
  </sheetData>
</worksheet>`;
}

function crc32(bytes: Uint8Array): number {
  let crc = 0xffffffff;
  for (const byte of bytes) {
    crc ^= byte;
    for (let i = 0; i < 8; i += 1) {
      crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1));
    }
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function writeUint16(target: number[], value: number): void {
  target.push(value & 0xff, (value >>> 8) & 0xff);
}

function writeUint32(target: number[], value: number): void {
  target.push(value & 0xff, (value >>> 8) & 0xff, (value >>> 16) & 0xff, (value >>> 24) & 0xff);
}

function encode(text: string): Uint8Array {
  return new TextEncoder().encode(text);
}

function createZip(files: Array<{ name: string; content: string }>): Blob {
  const chunks: Uint8Array[] = [];
  const centralDirectory: number[] = [];
  let offset = 0;

  for (const file of files) {
    const name = encode(file.name);
    const content = encode(file.content);
    const crc = crc32(content);
    const local: number[] = [];

    writeUint32(local, 0x04034b50);
    writeUint16(local, 20);
    writeUint16(local, 0x0800);
    writeUint16(local, 0);
    writeUint16(local, 0);
    writeUint16(local, 0);
    writeUint32(local, crc);
    writeUint32(local, content.length);
    writeUint32(local, content.length);
    writeUint16(local, name.length);
    writeUint16(local, 0);

    const localRecord = new Uint8Array([...local, ...name, ...content]);
    chunks.push(localRecord);

    writeUint32(centralDirectory, 0x02014b50);
    writeUint16(centralDirectory, 20);
    writeUint16(centralDirectory, 20);
    writeUint16(centralDirectory, 0x0800);
    writeUint16(centralDirectory, 0);
    writeUint16(centralDirectory, 0);
    writeUint16(centralDirectory, 0);
    writeUint32(centralDirectory, crc);
    writeUint32(centralDirectory, content.length);
    writeUint32(centralDirectory, content.length);
    writeUint16(centralDirectory, name.length);
    writeUint16(centralDirectory, 0);
    writeUint16(centralDirectory, 0);
    writeUint16(centralDirectory, 0);
    writeUint16(centralDirectory, 0);
    writeUint32(centralDirectory, 0);
    writeUint32(centralDirectory, offset);
    centralDirectory.push(...name);

    offset += localRecord.length;
  }

  const centralStart = offset;
  const centralBytes = new Uint8Array(centralDirectory);
  chunks.push(centralBytes);

  const end: number[] = [];
  writeUint32(end, 0x06054b50);
  writeUint16(end, 0);
  writeUint16(end, 0);
  writeUint16(end, files.length);
  writeUint16(end, files.length);
  writeUint32(end, centralBytes.length);
  writeUint32(end, centralStart);
  writeUint16(end, 0);
  chunks.push(new Uint8Array(end));

  return new Blob(chunks as unknown as BlobPart[], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
}

export function toXlsx<T>(rows: T[], columns: ExportColumn<T>[], sheetName: string): Blob {
  const safeSheetName = sanitizeSheetName(sheetName);
  return createZip([
    {
      name: "[Content_Types].xml",
      content: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>`,
    },
    {
      name: "_rels/.rels",
      content: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>`,
    },
    {
      name: "xl/workbook.xml",
      content: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="${xmlEscape(safeSheetName)}" sheetId="1" r:id="rId1"/></sheets>
</workbook>`,
    },
    {
      name: "xl/_rels/workbook.xml.rels",
      content: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>`,
    },
    { name: "xl/worksheets/sheet1.xml", content: worksheetXml(rows, columns) },
  ]);
}

export function downloadBlob(blob: Blob, fileName: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
