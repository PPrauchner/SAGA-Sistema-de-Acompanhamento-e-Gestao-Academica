import { downloadBlob } from "./exportData";

function getChartSvg(element: HTMLElement): SVGSVGElement {
  const svg = element.querySelector("svg");
  if (!svg) throw new Error("Nenhum grafico SVG foi encontrado para exportacao.");
  return svg;
}

function svgToDataUrl(svg: SVGSVGElement): { dataUrl: string; width: number; height: number } {
  const clone = svg.cloneNode(true) as SVGSVGElement;
  const box = svg.getBoundingClientRect();
  const width = Math.max(1, Math.round(box.width || Number(svg.getAttribute("width")) || 800));
  const height = Math.max(1, Math.round(box.height || Number(svg.getAttribute("height")) || 450));

  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  clone.setAttribute("width", String(width));
  clone.setAttribute("height", String(height));
  clone.setAttribute("viewBox", clone.getAttribute("viewBox") || `0 0 ${width} ${height}`);

  const background = document.createElementNS("http://www.w3.org/2000/svg", "rect");
  background.setAttribute("width", "100%");
  background.setAttribute("height", "100%");
  background.setAttribute("fill", getComputedStyle(document.body).getPropertyValue("--card").trim() || "#ffffff");
  clone.insertBefore(background, clone.firstChild);

  const serialized = new XMLSerializer().serializeToString(clone);
  return {
    dataUrl: `data:image/svg+xml;charset=utf-8,${encodeURIComponent(serialized)}`,
    width,
    height,
  };
}

async function svgToCanvas(element: HTMLElement, scale = 2): Promise<HTMLCanvasElement> {
  const { dataUrl, width, height } = svgToDataUrl(getChartSvg(element));
  const image = new Image();
  image.crossOrigin = "anonymous";

  await new Promise<void>((resolve, reject) => {
    image.onload = () => resolve();
    image.onerror = () => reject(new Error("Nao foi possivel preparar a imagem do grafico."));
    image.src = dataUrl;
  });

  const canvas = document.createElement("canvas");
  canvas.width = width * scale;
  canvas.height = height * scale;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("Canvas nao esta disponivel neste navegador.");

  context.fillStyle = "#ffffff";
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.drawImage(image, 0, 0, canvas.width, canvas.height);
  return canvas;
}

function canvasToBlob(canvas: HTMLCanvasElement, type: string, quality?: number): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) resolve(blob);
      else reject(new Error("Nao foi possivel gerar o arquivo de imagem."));
    }, type, quality);
  });
}

function escapePdfText(value: string): string {
  return value.replace(/\\/g, "\\\\").replace(/\(/g, "\\(").replace(/\)/g, "\\)");
}

function binaryFromDataUrl(dataUrl: string): string {
  return atob(dataUrl.split(",")[1] ?? "");
}

function createPdf(title: string, imageDataUrl: string, imageWidth: number, imageHeight: number): Blob {
  const pageWidth = 595;
  const pageHeight = 842;
  const margin = 48;
  const titleHeight = 36;
  const maxWidth = pageWidth - margin * 2;
  const maxHeight = pageHeight - margin * 2 - titleHeight;
  const ratio = Math.min(maxWidth / imageWidth, maxHeight / imageHeight);
  const drawWidth = imageWidth * ratio;
  const drawHeight = imageHeight * ratio;
  const x = (pageWidth - drawWidth) / 2;
  const y = pageHeight - margin - titleHeight - drawHeight;
  const imageBinary = binaryFromDataUrl(imageDataUrl);

  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${pageWidth} ${pageHeight}] /Resources << /Font << /F1 4 0 R >> /XObject << /Im1 5 0 R >> >> /Contents 6 0 R >>`,
    "<< /Type /Font /Subtype /Helvetica /BaseFont /Helvetica >>",
    `<< /Type /XObject /Subtype /Image /Width ${Math.round(imageWidth)} /Height ${Math.round(imageHeight)} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${imageBinary.length} >>\nstream\n${imageBinary}\nendstream`,
  ];

  const content = `BT /F1 16 Tf ${margin} ${pageHeight - margin} Td (${escapePdfText(title)}) Tj ET
q ${drawWidth.toFixed(2)} 0 0 ${drawHeight.toFixed(2)} ${x.toFixed(2)} ${y.toFixed(2)} cm /Im1 Do Q`;
  objects.push(`<< /Length ${content.length} >>\nstream\n${content}\nendstream`);

  let pdf = "%PDF-1.4\n";
  const offsets = [0];
  objects.forEach((object, index) => {
    offsets.push(pdf.length);
    pdf += `${index + 1} 0 obj\n${object}\nendobj\n`;
  });
  const xrefStart = pdf.length;
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  for (let i = 1; i < offsets.length; i += 1) {
    pdf += `${String(offsets[i]).padStart(10, "0")} 00000 n \n`;
  }
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefStart}\n%%EOF`;

  const bytes = new Uint8Array(pdf.length);
  for (let i = 0; i < pdf.length; i += 1) bytes[i] = pdf.charCodeAt(i) & 0xff;
  return new Blob([bytes], { type: "application/pdf" });
}

export async function exportChartAsPng(element: HTMLElement, fileName: string): Promise<void> {
  const canvas = await svgToCanvas(element);
  const blob = await canvasToBlob(canvas, "image/png");
  downloadBlob(blob, fileName);
}

export async function exportChartAsPdf(element: HTMLElement, title: string, fileName: string): Promise<void> {
  const canvas = await svgToCanvas(element);
  const imageDataUrl = canvas.toDataURL("image/jpeg", 0.92);
  const pdf = createPdf(title, imageDataUrl, canvas.width, canvas.height);
  downloadBlob(pdf, fileName);
}
