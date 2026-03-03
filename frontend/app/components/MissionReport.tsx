'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Code2, Brain, Film, Mic2, Cpu, ChevronDown, ChevronUp, Copy, Check, AlertTriangle
} from 'lucide-react';

type MissionData = {
  metadata: { algorithm: string; qubits: number | string };
  code: string;
  explanation: string;
  visuals: { video_prompt: string; image_prompt: string };
  audio_narration: string;
  nisq_warning?: string;
};

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button onClick={handleCopy} style={{
      background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.15)',
      borderRadius: '6px', padding: '6px 12px', cursor: 'pointer', color: '#fff',
      display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', transition: 'all 0.2s'
    }}>
      {copied ? <Check size={14} color="#00E676" /> : <Copy size={14} />}
      {copied ? 'Copied!' : 'Copy'}
    </button>
  );
}

function Section({
  icon, label, accentColor, children, defaultOpen = true
}: {
  icon: React.ReactNode; label: string; accentColor: string;
  children: React.ReactNode; defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div style={{ borderRadius: '12px', border: `1px solid rgba(255,255,255,0.08)`, overflow: 'hidden' }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          background: 'rgba(255,255,255,0.04)', padding: '14px 20px', border: 'none',
          cursor: 'pointer', color: '#fff'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ color: accentColor }}>{icon}</span>
          <span style={{ fontWeight: 700, fontSize: '13px', letterSpacing: '1px', textTransform: 'uppercase', color: accentColor }}>
            {label}
          </span>
        </div>
        {open ? <ChevronUp size={16} color="#8A8DAA" /> : <ChevronDown size={16} color="#8A8DAA" />}
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            style={{ overflow: 'hidden' }}
          >
            <div style={{ padding: '20px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function MissionReport({ data }: { data: MissionData }) {
  if (!data) return null;

  const metaItems = [
    { label: 'Algorithm', value: data.metadata?.algorithm || 'Unknown', color: '#00E5FF' },
    { label: 'Qubit Requirement', value: `${data.metadata?.qubits ?? 0} qubits`, color: '#FFD600' },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
      style={{ marginTop: '32px', display: 'flex', flexDirection: 'column', gap: '12px' }}
    >
      {/* Header Banner */}
      <div className="glass-panel" style={{
        padding: '24px 32px', border: '1px solid rgba(0, 229, 255, 0.3)',
        background: 'linear-gradient(135deg, rgba(0,229,255,0.06) 0%, rgba(213,0,249,0.04) 100%)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
          <Cpu size={22} color="#00E5FF" />
          <h2 style={{ fontSize: '20px', fontWeight: 800, letterSpacing: '1px', color: '#fff', margin: 0 }}>
            Mission Complete — Quantum Package Ready
          </h2>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
          {metaItems.map(({ label, value, color }) => (
            <div key={label} style={{
              background: 'rgba(0,0,0,0.35)', padding: '14px 18px',
              borderRadius: '10px', borderLeft: `3px solid ${color}`
            }}>
              <p style={{ color: '#8A8DAA', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '1px', margin: 0 }}>{label}</p>
              <p style={{ color, fontSize: '18px', fontWeight: 700, margin: '4px 0 0' }}>{value}</p>
            </div>
          ))}
        </div>
      </div>

      {/* NISQ Warning Banner */}
      {data.nisq_warning && (
        <div className="glass-panel" style={{
          padding: '14px 20px', border: '1px solid rgba(255, 214, 0, 0.3)',
          background: 'rgba(255, 214, 0, 0.05)', display: 'flex', alignItems: 'flex-start', gap: '12px'
        }}>
          <AlertTriangle size={18} color="#FFD600" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div>
            <p style={{ color: '#FFD600', fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '1px', margin: 0 }}>
              NISQ Hardware Warning (Non-Blocking)
            </p>
            <p style={{ color: '#c0c3db', fontSize: '13px', marginTop: '4px', lineHeight: '1.5' }}>{data.nisq_warning}</p>
          </div>
        </div>
      )}

      {/* Explanation */}
      <Section icon={<Brain size={16} />} label="Architect Explanation" accentColor="#D500F9" defaultOpen={true}>
        <p style={{ color: '#c0c3db', lineHeight: '1.75', fontSize: '15px', margin: 0 }}>{data.explanation}</p>
      </Section>

      {/* Generated Code */}
      <Section icon={<Code2 size={16} />} label="Generated Qiskit Code" accentColor="#00E5FF" defaultOpen={true}>
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '10px' }}>
          <CopyButton text={data.code} />
        </div>
        <pre style={{
          background: '#0a0a1a', color: '#00E676', padding: '20px', borderRadius: '10px',
          overflowX: 'auto', fontFamily: '"Fira Code", "Cascadia Code", monospace', fontSize: '13px',
          lineHeight: '1.65', margin: 0, border: '1px solid rgba(0, 230, 118, 0.1)'
        }}>
          <code>{data.code}</code>
        </pre>
      </Section>

      {/* Media Prompts */}
      <Section icon={<Film size={16} />} label="Visual Media Brief" accentColor="#D500F9" defaultOpen={false}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {data.visuals?.video_prompt && (
            <div style={{ background: 'rgba(213,0,249,0.07)', padding: '16px', borderRadius: '10px', border: '1px solid rgba(213,0,249,0.2)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <p style={{ fontSize: '11px', color: '#D500F9', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '1px', margin: 0 }}>
                  🎬 Veo Video Prompt
                </p>
                <CopyButton text={data.visuals.video_prompt} />
              </div>
              <p style={{ color: '#e0e0f0', fontSize: '14px', lineHeight: '1.65', margin: 0 }}>{data.visuals.video_prompt}</p>
            </div>
          )}
          {data.visuals?.image_prompt && (
            <div style={{ background: 'rgba(0,229,255,0.05)', padding: '16px', borderRadius: '10px', border: '1px solid rgba(0,229,255,0.15)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <p style={{ fontSize: '11px', color: '#00E5FF', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '1px', margin: 0 }}>
                  🖼 Imagen Concept Art Prompt
                </p>
                <CopyButton text={data.visuals.image_prompt} />
              </div>
              <p style={{ color: '#e0e0f0', fontSize: '14px', lineHeight: '1.65', margin: 0 }}>{data.visuals.image_prompt}</p>
            </div>
          )}
        </div>
      </Section>

      {/* Audio Narration */}
      {data.audio_narration && (
        <Section icon={<Mic2 size={16} />} label="Audio Narration Script" accentColor="#FFD600" defaultOpen={false}>
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '10px' }}>
            <CopyButton text={data.audio_narration} />
          </div>
          <blockquote style={{
            background: 'rgba(255,214,0,0.06)', padding: '20px 24px',
            borderLeft: '4px solid #FFD600', borderRadius: '0 10px 10px 0',
            fontStyle: 'italic', color: '#fff', fontSize: '16px', lineHeight: '1.75', margin: 0
          }}>
            &ldquo;{data.audio_narration}&rdquo;
          </blockquote>
        </Section>
      )}
    </motion.div>
  );
}
