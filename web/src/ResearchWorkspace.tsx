import { navigateTo, useRoute } from './navigation';
import ResearchStudy from './ResearchStudy';
import SourceReproduction from './SourceReproduction';
import SourceInvestigator from './SourceInvestigator';
import ExperimentWorkbench from './ExperimentWorkbench';
import './source.css';

export default function ResearchWorkspace() {
  const route = useRoute();
  const view = route === 'source-investigator' ? 'investigator' : route === 'experiment-workbench' ? 'workbench' : route === 'source-reproduction' ? 'source' : 'controlled';
  return <div className="research-workspace"><div className="study-tabs research-switch" role="group" aria-label="Research views"><button aria-pressed={view === 'controlled'} onClick={() => navigateTo('controlled-study')}>Controlled study</button><button aria-pressed={view === 'source'} onClick={() => navigateTo('source-reproduction')}>Source reproduction</button><button aria-pressed={view === 'investigator'} onClick={() => navigateTo('source-investigator')}>Source investigator</button><button aria-pressed={view === 'workbench'} onClick={() => navigateTo('experiment-workbench')}>Design an experiment</button></div>{view === 'controlled' ? <ResearchStudy /> : view === 'source' ? <SourceReproduction onInvestigate={() => navigateTo('source-investigator')} /> : view === 'workbench' ? <ExperimentWorkbench /> : <SourceInvestigator />}</div>;
}
