'use client';

import { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Sphere, MeshDistortMaterial, Icosahedron, GradientTexture } from '@react-three/drei';
import * as THREE from 'three';

export default function QuantumSphere({ state }: { state: 'idle' | 'generating' | 'success' | 'error' }) {
  const meshRef = useRef<THREE.Group>(null);
  const coreRef = useRef<THREE.Mesh>(null);

  // Dynamic properties based on orchestrator state
  const emissiveColors = {
    idle: '#5A189A', // Deep Violet Emissive
    generating: '#F72585', // Neon Pink
    success: '#FFD600', // Gold
    error: '#FF1744' // Red
  };

  const gradients = {
    idle: ['#3A0CA3', '#E0AAFF'], // Deep Purple to Light Violet gradient
    generating: ['#7209B7', '#4CC9F0'], // Purple to Cyan
    success: ['#FFD600', '#FF9E00'], // Gold to Orange
    error: ['#D90429', '#8D0801'] // Red to Dark Red
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
      meshRef.current.position.y = Math.sin(stateObj.clock.elapsedTime * speeds[state]) * 0.2;
    }
  });

  return (
    <group ref={meshRef} scale={state === 'idle' ? 1.2 : 1.8}>
      {/* Outer Quantum Shell */}
      <Icosahedron args={[1.2, 1]}>
        <meshStandardMaterial 
          wireframe={true} 
          emissive={emissiveColors[state]}
          emissiveIntensity={0.6}
          transparent={true}
          opacity={0.3}
          color="#ffffff"
        >
          <GradientTexture stops={[0, 1]} colors={gradients[state]} />
        </meshStandardMaterial>
      </Icosahedron>
      
      {/* Inner Probability Core */}
      <Sphere ref={coreRef} args={[0.8, 64, 64]}>
        <MeshDistortMaterial
          distort={distorts[state]}
          speed={speeds[state]}
          roughness={0.1}
          metalness={0.9}
          emissive={emissiveColors[state]}
          emissiveIntensity={0.2}
          color="#ffffff"
        >
          <GradientTexture stops={[0, 1]} colors={gradients[state]} />
        </MeshDistortMaterial>
      </Sphere>
      
      {/* Outer Orbiting Ring */}
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[1.5, 0.02, 16, 100]} />
        <meshStandardMaterial 
          emissive={emissiveColors[state]} 
          emissiveIntensity={0.8}
          color="#ffffff"
        >
          <GradientTexture stops={[0, 1]} colors={gradients[state]} />
        </meshStandardMaterial>
      </mesh>
    </group>
  );
}
