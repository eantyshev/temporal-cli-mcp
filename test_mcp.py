#!/usr/bin/env python3
import io
import json
import subprocess
import sys
import select
from typing import Dict, Any


def write_message(proc: subprocess.Popen, payload: Dict[str, Any]) -> None:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    if proc.stdin is None:
        raise RuntimeError("Process stdin is not available")
    proc.stdin.write(header)
    proc.stdin.write(body)
    proc.stdin.flush()


def read_message(proc: subprocess.Popen) -> Dict[str, Any]:
    # Read headers
    reader = proc.stdout
    if reader is None:
        raise RuntimeError("Process stdout is not available")
    content_length = None
    timeout: float = 10.0
    header_buf = io.StringIO()
    saw_content_length = False
    end_of_headers = False
    while not end_of_headers:
        rlist, _, _ = select.select([reader], [], [], timeout)
        if not rlist:
            # Dump any stderr to help debug
            if proc.stderr is not None:
                try:
                    err = proc.stderr.read()
                    if isinstance(err, bytes):
                        err = err.decode("utf-8", errors="replace")
                    print("[server stderr]", err)
                except Exception:
                    pass
            raise TimeoutError("Timed out waiting for server response header")
        line = reader.readline().decode("utf-8", errors="replace")
        if line in ("\r\n", "\n", ""):
            # Only treat blank line as end of headers if we've seen Content-Length already
            if saw_content_length:
                end_of_headers = True
                break
            else:
                # Ignore spurious blank lines before headers
                continue
        header_buf.write(line)
        if line.lower().startswith("content-length:"):
            try:
                content_length = int(line.split(":", 1)[1].strip())
                saw_content_length = True
            except Exception:
                pass
    if content_length is None:
        raise RuntimeError("No Content-Length header in response")
    body = reader.read(content_length)
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="replace")
    return json.loads(body)


def test_mcp_server():
    """Spin up the MCP server and list tools via MCP STDIO protocol."""
    process = subprocess.Popen(
        [sys.executable, "-m", "temporal_cli_mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            },
        }
        write_message(process, init_request)
        init_response = read_message(process)
        print("Initialization response:", json.dumps(init_response))

        write_message(
            process,
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {},
            },
        )

        write_message(
            process,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {},
            },
        )
        tools_response = read_message(process)
        print("Tools list response:", json.dumps(tools_response))

        tools = tools_response.get("result", {}).get("tools", [])
        print(f"Available tools: {len(tools)}")

    finally:
        try:
            process.terminate()
        except Exception:
            pass
        process.wait(timeout=5)


if __name__ == "__main__":
    test_mcp_server()