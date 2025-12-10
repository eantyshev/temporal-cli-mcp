# Payload Decoding Guide

Base64 decoding patterns for Temporal workflow history payloads using base64 and jq.

## Table of Contents

- [Why Decode Payloads](#why-decode-payloads)
- [Payload Locations](#payload-locations)
- [Basic Decoding](#basic-decoding)
- [Decoding Recipes](#decoding-recipes)
- [Complete Decoding Functions](#complete-decoding-functions)
- [Truncation Strategies](#truncation-strategies)
- [Common Patterns](#common-patterns)

## Why Decode Payloads

Temporal encodes workflow inputs, outputs, and event data as base64 strings in JSON output. To inspect actual values, you must decode them.

**What's encoded:**
- Workflow inputs
- Workflow outputs/results
- Activity inputs
- Activity results
- Signal payloads
- Query payloads
- Child workflow inputs/results
- Failure details

---

## Payload Locations

### 30+ Payload Paths in Event History

Payloads appear in specific event attribute paths:

```bash
# Workflow execution
.events[].workflowExecutionStartedEventAttributes.input.payloads[].data
.events[].workflowExecutionCompletedEventAttributes.result.payloads[].data
.events[].workflowExecutionFailedEventAttributes.failure.cause.encodedAttributes

# Activity task
.events[].activityTaskScheduledEventAttributes.input.payloads[].data
.events[].activityTaskCompletedEventAttributes.result.payloads[].data
.events[].activityTaskFailedEventAttributes.failure.cause.encodedAttributes

# Signal workflow
.events[].signalExternalWorkflowExecutionInitiatedEventAttributes.input.payloads[].data
.events[].workflowExecutionSignaledEventAttributes.input.payloads[].data

# Child workflow
.events[].startChildWorkflowExecutionInitiatedEventAttributes.input.payloads[].data
.events[].childWorkflowExecutionCompletedEventAttributes.result.payloads[].data
.events[].childWorkflowExecutionFailedEventAttributes.failure.cause.encodedAttributes

# Timer
.events[].timerStartedEventAttributes.input.payloads[].data

# Update
.events[].workflowExecutionUpdateAcceptedEventAttributes.request.input.payloads[].data

# ... and 20+ more paths
```

---

## Basic Decoding

### Decode Single Payload

```bash
# Get workflow history
HISTORY=$(temporal --env staging -o json --time-format iso workflow show \
  --workflow-id "my-workflow-123")

# Decode workflow input (first payload)
echo "$HISTORY" | \
  jq -r '.events[0].workflowExecutionStartedEventAttributes.input.payloads[0].data' | \
  base64 -d
```

### Decode and Parse as JSON

```bash
# Decode and pretty-print JSON
echo "$HISTORY" | \
  jq -r '.events[0].workflowExecutionStartedEventAttributes.input.payloads[0].data' | \
  base64 -d | \
  jq '.'
```

### Decode All Input Payloads

```bash
temporal --env prod -o json --time-format iso workflow show \
  --workflow-id "order-456" | \
  jq '.events[0].workflowExecutionStartedEventAttributes.input.payloads[]?.data' | \
  while read -r encoded; do
    echo "$encoded" | tr -d '"' | base64 -d | jq '.' 2>/dev/null || echo "$encoded"
  done
```

---

## Decoding Recipes

### Recipe 1: Decode Workflow Input

```bash
decode_workflow_input() {
  local workflow_id=$1
  local env=${2:-staging}

  temporal --env "$env" -o json --time-format iso workflow show \
    --workflow-id "$workflow_id" | \
    jq -r '.events[0].workflowExecutionStartedEventAttributes.input.payloads[0].data' | \
    base64 -d | \
    jq '.'
}

# Usage
decode_workflow_input "patient-onboard-123" "prod"
```

### Recipe 2: Decode Workflow Result

```bash
decode_workflow_result() {
  local workflow_id=$1
  local env=${2:-staging}

  temporal --env "$env" -o json --time-format iso workflow show \
    --workflow-id "$workflow_id" | \
    jq -r '.events[] |
      select(.workflowExecutionCompletedEventAttributes) |
      .workflowExecutionCompletedEventAttributes.result.payloads[0].data' | \
    base64 -d | \
    jq '.'
}

# Usage
decode_workflow_result "order-789" "prod"
```

### Recipe 3: Decode Activity Results

```bash
decode_activity_results() {
  local workflow_id=$1
  local env=${2:-staging}

  echo "=== Activity Results ==="
  temporal --env "$env" -o json --time-format iso workflow show \
    --workflow-id "$workflow_id" | \
    jq -r '.events[] |
      select(.activityTaskCompletedEventAttributes) |
      {
        eventId: .eventId,
        activityId: .activityTaskCompletedEventAttributes.scheduledEventId,
        data: .activityTaskCompletedEventAttributes.result.payloads[0].data
      } |
      "Event \(.eventId) (Activity \(.activityId)):\n\(.data)"' | \
    while read -r line; do
      if echo "$line" | grep -q "^Event"; then
        echo "$line"
      else
        echo "$line" | base64 -d | jq '.' 2>/dev/null || echo "(not JSON)"
      fi
    done
}

# Usage
decode_activity_results "my-workflow" "staging"
```

### Recipe 4: Decode Signal Payloads

```bash
decode_signal_payloads() {
  local workflow_id=$1
  local env=${2:-staging}

  echo "=== Signal Payloads ==="
  temporal --env "$env" -o json --time-format iso workflow show \
    --workflow-id "$workflow_id" | \
    jq -r '.events[] |
      select(.workflowExecutionSignaledEventAttributes) |
      {
        eventId: .eventId,
        signalName: .workflowExecutionSignaledEventAttributes.signalName,
        data: .workflowExecutionSignaledEventAttributes.input.payloads[0].data
      } |
      "Event \(.eventId) - Signal: \(.signalName)\n\(.data)"' | \
    while read -r line; do
      if echo "$line" | grep -q "^Event"; then
        echo "$line"
      else
        echo "$line" | base64 -d | jq '.' 2>/dev/null || echo "(not JSON)"
      fi
    done
}

# Usage
decode_signal_payloads "order-456" "prod"
```

### Recipe 5: Decode Failure Details

```bash
decode_failure_details() {
  local workflow_id=$1
  local env=${2:-staging}

  echo "=== Failure Details ==="
  temporal --env "$env" -o json --time-format iso workflow show \
    --workflow-id "$workflow_id" | \
    jq -r '.events[] |
      select(.workflowExecutionFailedEventAttributes or .activityTaskFailedEventAttributes) |
      {
        eventId: .eventId,
        type: .eventType,
        message: (.workflowExecutionFailedEventAttributes.failure.message // .activityTaskFailedEventAttributes.failure.message),
        encoded: (.workflowExecutionFailedEventAttributes.failure.cause.encodedAttributes // .activityTaskFailedEventAttributes.failure.cause.encodedAttributes)
      } |
      "Event \(.eventId) - \(.type)\nMessage: \(.message)\nEncoded: \(.encoded // "none")"' | \
    while read -r line; do
      if echo "$line" | grep -q "^Encoded:"; then
        encoded=$(echo "$line" | sed 's/^Encoded: //')
        if [ "$encoded" != "none" ]; then
          echo "Decoded:"
          echo "$encoded" | base64 -d 2>/dev/null || echo "(decode failed)"
        fi
      else
        echo "$line"
      fi
    done
}

# Usage
decode_failure_details "failed-workflow" "prod"
```

---

## Complete Decoding Functions

### Comprehensive Decoder

```bash
#!/bin/bash
# decode_all_payloads.sh - Decode all payloads in workflow history

decode_all_payloads() {
  local workflow_id=$1
  local env=${2:-staging}
  local max_len=${3:-4000}

  echo "=== Decoding Payloads for: $workflow_id ==="
  echo

  HISTORY=$(temporal --env "$env" -o json --time-format iso workflow show \
    --workflow-id "$workflow_id")

  # Decode workflow input
  echo "--- Workflow Input ---"
  echo "$HISTORY" | \
    jq -r '.events[0].workflowExecutionStartedEventAttributes.input.payloads[0]?.data // empty' | \
    base64 -d 2>/dev/null | \
    jq '.' 2>/dev/null || echo "(no input or decode failed)"
  echo

  # Decode workflow result
  echo "--- Workflow Result ---"
  echo "$HISTORY" | \
    jq -r '.events[] |
      select(.workflowExecutionCompletedEventAttributes) |
      .workflowExecutionCompletedEventAttributes.result.payloads[0]?.data // empty' | \
    base64 -d 2>/dev/null | \
    jq '.' 2>/dev/null || echo "(no result yet or decode failed)"
  echo

  # Decode activity results
  echo "--- Activity Results ---"
  local activity_count=$(echo "$HISTORY" | jq '[.events[] | select(.activityTaskCompletedEventAttributes)] | length')
  if [ "$activity_count" -gt 0 ]; then
    echo "$HISTORY" | \
      jq -r '.events[] |
        select(.activityTaskCompletedEventAttributes) |
        "Activity \(.activityTaskCompletedEventAttributes.scheduledEventId):\n\(.activityTaskCompletedEventAttributes.result.payloads[0].data)"' | \
      while read -r line; do
        if echo "$line" | grep -q "^Activity"; then
          echo "$line"
        else
          decoded=$(echo "$line" | base64 -d 2>/dev/null)
          if [ ${#decoded} -gt $max_len ]; then
            echo "${decoded:0:$max_len}... [truncated: ${#decoded} chars total]"
          else
            echo "$decoded" | jq '.' 2>/dev/null || echo "$decoded"
          fi
        fi
      done
  else
    echo "(no completed activities)"
  fi
  echo

  # Decode signals
  echo "--- Signals ---"
  local signal_count=$(echo "$HISTORY" | jq '[.events[] | select(.workflowExecutionSignaledEventAttributes)] | length')
  if [ "$signal_count" -gt 0 ]; then
    echo "$HISTORY" | \
      jq -r '.events[] |
        select(.workflowExecutionSignaledEventAttributes) |
        "Signal: \(.workflowExecutionSignaledEventAttributes.signalName)\n\(.workflowExecutionSignaledEventAttributes.input.payloads[0].data)"' | \
      while read -r line; do
        if echo "$line" | grep -q "^Signal:"; then
          echo "$line"
        else
          echo "$line" | base64 -d 2>/dev/null | jq '.' 2>/dev/null || echo "(decode failed)"
        fi
      done
  else
    echo "(no signals)"
  fi
}

# Usage
decode_all_payloads "my-workflow-123" "prod" 4000
```

### jq-Based Decoder (Advanced)

```bash
decode_history_with_jq() {
  local workflow_id=$1
  local env=${2:-staging}

  temporal --env "$env" -o json --time-format iso workflow show \
    --workflow-id "$workflow_id" | \
    jq '
      # Decode workflow input
      .events[0].workflowExecutionStartedEventAttributes.input.payloads[0]?.data |=
        if . then (@base64d | try fromjson catch .) else null end |

      # Decode activity results
      .events |= map(
        if .activityTaskCompletedEventAttributes.result.payloads then
          .activityTaskCompletedEventAttributes.result.payloads |= map(
            .data |= (@base64d | try fromjson catch .)
          )
        else . end
      ) |

      # Decode workflow result
      .events |= map(
        if .workflowExecutionCompletedEventAttributes.result.payloads then
          .workflowExecutionCompletedEventAttributes.result.payloads |= map(
            .data |= (@base64d | try fromjson catch .)
          )
        else . end
      ) |

      # Decode signals
      .events |= map(
        if .workflowExecutionSignaledEventAttributes.input.payloads then
          .workflowExecutionSignaledEventAttributes.input.payloads |= map(
            .data |= (@base64d | try fromjson catch .)
          )
        else . end
      )
    '
}

# Usage
decode_history_with_jq "order-456" "prod"
```

---

## Truncation Strategies

### Truncate Long Strings

```bash
MAX_LEN=4000

decode_and_truncate() {
  local encoded=$1

  decoded=$(echo "$encoded" | base64 -d 2>/dev/null)

  if [ ${#decoded} -gt $MAX_LEN ]; then
    echo "${decoded:0:$MAX_LEN}... [truncated: showing first $MAX_LEN of ${#decoded} characters]"
  else
    echo "$decoded"
  fi
}

# Usage
ENCODED_PAYLOAD="VGhpcyBpcyBhIGxvbmcgcGF5bG9hZA=="
decode_and_truncate "$ENCODED_PAYLOAD"
```

### Smart Truncation (JSON vs String)

```bash
smart_decode_and_truncate() {
  local encoded=$1
  local max_len=${2:-4000}

  decoded=$(echo "$encoded" | base64 -d 2>/dev/null)

  # Try to parse as JSON
  if echo "$decoded" | jq '.' >/dev/null 2>&1; then
    # It's JSON - pretty print and then truncate
    pretty=$(echo "$decoded" | jq '.' 2>/dev/null)
    if [ ${#pretty} -gt $max_len ]; then
      echo "${pretty:0:$max_len}... [truncated JSON: ${#pretty} chars total]"
    else
      echo "$pretty"
    fi
  else
    # It's a string - truncate directly
    if [ ${#decoded} -gt $max_len ]; then
      echo "${decoded:0:$max_len}... [truncated string: ${#decoded} chars total]"
    else
      echo "$decoded"
    fi
  fi
}

# Usage
smart_decode_and_truncate "$ENCODED_PAYLOAD" 2000
```

---

## Common Patterns

### Pattern 1: Extract and Decode Specific Field

```bash
# Get customer ID from workflow input
get_customer_id() {
  local workflow_id=$1
  local env=${2:-staging}

  temporal --env "$env" -o json --time-format iso workflow show \
    --workflow-id "$workflow_id" | \
    jq -r '.events[0].workflowExecutionStartedEventAttributes.input.payloads[0].data' | \
    base64 -d | \
    jq -r '.customerId'
}

# Usage
CUSTOMER_ID=$(get_customer_id "patient-onboard-123" "prod")
echo "Customer ID: $CUSTOMER_ID"
```

### Pattern 2: Decode All Payloads of Specific Type

```bash
# Decode all activity inputs
decode_all_activity_inputs() {
  local workflow_id=$1
  local env=${2:-staging}

  temporal --env "$env" -o json --time-format iso workflow show \
    --workflow-id "$workflow_id" | \
    jq -r '.events[] |
      select(.activityTaskScheduledEventAttributes) |
      {
        eventId: .eventId,
        activityType: .activityTaskScheduledEventAttributes.activityType.name,
        input: .activityTaskScheduledEventAttributes.input.payloads[0].data
      } |
      @json' | \
    while read -r event; do
      event_id=$(echo "$event" | jq -r '.eventId')
      activity_type=$(echo "$event" | jq -r '.activityType')
      input=$(echo "$event" | jq -r '.input' | base64 -d 2>/dev/null | jq '.' 2>/dev/null || echo "(decode failed)")

      echo "Event $event_id - $activity_type:"
      echo "$input"
      echo
    done
}

# Usage
decode_all_activity_inputs "my-workflow" "staging"
```

### Pattern 3: Compare Input and Output

```bash
compare_input_output() {
  local workflow_id=$1
  local env=${2:-staging}

  HISTORY=$(temporal --env "$env" -o json --time-format iso workflow show \
    --workflow-id "$workflow_id")

  echo "=== Input ==="
  echo "$HISTORY" | \
    jq -r '.events[0].workflowExecutionStartedEventAttributes.input.payloads[0].data' | \
    base64 -d | \
    jq '.'

  echo
  echo "=== Output ==="
  echo "$HISTORY" | \
    jq -r '.events[] |
      select(.workflowExecutionCompletedEventAttributes) |
      .workflowExecutionCompletedEventAttributes.result.payloads[0].data' | \
    base64 -d | \
    jq '.'
}

# Usage
compare_input_output "order-456" "prod"
```

### Pattern 4: Find Payloads Containing Specific Value

```bash
find_payloads_with_value() {
  local workflow_id=$1
  local search_value=$2
  local env=${3:-staging}

  echo "Searching for payloads containing: $search_value"

  temporal --env "$env" -o json --time-format iso workflow show \
    --workflow-id "$workflow_id" | \
    jq -r '.events[] |
      select(.activityTaskCompletedEventAttributes or .workflowExecutionSignaledEventAttributes) |
      {
        eventId: .eventId,
        type: .eventType,
        data: (
          .activityTaskCompletedEventAttributes.result.payloads[0].data //
          .workflowExecutionSignaledEventAttributes.input.payloads[0].data
        )
      } |
      @json' | \
    while read -r event; do
      event_id=$(echo "$event" | jq -r '.eventId')
      event_type=$(echo "$event" | jq -r '.type')
      data=$(echo "$event" | jq -r '.data' | base64 -d 2>/dev/null)

      if echo "$data" | grep -q "$search_value"; then
        echo "Found in Event $event_id ($event_type):"
        echo "$data" | jq '.' 2>/dev/null || echo "$data"
        echo
      fi
    done
}

# Usage
find_payloads_with_value "my-workflow" "customer-123" "staging"
```

---

## Error Handling

### Handle Decode Failures

```bash
safe_decode() {
  local encoded=$1

  if [ -z "$encoded" ]; then
    echo "(empty payload)"
    return
  fi

  decoded=$(echo "$encoded" | base64 -d 2>&1)
  decode_exit=$?

  if [ $decode_exit -ne 0 ]; then
    echo "(base64 decode failed)"
    return
  fi

  # Try JSON parse
  if echo "$decoded" | jq '.' >/dev/null 2>&1; then
    echo "$decoded" | jq '.'
  else
    echo "$decoded"
  fi
}

# Usage
PAYLOAD=$(temporal --env staging -o json --time-format iso workflow show \
  --workflow-id "my-workflow" | \
  jq -r '.events[0].workflowExecutionStartedEventAttributes.input.payloads[0].data')

safe_decode "$PAYLOAD"
```

---

## See Also

- [History Filtering](05-history-filtering.md) - Filtering large histories before decoding
- [Command Patterns](01-command-patterns.md) - Getting workflow history
- [Smart Patterns](06-smart-patterns.md) - Smart history inspection
