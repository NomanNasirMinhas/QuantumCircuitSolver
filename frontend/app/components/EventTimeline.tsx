'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, CheckCircle, AlertTriangle, Loader2, Activity } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export type QuantumEvent = {
  type: 'progress' | 'success' | 'error' | 'warning' | 'complete' | 'fatal' | 'content_chunk';
  agent: string;
  status: string;
  details?: unknown;
  data?: unknown;
  restored?: boolean;
  session_id?: string;
  content_type?: 'text' | 'image' | 'audio' | 'video';
  content?: string;
  mime_type?: string;
  label?: string;
};

const typeConfig: Record<string, { color: string; glow: string; Icon: LucideIcon }> = {
  progress: { color: '#00E5FF', glow: 'rgba(0, 229, 255, 0.4)', Icon: Loader2 },
  success: { color: '#00E676', glow: 'rgba(0, 230, 118, 0.4)', Icon: CheckCircle },
  error: { color: '#FF1744', glow: 'rgba(255, 23, 68, 0.4)', Icon: AlertTriangle },
  fatal: { color: '#FF1744', glow: 'rgba(255, 23, 68, 0.4)', Icon: AlertTriangle },
  warning: { color: '#FFD600', glow: 'rgba(255, 214, 0, 0.4)', Icon: AlertTriangle },
  complete: { color: '#D500F9', glow: 'rgba(213, 0, 249, 0.4)', Icon: Bot },
  content_chunk: { color: '#64FFDA', glow: 'rgba(100, 255, 218, 0.4)', Icon: Activity },
};

function EventNode({ ev, index, isLast }: { ev: QuantumEvent; index: number; isLast: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const cfg = typeConfig[ev.type] || typeConfig.progress;
  const IconComp = cfg.Icon;
  const isActive = isLast && ev.type === 'progress';

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.6 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.35, delay: 0.05 }}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        position: 'relative',
        minWidth: '0',
        flex: '0 0 auto',
      }}
    >
      {/* Node circle */}
      <button
        onClick={() => setExpanded(!expanded)}
        style={{
          position: 'relative',
          width: '48px',
          height: '48px',
          borderRadius: '50%',
          background: `radial-gradient(circle, ${cfg.color}22 0%, ${cfg.color}08 100%)`,
          border: `2px solid ${cfg.color}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: 'pointer',
          transition: 'all 0.3s ease',
          boxShadow: isActive
            ? `0 0 16px ${cfg.glow}, 0 0 32px ${cfg.glow}`
            : `0 0 8px ${cfg.glow}`,
          animation: isActive ? 'pulse-ring 1.5s ease-in-out infinite' : 'none',
          zIndex: 2,
          padding: 0,
          color: cfg.color,
        }}
        title={`[${ev.agent}] ${ev.status}`}
      >
        <IconComp
          size={20}
          color={cfg.color}
          className={isActive ? 'animate-spin' : ''}
        />
        {ev.restored && (
          <span style={{
            position: 'absolute',
            top: '-4px',
            right: '-4px',
            width: '12px',
            height: '12px',
            borderRadius: '50%',
            background: '#00E5FF',
            border: '2px solid rgba(20, 15, 40, 0.9)',
          }} />
        )}
      </button>

      {/* Agent label */}
      <span style={{
        marginTop: '8px',
        fontSize: '10px',
        fontWeight: 700,
        color: cfg.color,
        letterSpacing: '0.5px',
        textTransform: 'uppercase',
        textAlign: 'center',
        maxWidth: '80px',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
      }}>
        {ev.agent}
      </span>

      {/* Expanded tooltip/popover */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.9 }}
            transition={{ duration: 0.2 }}
            style={{
              position: 'absolute',
              top: '80px',
              left: '50%',
              transform: 'translateX(-50%)',
              background: 'rgba(15, 10, 35, 0.95)',
              border: `1px solid ${cfg.color}44`,
              borderRadius: '12px',
              padding: '14px 18px',
              minWidth: '240px',
              maxWidth: '320px',
              zIndex: 100,
              boxShadow: `0 8px 32px rgba(0,0,0,0.5), 0 0 12px ${cfg.glow}`,
              backdropFilter: 'blur(12px)',
            }}
          >
            {/* Arrow */}
            <div style={{
              position: 'absolute',
              top: '-6px',
              left: '50%',
              transform: 'translateX(-50%) rotate(45deg)',
              width: '12px',
              height: '12px',
              background: 'rgba(15, 10, 35, 0.95)',
              border: `1px solid ${cfg.color}44`,
              borderRight: 'none',
              borderBottom: 'none',
            }} />
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <strong style={{ fontSize: '12px', color: cfg.color, letterSpacing: '0.5px' }}>
                [{ev.agent}]
              </strong>
              <span style={{ fontSize: '10px', color: '#8A8DAA' }}>
                #{index + 1}
              </span>
            </div>
            <p style={{ fontSize: '13px', color: '#c0c3db', lineHeight: '1.5', margin: 0, overflowWrap: 'anywhere' }}>
              {String(ev.status)}
            </p>
            {Boolean(ev.details) && (
              <div style={{
                marginTop: '10px',
                padding: '8px',
                background: 'rgba(0,0,0,0.4)',
                borderRadius: '6px',
                fontSize: '11px',
                fontFamily: 'monospace',
                color: '#FF1744',
                maxHeight: '120px',
                overflowY: 'auto',
              }}>
                {JSON.stringify(ev.details, null, 2)}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

function ConnectorLine({ color, isLast }: { color: string; isLast: boolean }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      height: '4px',
      minWidth: '32px',
      flex: '0 0 auto',
      position: 'relative',
    }}>
      {/* Line */}
      <div style={{
        width: '100%',
        height: '2px',
        background: isLast
          ? `linear-gradient(90deg, ${color}, transparent)`
          : `linear-gradient(90deg, ${color}88, ${color}44)`,
        borderRadius: '1px',
        boxShadow: `0 0 6px ${color}33`,
      }} />
      {/* Signal dot traveling animation */}
      {isLast && (
        <div style={{
          position: 'absolute',
          width: '6px',
          height: '6px',
          borderRadius: '50%',
          background: color,
          boxShadow: `0 0 8px ${color}`,
          animation: 'signal-travel 1.2s ease-in-out infinite',
          top: '-1px',
        }} />
      )}
    </div>
  );
}

export default function EventTimeline({ events }: { events: QuantumEvent[] }) {
  if (events.length === 0) return null;

  return (
    <div className="glass-panel" style={{ padding: '24px', marginTop: '24px', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        marginBottom: '20px',
      }}>
        <Activity size={16} color="#00E5FF" />
        <h3 style={{
          margin: 0,
          color: '#8A8DAA',
          textTransform: 'uppercase',
          fontSize: '14px',
          letterSpacing: '1px',
        }}>
          Live Agent Telemetry
        </h3>
        <span style={{
          marginLeft: 'auto',
          fontSize: '11px',
          color: '#8A8DAA',
          background: 'rgba(0, 229, 255, 0.1)',
          padding: '3px 10px',
          borderRadius: '12px',
          border: '1px solid rgba(0, 229, 255, 0.2)',
        }}>
          {events.length} event{events.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Network graph — wrapping centered layout */}
      <div style={{
        overflowY: 'visible',
        paddingBottom: '120px', // Space for expanded popovers
        marginBottom: '-100px',
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          flexWrap: 'wrap',
          justifyContent: 'center',
          gap: '4px 0',
          padding: '8px 4px',
        }}>
          {events.map((ev, idx) => {
            const isLast = idx === events.length - 1;
            const cfg = typeConfig[ev.type] || typeConfig.progress;
            const nextCfg = !isLast ? (typeConfig[events[idx + 1].type] || typeConfig.progress) : cfg;
            // Blend connector color between current and next
            const connColor = isLast ? cfg.color : nextCfg.color;

            return (
              <div key={idx} style={{ display: 'flex', alignItems: 'center' }}>
                <EventNode ev={ev} index={idx} isLast={isLast} />
                {!isLast && (
                  <ConnectorLine
                    color={connColor}
                    isLast={idx === events.length - 2}
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* CSS animations */}
      <style>{`
        @keyframes pulse-ring {
          0%, 100% { box-shadow: 0 0 8px rgba(0,229,255,0.3), 0 0 16px rgba(0,229,255,0.15); }
          50% { box-shadow: 0 0 20px rgba(0,229,255,0.5), 0 0 40px rgba(0,229,255,0.25); }
        }
        @keyframes signal-travel {
          0% { left: 0; opacity: 1; }
          100% { left: calc(100% - 6px); opacity: 0; }
        }
      `}</style>
    </div>
  );
}
