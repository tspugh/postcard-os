// Shared primitives + helpers for the Postcard dashboard
const { useState, useEffect, useRef, useMemo } = React;

// ---------- helpers ----------
const money = (cents) => cents == null ? '—' : '$' + (cents / 100).toLocaleString('en-US', { maximumFractionDigits: cents % 100 ? 2 : 0 });

function timeAgo(ts) {
  const d = (Date.now() - new Date(ts).getTime()) / 1000;
  if (d < 90) return 'just now';
  if (d < 3600) return Math.round(d / 60) + 'm ago';
  if (d < 86400 * 1.5) return Math.round(d / 3600) + 'h ago';
  return Math.round(d / 86400) + 'd ago';
}
function shortDate(ts) {
  // date-only strings ('2026-06-19') parse as UTC midnight; pin them to local time
  const d = /^\d{4}-\d{2}-\d{2}$/.test(ts) ? new Date(ts + 'T00:00:00') : new Date(ts);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}
function daysUntil(dateStr) {
  const end = new Date(dateStr + 'T00:00:00'); // local midnight at start of deadline day
  const today = new Date(); today.setHours(0, 0, 0, 0);
  return Math.max(0, Math.round((end - today) / 86400e3));
}

// Pipeline column for a business
function columnOf(b) {
  if (b.status === 'disqualified') return 'disqualified';
  if (b.status === 'staged') return 'staged';
  if (b.status === 'researching') return 'researching';
  const p = b.participation;
  if (!p || p.status === 'prospecting') return 'researched';
  if (p.status === 'paid') return 'committed';
  return p.status; // contacted | interested | waitlisted | committed | declined
}

const STATUS_META = {
  staged:       { label: 'Staged',       color: 'var(--c-gray)' },
  researching:  { label: 'Researching',  color: 'var(--c-blue)' },
  researched:   { label: 'Researched',   color: 'var(--c-cyan)' },
  contacted:    { label: 'Contacted',    color: 'var(--c-violet)' },
  interested:   { label: 'Interested',   color: 'var(--c-amber)' },
  waitlisted:   { label: 'Waitlisted',   color: 'var(--c-orange)' },
  committed:    { label: 'Committed',    color: 'var(--c-green)' },
  declined:     { label: 'Declined',     color: 'var(--c-red)' },
  disqualified: { label: 'Disqualified', color: 'var(--c-red)' },
};
const BOARD_COLUMNS = ['staged', 'researching', 'researched', 'contacted', 'interested', 'waitlisted', 'committed'];

const EMAIL_STATUS_META = {
  in_review:  { label: 'In review',  cls: 'es-review' },
  approved:   { label: 'Approved',   cls: 'es-approved' },
  sent:       { label: 'Sent',       cls: 'es-sent' },
  superseded: { label: 'Superseded', cls: 'es-superseded' },
};

// ---------- atoms ----------
function StatusDot({ status }) {
  return <span className="status-dot" style={{ background: STATUS_META[status]?.color }}></span>;
}

function CategoryTag({ category }) {
  return <span className="cat-tag">{category}</span>;
}

function Pill({ children, tone, title }) {
  return <span className={'pill ' + (tone || '')} title={title}>{children}</span>;
}

function Btn({ children, onClick, kind, disabled, title, small }) {
  return (
    <button
      className={'btn ' + (kind || 'btn-ghost') + (small ? ' btn-sm' : '')}
      onClick={onClick} disabled={disabled} title={title}
    >{children}</button>
  );
}

function IconChevron({ open }) {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" style={{ transform: open ? 'rotate(90deg)' : 'none', transition: 'transform .15s' }}>
      <path d="M4 2l4 4-4 4" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"></path>
    </svg>
  );
}

function Toast({ toasts }) {
  return (
    <div className="toast-stack">
      {toasts.map((t) => <div key={t.id} className="toast">{t.text}</div>)}
    </div>
  );
}

function useToasts() {
  const [toasts, setToasts] = useState([]);
  const push = (text) => {
    const id = Math.random().toString(36).slice(2);
    setToasts((ts) => [...ts, { id, text }]);
    setTimeout(() => setToasts((ts) => ts.filter((x) => x.id !== id)), 2600);
  };
  return [toasts, push];
}

Object.assign(window, {
  money, timeAgo, shortDate, daysUntil, columnOf,
  STATUS_META, BOARD_COLUMNS, EMAIL_STATUS_META,
  StatusDot, CategoryTag, Pill, Btn, IconChevron, Toast, useToasts,
});
