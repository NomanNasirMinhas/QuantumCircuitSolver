'use client';

import { useRef, useEffect, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

const PARTICLE_COUNT = 220;
const CONNECTION_DISTANCE = 1.4;
const FIELD_RADIUS = 5.5;
const MAX_LINES = PARTICLE_COUNT * 6;

// Deterministic seeded random for reproducible particle layouts
function seededRandom(seed: number): number {
  const x = Math.sin(seed * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
}

function initParticleData() {
  const positions = new Float32Array(PARTICLE_COUNT * 3);
  const basePositions = new Float32Array(PARTICLE_COUNT * 3);
  const seeds = new Float32Array(PARTICLE_COUNT);
  const sizes = new Float32Array(PARTICLE_COUNT);

  for (let i = 0; i < PARTICLE_COUNT; i++) {
    const s1 = seededRandom(i * 3 + 0);
    const s2 = seededRandom(i * 3 + 1);
    const s3 = seededRandom(i * 3 + 2);

    const theta = s1 * Math.PI * 2;
    const phi = Math.acos(2 * s2 - 1);
    const r = FIELD_RADIUS * (0.15 + s3 * 0.85);
    const x = r * Math.sin(phi) * Math.cos(theta);
    const y = r * Math.sin(phi) * Math.sin(theta);
    const z = r * Math.cos(phi);

    positions[i * 3] = x;
    positions[i * 3 + 1] = y;
    positions[i * 3 + 2] = z;
    basePositions[i * 3] = x;
    basePositions[i * 3 + 1] = y;
    basePositions[i * 3 + 2] = z;
    seeds[i] = seededRandom(i * 7 + 5) * Math.PI * 2;
    sizes[i] = 0.8 + seededRandom(i * 11 + 3) * 1.4;
  }

  return { positions, basePositions, seeds, sizes };
}

function createParticleTexture(): THREE.CanvasTexture {
  const canvas = document.createElement('canvas');
  canvas.width = 64;
  canvas.height = 64;
  const ctx = canvas.getContext('2d')!;
  const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
  gradient.addColorStop(0, 'rgba(255, 255, 255, 1.0)');
  gradient.addColorStop(0.15, 'rgba(255, 255, 255, 0.7)');
  gradient.addColorStop(0.35, 'rgba(255, 255, 255, 0.15)');
  gradient.addColorStop(0.6, 'rgba(255, 255, 255, 0.03)');
  gradient.addColorStop(1, 'rgba(255, 255, 255, 0.0)');
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, 64, 64);
  return new THREE.CanvasTexture(canvas);
}

// Pre-compute all data outside the component (pure, deterministic)
const INIT = initParticleData();

const STATE_COLORS_1: Record<string, THREE.Color> = {
  idle: new THREE.Color('#7B2FBE'),
  generating: new THREE.Color('#00BFA5'),
  success: new THREE.Color('#00BCD4'),
  error: new THREE.Color('#9C27B0'),
};

const STATE_COLORS_2: Record<string, THREE.Color> = {
  idle: new THREE.Color('#00E5FF'),
  generating: new THREE.Color('#7C4DFF'),
  success: new THREE.Color('#6A1B9A'),
  error: new THREE.Color('#E040FB'),
};

const CORE_TINTS: Record<string, string> = {
  idle: '#5A189A',
  generating: '#00BFA5',
  success: '#7C4DFF',
  error: '#9C27B0',
};

const SPEEDS: Record<string, number> = {
  idle: 0.3,
  generating: 1.6,
  success: 0.5,
  error: 0.15,
};

export default function QuantumParticleField({ state }: { state: 'idle' | 'generating' | 'success' | 'error' }) {
  const pointsRef = useRef<THREE.Points>(null);
  const linesRef = useRef<THREE.LineSegments>(null);
  const coreRef = useRef<THREE.Mesh>(null);
  const particleTexture = useMemo(
    () => (typeof document === 'undefined' ? null : createParticleTexture()),
    []
  );

  // Mutable buffers stored in refs so useFrame can write into them freely
  const positionsRef = useRef(new Float32Array(INIT.positions));
  const colorsRef = useRef(new Float32Array(PARTICLE_COUNT * 3));
  const sizesRef = useRef(new Float32Array(INIT.sizes));
  const linePosRef = useRef(new Float32Array(MAX_LINES * 6));
  const lineColRef = useRef(new Float32Array(MAX_LINES * 6));

  // Attach buffers to geometry once on mount
  useEffect(() => {
    if (pointsRef.current) {
      const geo = pointsRef.current.geometry;
      geo.setAttribute('position', new THREE.BufferAttribute(positionsRef.current, 3));
      geo.setAttribute('color', new THREE.BufferAttribute(colorsRef.current, 3));
      geo.setAttribute('size', new THREE.BufferAttribute(sizesRef.current, 1));
    }
    if (linesRef.current) {
      const geo = linesRef.current.geometry;
      geo.setAttribute('position', new THREE.BufferAttribute(linePosRef.current, 3));
      geo.setAttribute('color', new THREE.BufferAttribute(lineColRef.current, 3));
    }
  }, []);

  useEffect(() => {
    return () => {
      particleTexture?.dispose();
    };
  }, [particleTexture]);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    const speed = SPEEDS[state];
    const c1 = STATE_COLORS_1[state];
    const c2 = STATE_COLORS_2[state];

    if (!pointsRef.current || !linesRef.current) return;

    const positions = positionsRef.current;
    const colors = colorsRef.current;
    const pSizes = sizesRef.current;
    const basePositions = INIT.basePositions;
    const seeds = INIT.seeds;
    const baseSizes = INIT.sizes;

    // Update particle positions: orbital motion + drift
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const seed = seeds[i];
      const bx = basePositions[i * 3];
      const by = basePositions[i * 3 + 1];
      const bz = basePositions[i * 3 + 2];

      const orbitRadius = 0.3 + Math.sin(seed) * 0.2;
      const orbitSpeed = speed * (0.5 + Math.cos(seed * 2) * 0.3);
      const ox = Math.cos(t * orbitSpeed + seed) * orbitRadius;
      const oy = Math.sin(t * orbitSpeed * 0.7 + seed * 1.3) * orbitRadius;
      const oz = Math.sin(t * orbitSpeed * 0.5 + seed * 0.7) * orbitRadius * 0.5;

      positions[i * 3] = bx + ox;
      positions[i * 3 + 1] = by + oy;
      positions[i * 3 + 2] = bz + oz;

      // Color: mix between two state colors based on seed
      const mix = (Math.sin(t * 0.5 + seed * 3) + 1) * 0.5;
      colors[i * 3] = c1.r + (c2.r - c1.r) * mix;
      colors[i * 3 + 1] = c1.g + (c2.g - c1.g) * mix;
      colors[i * 3 + 2] = c1.b + (c2.b - c1.b) * mix;

      // Pulsing size
      pSizes[i] = baseSizes[i] * (0.7 + 0.3 * Math.sin(t * speed * 2 + seed));
    }

    const ptGeo = pointsRef.current.geometry;
    (ptGeo.attributes.position as THREE.BufferAttribute).needsUpdate = true;
    (ptGeo.attributes.color as THREE.BufferAttribute).needsUpdate = true;
    (ptGeo.attributes.size as THREE.BufferAttribute).needsUpdate = true;

    // Build connection lines between nearby particles
    const linePositions = linePosRef.current;
    const lineColors = lineColRef.current;
    let lineIdx = 0;
    for (let i = 0; i < PARTICLE_COUNT && lineIdx < MAX_LINES; i++) {
      for (let j = i + 1; j < PARTICLE_COUNT && lineIdx < MAX_LINES; j++) {
        const dx = positions[i * 3] - positions[j * 3];
        const dy = positions[i * 3 + 1] - positions[j * 3 + 1];
        const dz = positions[i * 3 + 2] - positions[j * 3 + 2];
        const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
        if (dist < CONNECTION_DISTANCE) {
          const alpha = 1.0 - dist / CONNECTION_DISTANCE;
          const offset = lineIdx * 6;
          linePositions[offset] = positions[i * 3];
          linePositions[offset + 1] = positions[i * 3 + 1];
          linePositions[offset + 2] = positions[i * 3 + 2];
          linePositions[offset + 3] = positions[j * 3];
          linePositions[offset + 4] = positions[j * 3 + 1];
          linePositions[offset + 5] = positions[j * 3 + 2];

          lineColors[offset] = c1.r * alpha;
          lineColors[offset + 1] = c1.g * alpha;
          lineColors[offset + 2] = c1.b * alpha;
          lineColors[offset + 3] = c1.r * alpha;
          lineColors[offset + 4] = c1.g * alpha;
          lineColors[offset + 5] = c1.b * alpha;
          lineIdx++;
        }
      }
    }

    // Zero out remaining
    for (let k = lineIdx * 6; k < linePositions.length; k++) {
      linePositions[k] = 0;
      lineColors[k] = 0;
    }

    const lnGeo = linesRef.current.geometry;
    (lnGeo.attributes.position as THREE.BufferAttribute).needsUpdate = true;
    (lnGeo.attributes.color as THREE.BufferAttribute).needsUpdate = true;
    lnGeo.setDrawRange(0, lineIdx * 2);

    // Pulse the core glow
    if (coreRef.current) {
      const mat = coreRef.current.material as THREE.MeshBasicMaterial;
      mat.color.set(CORE_TINTS[state]);
      mat.opacity = 0.08 + 0.06 * Math.sin(t * speed * 2);
      coreRef.current.scale.setScalar(0.5 + 0.15 * Math.sin(t * speed));
    }
  });

  return (
    <group>
      {/* Particle points — geometry attached imperatively via useEffect */}
      <points ref={pointsRef}>
        <bufferGeometry />
        <pointsMaterial
          vertexColors
          transparent
          opacity={0.55}
          sizeAttenuation
          size={1.8}
          map={particleTexture ?? undefined}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </points>

      {/* Connection lines — geometry attached imperatively via useEffect */}
      <lineSegments ref={linesRef}>
        <bufferGeometry />
        <lineBasicMaterial
          vertexColors
          transparent
          opacity={0.15}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </lineSegments>

      {/* Central energy core glow */}
      <mesh ref={coreRef}>
        <sphereGeometry args={[0.4, 32, 32]} />
        <meshBasicMaterial
          color={CORE_TINTS[state]}
          transparent
          opacity={0.06}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>
    </group>
  );
}
