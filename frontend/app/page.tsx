'use client';

import { useState, useRef, useEffect } from 'react';
import { Canvas } from '@react-three/fiber';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Terminal, Loader2, RotateCcw, X, Clock, Cpu } from 'lucide-react';
import QuantumSphere from './components/QuantumSphere';
import EventTimeline, { QuantumEvent } from './components/EventTimeline';
import MissionReport from './components/MissionReport';

type SessionSummary = {
  session_id: string;
  user_input: string;
  stage: string;
  attempt: number;
  created_at: string;
  updated_at: string;
};

export default function Home() {
  const [prompt, setPrompt] = useState('');
  const [status, setStatus] = useState<'idle' | 'generating' | 'success' | 'error'>('idle');
  const [events, setEvents] = useState<QuantumEvent[]>([]);
  const [finalData, setFinalData] = useState<any>(null);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [showSessionPanel, setShowSessionPanel] = useState(false);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const eventsEndRef = useRef<HTMLDivElement>(null);

  // Fetch saved sessions on mount
  useEffect(() => {
    fetchSessions();
  }, []);

  // Auto-scroll timeline
  useEffect(() => {
    if (eventsEndRef.current) {
      eventsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [events]);

  const fetchSessions = async () => {
    try {
      const res = await fetch('http://localhost:8000/sessions');
      if (res.ok) {
        const data = await res.json();
        setSessions(data);
      }
    } catch {
      // Backend not running, silently ignore
    }
  };

  const deleteSession = async (sessionId: string) => {
    try {
      await fetch(`http://localhost:8000/sessions/${sessionId}`, { method: 'DELETE' });
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
    } catch {
      // ignore
    }
  };

  const startWorkflow = (userPrompt: string, sessionId: string | null = null) => {
    if (status === 'generating') return;

    setStatus('generating');
    setEvents([]);
    setFinalData(null);
    setShowSessionPanel(false);
    setActiveSessionId(sessionId);

    const ws = new WebSocket('ws://localhost:8000/ws/simulate');
    wsRef.current = ws;

    ws.onopen = () => {
      if (sessionId) {
        // Resume mode: send JSON payload
        ws.send(JSON.stringify({ prompt: userPrompt, session_id: sessionId }));
        setEvents([{ type: 'progress', agent: 'System', status: `Resuming session ${sessionId.slice(0, 8)}...` }]);
      } else {
        ws.send(userPrompt);
        setEvents([{ type: 'progress', agent: 'System', status: 'WebSocket connected. Sending payload...' }]);
      }
    };

    ws.onmessage = (event) => {
      try {
        const data: QuantumEvent = JSON.parse(event.data);
        setEvents((prev) => [...prev, data]);

        // Capture session_id from backend if it sends one
        if (data.session_id) {
          setActiveSessionId(data.session_id);
        }

        if (data.type === 'complete' && data.data) {
          setFinalData(data.data);
          setStatus('success');
          setActiveSessionId(null);
          ws.close();
          fetchSessions(); // Refresh — completed sessions get cleaned up
        } else if (data.type === 'fatal' || (data.type === 'error' && data.agent === 'Orchestrator')) {
          setStatus('error');
          ws.close();
          fetchSessions(); // A checkpoint may have been saved before the error
        }
      } catch (err) {
        console.error("Failed to parse WS message", err);
      }
    };

    ws.onerror = () => {
      setEvents((prev) => [...prev, { type: 'fatal', agent: 'Network', status: 'WebSocket connection error. Is the backend running?' }]);
      setStatus('error');
      fetchSessions();
    };

    ws.onclose = () => {
      setStatus(prev => (prev === 'generating' ? 'error' : prev));
      fetchSessions();
    };
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || status === 'generating') return;
    startWorkflow(prompt);
  };

  const handleResume = (session: SessionSummary) => {
    setPrompt(session.user_input);
    startWorkflow(session.user_input, session.session_id);
  };

  const stageLabel = (stage: string) => {
    const labels: Record<string, string> = {
      CREATED: 'Starting',
      TRANSLATED: 'Translated',
      ARCHITECTED: 'Circuit Built',
      AUDITED: 'Audited',
      EVALUATED: 'Evaluated',
      COMPLETED: 'Completed',
    };
    return labels[stage] || stage;
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

        {/* Resume Sessions Banner */}
        <AnimatePresence>
          {sessions.length > 0 && status !== 'generating' && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              style={{ marginBottom: '24px' }}
            >
              <button
                onClick={() => setShowSessionPanel(!showSessionPanel)}
                style={{
                  width: '100%',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px',
                  padding: '14px 20px',
                  background: 'linear-gradient(135deg, rgba(213, 0, 249, 0.12), rgba(0, 229, 255, 0.12))',
                  border: '1px solid rgba(213, 0, 249, 0.35)',
                  borderRadius: '12px',
                  color: '#D500F9',
                  fontWeight: 600,
                  fontSize: '14px',
                  cursor: 'pointer',
                  letterSpacing: '0.5px',
                  transition: 'all 0.2s ease',
                }}
              >
                <RotateCcw size={16} />
                {sessions.length} interrupted session{sessions.length > 1 ? 's' : ''} — Click to resume
              </button>

              {/* Session List Panel */}
              <AnimatePresence>
                {showSessionPanel && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    style={{ overflow: 'hidden' }}
                  >
                    <div className="glass-panel" style={{ marginTop: '12px', padding: '16px', maxHeight: '300px', overflowY: 'auto' }}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        {sessions.map((session) => (
                          <div
                            key={session.session_id}
                            style={{
                              display: 'flex', alignItems: 'center', gap: '12px',
                              padding: '12px 16px',
                              background: 'rgba(255,255,255,0.03)',
                              border: '1px solid rgba(255,255,255,0.08)',
                              borderRadius: '8px',
                              transition: 'border-color 0.2s',
                            }}
                          >
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <div style={{ fontSize: '13px', color: '#fff', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {session.user_input}
                              </div>
                              <div style={{ display: 'flex', gap: '16px', marginTop: '6px', fontSize: '12px', color: '#8A8DAA' }}>
                                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                  <Cpu size={12} />
                                  {stageLabel(session.stage)}
                                </span>
                                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                  <Clock size={12} />
                                  {new Date(session.updated_at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                                </span>
                              </div>
                            </div>

                            <button
                              onClick={() => handleResume(session)}
                              style={{
                                padding: '8px 16px',
                                background: 'rgba(0, 229, 255, 0.15)',
                                border: '1px solid rgba(0, 229, 255, 0.4)',
                                borderRadius: '6px',
                                color: '#00E5FF',
                                fontSize: '12px',
                                fontWeight: 600,
                                cursor: 'pointer',
                                whiteSpace: 'nowrap',
                              }}
                            >
                              Resume
                            </button>
                            <button
                              onClick={() => deleteSession(session.session_id)}
                              title="Delete session"
                              style={{
                                padding: '6px',
                                background: 'transparent',
                                border: '1px solid rgba(255,23,68,0.3)',
                                borderRadius: '6px',
                                color: '#FF1744',
                                cursor: 'pointer',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                              }}
                            >
                              <X size={14} />
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          )}
        </AnimatePresence>

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

        {/* Input Bar pinned to bottom */}
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
