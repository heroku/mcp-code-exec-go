import os
import tempfile
import subprocess
import shutil
from typing import Annotated, Optional, List, Dict, Any
from pydantic import Field

def run_command(cmd: List[str], cwd: Optional[str] = None) -> Dict[str, Any]:
    """Executes a command using subprocess and returns output and errors."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=cwd)
        return {
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip()
        }
    except subprocess.TimeoutExpired:
        return {
            "returncode": -2,
            "stdout": "",
            "stderr": "Error: Execution timed out"
        }

def install_dependencies(packages: Optional[List[str]], cwd: Optional[str] = None) -> Dict[str, Any]:
    """
    Installs required Go packages using `go get`.

    Args:
        packages: A list of Go import paths to install.
        cwd: Directory where go.mod exists.

    Returns:
        Result of the install command.
    """
    if not packages:
        return {"returncode": 0, "stdout": "", "stderr": ""}

    cmd = ["go", "get"] + packages
    return run_command(cmd, cwd=cwd)


def code_exec_go(
    code: Annotated[
        str,
        Field(description="The Go code to execute as a string.")
    ],
    packages: Annotated[
        Optional[List[str]],
        Field(description="Optional list of Go import paths to install using `go get`.")
    ] = None
) -> Dict[str, Any]:
    """Executes a Go code snippet with optional Go module dependencies.

    The Go runtime has access to networking, the filesystem, and standard packages.
    Code is compiled and run in a temporary module directory with any specified dependencies installed.

    A non-zero exit code is an error and should be fixed.

    Returns:
        JSON containing:
            - 'returncode': Exit status of the execution.
            - 'stdout': Captured standard output.
            - 'stderr': Captured standard error or install failure messages.
    """
    temp_dir = tempfile.mkdtemp()
    try:
        mod_result = run_command(["go", "mod", "init", "tempmodule"], cwd=temp_dir)
        if mod_result["returncode"] != 0:
            return mod_result

        install_result = install_dependencies(packages, cwd=temp_dir)
        if install_result["returncode"] != 0:
            return {
                "returncode": install_result["returncode"],
                "stdout": install_result["stdout"],
                "stderr": f"Dependency install failed:\n{install_result['stderr']}"
            }

        temp_path = os.path.join(temp_dir, "main.go")
        with open(temp_path, "w") as f:
            f.write(code)

        return run_command(["go", "run", "."], cwd=temp_dir)

    finally:
        shutil.rmtree(temp_dir)
