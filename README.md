Temporal CLI MCP Server
=======================

An MCP server that wraps the Temporal CLI for automation of workflow inspection and one-off operations. It focuses exclusively on the `workflow` command group and outputs JSON for easy parsing.

Key points

- Only the "workflow" section is supported (e.g., list, describe, start, signal, query, cancel, terminate, show/history).
- No explicit address/namespace/TLS/API key flags in tools. All connectivity and auth come from the Temporal CLI Environment selected by `--env`.
- Every command is executed with `-o json --time-format iso`, and the MCP returns parsed JSON in a `data` field alongside raw `stdout`.
- For option details, use the Temporal CLI help: `temporal workflow <sub-command> --help`.

Temporal CLI environments

This MCP relies on Temporal CLI environments. Set them up with the CLI and select one when starting the MCP:

- Use the CLI directly: `temporal --env <env-name> workflow <args>`
- Start MCP with an environment: the MCP forwards `--env <env-name>` to all `temporal` calls.

Usage

- Via script entrypoint (installed):

```bash
temporal-cli-mcp --env prod
```

- Via module execution (dev):

```bash
uv run python -m temporal_cli_mcp --env staging
```

MCP client config example

Update your `mcp_config.json` to pass the `--env` argument:

```json
{
	"mcpServers": {
		"temporal-cli": {
			"command": "uv",
			"args": ["run", "python", "-m", "temporal_cli_mcp", "--env", "prod"],
			"cwd": "/path/to/temporal-cli-mcp"
		}
	}
}
```

Exposed tools (JSON output)

- list_workflows(query?: string, limit?: number = 10)
- describe_workflow(workflow_id: string)
- start_workflow(workflow_type: string, task_queue: string, workflow_id?: string, input_data?: string)
- signal_workflow(workflow_id: string, signal_name: string, input_data?: string)
- query_workflow(workflow_id: string, query_type: string, input_data?: string)
- cancel_workflow(workflow_id: string)
- terminate_workflow(workflow_id: string, reason?: string)
- get_workflow_history(workflow_id: string, follow?: boolean)

Each tool returns a JSON object like:

```json
{
	"success": true,
	"returncode": 0,
	"stdout": "...raw CLI output...",
	"stderr": "",
	"cmd": ["temporal", "--env", "prod", "-o", "json", "--time-format", "iso", "workflow", "describe", "--workflow-id", "my-id"],
	"data": { "parsed": "json from CLI if available" }
}
```

Tips

- To learn flags for a subcommand, consult the CLI directly: `temporal workflow <sub-command> --help`.
- Ensure you have defined the desired Temporal CLI environment in your `$HOME/.config/temporalio/temporal.yaml` (or your chosen env file).

Requirements

- `temporal` CLI installed and available in PATH.
- Python 3.11+.
