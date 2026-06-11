// Campaign view — picker, slot board, waitlist panel, outreach kanban, postcard preview
const LIFECYCLE = ['draft', 'filling', 'full', 'fulfillment', 'completed', 'archived'];
const KB_COLUMNS = ['prospecting', 'contacted', 'interested', 'waitlisted', 'committed'];
const KB_META = {
  prospecting: { label: 'Prospecting', color: 'var(--c-cyan)' },
  contacted:   { label: 'Contacted',   color: 'var(--c-violet)' },
  interested:  { label: 'Interested',  color: 'var(--c-amber)' },
  waitlisted:  { label: 'Waitlisted',  color: 'var(--c-orange)' },
  committed:   { label: 'Committed',   color: 'var(--c-green)' },
};

function CampaignView({ businesses, campaign, mayCampaign, onOpen, update, toast }) {
  const [campId, setCampId] = React.useState(campaign.id);
  const isArchived = campId === mayCampaign.id;

  return (
    <div className="view-pad" data-screen-label="Campaign">
      <div className="camp-head">
        <select className="camp-select" value={campId} onChange={(e) => setCampId(e.target.value)}>
          <option value={campaign.id}>{campaign.name} — filling</option>
          <option value={mayCampaign.id}>{mayCampaign.name} — archived</option>
        </select>
        <div className="camp-lifecycle">
          {LIFECYCLE.map((s) => (
            <span key={s} className={'stage' + ((isArchived ? 'archived' : campaign.status) === s ? ' current' : '')}>{s}</span>
          ))}
        </div>
      </div>
      {isArchived
        ? <ArchivedCampaign may={mayCampaign} onOpen={onOpen} />
        : <LiveCampaign businesses={businesses} campaign={campaign} onOpen={onOpen} update={update} toast={toast} />}
    </div>
  );
}

// ---------- live (June) ----------
function LiveCampaign({ businesses, campaign, onOpen, update, toast }) {
  const attached = businesses.filter((b) => b.participation && b.participation.status !== 'declined');
  const declined = businesses.filter((b) => b.participation && b.participation.status === 'declined');
  const committed = attached.filter((b) => ['committed', 'paid'].includes(b.participation.status));
  const committedCents = committed.reduce((s, b) => s + (b.participation.committedAmountCents || 0), 0);
  const collectedCents = committed.filter((b) => b.participation.paymentStatus === 'paid').reduce((s, b) => s + (b.participation.committedAmountCents || 0), 0);
  const waitlisted = attached.filter((b) => b.participation.status === 'waitlisted');
  const days = daysUntil(campaign.deadline);

  const stats = [
    { label: 'Slots filled', value: committed.length + ' of ' + campaign.totalSlots, sub: (campaign.totalSlots - committed.length) + ' remaining · mirror this urgency' },
    { label: 'Committed', value: money(committedCents), sub: 'asking ' + money(campaign.slotPriceCents) + '/slot' },
    { label: 'Collected', value: money(collectedCents), sub: money(committedCents - collectedCents) + ' outstanding' },
    { label: 'Waitlisted', value: String(waitlisted.length), sub: 'preserved revenue' },
    { label: 'Deadline', value: days + ' days', sub: 'closes ' + shortDate(campaign.deadline) },
  ];

  return (
    <div>
      <div className="summary-strip" data-screen-label="Campaign summary">
        {stats.map((s, i) => (
          <div key={i} className="stat">
            <div className="stat-label">{s.label}</div>
            <div className="stat-value">{s.value}</div>
            <div className="stat-sub">{s.sub}</div>
          </div>
        ))}
      </div>

      <section>
        <h2 className="sec-label">Category slots — one business per industry</h2>
        <SlotTable businesses={businesses} campaign={campaign} onOpen={onOpen} update={update} toast={toast} />
      </section>

      <section style={{ marginTop: '22px' }}>
        <h2 className="sec-label">Outreach pipeline — this campaign</h2>
        <div className="kb" data-screen-label="Campaign kanban">
          {KB_COLUMNS.map((col) => {
            const cards = attached.filter((b) => col === 'committed'
              ? ['committed', 'paid'].includes(b.participation.status)
              : b.participation.status === col);
            return (
              <div key={col} className="kb-col">
                <div className="kb-head"><span className="status-dot" style={{ background: KB_META[col].color }}></span>{KB_META[col].label}<span className="kb-count">{cards.length}</span></div>
                <div className="kb-cards">
                  {cards.map((b) => <LeadCard key={b.id} biz={b} campaign={campaign} onOpen={onOpen} />)}
                  {cards.length === 0 && <div className="kb-empty">Empty</div>}
                </div>
              </div>
            );
          })}
          {declined.length > 0 && (
            <div className="kb-col">
              <div className="kb-head"><span className="status-dot" style={{ background: 'var(--c-red)' }}></span>Declined<span className="kb-count">{declined.length}</span></div>
              <div className="kb-cards">
                {declined.map((b) => (
                  <button key={b.id} className="lead-card closed-card" onClick={() => onOpen(b.id)}>
                    <div className="lead-top"><span className="lead-name">{b.name}</span></div>
                    <div className="lead-tags"><CategoryTag category={b.category} /><Pill tone="pill-red">declined</Pill></div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>

      <PostcardPreview businesses={businesses} campaign={campaign} toast={toast} />
    </div>
  );
}

function SlotTable({ businesses, campaign, onOpen, update, toast }) {
  const settings = window.POSTCARD_SEED.SETTINGS;

  const move = (rows, idx, dir) => {
    const a = rows[idx], b = rows[idx + dir];
    if (!b) return;
    update(a.id, (x) => { x.participation.waitlistOrder = idx + dir + 1; });
    update(b.id, (x) => { x.participation.waitlistOrder = idx + 1; });
    toast('Waitlist reordered');
  };

  return (
    <div className="lt-wrap" data-screen-label="Slot table">
      <table className="lt slot-lt">
        <thead>
          <tr>
            <th>Category</th><th>Business</th><th>Status</th><th>Amount</th><th>Payment</th><th>Fulfillment</th><th>Waitlist</th>
          </tr>
        </thead>
        <tbody>
          {settings.categories.map((cat) => {
            const winner = businesses.find((b) => b.category === cat && b.participation && ['committed', 'paid'].includes(b.participation.status));
            const pitched = businesses.filter((b) => b.category === cat && b.participation && ['prospecting', 'contacted', 'interested'].includes(b.participation.status));
            const wl = businesses
              .filter((b) => b.category === cat && b.participation && b.participation.status === 'waitlisted')
              .sort((a, b) => a.participation.waitlistOrder - b.participation.waitlistOrder);
            const f = winner && winner.participation.fulfillment;
            const done = f ? ['logo_received', 'offer_confirmed', 'artwork_approved'].filter((k) => f[k]).length : 0;
            return (
              <tr key={cat} className={winner ? '' : 'slot-open-row'}>
                <td><span className="lt-name"><CategoryTag category={cat} />{winner && <span className="dim num">slot {winner.participation.slot}</span>}</span></td>
                <td>
                  {winner
                    ? <a className="link slot-biz" onClick={() => onOpen(winner.id)}>{winner.name}</a>
                    : pitched.length > 0
                      ? <span className="slot-pitched">{pitched.map((b) => <a key={b.id} className="link" onClick={() => onOpen(b.id)}>{b.name}</a>)}</span>
                      : <span className="dim">—</span>}
                </td>
                <td>
                  {winner
                    ? <Pill tone="pill-green">committed{winner.participation.status === 'paid' ? ' · paid' : ''}</Pill>
                    : pitched.length > 0
                      ? <Pill>{pitched.length} active pitch{pitched.length > 1 ? 'es' : ''}</Pill>
                      : <Pill tone="pill-subtle">open</Pill>}
                </td>
                <td className="num">{winner
                  ? <span className="committed-price">{money(winner.participation.committedAmountCents)}{winner.participation.committedAmountCents !== winner.participation.askingPriceCents ? ' (neg.)' : ''}</span>
                  : <span className="dim">{money(campaign.slotPriceCents)} asking</span>}</td>
                <td>{winner ? (winner.participation.paymentStatus === 'paid' ? <Pill tone="pill-green">paid</Pill> : <Pill>unpaid</Pill>) : <span className="dim">—</span>}</td>
                <td>{winner
                  ? <span className="ft-mini" title={done + ' of 3 — logo, offer, artwork'}><span className="ft-mini-bar"><span className="ft-mini-fill" style={{ width: (done / 3 * 100) + '%' }}></span></span><span className="num dim">{done}/3</span></span>
                  : <span className="dim">—</span>}</td>
                <td>
                  {wl.length === 0 ? <span className="dim">—</span> : (
                    <div className="wl-cell">
                      {wl.map((b, i) => (
                        <span key={b.id} className="wl-cell-row">
                          <span className="wl-pos">#{b.participation.waitlistOrder}</span>
                          <a className="link" onClick={() => onOpen(b.id)}>{b.name}</a>
                          <span className="wl-actions">
                            <button className="wl-btn" disabled={i === 0} title="Move up" onClick={() => move(wl, i, -1)}>↑</button>
                            <button className="wl-btn" disabled={i === wl.length - 1} title="Move down" onClick={() => move(wl, i, 1)}>↓</button>
                            <button className="wl-btn wl-promote" disabled={!!winner}
                              title={winner ? 'Enabled when the ' + cat + ' slot frees up. Requires a committed amount.' : 'Promote — requires committed amount'}
                              onClick={() => toast('Promotion runs the exclusivity check and requires a committed amount.')}>Promote</button>
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

function SlotBoard({ businesses, campaign, onOpen }) {
  const settings = window.POSTCARD_SEED.SETTINGS;
  return (
    <div className="slot-grid" data-screen-label="Slot board">
      {settings.categories.map((cat) => {
        const inCat = businesses.filter((b) => b.participation && b.participation.category !== undefined ? b.category === cat && b.participation : false);
        const winner = businesses.find((b) => b.category === cat && b.participation && ['committed', 'paid'].includes(b.participation.status));
        const pitched = businesses.filter((b) => b.category === cat && b.participation && ['prospecting', 'contacted', 'interested'].includes(b.participation.status));
        const wl = businesses.filter((b) => b.category === cat && b.participation && b.participation.status === 'waitlisted');
        if (winner) {
          const f = winner.participation.fulfillment;
          const done = ['logo_received', 'offer_confirmed', 'artwork_approved'].filter((k) => f[k]).length;
          return (
            <button key={cat} className="slot-tile filled lead-card" onClick={() => onOpen(winner.id)} style={{ cursor: 'pointer' }}>
              <span className="slot-cat"><StatusDot status="committed" />{cat}<span className="slot-num">slot {winner.participation.slot}</span></span>
              <span className="slot-name">{winner.name}</span>
              <span className="slot-detail">
                <span className="committed-price lead-price" style={{ marginLeft: 0 }}>{money(winner.participation.committedAmountCents)}</span>
                {winner.participation.paymentStatus === 'paid' ? <Pill tone="pill-green">paid</Pill> : <Pill>unpaid</Pill>}
                <span className="meta-dim">{done}/3 fulfillment</span>
                {wl.length > 0 && <Pill tone="pill-orange">{wl.length} waitlisted</Pill>}
              </span>
              <span className="slot-mini-bar"><span className="slot-mini-fill" style={{ width: (done / 3 * 100) + '%', display: 'block' }}></span></span>
            </button>
          );
        }
        return (
          <div key={cat} className="slot-tile">
            <span className="slot-cat"><StatusDot status={pitched.length ? 'contacted' : 'staged'} />{cat}</span>
            {pitched.length > 0
              ? <span className="slot-detail">{pitched.map((b) => (
                  <a key={b.id} className="link" style={{ cursor: 'pointer' }} onClick={() => onOpen(b.id)}>{b.name}</a>
                ))}</span>
              : <span className="slot-empty-label">Open — no active pitches</span>}
            <span className="slot-detail meta-dim" style={{ marginTop: 'auto' }}>{pitched.length ? pitched.length + ' active pitch' + (pitched.length > 1 ? 'es' : '') : money(campaign.slotPriceCents) + ' asking'}</span>
          </div>
        );
      })}
    </div>
  );
}

function WaitlistPanel({ businesses, onOpen, update, toast }) {
  const settings = window.POSTCARD_SEED.SETTINGS;
  const groups = settings.categories.map((cat) => ({
    cat,
    occupied: businesses.some((b) => b.category === cat && b.participation && ['committed', 'paid'].includes(b.participation.status)),
    rows: businesses
      .filter((b) => b.category === cat && b.participation && b.participation.status === 'waitlisted')
      .sort((a, b) => a.participation.waitlistOrder - b.participation.waitlistOrder),
  })).filter((g) => g.rows.length > 0);

  const move = (cat, idx, dir) => {
    const g = groups.find((x) => x.cat === cat);
    const a = g.rows[idx], b = g.rows[idx + dir];
    if (!b) return;
    update(a.id, (x) => { x.participation.waitlistOrder = idx + dir + 1; });
    update(b.id, (x) => { x.participation.waitlistOrder = idx + 1; });
    toast('Waitlist reordered');
  };

  if (groups.length === 0) return <div className="wl-panel wl-empty">No one waitlisted yet. When a category fills, extra interest lands here instead of being declined.</div>;

  return (
    <div className="wl-panel" data-screen-label="Waitlist panel">
      {groups.map((g) => (
        <div key={g.cat} className="wl-group">
          <div className="wl-cat">{g.cat}<span className="wl-state meta-dim">{g.occupied ? 'slot occupied' : 'slot free'}</span></div>
          {g.rows.map((b, i) => (
            <div key={b.id} className="wl-row">
              <span className="wl-pos">#{b.participation.waitlistOrder}</span>
              <a className="wl-name link" style={{ cursor: 'pointer', borderBottom: 'none' }} onClick={() => onOpen(b.id)}>{b.name}</a>
              <div className="wl-actions">
                <button className="wl-btn" disabled={i === 0} title="Move up" onClick={() => move(g.cat, i, -1)}>↑</button>
                <button className="wl-btn" disabled={i === g.rows.length - 1} title="Move down" onClick={() => move(g.cat, i, 1)}>↓</button>
                <button className="wl-btn" style={{ width: 'auto', padding: '0 8px', fontWeight: 600 }} disabled={g.occupied}
                  title={g.occupied ? 'Enabled when the ' + g.cat + ' slot frees up (cancellation or decline). Requires a committed amount.' : 'Promote — requires committed amount'}
                  onClick={() => toast('Promotion runs the exclusivity check and requires a committed amount.')}>Promote</button>
              </div>
            </div>
          ))}
        </div>
      ))}
      <p className="set-note" style={{ marginTop: '10px' }}>Next-in-line is the default; you keep final say. Waitlists carry forward as priority prospects for the next campaign.</p>
    </div>
  );
}

// ---------- archived (May) ----------
function ArchivedCampaign({ may, onOpen }) {
  const paid = may.participants.filter((p) => p.status === 'paid');
  const collected = paid.reduce((s, p) => s + p.amountCents, 0);
  const stats = [
    { label: 'Slots filled', value: paid.length + ' of ' + may.totalSlots, sub: 'electrician, hvac, landscaper went unfilled' },
    { label: 'Committed', value: money(collected), sub: 'all commitments collected' },
    { label: 'Collected', value: money(collected), sub: '$0 outstanding' },
    { label: 'Waitlisted', value: String(may.participants.filter((p) => p.status === 'waitlisted').length), sub: 'carried into June as priority' },
    { label: 'Closed', value: shortDate(may.deadline), sub: 'archived, never deleted' },
  ];
  return (
    <div data-screen-label="Archived campaign">
      <div className="archived-banner"><strong>Archived.</strong> Read-only history — participants and waitlist below surfaced as priority prospects when June was composed.</div>
      <div className="summary-strip">
        {stats.map((s, i) => (
          <div key={i} className="stat">
            <div className="stat-label">{s.label}</div>
            <div className="stat-value">{s.value}</div>
            <div className="stat-sub">{s.sub}</div>
          </div>
        ))}
      </div>
      <h2 className="sec-label">Participants</h2>
      <div className="lt-wrap" style={{ maxWidth: '880px' }}>
        <table className="lt" style={{ minWidth: '640px' }}>
          <thead><tr><th>Business</th><th>Category</th><th>Outcome</th><th>Amount</th><th>Method</th><th>Slot</th></tr></thead>
          <tbody>
            {may.participants.map((p) => (
              <tr key={p.businessId + p.category} onClick={() => onOpen(p.businessId)}>
                <td><span className="lt-name">{p.name}</span></td>
                <td><CategoryTag category={p.category} /></td>
                <td>
                  {p.status === 'paid' && <Pill tone="pill-green">paid</Pill>}
                  {p.status === 'waitlisted' && <Pill tone="pill-orange">waitlisted #{p.waitlistOrder} → carried to June</Pill>}
                  {p.status === 'declined' && <Pill tone="pill-red">declined</Pill>}
                </td>
                <td className="num">{p.amountCents ? money(p.amountCents) : '—'}</td>
                <td className="dim">{p.method || '—'}</td>
                <td className="num dim">{p.slot || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---------- postcard preview ----------
const PC_COPY = {
  'b-tippecanoe': { headline: 'Storm season is coming', offer: 'Free roof inspection — before the hail does it for you', contact: '(765) 555-0142' },
  'b-wabash': { headline: 'Beat the June heat', offer: 'Free estimate on AC replacement + same-day service', contact: '(765) 555-0177' },
  'b-redbrick': { headline: 'Best Patio 2025', offer: '10% off lunch, all June', contact: 'redbrickbistro.com' },
};

function PostcardPreview({ businesses, campaign, toast }) {
  const [selected, setSelected] = React.useState(null);
  const [comments, setComments] = React.useState([
    { slot: 1, author: 'grant', body: 'Make the inspection offer bigger — it\u2019s the whole pitch.', ts: new Date(Date.now() - 5 * 3600e3).toISOString(), resolved: false },
  ]);
  const [text, setText] = React.useState('');

  const committed = businesses.filter((b) => b.participation && ['committed', 'paid'].includes(b.participation.status));
  const settings = window.POSTCARD_SEED.SETTINGS;
  const usedCats = committed.map((b) => b.category);
  const openCats = settings.categories.filter((c) => !usedCats.includes(c));

  // slots 1..8: committed businesses by slot number, then open categories
  const slots = Array.from({ length: 8 }, (_, i) => {
    const n = i + 1;
    const biz = committed.find((b) => b.participation.slot === n);
    if (biz) return { n, biz };
    return { n, cat: openCats[(n - committed.length - 1 + committed.length) % openCats.length] };
  });
  // assign open categories deterministically to empty slots
  let openIdx = 0;
  slots.forEach((s) => { if (!s.biz) { s.cat = openCats[openIdx++] || '—'; } });

  const slotComments = comments.filter((c) => c.slot === selected);
  const addComment = () => {
    if (!text.trim() || !selected) return;
    setComments((cs) => [...cs, { slot: selected, author: 'grant', body: text.trim(), ts: new Date().toISOString(), resolved: false }]);
    setText('');
    toast('Comment anchored to slot ' + selected);
  };

  return (
    <section className="pc-section" data-screen-label="Postcard preview">
      <h2 className="sec-label">Postcard preview</h2>
      <div className="pc-frame-wrap">
        <div className="pc-card">
          <div className="pc-header">Lafayette Local Business Spotlight<span className="pc-month">JUNE 2026 · grid-4x2-v1</span></div>
          <div className="pc-grid">
            {slots.map((s) => s.biz ? (
              <button key={s.n} className={'pc-slot' + (selected === s.n ? ' selected' : '')} onClick={() => setSelected(selected === s.n ? null : s.n)}>
                <span className="pcs-biz">{s.biz.name}</span>
                <span className="pcs-headline">{PC_COPY[s.biz.id]?.headline || '—'}</span>
                <span className="pcs-offer">{PC_COPY[s.biz.id]?.offer || ''}</span>
                <span className="pcs-contact">{PC_COPY[s.biz.id]?.contact || ''}</span>
                {comments.some((c) => c.slot === s.n && !c.resolved) && <span className="pcs-comment-dot" title="Unresolved comment"></span>}
              </button>
            ) : (
              <button key={s.n} className={'pc-slot empty' + (selected === s.n ? ' selected' : '')} onClick={() => setSelected(selected === s.n ? null : s.n)}>
                <span className="pcs-cat">{s.cat}</span>
                <span className="pcs-open">slot {s.n} · open</span>
              </button>
            ))}
          </div>
        </div>
        <div className="pc-side">
          <div className="pc-meta-row">
            <span>Draft</span>
            <select defaultValue="v1"><option value="v1">v1 — current</option></select>
            <span className="meta-dim">· empty slots print as labeled placeholders</span>
          </div>
          <div className="pc-comments">
            {selected == null && <p className="pc-comments-empty">Click a slot to read or leave feedback anchored to it — “make the plumber’s offer bigger” goes on the plumber’s slot.</p>}
            {selected != null && (
              <div>
                <div className="dsec-label">Slot {selected} comments</div>
                {slotComments.length === 0 && <p className="pc-comments-empty">No comments on this slot yet.</p>}
                <div className="comment-list">
                  {slotComments.map((c, i) => (
                    <div key={i} className={'comment' + (c.resolved ? ' resolved' : '')}>
                      <div className="comment-head">
                        <span className="comment-author">{c.author === 'grant' ? 'Grant' : 'Agent'}</span>
                        <span className="meta-dim">{timeAgo(c.ts)}</span>
                        <button className="resolve-btn" onClick={() => setComments((cs) => cs.map((x) => x === c ? { ...x, resolved: !x.resolved } : x))}>{c.resolved ? 'Resolved ✓' : 'Resolve'}</button>
                      </div>
                      <p className="comment-body">{c.body}</p>
                    </div>
                  ))}
                </div>
                <div className="comment-input">
                  <textarea rows={2} placeholder={'Comment on slot ' + selected + '…'} value={text} onChange={(e) => setText(e.target.value)}></textarea>
                  <Btn small kind="btn-primary" onClick={addComment} disabled={!text.trim()}>Comment</Btn>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

Object.assign(window, { CampaignView });
