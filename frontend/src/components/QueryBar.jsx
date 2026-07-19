import { useState, useRef } from 'react';
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
      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginLeft: 6 }}>Agent 7 is thinking…</span>
    </div>
  );
}

export default function QueryBar() {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState(null);
  const inputRef = useRef(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;
    setLoading(true);
    setAnswer(null);
    try {
      const res = await askAgent7(question);
      setAnswer(res.answer);
    } catch {
      setAnswer('Error connecting to Agent 7. Make sure the backend server is running.');
    } finally {
      setLoading(false);
    }
  };

  const suggestions = [
    'What is the main cause of pollution in Delhi today?',
    'Where should inspectors go first?',
    'Give me a summary of today\'s air quality situation.',
  ];

  return (
    <div style={{ position: 'relative' }}>
      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: 8 }}>
        <div style={{ position: 'relative', flex: 1 }}>
          <span style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', fontSize: '1rem' }}>🔍</span>
          <input
            ref={inputRef}
            className="input"
            style={{ paddingLeft: 36 }}
            placeholder="Ask anything about Delhi's air quality…"
            value={question}
            onChange={e => setQuestion(e.target.value)}
            disabled={loading}
          />
        </div>
        <button className="btn btn-primary" type="submit" disabled={loading || !question.trim()} style={{ whiteSpace: 'nowrap' }}>
          {loading ? '…' : 'Ask AI'}
        </button>
      </form>

      {/* Dropdown answer panel — anchored right so it never overlaps the map */}
      {(loading || answer) && (
        <div style={{
          position: 'absolute', top: 'calc(100% + 8px)', right: 0, left: 'auto',
          width: 'min(640px, 100%)', zIndex: 9999,
          background: 'var(--surface)', borderRadius: 'var(--radius-md)',
          boxShadow: 'var(--shadow-lg)', border: '1px solid var(--border)',
          padding: '1rem', animation: 'countUp 0.2s ease-out',
          maxHeight: 260, overflowY: 'auto',
        }}>
          <div style={{ display: 'flex', align: 'center', gap: 6, marginBottom: 8 }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--accent)', background: 'var(--accent-light)', padding: '2px 8px', borderRadius: 99 }}>
              🤖 Agent 7 · Natural Language Response
            </span>
          </div>
          {loading ? <ThinkingDots /> : (
            <div style={{ fontSize: '0.88rem', lineHeight: 1.7, color: 'var(--text-primary)', whiteSpace: 'pre-wrap' }}>
              {answer}
            </div>
          )}
        </div>
      )}

      {/* Quick suggestions */}
      {!answer && !loading && (
        <div style={{ display: 'flex', gap: 6, marginTop: 6, flexWrap: 'wrap' }}>
          {suggestions.map(s => (
            <button key={s} className="btn btn-ghost" style={{ fontSize: '0.75rem', padding: '3px 10px' }} onClick={() => { setQuestion(s); inputRef.current?.focus(); }}>
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
