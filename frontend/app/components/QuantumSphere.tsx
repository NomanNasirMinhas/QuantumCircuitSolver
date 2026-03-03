'use client';

import { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Sphere, MeshDistortMaterial } from '@react-three/drei';
import * as THREE from 'three';

export default function QuantumSphere({ state }: { state: 'idle' | 'generating' | 'success' | 'error' }) {
  const meshRef = useRef<THREE.Mesh>(null);

  // Dynamic properties based on orchestrator state
  const colors = {
    idle: '#00E5FF', // Cyan
    generating: '#D500F9', // Purple
    success: '#FFD600', // Gold
    error: '#FF1744' // Red
  };

  const speeds = {
    idle: 0.5,
    generating: 2.5,
    success: 0.8,
    error: 0.1
  };

  const distorts = {
    idle: 0.3,
    generating: 0.8,
    success: 0.4,
    error: 1.0
  };

  useFrame((stateObj, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.x += delta * (speeds[state] * 0.2);
      meshRef.current.rotation.y += delta * (speeds[state] * 0.3);
      
      // Gentle floating animation
      meshRef.current.position.y = Math.sin(stateObj.clock.elapsedTime) * 0.2;
    }
  });

  return (
    <Sphere ref={meshRef} args={[1.5, 64, 64]} scale={2}>
      <MeshDistortMaterial
        color={colors[state]}
        attach="material"
        distort={distorts[state]}
        speed={speeds[state]}
        roughness={0.2}
        metalness={0.8}
        wireframe={state === 'generating'}
      />
    </Sphere>
  );
}
