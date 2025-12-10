# Query Construction Guide

Complete guide to constructing Temporal workflow list filter queries with 50+ examples.

## Table of Contents

- [Query Syntax Rules](#query-syntax-rules)
- [Supported Fields](#supported-fields)
- [Supported Operators](#supported-operators)
- [Standard Field Queries](#standard-field-queries)
- [Custom Search Attributes](#custom-search-attributes)
- [Time-Based Queries](#time-based-queries)
- [Combined Queries](#combined-queries)
- [Real-World Examples](#real-world-examples)
- [Common Mistakes](#common-mistakes)
- [Data Type Reference](#data-type-reference)

## Query Syntax Rules

### Basic Rules

| Element | Rule | Example |
|---------|------|---------|
| **Field names** | Case-sensitive, backticks for special chars | `WorkflowType`, `` `my-field` `` |
| **String values** | Single quotes required | `'MyWorkflow'` |
| **Numeric values** | No quotes | `123`, `45.67` |
| **Boolean values** | Lowercase, no quotes | `true`, `false` |
| **Datetime values** | ISO 8601 with single quotes | `'2025-01-01T00:00:00Z'` |
| **Arrays** | Parentheses with comma separation | `('val1', 'val2', 'val3')` |
| **Logical operators** | Uppercase | `AND`, `OR` |
| **Grouping** | Parentheses | `(A AND B) OR C` |

### Query Structure

```bash
temporal --env <env> -o json --time-format iso workflow list \
  --query "<field> <operator> <value> [AND/OR <field> <operator> <value>]" \
  --limit <N>
```

---

## Supported Fields

### Core Standard Fields

| Field | Type | Description |
|-------|------|-------------|
| `WorkflowId` | Keyword | Unique workflow identifier |
| `WorkflowType` | Keyword | Workflow type name |
| `RunId` | Keyword | Specific run identifier |
| `ExecutionStatus` | Keyword | Current execution status |
| `StartTime` | Datetime | When workflow started |
| `CloseTime` | Datetime | When workflow completed |
| `ExecutionTime` | Datetime | Execution timestamp |
| `BuildIds` | KeywordList | Worker build identifier |
| `TaskQueue` | Keyword | Task queue name |
| `TemporalReportedProblems` | KeywordList | Workflow issues (failures, timeouts) |
| `WorkflowTaskStartedEventId` | Int | Event ID (internal) |

### TemporalReportedProblems Values

This built-in field tracks workflow problems. Common values:

| Value | Description |
|-------|-------------|
| `category=WorkflowTaskFailed` | WorkflowTask failed (includes non-deterministic errors) |
| `category=WorkflowTaskTimedOut` | WorkflowTask timed out |
| `cause=WorkflowTaskFailedCauseNonDeterministicError` | Non-deterministic error specifically |

### Execution Statuses

Valid values for `ExecutionStatus`:
- `Running` - Currently executing
- `Completed` - Successfully finished
- `Failed` - Execution failed
- `Canceled` - Cancelled by request
- `Terminated` - Forcefully terminated
- `ContinuedAsNew` - Continued as new execution
- `TimedOut` - Exceeded timeout

---

## Supported Operators

### Comparison Operators

| Operator | Use Case | Example |
|----------|----------|---------|
| `=` | Exact equality | `WorkflowType = 'OnboardingFlow'` |
| `!=` | Not equal | `ExecutionStatus != 'Completed'` |
| `>` | Greater than | `StartTime > '2025-01-01T00:00:00Z'` |
| `>=` | Greater or equal | `Priority >= 1` |
| `<` | Less than | `CloseTime < '2025-12-31T23:59:59Z'` |
| `<=` | Less or equal | `RetryCount <= 5` |

### Special Operators

| Operator | Use Case | Example |
|----------|----------|---------|
| `STARTS_WITH` | Prefix matching (Keyword only) | `WorkflowType STARTS_WITH 'patient'` |
| `IN` | Match any value in list | `ExecutionStatus IN ('Failed', 'Canceled')` |
| `BETWEEN` | Range match | `StartTime BETWEEN '2025-01-01' AND '2025-01-31'` |
| `IS NULL` | Field has no value | `CloseTime IS NULL` |
| `IS NOT NULL` | Field has a value | `CloseTime IS NOT NULL` |

### Logical Operators

| Operator | Purpose | Example |
|----------|---------|---------|
| `AND` | Both conditions true | `WorkflowType = 'A' AND ExecutionStatus = 'Failed'` |
| `OR` | Either condition true | `ExecutionStatus = 'Failed' OR ExecutionStatus = 'Canceled'` |

### NOT Supported

❌ `LIKE` - Use `STARTS_WITH` instead
❌ `CONTAINS` - Use `STARTS_WITH` instead
❌ `REGEX` - Not supported
❌ Wildcards (`%`, `*`) - Use `STARTS_WITH` instead

---

## Standard Field Queries

### WorkflowType Queries

```bash
# Exact match
temporal --env staging -o json --time-format iso workflow list \
  --query "WorkflowType = 'OnboardingFlow'"

# Prefix matching
temporal --env prod -o json --time-format iso workflow list \
  --query "WorkflowType STARTS_WITH 'patient'"

# Multiple types
temporal --env staging -o json --time-format iso workflow list \
  --query "WorkflowType IN ('OnboardingFlow', 'UserRegistration', 'OrderProcessing')"
```

### WorkflowId Queries

```bash
# Exact workflow ID
temporal --env prod -o json --time-format iso workflow list \
  --query "WorkflowId = 'patient-onboard-12345'"

# Prefix pattern
temporal --env staging -o json --time-format iso workflow list \
  --query "WorkflowId STARTS_WITH 'user-'"

# Multiple IDs
temporal --env prod -o json --time-format iso workflow list \
  --query "WorkflowId IN ('wf-1', 'wf-2', 'wf-3')"
```

### ExecutionStatus Queries

```bash
# Running workflows
temporal --env prod -o json --time-format iso workflow list \
  --query "ExecutionStatus = 'Running'"

# Failed workflows
temporal --env staging -o json --time-format iso workflow list \
  --query "ExecutionStatus = 'Failed'"

# Failed or canceled
temporal --env prod -o json --time-format iso workflow list \
  --query "ExecutionStatus IN ('Failed', 'Canceled', 'TimedOut')"

# Not completed
temporal --env staging -o json --time-format iso workflow list \
  --query "ExecutionStatus != 'Completed'"
```

### TaskQueue Queries

```bash
# Specific queue
temporal --env prod -o json --time-format iso workflow list \
  --query "TaskQueue = 'patient-workflows'"

# Queue prefix
temporal --env staging -o json --time-format iso workflow list \
  --query "TaskQueue STARTS_WITH 'prod-'"
```

### BuildIds Queries

```bash
# Specific build
temporal --env prod -o json --time-format iso workflow list \
  --query "BuildIds = 'build-v1.2.3'"

# Multiple builds
temporal --env staging -o json --time-format iso workflow list \
  --query "BuildIds IN ('build-123', 'build-124', 'build-125')"
```

---

## Custom Search Attributes

Custom search attributes must be configured in your Temporal cluster. Use backticks for field names with special characters.

### Custom Keyword Fields

```bash
# Customer ID
temporal --env prod -o json --time-format iso workflow list \
  --query "CustomerId = 'customer-abc-123'"

# With prefix
temporal --env staging -o json --time-format iso workflow list \
  --query "CustomerId STARTS_WITH 'customer-'"

# Environment
temporal --env prod -o json --time-format iso workflow list \
  --query "Environment IN ('staging', 'prod', 'dev')"

# Field with special characters (use backticks)
temporal --env prod -o json --time-format iso workflow list \
  --query "\`my-custom-field\` = 'value'"

temporal --env staging -o json --time-format iso workflow list \
  --query "\`user.email\` = 'user@example.com'"

temporal --env prod -o json --time-format iso workflow list \
  --query "\`tenant-id\` = 'tenant-123'"
```

### Custom Numeric Fields

```bash
# Integer comparison (NO quotes)
temporal --env prod -o json --time-format iso workflow list \
  --query "Priority = 1"

temporal --env staging -o json --time-format iso workflow list \
  --query "RetryCount > 5"

temporal --env prod -o json --time-format iso workflow list \
  --query "AttemptNumber >= 3"

# Range
temporal --env staging -o json --time-format iso workflow list \
  --query "Priority BETWEEN 1 AND 5"

# Floating-point (NO quotes)
temporal --env prod -o json --time-format iso workflow list \
  --query "Amount > 99.99"

temporal --env staging -o json --time-format iso workflow list \
  --query "Price BETWEEN 10.0 AND 100.0"
```

### Custom Boolean Fields

```bash
# Boolean values (lowercase, NO quotes)
temporal --env prod -o json --time-format iso workflow list \
  --query "IsUrgent = true"

temporal --env staging -o json --time-format iso workflow list \
  --query "HasErrors = false"

temporal --env prod -o json --time-format iso workflow list \
  --query "RequiresApproval = true"
```

### Custom DateTime Fields

```bash
# Custom date fields (WITH quotes)
temporal --env prod -o json --time-format iso workflow list \
  --query "CustomCreatedAt > '2025-01-01T00:00:00Z'"

temporal --env staging -o json --time-format iso workflow list \
  --query "LastUpdatedAt <= '2025-11-22T23:59:59Z'"

temporal --env prod -o json --time-format iso workflow list \
  --query "DueDate BETWEEN '2025-11-01T00:00:00Z' AND '2025-11-30T23:59:59Z'"
```

---

## Time-Based Queries

### StartTime Queries

```bash
# Workflows started after date
temporal --env prod -o json --time-format iso workflow list \
  --query "StartTime > '2025-01-01T00:00:00Z'"

# Workflows started before date
temporal --env staging -o json --time-format iso workflow list \
  --query "StartTime < '2025-12-31T23:59:59Z'"

# Last 24 hours (example date)
temporal --env prod -o json --time-format iso workflow list \
  --query "StartTime > '2025-11-21T00:00:00Z'"

# Specific range
temporal --env staging -o json --time-format iso workflow list \
  --query "StartTime BETWEEN '2025-01-01T00:00:00Z' AND '2025-01-31T23:59:59Z'"
```

### CloseTime Queries

```bash
# Workflows completed before date
temporal --env prod -o json --time-format iso workflow list \
  --query "CloseTime < '2025-12-31T23:59:59Z'"

# Workflows still running (CloseTime not set)
temporal --env staging -o json --time-format iso workflow list \
  --query "CloseTime IS NULL"

# Completed workflows only
temporal --env prod -o json --time-format iso workflow list \
  --query "CloseTime IS NOT NULL"

# Completed in specific period
temporal --env staging -o json --time-format iso workflow list \
  --query "CloseTime BETWEEN '2025-11-01T00:00:00Z' AND '2025-11-22T23:59:59Z'"
```

### ExecutionTime Queries

```bash
# Execution time window
temporal --env prod -o json --time-format iso workflow list \
  --query "ExecutionTime BETWEEN '2025-01-15T00:00:00Z' AND '2025-01-20T00:00:00Z'"

temporal --env staging -o json --time-format iso workflow list \
  --query "ExecutionTime > '2025-11-01T00:00:00Z'"
```

---

## Combined Queries

### Simple AND Conditions

```bash
# Failed patient workflows
temporal --env prod -o json --time-format iso workflow list \
  --query "WorkflowType STARTS_WITH 'patient' AND ExecutionStatus = 'Failed'"

# Recent failures
temporal --env staging -o json --time-format iso workflow list \
  --query "ExecutionStatus = 'Failed' AND StartTime > '2025-11-01T00:00:00Z'"

# Custom field + status
temporal --env prod -o json --time-format iso workflow list \
  --query "CustomerId = 'abc-123' AND ExecutionStatus = 'Running'"

# Multiple conditions
temporal --env staging -o json --time-format iso workflow list \
  --query "WorkflowType = 'OrderProcessing' AND Priority = 1 AND IsUrgent = true"
```

### OR Conditions

```bash
# Failed or canceled (prefer IN operator)
temporal --env prod -o json --time-format iso workflow list \
  --query "ExecutionStatus IN ('Failed', 'Canceled', 'TimedOut')"

# Multiple workflow types (prefer IN operator)
temporal --env staging -o json --time-format iso workflow list \
  --query "WorkflowType IN ('TypeA', 'TypeB', 'TypeC')"
```

### Complex Logic with Parentheses

```bash
# Complex conditions with grouping
temporal --env prod -o json --time-format iso workflow list \
  --query "(WorkflowType STARTS_WITH 'patient' AND ExecutionStatus = 'Running') OR (Priority = 1 AND IsUrgent = true)"

# Multiple criteria
temporal --env staging -o json --time-format iso workflow list \
  --query "(WorkflowType = 'OnboardingFlow' OR WorkflowType = 'Registration') AND ExecutionStatus = 'Failed' AND StartTime > '2025-01-01T00:00:00Z'"

# Custom fields with complex logic
temporal --env prod -o json --time-format iso workflow list \
  --query "(CustomerId STARTS_WITH 'cust-' AND Environment = 'prod') OR (IsUrgent = true AND Priority <= 2)"

# Nested conditions
temporal --env staging -o json --time-format iso workflow list \
  --query "((WorkflowType = 'A' OR WorkflowType = 'B') AND ExecutionStatus = 'Running') OR (Priority = 1 AND CloseTime IS NULL)"
```

---

## Real-World Examples

### Production Monitoring

```bash
# High-priority failed workflows in production
temporal --env prod -o json --time-format iso workflow list \
  --query "Environment = 'prod' AND ExecutionStatus = 'Failed' AND Priority = 1"

# Long-running workflows
temporal --env prod -o json --time-format iso workflow list \
  --query "ExecutionStatus = 'Running' AND StartTime < '2025-11-20T00:00:00Z'"

# Workflows by specific build
temporal --env prod -o json --time-format iso workflow list \
  --query "Environment = 'prod' AND BuildIds = 'build-v1.2.3'"
```

### Customer Support

```bash
# Customer-specific running workflows
temporal --env prod -o json --time-format iso workflow list \
  --query "CustomerId = 'customer-123' AND ExecutionStatus = 'Running'"

# Recent customer workflows
temporal --env staging -o json --time-format iso workflow list \
  --query "CustomerId = 'customer-456' AND StartTime > '2025-11-20T00:00:00Z'"

# Customer workflows needing attention
temporal --env prod -o json --time-format iso workflow list \
  --query "CustomerId = 'customer-789' AND ExecutionStatus IN ('Failed', 'TimedOut')"
```

### Urgent Workflows

```bash
# Urgent workflows that need attention
temporal --env prod -o json --time-format iso workflow list \
  --query "IsUrgent = true AND ExecutionStatus IN ('Running', 'Failed')"

# Time-sensitive workflows
temporal --env staging -o json --time-format iso workflow list \
  --query "IsUrgent = true AND DueDate < '2025-11-23T00:00:00Z' AND CloseTime IS NULL"

# High-priority unresolved
temporal --env prod -o json --time-format iso workflow list \
  --query "Priority = 1 AND CloseTime IS NULL"
```

### Business Operations

```bash
# Failed onboarding workflows with retries
temporal --env prod -o json --time-format iso workflow list \
  --query "WorkflowType STARTS_WITH 'patient-onboard' AND ExecutionStatus = 'Failed' AND RetryCount > 3"

# High-value orders in progress
temporal --env staging -o json --time-format iso workflow list \
  --query "WorkflowType = 'OrderProcessing' AND Amount > 1000.0 AND ExecutionStatus = 'Running'"

# Support tickets needing approval
temporal --env prod -o json --time-format iso workflow list \
  --query "WorkflowType STARTS_WITH 'support' AND RequiresApproval = true AND CloseTime IS NULL"

# Recent tenant activity
temporal --env staging -o json --time-format iso workflow list \
  --query "\`tenant-id\` = 'tenant-abc' AND StartTime > '2025-11-20T00:00:00Z'"
```

### Debugging & Analysis

```bash
# Workflows with high retry count
temporal --env prod -o json --time-format iso workflow list \
  --query "RetryCount > 10 AND ExecutionStatus = 'Running'"

# Failed workflows in last hour
temporal --env staging -o json --time-format iso workflow list \
  --query "ExecutionStatus = 'Failed' AND CloseTime > '2025-11-22T14:00:00Z'"

# Specific error pattern (via custom attribute)
temporal --env prod -o json --time-format iso workflow list \
  --query "ErrorType = 'TimeoutError' AND ExecutionStatus = 'Failed'"
```

### Non-Deterministic Error Debugging

**IMPORTANT**: Workflows with non-deterministic errors stay `Running` but are stuck. Use `TemporalReportedProblems`:

```bash
# Find all workflows with WorkflowTask failures (includes non-deterministic errors)
temporal --env prod -o json --time-format iso workflow list \
  --query "ExecutionStatus = 'Running' AND TemporalReportedProblems IN ('category=WorkflowTaskFailed', 'category=WorkflowTaskTimedOut')" \
  --limit 20

# Count affected workflows
temporal --env prod -o json --time-format iso workflow count \
  --query "ExecutionStatus = 'Running' AND TemporalReportedProblems IN ('category=WorkflowTaskFailed')"

# Find by specific workflow type
temporal --env prod -o json --time-format iso workflow list \
  --query "WorkflowType = 'Megaflow' AND ExecutionStatus = 'Running' AND TemporalReportedProblems IN ('category=WorkflowTaskFailed')"
```

**Get error details from workflow history:**
```bash
temporal --env prod -o json --time-format iso workflow show \
  --workflow-id "workflow-id-here" | \
  jq '[.events[] | select(.eventType == "EVENT_TYPE_WORKFLOW_TASK_FAILED")] | .[-1]'
```

---

## Common Mistakes

### ❌ WRONG: LIKE operator

```bash
# ❌ WRONG
temporal --env prod -o json --time-format iso workflow list \
  --query "WorkflowType LIKE '%patient%'"
# Error: operator 'like' not allowed

# ✅ CORRECT
temporal --env prod -o json --time-format iso workflow list \
  --query "WorkflowType STARTS_WITH 'patient'"
```

### ❌ WRONG: Wildcards

```bash
# ❌ WRONG
temporal --env staging -o json --time-format iso workflow list \
  --query "WorkflowType = '*patient*'"
# Wildcards not supported

# ✅ CORRECT
temporal --env staging -o json --time-format iso workflow list \
  --query "WorkflowType STARTS_WITH 'patient'"
```

### ❌ WRONG: Multiple ORs

```bash
# ❌ INEFFICIENT
temporal --env prod -o json --time-format iso workflow list \
  --query "WorkflowType = 'A' OR WorkflowType = 'B' OR WorkflowType = 'C'"

# ✅ BETTER: Use IN
temporal --env prod -o json --time-format iso workflow list \
  --query "WorkflowType IN ('A', 'B', 'C')"
```

### ❌ WRONG: Case-insensitive field names

```bash
# ❌ WRONG
temporal --env staging -o json --time-format iso workflow list \
  --query "workflowtype = 'MyWorkflow'"
# Field names are case-sensitive

# ✅ CORRECT
temporal --env staging -o json --time-format iso workflow list \
  --query "WorkflowType = 'MyWorkflow'"
```

### ❌ WRONG: Quotes on numbers

```bash
# ❌ WRONG
temporal --env prod -o json --time-format iso workflow list \
  --query "Priority = '1'"

# ✅ CORRECT (no quotes for numbers)
temporal --env prod -o json --time-format iso workflow list \
  --query "Priority = 1"
```

### ❌ WRONG: Missing backticks for special chars

```bash
# ❌ WRONG
temporal --env staging -o json --time-format iso workflow list \
  --query "customer-id = 'value'"
# Syntax error

# ✅ CORRECT
temporal --env staging -o json --time-format iso workflow list \
  --query "\`customer-id\` = 'value'"
```

### ❌ WRONG: Unbalanced quotes

```bash
# ❌ WRONG
temporal --env prod -o json --time-format iso workflow list \
  --query "WorkflowType = 'MyFlow"
# Unbalanced quotes

# ✅ CORRECT
temporal --env prod -o json --time-format iso workflow list \
  --query "WorkflowType = 'MyFlow'"
```

---

## Data Type Reference

| Type | Operators | Quote? | Examples |
|------|-----------|--------|----------|
| **Keyword** | `=`, `!=`, `STARTS_WITH`, `IN` | Yes | `'value'`, `'MyWorkflow'` |
| **Text** | `=`, `!=`, `IN` | Yes | `'Full text content'` |
| **Int** | `=`, `!=`, `>`, `>=`, `<`, `<=`, `BETWEEN`, `IN` | No | `123`, `0`, `-456` |
| **Double** | `=`, `!=`, `>`, `>=`, `<`, `<=`, `BETWEEN`, `IN` | No | `123.45`, `0.0`, `-456.78` |
| **Bool** | `=`, `!=` | No | `true`, `false` |
| **Datetime** | `=`, `!=`, `>`, `>=`, `<`, `<=`, `BETWEEN` | Yes | `'2025-01-01T00:00:00Z'` |
| **KeywordList** | `=`, `IN` | Yes | `'value'`, `IN ('val1', 'val2')` |

### Notes by Type

**Keyword:**
- Case-sensitive
- Use `STARTS_WITH` for prefix matching
- Supports `IN` for multiple values

**Text:**
- Full-text searchable
- `STARTS_WITH` NOT supported on Text fields

**Int/Double:**
- No quotes needed
- Supports range queries with `BETWEEN`

**Bool:**
- Must be lowercase: `true` or `false`
- No quotes

**Datetime:**
- ISO 8601 format required
- Always use quotes
- UTC timezone recommended (Z suffix)

**KeywordList:**
- Array of keyword strings
- Use `=` to match exact array
- Use `IN` to match any element

---

## Performance Tips

### ✅ Good: Specific filters

```bash
# Reduces result set significantly
temporal --env prod -o json --time-format iso workflow list \
  --query "WorkflowType = 'OnboardingFlow' AND ExecutionStatus = 'Running'"
```

### ⚠️ Less Efficient: Broad queries

```bash
# Returns many results
temporal --env prod -o json --time-format iso workflow list \
  --query "ExecutionStatus = 'Running'"
```

### ✅ Good: Time ranges

```bash
# Limits scope with time bounds
temporal --env prod -o json --time-format iso workflow list \
  --query "StartTime > '2025-11-01T00:00:00Z' AND ExecutionStatus = 'Failed'"
```

### ✅ Good: Indexed custom attributes

```bash
# If CustomerId is indexed, this is efficient
temporal --env prod -o json --time-format iso workflow list \
  --query "CustomerId = 'customer-123'"
```

### ✅ Good: Use IN instead of multiple ORs

```bash
# More efficient than chaining OR conditions
temporal --env prod -o json --time-format iso workflow list \
  --query "ExecutionStatus IN ('Failed', 'Canceled', 'TimedOut')"
```

## See Also

- [Custom Search Attributes](03-custom-search-attributes.md) - Deep dive on custom fields
- [Command Patterns](01-command-patterns.md) - How to execute queries
- [Error Handling](07-error-handling.md) - Query syntax errors and fixes
- [Smart Patterns](06-smart-patterns.md) - Query validation and auto-retry logic
