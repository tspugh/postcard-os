// Campaign view — picker, lifecycle, slot table with inline waitlists, outreach kanban,
// postcard preview with slot-anchored comments, archived read-only history.
import React, { useEffect, useState } from 'react';
import { api } from './api.js';
import {
  ACTIVE_CAMPAIGN_STATUSES, Btn, CategoryTag, EMAIL_STATE_META, fulfillDone, money, Pill,
  shortDate, StatusDot, timeAgo,
} from './ui.jsx';

const LIFECYCLE = ['draft', 'filling', 'full', 'fulfillment', 'completed', 'archived'];
const KB_COLUMNS = ['prospecting', 'contacted', 'interested', 'waitlisted', 'committed'];
const KB_META = {
  prospecting: { label: 'Prospecting', color: 'var(--c-cyan)' },
  contacted:   { label: 'Contacted',   color: 'var(--c-violet)' },
  interested:  { label: 'Interested',  color: 'var(--c-amber)' },
  waitlisted:  { label: 'Waitlisted',  color: 'var(--c-orange)' },
  committed:   { label: 'Committed',   color: 'var(--c-green)' },
};

export function CampaignView({ settings, version, onOpen, toast, bump }) {
  const [campaigns, setCampaigns] = useState(null);
  const [campId, setCampId] = useState(null);
  const [board, setBoard] = useState(null);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    api.get('/campaigns').then((cs) => {
      setCampaigns(cs);
      if (cs.length && !cs.some((c) => c.id === campId)) {
        const active = cs.find((c) => ACTIVE_CAMPAIGN_STATUSES.includes(c.status));
        setCampId((active || cs[0]).id);
      }
    }).catch((e) => toast(e.message));
  }, [version]);

  useEffect(() => {
    if (campId) api.get('/campaigns/' + campId + '/board').then(setBoard).catch((e) => toast(e.message));
  }, [campId, version]);

  if (campaigns === null) return <div className="view-pad"><p className="empty-view">Loading…</p></div>;
  if (campaigns.length === 0) return <div className="view-pad"><CreateCampaign settings={settings} toast={toast} bump={bump} /></div>;
  if (!board) return <div className="view-pad"><p className="empty-view">Loading…</p></div>;

  const status = board.campaign.status;
  const isArchived = status === 'archived' || status === 'completed';

  return (
    <div className="view-pad">
      <div className="camp-head">
        <select className="camp-select" value={campId || ''} onChange={(e) => setCampId(e.target.value)}>
          {campaigns.map((c) => <option key={c.id} value={c.id}>{c.name} — {c.status}</option>)}
        </select>
        <Btn small onClick={() => setCreating(!creating)}>{creating ? 'Cancel' : '+ New campaign'}</Btn>
        <div className="camp-lifecycle">
          {LIFECYCLE.map((s) => <span key={s} className={'stage' + (status === s ? ' current' : '')}>{s}</span>)}
        </div>
      </div>
      {creating && (
        <CreateCampaign settings={settings} toast={toast} bump={bump}
          onDone={(c) => { setCreating(false); if (c?.id) setCampId(c.id); }} />
      )}
      {isArchived
        ? <ArchivedCampaign board={board} onOpen={onOpen} />
        : <LiveCampaign board={board} onOpen={onOpen} toast={toast} bump={bump} />}
    </div>
  );
}

const MONTHS = [
  ['01', 'January'], ['02', 'February'], ['03', 'March'], ['04', 'April'],
  ['05', 'May'], ['06', 'June'], ['07', 'July'], ['08', 'August'],
  ['09', 'September'], ['10', 'October'], ['11', 'November'], ['12', 'December'],
];

// Explicit month/year selects instead of <input type="month">: Firefox and
// desktop Safari render that as a bare text box with no picker.
function CreateCampaign({ settings, toast, bump, onDone }) {
  const thisYear = new Date().getFullYear();
  const [monthNum, setMonthNum] = useState('');
  const [year, setYear] = useState(String(thisYear));
  const [name, setName] = useState('');
  const [deadline, setDeadline] = useState('');
  const monthLabel = monthNum ? MONTHS.find(([n]) => n === monthNum)[1] : '';
  const autoName = monthNum ? `${settings.seed_market} ${monthLabel} ${year}` : 'auto-named from market + month';
  const submit = () => {
    const body = { month: `${year}-${monthNum}-01`, deadline };
    if (name.trim()) body.name = name.trim();
    api.post('/campaigns', body)
      .then((c) => { toast('Campaign created'); onDone?.(c); bump(); })
      .catch((e) => toast(e.message));
  };
  return (
    <div className="camp-create">
      <h3>New campaign</h3>
      <p>One postcard run: {settings.seed_market} · {settings.default_total_slots} slots at {money(settings.default_slot_price_cents)} (snapshotted from settings). Multiple campaigns can run in the same month.</p>
      <div className="set-field"><label>Name</label>
        <input type="text" value={name} placeholder={autoName} onChange={(e) => setName(e.target.value)} />
      </div>
      <div className="set-field"><label>Month</label>
        <div className="field-row">
          <select value={monthNum} onChange={(e) => setMonthNum(e.target.value)}>
            <option value="" disabled>Select month…</option>
            {MONTHS.map(([num, label]) => <option key={num} value={num}>{label}</option>)}
          </select>
          <select value={year} onChange={(e) => setYear(e.target.value)}>
            {[thisYear, thisYear + 1, thisYear + 2].map((y) => <option key={y} value={y}>{y}</option>)}
          </select>
        </div>
      </div>
      <div className="set-field"><label>Deadline</label><input type="date" value={deadline} onChange={(e) => setDeadline(e.target.value)} /></div>
      <Btn kind="btn-primary" disabled={!monthNum || !deadline} onClick={submit}>Create campaign</Btn>
    </div>
  );
}

function StatStrip({ stats }) {
  return (
    <div className="summary-strip">
      {stats.map((s, i) => (
        <div key={i} className={'stat' + (s.hot ? ' stat-hot' : '')}>
          <div className="stat-label">{s.label}</div>
          <div className="stat-value">{s.value}</div>
          <div className="stat-sub">{s.sub}</div>
        </div>
      ))}
    </div>
  );
}

function ParticipationCard({ p, onOpen }) {
  const isCommitted = p.status === 'committed' || p.status === 'paid';
  const feedback = (p.unresolved_feedback || 0) + (p.business_unresolved_comments || 0);
  return (
    <button className="lead-card" onClick={() => onOpen(p.business_id)}>
      <div className="lead-top">
        <span className="lead-name">{p.business_name}</span>
        {feedback > 0 && <span className="fb-badge" title={feedback + ' unresolved comment' + (feedback > 1 ? 's' : '')}>💬 {feedback}</span>}
      </div>
      <div className="lead-tags">
        <CategoryTag category={p.category} />
        {p.status === 'waitlisted' && <Pill tone="pill-orange">#{p.waitlist_order} waitlist</Pill>}
        {p.status === 'paid' && <Pill tone="pill-green">paid</Pill>}
        {p.email_state && p.email_state !== 'sent' && (
          <Pill tone={EMAIL_STATE_META[p.email_state].tone}>
            {p.email_state === 'draft_in_review' && p.drafts_in_review > 1
              ? p.drafts_in_review + ' drafts to review'
              : EMAIL_STATE_META[p.email_state].label}
          </Pill>
        )}
        {p.status === 'prospecting' && !p.email_state && <Pill tone="pill-subtle">no draft yet</Pill>}
      </div>
      <div className="lead-foot">
        <span>{timeAgo(p.created_at)}</span>
        {!isCommitted && <span className="lead-price">{money(p.asking_price_cents)} asking</span>}
        {isCommitted && <span className="lead-price committed-price">{money(p.committed_amount_cents)}{p.committed_amount_cents !== p.asking_price_cents ? ' (neg.)' : ''}</span>}
        {isCommitted && <span className="mini-checklist">{p.fulfillment_progress} ✓</span>}
      </div>
    </button>
  );
}

function LiveCampaign({ board, onOpen, toast, bump }) {
  const c = board.campaign;
  const stats = [
    { label: 'Slots filled', value: board.slots_filled + ' of ' + board.slots_total, sub: (board.slots_total - board.slots_filled) + ' remaining · mirror this urgency' },
    { label: 'Committed', value: money(board.committed_cents), sub: 'asking ' + money(c.slot_price_cents) + '/slot' },
    { label: 'Collected', value: money(board.collected_cents), sub: money(board.committed_cents - board.collected_cents) + ' outstanding' },
    { label: 'Waitlisted', value: String(board.waitlist_count), sub: 'preserved revenue' },
    { label: 'Deadline', value: board.days_until_deadline + ' days', sub: 'closes ' + shortDate(c.deadline) },
  ];

  const active = board.participations.filter((p) => p.status !== 'declined');
  const declined = board.participations.filter((p) => p.status === 'declined');

  return (
    <div>
      <StatStrip stats={stats} />

      <section>
        <h2 className="sec-label">Category slots — one business per industry</h2>
        <SlotTable board={board} onOpen={onOpen} toast={toast} bump={bump} />
      </section>

      <section style={{ marginTop: '22px' }}>
        <h2 className="sec-label">Outreach pipeline — this campaign</h2>
        <div className="kb">
          {KB_COLUMNS.map((col) => {
            const cards = active.filter((p) => col === 'committed' ? ['committed', 'paid'].includes(p.status) : p.status === col);
            return (
              <div key={col} className="kb-col">
                <div className="kb-head"><span className="status-dot" style={{ background: KB_META[col].color }}></span>{KB_META[col].label}<span className="kb-count">{cards.length}</span></div>
                <div className="kb-cards">
                  {cards.map((p) => <ParticipationCard key={p.id} p={p} onOpen={onOpen} />)}
                  {cards.length === 0 && <div className="kb-empty">Empty</div>}
                </div>
              </div>
            );
          })}
          {declined.length > 0 && (
            <div className="kb-col">
              <div className="kb-head"><span className="status-dot" style={{ background: 'var(--c-red)' }}></span>Declined<span className="kb-count">{declined.length}</span></div>
              <div className="kb-cards">
                {declined.map((p) => (
                  <button key={p.id} className="lead-card closed-card" onClick={() => onOpen(p.business_id)}>
                    <div className="lead-top"><span className="lead-name">{p.business_name}</span></div>
                    <div className="lead-tags"><CategoryTag category={p.category} /><Pill tone="pill-red">declined</Pill></div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>

      <PostcardPreview board={board} toast={toast} />
    </div>
  );
}

function SlotTable({ board, onOpen, toast, bump }) {
  const act = (fn) => fn().then(bump).catch((e) => toast(e.message));

  const move = (slot, idx, dir) => {
    const ids = slot.waitlist.map((w) => w.id);
    [ids[idx], ids[idx + dir]] = [ids[idx + dir], ids[idx]];
    act(() => api.post('/campaigns/' + board.campaign.id + '/waitlist-order', { category: slot.category, participation_ids: ids })
      .then(() => toast('Waitlist reordered')));
  };

  const promote = (w) => {
    const dollars = window.prompt('Committed amount for ' + w.business_name + ' (dollars) — promotion is a commitment:', String((w.asking_price_cents || 0) / 100));
    if (dollars == null) return;
    const cents = Math.round(parseFloat(dollars.replace(/[^0-9.]/g, '')) * 100);
    if (!cents || cents <= 0) { toast('Promotion requires a positive committed amount.'); return; }
    act(() => api.post('/participations/' + w.id + '/promote', { amount_cents: cents })
      .then(() => toast('Promoted — slot assigned at ' + money(cents))));
  };

  const pitchedByCat = {};
  board.participations.forEach((p) => {
    if (['prospecting', 'contacted', 'interested'].includes(p.status)) {
      (pitchedByCat[p.category] = pitchedByCat[p.category] || []).push(p);
    }
  });

  return (
    <div className="lt-wrap">
      <table className="lt slot-lt">
        <thead>
          <tr><th>Category</th><th>Business</th><th>Status</th><th>Amount</th><th>Payment</th><th>Fulfillment</th><th>Waitlist</th></tr>
        </thead>
        <tbody>
          {board.slots.map((slot) => {
            const winner = slot.committed;
            const pitched = pitchedByCat[slot.category] || [];
            const done = winner ? parseInt(winner.fulfillment_progress) : 0;
            return (
              <tr key={slot.category} className={winner ? '' : 'slot-open-row'}>
                <td><span className="lt-name"><CategoryTag category={slot.category} />{winner && <span className="dim num">slot {winner.slot_number}</span>}</span></td>
                <td>
                  {winner
                    ? <a className="link slot-biz" onClick={() => onOpen(findBusinessId(board, winner.participation_id))}>{winner.business_name}</a>
                    : pitched.length > 0
                      ? <span className="slot-pitched">{pitched.map((p) => <a key={p.id} className="link" onClick={() => onOpen(p.business_id)}>{p.business_name}</a>)}</span>
                      : <span className="dim">—</span>}
                </td>
                <td>
                  {winner
                    ? <Pill tone="pill-green">committed{winner.payment_status === 'paid' ? ' · paid' : ''}</Pill>
                    : pitched.length > 0
                      ? <Pill>{pitched.length} active pitch{pitched.length > 1 ? 'es' : ''}</Pill>
                      : <Pill tone="pill-subtle">open</Pill>}
                </td>
                <td className="num">{winner
                  ? <span className="committed-price">{money(winner.amount_cents)}</span>
                  : <span className="dim">{money(board.campaign.slot_price_cents)} asking</span>}</td>
                <td>{winner ? (winner.payment_status === 'paid' ? <Pill tone="pill-green">paid</Pill> : <Pill>unpaid</Pill>) : <span className="dim">—</span>}</td>
                <td>{winner
                  ? <span className="ft-mini" title={winner.fulfillment_progress + ' — logo, offer, artwork'}><span className="ft-mini-bar"><span className="ft-mini-fill" style={{ width: (done / 3 * 100) + '%' }}></span></span><span className="num dim">{winner.fulfillment_progress}</span></span>
                  : <span className="dim">—</span>}</td>
                <td>
                  {slot.waitlist.length === 0 ? <span className="dim">—</span> : (
                    <div className="wl-cell">
                      {slot.waitlist.map((w, i) => (
                        <span key={w.id} className="wl-cell-row">
                          <span className="wl-pos">#{w.waitlist_order}</span>
                          <a className="link" onClick={() => onOpen(w.business_id)}>{w.business_name}</a>
                          <span className="wl-actions">
                            <button className="wl-btn" disabled={i === 0} title="Move up" onClick={() => move(slot, i, -1)}>↑</button>
                            <button className="wl-btn" disabled={i === slot.waitlist.length - 1} title="Move down" onClick={() => move(slot, i, 1)}>↓</button>
                            <button className="wl-btn wl-promote" disabled={!!winner}
                              title={winner ? 'Enabled when the ' + slot.category + ' slot frees up. Requires a committed amount.' : 'Promote — requires committed amount'}
                              onClick={() => promote(w)}>Promote</button>
                          </span>
                        </span>
                      ))}
                    </div>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="lt-foot">Waitlist: next-in-line is the default, you keep final say — and it carries forward as priority prospects for the next campaign.</div>
    </div>
  );
}

const findBusinessId = (board, participationId) =>
  (board.participations.find((p) => p.id === participationId) || {}).business_id;

function ArchivedCampaign({ board, onOpen }) {
  const c = board.campaign;
  const stats = [
    { label: 'Slots filled', value: board.slots_filled + ' of ' + board.slots_total, sub: board.scarcity },
    { label: 'Committed', value: money(board.committed_cents), sub: 'final' },
    { label: 'Collected', value: money(board.collected_cents), sub: money(board.committed_cents - board.collected_cents) + ' outstanding' },
    { label: 'Waitlisted', value: String(board.waitlist_count), sub: 'carried forward as priority' },
    { label: 'Closed', value: shortDate(c.deadline), sub: c.status === 'archived' ? 'archived, never deleted' : 'completed' },
  ];
  return (
    <div>
      <div className="archived-banner"><strong>{c.status === 'archived' ? 'Archived.' : 'Completed.'}</strong> Read-only history — participants and waitlist below surface as priority prospects when the next campaign is composed.</div>
      <StatStrip stats={stats} />
      <h2 className="sec-label">Participants</h2>
      <div className="lt-wrap" style={{ maxWidth: '880px' }}>
        <table className="lt" style={{ minWidth: '640px' }}>
          <thead><tr><th>Business</th><th>Category</th><th>Outcome</th><th>Amount</th><th>Method</th><th>Slot</th></tr></thead>
          <tbody>
            {board.participations.map((p) => (
              <tr key={p.id} onClick={() => onOpen(p.business_id)}>
                <td><span className="lt-name">{p.business_name}</span></td>
                <td><CategoryTag category={p.category} /></td>
                <td>
                  {p.status === 'paid' && <Pill tone="pill-green">paid</Pill>}
                  {p.status === 'committed' && <Pill tone="pill-green">committed</Pill>}
                  {p.status === 'waitlisted' && <Pill tone="pill-orange">waitlisted #{p.waitlist_order} → carried forward</Pill>}
                  {p.status === 'declined' && <Pill tone="pill-red">declined</Pill>}
                  {['prospecting', 'contacted', 'interested'].includes(p.status) && <Pill>{p.status}</Pill>}
                </td>
                <td className="num">{p.committed_amount_cents ? money(p.committed_amount_cents) : '—'}</td>
                <td className="dim">{p.payment_method || '—'}</td>
                <td className="num dim">{p.slot_number || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---------- postcard preview ----------
function PostcardPreview({ board, toast }) {
  const campId = board.campaign.id;
  const [drafts, setDrafts] = useState([]);
  const [draftId, setDraftId] = useState(null);
  const [comments, setComments] = useState([]);
  const [selected, setSelected] = useState(null);
  const [text, setText] = useState('');

  useEffect(() => {
    api.get('/postcards/' + campId).then((ds) => {
      setDrafts(ds);
      setDraftId(ds.length ? ds[0].id : null);
    }).catch(() => setDrafts([]));
  }, [campId]);

  const draft = drafts.find((d) => d.id === draftId) || null;

  const loadComments = () => {
    if (!draft) return;
    api.get('/comments?entity_type=postcard_slot&entity_id=' + draft.id).then(setComments).catch(() => {});
  };
  useEffect(loadComments, [draftId]);

  const slotContent = {};
  if (draft) draft.slots.forEach((s) => { slotContent[s.slot] = s; });
  const committedBySlot = {};
  board.participations.forEach((p) => { if (p.slot_number) committedBySlot[p.slot_number] = p; });
  const openCats = board.slots.filter((s) => !s.committed).map((s) => s.category);

  let openIdx = 0;
  const cells = Array.from({ length: board.slots_total }, (_, i) => {
    const n = i + 1;
    const content = slotContent[n];
    const part = committedBySlot[n];
    if (content || part) return { n, content, part };
    return { n, cat: openCats[openIdx++] || 'open' };
  });

  const addComment = () => {
    if (!text.trim() || !selected || !draft) return;
    api.post('/comments', { entity_type: 'postcard_slot', entity_id: draft.id, slot_number: selected, author: 'grant', body: text.trim() })
      .then(() => { setText(''); loadComments(); toast('Comment anchored to slot ' + selected); })
      .catch((e) => toast(e.message));
  };
  const resolve = (c) => api.post('/comments/' + c.id + '/resolve', { resolved: !c.resolved }).then(loadComments).catch((e) => toast(e.message));

  const slotComments = comments.filter((c) => c.slot_number === selected);
  const month = new Date(board.campaign.month + 'T00:00:00').toLocaleDateString('en-US', { month: 'long', year: 'numeric' }).toUpperCase();

  return (
    <section className="pc-section">
      <h2 className="sec-label">Postcard preview</h2>
      <div className="pc-frame-wrap">
        <div className="pc-card">
          <div className="pc-header">{board.campaign.market.split(',')[0]} Local Business Spotlight<span className="pc-month">{month} · {draft ? draft.template_id : 'no draft yet'}</span></div>
          <div className="pc-grid">
            {cells.map((s) => {
              const isSel = selected === s.n;
              if (s.content || s.part) {
                return (
                  <button key={s.n} className={'pc-slot' + (isSel ? ' selected' : '')} onClick={() => setSelected(isSel ? null : s.n)}>
                    <span className="pcs-biz">{s.part ? s.part.business_name : ''}</span>
                    <span className="pcs-headline">{s.content ? s.content.headline : '—'}</span>
                    <span className="pcs-offer">{s.content ? s.content.offer_text : 'no slot content yet'}</span>
                    <span className="pcs-contact">{s.content ? s.content.contact_line : ''}</span>
                    {comments.some((c) => c.slot_number === s.n && !c.resolved) && <span className="pcs-comment-dot" title="Unresolved comment"></span>}
                  </button>
                );
              }
              return (
                <button key={s.n} className={'pc-slot empty' + (isSel ? ' selected' : '')} onClick={() => setSelected(isSel ? null : s.n)}>
                  <span className="pcs-cat">{s.cat}</span>
                  <span className="pcs-open">slot {s.n} · open</span>
                </button>
              );
            })}
          </div>
        </div>
        <div className="pc-side">
          <div className="pc-meta-row">
            <span>Draft</span>
            {drafts.length > 0 ? (
              <select value={draftId || ''} onChange={(e) => setDraftId(e.target.value)}>
                {drafts.map((d) => <option key={d.id} value={d.id}>v{d.version}{d.id === drafts[0].id ? ' — current' : ''}</option>)}
              </select>
            ) : <span className="meta-dim">none yet — the agent saves drafts via MCP</span>}
            <span className="meta-dim">· empty slots print as labeled placeholders</span>
          </div>
          <div className="pc-comments">
            {selected == null && <p className="pc-comments-empty">Click a slot to read or leave feedback anchored to it — “make the plumber’s offer bigger” goes on the plumber’s slot.</p>}
            {selected != null && (
              <div>
                <div className="dsec-label">Slot {selected} comments</div>
                {!draft && <p className="pc-comments-empty">Slot comments unlock once the agent saves a postcard draft.</p>}
                {draft && slotComments.length === 0 && <p className="pc-comments-empty">No comments on this slot yet.</p>}
                <div className="comment-list">
                  {slotComments.map((c) => (
                    <div key={c.id} className={'comment' + (c.resolved ? ' resolved' : '')}>
                      <div className="comment-head">
                        <span className="comment-author">{c.author === 'agent' ? 'Agent' : 'Grant'}</span>
                        <span className="meta-dim">{timeAgo(c.created_at)}</span>
                        <button className="resolve-btn" onClick={() => resolve(c)}>{c.resolved ? 'Resolved ✓' : 'Resolve'}</button>
                      </div>
                      <p className="comment-body">{c.body}</p>
                    </div>
                  ))}
                </div>
                {draft && (
                  <div className="comment-input">
                    <textarea rows={2} placeholder={'Comment on slot ' + selected + '…'} value={text} onChange={(e) => setText(e.target.value)}></textarea>
                    <Btn small kind="btn-primary" onClick={addComment} disabled={!text.trim()}>Comment</Btn>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
