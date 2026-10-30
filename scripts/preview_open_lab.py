"""Try the open-investigation workflow with simulated planning. No API key, credits or network.

The plans come from the developers' fixtures for the bundled examples, not from
Nemotron, and every record says so. The sandbox runs, repeat check and report
are real. Use it to rehearse; use scripts/start_app.py for live Nemotron runs.

    python scripts/preview_open_lab.py            # Docker sandbox (run setup_open_runner.py first)
    python scripts/preview_open_lab.py --local    # local process, no network isolation
"""
import argparse
import json
import pathlib
import sys
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--local", action="store_true", help="Run harnesses in a local process (no network isolation).")
    args = parser.parse_args()
    import uvicorn
    from counterlab.api import create_app
    from counterlab.open_lab.sandbox import DockerSandbox, LocalProcessSandbox
    from counterlab.open_lab.simulated import simulated_transport
    scratch = ROOT / "artifacts" / "preview" / ("open-lab-" + uuid.uuid4().hex[:12])
    sandbox = LocalProcessSandbox() if args.local else DockerSandbox()
    print(json.dumps({"preview": "simulated_planning_real_sandbox", "url": f"http://127.0.0.1:{args.port}/",
                      "sandbox": sandbox.ready(), "inference_requests": 0}, indent=2), flush=True)
    from counterlab.open_lab.settings import read_env
    env = scratch / "preview.env"  # Settings changes in the preview never touch your real .env
    env.parent.mkdir(parents=True, exist_ok=True)
    env.write_text("NEBIUS_API_KEY=simulated-preview-key-0000000000\n", encoding="utf-8")

    def configure():
        values = read_env(env)
        if not values.get("NEBIUS_API_KEY"):
            raise ValueError("No key saved in the preview settings.")
        return values
    app = create_app(state_root=scratch / "state", run_root=scratch / "runs", port=args.port,
                     transport=simulated_transport, configure=configure, open_sandbox=sandbox, env_path=env)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning", access_log=False)


if __name__ == "__main__":
    main()
