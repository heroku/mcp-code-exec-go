import os
import tempfile
import subprocess
import shutil
from typing import Optional, Dict, Any, List

def run_command(cmd: List[str]) -> Dict[str, Any]:
    """Executes a command using subprocess and returns output and errors."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
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

def install_dependencies(packages: Optional[List[str]]) -> Dict[str, Any]:
    """
    Installs required packages for a given language using the appropriate package manager.

    Args:
        packages: A list of package names to install

    Returns:
        The result of the package installation command, or a no-op result if no install is needed.
    """

    if not packages:
        return {"returncode": 0, "stdout": "", "stderr": ""}  # No installation needed

    cmd = ["go", "get"] + packages
    return run_command(cmd)

def code_exec_go(code: str, packages: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Executes a Go code snippet with optional Go module dependencies.

    Args:
        code: The Go code to execute as a string.
        packages: An optional list of Go package import paths to install using `go get`.

    Returns:
        A dictionary containing:
            - 'returncode': Exit status of the execution
            - 'stdout': Captured standard output
            - 'stderr': Captured standard error or install failure messages
    """
    # Running go creates files, so we want to create a temporary file directory:
    temp_dir = tempfile.mkdtemp()
    try:
        # Initialize a Go module
        mod_result = run_command(["go", "run", "."], cwd=temp_dir)
        if mod_result["returncode"] != 0:
            return mod_result

        # Install dependencies
        install_result = install_dependencies(packages, cwd=temp_dir)
        if install_result["returncode"] != 0:
            return {
                "returncode": install_result["returncode"],
                "stdout": install_result["stdout"],
                "stderr": f"Dependency install failed:\n{install_result['stderr']}"
            }

        # Write the Go code to a file
        temp_path = os.path.join(temp_dir, "main.go")
        with open(temp_path, "w") as f:
            f.write(code)

        # Run the Go program
        return run_command(["go", "run", "."], cwd=temp_dir)

    finally:
        shutil.rmtree(temp_dir)
