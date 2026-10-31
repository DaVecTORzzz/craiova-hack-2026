#!/usr/bin/env python3
"""Cross-platform launcher for SafeSight.

Works on Linux, macOS and Windows with Python 3.12+.

    python scripts/dev.py setup          # install backend, ML and frontend deps
    python scripts/dev.py demo           # backend + frontend + one real clip run
    python scripts/dev.py all            # backend + frontend only
    python scripts/dev.py backend        # one process
    python scripts/dev.py frontend       # one process
    python scripts/dev.py ml -- --source ../data/videos/... --zones fixtures/zones.stand12.json
    python scripts/dev.py check          # backend tests, ML tests, frontend build
    python scripts/dev.py doctor         # tools and required files
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
ML = ROOT / "ml"
FRONTEND = ROOT / "frontend"
FACE_MODEL = ML / "models" / "face_detection_yunet_2023mar.onnx"
DEFAULT_CLIP = ROOT / "data" / "videos" / "2026-10-30_restricted-zone_cam01_persoana-langa-motor.mp4"
FACE_MODEL_URL = (
    "https://github.com/opencv/opencv_zoo/raw/main/models/"
    "face_detection_yunet/face_detection_yunet_2023mar.onnx"
)
IS_WINDOWS = os.name == "nt"


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        fail(f"'{name}' nu este instalat sau nu este în PATH.")
    return path


def command(name: str, args: list[str]) -> list[str]:
    """Return a command that also works for .cmd wrappers on Windows."""
    path = require_tool(name)
    if IS_WINDOWS and path.lower().endswith((".cmd", ".bat")):
        # CreateProcess cannot execute .cmd/.bat directly; let cmd resolve it by name.
        return ["cmd", "/c", name, *args]
    return [path, *args]


def print_command(parts: list[str]) -> None:
    print("+ " + " ".join(parts))


def run(parts: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    print_command(parts)
    subprocess.run(parts, cwd=cwd, env=env, check=True)


def base_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    old_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(ROOT) + (os.pathsep + old_pythonpath if old_pythonpath else "")
    return env


def app_env(*, mock: bool, api_url: str, frontend_url: str, frontend_port: int) -> dict[str, str]:
    env = base_env()
    env["USE_MOCK"] = "true" if mock else "false"
    env["APP_BASE_URL"] = frontend_url
    env["VITE_API_URL"] = api_url
    # The UI always talks to the backend; --mock only switches the backend to fake events.
    env["VITE_USE_MOCK"] = "false"
    if frontend_port != 5173:
        origins = f"http://localhost:{frontend_port},http://127.0.0.1:{frontend_port}"
        if env.get("CORS_ORIGINS"):
            origins = f"{origins},{env['CORS_ORIGINS']}"
        env["CORS_ORIGINS"] = origins
    return env


def popen(parts: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.Popen:
    print_command(parts)
    kwargs: dict[str, object] = {
        "cwd": str(cwd),
        "env": env,
    }
    if IS_WINDOWS:
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(parts, **kwargs)  # type: ignore[arg-type]


def stop(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    try:
        if IS_WINDOWS:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        if IS_WINDOWS:
            process.kill()
        else:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass


def wait_for_http(url: str, timeout: float = 30.0, process: subprocess.Popen | None = None) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                response.read(1)
            return True
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.4)
    return False


def download_face_model() -> None:
    if FACE_MODEL.is_file():
        print(f"face model: {FACE_MODEL} (deja prezent)")
        return
    FACE_MODEL.parent.mkdir(parents=True, exist_ok=True)
    temporary = FACE_MODEL.with_suffix(".tmp")
    print(f"descărcare face model: {FACE_MODEL}")
    try:
        urllib.request.urlretrieve(FACE_MODEL_URL, temporary)
        temporary.replace(FACE_MODEL)
    except (urllib.error.URLError, OSError) as exc:
        temporary.unlink(missing_ok=True)
        fail(f"nu am putut descărca modelul YuNet: {exc}")
    print(f"face model: {FACE_MODEL} (descărcat)")


def backend_command(args: argparse.Namespace) -> list[str]:
    cmd = [
        *command("uv", ["run", "uvicorn", "app.main:app"]),
        "--host",
        args.host,
        "--port",
        str(args.backend_port),
    ]
    if not args.no_reload:
        cmd.append("--reload")
    return cmd


def frontend_command(args: argparse.Namespace) -> list[str]:
    return command(
        "npm",
        ["run", "dev", "--", "--host", args.host, "--port", str(args.frontend_port)],
    )


def api_url(args: argparse.Namespace) -> str:
    return f"http://localhost:{args.backend_port}"


def web_url(args: argparse.Namespace) -> str:
    return f"http://localhost:{args.frontend_port}"


def setup(args: argparse.Namespace) -> None:
    require_tool("uv")
    require_tool("npm")
    print("== backend")
    run(command("uv", ["sync"]), cwd=BACKEND)
    print("== ml")
    ml_sync = ["sync"] if args.skip_yolo else ["sync", "--extra", "yolo"]
    run(command("uv", ml_sync), cwd=ML)
    print("== frontend")
    npm_args = ["ci"] if (FRONTEND / "package-lock.json").is_file() else ["install"]
    run(command("npm", npm_args), cwd=FRONTEND)
    print("== modele")
    download_face_model()
    print("\nSetup gata. Pornește cu: python scripts/dev.py demo")


def doctor() -> None:
    checks = [
        ("python", sys.executable),
        ("uv", shutil.which("uv")),
        ("npm", shutil.which("npm")),
        ("node", shutil.which("node")),
        ("ffmpeg", shutil.which("ffmpeg")),
    ]
    for name, path in checks:
        print(f"{name:8} {'OK ' + path if path else 'LIPSEȘTE'}")
    print(f"backend  {'OK' if (BACKEND / 'app' / 'main.py').is_file() else 'LIPSEȘTE'}")
    print(f"ml       {'OK' if (ML / 'safesight_ml' / 'run.py').is_file() else 'LIPSEȘTE'}")
    print(f"frontend {'OK' if (FRONTEND / 'package.json').is_file() else 'LIPSEȘTE'}")
    print(f"model    {'OK' if FACE_MODEL.is_file() else 'LIPSEȘTE (rulează setup)'}")
    print(f"clip     {'OK' if DEFAULT_CLIP.is_file() else 'LIPSEȘTE (pune-l în data/videos)'}")


def check() -> None:
    print("== backend tests")
    run(command("uv", ["run", "pytest", "-q"]), cwd=BACKEND, env=base_env())
    print("== ml tests")
    run(command("uv", ["run", "pytest", "-q"]), cwd=ML)
    print("== automation smoke")
    run([sys.executable, "-m", "automation.smoke"], cwd=ROOT)
    print("== frontend build")
    run(command("npm", ["run", "build"]), cwd=FRONTEND)
    print("\nCheck gata: totul a trecut.")


def run_backend(args: argparse.Namespace) -> int:
    env = app_env(mock=args.mock, api_url=api_url(args), frontend_url=web_url(args), frontend_port=args.frontend_port)
    return subprocess.run(backend_command(args), cwd=BACKEND, env=env).returncode


def run_frontend(args: argparse.Namespace) -> int:
    env = app_env(mock=args.mock, api_url=api_url(args), frontend_url=web_url(args), frontend_port=args.frontend_port)
    return subprocess.run(frontend_command(args), cwd=FRONTEND, env=env).returncode


def run_ml(args: argparse.Namespace) -> int:
    extra = list(args.ml_args)
    if extra and extra[0] == "--":
        extra = extra[1:]
    cmd = command("uv", ["run", "python", "-m", "safesight_ml.run", *extra])
    return subprocess.run(cmd, cwd=ML, env=base_env()).returncode


def run_servers(processes: list[tuple[str, subprocess.Popen]]) -> int:
    try:
        while True:
            for name, process in processes:
                code = process.poll()
                if code is not None:
                    print(f"\n{name} s-a oprit cu codul {code}.")
                    return code or 1
            time.sleep(0.4)
    except KeyboardInterrupt:
        print("\nOprire cerută; închid procesele...")
        return 0
    finally:
        for _, process in processes:
            stop(process)


def run_all(args: argparse.Namespace) -> int:
    env = app_env(mock=args.mock, api_url=api_url(args), frontend_url=web_url(args), frontend_port=args.frontend_port)
    backend = popen(backend_command(args), cwd=BACKEND, env=env)
    try:
        frontend = popen(frontend_command(args), cwd=FRONTEND, env=env)
    except BaseException:
        stop(backend)
        raise
    print(f"\nBackend:  {api_url(args)}/health")
    print(f"Frontend: {web_url(args)}")
    print("Ctrl-C pentru oprire.\n")
    return run_servers([("backend", backend), ("frontend", frontend)])


def run_demo(args: argparse.Namespace) -> int:
    clip = Path(args.clip).expanduser().resolve() if args.clip else DEFAULT_CLIP
    env = app_env(mock=args.mock, api_url=api_url(args), frontend_url=web_url(args), frontend_port=args.frontend_port)
    backend = popen(backend_command(args), cwd=BACKEND, env=env)
    try:
        frontend = popen(frontend_command(args), cwd=FRONTEND, env=env)
    except BaseException:
        stop(backend)
        raise
    ml_process: subprocess.Popen | None = None
    processes: list[tuple[str, subprocess.Popen]] = [("backend", backend), ("frontend", frontend)]
    try:
        print(f"\nBackend:  {api_url(args)}/health")
        print(f"Frontend: {web_url(args)}")
        if not wait_for_http(f"{api_url(args)}/health", process=backend):
            print("Backend-ul nu a răspuns la /health.", file=sys.stderr)
            return 1

        if args.mock:
            print("Mod mock: backend-ul emite evenimente false; edge-ul nu pornește.")
        elif args.no_ml:
            print("Edge-ul nu pornește (--no-ml).")
        elif not clip.is_file():
            print(f"Clipul lipsește: {clip}", file=sys.stderr)
            print("UI-ul rămâne pornit. Folosește backend/scripts/demo_event.py pentru fallback.", file=sys.stderr)
        elif not FACE_MODEL.is_file():
            print("Modelul YuNet lipsește. Rulează: python scripts/dev.py setup", file=sys.stderr)
        else:
            ml_command = command(
                "uv",
                [
                    "run",
                    "python",
                    "-m",
                    "safesight_ml.run",
                    "--source",
                    str(clip),
                    "--zones",
                    "fixtures/zones.stand12.json",
                    "--camera-id",
                    "stand12",
                    "--engine-on",
                    "--post",
                    "--api-url",
                    api_url(args),
                    "--edge-token",
                    args.edge_token,
                    "--live-dir",
                    str(BACKEND / "snapshots" / "live"),
                ],
            )
            # Edge-ul procesează clipul și se oprește; serverele rămân pornite.
            ml_process = popen(ml_command, cwd=ML, env=base_env())

        print("Ctrl-C pentru oprire.\n")
        return run_servers(processes)
    finally:
        if ml_process is not None:
            stop(ml_process)
        stop(backend)
        stop(frontend)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SafeSight cross-platform launcher")
    sub = parser.add_subparsers(dest="command", required=True)

    p_setup = sub.add_parser("setup", help="instalează dependențele și modelul de blur")
    p_setup.add_argument("--skip-yolo", action="store_true", help="nu instala ultralytics (fără detecție reală)")
    p_setup.set_defaults(func=setup)

    p_doctor = sub.add_parser("doctor", help="verifică uneltele și fișierele necesare")
    p_doctor.set_defaults(func=lambda _args: doctor())

    p_check = sub.add_parser("check", help="rulează testele și build-ul")
    p_check.set_defaults(func=lambda _args: check())

    p_backend = sub.add_parser("backend", help="pornește doar API-ul")
    add_common(p_backend)
    p_backend.set_defaults(func=run_backend)

    p_frontend = sub.add_parser("frontend", help="pornește doar frontend-ul")
    add_common(p_frontend)
    p_frontend.set_defaults(func=run_frontend)

    p_all = sub.add_parser("all", help="pornește backend + frontend")
    add_common(p_all)
    p_all.set_defaults(func=run_all)

    p_demo = sub.add_parser("demo", help="backend + frontend + un run real pe clip")
    add_common(p_demo)
    p_demo.add_argument("--clip", type=Path, help="clipul folosit de edge")
    p_demo.add_argument("--no-ml", action="store_true", help="nu porni edge-ul")
    p_demo.add_argument("--edge-token", default=os.getenv("EDGE_TOKEN", "dev-edge-token"))
    p_demo.set_defaults(func=run_demo)

    p_ml = sub.add_parser("ml", help="pornește edge-ul; argumentele după -- merg la run.py")
    p_ml.add_argument("ml_args", nargs=argparse.REMAINDER)
    p_ml.set_defaults(func=run_ml)

    return parser


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--backend-port", type=int, default=8000)
    parser.add_argument("--frontend-port", type=int, default=5173)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--mock", action="store_true", help="backend mock, fără model")
    parser.add_argument("--no-reload", action="store_true", help="fără --reload pe backend")


def main() -> int:
    if sys.version_info < (3, 12):
        fail("ai nevoie de Python 3.12+ (backend-ul și ML-ul cer 3.12).")
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
