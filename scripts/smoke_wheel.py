#!/usr/bin/env python3
"""Wheel-install smoke test.

Builds the wheel, installs it into a throwaway virtualenv, and asserts that the
installed package works *from the bundled data* — i.e. the ecc skills/agents
resolve from ``sentinel_suite_mcp/_data/ecc`` and NOT from the repo's
``vendor/`` tree. The unit tests all run against ``vendor/``, so this is the
only check that the thing we actually ship is wired up correctly.

Run:  python scripts/smoke_wheel.py
Exits non-zero on any failure (used by CI).
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import venv
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _run(cmd: list[str], cwd: Path | None = None, env: dict | None = None) -> None:
    print("+ " + " ".join(str(c) for c in cmd), flush=True)
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=env, check=True)


def _venv_python(venv_dir: Path) -> Path:
    # Windows puts the interpreter in Scripts/, POSIX in bin/.
    win = venv_dir / "Scripts" / "python.exe"
    return win if win.exists() else venv_dir / "bin" / "python"


# The assertion that runs *inside* the fresh venv. Kept as a string so it
# executes with the installed package on sys.path, not the source tree.
CHECK = r"""
import os, sys
# Make sure nothing points us back at a source checkout.
os.environ.pop("SENTINEL_SUITE_ROOT", None)

from sentinel_suite_mcp import capabilities as cap

ecc = cap._ecc()
assert ecc is not None, "bundled ecc data not found in the installed wheel"
parts = ecc.resolve().parts
assert "_data" in parts, f"ecc must load from bundled _data, got: {ecc}"
assert "vendor" not in parts, f"ecc must NOT load from vendor/ in a wheel install, got: {ecc}"

skills = cap.ecc_list_skills()
agents = cap.ecc_list_agents()
assert len(skills) > 50, f"expected bundled skills, got {len(skills)}"
assert len(agents) > 20, f"expected bundled agents, got {len(agents)}"
assert skills[0]["name"] != "(unavailable)", "skills reported unavailable in wheel install"

# Router + a full skill fetch must work end-to-end from the bundle.
one = cap.ecc_get_skill(skills[0]["name"])
assert one and "skill not found" not in one, "could not fetch a bundled skill body"
rec = cap.recommend("add unit tests with test driven development")
assert rec["skills"] or rec["agents"], "router returned nothing from the bundle"

print(f"OK: wheel install healthy - {len(skills)} skills, {len(agents)} agents from {ecc}")
"""

CLI_CHECK = r"""
import subprocess, sys
# Console-script entry points must be installed and runnable.
out = subprocess.run([sys.executable, "-m", "sentinel_suite_mcp.cli", "info"],
                     capture_output=True, text=True)
assert out.returncode == 0, out.stderr
assert "sentinel-suite" in out.stdout, out.stdout
# Guard must detect a secret with zero checkout present. The test key is
# assembled at runtime (not written as a literal) so this script itself stays
# clean under the guard / secret scanners.
fake_key = "AKIA" + "X" * 16          # matches the AWS access-key pattern, obviously fake
scan = subprocess.run([sys.executable, "-m", "sentinel_suite_mcp.cli", "scan",
                       "--text", "key " + fake_key, "--json"],
                      capture_output=True, text=True)
assert "aws-access-key" in scan.stdout, scan.stdout
print("OK: CLI entry points + guard work from the wheel")
"""


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        dist = tmp / "dist"

        # 1. Build the wheel.
        _run([sys.executable, "-m", "build", "--wheel", "--outdir", str(dist)], cwd=REPO)
        wheels = list(dist.glob("sentinel_suite-*.whl"))
        assert wheels, f"no wheel produced in {dist}"
        wheel = wheels[0]
        print(f"built {wheel.name}")

        # 2. Fresh venv, install the wheel (with deps).
        venv_dir = tmp / "venv"
        venv.EnvBuilder(with_pip=True).create(venv_dir)
        py = _venv_python(venv_dir)
        _run([str(py), "-m", "pip", "install", "--quiet", "--upgrade", "pip"])
        _run([str(py), "-m", "pip", "install", "--quiet", str(wheel)])

        # 3. Run the assertions inside the venv, from a neutral cwd (tmp) so the
        #    source tree's vendor/ is never in reach.
        _run([str(py), "-c", CHECK], cwd=tmp)
        _run([str(py), "-c", CLI_CHECK], cwd=tmp)

    print("\n[PASS] wheel smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
