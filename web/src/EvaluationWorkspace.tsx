import { navigateTo, useRoute } from './navigation';
import Evaluation from './Evaluation';
import SourceEvaluation from './SourceEvaluation';
import './source.css';

export default function EvaluationWorkspace() {
  const fresh = useRoute() === 'source-evaluation';
  return <div className="research-workspace"><div className="study-tabs research-switch" role="group" aria-label="Evaluation views"><button aria-pressed={!fresh} onClick={() => navigateTo('evaluation')}>Original evaluation</button><button aria-pressed={fresh} onClick={() => navigateTo('source-evaluation')}>Fresh source evaluation</button></div>{fresh ? <SourceEvaluation /> : <Evaluation />}</div>;
}
