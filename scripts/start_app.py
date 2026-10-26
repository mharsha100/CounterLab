"""Start the built CounterLab app on this computer; startup uses no model credits."""

import argparse
import pathlib
import socket
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--read-only", action="store_true", help="Inspect recorded evidence; block all investigation starts without loading credentials.")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Choose a port from 1024 to 65535.")
    from counterlab.readiness import check_readiness, format_readiness
    readiness = check_readiness()
    if not readiness['inspection_ready']:
        raise SystemExit(format_readiness(readiness))
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", args.port))
        except OSError:
            raise SystemExit(f"Port {args.port} is already in use. Open the running app or choose --port with another number.") from None
    import uvicorn
    from counterlab.api import create_app
    print(f"CounterLab: http://127.0.0.1:{args.port}\nOpening recorded evidence uses no credits.", flush=True)
    uvicorn.run(create_app(port=args.port, read_only=args.read_only), host="127.0.0.1", port=args.port, log_level="warning", access_log=False)


if __name__ == "__main__":
    main()
