'use client';

import { motion } from 'framer-motion';

type Visuals = {
    video_prompt: string;
    image_prompt: string;
};

type MissionData = {
    metadata: { algorithm: string; qubits: number | string };
    code: string;
    explanation: string;
    visuals: Visuals;
    audio_narration: string;
};

export default function MissionReport({ data }: { data: MissionData }) {
  if (!data) return null;

  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
      className="glass-panel" 
      style={{ padding: '32px', marginTop: '32px', border: '1px solid #00E5FF' }}
    >
      <h2 style={{ color: '#00E5FF', marginBottom: '24px', fontSize: '24px', letterSpacing: '1px' }}>
        Quantum Execution Output
      </h2>
      
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginBottom: '24px' }}>
        <div style={{ background: 'rgba(0,0,0,0.4)', padding: '16px', borderRadius: '8px' }}>
          <strong style={{ color: '#8A8DAA', fontSize: '12px', textTransform: 'uppercase' }}>Mapped Algorithm</strong>
          <p style={{ color: '#fff', fontSize: '18px', marginTop: '4px' }}>{data.metadata?.algorithm || 'Unknown'}</p>
        </div>
        <div style={{ background: 'rgba(0,0,0,0.4)', padding: '16px', borderRadius: '8px' }}>
          <strong style={{ color: '#8A8DAA', fontSize: '12px', textTransform: 'uppercase' }}>Qubit Requirement</strong>
          <p style={{ color: '#FFD600', fontSize: '18px', marginTop: '4px' }}>{data.metadata?.qubits || 0}</p>
        </div>
      </div>

      <div style={{ marginBottom: '24px' }}>
        <strong style={{ color: '#D500F9', fontSize: '14px', textTransform: 'uppercase', letterSpacing: '1px' }}>Architect Explanation</strong>
        <p style={{ color: '#c0c3db', lineHeight: '1.6', marginTop: '8px' }}>
          {data.explanation}
        </p>
      </div>

      <div style={{ marginBottom: '24px' }}>
        <strong style={{ color: '#00E5FF', fontSize: '14px', textTransform: 'uppercase', letterSpacing: '1px' }}>Generated Qiskit Code</strong>
        <pre style={{ 
          background: '#050510', 
          color: '#00E676', 
          padding: '16px', 
          borderRadius: '8px', 
          overflowX: 'auto', 
          marginTop: '8px',
          fontFamily: 'monospace',
          fontSize: '14px'
        }}>
          <code>{data.code}</code>
        </pre>
      </div>

      <div style={{ marginBottom: '24px', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '24px' }}>
        <strong style={{ color: '#D500F9', fontSize: '14px', textTransform: 'uppercase', letterSpacing: '1px' }}>Visual Media Prompts</strong>
        
        <div style={{ marginTop: '12px' }}>
          <p style={{ fontSize: '12px', color: '#8A8DAA', textTransform: 'uppercase' }}>Generative Video (Veo)</p>
          <p style={{ color: '#fff', fontSize: '14px', marginTop: '4px', background: 'rgba(255,255,255,0.05)', padding: '12px', borderRadius: '4px' }}>
            {data.visuals?.video_prompt}
          </p>
        </div>
        
        <div style={{ marginTop: '12px' }}>
          <p style={{ fontSize: '12px', color: '#8A8DAA', textTransform: 'uppercase' }}>Generative Concept Art (Imagen)</p>
          <p style={{ color: '#fff', fontSize: '14px', marginTop: '4px', background: 'rgba(255,255,255,0.05)', padding: '12px', borderRadius: '4px' }}>
            {data.visuals?.image_prompt}
          </p>
        </div>
      </div>

      <div>
        <strong style={{ color: '#FFD600', fontSize: '14px', textTransform: 'uppercase', letterSpacing: '1px' }}>Audio Narration Script</strong>
        <p style={{ color: '#fff', fontSize: '16px', fontStyle: 'italic', marginTop: '8px', background: 'rgba(255,214,0,0.1)', padding: '16px', borderLeft: '4px solid #FFD600', borderRadius: '0 8px 8px 0' }}>
          "{data.audio_narration}"
        </p>
      </div>

    </motion.div>
  );
}
