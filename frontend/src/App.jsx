import React, { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

// MAPIS operator console. Audience: the security / platform team that runs the multi-agent system (not the end user).
//  * Live monitor      - every message the agents exchange, as MAPIS scores it; alerts with the forensic trace; quarantine review
//  * Session inspector - replay any held-out benchmark session hop by hop and see why MAPIS held or passed each message
//  * Results           - the measured benchmark numbers (MAPIS vs stateless DeBERTa vs Llama Guard / NeMo)

const API = process.env.REACT_APP_API || "http://localhost:8000/api/v1";
const WS = API.replace(/^http/, "ws") + "/ws";
const TIERS = ["PASS", "FLAG", "QUARANTINE", "BLOCK"];
const COLOR = { PASS: "#16a34a", FLAG: "#ca8a04", QUARANTINE: "#ea580c", BLOCK: "#dc2626" };
const SCENARIOS = { clean: "Clean task", attack: "Overt injection in a document", decomposed: "Decomposed attack (no cue in any message)" };
const DATASETS = { multihop: "MAPIS-MultiHop (multi-hop attacks + benign twins)", realharm: "RealHarm (InjecAgent direct harm + ASB)",
  v1: "MAPIS-Bench v1 (AgentDojo + InjecAgent)", decomposed: "Decomposed", bipia: "BIPIA (unseen dataset)", independent: "Independent (hand-written)" };
const card = { background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, padding: 14, marginBottom: 16 };
const pct = (x) => (x == null ? "—" : `${(100 * x).toFixed(1)} %`);

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
      <div style={{ fontSize: 12, color: "#6b7280", marginTop: 4 }}>{e.preview}</div>
      <ul style={{ margin: "6px 0 0", paddingLeft: 18, fontSize: 12 }}>{(e.reasons || []).map((r, i) => <li key={i}>{r}</li>)}</ul>
      <Trace trace={e.trace} />
      {e.tier === "QUARANTINE" && onReview && (
        <div style={{ marginTop: 8, fontSize: 12 }}>
          {e.status === "open" || !e.status ? (<>
            <button onClick={() => onReview(e.event_id, "release")}>Release (deliver the message)</button>{" "}
            <button onClick={() => onReview(e.event_id, "reject")}>Reject (drop it)</button></>) : <i>{e.status}</i>}
        </div>)}
    </div>
  );
}

function TrustChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="hop" /><YAxis domain={[0, 1]} />
        <Tooltip />
        <ReferenceLine y={0.75} stroke={COLOR.FLAG} strokeDasharray="4 4" label={{ value: "FLAG", fontSize: 10, position: "right" }} />
        <ReferenceLine y={0.5} stroke={COLOR.QUARANTINE} strokeDasharray="4 4" label={{ value: "QUARANTINE", fontSize: 10, position: "right" }} />
        <ReferenceLine y={0.25} stroke={COLOR.BLOCK} strokeDasharray="4 4" label={{ value: "BLOCK", fontSize: 10, position: "right" }} />
        <Line type="monotone" dataKey="trust" stroke="#2563eb" strokeWidth={2} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

// ── Tab 1: live monitor ─────────────────────────────────────────────────────────────────────────────
function LiveMonitor() {
  const [stats, setStats] = useState(null);
  const [events, setEvents] = useState([]);
  const [scenario, setScenario] = useState("decomposed");
  const [framework, setFramework] = useState("langgraph");
  const [run, setRun] = useState(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const [s, ev] = await Promise.all([axios.get(`${API}/stats`), axios.get(`${API}/events?limit=200`)]);
      setStats(s.data); setEvents(ev.data);
    } catch { /* backend offline */ }
  }, []);

  useEffect(() => {
    refresh();
    const ws = new WebSocket(WS);
    ws.onmessage = () => refresh();
    return () => ws.close();
  }, [refresh]);

  const launch = async () => {
    setBusy(true);
    try { setRun((await axios.post(`${API}/pipeline/run`, { scenario, framework })).data); } finally { setBusy(false); refresh(); }
  };
  const review = async (id, action) => { await axios.post(`${API}/quarantine/${id}/${action}`); refresh(); };

  const timeline = useMemo(() => {
    const sid = run?.session_id || events[0]?.session_id;
    return events.filter((e) => e.session_id === sid).slice().reverse().map((e) => ({ hop: e.hop, trust: e.trust, tier: e.tier }));
  }, [events, run]);
  const alerts = events.filter((e) => e.tier !== "PASS");

  return (<>
    <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
      {TIERS.map((t) => (
        <div key={t} style={{ flex: 1, ...card, marginBottom: 0 }}>
          <div style={{ fontSize: 12, color: "#6b7280" }}>{t}</div>
          <div style={{ fontSize: 26, fontWeight: 700, color: COLOR[t] }}>{stats?.tiers?.[t] ?? "—"}</div>
        </div>))}
    </div>

    <div style={card}>
      <b>Run the 5-agent testbed</b> (planner → web → file → memory → code/email agent; MAPIS inspects every hop before it is delivered)<br />
      <div style={{ marginTop: 8 }}>
        <select value={framework} onChange={(e) => setFramework(e.target.value)}>
          <option value="langgraph">LangGraph</option><option value="autogen">AutoGen</option>
        </select>{" "}
        <select value={scenario} onChange={(e) => setScenario(e.target.value)}>
          {Object.entries(SCENARIOS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>{" "}
        <button disabled={busy} onClick={launch}>{busy ? "Running…" : "Run"}</button>
        {run && <span style={{ marginLeft: 12, fontSize: 13 }}>{run.blocked ? `🚨 stopped at ${run.stopped_at} — the email was NOT sent` : `✅ completed — emails sent: ${run.emails_sent}`}</span>}
      </div>
    </div>

    <div style={card}><b>Trust timeline (latest session)</b><TrustChart data={timeline} /></div>

    <h3>Alerts &amp; forensic traces</h3>
    {alerts.length === 0 ? <div style={{ color: "#6b7280" }}>No alerts yet — run a scenario.</div> : alerts.slice(0, 30).map((e) => <EventCard key={e.event_id} e={e} onReview={review} />)}
  </>);
}

// ── Tab 2: session inspector (benchmark replay) ─────────────────────────────────────────────────────────
function SessionInspector() {
  const [dataset, setDataset] = useState("multihop");
  const [list, setList] = useState([]);
  const [pick, setPick] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    axios.get(`${API}/samples?dataset=${dataset}`).then((r) => { setList(r.data); setPick(r.data[0]?.sample_id || ""); }).catch(() => setList([]));
  }, [dataset]);

  const go = async () => {
    setBusy(true);
    try { setResult((await axios.post(`${API}/replay`, { dataset, sample_id: pick })).data); } finally { setBusy(false); }
  };
  const label = (s) => `${s.attack ? "ATTACK" : "benign"} · ${s.attack ? `${s.attack_class} / ${s.vector || "-"}` : s.benign_kind || "-"} · ${s.hops} hops · ${s.task}`;

  return (<>
    <div style={card}>
      <b>Replay a held-out test session through MAPIS</b>
      <div style={{ marginTop: 8, display: "flex", gap: 8, flexWrap: "wrap" }}>
        <select value={dataset} onChange={(e) => setDataset(e.target.value)}>
          {Object.entries(DATASETS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select value={pick} onChange={(e) => setPick(e.target.value)} style={{ maxWidth: 620 }}>
          {list.map((s) => <option key={s.sample_id} value={s.sample_id}>{label(s)}</option>)}
        </select>
        <button disabled={busy || !pick} onClick={go}>{busy ? "Replaying…" : "Replay"}</button>
      </div>
    </div>

    {result && (<>
      <div style={{ ...card, borderLeft: `4px solid ${result.outcome.includes("MISSED") || result.outcome.includes("false") ? COLOR.BLOCK : COLOR.PASS}` }}>
        <b>{result.outcome}</b>{result.held_at_hop ? ` (held at hop ${result.held_at_hop})` : ""} ·{" "}
        {result.attack ? `${result.attack_class} via ${result.vector}` : `benign twin: ${result.benign_kind}`}
        <div style={{ fontSize: 12, color: "#6b7280" }}>{result.notes}</div>
      </div>
      <div style={card}><b>Trust per hop</b><TrustChart data={result.events.map((e) => ({ hop: e.hop, trust: e.trust }))} /></div>
      <div style={card}>
        <b>Hop by hop</b>
        <table style={{ width: "100%", fontSize: 12, borderCollapse: "collapse", marginTop: 8 }}>
          <thead><tr style={{ textAlign: "left", borderBottom: "1px solid #e5e7eb" }}>
            <th>hop</th><th>role</th><th>channel</th><th>tier</th><th>trust</th><th>message / action</th><th>session signals</th></tr></thead>
          <tbody>{result.events.map((e) => {
            const s = e.extra?.signals;
            return (<tr key={e.event_id} style={{ borderBottom: "1px solid #f3f4f6", verticalAlign: "top" }}>
              <td>{e.hop}</td><td>{e.role}</td><td>{e.source} → {e.target}</td><td><Badge tier={e.tier} /></td><td>{e.trust.toFixed(3)}</td>
              <td style={{ maxWidth: 360 }}>{e.preview}{e.tool_call ? <div><code>{JSON.stringify(e.tool_call)}</code></div> : null}
                {(e.reasons || []).length ? <div style={{ color: COLOR.BLOCK }}>{e.reasons.join("; ")}</div> : null}</td>
              <td style={{ color: "#6b7280" }}>{s ? `claims ${s.claims} · reuse ${s.reuse.join(", ") || "none"} · user items ${s.trusted.join(", ") || "none"} · unrequested ${s.unrequested} · echo ${s.echo} · drift ${s.drift}` : e.role === "user" || e.role === "system" ? "user = trust anchor" : "— (stateless fallback detector)"}</td>
            </tr>);
          })}</tbody>
        </table>
      </div>
      {result.events.filter((e) => e.trace?.length).map((e) => <EventCard key={"t" + e.event_id} e={e} />)}
    </>)}
  </>);
}

// ── Tab 3: measured results ─────────────────────────────────────────────────────────────────────────────
function Results() {
  const [r, setR] = useState(null);
  useEffect(() => { axios.get(`${API}/results`).then((x) => setR(x.data)).catch(() => setR({})); }, []);
  if (!r) return <div>Loading…</div>;
  const b = r.benchmark || {};
  const systems = { ...b, ...(r.llamaguard || {}), ...(r.nemo || {}) };
  const names = { mapis: "MAPIS (stateful)", "mapis-model": "MAPIS model only", "deberta-v3-small": "Stateless DeBERTa", "llama-guard-3": "Llama Guard 3", "nemo-guardrails": "NeMo Guardrails", regex: "Regex" };
  const keys = Object.keys(names).filter((k) => systems[k]);
  if (!keys.length) return <div style={card}>No results yet. Copy <code>results/benchmark.json</code> (and <code>benchmark_llamaguard.json</code>) from the GPU machine into <code>results/</code>.</div>;
  const row = (k, scope) => (scope === "overall" ? systems[k].overall : systems[k].by_set?.[scope]);
  const chart = (scope) => keys.filter((k) => row(k, scope)).map((k) => ({ system: names[k], recall: +(100 * row(k, scope).recall).toFixed(1), fpr: +(100 * row(k, scope).fpr).toFixed(1) }));
  const Table = ({ scope, title }) => (
    <div style={card}>
      <b>{title}</b>
      <table style={{ width: "100%", fontSize: 13, marginTop: 8 }}>
        <thead><tr style={{ textAlign: "left" }}><th>system</th><th>recall</th><th>FPR</th><th>accuracy</th><th>F1</th><th>n</th></tr></thead>
        <tbody>{keys.filter((k) => row(k, scope)).map((k) => { const m = row(k, scope); return (
          <tr key={k}><td>{names[k]}</td><td>{pct(m.recall)}</td><td>{pct(m.fpr)}</td><td>{pct(m.accuracy)}</td><td>{m.f1?.toFixed(3)}</td><td>{m.n}</td></tr>); })}</tbody>
      </table>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={chart(scope)}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="system" fontSize={11} /><YAxis domain={[0, 100]} /><Tooltip /><Legend />
          <Bar dataKey="recall" name="recall %" fill="#2563eb" /><Bar dataKey="fpr" name="false-positive rate %" fill="#dc2626" /></BarChart>
      </ResponsiveContainer>
    </div>);
  return (<>
    <Table scope="overall" title="All held-out test sessions" />
    <Table scope="MAPIS-MultiHop" title="Multi-hop attacks (MAPIS-MultiHop) — the core claim" />
    <Table scope="RealHarm: InjecAgent direct harm" title="RealHarm: InjecAgent direct harm" />
    <Table scope="RealHarm: ASB" title="RealHarm: Agent Security Bench" />
    <Table scope="BIPIA (unseen dataset)" title="BIPIA (never trained on)" />
    {r.seeds && <div style={card}><b>Three training seeds (mean ± std)</b>
      <table style={{ width: "100%", fontSize: 13, marginTop: 8 }}><tbody>{Object.entries(r.seeds).map(([k, v]) => (
        <tr key={k}><td>{k}</td><td>recall {pct(v.recall.mean)} ± {(100 * v.recall.std).toFixed(1)}</td><td>FPR {pct(v.fpr.mean)} ± {(100 * v.fpr.std).toFixed(1)}</td></tr>))}</tbody></table></div>}
  </>);
}

export default function App() {
  const [tab, setTab] = useState("live");
  const [health, setHealth] = useState(null);
  useEffect(() => { axios.get(`${API}/health`).then((h) => setHealth(h.data)).catch(() => setHealth(null)); }, []);
  const Tab = ({ id, children }) => (
    <button onClick={() => setTab(id)} style={{ padding: "6px 14px", border: "none", borderBottom: tab === id ? "3px solid #2563eb" : "3px solid transparent", background: "none", fontWeight: tab === id ? 700 : 400, cursor: "pointer" }}>{children}</button>);
  return (
    <div style={{ maxWidth: 1150, margin: "0 auto", padding: 20, fontFamily: "system-ui, sans-serif", background: "#f9fafb", minHeight: "100vh" }}>
      <h2 style={{ marginBottom: 0 }}>MAPIS — Multi-Agent Prompt Injection Shield</h2>
      <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 8 }}>
        Operator console · {health ? `detector: ${health.detector} · session store: ${health.store}` : "backend offline"}
      </div>
      <div style={{ borderBottom: "1px solid #e5e7eb", marginBottom: 16 }}>
        <Tab id="live">Live monitor</Tab><Tab id="inspect">Session inspector</Tab><Tab id="results">Results</Tab>
      </div>
      {tab === "live" && <LiveMonitor />}
      {tab === "inspect" && <SessionInspector />}
      {tab === "results" && <Results />}
    </div>
  );
}
