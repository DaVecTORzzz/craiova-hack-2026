#!/usr/bin/env python3
"""Cross-platform launcher for SafeSight.

Works on Linux, macOS and Windows with Python 3.12+.

    python scripts/dev.py setup          # install backend, ML and frontend deps
    python scripts/dev.py demo           # backend + frontend + one real clip run
    python scripts/dev.py demo --clip ../data/videos/<clip>.mp4
    python scripts/dev.py demo --rtsp rtsp://127.0.0.1:8554/stand12
    python scripts/dev.py all            # backend + frontend only
    python scripts/dev.py backend        # one process
    python scripts/dev.py frontend       # one process
    python scripts/dev.py ml -- --source ../data/videos/... --zones fixtures/zones.stand12.json
    python scripts/dev.py fallback       # one demo event via the backend edge routes
    python scripts/dev.py check          # backend tests, ML tests, frontend build
    python scripts/dev.py doctor         # tools and required files
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    for extra_path in [
        r"C:\Users\PC\AppData\Local\Programs\nodejs",
        r"C:\Program Files\nodejs",
        str(Path.home() / "AppData" / "Local" / "Programs" / "nodejs"),
    ]:
        if os.path.isdir(extra_path) and extra_path not in os.environ.get("PATH", ""):
            os.environ["PATH"] = extra_path + os.pathsep + os.environ.get("PATH", "")

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


def dotenv_value(key: str) -> str | None:
    """Read one key from the root .env without loading secrets into the frontend."""
    path = ROOT / ".env"
    if not path.is_file():
        return None
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() != key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        return value
    return None


def resolve_edge_token(cli_value: str | None) -> str:
    return cli_value or os.environ.get("EDGE_TOKEN") or dotenv_value("EDGE_TOKEN") or "dev-edge-token"


def resolve_snapshot_dir() -> Path:
    raw = os.environ.get("SNAPSHOT_DIR") or dotenv_value("SNAPSHOT_DIR") or "./snapshots"
    path = Path(raw).expanduser()
    return path if path.is_absolute() else (BACKEND / path)


def app_env(
    *,
    mock: bool,
    api_url: str,
    frontend_url: str,
    frontend_port: int,
    demo_clip: str | None = None,
    demo_camera: str | None = None,
) -> dict[str, str]:
    env = base_env()
    env["USE_MOCK"] = "true" if mock else "false"
    env["APP_BASE_URL"] = frontend_url
    env["VITE_API_URL"] = api_url
    # The UI always talks to the backend; --mock only switches the backend to fake events.
    env["VITE_USE_MOCK"] = "false"
    if demo_clip:
        env["VITE_DEMO_CLIP"] = demo_clip
    if demo_camera:
        env["VITE_DEMO_CAMERA"] = demo_camera
    if frontend_port != 5173:
        origins = f"http://localhost:{frontend_port},http://127.0.0.1:{frontend_port}"
        existing = env.get("CORS_ORIGINS") or dotenv_value("CORS_ORIGINS")
        if existing:
            origins = f"{origins},{existing}"
        env["CORS_ORIGINS"] = origins
    return env


def mask_url(url: str) -> str:
    """Hide RTSP credentials and query tokens in anything printed."""
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    if parsed.port:
        host = f"{host}:{parsed.port}"
    auth = "***@" if parsed.username or parsed.password else ""
    return urlunsplit((parsed.scheme, f"{auth}{host}", parsed.path, "", ""))


def popen(parts: list[str], *, cwd: Path, env: dict[str, str], shown: list[str] | None = None) -> subprocess.Popen:
    print_command(shown or parts)
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


def enable_demo_engine(base_url: str, camera_id: str = "stand12") -> None:
    """Match the UI engine state with the demo edge run."""
    request = urllib.request.Request(
        f"{base_url}/cameras/{camera_id}/engine",
        data=b'{"on": true}',
        method="PUT",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            response.read(1)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"warn: nu am putut porni motorul în backend: {exc}", file=sys.stderr)


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
        ["run", "dev", "--", "--host", args.host, "--port", str(args.frontend_port), "--strictPort"],
    )


def port_in_use(host: str, port: int) -> bool:
    probe = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((probe, port)) == 0


def ensure_ports(args: argparse.Namespace, *, backend: bool = False, frontend: bool = False) -> None:
    if backend and port_in_use(args.host, args.backend_port):
        fail(
            f"portul backend {args.backend_port} este deja folosit. "
            "Oprește procesul vechi sau folosește --backend-port <alt port>."
        )
    if frontend and port_in_use(args.host, args.frontend_port):
        fail(
            f"portul frontend {args.frontend_port} este deja folosit. "
            "Oprește procesul vechi sau folosește --frontend-port <alt port>."
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
    ensure_ports(args, backend=True)
    env = app_env(mock=args.mock, api_url=api_url(args), frontend_url=web_url(args), frontend_port=args.frontend_port)
    return subprocess.run(backend_command(args), cwd=BACKEND, env=env).returncode


def run_frontend(args: argparse.Namespace) -> int:
    ensure_ports(args, frontend=True)
    env = app_env(mock=args.mock, api_url=api_url(args), frontend_url=web_url(args), frontend_port=args.frontend_port)
    return subprocess.run(frontend_command(args), cwd=FRONTEND, env=env).returncode


def run_ml(args: argparse.Namespace) -> int:
    extra = list(args.ml_args)
    if extra and extra[0] == "--":
        extra = extra[1:]
    cmd = command("uv", ["run", "python", "-m", "safesight_ml.run", *extra])
    return subprocess.run(cmd, cwd=ML, env=base_env()).returncode


def run_fallback(args: argparse.Namespace) -> int:
    """Send one real edge-shaped event through backend/scripts/demo_event.py."""
    token = resolve_edge_token(args.edge_token)
    target = args.api_url or api_url(args)
    extra: list[str] = [
        "run",
        "python",
        "scripts/demo_event.py",
        "--type",
        args.type,
        "--api-url",
        target,
        "--edge-token",
        token,
    ]
    if args.snapshot:
        snapshot = args.snapshot.expanduser().resolve()
        if not snapshot.is_file():
            fail(f"snapshot-ul nu există: {snapshot}")
        extra.extend(["--snapshot", str(snapshot)])
    if args.no_engine:
        extra.append("--no-engine")
    cmd = command("uv", extra)
    code = subprocess.run(cmd, cwd=BACKEND, env=base_env()).returncode
    if code != 0:
        print("Fallback-ul a eșuat. Backend-ul rulează? Încearcă: ./run.sh all", file=sys.stderr)
    return code


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
    ensure_ports(args, backend=True, frontend=True)
    env = app_env(mock=args.mock, api_url=api_url(args), frontend_url=web_url(args), frontend_port=args.frontend_port)
    backend = popen(backend_command(args), cwd=BACKEND, env=env)
    try:
        print(f"Backend:  {api_url(args)}/health")
        if not wait_for_http(f"{api_url(args)}/health", process=backend):
            print("Backend-ul nu a răspuns la /health.", file=sys.stderr)
            stop(backend)
            return 1
        frontend = popen(frontend_command(args), cwd=FRONTEND, env=env)
    except BaseException:
        stop(backend)
        raise
    print(f"Frontend: {web_url(args)}")
    print("Ctrl-C pentru oprire.\n")
    return run_servers([("backend", backend), ("frontend", frontend)])


@dataclass(frozen=True)
class DemoFeed:
    camera_id: str
    clip: Path
    zones: str  # relative to ml/


VIDEOS = ROOT / "data" / "videos"
# One clip per seeded camera. The clips are handheld, so each zone is drawn on the clip's
# first frame and follows the ground with --align-reference.
DEMO_FEEDS = (
    DemoFeed("stand12", DEFAULT_CLIP, "fixtures/zones.stand12.json"),
    DemoFeed("taxiway-b", VIDEOS / "2026-10-30_broll_cam01_marshaller-conuri-apron.mp4", "fixtures/zones/broll-cam01.json"),
    DemoFeed("baggage-area", VIDEOS / "2026-10-30_broll_cam02_avion-la-poarta-bagaje.mp4", "fixtures/zones/broll-cam02.json"),
)


def demo_feeds(args: argparse.Namespace) -> list[DemoFeed]:
    """--clip/--rtsp keep the single-camera demo; otherwise every camera gets its clip."""
    if args.clip or args.rtsp:
        clip = Path(args.clip).expanduser().resolve() if args.clip else DEFAULT_CLIP
        return [DemoFeed(args.camera_id, clip, "fixtures/zones.stand12.json")]
    wanted = [item.strip() for item in args.cameras.split(",") if item.strip()]
    known = {feed.camera_id: feed for feed in DEMO_FEEDS}
    unknown = [camera for camera in wanted if camera not in known]
    if unknown:
        fail(f"camere necunoscute în --cameras: {', '.join(unknown)} (există: {', '.join(known)})")
    return [known[camera] for camera in wanted]


def run_demo(args: argparse.Namespace) -> int:
    ensure_ports(args, backend=True, frontend=True)
    feeds = demo_feeds(args)
    token = resolve_edge_token(args.edge_token)
    live_dir = resolve_snapshot_dir() / "live"
    runnable = [feed for feed in feeds if args.rtsp or feed.clip.is_file()]
    env = app_env(
        mock=args.mock,
        api_url=api_url(args),
        frontend_url=web_url(args),
        frontend_port=args.frontend_port,
        demo_clip=",".join(f"{feed.camera_id}={feed.clip.name}" for feed in runnable) if not args.rtsp else None,
        demo_camera=",".join(feed.camera_id for feed in runnable) or None,
    )
    env["EDGE_TOKEN"] = token
    backend = popen(backend_command(args), cwd=BACKEND, env=env)
    frontend: subprocess.Popen | None = None
    try:
        print(f"Backend:  {api_url(args)}/health")
        if not wait_for_http(f"{api_url(args)}/health", process=backend):
            print("Backend-ul nu a răspuns la /health.", file=sys.stderr)
            stop(backend)
            return 1
        if not args.mock and not args.no_ml:
            for feed in runnable:
                enable_demo_engine(api_url(args), feed.camera_id)
        frontend = popen(frontend_command(args), cwd=FRONTEND, env=env)
    except BaseException:
        stop(backend)
        raise
    edges: list[subprocess.Popen] = []
    processes: list[tuple[str, subprocess.Popen]] = [("backend", backend), ("frontend", frontend)]
    try:
        print(f"Frontend: {web_url(args)}")
        for feed in feeds:
            source = mask_url(args.rtsp) if args.rtsp else feed.clip.name
            print(f"Edge:     {feed.camera_id} <- {source}")
        print()

        if args.mock:
            print("Mod mock: backend-ul emite evenimente false; edge-ul nu pornește.")
        elif args.no_ml:
            print("Edge-ul nu pornește (--no-ml).")
        elif not FACE_MODEL.is_file():
            print("Modelul YuNet lipsește. Rulează: python scripts/dev.py setup", file=sys.stderr)
        else:
            for feed in feeds:
                if not args.rtsp and not feed.clip.is_file():
                    print(f"Clipul lipsește pentru {feed.camera_id}: {feed.clip}", file=sys.stderr)
                    continue
                source = args.rtsp or str(feed.clip)
                ml_command = command(
                    "uv",
                    [
                        "run",
                        "python",
                        "-m",
                        "safesight_ml.run",
                        "--source",
                        source,
                        "--zones",
                        feed.zones,
                        "--camera-id",
                        feed.camera_id,
                        "--engine-on",
                        "--loop",
                        "--post",
                        "--api-url",
                        api_url(args),
                        "--edge-token",
                        token,
                        "--live-dir",
                        str(live_dir),
                        # The clip camera pans; the zone follows the ground from its first frame.
                        # Not for RTSP: the published clip may differ and the zone would stay unknown.
                        *([] if args.rtsp else ["--align-reference", str(feed.clip)]),
                    ],
                )
                shown = [mask_url(part) if part == source else part for part in ml_command]
                shown = ["***" if previous == "--edge-token" else part for previous, part in zip(["", *shown], shown)]
                edges.append(popen(ml_command, cwd=ML, env=base_env(), shown=shown))
            if not edges:
                print("Niciun edge pornit. Folosește backend/scripts/demo_event.py pentru fallback.", file=sys.stderr)

        # Clipurile rulează în buclă; RTSP rulează continuu. Serverele rămân pornite.
        print("Ctrl-C pentru oprire.\n")
        return run_servers(processes)
    finally:
        for edge in edges:
            stop(edge)
        stop(backend)
        if frontend is not None:
            stop(frontend)


def rtsp_url(value: str) -> str:
    if urlsplit(value).scheme not in ("rtsp", "rtsps"):
        raise argparse.ArgumentTypeError("trebuie să înceapă cu rtsp:// sau rtsps://")
    return value


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

    p_demo = sub.add_parser("demo", help="backend + frontend + câte un edge pe fiecare cameră demo")
    add_common(p_demo)
    source = p_demo.add_mutually_exclusive_group()
    source.add_argument("--clip", type=Path, help="clip local folosit de edge (implicit cam01)")
    source.add_argument("--rtsp", type=rtsp_url, help="flux RTSP, ex. rtsp://127.0.0.1:8554/stand12")
    p_demo.add_argument("--camera-id", default="stand12", help="cu --clip/--rtsp: camera din backend pentru live frame")
    p_demo.add_argument(
        "--cameras",
        default=",".join(feed.camera_id for feed in DEMO_FEEDS),
        help="fără --clip/--rtsp: camerele pornite, separate prin virgulă",
    )
    p_demo.add_argument("--no-ml", action="store_true", help="nu porni edge-ul")
    p_demo.add_argument("--edge-token", default=None, help="token edge; implicit EDGE_TOKEN din mediu sau .env")
    p_demo.set_defaults(func=run_demo)

    p_ml = sub.add_parser("ml", help="pornește edge-ul; argumentele după -- merg la run.py")
    p_ml.add_argument("ml_args", nargs=argparse.REMAINDER)
    p_ml.set_defaults(func=run_ml)

    p_fallback = sub.add_parser("fallback", help="trimite un eveniment demo prin rutele edge")
    p_fallback.add_argument("--type", default="RESTRICTED_ZONE", choices=("RESTRICTED_ZONE", "NO_PPE", "FOD"))
    p_fallback.add_argument("--api-url", default=None, help="URL API; implicit http://localhost:<backend-port>")
    p_fallback.add_argument("--backend-port", type=int, default=8000)
    p_fallback.add_argument("--edge-token", default=None, help="token edge; implicit EDGE_TOKEN din mediu sau .env")
    p_fallback.add_argument("--snapshot", type=Path, help="JPEG deja blurat; altfel se folosește cadrul sintetic")
    p_fallback.add_argument("--no-engine", action="store_true", help="nu porni motorul pentru RESTRICTED_ZONE")
    p_fallback.set_defaults(func=run_fallback)

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
