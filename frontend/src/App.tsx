import { useEffect, useState } from 'react';
import './styles.css';

type PlanSummary = { id: string; title: string };
type Plan = {
  id: string;
  text: string;
  review: {
    deadline_day: number | null;
    tasks: {
      id: string; name: string; owner: string | null;
      duration_days: number; depends_on: string[]; quote: string;
    }[];
    findings: { title: string; detail: string; quote: string | null }[];
  };
  schedule: {
    status: 'scheduled' | 'cycle';
    schedule: { id: string; start_day: number; end_day: number }[];
    end_day: number | null;
    deadline_day: number | null;
    meets_deadline: boolean | null;
    days_late: number | null;
    cycle: string[];
    optimal: boolean;
    lower_bound_day: number | null;
  };
};

async function readResponse<T>(response: Response): Promise<T> {
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(typeof body?.detail === 'string' ? body.detail : 'The request failed. Please try again.');
  }
  return body as T;
}

export default function App() {
  const [plans, setPlans] = useState<PlanSummary[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [plan, setPlan] = useState<Plan | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [reviewing, setReviewing] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/plans', { signal: controller.signal })
      .then(readResponse<PlanSummary[]>)
      .then((items) => {
        setPlans(items);
        if (items.length > 0) setSelectedId(items[0].id);
        else setLoading(false);
      })
      .catch((reason) => {
        if (reason.name !== 'AbortError') { setError(reason.message); setLoading(false); }
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    const controller = new AbortController();
    setPlan(null);
    setError('');
    setLoading(true);
    fetch(`/api/plans/${selectedId}`, { signal: controller.signal })
      .then(readResponse<Plan>)
      .then((result) => { setPlan(result); setLoading(false); })
      .catch((reason) => {
        if (reason.name !== 'AbortError') { setError(reason.message); setLoading(false); }
      });
    return () => controller.abort();
  }, [selectedId]);

  async function runReview() {
    setReviewing(true);
    setError('');
    try {
      const result = await fetch(`/api/plans/${selectedId}/review`, { method: 'POST' }).then(readResponse<Plan>);
      setPlan(result);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The AI review could not be completed.');
    } finally {
      setReviewing(false);
    }
  }

  const schedule = plan?.schedule;
  const blocked = schedule?.status === 'cycle';
  const deadlineUnclear = schedule?.deadline_day === null;
  const uncertain = schedule && !schedule.optimal && schedule.meets_deadline === false
    && (schedule.lower_bound_day ?? 0) <= (schedule.deadline_day ?? 0);
  const title = blocked ? 'This plan is blocked'
    : deadlineUnclear ? 'The deadline needs clarification'
    : schedule?.meets_deadline ? 'This plan can meet its deadline'
    : uncertain ? 'The deadline is not yet confirmed'
    : 'This plan will miss its deadline';
  const taskName = (id: string) => plan?.review.tasks.find((task) => task.id === id)?.name ?? id;

  return (
    <main>
      <header><span className="brand-mark" aria-hidden="true">W</span><span>WhiteSpace <span className="muted">/ Plan reviewer</span></span></header>
      <div className="page-heading"><p className="eyebrow">Town council events</p><h1>Check an event plan</h1><p className="muted">See what can finish on time, and what needs attention.</p></div>
      <div className="toolbar">
        <label>Plan<select value={selectedId} disabled={reviewing} onChange={(event) => setSelectedId(event.target.value)}>
          {plans.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}
        </select></label>
        <button className="primary" disabled={reviewing || !selectedId || loading} onClick={runReview}>{reviewing ? 'Reviewing with AI…' : 'Review with AI'}</button>
      </div>
      {error && <p role="alert" className="notice warning">{error}</p>}
      {loading && <p role="status" className="notice">Loading the plan…</p>}
      {reviewing && <p role="status" className="notice">Reading the full document and preparing a new review. This may take a minute. The previous result stays below until it is ready.</p>}
      {plan && (
        <>
          <section className={`verdict card ${blocked || deadlineUnclear || !schedule?.meets_deadline ? 'attention' : 'on-time'}`}>
            <p className="eyebrow">{plans.find((item) => item.id === plan.id)?.title}</p>
            <h2>{title}</h2>
            {blocked ? <p>These tasks are waiting for each other. Clarify the order before this plan can be scheduled.</p>
              : deadlineUnclear ? <p>The document does not give one clear deadline. Review the findings below.</p>
              : schedule?.meets_deadline ? <p>There are {(schedule.deadline_day ?? 0) - (schedule.end_day ?? 0)} days to spare in this schedule.</p>
              : uncertain ? <p>The best schedule found is late, but a better order may still meet the deadline.</p>
              : <p>The {schedule?.optimal ? 'earliest finish is' : 'current schedule finishes'} {schedule?.days_late} days after the deadline.</p>}
            <div className="metrics">
              <div><span>{schedule?.optimal ? 'Earliest finish' : 'Finish in this schedule'}</span><strong>{schedule?.end_day === null ? 'Blocked' : `Day ${schedule?.end_day}`}</strong></div>
              <div><span>Deadline</span><strong>{deadlineUnclear ? 'Unclear' : `Day ${schedule?.deadline_day}`}</strong></div>
              <div><span>Work to organise</span><strong>{plan.review.tasks.length} tasks</strong></div>
            </div>
          </section>
          {blocked && <section className="card"><h2>Resolve this circular dependency</h2><ol className="cycle">{schedule?.cycle.map((id) => <li key={id}>{taskName(id)}</li>)}</ol><p className="muted">The last task waits for the first, so none of these tasks can start.</p></section>}
          <section className="card"><div className="section-heading"><h2>Review findings</h2><span className="muted">{plan.review.findings.length} remarks</span></div>
            {plan.review.findings.length === 0 && <p className="muted">No issues identified in the written plan.</p>}
            {plan.review.findings.map((finding, index) => <article className="finding" key={index}>
              <h3>{finding.title}</h3><p>{finding.detail}</p>
              {finding.quote !== null && <details><summary>Read the source quote</summary><blockquote>{finding.quote}</blockquote></details>}
            </article>)}
          </section>
          <section className="card"><h2>Tasks and schedule</h2>
            <p className="muted">Day 0 is kickoff. One week is seven days. Each person does one task at a time.</p>
            {!blocked && <p className="proof">{schedule?.optimal ? `The shortest finish is proved: day ${schedule.end_day}.` : `The shortest finish has not been proved. No valid schedule can finish before day ${schedule?.lower_bound_day}.`}</p>}
            <div className="table-scroll"><table><thead><tr><th>Task</th><th>Person</th><th>Duration</th><th>Starts</th><th>Finishes</th></tr></thead><tbody>
              {plan.review.tasks.map((task) => {
                const entry = schedule?.schedule.find((item) => item.id === task.id);
                return <tr key={task.id}><td>{task.name}<details><summary>Source and dependencies</summary><blockquote>{task.quote}</blockquote><p className="muted">Waits for: {task.depends_on.length ? task.depends_on.map(taskName).join('; ') : 'Nothing'}</p></details></td><td>{task.owner ?? <span className="warning-text">Unassigned</span>}</td><td>{task.duration_days} days</td><td>{entry ? `Day ${entry.start_day}` : '—'}</td><td>{entry ? `Day ${entry.end_day}` : '—'}</td></tr>;
              })}
            </tbody></table></div>
          </section>
          <details className="card original"><summary>Read the original plan</summary><pre>{plan.text}</pre></details>
        </>
      )}
      <footer>Plan reviewer · Pellerby Town Council</footer>
    </main>
  );
}
