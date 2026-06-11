// Settings view — the human control panel. Edits are local until blur/action, then
// PATCHed; the server validates (tone vocabulary, positive price, category list shape).
import React, { useState } from 'react';
import { api } from './api.js';
import { Btn } from './ui.jsx';

export function SettingsView({ settings, toast, bump }) {
  const [s, setS] = useState({
    ...settings,
    operator_business: settings.operator_business || { name: '', description: '', personal_notes: '', signature: '' },
  });
  const [newCat, setNewCat] = useState('');

  const persist = (fields) =>
    api.patch('/settings', fields)
      .then(() => { toast('Settings saved'); bump(); })
      .catch((e) => toast(e.message));

  const set = (key, val) => setS((x) => ({ ...x, [key]: val }));
  const setBiz = (key, val) => setS((x) => ({ ...x, operator_business: { ...x.operator_business, [key]: val } }));

  const saveBiz = () => persist({ operator_business: s.operator_business });

  const addCat = () => {
    const c = newCat.trim().toLowerCase();
    if (!c) return;
    if (s.categories.includes(c)) { toast('"' + c + '" is already in the vocabulary'); return; }
    const next = [...s.categories, c];
    set('categories', next);
    setNewCat('');
    persist({ categories: next });
  };

  const removeCat = (c) => {
    const next = s.categories.filter((x) => x !== c);
    set('categories', next);
    persist({ categories: next }).then(() => toast('Removed "' + c + '" — existing leads keep their tag'));
  };

  return (
    <div className="view-pad">
      <div className="view-head">
        <h1 className="view-title">Settings</h1>
        <span className="view-sub">the agent reads all of this — pricing, taxonomy, and voice stay consistent without repetition</span>
      </div>
      <div className="set-grid">
        <div className="set-card">
          <h3>Campaign defaults</h3>
          <p className="set-sub">Snapshotted onto each campaign at creation.</p>
          <div className="set-inline">
            <div className="set-field">
              <label>Default slot price</label>
              <input type="text" value={'$' + (s.default_slot_price_cents / 100)}
                onChange={(e) => {
                  const n = parseFloat(e.target.value.replace(/[^0-9.]/g, ''));
                  if (!isNaN(n)) set('default_slot_price_cents', Math.round(n * 100));
                }}
                onBlur={() => persist({ default_slot_price_cents: s.default_slot_price_cents })} />
            </div>
            <div className="set-field">
              <label>Spots per card</label>
              <input type="number" min="1" max="12" value={s.default_total_slots}
                onChange={(e) => set('default_total_slots', +e.target.value || 8)}
                onBlur={() => persist({ default_total_slots: s.default_total_slots })} />
            </div>
          </div>
          <div className="set-field">
            <label>Seed market</label>
            <input type="text" value={s.seed_market} onChange={(e) => set('seed_market', e.target.value)}
              onBlur={() => persist({ seed_market: s.seed_market })} />
          </div>
          <p className="set-note">Changes apply to future snapshots only — existing participations keep their captured asking price.</p>
        </div>

        <div className="set-card">
          <h3>Category vocabulary</h3>
          <p className="set-sub">Lead tagging and campaign slots draw from this shared, editable taxonomy.</p>
          <div className="chips">
            {s.categories.map((c) => (
              <span key={c} className="chip">{c}
                <button title={'Remove "' + c + '"'} onClick={() => removeCat(c)}>×</button>
              </span>
            ))}
          </div>
          <div className="chip-add">
            <input placeholder="Add a category…" value={newCat} onChange={(e) => setNewCat(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') addCat(); }} />
            <Btn small onClick={addCat} disabled={!newCat.trim()}>Add</Btn>
          </div>
        </div>

        <div className="set-card">
          <h3>My business</h3>
          <p className="set-sub">Sender context for the agent — and your own slot on the card.</p>
          <div className="set-field">
            <label>Name</label>
            <input type="text" value={s.operator_business.name || ''} onChange={(e) => setBiz('name', e.target.value)} onBlur={saveBiz} />
          </div>
          <div className="set-field">
            <label>What we do</label>
            <textarea rows={2} value={s.operator_business.description || ''} onChange={(e) => setBiz('description', e.target.value)} onBlur={saveBiz}></textarea>
          </div>
          <div className="set-field">
            <label>Personal notes for the agent</label>
            <textarea rows={2} value={s.operator_business.personal_notes || ''} onChange={(e) => setBiz('personal_notes', e.target.value)} onBlur={saveBiz}></textarea>
          </div>
          <div className="set-field">
            <label>Email signature</label>
            <textarea rows={2} value={s.operator_business.signature || ''} onChange={(e) => setBiz('signature', e.target.value)} onBlur={saveBiz}></textarea>
          </div>
        </div>

        <div className="set-card">
          <h3>Outreach style</h3>
          <p className="set-sub">Served to the agent verbatim — it writes the way you would.</p>
          <div className="set-field">
            <label>Base tone</label>
            <select value={s.outreach_tone} onChange={(e) => { set('outreach_tone', e.target.value); persist({ outreach_tone: e.target.value }); }}>
              <option value="neighborly">Neighborly — warm, local, first-name</option>
              <option value="direct">Direct — short, numbers first</option>
              <option value="professional">Professional — polished, formal</option>
            </select>
          </div>
          <div className="set-field">
            <label>What a good email looks like to me</label>
            <textarea rows={5} value={s.outreach_instructions || ''} onChange={(e) => set('outreach_instructions', e.target.value)}
              onBlur={() => persist({ outreach_instructions: s.outreach_instructions })}></textarea>
          </div>
          <p className="set-note">These instructions are delivered to the agent exactly as written, alongside the quality bars.</p>
        </div>
      </div>
    </div>
  );
}
