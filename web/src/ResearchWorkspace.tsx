import { useState } from 'react';
import ResearchStudy from './ResearchStudy';
import SourceReproduction from './SourceReproduction';
import SourceInvestigator from './SourceInvestigator';
import './source.css';

export default function ResearchWorkspace() {
  const [view, setView] = useState(() => new URLSearchParams(window.location.search).get('view') === 'source-investigator' ? 'investigator' : 'controlled');
  return <div className="research-workspace"><div className="study-tabs research-switch" role="group" aria-label="Research views"><button aria-pressed={view === 'controlled'} onClick={() => setView('controlled')}>Controlled study</button><button aria-pressed={view === 'source'} onClick={() => setView('source')}>Source reproduction</button><button aria-pressed={view === 'investigator'} onClick={() => setView('investigator')}>Source investigator</button></div>{view === 'controlled' ? <ResearchStudy /> : view === 'source' ? <SourceReproduction onInvestigate={() => setView('investigator')} /> : <SourceInvestigator />}</div>;
}
