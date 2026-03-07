'use client';

import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { Canvas } from '@react-three/fiber';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, BrainCircuit, Play, Terminal, XCircle, Lightbulb, Loader2, Send } from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
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

type PreviousRunSummary = {
  run_id: string;
  session_id: string;
  prompt: string;
  status: string;
  has_final_package: boolean;
  identified_algorithm?: string;
  created_at: string;
  updated_at: string;
};

type PreviousRunDetail = PreviousRunSummary & {
  run_context?: Record<string, unknown> | null;
  mapping?: Record<string, unknown> | null;
  final_package?: FinalResultData | null;
};

type FinalResultData = {
  metadata?: { algorithm: string; qubits: number };
  problem_algorithm_mapping?: {
    problem_class?: string;
    identified_algorithm?: string;
    why_this_algorithm?: string;
    how_user_problem_maps?: string;
  };
  quantum_story_context?: string;
  complete_code?: string;
  algorithm_explanation?: string;
  video_prompt?: string;
  imagen_graphic_prompt?: string;
  qiskit_circuit_diagram?: string;
  generated_illustration?: string;
  generated_illustration_mime?: string;
  generated_video?: string;
  generated_video_mime?: string;
  generated_video_uri?: string;
  result_diagram?: string;
  narrative_audio?: string;
  narrative_audio_mime?: string;
  simulation_results?: {
    status?: string;
    histogram?: Record<string, number>;
    raw_output?: string;
    error?: unknown;
  };
  nisq_warning?: string;
};

type AccessCodeResponse = {
  ok?: boolean;
  reason?: string;
  message?: string;
  access_token?: string;
  total?: number;
  used?: number;
  remaining?: number;
  exhausted?: boolean;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/simulate';
const MAX_WS_RECONNECT_ATTEMPTS = 3;

const PRESET_PROMPTS = [
  'Find the shortest path in a 10-node network using a Grover-style search strategy.',
  'Factor the number 15 and explain the quantum logic pedagogically.',
  'Simulate the hydrogen molecule ground state using a compact VQE ansatz.',
  'Solve a 4-city traveling salesman problem using a QAOA-inspired circuit.',
];

export default function Home() {
  const [accessCode, setAccessCode] = useState('');
  const [accessToken, setAccessToken] = useState('');
  const [isAccessGranted, setIsAccessGranted] = useState(false);
  const [isCheckingAccess, setIsCheckingAccess] = useState(true);
  const [isSubmittingAccessCode, setIsSubmittingAccessCode] = useState(false);
  const [accessError, setAccessError] = useState('');
  const [accessInfo, setAccessInfo] = useState<AccessCodeResponse | null>(null);

  const [prompt, setPrompt] = useState('');
  const [isSimulating, setIsSimulating] = useState(false);
  const [events, setEvents] = useState<QuantumEvent[]>([]);
  const [finalResult, setFinalResult] = useState<FinalResultData | null>(null);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [showSessionPanel, setShowSessionPanel] = useState(false);
  const [previousRuns, setPreviousRuns] = useState<PreviousRunSummary[]>([]);
  const [isLoadingPreviousRuns, setIsLoadingPreviousRuns] = useState(true);
  const [previousRunsError, setPreviousRunsError] = useState('');
  const [loadingRunId, setLoadingRunId] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const workflowFinishedRef = useRef(false);
  const currentPromptRef = useRef('');
  const currentSessionIdRef = useRef<string | null>(null);
  const currentAccessTokenRef = useRef('');

  const fetchAccessStatus = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/access/status`);
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data: AccessCodeResponse = await res.json();
      setAccessInfo(data);
      return data;
    } catch (err) {
      console.error('Failed to fetch access status:', err);
      return null;
    }
  };

  const submitAccessCode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!accessCode.trim() || isSubmittingAccessCode) return;

    setIsSubmittingAccessCode(true);
    setAccessError('');

    try {
      const res = await fetch(`${API_BASE_URL}/access/consume`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: accessCode.trim() }),
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const data: AccessCodeResponse = await res.json();
      setAccessInfo(data);

      if (data.ok) {
        const token = data.access_token || '';
        if (!token) {
          setAccessError('Access token was not returned by backend. Try again.');
          return;
        }
        setAccessToken(token);
        currentAccessTokenRef.current = token;
        setIsAccessGranted(true);
        setAccessCode('');
        setAccessError('');
      } else if (data.reason === 'exhausted') {
        setAccessError('All access codes are exhausted. Ask admin to reset codes.');
      } else if (data.reason === 'already_used') {
        setAccessError('This code was already used. Please enter a fresh code.');
      } else {
        setAccessError(data.message || 'Invalid access code.');
      }
    } catch (err) {
      console.error('Failed to submit access code:', err);
      setAccessError('Unable to validate access code. Check backend connectivity.');
    } finally {
      setIsSubmittingAccessCode(false);
    }
  };

  const fetchSessions = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/sessions`);
      if (res.ok) {
        const data = await res.json();
        setSessions(data);
      }
    } catch (err) {
      console.error('Failed to fetch sessions:', err);
    }
  };

  const fetchPreviousRuns = async () => {
    setIsLoadingPreviousRuns(true);
    setPreviousRunsError('');
    try {
      const res = await fetch(`${API_BASE_URL}/runs/history?limit=200`);
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data: PreviousRunSummary[] = await res.json();
      setPreviousRuns(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to fetch previous runs:', err);
      setPreviousRunsError('Unable to load previous runs right now.');
      setPreviousRuns([]);
    } finally {
      setIsLoadingPreviousRuns(false);
    }
  };

  const loadPreviousRun = async (runId: string) => {
    if (!runId || loadingRunId) return;
    setLoadingRunId(runId);
    setPreviousRunsError('');
    try {
      const res = await fetch(`${API_BASE_URL}/runs/history/${encodeURIComponent(runId)}`);
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const detail: PreviousRunDetail = await res.json();
      if (!detail.final_package) {
        setPreviousRunsError('This run does not have a final result package yet.');
        return;
      }
      setEvents([]);
      setFinalResult(detail.final_package);
      setPrompt(detail.prompt || '');
      setIsSimulating(false);
      setAccessError('');
      setShowSessionPanel(false);
    } catch (err) {
      console.error('Failed to load previous run:', err);
      setPreviousRunsError('Unable to load this run.');
    } finally {
      setLoadingRunId(null);
    }
  };

  const recoverCompletedRunFromHistory = async (runId: string | null | undefined) => {
    if (!runId) return false;
    try {
      const res = await fetch(`${API_BASE_URL}/runs/history/${encodeURIComponent(runId)}`);
      if (!res.ok) return false;
      const detail: PreviousRunDetail = await res.json();
      if (!detail.final_package) return false;

      workflowFinishedRef.current = true;
      setFinalResult(detail.final_package);
      setIsSimulating(false);
      setIsAccessGranted(false);
      setAccessToken('');
      currentAccessTokenRef.current = '';
      setEvents((prev) => [
        ...prev,
        {
          type: 'success',
          agent: 'Orchestrator',
          status: 'Recovered final result from completed run history.',
        },
      ]);
      void fetchAccessStatus();
      void fetchPreviousRuns();
      return true;
    } catch (err) {
      console.error('Failed to recover completed run from history:', err);
      return false;
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      void fetchAccessStatus().finally(() => setIsCheckingAccess(false));
      void fetchPreviousRuns();
    }, 0);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!isAccessGranted) return;
    const timer = setTimeout(() => {
      void fetchSessions();
    }, 0);
    return () => clearTimeout(timer);
  }, [isAccessGranted]);

  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        window.clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current && wsRef.current.readyState <= WebSocket.OPEN) {
        wsRef.current.close();
      }
    };
  }, []);



  const deleteSession = async (sessionId: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, { method: 'DELETE' });
      if (res.ok) {
        fetchSessions();
      }
    } catch (err) {
      console.error('Failed to delete session:', err);
    }
  };

  const startWorkflow = (userPrompt: string, sessionId: string | null = null, isReconnect = false) => {
    if (!isAccessGranted && !sessionId) {
      setAccessError('Enter a fresh access code before running a prompt.');
      return;
    }
    if (isSimulating && !isReconnect) return;

    currentPromptRef.current = userPrompt;

    if (!isReconnect) {
      currentSessionIdRef.current = sessionId;
      if (reconnectTimeoutRef.current) {
        window.clearTimeout(reconnectTimeoutRef.current);
      }
      reconnectAttemptsRef.current = 0;
      workflowFinishedRef.current = false;
      setIsSimulating(true);
      setEvents([]);
      setFinalResult(null);
      setShowSessionPanel(false);
    } else {
      if (sessionId) {
        currentSessionIdRef.current = sessionId;
      }
      setIsSimulating(true);
    }

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      const connectedAttempt = reconnectAttemptsRef.current;
      reconnectAttemptsRef.current = 0;
      const tokenForRequest = currentAccessTokenRef.current || accessToken;
      const payload = {
        prompt: currentPromptRef.current,
        session_id: currentSessionIdRef.current ?? sessionId,
        access_token: sessionId ? undefined : tokenForRequest,
      };
      ws.send(JSON.stringify(payload));
      if (isReconnect) {
        setEvents((prev) => [
          ...prev,
          {
            type: 'progress',
            agent: 'Network',
            status: `Reconnected (attempt ${connectedAttempt})`,
          },
        ]);
      }
    };

    ws.onmessage = (event) => {
      try {
        const data: QuantumEvent = JSON.parse(event.data);
        if (data.session_id) {
          currentSessionIdRef.current = data.session_id;
        }

        if (data.type === 'progress' && data.status.startsWith('T')) return;

        if (data.type === 'content_chunk') {
          return;
        }

        if (data.type === 'complete' && data.data) {
          workflowFinishedRef.current = true;
          setFinalResult(data.data as FinalResultData);
          setIsSimulating(false);
          setIsAccessGranted(false);
          setAccessToken('');
          currentAccessTokenRef.current = '';
          void fetchAccessStatus();
          ws.close();
          fetchSessions();
          void fetchPreviousRuns();
        } else if (data.type === 'fatal') {
          if (data.agent === 'AccessControl' && currentSessionIdRef.current) {
            void recoverCompletedRunFromHistory(currentSessionIdRef.current).then((recovered) => {
              if (!recovered) {
                workflowFinishedRef.current = true;
                setEvents((prev) => [...prev, data]);
                setIsSimulating(false);
                setIsAccessGranted(false);
                setAccessToken('');
                currentAccessTokenRef.current = '';
                void fetchAccessStatus();
                fetchSessions();
                void fetchPreviousRuns();
              }
            });
            ws.close();
            return;
          }

          workflowFinishedRef.current = true;
          setEvents((prev) => [...prev, data]);
          setIsSimulating(false);
          setIsAccessGranted(false);
          setAccessToken('');
          currentAccessTokenRef.current = '';
          void fetchAccessStatus();
          ws.close();
          fetchSessions();
          void fetchPreviousRuns();
        } else {
          setEvents((prev) => [...prev, data]);
        }
      } catch (err) {
        console.error("Failed to parse WS message", err);
      }
    };

    ws.onerror = () => {
      console.error('WebSocket error');
    };

    ws.onclose = () => {
      fetchSessions();
      void fetchPreviousRuns();
      if (workflowFinishedRef.current) {
        setIsSimulating(false);
        return;
      }

      if (reconnectAttemptsRef.current >= MAX_WS_RECONNECT_ATTEMPTS) {
        setEvents((prev) => [
          ...prev,
          {
            type: 'fatal',
            agent: 'Network',
            status: `WebSocket disconnected. Retry limit (${MAX_WS_RECONNECT_ATTEMPTS}) reached.`,
          },
        ]);
        setIsSimulating(false);
        return;
      }

      reconnectAttemptsRef.current += 1;
      const delayMs = 2 ** (reconnectAttemptsRef.current - 1) * 1000;
      setEvents((prev) => [
        ...prev,
        {
          type: 'warning',
          agent: 'Network',
          status: `Connection lost. Reconnecting in ${delayMs / 1000}s (attempt ${reconnectAttemptsRef.current}/${MAX_WS_RECONNECT_ATTEMPTS})...`,
        },
      ]);
      reconnectTimeoutRef.current = window.setTimeout(() => {
        startWorkflow(currentPromptRef.current, currentSessionIdRef.current, true);
      }, delayMs);
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

  const openAccessGateForNextPrompt = () => {
    setEvents([]);
    setFinalResult(null);
    setPrompt('');
    setAccessError('');
    setShowSessionPanel(false);
    void fetchPreviousRuns();
  };

  if (isCheckingAccess) {
    return (
      <div style={{ minHeight: '100vh', width: '100vw', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#060914', color: '#fff' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontFamily: 'monospace' }}>
          <Loader2 size={20} className="animate-spin" color="#00E5FF" />
          <span>Checking access status...</span>
        </div>
      </div>
    );
  }

  if (!isAccessGranted && !isSimulating && !finalResult && events.length === 0) {
    const exhausted = !!accessInfo?.exhausted;
    return (
      <div style={{ minHeight: '100vh', width: '100vw', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#060914', padding: '24px' }}>
        <div style={{ width: '100%', maxWidth: '1080px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px', alignItems: 'start' }}>
          <div style={{ background: 'rgba(20,24,34,0.95)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: '16px', padding: '28px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
              <BrainCircuit size={20} color="#00E5FF" />
              <h1 style={{ margin: 0, color: '#fff', fontFamily: 'monospace', fontSize: '20px' }}>Access Code Required</h1>
            </div>

            <p style={{ marginTop: 0, color: 'rgba(255,255,255,0.75)', fontSize: '14px', lineHeight: '1.6' }}>
              Enter one-time access code to run a new prompt.
            </p>

            {typeof accessInfo?.remaining === 'number' && (
              <p style={{ color: exhausted ? '#FF1744' : '#00E5FF', fontSize: '13px', marginBottom: '14px' }}>
                Remaining codes: {accessInfo.remaining}
              </p>
            )}

            {exhausted ? (
              <div style={{ padding: '14px', borderRadius: '10px', border: '1px solid rgba(255,23,68,0.4)', background: 'rgba(255,23,68,0.1)', color: '#FF8A80', fontSize: '14px' }}>
                All access codes are exhausted. Ask admin to reset codes.
              </div>
            ) : (
              <form onSubmit={submitAccessCode} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <input
                  type="text"
                  value={accessCode}
                  onChange={(e) => setAccessCode(e.target.value.toUpperCase())}
                  placeholder="QCS-XXXX-XXXX"
                  style={{
                    width: '100%',
                    padding: '12px 14px',
                    borderRadius: '10px',
                    border: '1px solid rgba(255,255,255,0.2)',
                    background: 'rgba(0,0,0,0.35)',
                    color: '#fff',
                    fontFamily: 'monospace',
                    fontSize: '14px',
                  }}
                />
                <button
                  type="submit"
                  disabled={isSubmittingAccessCode || !accessCode.trim()}
                  style={{
                    padding: '12px 14px',
                    borderRadius: '10px',
                    border: 'none',
                    background: isSubmittingAccessCode ? 'rgba(0,229,255,0.35)' : 'linear-gradient(135deg, #00E5FF, #00B8D4)',
                    color: '#041018',
                    fontWeight: 700,
                    cursor: isSubmittingAccessCode ? 'not-allowed' : 'pointer',
                    fontFamily: 'monospace',
                  }}
                >
                  {isSubmittingAccessCode ? 'Validating...' : 'Unlock Platform'}
                </button>
              </form>
            )}

            {accessError && (
              <p style={{ marginTop: '12px', marginBottom: 0, color: '#FF8A80', fontSize: '13px' }}>{accessError}</p>
            )}
          </div>

          <div style={{ background: 'rgba(20,24,34,0.95)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: '16px', padding: '22px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px', marginBottom: '12px' }}>
              <h2 style={{ margin: 0, color: '#fff', fontFamily: 'monospace', fontSize: '17px' }}>Previous Runs</h2>
              <button
                type="button"
                onClick={() => void fetchPreviousRuns()}
                style={{
                  border: '1px solid rgba(255,255,255,0.2)',
                  background: 'rgba(0,0,0,0.35)',
                  color: '#9CEFFF',
                  borderRadius: '8px',
                  padding: '6px 10px',
                  fontSize: '12px',
                  cursor: 'pointer',
                }}
              >
                Refresh
              </button>
            </div>

            <p style={{ marginTop: 0, color: 'rgba(255,255,255,0.65)', fontSize: '13px', lineHeight: '1.5' }}>
              Browse final results from earlier runs without a passcode.
            </p>

            {isLoadingPreviousRuns ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#9CEFFF', fontSize: '13px' }}>
                <Loader2 size={14} className="animate-spin" />
                Loading previous runs...
              </div>
            ) : previousRunsError ? (
              <div style={{ color: '#FF8A80', fontSize: '13px' }}>{previousRunsError}</div>
            ) : previousRuns.length === 0 ? (
              <div style={{ color: 'rgba(255,255,255,0.55)', fontSize: '13px' }}>No previous runs found.</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '420px', overflowY: 'auto', paddingRight: '4px' }} className="custom-scrollbar">
                {previousRuns.map((run) => {
                  const disabled = !run.has_final_package || loadingRunId !== null;
                  const isLoadingThisRun = loadingRunId === run.run_id;
                  return (
                    <div key={run.run_id} style={{ border: '1px solid rgba(255,255,255,0.1)', borderRadius: '10px', padding: '12px', background: 'rgba(0,0,0,0.28)' }}>
                      <div style={{ color: '#fff', fontSize: '13px', marginBottom: '6px', lineHeight: '1.4' }}>
                        {run.prompt || '(Prompt unavailable)'}
                      </div>
                      <div style={{ color: 'rgba(255,255,255,0.55)', fontSize: '11px', marginBottom: '8px' }}>
                        {new Date(run.updated_at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                        {' • '}
                        {run.status}
                        {run.identified_algorithm ? ` • ${run.identified_algorithm}` : ''}
                      </div>
                      <button
                        type="button"
                        onClick={() => void loadPreviousRun(run.run_id)}
                        disabled={disabled}
                        style={{
                          border: '1px solid rgba(0,229,255,0.35)',
                          background: disabled ? 'rgba(0,229,255,0.1)' : 'rgba(0,229,255,0.2)',
                          color: '#9CEFFF',
                          borderRadius: '8px',
                          padding: '7px 10px',
                          fontSize: '12px',
                          cursor: disabled ? 'not-allowed' : 'pointer',
                        }}
                      >
                        {isLoadingThisRun ? 'Loading...' : run.has_final_package ? 'View Final Result' : 'No Final Result Yet'}
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

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

        {!isAccessGranted && !isSimulating && (
          <div style={{ marginBottom: '20px', padding: '14px 16px', borderRadius: '12px', border: '1px solid rgba(255,193,7,0.35)', background: 'rgba(255,193,7,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
            <div style={{ color: '#FFE082', fontSize: '13px' }}>
              Enter a one-time access code to run a new prompt. Previous runs can be viewed without a code.
            </div>
            <button
              onClick={openAccessGateForNextPrompt}
              style={{
                border: '1px solid rgba(255,255,255,0.2)',
                background: 'rgba(0,0,0,0.35)',
                color: '#fff',
                borderRadius: '8px',
                padding: '8px 12px',
                fontSize: '12px',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              Enter New Code
            </button>
          </div>
        )}

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
                style={{ overflow: 'hidden' }}
              >
                <EventTimeline events={events} />
              </motion.div>
            )}

            {finalResult && (
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
                {finalResult.quantum_story_context && (
                  <div style={{ background: 'rgba(20, 24, 34, 0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '16px', padding: '24px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                      <Lightbulb size={20} color="#FFD600" />
                      <h2 style={{ margin: 0, color: '#fff', fontSize: '18px', fontWeight: 600, fontFamily: 'monospace' }}>Quantum Story Context</h2>
                    </div>
                    <div style={{ color: 'rgba(255,255,255,0.8)', fontSize: '14px', lineHeight: '1.6', maxHeight: '300px', overflowY: 'auto' }} className="custom-scrollbar">
                      <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
                        {finalResult.quantum_story_context}
                      </ReactMarkdown>
                    </div>
                  </div>
                )}

                {finalResult.problem_algorithm_mapping && (
                  <div style={{ background: 'rgba(20, 24, 34, 0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '16px', padding: '24px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                      <Lightbulb size={20} color="#00E5FF" />
                      <h2 style={{ margin: 0, color: '#fff', fontSize: '18px', fontWeight: 600, fontFamily: 'monospace' }}>
                        Why This Quantum Algorithm Fits
                      </h2>
                    </div>
                    <div style={{ color: 'rgba(255,255,255,0.85)', fontSize: '14px', lineHeight: '1.65', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      <div>
                        <strong>Problem class:</strong> {finalResult.problem_algorithm_mapping.problem_class || 'Unknown'}
                      </div>
                      <div>
                        <strong>Chosen algorithm:</strong> {finalResult.problem_algorithm_mapping.identified_algorithm || 'Unknown'}
                      </div>
                      <div>
                        <strong>Why:</strong> {finalResult.problem_algorithm_mapping.why_this_algorithm || 'No justification provided.'}
                      </div>
                      <div>
                        <strong>How user problem maps:</strong> {finalResult.problem_algorithm_mapping.how_user_problem_maps || 'No mapping narrative provided.'}
                      </div>
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
                    <div style={{ background: 'rgba(0,0,0,0.5)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '12px', padding: '16px' }}>
                      <div style={{ fontSize: '12px', color: '#FFD600', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '12px', fontFamily: 'monospace' }}>Narrative Audio</div>
                      {finalResult.narrative_audio ? (
                        <audio controls style={{ width: '100%' }} src={`data:${finalResult.narrative_audio_mime || 'audio/wav'};base64,${finalResult.narrative_audio}`} />
                      ) : (
                        <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.4)', fontStyle: 'italic' }}>No audio generated</div>
                      )}
                    </div>

                    <div style={{ background: 'rgba(0,0,0,0.5)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '12px', padding: '16px' }}>
                      <div style={{ fontSize: '12px', color: '#00E5FF', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '12px', fontFamily: 'monospace' }}>Imagen Illustration</div>
                      {finalResult.generated_illustration ? (
                        <img
                          src={`data:${finalResult.generated_illustration_mime || 'image/png'};base64,${finalResult.generated_illustration}`}
                          alt="Imagen-generated conceptual illustration"
                          style={{ width: '100%', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }}
                        />
                      ) : (
                        <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.4)', fontStyle: 'italic' }}>No Imagen illustration generated</div>
                      )}
                    </div>

                    <div style={{ background: 'rgba(0,0,0,0.5)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '12px', padding: '16px' }}>
                      <div style={{ fontSize: '12px', color: '#D500F9', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '12px', fontFamily: 'monospace' }}>Veo Output</div>
                      {finalResult.generated_video ? (
                        <video controls style={{ width: '100%', borderRadius: '8px' }} src={`data:${finalResult.generated_video_mime || 'video/mp4'};base64,${finalResult.generated_video}`} />
                      ) : finalResult.generated_video_uri ? (
                        <a href={finalResult.generated_video_uri} target="_blank" rel="noreferrer" style={{ color: '#00E5FF', fontSize: '13px' }}>
                          Open generated video URL
                        </a>
                      ) : (
                        <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.4)', fontStyle: 'italic' }}>No video generated</div>
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
                      <h2 style={{ margin: 0, color: '#fff', fontSize: '18px', fontWeight: 600, fontFamily: 'monospace' }}>Architectural Circuit & Code</h2>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                      {/* Code Block */}
                      {finalResult.complete_code && (
                        <div style={{ flex: 1, minHeight: '200px', background: '#0d1117', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)', overflow: 'hidden', position: 'relative', display: 'flex' }}>
                          <SyntaxHighlighter
                            language="python"
                            style={oneDark}
                            customStyle={{ margin: 0, width: '100%', fontSize: '13px', padding: '16px', background: 'transparent' }}
                            wrapLongLines={true}
                          >
                            {finalResult.complete_code}
                          </SyntaxHighlighter>
                        </div>
                      )}

                      {/* Circuit Diagram */}
                      <div style={{ flex: 1, minHeight: '400px', background: '#0d1117', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)', overflow: 'hidden', position: 'relative', display: 'flex' }}>
                         {finalResult.qiskit_circuit_diagram ? (
                            <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px', overflow: 'auto' }}>
                              <img 
                                src={`data:image/png;base64,${finalResult.qiskit_circuit_diagram}`} 
                                alt="Generated Quantum Circuit Diagram" 
                                style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', background: 'white', borderRadius: '4px' }}
                              />
                            </div>
                          ) : (
                            <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '13px', fontFamily: 'monospace' }}>
                              No circuit diagram generated.
                            </div>
                          )}
                      </div>
                    </div>

                    {/* Result Diagram */}
                    {finalResult.result_diagram && (
                      <div style={{ flex: 1, marginTop: '24px', minHeight: '400px', background: '#0d1117', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)', overflow: 'hidden', position: 'relative', display: 'flex' }}>
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', position: 'absolute', top: '16px', left: '16px' }}>
                          <h3 style={{ margin: 0, color: '#fff', fontSize: '16px', fontWeight: 600, fontFamily: 'monospace' }}>Result Diagram (Simulation Histogram)</h3>
                        </div>
                        <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px', overflow: 'auto', marginTop: '40px' }}>
                          <img 
                            src={`data:image/png;base64,${finalResult.result_diagram}`} 
                            alt="Result Histogram Diagram" 
                            style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', background: 'white', borderRadius: '4px' }}
                          />
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Math/Logic Explanation */}
                  <div style={{ background: 'rgba(20, 24, 34, 0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '16px', padding: '24px' }}>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '16px' }}>
                      <BrainCircuit size={20} color="#D500F9" />
                      <h2 style={{ margin: 0, color: '#fff', fontSize: '18px', fontWeight: 600, fontFamily: 'monospace' }}>Algorithm Explanation</h2>
                    </div>
                    <div style={{ color: 'rgba(255,255,255,0.8)', fontSize: '14px', lineHeight: '1.6' }} className="markdown-body">
                      {finalResult.algorithm_explanation ? (
                        <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
                          {finalResult.algorithm_explanation}
                        </ReactMarkdown>
                      ) : (
                        <span style={{ fontStyle: 'italic', color: 'rgba(255,255,255,0.4)' }}>No explanation available.</span>
                      )}
                    </div>
                  </div>

                </div>

                <div style={{ background: 'rgba(20, 24, 34, 0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '16px', padding: '24px' }}>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '16px' }}>
                    <Activity size={20} color="#FFD600" />
                    <h2 style={{ margin: 0, color: '#fff', fontSize: '18px', fontWeight: 600, fontFamily: 'monospace' }}>Simulation Results</h2>
                  </div>
                  <div style={{ color: 'rgba(255,255,255,0.85)', fontSize: '14px', lineHeight: '1.6', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div>
                      <strong>Status:</strong> {finalResult.simulation_results?.status || 'Unknown'}
                    </div>
                    {finalResult.simulation_results?.histogram && Object.keys(finalResult.simulation_results.histogram).length > 0 && (
                      <div>
                        <strong>Histogram counts:</strong> {Object.entries(finalResult.simulation_results.histogram).map(([state, count]) => `${state}: ${count}`).join(' | ')}
                      </div>
                    )}
                    {Boolean(finalResult.simulation_results?.error) && (
                      <div>
                        <strong>Execution warning:</strong> {String(finalResult.simulation_results?.error)}
                      </div>
                    )}
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
          {!isSimulating && (
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', padding: '8px 8px 12px 8px' }}>
              {PRESET_PROMPTS.map((preset, idx) => (
                <button
                  key={`preset-${idx}`}
                  type="button"
                  onClick={() => {
                    setPrompt(preset);
                    startWorkflow(preset);
                  }}
                  style={{
                    border: '1px solid rgba(0, 229, 255, 0.35)',
                    background: 'rgba(0, 229, 255, 0.08)',
                    color: '#9CEFFF',
                    padding: '8px 10px',
                    borderRadius: '999px',
                    fontSize: '12px',
                    cursor: 'pointer',
                    textAlign: 'left',
                  }}
                  title={preset}
                >
                  Preset {idx + 1}
                </button>
              ))}
            </div>
          )}
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
