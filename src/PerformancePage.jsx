import { useEffect, useState } from 'react';
import { api } from './services/api';
import SnapshotHistory from './SnapshotHistory';

const field = (data, key) => data?.[key] ?? data?.performance?.[key] ?? data?.features?.[key] ?? 'Data unavailable';
const get = (data, ...keys) => keys.reduce((result, key) => result ?? data?.[key], undefined);

export default function PerformancePage({ user }) {
  const [prediction, setPrediction] = useState();
  const [error, setError] = useState();

  useEffect(() => {
    api.prediction('me').then(response => setPrediction(response.prediction || response)).catch(setError);
  }, []);

  const indicators = [
    ['Previous Period Grade', 'G1'], ['Latest Previous Period Grade', 'G2'],
    ['Absences', 'absences'], ['Study Time', 'studytime'],
    ['Previous Failures', 'failures'],
  ];

  return <>
    <header className="top"><div><h1>My Performance</h1><p>Detailed academic performance information available from your record.</p></div><div className="user-chip">{user.name || user.email}</div></header>
    {error ? <div className="api-error">{error.message || 'Unable to load performance data. Please try again.'}</div> : !prediction ? <div className="card state">Loading performance data…</div> : <>
      <section className="prediction"><small>PREDICTED SCORE</small><strong>{get(prediction, 'predicted_score', 'score') ?? 'Data unavailable'}</strong><div>Model output based on currently available academic information.</div></section>
      <section className="card section"><h2>Academic Indicators</h2><p className="muted">Only fields provided by the backend are shown. Missing values are marked as unavailable.</p><div className="indicators">{indicators.map(([label, key]) => <div className="indicator" key={key}><small>{label}</small><b>{field(prediction, key)}</b></div>)}</div></section>
      <SnapshotHistory studentId="me" />
    </>}
  </>;
}
