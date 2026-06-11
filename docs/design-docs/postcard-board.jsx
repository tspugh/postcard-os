// Summary strip, pipeline board, staging modal, activity feed
function SummaryStrip({ businesses, campaign, onFilter }) {
  const parts = businesses.filter((b) => b.participation).map((b) => b.participation);
  const committed = parts.filter((p) => p.status === 'committed' || p.status === 'paid');
  const committedCents = committed.reduce((s, p) => s + (p.committedAmountCents || 0), 0);
  const collectedCents = committed.filter((p) => p.paymentStatus === 'paid').reduce((s, p) => s + (p.committedAmountCents || 0), 0);
  const drafts = parts.reduce((s, p) => s + p.emails.filter((e) => e.status === 'in_review').length, 0);
  const waitlist = parts.filter((p) => p.status === 'waitlisted').length;
  const unviewed = businesses.filter((b) => !b.viewedAt && b.status !== 'disqualified').length;
  const days = daysUntil(campaign.deadline);

  const stats = [
    { k: 'slots', label: 'Slots filled', value: committed.length + ' of ' + campaign.totalSlots, sub: (campaign.totalSlots - committed.length) + ' remaining', accent: committed.length >= campaign.totalSlots },
    { k: 'committed', label: 'Committed', value: money(committedCents), sub: money(collectedCents) + ' collected' },
    { k: 'drafts', label: 'Drafts to review', value: String(drafts), sub: drafts ? 'awaiting your approval' : 'all clear', hot: drafts > 0 },
    { k: 'waitlist', label: 'Waitlisted', value: String(waitlist), sub: 'preserved revenue' },
    { k: 'unviewed', label: 'Unviewed leads', value: String(unviewed), sub: unviewed ? 'new from the agent' : 'all seen', hot: unviewed > 0 },
    { k: 'deadline', label: 'Deadline', value: days + ' days', sub: 'closes ' + shortDate(campaign.deadline) },
  ];

  return (
    <div className="summary-strip" data-screen-label="Summary strip">
      {stats.map((s) => (
        <div key={s.k} className={'stat' + (s.hot ? ' stat-hot' : '')}>
          <div className="stat-label">{s.label}</div>
          <div className="stat-value">{s.value}</div>
          <div className="stat-sub">{s.sub}</div>
        </div>
      ))}
    </div>
  );
}

// ---------- lead card ----------
function LeadCard({ biz, campaign, onOpen }) {
  const p = biz.participation;
  const unviewed = !biz.viewedAt;
  const draftsInReview = p ? p.emails.filter((e) => e.status === 'in_review').length : 0;
  const f = p && p.fulfillment;
  const fulfillDone = f ? ['logo_received', 'offer_confirmed', 'artwork_approved'].filter((k) => f[k]).length : 0;
  const isCommitted = p && (p.status === 'committed' || p.status === 'paid');

  return (
    <button className={'lead-card' + (unviewed ? ' unviewed' : '')} onClick={() => onOpen(biz.id)}>
      <div className="lead-top">
        <span className="lead-name">{biz.name}</span>
        {unviewed && <span className="unviewed-dot" title="Not yet viewed"></span>}
      </div>
      <div className="lead-tags">
        <CategoryTag category={biz.category} />
        {p && p.status === 'waitlisted' && <Pill tone="pill-orange">#{p.waitlistOrder} waitlist</Pill>}
        {p && p.status === 'paid' && <Pill tone="pill-green">paid</Pill>}
        {draftsInReview > 0 && <Pill tone="pill-review">{draftsInReview} draft to review</Pill>}
      </div>
      <div className="lead-foot">
        <span>{timeAgo(biz.createdAt)}</span>
        {p && !isCommitted && <span className="lead-price">{money(p.askingPriceCents)} asking</span>}
        {isCommitted && <span className="lead-price committed-price">{money(p.committedAmountCents)}{p.committedAmountCents !== p.askingPriceCents ? ' (neg.)' : ''}</span>}
        {isCommitted && <span className="mini-checklist" title={'Fulfillment ' + fulfillDone + '/3'}>{fulfillDone}/3 ✓</span>}
      </div>
    </button>
  );
}

// ---------- board ----------
function Board({ businesses, campaign, onOpen }) {
  const [showClosed, setShowClosed] = React.useState(false);
  const byCol = {};
  BOARD_COLUMNS.forEach((c) => { byCol[c] = []; });
  const closed = [];
  businesses.forEach((b) => {
    const col = columnOf(b);
    if (col === 'disqualified' || col === 'declined') closed.push(b);
    else byCol[col].push(b);
  });
  Object.values(byCol).forEach((arr) => arr.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt)));

  return (
    <div className="board-wrap">
      <div className="board" data-screen-label="Pipeline board">
        {BOARD_COLUMNS.map((col) => (
          <div key={col} className="col">
            <div className="col-head">
              <StatusDot status={col} />
              <span className="col-title">{STATUS_META[col].label}</span>
              <span className="col-count">{byCol[col].length}</span>
            </div>
            <div className="col-cards">
              {byCol[col].map((b) => <LeadCard key={b.id} biz={b} campaign={campaign} onOpen={onOpen} />)}
              {byCol[col].length === 0 && <div className="col-empty">Empty</div>}
            </div>
          </div>
        ))}
        <div className={'col col-closed' + (showClosed ? ' open' : '')}>
          <button className="col-head col-head-btn" onClick={() => setShowClosed(!showClosed)}>
            <IconChevron open={showClosed} />
            <span className="col-title">Closed</span>
            <span className="col-count">{closed.length}</span>
          </button>
          {showClosed && (
            <div className="col-cards">
              {closed.map((b) => (
                <button key={b.id} className="lead-card closed-card" onClick={() => onOpen(b.id)}>
                  <div className="lead-top"><span className="lead-name">{b.name}</span></div>
                  <div className="lead-tags">
                    <CategoryTag category={b.category} />
                    <Pill tone="pill-red">{b.dq ? b.dq.code : 'declined'}</Pill>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------- staging modal ----------
function StagingModal({ settings, businesses, onClose, onStage, toast }) {
  const [text, setText] = React.useState('');
  const [results, setResults] = React.useState(null);

  const parse = () => {
    const lines = text.split('\n').map((l) => l.trim()).filter(Boolean);
    const ok = [], errors = [];
    const existing = new Set(businesses.map((b) => b.name.toLowerCase().replace(/[^a-z0-9]/g, '')));
    lines.forEach((line, i) => {
      const parts = line.split(',').map((s) => s.trim());
      const [name, category, website] = parts;
      if (!name || !category || !website) {
        errors.push({ line: i + 1, msg: 'Staging bar: every lead needs name, category, and website — got "' + line + '"' });
        return;
      }
      if (!settings.categories.includes(category.toLowerCase())) {
        errors.push({ line: i + 1, msg: '"' + category + '" is not in the category vocabulary (' + settings.categories.join(', ') + ')' });
        return;
      }
      if (!/^https?:\/\/.+\..+/.test(website)) {
        errors.push({ line: i + 1, msg: 'Website "' + website + '" doesn\u2019t look like a working URL — the URL is the proof-of-existence test' });
        return;
      }
      const norm = name.toLowerCase().replace(/[^a-z0-9]/g, '');
      if (existing.has(norm)) {
        errors.push({ line: i + 1, msg: '"' + name + '" duplicates an existing record — never auto-merged' });
        return;
      }
      existing.add(norm);
      ok.push({ name, category: category.toLowerCase(), website });
    });
    setResults({ ok, errors });
    if (ok.length && errors.length === 0) {
      onStage(ok);
      toast('Staged ' + ok.length + ' lead' + (ok.length === 1 ? '' : 's'));
      onClose();
    } else if (ok.length) {
      onStage(ok);
    }
  };

  return (
    <div className="drawer-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal" data-screen-label="Stage leads">
        <h3 className="modal-title">Stage leads</h3>
        <p className="modal-sub">One per line: <code>name, category, website</code>. The staging bar is enforced — name + category + working website URL.</p>
        <textarea rows={6} placeholder={'Lafayette Tire & Lube, auto repair, https://laftirelube.com\nHarrison Homes Realty, realtor, https://harrisonhomes.com'}
          value={text} onChange={(e) => setText(e.target.value)} autoFocus></textarea>
        {results && results.errors.length > 0 && (
          <div className="stage-errors">
            {results.ok.length > 0 && <div className="stage-ok">✓ {results.ok.length} staged</div>}
            {results.errors.map((e, i) => <div key={i} className="stage-err">Line {e.line}: {e.msg}</div>)}
          </div>
        )}
        <div className="modal-actions">
          <Btn kind="btn-primary" onClick={parse} disabled={!text.trim()}>Stage</Btn>
          <Btn onClick={onClose}>Cancel</Btn>
        </div>
      </div>
    </div>
  );
}

// ---------- activity feed ----------
function ActivityFeed({ activity, open, onToggle }) {
  return (
    <div className={'activity' + (open ? ' open' : '')} data-screen-label="Agent activity feed">
      <button className="activity-toggle" onClick={onToggle}>
        <span className="activity-pulse"></span>
        Agent activity
        <span className="meta-dim">last run {timeAgo(activity[0].ts)}</span>
        <span className="activity-chevron"><IconChevron open={open} /></span>
      </button>
      {open && (
        <ul className="activity-list">
          {activity.map((a) => (
            <li key={a.id} className="activity-row">
              <span className={'activity-outcome ' + a.outcome} title={a.outcome}></span>
              <code className="activity-tool">{a.tool.replace('postcard_', '')}</code>
              <span className="activity-detail">{a.detail}</span>
              <span className="meta-dim activity-ts">{timeAgo(a.ts)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

Object.assign(window, { SummaryStrip, Board, StagingModal, ActivityFeed, LeadCard });
