import { useState } from 'react';
import type { Review } from './App';

type Props = {
  initialReview: Review;
  applying: boolean;
  onApply: (review: Review) => Promise<void>;
  onCancel: () => void;
};

export default function ReviewEditor({ initialReview, applying, onApply, onCancel }: Props) {
  const [review, setReview] = useState<Review>(() => ({
    ...initialReview,
    tasks: initialReview.tasks.map((task) => ({ ...task, depends_on: [...task.depends_on] })),
    findings: [...initialReview.findings],
  }));

  function updateTask(index: number, change: Partial<Review['tasks'][number]>) {
    setReview((current) => ({ ...current, tasks: current.tasks.map((task, i) => i === index ? { ...task, ...change } : task) }));
  }

  return (
    <form className="card editor" onSubmit={(event) => { event.preventDefault(); void onApply(review); }}>
      <h2>Edit review</h2>
      <p className="muted">Correct the details, then apply them to see the new finish day. This does not call AI.</p>
      <fieldset disabled={applying}>
        <label className="deadline-field">Deadline day<input type="number" step="1" value={review.deadline_day ?? ''} placeholder="Unknown" onChange={(event) => setReview((current) => ({ ...current, deadline_day: event.target.value === '' ? null : Number(event.target.value) }))} /></label>
        <div className="table-scroll"><table><thead><tr><th>Task</th><th>Person</th><th>Days</th><th>Waits for</th></tr></thead><tbody>
          {review.tasks.map((task, index) => <tr key={task.id}>
            <td><input required aria-label={`Name for task ${task.id}`} value={task.name} onChange={(event) => updateTask(index, { name: event.target.value })} /></td>
            <td><input aria-label={`Person for ${task.name}`} placeholder="Unassigned" value={task.owner ?? ''} onChange={(event) => updateTask(index, { owner: event.target.value.trim() ? event.target.value : null })} /></td>
            <td><input required type="number" min="1" step="1" aria-label={`Duration for ${task.name}`} value={task.duration_days} onChange={(event) => updateTask(index, { duration_days: Number(event.target.value) })} /></td>
            <td><details className="dependency-picker"><summary>{task.depends_on.length ? `${task.depends_on.length} tasks` : 'Nothing'}</summary><div className="dependency-options">
              {review.tasks.map((other) => <label key={other.id}><input type="checkbox" aria-label={`${task.name} waits for ${other.name}`} checked={task.depends_on.includes(other.id)} onChange={(event) => updateTask(index, { depends_on: event.target.checked ? [...task.depends_on, other.id] : task.depends_on.filter((id) => id !== other.id) })} /><span>{other.name}{other.id === task.id ? ' (this task)' : ''}</span></label>)}
            </div></details></td>
          </tr>)}
        </tbody></table></div>
        {review.findings.length > 0 && <div className="editor-findings"><h3>Remove remarks you disagree with</h3>{review.findings.map((finding, index) => <div className="editor-finding" key={index}><span>{finding.title}</span><button type="button" onClick={() => setReview((current) => ({ ...current, findings: current.findings.filter((_, i) => i !== index) }))}>Dismiss</button></div>)}</div>}
        <div className="actions editor-actions"><button type="submit" className="primary">{applying ? 'Recalculating…' : 'Apply and recalculate'}</button><button type="button" onClick={onCancel}>Cancel</button></div>
      </fieldset>
    </form>
  );
}
