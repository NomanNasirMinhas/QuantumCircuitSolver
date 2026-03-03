'use client';

import { motion } from 'framer-motion';
import { Bot, CheckCircle, AlertTriangle, Loader2 } from 'lucide-react';

export type QuantumEvent = {
  type: 'progress' | 'success' | 'error' | 'warning' | 'complete' | 'fatal';
  agent: string;
  status: string;
  details?: any;
  data?: any;
};

export default function EventTimeline({ events }: { events: QuantumEvent[] }) {
  if (events.length === 0) return null;

  return (
    <div className="glass-panel" style={{ padding: '24px', marginTop: '24px', maxHeight: '400px', overflowY: 'auto' }}>
      <h3 style={{ marginBottom: '16px', color: '#8A8DAA', textTransform: 'uppercase', fontSize: '14px', letterSpacing: '1px' }}>
        Live Agent Telemetry
      </h3>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {events.map((ev, idx) => (
          <motion.div 
            key={idx}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4 }}
            style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}
          >
            <div style={{ marginTop: '2px' }}>
              {ev.type === 'progress' && <Loader2 className="animate-spin" size={18} color="#00E5FF" />}
              {ev.type === 'success' && <CheckCircle size={18} color="#00E676" />}
              {(ev.type === 'error' || ev.type === 'fatal') && <AlertTriangle size={18} color="#FF1744" />}
              {ev.type === 'warning' && <AlertTriangle size={18} color="#FFD600" />}
              {ev.type === 'complete' && <Bot size={18} color="#D500F9" />}
            </div>
            
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <strong style={{ fontSize: '14px', color: ev.type === 'error' ? '#FF1744' : '#fff' }}>
                  [{ev.agent}]
                </strong>
                <span style={{ fontSize: '12px', color: '#8A8DAA' }}>
                   {new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'})}
                </span>
              </div>
              <p style={{ fontSize: '14px', color: '#c0c3db', marginTop: '4px', lineHeight: '1.5' }}>
                {ev.status}
              </p>
              
              {ev.details && (
                <div style={{ marginTop: '8px', padding: '8px', background: 'rgba(0,0,0,0.3)', borderRadius: '4px', fontSize: '12px', fontFamily: 'monospace', color: '#FF1744' }}>
                  {JSON.stringify(ev.details, null, 2)}
                </div>
              )}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
