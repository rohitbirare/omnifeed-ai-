import Check from 'lucide-react/dist/esm/icons/check.js';
import Sparkles from 'lucide-react/dist/esm/icons/sparkles.js';

export default function HookPicker({ hooks, selectedId, onSelect, loading, onGenerate, disabled }) {
  return (
    <section className="studio-section" aria-labelledby="hooks-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">02 / Opening line</p>
          <h2 id="hooks-heading">Hook studio</h2>
        </div>
        <button className="button button-subtle button-small" onClick={onGenerate} disabled={disabled || loading}>
          <Sparkles size={15} aria-hidden="true" />
          {loading ? 'Finding hooks' : 'Generate hooks'}
        </button>
      </div>

      {hooks.length ? (
        <div className="hook-list" role="radiogroup" aria-label="Choose an opening hook">
          {hooks.map((hook) => {
            const selected = selectedId === hook.id;
            return (
              <button
                className={`hook-option${selected ? ' is-selected' : ''}`}
                key={hook.id}
                onClick={() => onSelect(hook)}
                role="radio"
                aria-checked={selected}
              >
                <span className="hook-radio" aria-hidden="true">{selected && <Check size={13} />}</span>
                <span className="hook-copy">{hook.text}</span>
                <span className="hook-score"><strong>{hook.score}</strong><small>score</small></span>
              </button>
            );
          })}
        </div>
      ) : (
        <div className="inline-empty">Generate a few openings, then choose the one that earns the first second.</div>
      )}
    </section>
  );
}
