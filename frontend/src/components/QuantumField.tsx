function Gate({ x, y, name, color = "violet" }: { x: number; y: number; name: string; color?: string }) {
  return (
    <g className={`hero-gate hero-gate-${color}`} transform={`translate(${x} ${y})`}>
      <rect x="-27" y="-23" width="54" height="46" rx="2" />
      <text textAnchor="middle" dominantBaseline="central">{name}</text>
    </g>
  );
}

export function QuantumField() {
  return (
    <div className="quantum-field" aria-hidden="true">
      <div className="field-pixels field-pixels-a" />
      <div className="field-pixels field-pixels-b" />
      <svg viewBox="0 0 1440 650" preserveAspectRatio="xMidYMid slice">
        <defs>
          <pattern id="quantum-dots" width="22" height="22" patternUnits="userSpaceOnUse">
            <circle cx="2" cy="2" r="1.5" fill="#4b4e58" />
          </pattern>
        </defs>
        <rect width="1440" height="650" fill="url(#quantum-dots)" opacity=".48" />
        {[174, 254, 334, 414, 494].map((y, index) => (
          <g key={y}>
            <text className="rail-label" x="550" y={y + 5}>q[{index}]</text>
            <path className="rail" d={`M 616 ${y} H 1390`} />
            <path className={`rail-pulse rail-pulse-${index}`} d={`M 616 ${y} H 1390`} />
          </g>
        ))}
        <Gate x={688} y={174} name="H" color="cyan" />
        <Gate x={688} y={334} name="H" color="cyan" />
        <Gate x={799} y={254} name="RZ" />
        <Gate x={799} y={414} name="RY" />
        <path className="entangle-line" d="M 918 174 V 334" />
        <circle className="control-dot" cx="918" cy="174" r="8" />
        <circle className="entangle-target" cx="918" cy="334" r="17" />
        <path className="entangle-cross" d="M 918 317 V 351 M 901 334 H 935" />
        <Gate x={1038} y={174} name="T" color="yellow" />
        <Gate x={1038} y={494} name="H" color="cyan" />
        <path className="entangle-line secondary" d="M 1154 254 V 414" />
        <circle className="control-dot" cx="1154" cy="254" r="8" />
        <circle className="entangle-target" cx="1154" cy="414" r="17" />
        <path className="entangle-cross" d="M 1154 397 V 431 M 1137 414 H 1171" />
        <Gate x={1280} y={334} name="SX" color="orange" />
        <Gate x={1280} y={494} name="RZ" />
        <path className="circuit-bracket" d="M 606 124 H 1354 V 540 H 606" />
      </svg>
    </div>
  );
}
