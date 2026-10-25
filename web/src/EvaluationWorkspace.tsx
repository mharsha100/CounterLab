import { useState } from 'react';
import Evaluation from './Evaluation';
import SourceEvaluation from './SourceEvaluation';
import './source.css';

export default function EvaluationWorkspace({ initialFresh = false }: { initialFresh?: boolean }) {
  const [fresh, setFresh] = useState(initialFresh);
  return <div className="research-workspace"><div className="study-tabs research-switch" role="group" aria-label="Evaluation views"><button aria-pressed={!fresh} onClick={() => setFresh(false)}>Original evaluation</button><button aria-pressed={fresh} onClick={() => setFresh(true)}>Fresh source evaluation</button></div>{fresh ? <SourceEvaluation /> : <Evaluation />}</div>;
}
