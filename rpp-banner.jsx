export default function RPPLinkedInBanner() {
  // LinkedIn banner dimensions: 1584 x 396
  const width = 1584;
  const height = 396;
  
  // Spiral color palette from RPP image
  const colors = {
    pink: '#d16ba5',
    coral: '#f28d7d',
    orange: '#f0856a',
    yellow: '#f3e06e',
    green: '#5bd6a2',
    cyan: '#5ed5d5',
    blue: '#5da5d5',
    purple: '#9b6dd6',
  };

  // Orbital nodes positioned around the left spiral area
  const nodes = [
    { x: 180, y: 60, color: colors.pink },
    { x: 320, y: 45, color: colors.coral },
    { x: 420, y: 90, color: colors.orange },
    { x: 140, y: 180, color: colors.blue },
    { x: 380, y: 340, color: colors.yellow },
    { x: 200, y: 330, color: colors.green },
    { x: 100, y: 280, color: colors.cyan },
    { x: 450, y: 220, color: colors.purple },
  ];

  // Phase markers (triangular direction indicators)
  const markers = [
    { x: 280, y: 120, rotation: 45, color: colors.cyan },
    { x: 350, y: 180, rotation: -30, color: colors.purple },
    { x: 300, y: 260, rotation: 15, color: colors.yellow },
    { x: 420, y: 150, rotation: -60, color: colors.pink },
    { x: 380, y: 280, rotation: 30, color: colors.green },
  ];

  // Theta sector labels
  const sectors = [
    { x: 520, y: 70, label: 'GENE' },
    { x: 620, y: 110, label: 'MEMORY' },
    { x: 720, y: 150, label: 'WITNESS' },
    { x: 800, y: 200, label: 'DREAM' },
    { x: 720, y: 280, label: 'BRIDGE' },
    { x: 620, y: 320, label: 'GUARDIAN' },
  ];

  return (
    <div style={{ 
      width: '100%', 
      maxWidth: width, 
      margin: '0 auto',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    }}>
      <svg 
        viewBox={`0 0 ${width} ${height}`} 
        style={{ width: '100%', height: 'auto', display: 'block' }}
      >
        <defs>
          {/* Gradients */}
          <linearGradient id="titleGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={colors.pink} />
            <stop offset="33%" stopColor={colors.purple} />
            <stop offset="66%" stopColor={colors.blue} />
            <stop offset="100%" stopColor={colors.cyan} />
          </linearGradient>
          
          <linearGradient id="accentBar" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor={colors.cyan} />
            <stop offset="25%" stopColor={colors.green} />
            <stop offset="50%" stopColor={colors.yellow} />
            <stop offset="75%" stopColor={colors.orange} />
            <stop offset="100%" stopColor={colors.pink} />
          </linearGradient>
          
          <radialGradient id="coreGlow" cx="20%" cy="50%" r="40%">
            <stop offset="0%" stopColor="white" stopOpacity="0.15" />
            <stop offset="30%" stopColor={colors.cyan} stopOpacity="0.1" />
            <stop offset="60%" stopColor={colors.purple} stopOpacity="0.05" />
            <stop offset="100%" stopColor="transparent" stopOpacity="0" />
          </radialGradient>
          
          <radialGradient id="nodeGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="white" stopOpacity="0.8" />
            <stop offset="50%" stopColor="currentColor" stopOpacity="0.6" />
            <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
          </radialGradient>

          {/* Filters */}
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          
          <filter id="softGlow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="8" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        
        {/* Background */}
        <rect width={width} height={height} fill="#0a0a0f" />
        
        {/* Top accent bar */}
        <rect x="0" y="0" width={width} height="3" fill="url(#accentBar)" />
        
        {/* Core glow from left (where profile pic overlaps) */}
        <ellipse cx="100" cy={height/2} rx="350" ry="300" fill="url(#coreGlow)" />
        
        {/* Holographic grid (perspective) */}
        <g opacity="0.15">
          {[...Array(20)].map((_, i) => (
            <line 
              key={`vline-${i}`}
              x1={600 + i * 50} 
              y1="0" 
              x2={400 + i * 60} 
              y2={height}
              stroke={colors.cyan} 
              strokeWidth="0.5"
            />
          ))}
          {[...Array(8)].map((_, i) => (
            <line 
              key={`hline-${i}`}
              x1="500" 
              y1={50 + i * 50} 
              x2={width} 
              y2={30 + i * 45}
              stroke={colors.cyan} 
              strokeWidth="0.5"
            />
          ))}
        </g>
        
        {/* Orbital rings (spiral shells) */}
        <ellipse cx="200" cy={height/2} rx="120" ry="120" 
          fill="none" stroke={colors.pink} strokeWidth="1.5" opacity="0.4" />
        <ellipse cx="200" cy={height/2} rx="180" ry="180" 
          fill="none" stroke={colors.cyan} strokeWidth="1.5" opacity="0.3" />
        <ellipse cx="200" cy={height/2} rx="250" ry="250" 
          fill="none" stroke={colors.yellow} strokeWidth="1" opacity="0.2" />
        <ellipse cx="200" cy={height/2} rx="320" ry="320" 
          fill="none" stroke={colors.purple} strokeWidth="1" opacity="0.15" />
        
        {/* Spiral arc (main visual from RPP logo) */}
        <path
          d="M 250 198 
             A 80 80 0 1 1 200 118
             A 120 120 0 1 0 320 198
             A 160 160 0 1 1 200 358"
          fill="none"
          stroke="url(#accentBar)"
          strokeWidth="3"
          strokeLinecap="round"
          opacity="0.7"
          filter="url(#glow)"
        />
        
        {/* Central core (white glow point) */}
        <circle cx="200" cy={height/2} r="15" fill="white" opacity="0.9" filter="url(#softGlow)" />
        <circle cx="200" cy={height/2} r="8" fill="white" />
        <circle cx="200" cy={height/2} r="4" fill="#0a0a0f" />
        
        {/* Crosshairs at center */}
        <line x1="180" y1={height/2} x2="165" y2={height/2} stroke="white" strokeWidth="1" opacity="0.5" />
        <line x1="220" y1={height/2} x2="235" y2={height/2} stroke="white" strokeWidth="1" opacity="0.5" />
        <line x1="200" y1={height/2 - 20} x2="200" y2={height/2 - 35} stroke="white" strokeWidth="1" opacity="0.5" />
        <line x1="200" y1={height/2 + 20} x2="200" y2={height/2 + 35} stroke="white" strokeWidth="1" opacity="0.5" />
        
        {/* Orbital nodes */}
        {nodes.map((node, i) => (
          <g key={`node-${i}`} filter="url(#glow)">
            <circle cx={node.x} cy={node.y} r="10" fill={node.color} opacity="0.3" />
            <circle cx={node.x} cy={node.y} r="6" fill={node.color} />
          </g>
        ))}
        
        {/* Phase direction markers (triangles) */}
        {markers.map((m, i) => (
          <polygon
            key={`marker-${i}`}
            points="0,-8 6,6 -6,6"
            fill={m.color}
            opacity="0.7"
            transform={`translate(${m.x}, ${m.y}) rotate(${m.rotation})`}
            filter="url(#glow)"
          />
        ))}
        
        {/* Flow lines (phase vectors) */}
        <line x1="350" y1="100" x2="550" y2="80" 
          stroke={colors.cyan} strokeWidth="1" opacity="0.4" strokeDasharray="4 4" />
        <line x1="400" y1="200" x2="600" y2="180" 
          stroke={colors.purple} strokeWidth="1" opacity="0.3" strokeDasharray="4 4" />
        <line x1="380" y1="300" x2="580" y2="320" 
          stroke={colors.yellow} strokeWidth="1" opacity="0.3" strokeDasharray="4 4" />
        
        {/* Sector labels */}
        {sectors.map((s, i) => (
          <text 
            key={`sector-${i}`}
            x={s.x} 
            y={s.y} 
            fill="white" 
            opacity="0.25"
            fontSize="10"
            fontFamily="SF Mono, Monaco, monospace"
            letterSpacing="2"
          >
            {s.label}
          </text>
        ))}
        
        {/* Right side wave field (subtle) */}
        <ellipse cx="1300" cy="100" rx="300" ry="200" fill={colors.pink} opacity="0.05" />
        <ellipse cx="1100" cy="300" rx="250" ry="150" fill={colors.cyan} opacity="0.04" />
        <ellipse cx="1400" cy="250" rx="200" ry="180" fill={colors.purple} opacity="0.03" />
        
        {/* Title area */}
        <text x="1500" y="155" textAnchor="end" fontSize="48" fontWeight="700" fill="url(#titleGradient)">
          Anywave Creations
        </text>
        <text x="1500" y="195" textAnchor="end" fontSize="18" fill="white" opacity="0.6" letterSpacing="1">
          Consent-Aware Systems Architecture
        </text>
        <text x="1500" y="235" textAnchor="end" fontSize="11" fill={colors.cyan} opacity="0.7" 
          fontFamily="SF Mono, Monaco, monospace" letterSpacing="3">
          COHERENCE · SOVEREIGNTY · RESONANCE
        </text>
        
        {/* Consent state indicators (bottom left, after profile area) */}
        <g transform="translate(280, 360)">
          <circle cx="0" cy="0" r="4" fill={colors.green} filter="url(#glow)" />
          <circle cx="16" cy="0" r="4" fill={colors.yellow} filter="url(#glow)" />
          <circle cx="32" cy="0" r="4" fill={colors.coral} filter="url(#glow)" />
          <text x="50" y="4" fontSize="9" fill="white" opacity="0.4" 
            fontFamily="SF Mono, Monaco, monospace" letterSpacing="1">
            ACSP ACTIVE
          </text>
        </g>
        
        {/* Address example (subtle, technical detail) */}
        <text x="1500" y="370" textAnchor="end" fontSize="10" fill={colors.cyan} opacity="0.3"
          fontFamily="SF Mono, Monaco, monospace">
          θ:GENE · φ:GROUNDED · h:1 → 0x0182801
        </text>
        
        {/* Bottom accent bar */}
        <rect x="0" y={height - 3} width={width} height="3" fill="url(#accentBar)" />
        
        {/* Scan line effect */}
        <g opacity="0.03">
          {[...Array(99)].map((_, i) => (
            <line 
              key={`scan-${i}`}
              x1="0" 
              y1={i * 4} 
              x2={width} 
              y2={i * 4}
              stroke={colors.cyan} 
              strokeWidth="1"
            />
          ))}
        </g>
      </svg>
    </div>
  );
}
