// Shared primitives + helpers — ported from the design (postcard-ui.jsx), adapted to
// the backend's snake_case documents.
import React, { useState } from 'react';

export const money = (cents) =>
  cents == null ? '—' : '$' + (cents / 100).toLocaleString('en-US', { maximumFractionDigits: cents % 100 ? 2 : 0 });

export function timeAgo(ts) {
  if (!ts) return '—';
  const d = (Date.now() - new Date(ts).getTime()) / 1000;
  if (d < 90) return 'just now';
  if (d < 3600) return Math.round(d / 60) + 'm ago';
  if (d < 86400 * 1.5) return Math.round(d / 3600) + 'h ago';
  return Math.round(d / 86400) + 'd ago';
}

export function shortDate(ts) {
  const d = /^\d{4}-\d{2}-\d{2}$/.test(ts) ? new Date(ts + 'T00:00:00') : new Date(ts);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function daysUntil(dateStr) {
  const end = new Date(dateStr + 'T00:00:00');
  const today = new Date(); today.setHours(0, 0, 0, 0);
  return Math.max(0, Math.round((end - today) / 86400e3));
}

export const ACTIVE_CAMPAIGN_STATUSES = ['draft', 'filling', 'full', 'fulfillment'];

// Pipeline column for a business document (enrichment status × participation status)
export function columnOf(b) {
  if (b.status === 'disqualified') return 'disqualified';
  if (b.status === 'staged') return 'staged';
  if (b.status === 'researching') return 'researching';
  const p = b.participation;
  if (!p || p.status === 'prospecting') return 'researched';
  if (p.status === 'paid') return 'committed';
  return p.status;
}

export const STATUS_META = {
  staged:       { label: 'Staged',       color: 'var(--c-gray)' },
  researching:  { label: 'Researching',  color: 'var(--c-blue)' },
  researched:   { label: 'Researched',   color: 'var(--c-cyan)' },
  prospecting:  { label: 'Prospecting',  color: 'var(--c-cyan)' },
  contacted:    { label: 'Contacted',    color: 'var(--c-violet)' },
  interested:   { label: 'Interested',   color: 'var(--c-amber)' },
  waitlisted:   { label: 'Waitlisted',   color: 'var(--c-orange)' },
  committed:    { label: 'Committed',    color: 'var(--c-green)' },
  paid:         { label: 'Committed',    color: 'var(--c-green)' },
  declined:     { label: 'Declined',     color: 'var(--c-red)' },
  disqualified: { label: 'Disqualified', color: 'var(--c-red)' },
};

export const EMAIL_STATUS_META = {
  in_review:  { label: 'In review',  cls: 'es-review' },
  approved:   { label: 'Approved',   cls: 'es-approved' },
  sent:       { label: 'Sent',       cls: 'es-sent' },
  superseded: { label: 'Superseded', cls: 'es-superseded' },
};

export const FULFILLMENT_KEYS = ['logo_received', 'offer_confirmed', 'artwork_approved'];
export const fulfillDone = (f) => FULFILLMENT_KEYS.filter((k) => f && f[k]).length;

// ---------- atoms ----------
export const StatusDot = ({ status }) => (
  <span className="status-dot" style={{ background: STATUS_META[status]?.color }}></span>
);

export const CategoryTag = ({ category }) => <span className="cat-tag">{category}</span>;

export const Pill = ({ children, tone, title }) => (
  <span className={'pill ' + (tone || '')} title={title}>{children}</span>
);

export const Btn = ({ children, onClick, kind, disabled, title, small }) => (
  <button className={'btn ' + (kind || 'btn-ghost') + (small ? ' btn-sm' : '')} onClick={onClick} disabled={disabled} title={title}>
    {children}
  </button>
);

export const IconChevron = ({ open }) => (
  <svg width="12" height="12" viewBox="0 0 12 12" style={{ transform: open ? 'rotate(90deg)' : 'none', transition: 'transform .15s' }}>
    <path d="M4 2l4 4-4 4" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"></path>
  </svg>
);

export const Toast = ({ toasts }) => (
  <div className="toast-stack">
    {toasts.map((t) => <div key={t.id} className="toast">{t.text}</div>)}
  </div>
);

export function useToasts() {
  const [toasts, setToasts] = useState([]);
  const push = (text) => {
    const id = Math.random().toString(36).slice(2);
    setToasts((ts) => [...ts, { id, text }]);
    setTimeout(() => setToasts((ts) => ts.filter((x) => x.id !== id)), 3200);
  };
  return [toasts, push];
}

// Wrap a mutation: run it, toast the server's actionable error message on failure.
export const attempt = (toast, after) => async (fn) => {
  try {
    await fn();
    if (after) after();
  } catch (e) {
    toast(e.message);
  }
};
