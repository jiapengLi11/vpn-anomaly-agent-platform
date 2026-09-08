from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_MARKERS = (
    "UER" + "_BERT",
    "UER" + "-BERT",
    "uer" + "bert",
    "kunpeng" + "_test",
    "android" + "_finetuned",
    "commercial" + "_vpn_smoke",
    "E:" + "\\project11",
    "C:" + "\\Users\\",
)
TEXT_SUFFIXES = {
    ".css", ".csv", ".html", ".js", ".json", ".md", ".py", ".toml", ".txt",
    ".vue", ".yaml", ".yml",
}


def tracked_files() -> list[Path]:
    output = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=ROOT
    ).decode("utf-8")
    return [ROOT / item for item in output.split("\0") if item]


def main() -> int:
    violations: list[str] = []
    for path in tracked_files():
        if path.suffix.lower() not in TEXT_SUFFIXES or not path.is_file():
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        lowered = content.lower()
        for index, marker in enumerate(FORBIDDEN_MARKERS, start=1):
            if marker.lower() in lowered:
                relative = path.relative_to(ROOT).as_posix()
                violations.append(f"{relative}: forbidden public-boundary marker #{index}")

    if violations:
        print("Public boundary scan failed:")
        print("\n".join(f"- {item}" for item in violations))
        return 1

    print("Public boundary scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
