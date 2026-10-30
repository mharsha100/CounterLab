import { Component, type ReactNode } from 'react';

export default class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() { return { failed: true }; }

  render() {
    if (!this.state.failed) return this.props.children;
    return <main style={{ maxWidth: 720, margin: '10vh auto', padding: 28 }} role="alert">
      <span className="overline">COUNTERLAB / DISPLAY RECOVERY</span>
      <h1>This view could not be displayed.</h1>
      <p>Reload the interface to read the saved evidence again. Reloading does not
        start a new investigation or repeat a model request.</p>
      <p>Unsaved workbench edits will be lost. A running investigation continues
        on the local server; inspect Run history after reloading.</p>
      <button className="button button-primary" onClick={() => window.location.reload()}>Reload interface</button>
    </main>;
  }
}
