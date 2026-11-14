"""Check actual release archives contain their installation/runtime inputs."""
from pathlib import Path
import tarfile
import zipfile


def main():
    root = Path(__file__).resolve().parents[1]
    distribution = root / "dist"
    wheels = list(distribution.glob("*.whl"))
    sources = list(distribution.glob("*.tar.gz"))
    assert len(wheels) == len(sources) == 1, "Expected one wheel and one source archive"
    with zipfile.ZipFile(wheels[0]) as archive:
        names = set(archive.namelist())
        for name in ("cli.py", "worker.py", "core.py", "server.py", "skills/SKILL.md"):
            assert "cli_anything/kselect/" + name in names, f"Wheel is missing {name}"
        assert any(name.endswith("/entry_points.txt") for name in names)
        assert any(name.endswith("/licenses/NOTICE") for name in names)
    with tarfile.open(sources[0]) as archive:
        names = {name.split("/", 1)[1] for name in archive.getnames() if "/" in name}
        for name in ("requirements-lock.txt", "scripts/setup.ps1", "scripts/live_acceptance.py", "cli_anything/kselect/skills/SKILL.md", "tests/fixtures/1400-8in-300cfm.pdf"):
            assert name in names, f"Source archive is missing {name}"
    print("Wheel runtime, entry points, notices and source installation inputs verified.")


if __name__ == "__main__":
    main()
