// Leads view — table of all businesses (campaign-independent), by-contact toggle,
// structured add-leads. The staging bar is enforced server-side; rejections surface inline.
import React, { useState } from 'react';
import { api } from './api.js';
import { Btn, CategoryTag, columnOf, money, Pill, STATUS_META, StatusDot, timeAgo } from './ui.jsx';

const STAGES = ['staged', 'researching', 'researched', 'contacted', 'interested', 'waitlisted', 'committed', 'declined', 'disqualified'];

export function LeadsView({ businesses, settings, onOpen, toast, bump }) {
  const [mode, setMode] = useState('businesses');
  const [q, setQ] = useState('');
  const [cat, setCat] = useState('all');
  const [stage, setStage] = useState('all');
  const [sort, setSort] = useState({ key: 'added', dir: -1 });
  const [adding, setAdding] = useState(false);

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
    return (new Date(a.created_at) - new Date(b.created_at)) * sort.dir;
  });

  const toggleSort = (key) => setSort((s) => s.key === key ? { key, dir: -s.dir } : { key, dir: key === 'added' ? -1 : 1 });
  const arrow = (key) => sort.key === key ? (sort.dir > 0 ? ' ↑' : ' ↓') : '';
  const totalContacts = businesses.reduce((s, b) => s + b.contacts.length, 0);

  return (
    <div className="view-pad">
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
          {STAGES.map((s) => <option key={s} value={s}>{STATUS_META[s].label}</option>)}
        </select>
        {(q || cat !== 'all' || stage !== 'all') && <Btn small onClick={() => { setQ(''); setCat('all'); setStage('all'); }}>Clear</Btn>}
      </div>

      {mode === 'businesses'
        ? <BusinessTable rows={sorted} onOpen={onOpen} toggleSort={toggleSort} arrow={arrow} />
        : <ContactTable businesses={sorted} onOpen={onOpen} />}

      {adding && <AddLeadsModal settings={settings} onClose={() => setAdding(false)} toast={toast} bump={bump} />}
    </div>
  );
}

function BusinessTable({ rows, onOpen, toggleSort, arrow }) {
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
            const primary = b.contacts.find((c) => c.is_primary) || b.contacts[0];
            const isCommitted = p && (p.status === 'committed' || p.status === 'paid');
            const closed = col === 'disqualified' || col === 'declined';
            return (
              <tr key={b.id} className={closed ? 'row-closed' : ''} onClick={() => onOpen(b.id)}>
                <td><span className="lt-name">{!b.operator_viewed_at && <span className="unviewed-dot" title="Not yet viewed"></span>}{b.name}</span></td>
                <td><CategoryTag category={b.category} /></td>
                <td><Pill tone="pill-status"><StatusDot status={col} />{STATUS_META[col].label}{p && p.status === 'paid' ? ' · Paid' : ''}</Pill></td>
                <td>{primary ? <span className="lt-contact"><span>{primary.name || '—'}</span><span className="sub">{primary.title}</span></span> : <span className="dim">—</span>}</td>
                <td>{primary && primary.email ? <span>{primary.email} <span className="confidence" title={'Source: ' + (primary.email_source || 'unknown')}>{primary.email_confidence}</span></span> : <span className="dim">—</span>}</td>
                <td className="num">{primary && primary.phone ? primary.phone : <span className="dim">—</span>}</td>
                <td>{p ? <span className="dim">{p.campaign.name}{p.status === 'waitlisted' ? ' · WL #' + p.waitlist_order : ''}{p.slot_number ? ' · slot ' + p.slot_number : ''}</span> : <span className="dim">—</span>}</td>
                <td className="num">{p ? (isCommitted ? <span className="committed-price">{money(p.committed_amount_cents)}</span> : money(p.asking_price_cents) + ' ask') : <span className="dim">—</span>}</td>
                <td className="dim num">{timeAgo(b.created_at)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="lt-foot">{rows.length} rows shown · click any row for research, contacts, emails &amp; comments</div>
    </div>
  );
}

function ContactTable({ businesses, onOpen }) {
  const rows = [];
  businesses.forEach((b) => b.contacts.forEach((c) => rows.push({ c, b })));
  return (
    <div className="lt-wrap">
      <table className="lt">
        <thead>
          <tr><th>Contact</th><th>Title</th><th>Email</th><th>Phone</th><th>Business</th><th>Category</th><th>Stage</th></tr>
        </thead>
        <tbody>
          {rows.map(({ c, b }) => {
            const col = columnOf(b);
            return (
              <tr key={c.id} onClick={() => onOpen(b.id)}>
                <td><span className="lt-name">{c.name || '—'}{c.is_primary && <Pill tone="pill-subtle">primary</Pill>}</span></td>
                <td className="dim">{c.title || '—'}</td>
                <td>{c.email ? <span>{c.email} <span className="confidence" title={'Source: ' + (c.email_source || 'unknown')}>{c.email_confidence}</span></span> : <span className="dim">—</span>}</td>
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

// Structured row-based lead entry. The server enforces the bar; per-lead rejections
// (including duplicate-naming) come back and render on the matching row.
export function AddLeadsModal({ settings, onClose, toast, bump }) {
  const blankRow = () => ({ key: Math.random().toString(36).slice(2), name: '', category: settings.categories[0], website: '', err: null });
  const [rows, setRows] = useState([blankRow()]);
  const [busy, setBusy] = useState(false);

  const setRow = (key, field, val) => setRows((rs) => rs.map((r) => r.key === key ? { ...r, [field]: val, err: null } : r));
  const filled = rows.filter((r) => r.name || r.website);

  const submit = async () => {
    if (!filled.length || busy) return;
    setBusy(true);
    try {
      const result = await api.post('/businesses/stage', {
        leads: filled.map((r) => ({ name: r.name.trim(), category: r.category, website: r.website.trim() })),
      });
      if (result.staged.length) {
        toast('Staged ' + result.staged.length + ' lead' + (result.staged.length === 1 ? '' : 's'));
        bump();
      }
      if (result.rejected.length) {
        const reasonByName = {};
        result.rejected.forEach((rej) => { reasonByName[(rej.lead.name || '').trim()] = rej.reason; });
        setRows((rs) => rs
          .filter((r) => !result.staged.some((s) => s.name === r.name.trim()))
          .map((r) => ({ ...r, err: reasonByName[r.name.trim()] || null })));
      } else {
        onClose();
      }
    } catch (e) {
      toast(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="drawer-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal">
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
        <Btn small onClick={() => setRows((rs) => [...rs, blankRow()])}>+ Add another</Btn>
        <div className="modal-actions">
          <Btn kind="btn-primary" onClick={submit} disabled={!filled.length || busy}>
            Stage {filled.length || ''} lead{filled.length === 1 ? '' : 's'}
          </Btn>
          <Btn onClick={onClose}>Cancel</Btn>
        </div>
      </div>
    </div>
  );
}
