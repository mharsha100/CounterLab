import { useState } from 'react';
import ResearchStudy from './ResearchStudy';
import SourceReproduction from './SourceReproduction';
import SourceInvestigator from './SourceInvestigator';
import ExperimentWorkbench from './ExperimentWorkbench';
import './source.css';

export default function ResearchWorkspace() {
  const [view, setView] = useState(() => {
    const requested = new URLSearchParams(window.location.search).get('view');
    return requested === 'source-investigator' ? 'investigator' : requested === 'experiment-workbench' ? 'workbench' : requested === 'source-reproduction' ? 'source' : 'controlled';
  });
  return <div className="research-workspace"><div className="study-tabs research-switch" role="group" aria-label="Research views"><button aria-pressed={view === 'controlled'} onClick={() => setView('controlled')}>Controlled study</button><button aria-pressed={view === 'source'} onClick={() => setView('source')}>Source reproduction</button><button aria-pressed={view === 'investigator'} onClick={() => setView('investigator')}>Source investigator</button><button aria-pressed={view === 'workbench'} onClick={() => setView('workbench')}>Design an experiment</button></div>{view === 'controlled' ? <ResearchStudy /> : view === 'source' ? <SourceReproduction onInvestigate={() => setView('investigator')} /> : view === 'workbench' ? <ExperimentWorkbench /> : <SourceInvestigator />}</div>;
}
