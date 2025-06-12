import asyncio, os, sys, subprocess, textwrap, json, base64
from pathlib import Path
from typing import Sequence, Mapping

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "example_clients"
PYTHON_EXE = sys.executable


async def call_client(
    module_name: str,
    cli_args: Sequence[str],
    extra_env: Mapping[str, str] | None = None,
) -> str:
    env = os.environ.copy() | (extra_env or {})

    if module_name == "remote_stdio":
        app = env.get("APP_NAME")
        if not app:
            raise RuntimeError("APP_NAME env-var required for remote_stdio context")

        if "--args" in cli_args:
            i = cli_args.index("--args")
            raw_json = cli_args[i + 1]
            encoded = base64.b64encode(raw_json.encode()).decode()

            # nasty stuff to get go to not complain about this test setup...
            shell_cmd = (
                f"echo '{encoded}' | base64 -d | jq -Rs . "
                f"| sed 's/^\"//' | sed 's/\"$//' | sed 's/\\\\\"/\"/g' "
                f"| xargs -IARG python -m example_clients.stdio_client mcp call_tool --args ARG"
            )
            cmd = [
                "heroku", "run", "--exit-code", "--app", app, "--",
                "bash", "-c", shell_cmd
            ]
        else:
            cmd = [
                "heroku", "run", "--exit-code", "--app", app, "--",
                "python", "-m", f"example_clients.stdio_client", "mcp", *cli_args,
            ]

    else:
        cmd = [
            PYTHON_EXE,
            "-m", f"example_clients.{module_name}",
            "mcp", *cli_args,
        ]

    print("Final shell command:", repr(cmd))

    proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=ROOT, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    out_b, err_b = await proc.communicate()
    out, err = out_b.decode(), err_b.decode()

    if proc.returncode:
        print("STDERR from Heroku run:\n", err, file=sys.stderr)
        print("STDOUT from Heroku run:\n", out, file=sys.stderr)

    if proc.returncode:
        raise RuntimeError(
            textwrap.dedent(
                f"""
                Client {module_name} exited with {proc.returncode}
                CMD   : {' '.join(cmd)}
                STDERR:
                {err}"""
            )
        )
    return out
