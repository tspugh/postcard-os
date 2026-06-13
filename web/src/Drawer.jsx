// Detail drawer — research, contacts, email thread, comments, payment & fulfillment.
// Hydrates from GET /api/businesses/{id} (one composite document; the fetch itself
// clears the "unviewed" badge). All guards live server-side; errors toast verbatim.
import React, { useEffect, useState } from 'react';
import { api } from './api.js';
import {
  ACTIVE_CAMPAIGN_STATUSES, Btn, CategoryTag, columnOf, EMAIL_STATUS_META,
  FULFILLMENT_KEYS, fulfillDone, money, Pill, shortDate, STATUS_META, StatusDot, timeAgo,
} from './ui.jsx';

export function DetailDrawer({ businessId, settings, onClose, toast }) {
  const [biz, setBiz] = useState(null);

  const refresh = () => api.get('/businesses/' + businessId).then(setBiz).catch((e) => toast(e.message));
  useEffect(() => { refresh(); }, [businessId]);

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  if (!biz) return null;

  // The participation on an active campaign, else the most recent one.
  const p = (biz.participations || []).find((x) => ACTIVE_CAMPAIGN_STATUSES.includes(x.campaign.status))
    || (biz.participations || [])[0] || null;
  const col = columnOf({ ...biz, participation: p });
  const isCommitted = p && (p.status === 'committed' || p.status === 'paid');

  const act = (fn) => fn().then(refresh).catch((e) => toast(e.message));

  return (
    <div className="drawer-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <aside className="drawer">
        <header className="drawer-head">
          <div className="drawer-head-top">
            <Pill tone="pill-status"><StatusDot status={col} />{STATUS_META[col].label}{p && p.status === 'paid' ? ' · Paid' : ''}</Pill>
            <button className="icon-btn" onClick={onClose} title="Close (Esc)">
              <svg width="14" height="14" viewBox="0 0 14 14"><path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"></path></svg>
            </button>
          </div>
          <h2 className="drawer-title">{biz.name}</h2>
          <div className="drawer-meta">
            <a className="link" href={biz.website} target="_blank" rel="noopener noreferrer">{biz.website.replace('https://', '')}</a>
            <span className="meta-dim">·</span>
            <label className="cat-edit">
              <select value={biz.category} onChange={(e) => act(() => api.patch('/businesses/' + biz.id, { category: e.target.value }).then(() => toast('Category updated')))}>
                {[...new Set([...settings.categories, biz.category])].map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </label>
            <span className="meta-dim">·</span>
            <span className="meta-dim">added {timeAgo(biz.created_at)} · {biz.source === 'operator' ? 'staged by you' : 'staged by agent'}</span>
          </div>
        </header>

        <div className="drawer-body">
          {biz.dq_code && (
            <div className="dq-banner">
              <strong>Disqualified — {biz.dq_code}</strong>
              {biz.dq_reason && <p>{biz.dq_reason}</p>}
            </div>
          )}
          {biz.status === 'researching' && (
            <div className="claim-banner">Claimed by agent {timeAgo(biz.claimed_at)} — research in progress.</div>
          )}

          {p && (
            <section className="dsec">
              <div className="dsec-label">Campaign</div>
              <div className="part-row">
                <span>{p.campaign.name}</span>
                <span className="meta-dim">asking {money(p.asking_price_cents)}</span>
                {p.committed_amount_cents != null && <Pill tone="pill-green">committed {money(p.committed_amount_cents)}{p.committed_amount_cents !== p.asking_price_cents ? ' (negotiated)' : ''}</Pill>}
                {p.slot_number != null && <Pill>slot {p.slot_number}</Pill>}
                {p.status === 'waitlisted' && <Pill tone="pill-orange">waitlist #{p.waitlist_order}</Pill>}
              </div>
            </section>
          )}

          {(biz.premise || biz.hooks.length > 0 || biz.evidence_urls.length > 0) && (
            <section className="dsec">
              <div className="dsec-label">Research</div>
              {biz.premise && <p className="premise">{biz.premise}</p>}
              {biz.hooks.length > 0 && (
                <div className="hooks">{biz.hooks.map((h, i) => <span key={i} className="hook-chip">{h}</span>)}</div>
              )}
              {biz.evidence_urls.length > 0 && (
                <div className="evidence">
                  {biz.evidence_urls.map((u, i) => (
                    <a key={i} className="link evidence-link" href={u} target="_blank" rel="noopener noreferrer">
                      <svg width="11" height="11" viewBox="0 0 12 12"><path d="M5 2H2v8h8V7M7 1h4v4M11 1L5.5 6.5" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"></path></svg>
                      {u.replace('https://', '')}
                    </a>
                  ))}
                </div>
              )}
            </section>
          )}

          <ContactsSection biz={biz} act={act} toast={toast} />

          {isCommitted && <MoneySection p={p} act={act} toast={toast} />}

          {p && p.emails.length > 0 && <EmailThread p={p} act={act} toast={toast} />}

          <CommentsSection biz={biz} act={act} />

          {p && p.events.length > 0 && (
            <section className="dsec">
              <div className="dsec-label">State changes</div>
              <ul className="events">
                {p.events.map((ev) => (
                  <li key={ev.id}><span className="event-dot"></span>{ev.label}<span className="meta-dim event-ts">{timeAgo(ev.occurred_at)}</span></li>
                ))}
              </ul>
            </section>
          )}
        </div>
      </aside>
    </div>
  );
}

// ---------- contacts ----------
function ContactsSection({ biz, act, toast }) {
  const [editing, setEditing] = useState(null); // contact id | 'new' | null
  const blank = { name: '', title: '', email: '', email_source: '', email_confidence: 'listed', phone: '' };

  const save = (form, id) => act(async () => {
    const payload = Object.fromEntries(Object.entries(form).filter(([, v]) => v !== '' && v != null));
    if (id !== 'new') payload.contact_id = id;
    await api.post('/businesses/' + biz.id + '/contacts', payload);
    setEditing(null);
    toast(id === 'new' ? 'Contact added' : 'Contact updated');
  });

  const remove = (c) => act(async () => {
    await api.del('/contacts/' + c.id);
    toast('Contact removed');
  });

  return (
    <section className="dsec">
      <div className="dsec-label-row">
        <div className="dsec-label">Contacts</div>
        <Btn small onClick={() => setEditing('new')}>+ Add</Btn>
      </div>
      {biz.contacts.length === 0 && editing !== 'new' && (
        <p className="empty-note">No contacts yet — finding one is research work.</p>
      )}
      <div className="contact-list">
        {biz.contacts.map((c) => editing === c.id
          ? <ContactForm key={c.id} initial={c} onSave={(f) => save(f, c.id)} onCancel={() => setEditing(null)} />
          : (
            <div key={c.id} className="contact-row">
              <div className="contact-main">
                <span className="contact-name">{c.name || '—'}{c.is_primary && <Pill tone="pill-subtle">primary</Pill>}</span>
                <span className="meta-dim">{c.title}</span>
              </div>
              <div className="contact-detail">
                {c.email && <span>{c.email} <span className="confidence" title={'Source: ' + (c.email_source || 'unknown')}>{c.email_confidence}</span></span>}
                {c.phone && <span>{c.phone}</span>}
              </div>
              <div className="contact-actions">
                <Btn small onClick={() => setEditing(c.id)}>Edit</Btn>
                <Btn small onClick={() => remove(c)}>Delete</Btn>
              </div>
            </div>
          ))}
        {editing === 'new' && <ContactForm initial={blank} onSave={(f) => save(f, 'new')} onCancel={() => setEditing(null)} />}
      </div>
    </section>
  );
}

function ContactForm({ initial, onSave, onCancel }) {
  const [f, setF] = useState({ ...initial });
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  return (
    <div className="contact-form">
      <div className="cf-grid">
        <input placeholder="Name" value={f.name || ''} onChange={set('name')} />
        <input placeholder="Title" value={f.title || ''} onChange={set('title')} />
        <input placeholder="Email" value={f.email || ''} onChange={set('email')} />
        <input placeholder="Phone" value={f.phone || ''} onChange={set('phone')} />
        <input placeholder="Email source (URL or note)" value={f.email_source || ''} onChange={set('email_source')} />
        <select value={f.email_confidence || 'listed'} onChange={set('email_confidence')}>
          <option value="listed">listed</option>
          <option value="scraped">scraped</option>
          <option value="guessed">guessed</option>
        </select>
      </div>
      <div className="cf-actions">
        <Btn small kind="btn-primary" onClick={() => onSave(f)}>Save</Btn>
        <Btn small onClick={onCancel}>Cancel</Btn>
      </div>
    </div>
  );
}

// ---------- payment + fulfillment ----------
function MoneySection({ p, act, toast }) {
  const f = p.fulfillment || {};
  const items = [
    ['logo_received', 'Logo received'],
    ['offer_confirmed', 'Offer confirmed'],
    ['artwork_approved', 'Artwork approved'],
  ];
  const done = fulfillDone(f);

  const setPay = (field) => (e) => {
    const v = e.target.value || null;
    if (!v) return;
    const body = field === 'payment_status'
      ? { payment_status: v, payment_method: p.payment_method }
      : { payment_status: p.payment_status || 'pending', payment_method: v };
    act(() => api.patch('/participations/' + p.id + '/payment', body).then(() => toast('Payment updated')));
  };

  return (
    <section className="dsec">
      <div className="dsec-label">Payment &amp; fulfillment</div>
      <div className="pay-grid">
        <label>Status
          <select value={p.payment_status || ''} onChange={setPay('payment_status')}>
            <option value="">—</option><option value="pending">pending</option><option value="paid">paid</option>
          </select>
        </label>
        <label>Method
          <select value={p.payment_method || ''} onChange={setPay('payment_method')}>
            <option value="">—</option><option value="cash">cash</option><option value="paypal">paypal</option><option value="check">check</option><option value="other">other</option>
          </select>
        </label>
        <div className="pay-date">
          <span className="meta-dim">{p.paid_at ? 'Paid ' + shortDate(p.paid_at) : 'Not paid yet'}</span>
        </div>
      </div>
      <div className="fulfill">
        <div className="fulfill-head">
          <span>Ready to print</span>
          <span className="meta-dim">{done}/{FULFILLMENT_KEYS.length}</span>
        </div>
        <div className="fulfill-bar"><div className="fulfill-fill" style={{ width: (done / FULFILLMENT_KEYS.length * 100) + '%' }}></div></div>
        <div className="fulfill-items">
          {items.map(([k, label]) => (
            <label key={k} className="check-row">
              <input type="checkbox" checked={!!f[k]} onChange={(e) =>
                act(() => api.patch('/participations/' + p.id + '/fulfillment', { [k]: e.target.checked }))} />
              <span>{label}</span>
            </label>
          ))}
        </div>
      </div>
    </section>
  );
}

// ---------- email thread ----------
// One card, newest version by default; the tiny ←/→ pager in the corner flips through
// prior versions for comparison (no diff — you just look at the one you want).
function EmailThread({ p, act, toast }) {
  const [idx, setIdx] = useState(0);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState({ subject: '', body: '' });
  useEffect(() => { setIdx(0); setEditing(false); }, [p.id, p.emails.length]);

  const emails = p.emails; // newest first
  const e = emails[Math.min(idx, emails.length - 1)];
  const maxV = Math.max(...emails.map((x) => x.version));
  const meta = EMAIL_STATUS_META[e.status];

  const approve = () => act(() => api.post('/emails/' + e.id + '/approve')
    .then(() => toast('Approved — the agent will place it in your Gmail drafts (Copy still works).')));

  const copy = () => {
    const text = 'Subject: ' + e.subject + '\n\n' + e.body;
    if (navigator.clipboard) navigator.clipboard.writeText(text).catch(() => {});
    toast('Copied to clipboard');
  };

  const markSent = () => act(() => api.post('/emails/' + e.id + '/mark-sent')
    .then(() => toast('Marked sent — moved to Contacted.')));

  const saveEdit = () => act(() => api.post('/emails', { participation_id: p.id, subject: draft.subject, body: draft.body })
    .then(() => { setEditing(false); setIdx(0); toast('Saved as next version, attributed to you.'); }));

  return (
    <section className="dsec">
      <div className="dsec-label-row">
        <div className="dsec-label">Email
          {p.email_state === 'revised' && idx === 0 && <Pill tone="pill-review">new version since your feedback</Pill>}
        </div>
        <div className="ver-pager" title="Flip through versions to compare">
          <button className="wl-btn" disabled={idx >= emails.length - 1} title="Older version" onClick={() => { setIdx(idx + 1); setEditing(false); }}>←</button>
          <span className="meta-dim">v{e.version} of {maxV}{idx === 0 ? ' · latest' : ''}</span>
          <button className="wl-btn" disabled={idx === 0} title="Newer version" onClick={() => { setIdx(idx - 1); setEditing(false); }}>→</button>
        </div>
      </div>
      <article className={'email-card ' + meta.cls}>
        <header className="email-head">
          <span className={'email-status ' + meta.cls}>{meta.label}</span>
          {e.provider_draft_id && (
            <a className="email-status es-handoff" href="https://mail.google.com/mail/u/0/#drafts"
              target="_blank" rel="noopener noreferrer"
              title={'Draft created in ' + (e.delivery_provider || 'your mailbox') + ' by the agent ' + timeAgo(e.handed_off_at) + ' — send it from there'}>
              In {e.delivery_provider === 'gmail' ? 'Gmail' : e.delivery_provider} drafts ↗
            </a>
          )}
          <span className="email-author">{e.author === 'agent' ? 'Agent' : 'Grant'}</span>
          <span className="meta-dim">v{e.version} · {timeAgo(e.created_at)}</span>
        </header>
        {editing ? (
          <div className="email-edit">
            <input value={draft.subject} onChange={(ev) => setDraft({ ...draft, subject: ev.target.value })} />
            <textarea rows={9} value={draft.body} onChange={(ev) => setDraft({ ...draft, body: ev.target.value })}></textarea>
            <div className="cf-actions">
              <Btn small kind="btn-primary" onClick={saveEdit}>Save as v{maxV + 1}</Btn>
              <Btn small onClick={() => setEditing(false)}>Cancel</Btn>
            </div>
          </div>
        ) : (
          <div className="email-content">
            <div className="email-subject">{e.subject}</div>
            <pre className="email-body">{e.body}</pre>
          </div>
        )}
        {!editing && <EmailComments e={e} act={act} toast={toast} />}
        {!editing && (
          <footer className="email-actions">
            <Btn small kind="btn-primary" disabled={e.status !== 'in_review'} title={e.status !== 'in_review' ? 'Approve is only available on in-review versions' : ''} onClick={approve}>Approve</Btn>
            <Btn small disabled={e.status !== 'in_review'} title={e.status !== 'in_review' ? 'Only the in-review version can be edited' : 'Saves as the next version, attributed to you'} onClick={() => { setEditing(true); setDraft({ subject: e.subject, body: e.body }); }}>Edit</Btn>
            <Btn small disabled={e.status !== 'approved'} title={e.status !== 'approved' ? 'Copy is enabled once approved' : ''} onClick={copy}>Copy</Btn>
            <Btn small disabled={e.status !== 'approved'} title={e.status !== 'approved' ? 'Mark Sent is enabled once approved' : 'You send it from your own inbox'} onClick={markSent}>Mark Sent</Btn>
          </footer>
        )}
      </article>
    </section>
  );
}

// Shared comment renderer: unresolved comments are always visible; resolved ones are
// collapsed behind a toggle (still on the record, but not obstructive — and invisible
// to the agent, whose worklists only count unresolved).
function CommentList({ comments, act }) {
  const [showResolved, setShowResolved] = useState(false);
  const open = comments.filter((c) => !c.resolved);
  const resolved = comments.filter((c) => c.resolved);
  const resolve = (c) => act(() => api.post('/comments/' + c.id + '/resolve', { resolved: !c.resolved }));
  const row = (c) => (
    <div key={c.id} className={'comment' + (c.resolved ? ' resolved' : '')}>
      <div className="comment-head">
        <span className="comment-author">{c.author === 'agent' ? 'Agent' : 'Grant'}</span>
        <span className="meta-dim">{timeAgo(c.created_at)}</span>
        <button className="resolve-btn" title={c.resolved ? 'Resolved comments are hidden from the agent — reopen to resurface' : 'Resolving hides it from the agent (done or obsolete)'} onClick={() => resolve(c)}>{c.resolved ? 'Resolved ✓' : 'Resolve'}</button>
      </div>
      <p className="comment-body">{c.body}</p>
    </div>
  );
  return (
    <div className="comment-list">
      {open.map(row)}
      {resolved.length > 0 && (
        <button className="resolved-toggle" onClick={() => setShowResolved(!showResolved)}>
          {showResolved ? '▾ hide' : '▸ show'} {resolved.length} resolved
        </button>
      )}
      {showResolved && resolved.map(row)}
    </div>
  );
}

// Per-version feedback: "request revisions" = leave a comment on the draft. The agent's
// next session reads it (revision_requests worklist) and saves the next version; you
// resolve the comment once the revision satisfies it.
function EmailComments({ e, act, toast }) {
  const [text, setText] = useState('');
  const comments = e.comments || [];
  if (comments.length === 0 && e.status !== 'in_review') return null;

  const add = () => {
    if (!text.trim()) return;
    act(() => api.post('/comments', { entity_type: 'email', entity_id: e.id, author: 'grant', body: text.trim() })
      .then(() => { setText(''); toast('Revision requested — the agent will respond with the next version.'); }));
  };

  return (
    <div className="email-feedback">
      <CommentList comments={comments} act={act} />
      {e.status === 'in_review' && (
        <div className="comment-input">
          <textarea rows={2} placeholder={'Request revisions on v' + e.version + '…'} value={text}
            onChange={(ev) => setText(ev.target.value)}
            onKeyDown={(ev) => { if (ev.key === 'Enter' && (ev.metaKey || ev.ctrlKey)) add(); }}></textarea>
          <Btn small kind="btn-primary" onClick={add} disabled={!text.trim()}>Comment</Btn>
        </div>
      )}
    </div>
  );
}

// ---------- comments ----------
function CommentsSection({ biz, act }) {
  const [text, setText] = useState('');
  const add = () => {
    if (!text.trim()) return;
    act(() => api.post('/comments', { entity_type: 'business', entity_id: biz.id, author: 'grant', body: text.trim() })
      .then(() => setText('')));
  };
  return (
    <section className="dsec">
      <div className="dsec-label">Comments</div>
      <CommentList comments={biz.comments || []} act={act} />
      <div className="comment-input">
        <textarea rows={2} placeholder="Leave a comment for the agent…" value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) add(); }}></textarea>
        <Btn small kind="btn-primary" onClick={add} disabled={!text.trim()}>Comment</Btn>
      </div>
    </section>
  );
}
