import { useState, useRef, useEffect } from 'react';
import { askAgent7 } from '../services/api';

function ThinkingDots() {
  return (
    <div style={{ display: 'flex', gap: 4, alignItems: 'center', padding: '0.5rem 0' }}>
      {[0, 1, 2].map(i => (
        <div key={i} style={{
          width: 7, height: 7, borderRadius: '50%',
          background: 'var(--accent)',
          animation: `thinkingDot 1.2s ${i * 0.2}s infinite ease-in-out`,
        }} />
      ))}
      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginLeft: 6 }}>Analysing live data…</span>
    </div>
  );
}

export default function AiChatPanel({ cityName }) {
  const SUGGESTIONS = [
    `What is the main cause of pollution in ${cityName} today?`,
    'Where should inspectors go first?',
    'Give me a full summary of today\'s air quality situation.',
    'Are there any active anomalies?',
  ];
  
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: `Hello! I'm your VayuDrishti AI Assistant. I can answer questions about ${cityName}'s current air quality, which areas need attention, where inspectors should be deployed, and what citizens should be advised. All my answers are based on live monitoring data. How can I help you today?`
    }
  ]);
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSend = async (q) => {
    const text = (q || question).trim();
    if (!text || loading) return;
    setQuestion('');
    setMessages(prev => [...prev, { role: 'user', text }]);
    setLoading(true);
    try {
      const res = await askAgent7(text, cityName);
      setMessages(prev => [...prev, { role: 'assistant', text: res.answer }]);
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', text: '⚠ Could not connect to the platform. Please ensure the service is running and try again.' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>

      {/* Chat header */}
      <div style={{
        padding: '0.75rem 1rem',
        borderBottom: '1px solid var(--border)',
        background: 'var(--accent-light)',
        borderRadius: 'var(--radius-md) var(--radius-md) 0 0',
        display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0
      }}>
        <div style={{
          width: 32, height: 32, borderRadius: '50%',
          background: 'var(--accent)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '1rem', flexShrink: 0
        }}>🤖</div>
        <div>
          <div style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--accent)' }}>VayuDrishti AI Assistant</div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Answers based on live monitoring data</div>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 5 }}>
          <div style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--aqi-good)', animation: 'pulse 2s infinite' }} />
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Live</span>
        </div>
      </div>

      {/* Message list */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {messages.map((msg, i) => (
          <div key={i} style={{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
            <div style={{
              maxWidth: '88%',
              padding: '0.65rem 0.9rem',
              borderRadius: msg.role === 'user' ? '14px 14px 4px 14px' : '14px 14px 14px 4px',
              background: msg.role === 'user' ? 'var(--accent)' : 'var(--surface)',
              color: msg.role === 'user' ? 'white' : 'var(--text-primary)',
              fontSize: '0.85rem',
              lineHeight: 1.6,
              boxShadow: 'var(--shadow-sm)',
              border: msg.role === 'assistant' ? '1px solid var(--border)' : 'none',
              whiteSpace: 'pre-wrap',
              animation: 'countUp 0.2s ease-out',
            }}>
              {msg.text}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ display: 'flex' }}>
            <div style={{
              padding: '0.65rem 0.9rem',
              borderRadius: '14px 14px 14px 4px',
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              boxShadow: 'var(--shadow-sm)',
            }}>
              <ThinkingDots />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Quick suggestions (only if just the greeting is shown) */}
      {messages.length === 1 && !loading && (
        <div style={{ padding: '0 1rem 0.5rem', display: 'flex', flexDirection: 'column', gap: 5, flexShrink: 0 }}>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: 2 }}>Quick questions:</div>
          {SUGGESTIONS.map(s => (
            <button key={s} className="btn btn-ghost" style={{ fontSize: '0.78rem', padding: '5px 10px', textAlign: 'left', justifyContent: 'flex-start' }}
              onClick={() => handleSend(s)}>
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input box */}
      <div style={{ padding: '0.75rem 1rem', borderTop: '1px solid var(--border)', flexShrink: 0, background: 'var(--bg)' }}>
        <form onSubmit={e => { e.preventDefault(); handleSend(); }} style={{ display: 'flex', gap: 8 }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <input
              ref={inputRef}
              className="input"
              placeholder={`Ask anything about air quality in ${cityName}…`}
              value={question}
              onChange={e => setQuestion(e.target.value)}
              disabled={loading}
              autoFocus
            />
          </div>
          <button className="btn btn-primary" type="submit" disabled={loading || !question.trim()}>
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
