# Smart Patterns Guide

Intelligent workflow management patterns: count-first optimization, auto-retry fallback, query validation, and smart history inspection.

## Table of Contents

- [Count-Before-List Optimization](#count-before-list-optimization)
- [Auto-Retry WorkflowId Fallback](#auto-retry-workflowid-fallback)
- [Query Pre-Validation](#query-pre-validation)
- [Smart History Inspection](#smart-history-inspection)
- [Safe Batch Operations](#safe-batch-operations)
- [Complete Patterns](#complete-patterns)

## Count-Before-List Optimization

**Problem:** Listing workflows without knowing result size can overwhelm context and waste resources.

**Solution:** Always count first, then adjust limit based on count.

### Basic Pattern

```bash
# ✅ CORRECT: Count first
COUNT=$(temporal --env prod -o json --time-format iso workflow count \
  --query "WorkflowType = 'OnboardingFlow'" | jq '.count')

echo "Found $COUNT workflows"

# Adjust limit based on count
if [ "$COUNT" -gt 50 ]; then
  LIMIT=10  # Large result set - sample only
elif [ "$COUNT" -gt 0 ]; then
  LIMIT=$COUNT  # Small result set - get all
else
  echo "No workflows found"
  exit 0
fi

# List with appropriate limit
temporal --env prod -o json --time-format iso workflow list \
  --query "WorkflowType = 'OnboardingFlow'" \
  --limit $LIMIT
```

### Function Implementation

```bash
smart_list_workflows() {
  local query=$1
  local env=${2:-staging}
  local max_limit=${3:-50}

  # Count first
  COUNT=$(temporal --env "$env" -o json --time-format iso workflow count \
    --query "$query" | jq '.count')

  echo "Query: $query"
  echo "Total matches: $COUNT"

  if [ "$COUNT" -eq 0 ]; then
    echo "No workflows found"
    return 0
  fi

  # Determine appropriate limit
  if [ "$COUNT" -le 10 ]; then
    LIMIT=$COUNT
    echo "Small result set - fetching all $LIMIT workflows"
  elif [ "$COUNT" -le $max_limit ]; then
    LIMIT=$COUNT
    echo "Fetching all $LIMIT workflows"
  else
    LIMIT=$max_limit
    echo "Large result set - fetching first $LIMIT of $COUNT workflows"
    echo "Use pagination to see more"
  fi

  # List with determined limit
  temporal --env "$env" -o json --time-format iso workflow list \
    --query "$query" \
    --limit $LIMIT
}

# Usage
smart_list_workflows "ExecutionStatus = 'Failed'" "prod" 50
```

### Decision Tree

```bash
count_and_decide() {
  local query=$1
  local env=${2:-staging}

  COUNT=$(temporal --env "$env" -o json --time-format iso workflow count \
    --query "$query" | jq '.count')

  echo "Found $COUNT matching workflows"

  if [ "$COUNT" -eq 0 ]; then
    echo "No workflows found - consider broadening query"
  elif [ "$COUNT" -le 10 ]; then
    echo "Small set - safe to list all"
    temporal --env "$env" -o json --time-format iso workflow list \
      --query "$query" --limit $COUNT
  elif [ "$COUNT" -le 100 ]; then
    echo "Medium set - listing all, but consider if you need them all"
    temporal --env "$env" -o json --time-format iso workflow list \
      --query "$query" --limit $COUNT
  else
    echo "Large set ($COUNT workflows) - showing first 20"
    echo "Consider refining query or use pagination"
    temporal --env "$env" -o json --time-format iso workflow list \
      --query "$query" --limit 20
  fi
}

# Usage
count_and_decide "WorkflowType STARTS_WITH 'patient'" "prod"
```

---

## Auto-Retry WorkflowId Fallback

**Problem:** Querying by `WorkflowType = 'X'` may return empty if workflows use WorkflowType as prefix in WorkflowId.

**Solution:** Auto-retry with `WorkflowId STARTS_WITH 'X'` when WorkflowType query is empty.

### Basic Fallback Pattern

```bash
query_with_fallback() {
  local workflow_name=$1
  local env=${2:-staging}

  # Try WorkflowType first
  echo "Trying WorkflowType = '$workflow_name'..."
  RESULT=$(temporal --env "$env" -o json --time-format iso workflow list \
    --query "WorkflowType = '$workflow_name'" \
    --limit 10)

  COUNT=$(echo "$RESULT" | jq '.workflowExecutions | length')

  if [ "$COUNT" -eq 0 ]; then
    echo "No results for WorkflowType, trying WorkflowId prefix..."

    # Fallback: WorkflowId STARTS_WITH
    RESULT=$(temporal --env "$env" -o json --time-format iso workflow list \
      --query "WorkflowId STARTS_WITH '$workflow_name'" \
      --limit 10)

    COUNT=$(echo "$RESULT" | jq '.workflowExecutions | length')
    echo "Fallback found $COUNT workflows"
    echo "(Used: WorkflowId STARTS_WITH '$workflow_name')"
  else
    echo "Found $COUNT workflows with WorkflowType"
  fi

  echo "$RESULT"
}

# Usage
query_with_fallback "OnboardingFlow" "prod"
```

### Advanced Fallback with Metadata

```bash
smart_workflow_search() {
  local workflow_name=$1
  local env=${2:-staging}
  local limit=${3:-10}

  echo "=== Smart Workflow Search: $workflow_name ==="

  # Try WorkflowType
  RESULT=$(temporal --env "$env" -o json --time-format iso workflow list \
    --query "WorkflowType = '$workflow_name'" \
    --limit "$limit" 2>&1)

  if [ $? -eq 0 ]; then
    COUNT=$(echo "$RESULT" | jq '.workflowExecutions | length')

    if [ "$COUNT" -gt 0 ]; then
      echo "✓ Found $COUNT workflows using WorkflowType"
      echo "  Query: WorkflowType = '$workflow_name'"
      echo "$RESULT"
      return 0
    fi
  fi

  # Fallback to WorkflowId
  echo "→ WorkflowType returned 0 results, trying WorkflowId..."

  RESULT=$(temporal --env "$env" -o json --time-format iso workflow list \
    --query "WorkflowId STARTS_WITH '$workflow_name'" \
    --limit "$limit" 2>&1)

  if [ $? -eq 0 ]; then
    COUNT=$(echo "$RESULT" | jq '.workflowExecutions | length')

    if [ "$COUNT" -gt 0 ]; then
      echo "✓ Found $COUNT workflows using WorkflowId prefix"
      echo "  Query: WorkflowId STARTS_WITH '$workflow_name'"
      echo "  Note: These workflows use workflow type as ID prefix"
      echo "$RESULT"
      return 0
    fi
  fi

  echo "✗ No workflows found with either WorkflowType or WorkflowId pattern"
  echo "  Suggestions:"
  echo "  - Check workflow name spelling"
  echo "  - Try broader query: WorkflowType STARTS_WITH '${workflow_name:0:5}'"
  echo "  - Check workflow exists: temporal workflow list --limit 5"
  return 1
}

# Usage
smart_workflow_search "PatientOnboarding" "prod" 20
```

---

## Query Pre-Validation

**Problem:** Invalid queries cause errors and wasted API calls.

**Solution:** Validate query syntax before execution.

### Basic Validation

```bash
validate_query() {
  local query=$1

  # Check if query is empty
  if [ -z "$query" ]; then
    echo "ERROR: Query is empty"
    return 1
  fi

  # Check balanced quotes
  quote_count=$(echo "$query" | grep -o "'" | wc -l)
  if [ $((quote_count % 2)) -ne 0 ]; then
    echo "ERROR: Unbalanced single quotes in query"
    echo "Query: $query"
    return 1
  fi

  # Check balanced parentheses
  open=$(echo "$query" | grep -o '(' | wc -l)
  close=$(echo "$query" | grep -o ')' | wc -l)
  if [ "$open" -ne "$close" ]; then
    echo "ERROR: Unbalanced parentheses in query"
    echo "Open: $open, Close: $close"
    return 1
  fi

  # Check for LIKE operator
  if echo "$query" | grep -qi '\bLIKE\b'; then
    echo "ERROR: LIKE operator not supported"
    echo "Use STARTS_WITH instead"
    echo "Example: WorkflowType STARTS_WITH 'prefix'"
    return 1
  fi

  # Check for wildcards
  if echo "$query" | grep -q '%\|\\*'; then
    echo "ERROR: Wildcards (%, *) not supported"
    echo "Use STARTS_WITH for prefix matching"
    return 1
  fi

  echo "✓ Query validation passed"
  return 0
}

# Usage
if validate_query "WorkflowType = 'MyFlow'"; then
  temporal --env staging -o json --time-format iso workflow list \
    --query "WorkflowType = 'MyFlow'"
fi
```

### Comprehensive Validation

```bash
validate_and_suggest() {
  local query=$1
  local errors=()
  local suggestions=()

  # Empty check
  if [ -z "$query" ]; then
    errors+=("Query is empty")
    suggestions+=("Provide a query like: WorkflowType = 'MyFlow'")
  fi

  # Quote balance
  quote_count=$(echo "$query" | grep -o "'" | wc -l)
  if [ $((quote_count % 2)) -ne 0 ]; then
    errors+=("Unbalanced single quotes")
    suggestions+=("Ensure all string values are properly quoted: 'value'")
  fi

  # Parenthesis balance
  open=$(echo "$query" | grep -o '(' | wc -l)
  close=$(echo "$query" | grep -o ')' | wc -l)
  if [ "$open" -ne "$close" ]; then
    errors+=("Unbalanced parentheses (open: $open, close: $close)")
    suggestions+=("Check that all opening parentheses have matching closing ones")
  fi

  # Unsupported operators
  if echo "$query" | grep -qi '\bLIKE\b'; then
    errors+=("LIKE operator not supported")
    suggestions+=("Use STARTS_WITH instead: WorkflowType STARTS_WITH 'prefix'")
  fi

  if echo "$query" | grep -qi '\bCONTAINS\b'; then
    errors+=("CONTAINS operator not supported")
    suggestions+=("Use STARTS_WITH for prefix matching")
  fi

  # Wildcards
  if echo "$query" | grep -q '%'; then
    errors+=("Wildcard '%' not supported")
    suggestions+=("Use STARTS_WITH for prefix matching")
  fi

  if echo "$query" | grep -q '\\*'; then
    errors+=("Wildcard '*' not supported")
    suggestions+=("Use STARTS_WITH for prefix matching")
  fi

  # Logical operators case
  if echo "$query" | grep -q ' and ' || echo "$query" | grep -q ' or '; then
    errors+=("Logical operators must be uppercase")
    suggestions+=("Use 'AND' instead of 'and', 'OR' instead of 'or'")
  fi

  # Report results
  if [ ${#errors[@]} -eq 0 ]; then
    echo "✓ Query validation passed"
    return 0
  else
    echo "✗ Query validation failed"
    echo
    echo "Errors:"
    for error in "${errors[@]}"; do
      echo "  - $error"
    done
    echo
    echo "Suggestions:"
    for suggestion in "${suggestions[@]}"; do
      echo "  - $suggestion"
    done
    return 1
  fi
}

# Usage
if validate_and_suggest "WorkflowType STARTS_WITH 'patient'"; then
  echo "Executing query..."
fi
```

---

## Smart History Inspection

**Problem:** Large histories overwhelm context.

**Solution:** Automatically choose inspection strategy based on size.

### Auto-Strategy Selection

```bash
smart_inspect_history() {
  local workflow_id=$1
  local env=${2:-staging}

  HISTORY=$(temporal --env "$env" -o json --time-format iso workflow show \
    --workflow-id "$workflow_id")

  EVENT_COUNT=$(echo "$HISTORY" | jq '.events | length')

  echo "=== Smart History Inspection: $workflow_id ==="
  echo "Total Events: $EVENT_COUNT"
  echo

  if [ "$EVENT_COUNT" -lt 100 ]; then
    # SMALL: Show all
    echo "Strategy: FULL (< 100 events)"
    echo "$HISTORY" | jq '.events'

  elif [ "$EVENT_COUNT" -lt 500 ]; then
    # MEDIUM: Show critical path
    echo "Strategy: CRITICAL PATH (100-500 events)"
    echo "$HISTORY" | jq '.events[] |
      select(.eventType |
        test("WorkflowExecutionStarted|WorkflowExecutionCompleted|WorkflowExecutionFailed|ActivityTaskFailed|Signal")
      )'

  else
    # LARGE: Show summary only
    echo "Strategy: SUMMARY (500+ events)"
    echo
    echo "Event Type Counts:"
    echo "$HISTORY" | jq '[.events[] | .eventType] | group_by(.) |
      map({type: .[0], count: length}) |
      sort_by(-.count)' | \
      jq -r '.[] | "  \(.type): \(.count)"'
    echo
    echo "First 5 Events:"
    echo "$HISTORY" | jq '.events[0:5] | .[] | {eventId, eventType}'
    echo
    echo "Last 5 Events:"
    echo "$HISTORY" | jq '.events[-5:] | .[] | {eventId, eventType}'
    echo
    echo "For detailed analysis:"
    echo "  - Use pagination: jq '.events[0:100]'"
    echo "  - Filter by type: jq '.events[] | select(.eventType | contains(\"Failed\"))'"
    echo "  - See: references/05-history-filtering.md"
  fi
}

# Usage
smart_inspect_history "long-running-workflow" "prod"
```

---

## Safe Batch Operations

**Problem:** Batch operations (reset, terminate) can affect many workflows.

**Solution:** Validate, count, confirm before executing.

### Safe Batch Reset

```bash
safe_batch_reset() {
  local query=$1
  local reason=$2
  local reset_type=${3:-FirstWorkflowTask}
  local env=${4:-staging}

  echo "=== Safe Batch Reset ==="

  # Validate inputs
  if [ -z "$query" ]; then
    echo "ERROR: Query is required for batch operations"
    return 1
  fi

  if [ -z "$reason" ]; then
    echo "ERROR: Reason is required for batch operations"
    echo "Example reason: 'Reset after bug fix in v2.1.0'"
    return 1
  fi

  # Validate reset type
  if [[ ! "$reset_type" =~ ^(FirstWorkflowTask|LastWorkflowTask|BuildId)$ ]]; then
    echo "ERROR: Invalid reset type for batch operations"
    echo "Allowed: FirstWorkflowTask, LastWorkflowTask, BuildId"
    return 1
  fi

  # Count affected workflows
  echo "Counting affected workflows..."
  COUNT=$(temporal --env "$env" -o json --time-format iso workflow count \
    --query "$query" | jq '.count')

  if [ "$COUNT" -eq 0 ]; then
    echo "No workflows match query - aborting"
    return 0
  fi

  # Show details
  echo
  echo "Batch Reset Configuration:"
  echo "  Environment: $env"
  echo "  Query: $query"
  echo "  Affected Workflows: $COUNT"
  echo "  Reset Type: $reset_type"
  echo "  Reason: $reason"
  echo

  # Confirm
  read -p "This will reset $COUNT workflows. Continue? (type 'yes' to confirm): " confirm

  if [ "$confirm" != "yes" ]; then
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
}

# Usage
safe_batch_reset \
  "WorkflowType = 'BuggyFlow' AND ExecutionStatus = 'Failed'" \
  "Reset after bug fix in version 2.0.1" \
  "FirstWorkflowTask" \
  "staging"
```

---

## Complete Patterns

### All-in-One Smart Query

```bash
smart_query_workflow() {
  local query=$1
  local env=${2:-staging}
  local max_limit=${3:-50}

  echo "=== Smart Workflow Query ==="

  # 1. Validate query
  if ! validate_query "$query"; then
    return 1
  fi

  # 2. Count workflows
  echo "Counting workflows..."
  COUNT=$(temporal --env "$env" -o json --time-format iso workflow count \
    --query "$query" | jq '.count')

  echo "Found: $COUNT workflows"

  if [ "$COUNT" -eq 0 ]; then
    # 3. Try fallback if query was WorkflowType
    if echo "$query" | grep -q "WorkflowType = "; then
      workflow_name=$(echo "$query" | grep -oP "WorkflowType = '\K[^']+")
      echo "Trying WorkflowId fallback..."

      FALLBACK_QUERY="WorkflowId STARTS_WITH '$workflow_name'"
      COUNT=$(temporal --env "$env" -o json --time-format iso workflow count \
        --query "$FALLBACK_QUERY" | jq '.count')

      if [ "$COUNT" -gt 0 ]; then
        echo "Fallback found $COUNT workflows"
        query=$FALLBACK_QUERY
      else
        echo "No workflows found with either query"
        return 0
      fi
    else
      echo "No workflows found"
      return 0
    fi
  fi

  # 4. Determine limit
  if [ "$COUNT" -le "$max_limit" ]; then
    LIMIT=$COUNT
  else
    LIMIT=$max_limit
    echo "Limiting to first $LIMIT of $COUNT workflows"
  fi

  # 5. Execute query
  echo "Fetching workflows..."
  temporal --env "$env" -o json --time-format iso workflow list \
    --query "$query" \
    --limit "$LIMIT"
}

# Usage
smart_query_workflow "WorkflowType = 'OnboardingFlow'" "prod" 50
```

### Complete Workflow Inspector

```bash
inspect_workflow() {
  local workflow_id=$1
  local env=${2:-staging}

  echo "=== Complete Workflow Inspection: $workflow_id ==="
  echo

  # 1. Get workflow description
  echo "--- Workflow Status ---"
  DESC=$(temporal --env "$env" -o json --time-format iso workflow describe \
    --workflow-id "$workflow_id")

  echo "$DESC" | jq '{
    status: .workflowExecutionInfo.status,
    type: .workflowExecutionInfo.type.name,
    startTime: .workflowExecutionInfo.startTime,
    closeTime: .workflowExecutionInfo.closeTime
  }'
  echo

  # 2. Get history with smart filtering
  echo "--- Event History ---"
  HISTORY=$(temporal --env "$env" -o json --time-format iso workflow show \
    --workflow-id "$workflow_id")

  EVENT_COUNT=$(echo "$HISTORY" | jq '.events | length')
  echo "Total Events: $EVENT_COUNT"

  if [ "$EVENT_COUNT" -lt 100 ]; then
    echo "Showing all events:"
    echo "$HISTORY" | jq '.events[] | {eventId, eventType}'
  else
    echo "Event summary:"
    echo "$HISTORY" | jq '[.events[] | .eventType] | group_by(.) |
      map({type: .[0], count: length})' | \
      jq -r '.[] | "  \(.type): \(.count)"'
  fi
  echo

  # 3. Check for failures
  FAILURES=$(echo "$HISTORY" | jq '[.events[] | select(.eventType | contains("Failed"))] | length')
  if [ "$FAILURES" -gt 0 ]; then
    echo "--- Failures Detected ($FAILURES) ---"
    echo "$HISTORY" | jq '.events[] | select(.eventType | contains("Failed")) |
      {eventId, eventType}'
  fi
}

# Usage
inspect_workflow "patient-onboard-123" "prod"
```

## See Also

- [Query Construction](02-query-construction.md) - Building valid queries
- [History Filtering](05-history-filtering.md) - Advanced filtering techniques
- [Error Handling](07-error-handling.md) - Handling validation errors
- [Safety Checks](08-safety-checks.md) - Comprehensive safety validations
