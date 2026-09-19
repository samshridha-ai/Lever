import { useEffect, useState } from 'react';
import { api } from './services/api';

const score = value => typeof value === 'number' && Number.isFinite(value) ? value.toFixed(2) : (value ?? 'Data unavailable');
const fields = [
  ['G1', 'Previous Grade 1', '0–20'], ['G2', 'Previous Grade 2', '0–20'],
  ['absences', 'Absences', '0 or more'], ['studytime', 'Study Time', '1–4'],
  ['failures', 'Failures', '0 or more'],
];

export default function SnapshotHistory({ studentId, faculty = false }) {
  const [snapshots, setSnapshots] = useState();
  const [expanded, setExpanded] = useState(null);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState();
  const load = () => api.snapshots(studentId).then(data => {
    const rows = data.snapshots || [];
    setSnapshots(rows); setExpanded(rows[0]?.id ?? null);
  }).catch(setError);
  useEffect(() => { load(); }, [studentId]);
  const submit = async event => {
    event.preventDefault(); setError();
    try { await api.addSnapshot(studentId, Object.fromEntries(new FormData(event.currentTarget))); setAdding(false); await load(); }
    catch (err) { setError(err); }
  };
  return <section className="card section"><div className="section-head"><div><h2>Academic Information</h2><p className="muted">Latest snapshot is current; older snapshots are historical.</p></div>{faculty && <button className="primary" onClick={() => setAdding(!adding)}>+ Academic Snapshot</button>}</div>{error && <div className="api-error">{error.message || 'Unable to load academic snapshots.'}</div>}{adding && <form onSubmit={submit} className="form-grid">{fields.map(([key,label,placeholder]) => <label key={key}>{label}<input name={key} type="number" required placeholder={placeholder} min={key === 'studytime' ? 1 : 0} max={key === 'G1' || key === 'G2' ? 20 : undefined} step="1" /></label>)}<div className="modal-actions"><button type="button" className="secondary" onClick={() => setAdding(false)}>Cancel</button><button className="primary">Save snapshot</button></div></form>}{snapshots === undefined ? <div className="state">Loading academic snapshots…</div> : snapshots.length ? snapshots.map((snapshot, index) => <article className="intervention" key={snapshot.id}><button className="link" onClick={() => setExpanded(expanded === snapshot.id ? null : snapshot.id)}>{expanded === snapshot.id ? '▼' : '▶'} Academic Snapshot {snapshots.length - index}</button>{expanded === snapshot.id && <><div><small>G1 / G2</small>{snapshot.G1} / {snapshot.G2}</div><div><small>Absences</small>{snapshot.absences}</div><div><small>Study time / failures</small>{snapshot.studytime} / {snapshot.failures}</div><div><small>Prediction / risk</small>{score(snapshot.predicted_score)} / {snapshot.risk_level || 'Data unavailable'}</div></>}</article>) : <div className="state">No academic snapshots have been recorded.</div>}</section>;
}
