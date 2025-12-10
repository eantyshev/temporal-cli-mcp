# Safety Checks Guide

Validation rules and safety patterns for destructive Temporal operations.

## Table of Contents

- [Terminate Workflow](#terminate-workflow)
- [Reset Workflow](#reset-workflow)
- [Batch Operations](#batch-operations)
- [Pre-Operation Checklist](#pre-operation-checklist)
- [Safety Patterns](#safety-patterns)

## Terminate Workflow

**DANGER:** Terminate immediately stops workflow execution. Cannot be undone.

### Safety Rules

1. **ALWAYS provide --reason**
2. Double-check workflow ID
3. Consider `cancel` before `terminate`
4. Verify workflow status first
5. Document why termination is necessary

### Safe Termination Pattern

```bash
safe_terminate() {
  local workflow_id=$1
  local reason=$2
  local env=${3:-staging}

  # Validate inputs
  if [ -z "$workflow_id" ]; then
    echo "ERROR: WorkflowId is required"
    return 1
  fi

  if [ -z "$reason" ]; then
    echo "ERROR: Reason is required for termination"
    echo "Example: 'Workflow stuck in infinite loop after timeout'"
    return 1
  fi

  # Get current status
  echo "Checking workflow status..."
  STATUS=$(temporal --env "$env" -o json --time-format iso workflow describe \
    --workflow-id "$workflow_id" | jq -r '.workflowExecutionInfo.status')

  if [ -z "$STATUS" ]; then
    echo "ERROR: Workflow not found"
    return 1
  fi

  echo "Current status: $STATUS"

  # Warn if already terminated/completed
  if [[ "$STATUS" == "Completed" || "$STATUS" == "Terminated" ]]; then
    echo "WARNING: Workflow is already $STATUS"
    read -p "Continue anyway? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
      echo "Termination cancelled"
      return 0
    fi
  fi

  # Show details
  echo
  echo "Termination Details:"
  echo "  Environment: $env"
  echo "  WorkflowId: $workflow_id"
  echo "  Current Status: $STATUS"
  echo "  Reason: $reason"
  echo

  # Confirm
  read -p "Terminate this workflow? (type 'TERMINATE' to confirm): " confirm

  if [ "$confirm" != "TERMINATE" ]; then
    echo "Termination cancelled"
    return 0
  fi

  # Execute
  echo "Terminating workflow..."
  temporal --env "$env" -o json --time-format iso workflow terminate \
    --workflow-id "$workflow_id" \
    --reason "$reason"

  echo "Workflow terminated"
}

# Usage
safe_terminate "stuck-workflow-789" "Workflow stuck after timeout - manual intervention required" "prod"
```

### Pre-Termination Checklist

```bash
pre_terminate_check() {
  local workflow_id=$1
  local env=${2:-staging}

  echo "=== Pre-Termination Checklist ==="
  echo

  # 1. Get workflow details
  DESC=$(temporal --env "$env" -o json --time-format iso workflow describe \
    --workflow-id "$workflow_id")

  echo "1. Workflow Details:"
  echo "$DESC" | jq '{
    workflowId: .workflowExecutionInfo.execution.workflowId,
    workflowType: .workflowExecutionInfo.type.name,
    status: .workflowExecutionInfo.status,
    startTime: .workflowExecutionInfo.startTime
  }'
  echo

  # 2. Check if running
  STATUS=$(echo "$DESC" | jq -r '.workflowExecutionInfo.status')
  echo "2. Status Check: $STATUS"
  if [ "$STATUS" == "Running" ]; then
    echo "   ✓ Workflow is running (terminatable)"
  else
    echo "   ⚠️  Workflow is $STATUS (consider if termination needed)"
  fi
  echo

  # 3. Recent history
  echo "3. Recent Activity (last 5 events):"
  temporal --env "$env" -o json --time-format iso workflow show \
    --workflow-id "$workflow_id" | \
    jq '.events[-5:] | .[] | {eventId, eventType, eventTime}'
  echo

  # 4. Alternatives
  echo "4. Alternatives to Consider:"
  echo "   - Cancel: Request graceful shutdown (--cancel)"
  echo "   - Signal: Send signal to trigger shutdown"
  echo "   - Wait: Allow workflow to complete naturally"
  echo

  # 5. Recommendation
  echo "5. Recommendation:"
  if [ "$STATUS" == "Running" ]; then
    echo "   Try 'cancel' first for graceful shutdown"
    echo "   Use 'terminate' only if cancel doesn't work"
  else
    echo "   Workflow is $STATUS - termination may not be necessary"
  fi
}

# Usage
pre_terminate_check "my-workflow" "prod"
```

---

## Reset Workflow

**DANGER:** Reset can affect many workflows in batch mode. Use with extreme caution.

### Single Workflow Reset Rules

1. **MUST have** `--workflow-id`
2. **CANNOT use** `--yes` flag
3. **SHOULD have** `--reason`
4. **OPTIONAL** `--event-id`, `--run-id`

### Single Reset Pattern

```bash
safe_reset_single() {
  local workflow_id=$1
  local reason=$2
  local event_id=$3
  local env=${4:-staging}

  # Validate
  if [ -z "$workflow_id" ]; then
    echo "ERROR: WorkflowId is required"
    return 1
  fi

  if [ -z "$reason" ]; then
    echo "ERROR: Reason is required"
    return 1
  fi

  # Get workflow info
  echo "Workflow: $workflow_id"
  temporal --env "$env" -o json --time-format iso workflow describe \
    --workflow-id "$workflow_id" | \
    jq '{status: .workflowExecutionInfo.status, type: .workflowExecutionInfo.type.name}'

  # Confirm
  echo
  echo "Reset configuration:"
  echo "  WorkflowId: $workflow_id"
  echo "  Event ID: ${event_id:-last event}"
  echo "  Reason: $reason"
  read -p "Proceed? (yes/no): " confirm

  if [ "$confirm" != "yes" ]; then
    echo "Reset cancelled"
    return 0
  fi

  # Execute
  if [ -n "$event_id" ]; then
    temporal --env "$env" -o json --time-format iso workflow reset \
      --workflow-id "$workflow_id" \
      --event-id "$event_id" \
      --reason "$reason"
  else
    temporal --env "$env" -o json --time-format iso workflow reset \
      --workflow-id "$workflow_id" \
      --reason "$reason"
  fi
}

# Usage
safe_reset_single "failed-workflow" "Reset after dependency fix" "" "staging"
```

---

## Batch Operations

**EXTREME DANGER:** Batch operations affect multiple workflows simultaneously.

### Batch Reset Rules

1. **MUST have** `--query`
2. **MUST have** `--reason`
3. **MUST have** `--type` (FirstWorkflowTask, LastWorkflowTask, or BuildId)
4. **CANNOT have** `--workflow-id`, `--run-id`, `--event-id`
5. **REQUIRES** `--yes` to skip confirmation (or interactive prompt)

### Batch Reset Validation

```bash
validate_batch_reset() {
  local query=$1
  local reason=$2
  local reset_type=$3

  local errors=()

  # Required fields
  if [ -z "$query" ]; then
    errors+=("Query is required for batch operations")
  fi

  if [ -z "$reason" ]; then
    errors+=("Reason is required for batch operations")
  fi

  if [ -z "$reset_type" ]; then
    errors+=("Reset type is required for batch operations")
  fi

  # Validate reset type
  if [[ -n "$reset_type" && ! "$reset_type" =~ ^(FirstWorkflowTask|LastWorkflowTask|BuildId)$ ]]; then
    errors+=("Invalid reset type: $reset_type")
    errors+=("Allowed: FirstWorkflowTask, LastWorkflowTask, BuildId")
  fi

  # Report errors
  if [ ${#errors[@]} -gt 0 ]; then
    echo "✗ Batch reset validation failed:"
    for error in "${errors[@]}"; do
      echo "  - $error"
    done
    return 1
  fi

  echo "✓ Batch reset validation passed"
  return 0
}
```

### Safe Batch Reset Pattern

```bash
safe_batch_reset() {
  local query=$1
  local reason=$2
  local reset_type=${3:-FirstWorkflowTask}
  local env=${4:-staging}

  echo "=== Safe Batch Reset ==="
  echo

  # Validate inputs
  if ! validate_batch_reset "$query" "$reason" "$reset_type"; then
    return 1
  fi

  # Count affected workflows
  echo "Counting affected workflows..."
  COUNT=$(temporal --env "$env" -o json --time-format iso workflow count \
    --query "$query" | jq '.count')

  if [ "$COUNT" -eq 0 ]; then
    echo "No workflows match query"
    return 0
  fi

  # Show sample
  echo
  echo "Affected workflows: $COUNT"
  echo
  echo "Sample (first 5):"
  temporal --env "$env" -o json --time-format iso workflow list \
    --query "$query" \
    --limit 5 | \
    jq -r '.workflowExecutions[] | .execution.workflowId'
  echo

  # Show configuration
  echo "Batch Reset Configuration:"
  echo "  Environment: $env"
  echo "  Query: $query"
  echo "  Affected Workflows: $COUNT"
  echo "  Reset Type: $reset_type"
  echo "  Reason: $reason"
  echo

  # Multiple confirmations for safety
  if [ "$COUNT" -gt 100 ]; then
    echo "⚠️  WARNING: This affects $COUNT workflows (>100)"
    read -p "Are you sure? (type 'yes' to continue): " confirm1
    if [ "$confirm1" != "yes" ]; then
      echo "Batch reset cancelled"
      return 0
    fi
  fi

  read -p "Type the number of workflows to confirm ($COUNT): " confirm_count
  if [ "$confirm_count" != "$COUNT" ]; then
    echo "Count mismatch - batch reset cancelled"
    return 0
  fi

  read -p "Final confirmation - type 'RESET BATCH' to proceed: " confirm_final
  if [ "$confirm_final" != "RESET BATCH" ]; then
    echo "Batch reset cancelled"
    return 0
  fi

  # Execute
  echo "Executing batch reset..."
  temporal --env "$env" -o json --time-format iso workflow reset \
    --query "$query" \
    --type "$reset_type" \
    --reason "$reason" \
    --yes

  echo "Batch reset completed"
  echo "Affected: $COUNT workflows"
}

# Usage
safe_batch_reset \
  "WorkflowType = 'BuggyFlow' AND ExecutionStatus = 'Failed'" \
  "Reset after bug fix in version 2.1.0" \
  "FirstWorkflowTask" \
  "staging"
```

---

## Pre-Operation Checklist

### General Safety Checklist

```bash
pre_operation_checklist() {
  local operation=$1  # terminate, reset, cancel
  local workflow_id=$2
  local env=${3:-staging}

  echo "=== Pre-Operation Safety Checklist ==="
  echo "Operation: $operation"
  echo "WorkflowId: $workflow_id"
  echo "Environment: $env"
  echo

  # 1. Verify workflow exists
  echo "[ ] 1. Verifying workflow exists..."
  if temporal --env "$env" -o json --time-format iso workflow describe \
    --workflow-id "$workflow_id" >/dev/null 2>&1; then
    echo "    ✓ Workflow found"
  else
    echo "    ✗ Workflow not found"
    return 1
  fi

  # 2. Check workflow status
  echo "[ ] 2. Checking workflow status..."
  STATUS=$(temporal --env "$env" -o json --time-format iso workflow describe \
    --workflow-id "$workflow_id" | jq -r '.workflowExecutionInfo.status')
  echo "    Status: $STATUS"

  # 3. Review recent history
  echo "[ ] 3. Reviewing recent history..."
  temporal --env "$env" -o json --time-format iso workflow show \
    --workflow-id "$workflow_id" | \
    jq '.events[-3:] | .[] | .eventType'

  # 4. Check environment
  echo "[ ] 4. Environment confirmation..."
  read -p "    Is '$env' the correct environment? (yes/no): " env_confirm
  if [ "$env_confirm" != "yes" ]; then
    echo "    Operation cancelled - wrong environment"
    return 1
  fi

  # 5. Verify WorkflowId
  echo "[ ] 5. WorkflowId confirmation..."
  read -p "    Type the WorkflowId to confirm: " id_confirm
  if [ "$id_confirm" != "$workflow_id" ]; then
    echo "    WorkflowId mismatch - operation cancelled"
    return 1
  fi

  # 6. Reason provided
  echo "[ ] 6. Reason requirement..."
  read -p "    Enter reason for $operation: " reason
  if [ -z "$reason" ]; then
    echo "    Reason is required"
    return 1
  fi

  echo
  echo "✓ Pre-operation checklist complete"
  echo "Reason: $reason"
  echo
  read -p "Proceed with $operation? (yes/no): " final_confirm
  if [ "$final_confirm" != "yes" ]; then
    echo "Operation cancelled"
    return 1
  fi

  return 0
}

# Usage
if pre_operation_checklist "terminate" "my-workflow" "prod"; then
  echo "Safety checks passed - proceeding with operation"
fi
```

---

## Safety Patterns

### Dry-Run Pattern

```bash
dry_run_batch_operation() {
  local query=$1
  local operation=$2
  local env=${3:-staging}

  echo "=== Dry Run: $operation ==="

  # Count
  COUNT=$(temporal --env "$env" -o json --time-format iso workflow count \
    --query "$query" | jq '.count')

  echo "Would affect: $COUNT workflows"
  echo

  # Show sample
  if [ "$COUNT" -gt 0 ]; then
    echo "Sample workflows (first 10):"
    temporal --env "$env" -o json --time-format iso workflow list \
      --query "$query" \
      --limit 10 | \
      jq -r '.workflowExecutions[] | .execution.workflowId'
    echo

    # Show distribution
    echo "Workflow types:"
    temporal --env "$env" -o json --time-format iso workflow list \
      --query "$query" \
      --limit 100 | \
      jq -r '.workflowExecutions[] | .type.name' | \
      sort | uniq -c | sort -rn
  fi

  echo
  echo "This is a DRY RUN - no changes made"
}

# Usage
dry_run_batch_operation \
  "WorkflowType = 'TestFlow' AND ExecutionStatus = 'Failed'" \
  "reset" \
  "staging"
```

### Backup Before Operation

```bash
backup_workflow_before_operation() {
  local workflow_id=$1
  local env=${2:-staging}
  local backup_dir=${3:-.}

  BACKUP_FILE="$backup_dir/workflow-backup-${workflow_id}-$(date +%Y%m%d-%H%M%S).json"

  echo "Creating backup: $BACKUP_FILE"

  # Backup description
  temporal --env "$env" -o json --time-format iso workflow describe \
    --workflow-id "$workflow_id" > "$BACKUP_FILE"

  # Backup history
  temporal --env "$env" -o json --time-format iso workflow show \
    --workflow-id "$workflow_id" >> "$BACKUP_FILE"

  echo "Backup created successfully"
  echo "File: $BACKUP_FILE"
}

# Usage
backup_workflow_before_operation "critical-workflow" "prod" "/backups"
```

### Rate-Limited Batch Operations

```bash
batch_with_rate_limit() {
  local workflow_ids=("$@")
  local rate_limit=5  # workflows per second
  local delay=$(echo "scale=2; 1/$rate_limit" | bc)

  echo "Processing ${#workflow_ids[@]} workflows"
  echo "Rate limit: $rate_limit/second"

  for workflow_id in "${workflow_ids[@]}"; do
    echo "Processing: $workflow_id"

    # Perform operation here
    temporal --env staging -o json --time-format iso workflow cancel \
      --workflow-id "$workflow_id"

    # Rate limit
    sleep "$delay"
  done

  echo "Batch operation completed"
}
```

---

## Environment-Specific Safety

### Production Safety Layer

```bash
require_production_approval() {
  local env=$1
  local operation=$2

  if [ "$env" == "prod" ] || [ "$env" == "production" ]; then
    echo "⚠️  PRODUCTION ENVIRONMENT DETECTED"
    echo "Operation: $operation"
    echo

    # Require additional confirmation
    read -p "You are about to $operation in PRODUCTION. Type 'PRODUCTION' to confirm: " confirm

    if [ "$confirm" != "PRODUCTION" ]; then
      echo "Production operation cancelled"
      return 1
    fi

    # Optional: Require approval code
    read -p "Enter approval code (if required): " approval_code

    echo "Production operation approved"
  fi

  return 0
}

# Usage
if require_production_approval "prod" "batch reset"; then
  # Proceed with operation
  safe_batch_reset "$query" "$reason" "$reset_type" "prod"
fi
```

---

## See Also

- [Command Patterns](01-command-patterns.md) - Terminate and reset command syntax
- [Smart Patterns](06-smart-patterns.md) - Safe batch operation patterns
- [Error Handling](07-error-handling.md) - Handling operation failures
