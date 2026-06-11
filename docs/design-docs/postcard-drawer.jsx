// Detail drawer — research, contacts, email thread, comments, payment & fulfillment
const ACTIVE_STATUSES = ['prospecting', 'contacted', 'interested', 'waitlisted', 'committed', 'paid'];

function DetailDrawer({ biz, settings, campaign, onClose, update, toast }) {
  const p = biz.participation;
  const col = columnOf(biz);
  const isActive = p && ACTIVE_STATUSES.includes(p.status);
  const isCommitted = p && (p.status === 'committed' || p.status === 'paid');

  React.useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="drawer-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <aside className="drawer" data-screen-label={'Detail: ' + biz.name}>
        <header className="drawer-head">
          <div className="drawer-head-top">
            <Pill tone="pill-status"><StatusDot status={col} />{STATUS_META[col].label}{p && p.status === 'paid' ? ' · Paid' : ''}</Pill>
            <button className="icon-btn" onClick={onClose} title="Close (Esc)">
              <svg width="14" height="14" viewBox="0 0 14 14"><path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"></path></svg>
            </button>
          </div>
          <h2 className="drawer-title">{biz.name}</h2>
          <div className="drawer-meta">
            <a className="link" href={biz.website} target="_blank" rel="noopener">{biz.website.replace('https://', '')}</a>
            <span className="meta-dim">·</span>
            <label className="cat-edit">
              <select value={biz.category} onChange={(e) => { update(biz.id, (b) => { b.category = e.target.value; }); toast('Category updated'); }}>
                {settings.categories.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </label>
            <span className="meta-dim">·</span>
            <span className="meta-dim">added {timeAgo(biz.createdAt)} · {biz.source === 'operator' ? 'staged by you' : 'staged by agent'}</span>
          </div>
        </header>

        <div className="drawer-body">
          {biz.dq && (
            <div className="dq-banner">
              <strong>Disqualified — {biz.dq.code}</strong>
              <p>{biz.dq.note}</p>
            </div>
          )}

          {biz.status === 'researching' && (
            <div className="claim-banner">Claimed by agent {timeAgo(biz.claimedAt)} — research in progress.</div>
          )}

          {p && (
            <section className="dsec">
              <div className="dsec-label">Campaign</div>
              <div className="part-row">
                <span>{campaign.name}</span>
                <span className="meta-dim">asking {money(p.askingPriceCents)}</span>
                {p.committedAmountCents != null && <Pill tone="pill-green">committed {money(p.committedAmountCents)}{p.committedAmountCents !== p.askingPriceCents ? ' (negotiated)' : ''}</Pill>}
                {p.slot != null && <Pill>slot {p.slot}</Pill>}
                {p.status === 'waitlisted' && <Pill tone="pill-orange">waitlist #{p.waitlistOrder}</Pill>}
              </div>
            </section>
          )}

          {(biz.premise || biz.hooks.length > 0 || biz.evidence.length > 0) && (
            <section className="dsec">
              <div className="dsec-label">Research</div>
              {biz.premise && <p className="premise">{biz.premise}</p>}
              {biz.hooks.length > 0 && (
                <div className="hooks">
                  {biz.hooks.map((h, i) => <span key={i} className="hook-chip">{h}</span>)}
                </div>
              )}
              {biz.evidence.length > 0 && (
                <div className="evidence">
                  {biz.evidence.map((u, i) => (
                    <a key={i} className="link evidence-link" href={u} target="_blank" rel="noopener">
                      <svg width="11" height="11" viewBox="0 0 12 12"><path d="M5 2H2v8h8V7M7 1h4v4M11 1L5.5 6.5" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"></path></svg>
                      {u.replace('https://', '')}
                    </a>
                  ))}
                </div>
              )}
            </section>
          )}

          <ContactsSection biz={biz} isActive={isActive} update={update} toast={toast} />

          {isCommitted && <MoneySection biz={biz} update={update} toast={toast} />}

          {p && p.emails.length > 0 && <EmailThread biz={biz} update={update} toast={toast} />}

          <CommentsSection biz={biz} update={update} />

          {p && p.events.length > 0 && (
            <section className="dsec">
              <div className="dsec-label">State changes</div>
              <ul className="events">
                {p.events.map((ev, i) => (
                  <li key={i}><span className="event-dot"></span>{ev.label}<span className="meta-dim event-ts">{timeAgo(ev.ts)}</span></li>
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
function ContactsSection({ biz, isActive, update, toast }) {
  const [editing, setEditing] = React.useState(null); // contact id | 'new' | null
  const blank = { name: '', title: '', email: '', emailSource: '', emailConfidence: 'listed', phone: '' };

  const reachable = biz.contacts.filter((c) => c.email || c.phone);

  const remove = (c) => {
    if (isActive && reachable.length === 1 && (c.email || c.phone)) {
      toast('Blocked: last reachable contact on an active advertiser — edit instead of deleting.');
      return;
    }
    update(biz.id, (b) => { b.contacts = b.contacts.filter((x) => x.id !== c.id); });
    toast('Contact removed');
  };

  const save = (form, id) => {
    if (!form.email && !form.phone) { toast('A contact needs an email or a phone.'); return; }
    update(biz.id, (b) => {
      if (id === 'new') {
        b.contacts = [...b.contacts, { ...form, id: 'c-' + Math.random().toString(36).slice(2), isPrimary: b.contacts.length === 0 }];
      } else {
        b.contacts = b.contacts.map((x) => x.id === id ? { ...x, ...form } : x);
      }
    });
    setEditing(null);
    toast(id === 'new' ? 'Contact added' : 'Contact updated');
  };

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
                <span className="contact-name">{c.name || '—'}{c.isPrimary && <Pill tone="pill-subtle">primary</Pill>}</span>
                <span className="meta-dim">{c.title}</span>
              </div>
              <div className="contact-detail">
                {c.email && <span>{c.email} <span className="confidence" title={'Source: ' + (c.emailSource || 'unknown')}>{c.emailConfidence}</span></span>}
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
  const [f, setF] = React.useState({ ...initial });
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  return (
    <div className="contact-form">
      <div className="cf-grid">
        <input placeholder="Name" value={f.name || ''} onChange={set('name')} />
        <input placeholder="Title" value={f.title || ''} onChange={set('title')} />
        <input placeholder="Email" value={f.email || ''} onChange={set('email')} />
        <input placeholder="Phone" value={f.phone || ''} onChange={set('phone')} />
        <input placeholder="Email source (URL or note)" value={f.emailSource || ''} onChange={set('emailSource')} />
        <select value={f.emailConfidence || 'listed'} onChange={set('emailConfidence')}>
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
function MoneySection({ biz, update, toast }) {
  const p = biz.participation;
  const f = p.fulfillment;
  const items = [
    ['logo_received', 'Logo received'],
    ['offer_confirmed', 'Offer confirmed'],
    ['artwork_approved', 'Artwork approved'],
  ];
  const doneCount = items.filter(([k]) => f[k]).length;

  const setPay = (k) => (e) => {
    const v = e.target.value || null;
    update(biz.id, (b) => {
      b.participation[k] = v;
      if (k === 'paymentStatus' && v === 'paid') {
        b.participation.paidAt = new Date().toISOString();
        b.participation.status = 'paid';
        b.participation.events = [{ label: 'Payment recorded — ' + money(b.participation.committedAmountCents) + (b.participation.paymentMethod ? ' ' + b.participation.paymentMethod : ''), ts: new Date().toISOString() }, ...b.participation.events];
      }
      if (k === 'paymentStatus' && v !== 'paid' && b.participation.status === 'paid') {
        b.participation.status = 'committed';
        b.participation.paidAt = null;
      }
    });
    toast('Payment updated');
  };

  return (
    <section className="dsec">
      <div className="dsec-label">Payment &amp; fulfillment</div>
      <div className="pay-grid">
        <label>Status
          <select value={p.paymentStatus || ''} onChange={setPay('paymentStatus')}>
            <option value="">—</option><option value="pending">pending</option><option value="paid">paid</option>
          </select>
        </label>
        <label>Method
          <select value={p.paymentMethod || ''} onChange={setPay('paymentMethod')}>
            <option value="">—</option><option value="cash">cash</option><option value="paypal">paypal</option><option value="check">check</option><option value="other">other</option>
          </select>
        </label>
        <div className="pay-date">
          <span className="meta-dim">{p.paidAt ? 'Paid ' + shortDate(p.paidAt) : 'Not paid yet'}</span>
        </div>
      </div>
      <div className="fulfill">
        <div className="fulfill-head">
          <span>Ready to print</span>
          <span className="meta-dim">{doneCount}/3</span>
        </div>
        <div className="fulfill-bar"><div className="fulfill-fill" style={{ width: (doneCount / 3 * 100) + '%' }}></div></div>
        <div className="fulfill-items">
          {items.map(([k, label]) => (
            <label key={k} className="check-row">
              <input type="checkbox" checked={!!f[k]} onChange={(e) => {
                update(biz.id, (b) => { b.participation.fulfillment = { ...b.participation.fulfillment, [k]: e.target.checked }; });
              }} />
              <span>{label}</span>
            </label>
          ))}
        </div>
      </div>
    </section>
  );
}

// ---------- email thread ----------
function EmailThread({ biz, update, toast }) {
  const p = biz.participation;
  const [editingV, setEditingV] = React.useState(null);
  const [draft, setDraft] = React.useState({ subject: '', body: '' });
  const sorted = [...p.emails].sort((a, b) => b.v - a.v);

  const approve = (v) => {
    update(biz.id, (b) => {
      b.participation.emails = b.participation.emails.map((e) => e.v === v ? { ...e, status: 'approved' } : e);
      b.participation.events = [{ label: 'v' + v + ' approved by operator', ts: new Date().toISOString() }, ...b.participation.events];
    });
    toast('Approved — copy it and send from your inbox.');
  };

  const copy = (e) => {
    const text = 'Subject: ' + e.subject + '\n\n' + e.body;
    if (navigator.clipboard) navigator.clipboard.writeText(text).catch(() => {});
    toast('Copied to clipboard');
  };

  const markSent = (v) => {
    update(biz.id, (b) => {
      b.participation.emails = b.participation.emails.map((e) => e.v === v ? { ...e, status: 'sent' } : e);
      b.participation.events = [{ label: 'Marked sent by operator', ts: new Date().toISOString() }, ...b.participation.events];
      if (b.participation.status === 'prospecting') b.participation.status = 'contacted';
    });
    toast('Marked sent — moved to Contacted.');
  };

  const startEdit = (e) => { setEditingV(e.v); setDraft({ subject: e.subject, body: e.body }); };

  const saveEdit = () => {
    update(biz.id, (b) => {
      const maxV = Math.max(...b.participation.emails.map((e) => e.v));
      b.participation.emails = b.participation.emails.map((e) => e.status === 'in_review' ? { ...e, status: 'superseded' } : e);
      b.participation.emails = [...b.participation.emails, { v: maxV + 1, author: 'operator', status: 'in_review', subject: draft.subject, body: draft.body, ts: new Date().toISOString() }];
      b.participation.events = [{ label: 'v' + (maxV + 1) + ' saved by operator (edit)', ts: new Date().toISOString() }, ...b.participation.events];
    });
    setEditingV(null);
    toast('Saved as next version, attributed to you.');
  };

  return (
    <section className="dsec">
      <div className="dsec-label">Email thread <span className="meta-dim">({sorted.length} version{sorted.length === 1 ? '' : 's'}, newest first)</span></div>
      <div className="email-list">
        {sorted.map((e) => {
          const meta = EMAIL_STATUS_META[e.status];
          const isEditing = editingV === e.v;
          return (
            <article key={e.v} className={'email-card ' + meta.cls}>
              <header className="email-head">
                <span className={'email-status ' + meta.cls}>{meta.label}</span>
                <span className="email-author">{e.author === 'agent' ? 'Agent' : 'Grant'}</span>
                <span className="meta-dim">v{e.v} · {timeAgo(e.ts)}</span>
              </header>
              {isEditing ? (
                <div className="email-edit">
                  <input value={draft.subject} onChange={(ev) => setDraft({ ...draft, subject: ev.target.value })} />
                  <textarea rows={9} value={draft.body} onChange={(ev) => setDraft({ ...draft, body: ev.target.value })}></textarea>
                  <div className="cf-actions">
                    <Btn small kind="btn-primary" onClick={saveEdit}>Save as v{Math.max(...p.emails.map((x) => x.v)) + 1}</Btn>
                    <Btn small onClick={() => setEditingV(null)}>Cancel</Btn>
                  </div>
                </div>
              ) : (
                <div className="email-content">
                  <div className="email-subject">{e.subject}</div>
                  <pre className="email-body">{e.body}</pre>
                </div>
              )}
              {!isEditing && (
                <footer className="email-actions">
                  <Btn small kind="btn-primary" disabled={e.status !== 'in_review'} title={e.status !== 'in_review' ? 'Approve is only available on in-review versions' : ''} onClick={() => approve(e.v)}>Approve</Btn>
                  <Btn small disabled={e.status !== 'in_review'} title={e.status !== 'in_review' ? 'Only the in-review version can be edited' : 'Saves as the next version, attributed to you'} onClick={() => startEdit(e)}>Edit</Btn>
                  <Btn small disabled={e.status !== 'approved'} title={e.status !== 'approved' ? 'Copy is enabled once approved' : ''} onClick={() => copy(e)}>Copy</Btn>
                  <Btn small disabled={e.status !== 'approved'} title={e.status !== 'approved' ? 'Mark Sent is enabled once approved' : 'You send it from your own inbox'} onClick={() => markSent(e.v)}>Mark Sent</Btn>
                </footer>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}

// ---------- comments ----------
function CommentsSection({ biz, update }) {
  const [text, setText] = React.useState('');
  const add = () => {
    if (!text.trim()) return;
    update(biz.id, (b) => {
      b.comments = [...b.comments, { id: 'cm-' + Math.random().toString(36).slice(2), author: 'grant', body: text.trim(), ts: new Date().toISOString(), resolved: false }];
    });
    setText('');
  };
  return (
    <section className="dsec">
      <div className="dsec-label">Comments</div>
      <div className="comment-list">
        {biz.comments.map((c) => (
          <div key={c.id} className={'comment' + (c.resolved ? ' resolved' : '')}>
            <div className="comment-head">
              <span className="comment-author">{c.author === 'grant' ? 'Grant' : 'Agent'}</span>
              <span className="meta-dim">{timeAgo(c.ts)}</span>
              <button className="resolve-btn" onClick={() => update(biz.id, (b) => {
                b.comments = b.comments.map((x) => x.id === c.id ? { ...x, resolved: !x.resolved } : x);
              })}>{c.resolved ? 'Resolved ✓' : 'Resolve'}</button>
            </div>
            <p className="comment-body">{c.body}</p>
          </div>
        ))}
      </div>
      <div className="comment-input">
        <textarea rows={2} placeholder="Leave a comment for the agent…" value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) add(); }}></textarea>
        <Btn small kind="btn-primary" onClick={add} disabled={!text.trim()}>Comment</Btn>
      </div>
    </section>
  );
}

Object.assign(window, { DetailDrawer });
