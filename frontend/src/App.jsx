import React, { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, ReferenceLine } from "recharts";

const API = process.env.REACT_APP_API || "http://localhost:8000/api/v1";
const WS = API.replace(/^http/, "ws") + "/ws";
const TIERS = ["PASS", "FLAG", "QUARANTINE", "BLOCK"];
const COLOR = { PASS: "#16a34a", FLAG: "#ca8a04", QUARANTINE: "#ea580c", BLOCK: "#dc2626" };
const SCENARIOS = { clean: "Clean task", attack: "Overt injection in a document", decomposed: "Decomposed (no cue) attack" };

const Badge = ({ tier }) => (
  <span style={{ background: COLOR[tier] + "22", color: COLOR[tier], padding: "2px 8px", borderRadius: 4, fontWeight: 600, fontSize: 12 }}>{tier}</span>
);

function Trace({ trace }) {
  if (!trace?.length) return null;
  return (
    <ol style={{ margin: "8px 0 0", paddingLeft: 18, fontSize: 12, color: "#374151" }}>
      {trace.map((t, i) => (
        <li key={i}><b>{t.kind}</b> · hop {t.hop} · {t.source} → {t.target}{t.indicator ? <> · <code>{t.indicator}</code></> : null}
          <div style={{ color: "#6b7280" }}>{t.snippet}</div></li>
      ))}
    </ol>
  );
}

function EventCard({ e, onReview }) {
  return (
    <div style={{ background: "#fff", borderLeft: `4px solid ${COLOR[e.tier]}`, borderRadius: 8, padding: 12, marginBottom: 8, border: "1px solid #e5e7eb" }}>
      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <Badge tier={e.tier} />
        <span style={{ fontSize: 12 }}>{e.source} → {e.target} · hop {e.hop} · {e.role}</span>
        <span style={{ marginLeft: "auto", fontSize: 12 }}>trust <b>{e.trust?.toFixed(3)}</b></span>
      </div>
      <ul style={{ margin: "6px 0 0", paddingLeft: 18, fontSize: 12 }}>{(e.reasons || []).map((r, i) => <li key={i}>{r}</li>)}</ul>
      <Trace trace={e.trace} />
      {e.tier === "QUARANTINE" && (
        <div style={{ marginTop: 8, fontSize: 12 }}>
          {e.status === "open" || !e.status ? (<>
            <button onClick={() => onReview(e.event_id, "release")}>Release</button>{" "}
            <button onClick={() => onReview(e.event_id, "reject")}>Reject</button></>) : <i>{e.status}</i>}
        </div>)}
    </div>
  );
}

export default function App() {
  const [stats, setStats] = useState(null);
  const [events, setEvents] = useState([]);
  const [health, setHealth] = useState(null);
  const [scenario, setScenario] = useState("attack");
  const [run, setRun] = useState(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const [s, ev, h] = await Promise.all([axios.get(`${API}/stats`), axios.get(`${API}/events?limit=200`), axios.get(`${API}/health`)]);
      setStats(s.data); setEvents(ev.data); setHealth(h.data);
    } catch { setHealth(null); }
  }, []);

  useEffect(() => {
    refresh();
    const ws = new WebSocket(WS);
    ws.onmessage = () => refresh();
    return () => ws.close();
  }, [refresh]);

  const launch = async () => {
    setBusy(true);
    try { setRun((await axios.post(`${API}/pipeline/run`, { scenario })).data); } finally { setBusy(false); refresh(); }
  };
  const review = async (id, action) => { await axios.post(`${API}/quarantine/${id}/${action}`); refresh(); };

  const timeline = useMemo(() => {
    const sid = run?.session_id || events[0]?.session_id;
    return events.filter((e) => e.session_id === sid).slice().reverse().map((e) => ({ hop: e.hop, trust: e.trust, tier: e.tier }));
  }, [events, run]);
  const alerts = events.filter((e) => e.tier !== "PASS");

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: 20, fontFamily: "system-ui, sans-serif", background: "#f9fafb" }}>
      <h2 style={{ marginBottom: 0 }}>MAPIS — Multi-Agent Prompt Injection Shield</h2>
      <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 16 }}>
        {health ? `detector: ${health.detector} · session store: ${health.store}` : "backend offline"}
      </div>

      <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
        {TIERS.map((t) => (
          <div key={t} style={{ flex: 1, background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, padding: 14 }}>
            <div style={{ fontSize: 12, color: "#6b7280" }}>{t}</div>
            <div style={{ fontSize: 26, fontWeight: 700, color: COLOR[t] }}>{stats?.tiers?.[t] ?? "—"}</div>
          </div>))}
      </div>

      <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, padding: 14, marginBottom: 16 }}>
        <b>Run the 5-agent pipeline</b>{" "}
        <select value={scenario} onChange={(e) => setScenario(e.target.value)}>
          {Object.entries(SCENARIOS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>{" "}
        <button disabled={busy} onClick={launch}>{busy ? "Running…" : "Run"}</button>
        {run && <span style={{ marginLeft: 12, fontSize: 13 }}>{run.blocked ? `🚨 stopped at ${run.stopped_at}; email not sent` : `✅ completed; emails sent: ${run.emails_sent}`}</span>}
      </div>

      <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, padding: 14, marginBottom: 16, height: 240 }}>
        <b>Trust timeline (latest session)</b>
        <ResponsiveContainer width="100%" height="90%">
          <LineChart data={timeline}>
            <CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="hop" /><YAxis domain={[0, 1]} />
            <Tooltip />
            <ReferenceLine y={0.75} stroke={COLOR.FLAG} strokeDasharray="4 4" />
            <ReferenceLine y={0.5} stroke={COLOR.QUARANTINE} strokeDasharray="4 4" />
            <ReferenceLine y={0.25} stroke={COLOR.BLOCK} strokeDasharray="4 4" />
            <Line type="monotone" dataKey="trust" stroke="#2563eb" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <h3>Alerts &amp; forensic traces</h3>
      {alerts.length === 0 ? <div style={{ color: "#6b7280" }}>No alerts yet — run a scenario.</div> : alerts.slice(0, 30).map((e) => <EventCard key={e.event_id} e={e} onReview={review} />)}
    </div>
  );
}
