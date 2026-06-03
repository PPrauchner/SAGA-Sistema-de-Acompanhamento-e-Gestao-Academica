export function AuthIllustration() {
  const helix = Array.from({ length: 7 }, (_, i) => ({
    y: i * 14,
    x1: Math.sin(i * 0.9) * 14,
    x2: Math.sin(i * 0.9 + Math.PI) * 14,
  }));

  const stars = [
    { x: 85, y: 190, s: 6, op: 0.6 },
    { x: 380, y: 180, s: 5, op: 0.5 },
    { x: 420, y: 240, s: 4, op: 0.4 },
    { x: 60, y: 310, s: 5, op: 0.5 },
    { x: 155, y: 170, s: 4, op: 0.45 },
    { x: 350, y: 320, s: 6, op: 0.55 },
  ];

  const bars = [
    { h: 28, color: "#1F8A70" },
    { h: 40, color: "#5b8fcc" },
    { h: 20, color: "#D4A017" },
    { h: 48, color: "#1F8A70" },
  ];

  const networkNodes = [
    { cx: 195, cy: 70, r: 8 },
    { cx: 280, cy: 65, r: 10 },
    { cx: 305, cy: 100, r: 7 },
    { cx: 175, cy: 108, r: 9 },
  ];

  const windows = [145, 190, 255, 300];
  const columns = [145, 175, 205, 255, 285, 315];

  return (
    <svg viewBox="0 0 480 400" fill="none" xmlns="http://www.w3.org/2000/svg"
      style={{ width: "100%", maxWidth: 480, height: "auto" }} aria-hidden="true">

      {/* Glow circles */}
      <circle cx="240" cy="200" r="180" fill="rgba(212,160,23,0.04)" />
      <circle cx="240" cy="200" r="130" fill="rgba(31,138,112,0.05)" />

      {/* Building body */}
      <rect x="120" y="210" width="240" height="140" rx="4"
        fill="rgba(255,255,255,0.07)" stroke="rgba(255,255,255,0.14)" strokeWidth="1.5" />
      {columns.map((x, i) => (
        <rect key={i} x={x} y="215" width="11" height="130" rx="2" fill="rgba(255,255,255,0.06)" />
      ))}
      {/* Pediment */}
      <path d="M110 215 L240 158 L370 215 Z"
        fill="rgba(255,255,255,0.09)" stroke="rgba(255,255,255,0.18)" strokeWidth="1.5" />
      {/* Door */}
      <rect x="212" y="292" width="56" height="58" rx="4"
        fill="rgba(212,160,23,0.22)" stroke="rgba(212,160,23,0.38)" strokeWidth="1.5" />
      <line x1="240" y1="292" x2="240" y2="350" stroke="rgba(212,160,23,0.3)" strokeWidth="1" />
      {/* Windows */}
      {windows.map((x, i) => (
        <rect key={i} x={x} y="240" width="28" height="28" rx="3"
          fill="rgba(255,255,255,0.1)" stroke="rgba(255,255,255,0.2)" strokeWidth="1" />
      ))}
      {/* Spire */}
      <line x1="240" y1="134" x2="240" y2="158" stroke="rgba(212,160,23,0.6)" strokeWidth="2" />
      <circle cx="240" cy="130" r="8" fill="rgba(212,160,23,0.5)" stroke="#D4A017" strokeWidth="1.5" />

      {/* Graduation cap */}
      <g transform="translate(52,80)">
        <polygon points="36,0 80,20 36,32 -8,20"
          fill="rgba(255,255,255,0.14)" stroke="rgba(255,255,255,0.32)" strokeWidth="1.5" />
        <rect x="0" y="22" width="72" height="10" rx="3"
          fill="rgba(255,255,255,0.17)" stroke="rgba(255,255,255,0.28)" strokeWidth="1.5" />
        <line x1="72" y1="20" x2="80" y2="46" stroke="#D4A017" strokeWidth="2" />
        <circle cx="80" cy="48" r="5" fill="#D4A017" opacity="0.9" />
        {[-3, 0, 3].map((dx, i) => (
          <line key={i} x1={80 + dx} y1="53" x2={80 + dx} y2="64"
            stroke="#D4A017" strokeWidth="1" opacity="0.55" />
        ))}
      </g>

      {/* Open book */}
      <g transform="translate(338,108)">
        <path d="M0 62 Q0 0 52 0 Q52 62 52 62 Z"
          fill="rgba(255,255,255,0.1)" stroke="rgba(255,255,255,0.22)" strokeWidth="1.5" />
        <path d="M52 62 Q52 0 104 0 Q104 62 52 62 Z"
          fill="rgba(255,255,255,0.07)" stroke="rgba(255,255,255,0.16)" strokeWidth="1.5" />
        {[12, 22, 32, 44].map((y, i) => (
          <line key={i} x1="8" y1={y} x2="44" y2={y} stroke="rgba(255,255,255,0.18)" strokeWidth="1" />
        ))}
        {[12, 22, 32, 44].map((y, i) => (
          <line key={i} x1="60" y1={y} x2="96" y2={y} stroke="rgba(255,255,255,0.14)" strokeWidth="1" />
        ))}
        <polygon points="88,0 100,0 100,20 94,14 88,20"
          fill="#D4A017" opacity="0.65" />
      </g>

      {/* Network research nodes */}
      <circle cx="240" cy="100" r="14"
        fill="rgba(31,138,112,0.25)" stroke="#1F8A70" strokeWidth="1.5" opacity="0.7" />
      <circle cx="240" cy="100" r="6" fill="#1F8A70" opacity="0.8" />
      {networkNodes.map((node, i) => (
        <g key={i} opacity="0.65">
          <line x1="240" y1="100" x2={node.cx} y2={node.cy}
            stroke="rgba(31,138,112,0.3)" strokeWidth="1.5" strokeDasharray="4 3" />
          <circle cx={node.cx} cy={node.cy} r={node.r}
            fill="rgba(31,138,112,0.18)" stroke="#1F8A70" strokeWidth="1.5" />
        </g>
      ))}

      {/* Bar chart panel */}
      <g transform="translate(58,240)" opacity="0.68">
        <rect x="0" y="0" width="54" height="70" rx="5"
          fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.1)" strokeWidth="1" />
        {bars.map((bar, i) => (
          <rect key={i} x={4 + i * 12} y={65 - bar.h} width="9" height={bar.h}
            rx="2" fill={bar.color} opacity="0.75" />
        ))}
      </g>

      {/* Certificate scroll */}
      <g transform="translate(52,168)" opacity="0.58">
        <rect x="0" y="0" width="56" height="46" rx="5"
          fill="rgba(255,255,255,0.07)" stroke="rgba(255,255,255,0.17)" strokeWidth="1.5" />
        {[14, 22, 30].map((y, i) => (
          <line key={i} x1="8" y1={y} x2="44" y2={y}
            stroke="rgba(255,255,255,0.22)" strokeWidth="1" />
        ))}
        <circle cx="44" cy="8" r="7" fill="rgba(212,160,23,0.35)" stroke="#D4A017" strokeWidth="1.5" />
        <circle cx="44" cy="8" r="3" fill="#D4A017" opacity="0.75" />
      </g>

      {/* DNA helix */}
      <g transform="translate(392,248)" opacity="0.5">
        {helix.map((seg, i) => (
          <g key={i}>
            <circle cx={seg.x1} cy={seg.y} r="3" fill="rgba(31,138,112,0.75)" />
            <circle cx={seg.x2} cy={seg.y} r="3" fill="rgba(212,160,23,0.75)" />
            <line x1={seg.x1} y1={seg.y} x2={seg.x2} y2={seg.y}
              stroke="rgba(255,255,255,0.18)" strokeWidth="1" />
          </g>
        ))}
      </g>

      {/* Sparkle stars */}
      {stars.map((star, i) => (
        <g key={i} transform={`translate(${star.x},${star.y})`} opacity={star.op}>
          <line x1={0} y1={-star.s} x2={0} y2={star.s} stroke="#D4A017" strokeWidth="1.5" />
          <line x1={-star.s} y1={0} x2={star.s} y2={0} stroke="#D4A017" strokeWidth="1.5" />
          <line x1={-star.s * 0.7} y1={-star.s * 0.7} x2={star.s * 0.7} y2={star.s * 0.7}
            stroke="#D4A017" strokeWidth="1" />
          <line x1={star.s * 0.7} y1={-star.s * 0.7} x2={-star.s * 0.7} y2={star.s * 0.7}
            stroke="#D4A017" strokeWidth="1" />
        </g>
      ))}

      {/* Ground line */}
      <line x1="80" y1="352" x2="400" y2="352" stroke="rgba(255,255,255,0.07)" strokeWidth="1" />

      {/* Trees */}
      {[96, 362].map((x, i) => (
        <g key={i} transform={`translate(${x},318)`}>
          <ellipse cx="0" cy="-14" rx="17" ry="22"
            fill="rgba(31,138,112,0.18)" stroke="rgba(31,138,112,0.28)" strokeWidth="1" />
          <rect x="-3" y="0" width="6" height="22" rx="2" fill="rgba(255,255,255,0.07)" />
        </g>
      ))}
    </svg>
  );
}
