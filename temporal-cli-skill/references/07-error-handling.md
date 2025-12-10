# Error Handling Guide

Common Temporal CLI errors, their causes, and recovery strategies.

## Table of Contents

- [Query Syntax Errors](#query-syntax-errors)
- [Operator Errors](#operator-errors)
- [Field Errors](#field-errors)
- [Value Type Errors](#value-type-errors)
- [Connection Errors](#connection-errors)
- [Workflow Not Found](#workflow-not-found)
- [Permission Errors](#permission-errors)
- [Timeout Errors](#timeout-errors)
- [Non-Deterministic Workflow Errors](#non-deterministic-workflow-errors)

## Query Syntax Errors

### Error: Unbalanced Quotes

**Error message:**
```
parse error: unexpected end of string
```

**Cause:** Missing closing quote in query string

**Example:**
```bash
# ❌ WRONG
temporal --env prod -o json --time-format iso workflow list \
  --query "WorkflowType = 'MyFlow"
```

**Fix:**
```bash
# ✅ CORRECT
temporal --env prod -o json --time-format iso workflow list \
  --query "WorkflowType = 'MyFlow'"
```

**Detection:**
```bash
check_quotes() {
  local query=$1
  quote_count=$(echo "$query" | grep -o "'" | wc -l)

  if [ $((quote_count % 2)) -ne 0 ]; then
    echo "ERROR: Unbalanced quotes (found $quote_count single quotes)"
    echo "Ensure all string values are properly quoted"
    return 1
  fi
  return 0
}
```

---

### Error: Unbalanced Parentheses

**Error message:**
```
parse error: unmatched parenthesis
```

**Cause:** Missing opening or closing parenthesis

**Example:**
```bash
# ❌ WRONG
temporal --env prod -o json --time-format iso workflow list \
  --query "(WorkflowType = 'A' AND ExecutionStatus = 'Running'"
```

**Fix:**
```bash
# ✅ CORRECT
temporal --env prod -o json --time-format iso workflow list \
  --query "(WorkflowType = 'A' AND ExecutionStatus = 'Running')"
```

**Detection:**
```bash
check_parentheses() {
  local query=$1
  open=$(echo "$query" | grep -o '(' | wc -l)
  close=$(echo "$query" | grep -o ')' | wc -l)

  if [ "$open" -ne "$close" ]; then
    echo "ERROR: Unbalanced parentheses (open: $open, close: $close)"
    return 1
  fi
  return 0
}
```

---

## Operator Errors

### Error: operator 'like' not allowed

**Error message:**
```
operator 'like' not allowed
```

**Cause:** LIKE operator is not supported by Temporal

**Example:**
```bash
# ❌ WRONG
temporal --env prod -o json --time-format iso workflow list \
  --query "WorkflowType LIKE '%patient%'"
```

**Fix:**
```bash
# ✅ CORRECT: Use STARTS_WITH
temporal --env prod -o json --time-format iso workflow list \
  --query "WorkflowType STARTS_WITH 'patient'"
```

**Detection and Recovery:**
```bash
fix_like_operator() {
  local query=$1

  if echo "$query" | grep -qi '\bLIKE\b'; then
    echo "ERROR: LIKE operator not supported"
    echo "Original query: $query"

    # Suggest STARTS_WITH
    if echo "$query" | grep -q "LIKE '%.*%'"; then
      echo "Hint: LIKE '%text%' not supported. Use STARTS_WITH for prefix matching"
      echo "Example: WorkflowType STARTS_WITH 'text'"
    elif echo "$query" | grep -q "LIKE '.*%'"; then
      pattern=$(echo "$query" | grep -oP "LIKE '\K[^%]+")
      echo "Suggested fix: ${query//LIKE \'$pattern%\'/STARTS_WITH \'$pattern\'}"
    fi
    return 1
  fi
  return 0
}
```

---

### Error: operator 'contains' not allowed

**Error message:**
```
operator 'contains' not allowed
```

**Cause:** CONTAINS operator is not supported

**Example:**
```bash
# ❌ WRONG
temporal --env staging -o json --time-format iso workflow list \
  --query "WorkflowId CONTAINS 'patient'"
```

**Fix:**
```bash
# ✅ CORRECT: Use STARTS_WITH
temporal --env staging -o json --time-format iso workflow list \
  --query "WorkflowId STARTS_WITH 'patient'"
```

---

### Error: Wildcard Not Supported

**Error message:**
```
invalid character '%' in string literal
```

**Cause:** Wildcards (%, *) are not supported

**Example:**
```bash
# ❌ WRONG
temporal --env prod -o json --time-format iso workflow list \
  --query "WorkflowType = '*patient*'"
```

**Fix:**
```bash
# ✅ CORRECT
temporal --env prod -o json --time-format iso workflow list \
  --query "WorkflowType STARTS_WITH 'patient'"
```

**Detection:**
```bash
check_wildcards() {
  local query=$1

  if echo "$query" | grep -q '%'; then
    echo "ERROR: Wildcard '%' not supported"
    echo "Use STARTS_WITH for prefix matching"
    return 1
  fi

  if echo "$query" | grep -q '\\*'; then
    echo "ERROR: Wildcard '*' not supported"
    echo "Use STARTS_WITH for prefix matching"
    return 1
  fi

  return 0
}
```

---

## Field Errors

### Error: Unknown Field

**Error message:**
```
unknown field: CustomField
```

**Cause:** Field name not recognized (typo or not configured as custom search attribute)

**Example:**
```bash
# ❌ WRONG (field doesn't exist)
temporal --env prod -o json --time-format iso workflow list \
  --query "CustomField = 'value'"
```

**Fix:**
```bash
# ✅ CORRECT: Use valid field name
temporal --env prod -o json --time-format iso workflow list \
  --query "WorkflowType = 'value'"

# OR configure CustomField in Temporal cluster
```

**Valid standard fields:**
- `WorkflowId`
- `WorkflowType`
- `RunId`
- `ExecutionStatus`
- `StartTime`
- `CloseTime`
- `ExecutionTime`
- `BuildIds`
- `TaskQueue`

---

### Error: Case-Sensitive Field Names

**Error message:**
```
unknown field: workflowtype
```

**Cause:** Field names are case-sensitive

**Example:**
```bash
# ❌ WRONG
temporal --env staging -o json --time-format iso workflow list \
  --query "workflowtype = 'MyFlow'"
```

**Fix:**
```bash
# ✅ CORRECT: Use proper casing
temporal --env staging -o json --time-format iso workflow list \
  --query "WorkflowType = 'MyFlow'"
```

---

## Value Type Errors

### Error: Type Mismatch (String for Number)

**Error message:**
```
type mismatch: expected int, got string
```

**Cause:** Using quotes on numeric fields

**Example:**
```bash
# ❌ WRONG (quotes on number)
temporal --env prod -o json --time-format iso workflow list \
  --query "Priority = '1'"
```

**Fix:**
```bash
# ✅ CORRECT (no quotes)
temporal --env prod -o json --time-format iso workflow list \
  --query "Priority = 1"
```

---

### Error: Invalid Boolean Value

**Error message:**
```
invalid boolean value: True
```

**Cause:** Boolean must be lowercase

**Example:**
```bash
# ❌ WRONG
temporal --env staging -o json --time-format iso workflow list \
  --query "IsUrgent = True"
```

**Fix:**
```bash
# ✅ CORRECT (lowercase)
temporal --env staging -o json --time-format iso workflow list \
  --query "IsUrgent = true"
```

---

### Error: Invalid Datetime Format

**Error message:**
```
invalid datetime format
```

**Cause:** Datetime not in ISO 8601 format or missing quotes

**Example:**
```bash
# ❌ WRONG
temporal --env prod -o json --time-format iso workflow list \
  --query "StartTime > 2025-01-01"
```

**Fix:**
```bash
# ✅ CORRECT (ISO 8601 with quotes)
temporal --env prod -o json --time-format iso workflow list \
  --query "StartTime > '2025-01-01T00:00:00Z'"
```

---

## Connection Errors

### Error: connection refused

**Error message:**
```
connection refused
```

**Cause:** Cannot connect to Temporal server

**Troubleshooting:**
```bash
# 1. Check Temporal CLI config
cat ~/.config/temporalio/temporal.yaml

# 2. Test connection
temporal env get --env staging

# 3. Check if server is running
ping temporal.example.com

# 4. Verify environment name
temporal env list
```

**Fix:**
```bash
# Update environment configuration
temporal env set staging --address temporal.staging.example.com:7233
```

---

### Error: environment not found

**Error message:**
```
environment "prod" not found
```

**Cause:** Environment not configured in temporal.yaml

**Troubleshooting:**
```bash
# List configured environments
temporal env list

# Add missing environment
temporal env set prod --address temporal.prod.example.com:7233
```

---

## Workflow Not Found

### Error: workflow execution not found

**Error message:**
```
workflow execution not found
```

**Cause:** WorkflowId doesn't exist or wrong environment

**Troubleshooting:**
```bash
# 1. Verify WorkflowId
echo "Searching for workflow..."

# 2. Try listing to find it
temporal --env staging -o json --time-format iso workflow list \
  --query "WorkflowId STARTS_WITH 'patient'" \
  --limit 10

# 3. Check different environment
temporal --env prod -o json --time-format iso workflow describe \
  --workflow-id "my-workflow"
```

**Pattern:**
```bash
find_workflow() {
  local workflow_id=$1

  for env in staging prod dev; do
    echo "Checking $env..."
    if temporal --env "$env" -o json --time-format iso workflow describe \
      --workflow-id "$workflow_id" >/dev/null 2>&1; then
      echo "Found in: $env"
      return 0
    fi
  done

  echo "Workflow not found in any environment"
  return 1
}

# Usage
find_workflow "patient-onboard-123"
```

---

## Permission Errors

### Error: permission denied

**Error message:**
```
permission denied
```

**Cause:** Insufficient permissions for the operation

**Troubleshooting:**
```bash
# 1. Check your user permissions
temporal user get

# 2. Verify namespace access
temporal namespace describe

# 3. Contact admin for permissions
```

---

## Timeout Errors

### Error: context deadline exceeded

**Error message:**
```
context deadline exceeded
```

**Cause:** Operation took too long

**Recovery:**
```bash
# Retry with exponential backoff
retry_with_backoff() {
  local max_attempts=3
  local timeout=30
  local attempt=1

  while [ $attempt -le $max_attempts ]; do
    echo "Attempt $attempt of $max_attempts (timeout: ${timeout}s)"

    if timeout $timeout temporal --env staging -o json --time-format iso workflow list --limit 10; then
      return 0
    fi

    if [ $attempt -lt $max_attempts ]; then
      sleep $((2 ** attempt))
      timeout=$((timeout * 2))
    fi

    attempt=$((attempt + 1))
  done

  echo "Failed after $max_attempts attempts"
  return 1
}
```

---

## Error Recovery Patterns

### Comprehensive Error Handler

```bash
execute_with_error_handling() {
  local cmd=$1

  # Execute command and capture output
  OUTPUT=$(eval "$cmd" 2>&1)
  EXIT_CODE=$?

  if [ $EXIT_CODE -eq 0 ]; then
    echo "$OUTPUT"
    return 0
  fi

  # Parse error and provide helpful message
  if echo "$OUTPUT" | grep -q "operator 'like' not allowed"; then
    echo "ERROR: LIKE operator not supported"
    echo "Use STARTS_WITH instead"
    echo "Example: WorkflowType STARTS_WITH 'prefix'"

  elif echo "$OUTPUT" | grep -q "unknown field"; then
    field=$(echo "$OUTPUT" | grep -oP "unknown field: \K\w+")
    echo "ERROR: Unknown field '$field'"
    echo "Valid fields: WorkflowType, WorkflowId, ExecutionStatus, StartTime, CloseTime"

  elif echo "$OUTPUT" | grep -q "unbalanced"; then
    echo "ERROR: Query syntax error - check quotes and parentheses"

  elif echo "$OUTPUT" | grep -q "connection refused"; then
    echo "ERROR: Cannot connect to Temporal server"
    echo "Check environment configuration: temporal env list"

  elif echo "$OUTPUT" | grep -q "not found"; then
    echo "ERROR: Workflow or environment not found"
    echo "Verify WorkflowId and environment name"

  else
    echo "ERROR: $OUTPUT"
  fi

  return $EXIT_CODE
}

# Usage
execute_with_error_handling "temporal --env staging -o json --time-format iso workflow list --query \"WorkflowType LIKE '%flow%'\""
```

### Smart Retry Logic

```bash
smart_retry() {
  local cmd=$1
  local max_attempts=3
  local attempt=1

  while [ $attempt -le $max_attempts ]; do
    echo "Attempt $attempt of $max_attempts"

    OUTPUT=$(eval "$cmd" 2>&1)
    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ]; then
      echo "$OUTPUT"
      return 0
    fi

    # Don't retry on syntax errors
    if echo "$OUTPUT" | grep -qE "operator.*not allowed|unknown field|parse error"; then
      echo "Syntax error - not retrying"
      echo "$OUTPUT"
      return $EXIT_CODE
    fi

    # Retry on connection/timeout errors
    if echo "$OUTPUT" | grep -qE "connection|timeout|deadline"; then
      echo "Transient error - retrying..."
      sleep $((2 ** attempt))
      attempt=$((attempt + 1))
    else
      echo "$OUTPUT"
      return $EXIT_CODE
    fi
  done

  echo "Failed after $max_attempts attempts"
  return 1
}
```

---

## Non-Deterministic Workflow Errors

### Finding Workflows with Non-Deterministic Errors

**Key insight**: Workflows with non-deterministic errors remain in `Running` status, not `Failed`. They're stuck and keep retrying the same WorkflowTask.

**Use `TemporalReportedProblems` to find them:**
```bash
# Find running workflows with WorkflowTask failures
temporal --env prod -o json --time-format iso workflow list \
  --query "ExecutionStatus = 'Running' AND TemporalReportedProblems IN ('category=WorkflowTaskFailed', 'category=WorkflowTaskTimedOut')" \
  --limit 20
```

### Understanding the Error

```bash
# Get the last WorkflowTaskFailed event
temporal --env prod -o json --time-format iso workflow show \
  --workflow-id "workflow-id-here" | \
  jq '[.events[] | select(.eventType == "EVENT_TYPE_WORKFLOW_TASK_FAILED")] | .[-1]'
```

**Common non-deterministic error messages:**
```
[TMPRL1100] During replay, a matching ChildWorkflow command was expected...
[TMPRL1100] During replay, a matching Activity command was expected...
```

**The error indicates:**
- The workflow code has changed incompatibly
- A child workflow or activity was added/removed/reordered
- The workflow ID in the error message shows which command was expected

### Resolution Options

1. **Reset workflow** to before the problematic change:
```bash
temporal --env prod -o json --time-format iso workflow reset \
  --workflow-id "workflow-id" \
  --type LastWorkflowTask \
  --reason "Reset due to non-deterministic error after code change"
```

2. **Terminate and restart** if reset isn't viable:
```bash
temporal --env prod -o json --time-format iso workflow terminate \
  --workflow-id "workflow-id" \
  --reason "Non-deterministic error - workflow code incompatible"
```

3. **Deploy compatible code** that restores the expected behavior

## See Also

- [Query Construction](02-query-construction.md) - Valid query syntax
- [Smart Patterns](06-smart-patterns.md) - Query validation before execution
- [Command Patterns](01-command-patterns.md) - Correct command usage
