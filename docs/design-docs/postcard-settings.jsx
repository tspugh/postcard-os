// Settings view — the human control panel
function SettingsView({ settings, setSettings, toast }) {
  const [newCat, setNewCat] = React.useState('');

  const set = (key, val) => setSettings((s) => ({ ...s, [key]: val }));
  const setBiz = (key, val) => setSettings((s) => ({ ...s, myBusiness: { ...s.myBusiness, [key]: val } }));

  const addCat = () => {
    const c = newCat.trim().toLowerCase();
    if (!c) return;
    if (settings.categories.includes(c)) { toast('"' + c + '" is already in the vocabulary'); return; }
    set('categories', [...settings.categories, c]);
    setNewCat('');
    toast('Category added');
  };

  return (
    <div className="view-pad" data-screen-label="Settings">
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
              <input type="text" value={'$' + (settings.defaultSlotPriceCents / 100)} onChange={(e) => {
                const n = parseFloat(e.target.value.replace(/[^0-9.]/g, ''));
                if (!isNaN(n)) set('defaultSlotPriceCents', Math.round(n * 100));
              }} />
            </div>
            <div className="set-field">
              <label>Spots per card</label>
              <input type="number" min="1" max="12" value={settings.totalSlots} onChange={(e) => set('totalSlots', +e.target.value || 8)} />
            </div>
          </div>
          <div className="set-field">
            <label>Seed market</label>
            <input type="text" value={settings.seedMarket} onChange={(e) => set('seedMarket', e.target.value)} />
          </div>
          <p className="set-note">Changes apply to future snapshots only — existing participations keep their captured asking price.</p>
        </div>

        <div className="set-card">
          <h3>Category vocabulary</h3>
          <p className="set-sub">Lead tagging and campaign slots draw from this shared, editable taxonomy.</p>
          <div className="chips">
            {settings.categories.map((c) => (
              <span key={c} className="chip">{c}
                <button title={'Remove "' + c + '"'} onClick={() => { set('categories', settings.categories.filter((x) => x !== c)); toast('Removed "' + c + '" — existing leads keep their tag'); }}>×</button>
              </span>
            ))}
          </div>
          <div className="chip-add">
            <input placeholder="Add a category…" value={newCat} onChange={(e) => setNewCat(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') addCat(); }} />
            <Btn small onClick={addCat} disabled={!newCat.trim()}>Add</Btn>
          </div>
        </div>

        <div className="set-card">
          <h3>My business</h3>
          <p className="set-sub">Sender context for the agent — and your own slot on the card.</p>
          <div className="set-field">
            <label>Name</label>
            <input type="text" value={settings.myBusiness.name} onChange={(e) => setBiz('name', e.target.value)} />
          </div>
          <div className="set-field">
            <label>What we do</label>
            <textarea rows={2} value={settings.myBusiness.description} onChange={(e) => setBiz('description', e.target.value)}></textarea>
          </div>
          <div className="set-field">
            <label>Personal notes for the agent</label>
            <textarea rows={2} value={settings.myBusiness.notes} onChange={(e) => setBiz('notes', e.target.value)}></textarea>
          </div>
          <div className="set-field">
            <label>Email signature</label>
            <textarea rows={2} value={settings.myBusiness.signature} onChange={(e) => setBiz('signature', e.target.value)}></textarea>
          </div>
        </div>

        <div className="set-card">
          <h3>Outreach style</h3>
          <p className="set-sub">Served to the agent verbatim — it writes the way you would.</p>
          <div className="set-field">
            <label>Base tone</label>
            <select value={settings.tone} onChange={(e) => set('tone', e.target.value)}>
              <option value="neighborly">Neighborly — warm, local, first-name</option>
              <option value="direct">Direct — short, numbers first</option>
              <option value="professional">Professional — polished, formal</option>
            </select>
          </div>
          <div className="set-field">
            <label>What a good email looks like to me</label>
            <textarea rows={5} value={settings.outreachInstructions} onChange={(e) => set('outreachInstructions', e.target.value)}></textarea>
          </div>
          <p className="set-note">These instructions are delivered to the agent exactly as written, alongside the quality bars.</p>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { SettingsView });
