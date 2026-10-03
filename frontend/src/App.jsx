import { useEffect, useState } from "react";

const API = "http://localhost:8000";
const COLORS = { error: "#d32f2f", warning: "#ed6c02", info: "#0288d1" };

async function call(path, opts) {
  const r = await fetch(API + path, opts);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
  return data;
}
const post = (path, method, body) =>
  call(path, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

function ReviewTab() {
  const [diff, setDiff] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const run = async () => {
    setLoading(true); setError(""); setResult(null);
    try { setResult(await post("/api/review", "POST", { diff })); }
    catch (e) { setError(e.message); }
    setLoading(false);
  };

  return (
    <div>
      <textarea rows={14} style={{ width: "100%", fontFamily: "monospace" }}
        placeholder="Paste a unified diff (git diff output)..." value={diff}
        onChange={(e) => setDiff(e.target.value)} />
      <button onClick={run} disabled={loading || !diff.trim()}>
        {loading ? "Reviewing..." : "Run review"}
      </button>
      {error && <p style={{ color: "#d32f2f" }}>Error: {error}</p>}
      {result && (
        <div>
          <h3>{result.comments.length} issue(s)</h3>
          {result.failed_chunks.length > 0 && (
            <p style={{ color: "#ed6c02" }}>
              ⚠️ Partial review. AI failed for: {result.failed_chunks.map((c) => c.files.join(", ")).join("; ")}
            </p>
          )}
          {result.comments.map((c, i) => (
            <div key={i} style={{ borderLeft: `4px solid ${COLORS[c.severity]}`, padding: "4px 10px", margin: "8px 0", background: "#f6f6f6", color: "#222" }}>
              <b>{c.file}:{c.line}</b> [{c.severity}] <code>{c.rule_id}</code>
              <div>{c.message}</div>
              {c.suggestion && <div>💡 {c.suggestion}</div>}
            </div>
          ))}
          {result.skipped_files.length > 0 && <small>Skipped: {result.skipped_files.join(", ")}</small>}
        </div>
      )}
    </div>
  );
}

function SettingsTab() {
  const [yaml, setYaml] = useState("");
  const [msg, setMsg] = useState("");
  const [sim, setSim] = useState(false);

  useEffect(() => {
    call("/api/standards").then((d) => setYaml(d.yaml)).catch((e) => setMsg(e.message));
    call("/api/simulate-failure").then((d) => setSim(d.enabled)).catch(() => {});
  }, []);

  const save = async () => {
    try { await post("/api/standards", "PUT", { yaml }); setMsg("Saved ✔"); }
    catch (e) { setMsg("Not saved: " + e.message); }
  };
  const toggle = async (v) => { setSim(v); await post("/api/simulate-failure", "POST", { enabled: v }); };

  return (
    <div>
      <h3>Engineering standards (YAML)</h3>
      <textarea rows={16} style={{ width: "100%", fontFamily: "monospace" }} value={yaml}
        onChange={(e) => setYaml(e.target.value)} />
      <button onClick={save}>Save standards</button> <span>{msg}</span>
      <h3>Failure simulator (demo)</h3>
      <label><input type="checkbox" checked={sim} onChange={(e) => toggle(e.target.checked)} /> Simulate LLM outage</label>
    </div>
  );
}

function HistoryTab() {
  const [items, setItems] = useState([]);
  const load = () => call("/api/reviews").then(setItems).catch(() => {});
  useEffect(() => { load(); }, []);
  return (
    <div>
      <button onClick={load}>Refresh</button>
      {items.length === 0 && <p>No PR reviews yet.</p>}
      {items.map((it, i) => (
        <div key={i} style={{ margin: "8px 0", padding: 8, background: "#f6f6f6", color: "#222" }}>
          <b>{it.repo}#{it.pr}</b> — {it.status === "ok" ? `${it.result.comments.length} comments` : `❌ ${it.error}`}
          <div><small>{it.time}</small></div>
        </div>
      ))}
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState("review");
  const tabs = { review: <ReviewTab />, settings: <SettingsTab />, history: <HistoryTab /> };
  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: 20, textAlign: "left" }}>
      <h1>🤖 AI Code Review Bot</h1>
      {Object.keys(tabs).map((t) => (
        <button key={t} onClick={() => setTab(t)} style={{ marginRight: 8, fontWeight: tab === t ? "bold" : "normal" }}>{t}</button>
      ))}
      <hr />
      {tabs[tab]}
    </div>
  );
}