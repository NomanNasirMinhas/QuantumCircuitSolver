'use client';

import { useState, useRef, useEffect } from 'react';
import { Canvas } from '@react-three/fiber';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Terminal } from 'lucide-react';
import QuantumSphere from './components/QuantumSphere';
import EventTimeline, { QuantumEvent } from './components/EventTimeline';
import MissionReport from './components/MissionReport';

export default function Home() {
  const [prompt, setPrompt] = useState('');
  const [status, setStatus] = useState<'idle' | 'generating' | 'success' | 'error'>('idle');
  const [events, setEvents] = useState<QuantumEvent[]>([]);
  const [finalData, setFinalData] = useState<any>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const eventsEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll timeline
  useEffect(() => {
    if (eventsEndRef.current) {
      eventsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [events]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || status === 'generating') return;

    // Reset state
    setStatus('generating');
    setEvents([]);
    setFinalData(null);

    // Initialize WebSocket
    const ws = new WebSocket('ws://localhost:8000/ws/simulate');
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(prompt);
      setEvents([{ type: 'progress', agent: 'System', status: 'WebSocket connected. Sending payload...' }]);
    };

    ws.onmessage = (event) => {
      try {
        const data: QuantumEvent = JSON.parse(event.data);
        setEvents((prev) => [...prev, data]);
        
        if (data.type === 'complete' && data.data) {
          setFinalData(data.data);
          setStatus('success');
          ws.close();
        } else if (data.type === 'fatal' || (data.type === 'error' && data.agent === 'Orchestrator')) {
          setStatus('error');
          ws.close();
        }
      } catch (err) {
        console.error("Failed to parse WS message", err);
      }
    };

    ws.onerror = () => {
      setEvents((prev) => [...prev, { type: 'fatal', agent: 'Network', status: 'WebSocket connection error. Is the backend running?' }]);
      setStatus('error');
    };

    ws.onclose = () => {
      if (status === 'generating') setStatus('error');
    };
  };

  return (
    <div style={{ position: 'relative', minHeight: '100vh', width: '100vw', overflowX: 'hidden' }}>
      
      {/* 3D Background */}
      <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', zIndex: 0, pointerEvents: 'none' }}>
        <Canvas camera={{ position: [0, 0, 5], fov: 45 }}>
          <ambientLight intensity={0.5} />
          <directionalLight position={[10, 10, 5]} intensity={1} />
          <QuantumSphere state={status} />
        </Canvas>
      </div>

      {/* Foreground UI */}
      <main style={{ position: 'relative', zIndex: 10, maxWidth: '1000px', margin: '0 auto', padding: '40px 20px', display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        
        <header style={{ textAlign: 'center', marginBottom: '40px' }}>
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '12px', background: 'rgba(0, 229, 255, 0.1)', padding: '8px 16px', borderRadius: '24px', border: '1px solid rgba(0, 229, 255, 0.3)', marginBottom: '16px' }}>
              <Terminal size={18} color="#00E5FF" />
              <span style={{ color: '#00E5FF', fontWeight: 600, fontSize: '14px', letterSpacing: '1px' }}>AGENTIC CORE ONLINE</span>
            </div>
            
            <h1 style={{ fontSize: '48px', fontWeight: 800, letterSpacing: '-1px', background: 'linear-gradient(to right, #00E5FF, #D500F9)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', marginBottom: '16px' }}>
              Quantum Circuit Orchestrator
            </h1>
            <p style={{ color: '#8A8DAA', fontSize: '18px', maxWidth: '600px', margin: '0 auto', lineHeight: '1.6' }}>
              Describe a complex algorithmic problem. Our swarm of specialized quantum agents will design, validate, and simulate the exact circuit required to solve it.
            </p>
          </motion.div>
        </header>

        {/* Dynamic Content Area (Timeline or Results) */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '24px', marginBottom: '40px' }}>
          
          <AnimatePresence mode="popLayout">
            {events.length > 0 && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
              >
                <EventTimeline events={events} />
                <div ref={eventsEndRef} />
              </motion.div>
            )}

            {finalData && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
              >
                <MissionReport data={finalData} />
              </motion.div>
            )}
          </AnimatePresence>

        </div>

        {/* Input Bar pinned to bottom mostly */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="glass-panel" 
          style={{ padding: '8px', position: 'sticky', bottom: '24px', marginTop: 'auto' }}
        >
          <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '12px' }}>
            <input
              type="text"
              className="glass-input"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="E.g., I need to find the shortest path for an attacker scaling a 200 node network..."
              disabled={status === 'generating'}
            />
            <button 
              type="submit" 
              className="glass-button" 
              disabled={!prompt.trim() || status === 'generating'}
              style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
            >
              {status === 'generating' ? <Loader2 className="animate-spin" size={20} /> : <Send size={20} />}
              <span>{status === 'generating' ? 'ORCHESTRATING...' : 'EXECUTE'}</span>
            </button>
          </form>
        </motion.div>

      </main>
    </div>
  );
}

// Temporary import for the loader icon since it's used in the button above
import { Loader2 } from 'lucide-react';
