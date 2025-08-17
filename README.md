Temporal CLI MCP Server
=======================

Lean, focused MCP server for investigating problems and monitoring the health of a Temporal Cloud environment (namespace). It wraps Temporal CLI workflow commands and returns clean JSON for SWE/SRE assistance—plus a comprehensive query builder for easy exploration of workflow runs.

What it’s for

- Rapid workflow investigation: list, describe, history, stack traces, failure patterns
- Environment health checks: counts, filtered lists, query building/validation (comprehensive query builder)
- Encapsulated practices: safe list filters, prefix fallbacks, payload decoding, retry analysis

What it’s not

- Not a universal Temporal tool. It intentionally focuses on the `workflow` command group
- No dynamic workflow generation, SDK scaffolding, or broad orchestration features
- For those, use the Temporal SDK/CLI or other specialized tools

How it connects

- Uses your Temporal CLI environments for connectivity and auth
- You select the environment once; the server forwards `--env <name>` to every `temporal` call
- All commands run with `-o json --time-format iso`; responses include parsed data and raw stdout

Install in Claude Code

- Recommended (uvx from GitHub):

```bash
claude mcp add temporal-cli-mcp -- uvx git+https://github.com/eantyshev/temporal-cli-mcp temporal-cli-mcp --env prod
```

- Dev (local path; run from repo root):

```bash
claude mcp add temporal-cli-mcp -- uv run python -m temporal_cli_mcp --env staging
```

MCP client config example

Add `--env` to your `mcp_config.json`:

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

Tools at a glance

- Inspect/Query: list_workflows, list_workflows_structured, describe_workflow, get_workflow_history (with payload decoding)
- Control: start_workflow, signal_workflow, query_workflow, cancel_workflow, terminate_workflow, reset_workflow, trace_workflow
- Health/Analysis: count_workflows, get_failed_runs, build_workflow_query, validate_workflow_query, get_query_examples

Query builder highlights

- Build valid queries quickly: build_workflow_query (structured), list_workflows_structured (execute), validate_workflow_query (check), get_query_examples (learn)
- Safer patterns by default: supported fields/operators, prefix matching guidance, and validation tips

Why SWE/SREs like it

- Fast triage and deep dives without context switching
- Common analysis patterns built-in (e.g., fallback from WorkflowType to WorkflowId prefix, retry/failed-run counts)
- Safe, parseable JSON output for automations and dashboards

Prerequisites

- Temporal CLI installed and in PATH
- Temporal CLI environments configured (e.g., ~/.config/temporalio/temporal.yaml)

Help

- For flags and options, use: `temporal workflow <sub-command> --help`
