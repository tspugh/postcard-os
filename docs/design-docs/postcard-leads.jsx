// Leads view — table of all businesses (campaign-independent), by-contact toggle, structured add-leads
function LeadsView({ businesses, campaign, onOpen, onAdd, settings }) {
  const [mode, setMode] = React.useState('businesses'); // businesses | contacts
  const [q, setQ] = React.useState('');
  const [cat, setCat] = React.useState('all');
  const [stage, setStage] = React.useState('all');
  const [sort, setSort] = React.useState({ key: 'added', dir: -1 });
  const [adding, setAdding] = React.useState(false);

  const stages = ['staged', 'researching', 'researched', 'contacted', 'interested', 'waitlisted', 'committed', 'declined', 'disqualified'];

  const filtered = businesses.filter((b) => {
    const col = columnOf(b);
    if (cat !== 'all' && b.category !== cat) return false;
    if (stage !== 'all' && col !== stage) return false;
    if (q) {
      const hay = (b.name + ' ' + b.contacts.map((c) => (c.name || '') + ' ' + (c.email || '')).join(' ')).toLowerCase();
      if (!hay.includes(q.toLowerCase())) return false;
    }
    return true;
  });

  const sorted = [...filtered].sort((a, b) => {
    if (sort.key === 'name') return a.name.localeCompare(b.name) * sort.dir;
    if (sort.key === 'category') return a.category.localeCompare(b.category) * sort.dir;
    return (new Date(a.createdAt) - new Date(b.createdAt)) * sort.dir;
  });

  const toggleSort = (key) => setSort((s) => s.key === key ? { key, dir: -s.dir } : { key, dir: key === 'added' ? -1 : 1 });
  const arrow = (key) => sort.key === key ? (sort.dir > 0 ? ' ↑' : ' ↓') : '';

  const totalContacts = businesses.reduce((s, b) => s + b.contacts.length, 0);

  return (
    <div className="view-pad" data-screen-label="Leads">
      <div className="view-head">
        <h1 className="view-title">Leads</h1>
        <span className="view-sub">{businesses.length} businesses · {totalContacts} contacts · independent of any campaign</span>
        <div className="topbar-spacer"></div>
        <div className="seg">
          <button className={mode === 'businesses' ? 'active' : ''} onClick={() => setMode('businesses')}>By business</button>
          <button className={mode === 'contacts' ? 'active' : ''} onClick={() => setMode('contacts')}>By contact</button>
        </div>
        <Btn kind="btn-primary" onClick={() => setAdding(true)}>+ Add leads</Btn>
      </div>

      <div className="view-head filter-bar">
        <input type="search" placeholder="Search businesses or contacts…" value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={cat} onChange={(e) => setCat(e.target.value)}>
          <option value="all">All categories</option>
          {settings.categories.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <select value={stage} onChange={(e) => setStage(e.target.value)}>
          <option value="all">All stages</option>
          {stages.map((s) => <option key={s} value={s}>{STATUS_META[s].label}</option>)}
        </select>
        {(q || cat !== 'all' || stage !== 'all') && <Btn small onClick={() => { setQ(''); setCat('all'); setStage('all'); }}>Clear</Btn>}
      </div>

      {mode === 'businesses' ? (
        <BusinessTable rows={sorted} campaign={campaign} onOpen={onOpen} toggleSort={toggleSort} arrow={arrow} />
      ) : (
        <ContactTable businesses={sorted} onOpen={onOpen} />
      )}

      {adding && <AddLeadsModal settings={settings} businesses={businesses} onClose={() => setAdding(false)} onAdd={onAdd} />}
    </div>
  );
}

function BusinessTable({ rows, campaign, onOpen, toggleSort, arrow }) {
  return (
    <div className="lt-wrap">
      <table className="lt">
        <thead>
          <tr>
            <th className="sortable" onClick={() => toggleSort('name')}>Business{arrow('name')}</th>
            <th className="sortable" onClick={() => toggleSort('category')}>Category{arrow('category')}</th>
            <th>Stage</th>
            <th>Primary contact</th>
            <th>Email</th>
            <th>Phone</th>
            <th>Campaign</th>
            <th>Price</th>
            <th className="sortable" onClick={() => toggleSort('added')}>Added{arrow('added')}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((b) => {
            const col = columnOf(b);
            const p = b.participation;
            const primary = b.contacts.find((c) => c.isPrimary) || b.contacts[0];
            const isCommitted = p && (p.status === 'committed' || p.status === 'paid');
            const closed = col === 'disqualified' || col === 'declined';
            return (
              <tr key={b.id} className={closed ? 'row-closed' : ''} onClick={() => onOpen(b.id)}>
                <td><span className="lt-name">{!b.viewedAt && <span className="unviewed-dot" title="Not yet viewed"></span>}{b.name}</span></td>
                <td><CategoryTag category={b.category} /></td>
                <td><Pill tone="pill-status"><StatusDot status={col} />{STATUS_META[col].label}{p && p.status === 'paid' ? ' · Paid' : ''}</Pill></td>
                <td>{primary ? <span className="lt-contact"><span>{primary.name}</span><span className="sub">{primary.title}</span></span> : <span className="dim">—</span>}</td>
                <td>{primary && primary.email ? <span>{primary.email} <span className="confidence" title={'Source: ' + (primary.emailSource || 'unknown')}>{primary.emailConfidence}</span></span> : <span className="dim">—</span>}</td>
                <td className="num">{primary && primary.phone ? primary.phone : <span className="dim">—</span>}</td>
                <td>{p ? <span className="dim">{campaign.month}{p.status === 'waitlisted' ? ' · WL #' + p.waitlistOrder : ''}{p.slot ? ' · slot ' + p.slot : ''}</span> : <span className="dim">—</span>}</td>
                <td className="num">{p ? (isCommitted ? <span className="committed-price">{money(p.committedAmountCents)}</span> : money(p.askingPriceCents) + ' ask') : <span className="dim">—</span>}</td>
                <td className="dim num">{timeAgo(b.createdAt)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="lt-foot">{rows.length} of shown rows · click any row for research, contacts, emails &amp; comments</div>
    </div>
  );
}

function ContactTable({ businesses, onOpen }) {
  const rows = [];
  businesses.forEach((b) => {
    b.contacts.forEach((c) => rows.push({ c, b }));
  });
  return (
    <div className="lt-wrap">
      <table className="lt">
        <thead>
          <tr>
            <th>Contact</th><th>Title</th><th>Email</th><th>Phone</th><th>Business</th><th>Category</th><th>Stage</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ c, b }) => {
            const col = columnOf(b);
            return (
              <tr key={c.id} onClick={() => onOpen(b.id)}>
                <td><span className="lt-name">{c.name || '—'}{c.isPrimary && <Pill tone="pill-subtle">primary</Pill>}</span></td>
                <td className="dim">{c.title || '—'}</td>
                <td>{c.email ? <span>{c.email} <span className="confidence" title={'Source: ' + (c.emailSource || 'unknown')}>{c.emailConfidence}</span></span> : <span className="dim">—</span>}</td>
                <td className="num">{c.phone || <span className="dim">—</span>}</td>
                <td>{b.name}</td>
                <td><CategoryTag category={b.category} /></td>
                <td><Pill tone="pill-status"><StatusDot status={col} />{STATUS_META[col].label}</Pill></td>
              </tr>
            );
          })}
          {rows.length === 0 && <tr><td colSpan="7" className="dim" style={{ textAlign: 'center', padding: '20px' }}>No contacts match the current filters.</td></tr>}
        </tbody>
      </table>
      <div className="lt-foot">{rows.length} contacts · contacts belong to businesses, not campaigns — they carry forward month to month</div>
    </div>
  );
}

// Structured row-based lead entry (replaces the paste-a-string box)
function AddLeadsModal({ settings, businesses, onClose, onAdd }) {
  const blankRow = () => ({ key: Math.random().toString(36).slice(2), name: '', category: settings.categories[0], website: '', err: null });
  const [rows, setRows] = React.useState([blankRow()]);

  const setRow = (key, field, val) => setRows((rs) => rs.map((r) => r.key === key ? { ...r, [field]: val, err: null } : r));

  const submit = () => {
    const existing = new Set(businesses.map((b) => b.name.toLowerCase().replace(/[^a-z0-9]/g, '')));
    let anyErr = false;
    const checked = rows.filter((r) => r.name || r.website).map((r) => {
      let err = null;
      if (!r.name.trim() || !r.website.trim()) err = 'Staging bar: name, category, and website are all required.';
      else if (!/^https?:\/\/.+\..+/.test(r.website.trim())) err = 'Website must be a working URL (https://…) — it\u2019s the proof-of-existence test.';
      else {
        const norm = r.name.toLowerCase().replace(/[^a-z0-9]/g, '');
        if (existing.has(norm)) err = 'Duplicates an existing record — duplicates are never auto-merged.';
        else existing.add(norm);
      }
      if (err) anyErr = true;
      return { ...r, err };
    });
    if (checked.length === 0) return;
    if (anyErr) { setRows(checked.length ? checked : [blankRow()]); return; }
    onAdd(checked.map((r) => ({ name: r.name.trim(), category: r.category, website: r.website.trim() })));
    onClose();
  };

  return (
    <div className="drawer-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal" data-screen-label="Add leads">
        <h3 className="modal-title">Add leads</h3>
        <p className="modal-sub">The staging bar is enforced: <code>name</code> + <code>category</code> + working <code>website</code>. Leads enter the same pipeline the agent uses.</p>
        <div className="al-rows">
          {rows.map((r) => (
            <div key={r.key}>
              <div className={'al-row' + (r.err ? ' row-err' : '')}>
                <input placeholder="Business name" value={r.name} onChange={(e) => setRow(r.key, 'name', e.target.value)} autoFocus={rows.length === 1} />
                <select value={r.category} onChange={(e) => setRow(r.key, 'category', e.target.value)}>
                  {settings.categories.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
                <input placeholder="https://website.com" value={r.website} onChange={(e) => setRow(r.key, 'website', e.target.value)} />
                <button className="icon-btn" title="Remove row" onClick={() => setRows((rs) => rs.length > 1 ? rs.filter((x) => x.key !== r.key) : rs)}>
                  <svg width="12" height="12" viewBox="0 0 12 12"><path d="M2.5 2.5l7 7M9.5 2.5l-7 7" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"></path></svg>
                </button>
              </div>
              {r.err && <p className="al-err">{r.err}</p>}
            </div>
          ))}
        </div>
        <Btn small className="al-add" onClick={() => setRows((rs) => [...rs, blankRow()])}>+ Add another</Btn>
        <div className="modal-actions">
          <Btn kind="btn-primary" onClick={submit} disabled={!rows.some((r) => r.name || r.website)}>Stage {rows.filter((r) => r.name || r.website).length || ''} lead{rows.filter((r) => r.name || r.website).length === 1 ? '' : 's'}</Btn>
          <Btn onClick={onClose}>Cancel</Btn>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { LeadsView, AddLeadsModal });
