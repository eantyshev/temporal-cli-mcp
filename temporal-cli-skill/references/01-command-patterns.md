# Temporal CLI Command Patterns

Complete reference for all Temporal CLI workflow operations with bash examples using temporal, base64, and jq.

## Table of Contents

- [Global Flags Pattern](#global-flags-pattern)
- [List Workflows](#list-workflows)
- [Count Workflows](#count-workflows)
- [Describe Workflow](#describe-workflow)
- [Get Workflow History](#get-workflow-history)
- [Start Workflow](#start-workflow)
- [Signal Workflow](#signal-workflow)
- [Query Workflow](#query-workflow)
- [Cancel Workflow](#cancel-workflow)
- [Terminate Workflow](#terminate-workflow)
- [Reset Workflow](#reset-workflow)
- [Trace Workflow](#trace-workflow)
- [Error Handling](#error-handling)

## Global Flags Pattern

**CRITICAL:** ALL Temporal CLI commands MUST use these global flags:

```bash
temporal --env <environment> -o json --time-format iso workflow <operation> [args...]
```

**Flag breakdown:**
- `--env <env>` - Specifies Temporal environment from `~/.config/temporalio/temporal.yaml`
- `-o json` - Output in JSON format (enables parsing with jq)
- `--time-format iso` - Use ISO 8601 format for timestamps

**Example environments:** `staging`, `prod`, `dev`, `local`

---

## List Workflows

List workflow executions with optional filtering.

### Basic List

```bash
temporal --env staging -o json --time-format iso workflow list --limit 10
```

### With Query Filter

```bash
temporal --env prod -o json --time-format iso workflow list \
  --query "WorkflowType = 'OnboardingFlow'" \
  --limit 50
```

### Parse Results with jq

```bash
# Extract workflow IDs and statuses
temporal --env staging -o json --time-format iso workflow list --limit 10 | \
  jq '.workflowExecutions[] | {id: .execution.workflowId, status: .status}'
```

### Pretty Print Workflow List

```bash
temporal --env prod -o json --time-format iso workflow list \
  --query "ExecutionStatus = 'Running'" \
  --limit 20 | \
  jq -r '.workflowExecutions[] | "\(.execution.workflowId) - \(.status) - \(.startTime)"'
```

### Filter Specific Fields

```bash
# Get only workflow IDs
temporal --env staging -o json --time-format iso workflow list --limit 10 | \
  jq -r '.workflowExecutions[].execution.workflowId'
```

---

## Count Workflows

**BEST PRACTICE:** Always count before listing to understand result scope.

### Basic Count

```bash
temporal --env prod -o json --time-format iso workflow count
```

### Count with Query

```bash
temporal --env prod -o json --time-format iso workflow count \
  --query "ExecutionStatus = 'Failed'"
```

### Count-Then-List Pattern

```bash
# Get count to understand scope
COUNT=$(temporal --env prod -o json --time-format iso workflow count \
  --query "WorkflowType = 'OnboardingFlow'" | jq '.count')

echo "Found $COUNT workflows"

# Adjust limit based on count
if [ "$COUNT" -gt 50 ]; then
  echo "Large result set - limiting to 10"
  LIMIT=10
else
  LIMIT=$COUNT
fi

# List with appropriate limit
temporal --env prod -o json --time-format iso workflow list \
  --query "WorkflowType = 'OnboardingFlow'" \
  --limit $LIMIT
```

### Extract Count Value

```bash
# Store count as variable
FAILED_COUNT=$(temporal --env staging -o json --time-format iso workflow count \
  --query "ExecutionStatus = 'Failed'" | jq '.count')

echo "There are $FAILED_COUNT failed workflows"
```

---

## Describe Workflow

Get detailed information about a specific workflow execution.

### Basic Describe

```bash
temporal --env staging -o json --time-format iso workflow describe \
  --workflow-id "patient-onboard-12345"
```

### Describe Specific Run

```bash
temporal --env prod -o json --time-format iso workflow describe \
  --workflow-id "order-processing-456" \
  --run-id "abc123-def456-ghi789"
```

### Extract Workflow Status

```bash
temporal --env staging -o json --time-format iso workflow describe \
  --workflow-id "my-workflow-123" | \
  jq -r '.workflowExecutionInfo.status'
```

### Get Workflow Type

```bash
temporal --env prod -o json --time-format iso workflow describe \
  --workflow-id "order-456" | \
  jq -r '.workflowExecutionInfo.type.name'
```

### Check if Workflow is Running

```bash
STATUS=$(temporal --env staging -o json --time-format iso workflow describe \
  --workflow-id "my-workflow" | jq -r '.workflowExecutionInfo.status')

if [ "$STATUS" == "Running" ]; then
  echo "Workflow is still running"
else
  echo "Workflow status: $STATUS"
fi
```

---

## Get Workflow History

Retrieve complete event history for a workflow execution.

### Basic History

```bash
temporal --env staging -o json --time-format iso workflow show \
  --workflow-id "patient-onboard-12345"
```

### History for Specific Run

```bash
temporal --env prod -o json --time-format iso workflow show \
  --workflow-id "order-processing-456" \
  --run-id "abc123-def456-ghi789"
```

### Count Events in History

```bash
temporal --env staging -o json --time-format iso workflow show \
  --workflow-id "my-workflow" | \
  jq '.events | length'
```

### Show First 10 Events

```bash
temporal --env prod -o json --time-format iso workflow show \
  --workflow-id "order-456" | \
  jq '.events[0:10]'
```

### List Event Types

```bash
temporal --env staging -o json --time-format iso workflow show \
  --workflow-id "my-workflow" | \
  jq '[.events[] | .eventType] | unique'
```

### Find Failure Events

```bash
temporal --env prod -o json --time-format iso workflow show \
  --workflow-id "failed-workflow" | \
  jq '.events[] | select(.eventType | contains("Failed"))'
```

---

## Start Workflow

Create a new workflow execution.

### Basic Start

```bash
temporal --env staging -o json --time-format iso workflow start \
  --type "OnboardingFlow" \
  --task-queue "patient-workflows"
```

### Start with Workflow ID

```bash
temporal --env staging -o json --time-format iso workflow start \
  --type "OnboardingFlow" \
  --task-queue "patient-workflows" \
  --workflow-id "patient-onboard-$(date +%s)"
```

### Start with Input Data

```bash
temporal --env prod -o json --time-format iso workflow start \
  --type "OrderProcessing" \
  --task-queue "order-queue" \
  --workflow-id "order-$(uuidgen)" \
  --input '{"customerId": "cust-123", "amount": 99.99, "items": ["item1", "item2"]}'
```

### Start with Complex Input

```bash
# Create input JSON
INPUT=$(cat <<'EOF'
{
  "customer": {
    "id": "cust-456",
    "email": "customer@example.com"
  },
  "plan": "premium",
  "metadata": {
    "source": "web",
    "campaign": "summer2025"
  }
}
EOF
)

temporal --env staging -o json --time-format iso workflow start \
  --type "OnboardingFlow" \
  --task-queue "patient-workflows" \
  --workflow-id "onboard-$(date +%s)" \
  --input "$INPUT"
```

### Extract Started Workflow ID

```bash
RESULT=$(temporal --env staging -o json --time-format iso workflow start \
  --type "MyWorkflow" \
  --task-queue "my-queue")

WORKFLOW_ID=$(echo "$RESULT" | jq -r '.workflowId')
echo "Started workflow: $WORKFLOW_ID"
```

---

## Signal Workflow

Send a signal to a running workflow.

### Basic Signal

```bash
temporal --env prod -o json --time-format iso workflow signal \
  --workflow-id "order-processing-456" \
  --name "approvalReceived"
```

### Signal with Input Data

```bash
temporal --env staging -o json --time-format iso workflow signal \
  --workflow-id "patient-onboard-123" \
  --name "documentUploaded" \
  --input '{"documentType": "insurance", "documentId": "doc-789"}'
```

### Signal with Complex Data

```bash
SIGNAL_DATA=$(cat <<'EOF'
{
  "approver": "manager@example.com",
  "approved": true,
  "comments": "Looks good, approved",
  "timestamp": "2025-11-22T10:30:00Z"
}
EOF
)

temporal --env prod -o json --time-format iso workflow signal \
  --workflow-id "order-456" \
  --name "manualApproval" \
  --input "$SIGNAL_DATA"
```

### Signal Multiple Workflows

```bash
# Get list of workflow IDs
WORKFLOW_IDS=$(temporal --env staging -o json --time-format iso workflow list \
  --query "WorkflowType = 'OnboardingFlow' AND ExecutionStatus = 'Running'" \
  --limit 100 | \
  jq -r '.workflowExecutions[].execution.workflowId')

# Signal each one
for WF_ID in $WORKFLOW_IDS; do
  echo "Signaling $WF_ID"
  temporal --env staging -o json --time-format iso workflow signal \
    --workflow-id "$WF_ID" \
    --name "configUpdate" \
    --input '{"version": "2.0"}'
done
```

---

## Query Workflow

Query the current state of a running workflow.

### Basic Query

```bash
temporal --env staging -o json --time-format iso workflow query \
  --workflow-id "patient-onboard-12345" \
  --type "getStatus"
```

### Query with Input

```bash
temporal --env prod -o json --time-format iso workflow query \
  --workflow-id "order-456" \
  --type "getOrderDetails" \
  --input '{"includeHistory": true}'
```

### Parse Query Result

```bash
temporal --env staging -o json --time-format iso workflow query \
  --workflow-id "my-workflow" \
  --type "getCurrentState" | \
  jq '.queryResult'
```

### Query and Extract Specific Field

```bash
PROGRESS=$(temporal --env prod -o json --time-format iso workflow query \
  --workflow-id "long-running-workflow" \
  --type "getProgress" | \
  jq -r '.queryResult.percentComplete')

echo "Workflow is $PROGRESS% complete"
```

---

## Cancel Workflow

Request graceful cancellation of a workflow.

### Basic Cancel

```bash
temporal --env staging -o json --time-format iso workflow cancel \
  --workflow-id "test-workflow-123"
```

### Cancel Specific Run

```bash
temporal --env prod -o json --time-format iso workflow cancel \
  --workflow-id "order-456" \
  --run-id "abc123-def456"
```

### Cancel with Verification

```bash
WORKFLOW_ID="my-workflow-789"

# Verify it's running first
STATUS=$(temporal --env staging -o json --time-format iso workflow describe \
  --workflow-id "$WORKFLOW_ID" | jq -r '.workflowExecutionInfo.status')

if [ "$STATUS" == "Running" ]; then
  echo "Cancelling workflow..."
  temporal --env staging -o json --time-format iso workflow cancel \
    --workflow-id "$WORKFLOW_ID"
else
  echo "Workflow is not running (status: $STATUS)"
fi
```

---

## Terminate Workflow

Force immediate termination of a workflow (destructive operation).

### Basic Terminate

```bash
temporal --env staging -o json --time-format iso workflow terminate \
  --workflow-id "stuck-workflow-789" \
  --reason "Workflow stuck in infinite loop"
```

### Terminate Specific Run

```bash
temporal --env prod -o json --time-format iso workflow terminate \
  --workflow-id "problem-workflow" \
  --run-id "abc123" \
  --reason "Corrupted state detected, terminating"
```

### Safe Termination Pattern

```bash
WORKFLOW_ID="potentially-stuck-workflow"
REASON="Manual termination due to timeout - workflow exceeded SLA"

# Get current status
STATUS=$(temporal --env staging -o json --time-format iso workflow describe \
  --workflow-id "$WORKFLOW_ID" | jq -r '.workflowExecutionInfo.status')

echo "Current status: $STATUS"
read -p "Terminate this workflow? (yes/no): " confirm

if [ "$confirm" == "yes" ]; then
  temporal --env staging -o json --time-format iso workflow terminate \
    --workflow-id "$WORKFLOW_ID" \
    --reason "$REASON"
  echo "Workflow terminated"
else
  echo "Termination cancelled"
fi
```

---

## Reset Workflow

Reset a workflow execution to a previous point (advanced operation).

### Reset to Last Event

```bash
temporal --env staging -o json --time-format iso workflow reset \
  --workflow-id "failed-workflow-456" \
  --reason "Resetting after dependency service recovery"
```

### Reset to Specific Event

```bash
temporal --env prod -o json --time-format iso workflow reset \
  --workflow-id "order-789" \
  --event-id 42 \
  --reason "Resetting to before problematic activity execution"
```

### Reset with Run ID

```bash
temporal --env staging -o json --time-format iso workflow reset \
  --workflow-id "patient-onboard-123" \
  --run-id "abc123-def456" \
  --reason "Resetting specific run after bug fix"
```

### Batch Reset (DANGEROUS)

```bash
# Reset all failed workflows of a specific type
temporal --env staging -o json --time-format iso workflow reset \
  --query "WorkflowType = 'BuggyWorkflow' AND ExecutionStatus = 'Failed'" \
  --type FirstWorkflowTask \
  --reason "Mass reset after bug fix in version 2.1.0" \
  --yes
```

### Safe Batch Reset with Count

```bash
QUERY="WorkflowType = 'ProblematicFlow' AND ExecutionStatus = 'Failed'"
REASON="Reset after service dependency fix"

# Count affected workflows
COUNT=$(temporal --env staging -o json --time-format iso workflow count \
  --query "$QUERY" | jq '.count')

echo "This will reset $COUNT workflows"
read -p "Continue? (yes/no): " confirm

if [ "$confirm" == "yes" ]; then
  temporal --env staging -o json --time-format iso workflow reset \
    --query "$QUERY" \
    --type FirstWorkflowTask \
    --reason "$REASON" \
    --yes
else
  echo "Batch reset cancelled"
fi
```

### Reset Types

```bash
# Reset to FirstWorkflowTask (most common)
temporal --env staging -o json --time-format iso workflow reset \
  --workflow-id "my-workflow" \
  --type FirstWorkflowTask \
  --reason "Reset to beginning"

# Reset to LastWorkflowTask
temporal --env staging -o json --time-format iso workflow reset \
  --workflow-id "my-workflow" \
  --type LastWorkflowTask \
  --reason "Reset to last workflow task"

# Reset by Build ID (for versioning)
temporal --env prod -o json --time-format iso workflow reset \
  --query "BuildIds = 'buggy-build-v1.2.3'" \
  --type BuildId \
  --build-id "good-build-v1.2.2" \
  --reason "Rollback workflows from buggy build" \
  --yes
```

---

## Trace Workflow

Get stack trace (goroutine info) for a running workflow - useful for debugging stuck workflows.

### Basic Stack Trace

```bash
temporal --env prod -o json --time-format iso workflow stack \
  --workflow-id "long-running-workflow-999"
```

### Stack Trace for Specific Run

```bash
temporal --env staging -o json --time-format iso workflow stack \
  --workflow-id "stuck-workflow" \
  --run-id "abc123-def456"
```

### Parse Stack Trace

```bash
temporal --env prod -o json --time-format iso workflow stack \
  --workflow-id "my-workflow" | \
  jq -r '.stacks'
```

### Analyze Stuck Workflow

```bash
WORKFLOW_ID="potentially-stuck-workflow"

echo "Getting workflow status..."
temporal --env staging -o json --time-format iso workflow describe \
  --workflow-id "$WORKFLOW_ID" | \
  jq '{status: .workflowExecutionInfo.status, startTime: .workflowExecutionInfo.startTime}'

echo -e "\nGetting stack trace..."
temporal --env staging -o json --time-format iso workflow stack \
  --workflow-id "$WORKFLOW_ID" | \
  jq -r '.stacks'

echo -e "\nRecent events..."
temporal --env staging -o json --time-format iso workflow show \
  --workflow-id "$WORKFLOW_ID" | \
  jq '.events[-10:] | .[] | {eventType, eventId}'
```

---

## Error Handling

### Capture stderr and stdout

```bash
# Capture both outputs
RESULT=$(temporal --env prod -o json --time-format iso workflow list \
  --query "WorkflowType = 'MyFlow'" 2>&1)

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
  echo "$RESULT" | jq '.workflowExecutions | length'
else
  echo "Error occurred: $RESULT"
fi
```

### Check for Specific Errors

```bash
RESULT=$(temporal --env prod -o json --time-format iso workflow list \
  --query "WorkflowType LIKE '%pattern%'" 2>&1)

if [ $? -ne 0 ]; then
  if echo "$RESULT" | grep -q "operator 'like' not allowed"; then
    echo "ERROR: LIKE operator not supported"
    echo "Hint: Use STARTS_WITH instead"
    echo "Example: WorkflowType STARTS_WITH 'pattern'"
  elif echo "$RESULT" | grep -q "unbalanced"; then
    echo "ERROR: Query syntax error - check quotes and parentheses"
  else
    echo "ERROR: $RESULT"
  fi
  exit 1
fi
```

### Retry on Failure

```bash
retry_command() {
  local max_attempts=3
  local attempt=1

  while [ $attempt -le $max_attempts ]; do
    echo "Attempt $attempt of $max_attempts"

    if temporal --env staging -o json --time-format iso workflow list --limit 10; then
      return 0
    fi

    attempt=$((attempt + 1))
    sleep 2
  done

  echo "Command failed after $max_attempts attempts"
  return 1
}

retry_command
```

### Validate Before Execute

```bash
execute_query() {
  local query=$1

  # Basic validation
  if [ -z "$query" ]; then
    echo "ERROR: Query is empty"
    return 1
  fi

  # Check for LIKE operator
  if echo "$query" | grep -qi 'LIKE'; then
    echo "ERROR: LIKE operator not supported. Use STARTS_WITH"
    return 1
  fi

  # Execute if valid
  temporal --env staging -o json --time-format iso workflow list \
    --query "$query" \
    --limit 10
}

execute_query "WorkflowType = 'MyFlow'"
```

## Complete Examples

### Monitor Failed Workflows

```bash
#!/bin/bash
# Monitor and report failed workflows

ENV="prod"
WORKFLOW_TYPE="OnboardingFlow"

# Count failures
FAILED_COUNT=$(temporal --env "$ENV" -o json --time-format iso workflow count \
  --query "WorkflowType = '$WORKFLOW_TYPE' AND ExecutionStatus = 'Failed'" | \
  jq '.count')

echo "=== Failed Workflow Report ==="
echo "Environment: $ENV"
echo "Workflow Type: $WORKFLOW_TYPE"
echo "Failed Count: $FAILED_COUNT"
echo

if [ "$FAILED_COUNT" -gt 0 ]; then
  echo "Recent failures:"
  temporal --env "$ENV" -o json --time-format iso workflow list \
    --query "WorkflowType = '$WORKFLOW_TYPE' AND ExecutionStatus = 'Failed'" \
    --limit 10 | \
    jq -r '.workflowExecutions[] | "\(.execution.workflowId) - \(.closeTime)"'
fi
```

### Bulk Signal Workflows

```bash
#!/bin/bash
# Send signal to all running workflows of a type

WORKFLOW_TYPE="OnboardingFlow"
SIGNAL_NAME="configUpdate"
SIGNAL_DATA='{"version": "2.0", "feature_flags": {"new_ui": true}}'

# Get running workflows
WORKFLOW_IDS=$(temporal --env staging -o json --time-format iso workflow list \
  --query "WorkflowType = '$WORKFLOW_TYPE' AND ExecutionStatus = 'Running'" \
  --limit 100 | \
  jq -r '.workflowExecutions[].execution.workflowId')

COUNT=$(echo "$WORKFLOW_IDS" | wc -l)
echo "Signaling $COUNT workflows..."

for WF_ID in $WORKFLOW_IDS; do
  echo "Signaling: $WF_ID"
  temporal --env staging -o json --time-format iso workflow signal \
    --workflow-id "$WF_ID" \
    --name "$SIGNAL_NAME" \
    --input "$SIGNAL_DATA"
done

echo "Done!"
```

## See Also

- [Query Construction](02-query-construction.md) - Complete query syntax guide
- [Error Handling](07-error-handling.md) - Common errors and solutions
- [Safety Checks](08-safety-checks.md) - Validation for destructive operations
