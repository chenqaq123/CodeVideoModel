"""GPT-6 creates a deterministic, procedural Three.js scene from a text prompt."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

from . import WIDTH, HEIGHT, FPS, FRAMES, PROGRAM_MODEL, check_video

ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / "inference" / "render.py"
SOURCE_SUFFIXES = {".js", ".mjs", ".html", ".css", ".json", ".glsl", ".wgsl"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def case_files(root):
    case = root / "case"
    files = sorted(p for p in case.rglob("*") if p.is_file() and p.suffix in SOURCE_SUFFIXES)
    if not (case / "index.html").is_file() or not any(p.suffix in {".js", ".mjs"} for p in files):
        raise ValueError("A candidate needs case/index.html and procedural JavaScript.")
    for path in files:
        if path.is_symlink() or not path.resolve().is_relative_to(case.resolve()):
            raise ValueError("Case sources must not point outside the case directory.")
    return tuple(str(p.relative_to(root)) for p in files)


def generate(prompt: str, output: Path) -> None:
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Program generation needs an empty directory: {output}")
    output.mkdir(parents=True, exist_ok=True)
    (output / "vendor").mkdir()
    (output / "case").mkdir()
    agents = output / ".github/agents"
    agents.mkdir(parents=True)
    shutil.copyfile(ROOT / "prompts/program.agent.md", agents / "video-prompt-threejs.agent.md")
    for name in ("three.module.js", "LICENSE.threejs"):
        shutil.copyfile(ROOT / "vendor" / name, output / "vendor" / name)
    shutil.copyfile(RENDERER, output / "render.py")
    shutil.copyfile(ROOT / "templates/index.html", output / "case/index.html")
    shutil.copyfile(ROOT / "prompts/program.md", output / "AGENTS.md")
    (output / "prompt.txt").write_text(prompt, encoding="utf-8")
    prompt_data = {"prompt": prompt}
    (output / "prompt.json").write_text(json.dumps(prompt_data), encoding="utf-8")
    settings = dict(width=WIDTH, height=HEIGHT, fps=FPS, frames=FRAMES)
    (output / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
    prompts = ROOT / "prompts"
    camera = (prompts / "camera_contract.md").read_text()
    task = (prompts / "program_header.md").read_text() + "\n" + (prompts / "program_contract.md").read_text()
    task = task.replace("@CAMERA@", camera)
    values = {"WORK": str(output), "WIDTH": str(WIDTH), "HEIGHT": str(HEIGHT), "FPS": str(FPS),
              "FRAMES": str(FRAMES), "DURATION": str(FRAMES / FPS),
              "PROMPT_SHA": digest(output / "prompt.txt")}
    for key, value in values.items():
        task = task.replace(f"@{key}@", value)
    (output / "TASK.md").write_text(task, encoding="utf-8")
    locked = {str(p.relative_to(output)): digest(p) for p in
              (output / "AGENTS.md", output / "TASK.md", agents / "video-prompt-threejs.agent.md")}
    subprocess.run([
        "copilot", "-C", str(output), "--model", PROGRAM_MODEL,
        "--agent", "video-prompt-threejs",
        "--reasoning-effort", "xhigh", "--allow-all-tools", "--no-ask-user",
        "--no-remote", "--no-remote-export", "--autopilot", "--prompt",
        f"Read {output / 'AGENTS.md'} and {output / 'TASK.md'}. "
        "Complete only this isolated prompt-to-Three.js task as one "
        "uninterrupted /goal session. No reference video exists. Build, "
        "render, directly inspect generated keyframes/contact sheets against "
        "the prompt, refine, and deliver the fresh Candidate without waiting "
        "for user feedback.",
    ], check=True)
    for name, sha in locked.items():
        if digest(output / name) != sha:
            raise ValueError(f"The agent changed its instructions: {name}")
    if (output / "prompt.txt").read_text() != prompt:
        raise ValueError("The agent changed the target prompt.")
    if json.loads((output / "prompt.json").read_text()) != prompt_data:
        raise ValueError("The agent changed the structured prompt.")
    if json.loads((output / "settings.json").read_text()) != settings:
        raise ValueError("The agent changed the rendering contract.")
    for name in ("three.module.js", "LICENSE.threejs"):
        if (output / "vendor" / name).read_bytes() != (ROOT / "vendor" / name).read_bytes():
            raise ValueError(f"The agent changed the shared runtime: {name}")
    result = json.loads((output / "result.json").read_text())
    if result.get("status") != "candidate":
        raise ValueError("The agent did not deliver a candidate.")
    case_files(output)
    check_video(output / "case/reconstruction.mp4")
    # Use the trusted renderer, not a possibly modified workspace copy.
    subprocess.run([sys.executable, str(RENDERER), "video",
                    "--scene", str(output)], check=True)
    check_video(output / "case/reconstruction.mp4")
    if not (output / "case/camera_trajectory.json").is_file():
        raise ValueError("The candidate has no camera trajectory.")
    shutil.copyfile(output / "case/reconstruction.mp4", output / "proxy.mp4")
