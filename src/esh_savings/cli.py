import argparse
import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(prog="esh-savings")
    sub = parser.add_subparsers(dest="cmd")
    serve = sub.add_parser("serve", help="Start the web dashboard")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true", default=False)
    args = parser.parse_args()
    if args.cmd == "serve":
        uvicorn.run("esh_savings.api.app:app", host=args.host, port=args.port, reload=args.reload)
    else:
        parser.print_help()
