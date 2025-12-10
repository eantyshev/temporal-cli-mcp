# History Filtering Guide

jq patterns for filtering and paging Temporal workflow event histories to manage context window usage.

## Table of Contents

- [Why Filter History](#why-filter-history)
- [Event Count Analysis](#event-count-analysis)
- [Filtering by Event Type](#filtering-by-event-type)
- [Pagination Patterns](#pagination-patterns)
- [Smart Filtering Strategies](#smart-filtering-strategies)
- [Summary and Statistics](#summary-and-statistics)
- [Complete Examples](#complete-examples)

## Why Filter History

Large workflow histories (500+ events) can overwhelm context windows and make analysis difficult. Use jq to filter intelligently.

**When to filter:**
- History has 100+ events
- You're debugging specific issues
- You need to focus on failures or specific activities
- Context window is limited

**Filtering strategies:**
1. **By event type** - Show only failures, signals, etc.
2. **Pagination** - Show events 1-100, 101-200, etc.
3. **Critical path** - Show only start, complete, fail events
4. **Exclude verbose** - Remove timers, heartbeats, markers
5. **Summary mode** - Event counts + first/last N events

---

## Event Count Analysis

### Count Total Events

```bash
temporal --env prod -o json --time-format iso workflow show \
  --workflow-id "my-workflow" | \
  jq '.events | length'
```

### Count Events by Type

```bash
temporal --env staging -o json --time-format iso workflow show \
  --workflow-id "long-workflow" | \
  jq '[.events[] | .eventType] | group_by(.) |
      map({type: .[0], count: length}) |
      sort_by(-.count)'
```

**Output example:**
```json
[
  {"type": "WorkflowTaskScheduled", "count": 42},
  {"type": "WorkflowTaskStarted", "count": 42},
  {"type": "WorkflowTaskCompleted", "count": 41},
  {"type": "ActivityTaskScheduled", "count": 15},
  {"type": "ActivityTaskCompleted", "count": 12},
  {"type": "ActivityTaskFailed", "count": 3}
]
```

### List Unique Event Types

```bash
temporal --env prod -o json --time-format iso workflow show \
  --workflow-id "my-workflow" | \
  jq '[.events[] | .eventType] | unique | sort'
```

---

## Filtering by Event Type

### Show Only Failures

```bash
# All failure events
temporal --env prod -o json --time-format iso workflow show \
  --workflow-id "failed-workflow" | \
  jq '.events[] | select(.eventType | contains("Failed"))'
```

### Show Specific Event Type

```bash
# Only WorkflowExecutionStarted
temporal --env staging -o json --time-format iso workflow show \
  --workflow-id "my-workflow" | \
  jq '.events[] | select(.eventType == "WorkflowExecutionStarted")'
```

### Show Multiple Event Types

```bash
# Started, Completed, or Failed
temporal --env prod -o json --time-format iso workflow show \
  --workflow-id "my-workflow" | \
  jq '.events[] |
    select(.eventType |
      test("WorkflowExecutionStarted|WorkflowExecutionCompleted|WorkflowExecutionFailed")
    )'
```

### Filter Activity Events

```bash
# Only activity-related events
temporal --env staging -o json --time-format iso workflow show \
  --workflow-id "my-workflow" | \
  jq '.events[] | select(.eventType | contains("Activity"))'
```

### Filter Signal Events

```bash
# Only signals
temporal --env prod -o json --time-format iso workflow show \
  --workflow-id "my-workflow" | \
  jq '.events[] | select(.eventType | contains("Signal"))'
```

### Filter Timer Events

```bash
# Only timer events
temporal --env staging -o json --time-format iso workflow show \
  --workflow-id "my-workflow" | \
  jq '.events[] | select(.eventType | contains("Timer"))'
```

---

## Pagination Patterns

### First N Events

```bash
# First 100 events
temporal --env prod -o json --time-format iso workflow show \
  --workflow-id "huge-workflow" | \
  jq '.events[0:100]'

# First 50 events
temporal --env staging -o json --time-format iso workflow show \
  --workflow-id "my-workflow" | \
  jq '.events[0:50]'
```

### Events N to M

```bash
# Events 101-200
temporal --env prod -o json --time-format iso workflow show \
  --workflow-id "huge-workflow" | \
  jq '.events[100:200]'

# Events 51-100
temporal --env staging -o json --time-format iso workflow show \
  --workflow-id "my-workflow" | \
  jq '.events[50:100]'
```

### Last N Events

```bash
# Last 50 events
temporal --env prod -o json --time-format iso workflow show \
  --workflow-id "my-workflow" | \
  jq '.events[-50:]'

# Last 10 events
temporal --env staging -o json --time-format iso workflow show \
  --workflow-id "my-workflow" | \
  jq '.events[-10:]'
```

### Pagination Function

```bash
show_events_page() {
  local workflow_id=$1
  local start=${2:-0}
  local end=${3:-100}
  local env=${4:-staging}

  echo "Showing events $start to $end for $workflow_id"
  temporal --env "$env" -o json --time-format iso workflow show \
    --workflow-id "$workflow_id" | \
    jq ".events[$start:$end]"
}

# Usage
show_events_page "long-workflow" 0 100 "prod"
show_events_page "long-workflow" 100 200 "prod"
```

---

## Smart Filtering Strategies

### Critical Path Only

Show only the most important events:

```bash
temporal --env prod -o json --time-format iso workflow show \
  --workflow-id "my-workflow" | \
  jq '.events[] |
    select(.eventType |
      test("WorkflowExecutionStarted|WorkflowExecutionCompleted|WorkflowExecutionFailed|ActivityTaskFailed|ChildWorkflowExecutionFailed")
    )'
```

### Exclude Verbose Events

Remove noisy events:

```bash
temporal --env staging -o json --time-format iso workflow show \
  --workflow-id "my-workflow" | \
  jq '.events[] |
    select(.eventType |
      test("TimerFired|ActivityTaskCancelRequested|MarkerRecorded|WorkflowTaskScheduled|WorkflowTaskStarted") | not
    )'
```

### Show Only User-Initiated Actions

```bash
# Signals, queries, updates
temporal --env prod -o json --time-format iso workflow show \
  --workflow-id "my-workflow" | \
  jq '.events[] |
    select(.eventType |
      test("Signal|Query|Update")
    )'
```

### Activity-Centric View

```bash
# Activity scheduled and results (success/failure)
temporal --env staging -o json --time-format iso workflow show \
  --workflow-id "my-workflow" | \
  jq '.events[] |
    select(.eventType |
      test("ActivityTaskScheduled|ActivityTaskCompleted|ActivityTaskFailed")
    )'
```

---

## Summary and Statistics

### Summary Mode

```bash
summary_mode() {
  local workflow_id=$1
  local env=${2:-staging}

  HISTORY=$(temporal --env "$env" -o json --time-format iso workflow show \
    --workflow-id "$workflow_id")

  echo "=== Event Summary for $workflow_id ==="
  echo

  # Total count
  TOTAL=$(echo "$HISTORY" | jq '.events | length')
  echo "Total Events: $TOTAL"
  echo

  # Event type breakdown
  echo "Event Type Counts:"
  echo "$HISTORY" | jq '[.events[] | .eventType] | group_by(.) |
    map({type: .[0], count: length}) |
    sort_by(-.count)' | \
    jq -r '.[] | "  \(.type): \(.count)"'
  echo

  # First 5 events
  echo "First 5 Events:"
  echo "$HISTORY" | jq '.events[0:5] | .[] | {eventId, eventType}'
  echo

  # Last 5 events
  echo "Last 5 Events:"
  echo "$HISTORY" | jq '.events[-5:] | .[] | {eventId, eventType}'
}

# Usage
summary_mode "long-running-workflow" "prod"
```

### Failure Analysis Summary

```bash
failure_summary() {
  local workflow_id=$1
  local env=${2:-staging}

  echo "=== Failure Analysis for $workflow_id ==="

  HISTORY=$(temporal --env "$env" -o json --time-format iso workflow show \
    --workflow-id "$workflow_id")

  # Count failures
  WORKFLOW_FAILED=$(echo "$HISTORY" | jq '[.events[] | select(.eventType == "WorkflowExecutionFailed")] | length')
  ACTIVITY_FAILED=$(echo "$HISTORY" | jq '[.events[] | select(.eventType == "ActivityTaskFailed")] | length')
  CHILD_FAILED=$(echo "$HISTORY" | jq '[.events[] | select(.eventType == "ChildWorkflowExecutionFailed")] | length')

  echo "Workflow Failures: $WORKFLOW_FAILED"
  echo "Activity Failures: $ACTIVITY_FAILED"
  echo "Child Workflow Failures: $CHILD_FAILED"
  echo

  if [ "$ACTIVITY_FAILED" -gt 0 ]; then
    echo "Failed Activities:"
    echo "$HISTORY" | jq '.events[] |
      select(.eventType == "ActivityTaskFailed") |
      {
        eventId,
        activityType: .activityTaskFailedEventAttributes.activityType.name,
        failure: .activityTaskFailedEventAttributes.failure.message
      }'
  fi
}

# Usage
failure_summary "failed-workflow" "prod"
```

### Activity Duration Statistics

```bash
activity_stats() {
  local workflow_id=$1
  local env=${2:-staging}

  echo "=== Activity Statistics for $workflow_id ==="

  temporal --env "$env" -o json --time-format iso workflow show \
    --workflow-id "$workflow_id" | \
    jq '
      [.events[] | select(.activityTaskCompletedEventAttributes)] |
      map({
        activityType: .activityTaskCompletedEventAttributes.activityType.name,
        scheduledEventId: .activityTaskCompletedEventAttributes.scheduledEventId,
        startedEventId: .activityTaskCompletedEventAttributes.startedEventId
      }) |
      group_by(.activityType) |
      map({
        activity: .[0].activityType,
        count: length
      })
    '
}

# Usage
activity_stats "my-workflow" "staging"
```

---

## Complete Examples

### Smart History Inspector

```bash
#!/bin/bash
# smart_history.sh - Intelligently filter history based on size

inspect_history() {
  local workflow_id=$1
  local env=${2:-staging}

  HISTORY=$(temporal --env "$env" -o json --time-format iso workflow show \
    --workflow-id "$workflow_id")

  EVENT_COUNT=$(echo "$HISTORY" | jq '.events | length')

  echo "=== Workflow History: $workflow_id ==="
  echo "Total Events: $EVENT_COUNT"
  echo

  if [ "$EVENT_COUNT" -lt 50 ]; then
    # Small history - show everything
    echo "Small history - showing all events:"
    echo "$HISTORY" | jq '.events[] | {eventId, eventType}'

  elif [ "$EVENT_COUNT" -lt 200 ]; then
    # Medium history - show critical path
    echo "Medium history - showing critical path:"
    echo "$HISTORY" | jq '.events[] |
      select(.eventType |
        test("Started|Completed|Failed|Signal")
      ) |
      {eventId, eventType}'

  elif [ "$EVENT_COUNT" -lt 500 ]; then
    # Large history - show summary + failures
    echo "Large history - showing summary and failures:"
    echo
    echo "Event Type Counts:"
    echo "$HISTORY" | jq '[.events[] | .eventType] | group_by(.) |
      map({type: .[0], count: length}) |
      sort_by(-.count)' | \
      jq -r '.[] | "  \(.type): \(.count)"'
    echo
    echo "Failures:"
    echo "$HISTORY" | jq '.events[] | select(.eventType | contains("Failed"))'

  else
    # Huge history - show summary only
    echo "Huge history ($EVENT_COUNT events) - showing summary only:"
    echo
    echo "Event Type Counts:"
    echo "$HISTORY" | jq '[.events[] | .eventType] | group_by(.) |
      map({type: .[0], count: length}) |
      sort_by(-.count)' | \
      jq -r '.[] | "  \(.type): \(.count)"'
    echo
    echo "First 5 events:"
    echo "$HISTORY" | jq '.events[0:5] | .[] | {eventId, eventType}'
    echo
    echo "Last 5 events:"
    echo "$HISTORY" | jq '.events[-5:] | .[] | {eventId, eventType}'
    echo
    echo "Use pagination or event-type filtering for detailed analysis"
    echo "Example: jq '.events[0:100]' for first 100 events"
  fi
}

# Usage
inspect_history "my-workflow" "prod"
```

### Interactive History Browser

```bash
#!/bin/bash
# browse_history.sh - Interactive history browser

browse_history() {
  local workflow_id=$1
  local env=${2:-staging}

  HISTORY=$(temporal --env "$env" -o json --time-format iso workflow show \
    --workflow-id "$workflow_id")

  while true; do
    echo "=== History Browser: $workflow_id ==="
    echo "1. Show summary"
    echo "2. Show failures only"
    echo "3. Show activities only"
    echo "4. Show signals only"
    echo "5. Show first 50 events"
    echo "6. Show last 50 events"
    echo "7. Custom jq filter"
    echo "8. Exit"
    read -p "Choose option: " choice

    case $choice in
      1)
        echo "$HISTORY" | jq '[.events[] | .eventType] | group_by(.) |
          map({type: .[0], count: length}) |
          sort_by(-.count)'
        ;;
      2)
        echo "$HISTORY" | jq '.events[] | select(.eventType | contains("Failed"))'
        ;;
      3)
        echo "$HISTORY" | jq '.events[] | select(.eventType | contains("Activity"))'
        ;;
      4)
        echo "$HISTORY" | jq '.events[] | select(.eventType | contains("Signal"))'
        ;;
      5)
        echo "$HISTORY" | jq '.events[0:50]'
        ;;
      6)
        echo "$HISTORY" | jq '.events[-50:]'
        ;;
      7)
        read -p "Enter jq filter: " filter
        echo "$HISTORY" | jq "$filter"
        ;;
      8)
        break
        ;;
      *)
        echo "Invalid option"
        ;;
    esac
    echo
  done
}

# Usage
browse_history "my-workflow" "staging"
```

### Export Filtered History

```bash
export_filtered_history() {
  local workflow_id=$1
  local filter_type=$2  # failures, activities, signals, critical
  local output_file=$3
  local env=${4:-staging}

  case $filter_type in
    failures)
      jq_filter='.events[] | select(.eventType | contains("Failed"))'
      ;;
    activities)
      jq_filter='.events[] | select(.eventType | contains("Activity"))'
      ;;
    signals)
      jq_filter='.events[] | select(.eventType | contains("Signal"))'
      ;;
    critical)
      jq_filter='.events[] | select(.eventType | test("Started|Completed|Failed"))'
      ;;
    *)
      echo "Unknown filter type: $filter_type"
      return 1
      ;;
  esac

  echo "Exporting $filter_type events for $workflow_id to $output_file"
  temporal --env "$env" -o json --time-format iso workflow show \
    --workflow-id "$workflow_id" | \
    jq "$jq_filter" > "$output_file"

  echo "Done! Events written to $output_file"
}

# Usage
export_filtered_history "failed-workflow" "failures" "/tmp/failures.json" "prod"
```

---

## Performance Considerations

### Filter Before Decoding

When dealing with payloads, filter events first, then decode:

```bash
# ✅ GOOD: Filter first
temporal --env prod -o json --time-format iso workflow show \
  --workflow-id "huge-workflow" | \
  jq '.events[] | select(.eventType == "ActivityTaskCompleted")' | \
  jq -r '.activityTaskCompletedEventAttributes.result.payloads[0].data' | \
  base64 -d

# ❌ BAD: Decode everything
# (This would decode all payloads, very expensive)
```

### Use Pagination for Large Histories

```bash
# Process in chunks
for i in {0..1000..100}; do
  echo "Processing events $i to $((i+100))"
  temporal --env prod -o json --time-format iso workflow show \
    --workflow-id "huge-workflow" | \
    jq ".events[$i:$((i+100))]" | \
    # Process this chunk
    jq '.[] | select(.eventType | contains("Failed"))'
done
```

---

## See Also

- [Payload Decoding](04-payload-decoding.md) - Decoding filtered events
- [Smart Patterns](06-smart-patterns.md) - Smart history inspection logic
- [Command Patterns](01-command-patterns.md) - Getting workflow history
