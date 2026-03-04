'use client';

import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { Canvas } from '@react-three/fiber';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, BrainCircuit, Play, Terminal, XCircle, Lightbulb, Pause, Loader2, Send } from 'lucide-react';
import QuantumParticleField from './components/QuantumSphere';
import EventTimeline, { QuantumEvent } from './components/EventTimeline';

type SessionSummary = {
  session_id: string;
  user_input: string;
  stage: string;
  attempt: number;
  created_at: string;
  updated_at: string;
};

type FinalResultData = {
  metadata?: { algorithm: string; qubits: number };
  story_explanation?: string;
  code?: string;
  explanation?: string;
  visuals?: {
    video_prompt?: string;
    circuit_diagram?: string; // base64 encoded image
  };
  audio_narration?: string; // base64 encoded audio
  nisq_warning?: string;
};

export default function Home() {
  const [prompt, setPrompt] = useState('');
  const [isSimulating, setIsSimulating] = useState(false);
  const [events, setEvents] = useState<QuantumEvent[]>([]);
  const [finalResult, setFinalResult] = useState<FinalResultData | null>(null);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [showSessionPanel, setShowSessionPanel] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const eventsEndRef = useRef<HTMLDivElement>(null);

  // Audio Player State
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);

  const fetchSessions = async () => {
    try {
      const res = await fetch('http://localhost:8000/sessions');
      if (res.ok) {
        const data = await res.json();
        setSessions(data);
      }
    } catch (err) {
      console.error('Failed to fetch sessions:', err);
    }
  };

  useEffect(() => {
    fetchSessions(); 
  }, []);

  // Auto-scroll timeline
  useEffect(() => {
    eventsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  const deleteSession = async (sessionId: string) => {
    try {
      const res = await fetch(`http://localhost:8000/sessions/${sessionId}`, { method: 'DELETE' });
      if (res.ok) {
        fetchSessions();
      }
    } catch (err) {
      console.error('Failed to delete session:', err);
    }
  };

  const startWorkflow = (userPrompt: string, sessionId: string | null = null) => {
    if (isSimulating) return;

    setIsSimulating(true);
    setEvents([]);
    setFinalResult(null);
    setShowSessionPanel(false);

    // Stop and reset audio if playing
    if (audioRef.current && isPlayingAudio) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setIsPlayingAudio(false);
    }

    const ws = new WebSocket('ws://localhost:8000/ws/simulate');
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({ prompt: userPrompt, session_id: sessionId }));
    };

    ws.onmessage = (event) => {
      try {
        const data: QuantumEvent = JSON.parse(event.data);

        // Filter out agent thinking trace logging
        if (data.type === 'progress' && data.status.startsWith('T')) return;

        if (data.type === 'complete' && data.data) {
          setFinalResult(data.data as FinalResultData);
          setIsSimulating(false);
          ws.close();
          fetchSessions(); // Refresh — completed sessions get cleaned up
        } else if (data.type === 'fatal') {
          setEvents((prev) => [...prev, data]);
          setIsSimulating(false);
          ws.close();
          fetchSessions(); // A checkpoint may have been saved before the error
        } else {
          setEvents((prev) => [...prev, data]);
        }
      } catch (err) {
        console.error("Failed to parse WS message", err);
      }
    };

    ws.onerror = () => {
      setEvents((prev) => [...prev, { type: 'fatal', agent: 'Network', status: 'WebSocket connection error. Is the backend running?' }]);
      setIsSimulating(false);
      fetchSessions();
    };

    ws.onclose = () => {
      setIsSimulating(prev => (prev === true ? false : prev)); // If still simulating, set to false
      fetchSessions();
    };
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || isSimulating) return;
    startWorkflow(prompt);
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

  const getStageColor = (stage: string) => {
    const colors: Record<string, string> = {
      CREATED: '#8A8DAA',
      TRANSLATED: '#00E5FF',
      ARCHITECTED: '#D500F9',
      AUDITED: '#FFD600',
      EVALUATED: '#00E5FF',
      COMPLETED: '#00E5FF',
    };
    return colors[stage] || '#8A8DAA';
  };

  const handleAudioPlayPause = () => {
    if (audioRef.current) {
      if (isPlayingAudio) {
        audioRef.current.pause();
      } else {
        audioRef.current.play();
      }
      setIsPlayingAudio(!isPlayingAudio);
    }
  };

  return (
    <div style={{ position: 'relative', minHeight: '100vh', width: '100vw', overflowX: 'hidden' }}>

      {/* 3D Background */}
      <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', zIndex: 0, pointerEvents: 'none' }}>
        <Canvas camera={{ position: [0, 0, 5], fov: 45 }}>
          <ambientLight intensity={0.5} />
          <directionalLight position={[10, 10, 5]} intensity={1} />
          <QuantumParticleField state={isSimulating ? 'generating' : 'idle'} />
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
              <BrainCircuit size={18} color="#00E5FF" />
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
          {sessions.length > 0 && !isSimulating && (
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
                <Activity size={16} />
                {sessions.length} interrupted session{sessions.length > 1 ? 's' : ''} — Click to resume
              </button>

              {/* Session List Panel */}
              {/* Session List Panel */}
              <AnimatePresence>
                {showSessionPanel && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.3 }}
                    style={{ overflow: 'hidden' }}
                  >
                    <div style={{
                      background: 'rgba(20, 24, 34, 0.95)',
                      borderRadius: '16px',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      marginBottom: '24px',
                      boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
                    }}>
                      <div style={{ padding: '16px 24px', borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
                        <h3 style={{ margin: 0, color: '#fff', fontSize: '16px', fontWeight: 600 }}>Active Simulation Pipelines</h3>
                      </div>
                      <div style={{ padding: '16px 24px', display: 'flex', flexDirection: 'column', gap: '12px', maxHeight: '300px', overflowY: 'auto' }} className="custom-scrollbar">
                        {sessions.map((session) => (
                          <div 
                            key={session.session_id}
                            style={{
                              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                              background: 'rgba(0, 0, 0, 0.3)', padding: '12px 16px', borderRadius: '12px',
                              border: '1px solid rgba(255, 255, 255, 0.05)', transition: 'all 0.2s',
                              cursor: 'pointer'
                            }}
                            onClick={() => startWorkflow(session.user_input, session.session_id)}
                            onMouseOver={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'}
                            onMouseOut={(e) => e.currentTarget.style.background = 'rgba(0, 0, 0, 0.3)'}
                          >
                            <div style={{ flex: 1, overflow: 'hidden', marginRight: '16px' }}>
                              <div style={{ color: '#fff', fontSize: '14px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', marginBottom: '4px' }}>
                                &quot;{session.user_input}&quot;
                              </div>
                              <div style={{ display: 'flex', gap: '16px', color: 'rgba(255, 255, 255, 0.5)', fontSize: '12px' }}>
                                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                  <Terminal size={12} color={getStageColor(session.stage)} />
                                  {stageLabel(session.stage)}
                                </span>
                                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                  <Activity size={12} />
                                  {new Date(session.updated_at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                                </span>
                              </div>
                            </div>
                            
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                deleteSession(session.session_id);
                              }}
                              style={{
                                background: 'transparent', border: 'none', color: 'rgba(255, 255, 255, 0.3)', cursor: 'pointer',
                                padding: '8px', borderRadius: '8px', transition: 'all 0.2s',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                              }}
                            >
                              <XCircle size={14} color="#FF1744" />
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
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {events.map((event, i) => (
                    <div key={i} style={{ 
                      padding: '12px 16px', background: 'rgba(0,0,0,0.4)', borderRadius: '8px',
                      borderLeft: `4px solid ${event.type === 'error' ? '#FF1744' : event.type === 'warning' ? '#FFD600' : '#00E5FF'}`,
                      display: 'flex', flexDirection: 'column', gap: '6px'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '1px', color: 'rgba(255,255,255,0.5)', background: 'rgba(255,255,255,0.1)', padding: '2px 6px', borderRadius: '4px' }}>
                          {event.type}
                        </span>
                        <span style={{ fontSize: '13px', color: '#00E5FF', fontWeight: 500, fontFamily: 'monospace' }}>
                          {event.agent}
                        </span>
                      </div>
                      <div style={{ fontSize: '14px', color: '#E2E8F0', lineHeight: '1.5', fontFamily: 'monospace' }}>
                        <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>{event.status}</ReactMarkdown>
                      </div>
                    </div>
                  ))}
                  <div ref={eventsEndRef} />
                </div>
              </motion.div>
            )}

            {finalResult && !isSimulating && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}
              >
                {finalResult.nisq_warning && (
                  <div style={{ padding: '16px', background: 'rgba(255, 23, 68, 0.1)', borderLeft: '4px solid #FF1744', borderRadius: '8px', display: 'flex', gap: '12px' }}>
                    <Activity size={20} color="#FF1744" style={{ flexShrink: 0, marginTop: '2px' }} />
                    <div>
                      <h3 style={{ margin: '0 0 4px 0', color: '#FF1744', fontSize: '14px', fontWeight: 600 }}>Hardware Coherence Warning</h3>
                      <p style={{ margin: 0, color: 'rgba(255,255,255,0.8)', fontSize: '13px', lineHeight: '1.5' }}>
                        {finalResult.nisq_warning}
                      </p>
                    </div>
                  </div>
                )}

                {/* Story Context Panel */}
                {finalResult.story_explanation && (
                  <div style={{ background: 'rgba(20, 24, 34, 0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '16px', padding: '24px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                      <Lightbulb size={20} color="#FFD600" />
                      <h2 style={{ margin: 0, color: '#fff', fontSize: '18px', fontWeight: 600, fontFamily: 'monospace' }}>Quantum Story Context</h2>
                    </div>
                    <div style={{ color: 'rgba(255,255,255,0.8)', fontSize: '14px', lineHeight: '1.6', maxHeight: '300px', overflowY: 'auto' }} className="custom-scrollbar">
                      <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
                        {finalResult.story_explanation}
                      </ReactMarkdown>
                    </div>
                  </div>
                )}

                {/* Multimedia Panel */}
                <div style={{ background: 'rgba(20, 24, 34, 0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '16px', padding: '24px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                    <Play size={20} color="#00E5FF" />
                    <h2 style={{ margin: 0, color: '#fff', fontSize: '18px', fontWeight: 600, fontFamily: 'monospace' }}>Multimedia Assets</h2>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
                    
                    {/* Audio Player */}
                    <div style={{ background: 'rgba(0,0,0,0.5)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '12px', padding: '16px' }}>
                      <div style={{ fontSize: '12px', color: '#FFD600', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '12px', fontFamily: 'monospace' }}>Narrative Audio</div>
                      {finalResult.audio_narration ? (
                        finalResult.audio_narration.includes(' ') || finalResult.audio_narration.length < 500 ? (
                            <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.7)', fontStyle: 'italic', maxHeight: '150px', overflowY: 'auto' }} className="custom-scrollbar">
                              <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>{finalResult.audio_narration}</ReactMarkdown>
                            </div>
                          ) : (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                              <audio 
                                ref={audioRef} 
                                src={`data:audio/mp3;base64,${finalResult.audio_narration}`} 
                                onEnded={() => setIsPlayingAudio(false)} 
                                onPause={() => setIsPlayingAudio(false)}
                                onPlay={() => setIsPlayingAudio(true)}
                                style={{ display: 'none' }} 
                              />
                              <button 
                                onClick={handleAudioPlayPause}
                                style={{ 
                                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                                  padding: '16px', background: 'rgba(0, 229, 255, 0.1)', border: '1px solid rgba(0, 229, 255, 0.3)',
                                  borderRadius: '50%', color: '#00E5FF', cursor: 'pointer', transition: 'all 0.2s'
                                }}
                              >
                                {isPlayingAudio ? <Pause size={24} /> : <Play size={24} style={{ marginLeft: '4px' }} />}
                              </button>
                              <div style={{ fontSize: '14px', color: 'rgba(255,255,255,0.8)', fontFamily: 'monospace' }}>
                                {isPlayingAudio ? 'Playing Narrative...' : 'Play Scenario Narrative'}
                              </div>
                            </div>
                          )
                      ) : (
                        <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.4)', fontStyle: 'italic' }}>No audio generated</div>
                      )}
                    </div>

                    {/* Video Prompt */}
                    <div style={{ background: 'rgba(0,0,0,0.5)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '12px', padding: '16px' }}>
                      <div style={{ fontSize: '12px', color: '#D500F9', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '12px', fontFamily: 'monospace' }}>Veo Video Prompt</div>
                      {finalResult.visuals?.video_prompt ? (
                        <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.7)', fontStyle: 'italic', borderLeft: '2px solid #D500F9', paddingLeft: '12px', maxHeight: '150px', overflowY: 'auto' }} className="custom-scrollbar">
                          &quot;{finalResult.visuals.video_prompt}&quot;
                        </div>
                      ) : (
                        <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.4)', fontStyle: 'italic' }}>No prompt generated</div>
                      )}
                    </div>

                  </div>
                </div>

                {/* Circuit Info (Code, Diagram, Explanation) */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '24px' }}>
                  
                  {/* Circuit Visuals */}
                  <div style={{ background: 'rgba(20, 24, 34, 0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '16px', padding: '24px', display: 'flex', flexDirection: 'column' }}>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '16px' }}>
                      <Terminal size={20} color="#00E5FF" />
                      <h2 style={{ margin: 0, color: '#fff', fontSize: '18px', fontWeight: 600, fontFamily: 'monospace' }}>Architectural Circuit</h2>
                    </div>
                    
                    <div style={{ flex: 1, minHeight: '400px', background: '#0d1117', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)', overflow: 'hidden', position: 'relative', display: 'flex' }}>
                       {finalResult.visuals?.circuit_diagram ? (
                          <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px', overflow: 'auto' }}>
                            <img 
                              src={`data:image/png;base64,${finalResult.visuals.circuit_diagram}`} 
                              alt="Generated Quantum Circuit Diagram" 
                              style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', background: 'white', borderRadius: '4px' }}
                            />
                          </div>
                        ) : (finalResult.code ? (
                          <pre style={{ padding: '16px', margin: 0, fontSize: '13px', color: 'rgba(255,255,255,0.9)', fontFamily: 'monospace', whiteSpace: 'pre-wrap', overflow: 'auto', width: '100%' }}>
                            {finalResult.code}
                          </pre>
                        ) : (
                          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '13px', fontFamily: 'monospace' }}>
                            No circuit generated.
                          </div>
                        ))}
                    </div>
                  </div>

                  {/* Math/Logic Explanation */}
                  <div style={{ background: 'rgba(20, 24, 34, 0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '16px', padding: '24px' }}>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '16px' }}>
                      <BrainCircuit size={20} color="#D500F9" />
                      <h2 style={{ margin: 0, color: '#fff', fontSize: '18px', fontWeight: 600, fontFamily: 'monospace' }}>Algorithm Explanation</h2>
                    </div>
                    <div style={{ color: 'rgba(255,255,255,0.8)', fontSize: '14px', lineHeight: '1.6' }} className="markdown-body">
                      {finalResult.explanation ? (
                        <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
                          {finalResult.explanation}
                        </ReactMarkdown>
                      ) : (
                        <span style={{ fontStyle: 'italic', color: 'rgba(255,255,255,0.4)' }}>No explanation available.</span>
                      )}
                    </div>
                  </div>

                </div>

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
              disabled={isSimulating}
            />
            <button
              type="submit"
              className="glass-button"
              disabled={!prompt.trim() || isSimulating}
              style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
            >
              {isSimulating ? <Loader2 className="animate-spin" size={20} /> : <Send size={20} />}
              <span>{isSimulating ? 'ORCHESTRATING...' : 'EXECUTE'}</span>
            </button>
          </form>
        </motion.div>


      </main>
    </div>
  );
}
