import shutil
import subprocess
import sys
from pathlib import Path


def run_script(script_path: Path) -> None:
    print(f"\n=== Running: {script_path.name} ===")
    result = subprocess.run([sys.executable, str(script_path)], cwd=script_path.parent)
    if result.returncode != 0:
        raise RuntimeError(f"Step failed: {script_path.name} (exit code {result.returncode})")


def ensure_dimensions_file(run_dir: Path) -> None:
    dimensions = run_dir / "dimensions.txt"
    lake_coords = run_dir / "lake coordinates.txt"

    if dimensions.exists():
        return

    if lake_coords.exists():
        shutil.copyfile(lake_coords, dimensions)
        print("Created dimensions.txt from lake coordinates.txt")
        return

    raise FileNotFoundError(
        "Missing dimensions.txt (and no fallback lake coordinates.txt found)."
    )


def main() -> int:
    run_dir = Path.cwd()
    steps = [
        run_dir / "1. convert gif to jpg.py",
        run_dir / "2_ocr.py",
        run_dir / "3_rename.py",
        run_dir / "4_georeferencing.py",
        run_dir / "5_geotiff.py",
    ]

    missing = [step.name for step in steps if not step.exists()]
    if missing:
        print("Missing script file(s):")
        for name in missing:
            print(f" - {name}")
        return 1

    try:
        run_script(steps[0])
        run_script(steps[1])
        run_script(steps[2])
        ensure_dimensions_file(run_dir)
        run_script(steps[3])
        run_script(steps[4])
    except Exception as exc:
        print(f"\nPipeline stopped: {exc}")
        return 1

    print("\nPipeline completed successfully (steps 1 to 5).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
