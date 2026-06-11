// App shell — top bar (tabs + scarcity badge), views, drawer, activity feed, toasts.
// Ported from the design's Postcard Dashboard v2.html, wired to the live REST API.
import React, { useCallback, useEffect, useState } from 'react';
import { api } from './api.js';
import { CampaignView } from './Campaign.jsx';
import { DetailDrawer } from './Drawer.jsx';
import { LeadsView } from './Leads.jsx';
import { SettingsView } from './Settings.jsx';
import { IconChevron, timeAgo, Toast, useToasts } from './ui.jsx';

export default function App() {
  const [tab, setTab] = useState('leads');
  const [businesses, setBusinesses] = useState([]);
  const [settings, setSettings] = useState(null);
  const [summary, setSummary] = useState(null);
  const [activity, setActivity] = useState([]);
  const [openId, setOpenId] = useState(null);
  const [feedOpen, setFeedOpen] = useState(false);
  const [loadError, setLoadError] = useState(null);
  const [version, setVersion] = useState(0);
  const [toasts, pushToast] = useToasts();

  const bump = useCallback(() => setVersion((v) => v + 1), []);

  useEffect(() => {
    Promise.all([api.get('/businesses'), api.get('/settings'), api.get('/summary'), api.get('/activity?limit=40')])
      .then(([b, s, sum, act]) => {
        setBusinesses(b); setSettings(s); setSummary(sum); setActivity(act); setLoadError(null);
      })
      .catch((e) => setLoadError(e.message));
  }, [version]);

  // The activity feed answers "did the agent run?" — keep it fresh.
  useEffect(() => {
    const t = setInterval(() => {
      api.get('/activity?limit=40').then(setActivity).catch(() => {});
      api.get('/summary').then(setSummary).catch(() => {});
    }, 15000);
    return () => clearInterval(t);
  }, []);

  const closeDrawer = () => { setOpenId(null); bump(); };
  const camp = summary && summary.campaign;

  if (!settings) {
    return <div className="app"><div className="view-pad">{loadError ? <div className="error-banner">Cannot reach the server: {loadError}</div> : <p className="empty-view">Loading…</p>}</div></div>;
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="wordmark"><span className="wordmark-stamp">PC</span>Postcard</div>
        <nav className="topbar-tabs">
          {['leads', 'campaign', 'settings'].map((t) => (
            <button key={t} className={'topbar-tab' + (tab === t ? ' active' : '')} onClick={() => setTab(t)}>
              {t[0].toUpperCase() + t.slice(1)}
            </button>
          ))}
        </nav>
        <div className="topbar-spacer"></div>
        {camp && (
          <button className="scarcity-badge" title={camp.name + ' — open campaign view'} style={{ cursor: 'pointer', background: 'none' }} onClick={() => setTab('campaign')}>
            <span className="scarcity-dots">
              {Array.from({ length: camp.slots_total }, (_, i) => (
                <span key={i} className={'scarcity-dot' + (i < camp.slots_filled ? ' filled' : '')}></span>
              ))}
            </span>
            <span><b>{camp.slots_filled} of {camp.slots_total}</b> filled · closes in <b>{camp.days_until_deadline}d</b></span>
          </button>
        )}
      </header>

      <div className="view">
        {loadError && <div className="view-pad"><div className="error-banner">{loadError}</div></div>}
        {tab === 'leads' && (
          <LeadsView businesses={businesses} settings={settings} summary={summary} onOpen={setOpenId} toast={pushToast} bump={bump} />
        )}
        {tab === 'campaign' && (
          <CampaignView businesses={businesses} settings={settings} version={version} onOpen={setOpenId} toast={pushToast} bump={bump} />
        )}
        {tab === 'settings' && (
          <SettingsView settings={settings} toast={pushToast} bump={bump} />
        )}
      </div>

      <ActivityFeed activity={activity} open={feedOpen} onToggle={() => setFeedOpen(!feedOpen)} />

      {openId && (
        <DetailDrawer businessId={openId} settings={settings} onClose={closeDrawer} toast={pushToast} />
      )}

      <Toast toasts={toasts} />
    </div>
  );
}

function ActivityFeed({ activity, open, onToggle }) {
  return (
    <div className={'activity' + (open ? ' open' : '')}>
      <button className="activity-toggle" onClick={onToggle}>
        <span className="activity-pulse"></span>
        Agent activity
        <span className="meta-dim">{activity.length ? 'last run ' + timeAgo(activity[0].created_at) : 'no runs yet'}</span>
        <span className="activity-chevron"><IconChevron open={open} /></span>
      </button>
      {open && (
        <ul className="activity-list">
          {activity.length === 0 && <li className="activity-row"><span className="activity-detail meta-dim">Every agent tool call lands here, with its outcome.</span></li>}
          {activity.map((a) => (
            <li key={a.id} className="activity-row">
              <span className={'activity-outcome ' + a.outcome} title={a.outcome}></span>
              <code className="activity-tool">{a.tool_name.replace('postcard_', '')}</code>
              <span className="activity-detail">{a.detail || a.outcome}</span>
              <span className="meta-dim activity-ts">{timeAgo(a.created_at)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
