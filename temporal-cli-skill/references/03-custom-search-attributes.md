# Custom Search Attributes Guide

Deep dive into using custom search attributes in Temporal workflow queries.

## Table of Contents

- [Overview](#overview)
- [Custom Attribute Types](#custom-attribute-types)
- [Field Naming Rules](#field-naming-rules)
- [Backtick Escaping](#backtick-escaping)
- [Querying by Type](#querying-by-type)
- [Real-World Use Cases](#real-world-use-cases)
- [Best Practices](#best-practices)

## Overview

Custom search attributes extend Temporal's default fields with business-specific metadata. They must be configured in your Temporal cluster before use.

### Prerequisites

1. Custom attributes must be added to your Temporal cluster configuration
2. Workflows must set these attributes during execution
3. Attributes are indexed for query performance

### Standard vs Custom Fields

**Standard fields** (built-in):
- `WorkflowType`, `WorkflowId`, `ExecutionStatus`
- `StartTime`, `CloseTime`, `TaskQueue`
- Always available, no configuration needed

**Custom fields** (user-defined):
- `CustomerId`, `TenantId`, `Priority`
- `Environment`, `Region`, `Amount`
- Require cluster configuration and indexing

---

## Custom Attribute Types

Temporal supports 7 custom search attribute types:

| Type | Description | Quote? | Operators | Example Values |
|------|-------------|--------|-----------|----------------|
| **Keyword** | Case-sensitive string | Yes | `=`, `!=`, `STARTS_WITH`, `IN` | `'customer-123'` |
| **Text** | Full-text searchable | Yes | `=`, `!=`, `IN` | `'Full description'` |
| **Int** | Integer numbers | No | `=`, `!=`, `>`, `>=`, `<`, `<=`, `IN`, `BETWEEN` | `123`, `-456` |
| **Double** | Floating-point | No | `=`, `!=`, `>`, `>=`, `<`, `<=`, `IN`, `BETWEEN` | `99.99`, `-12.5` |
| **Bool** | Boolean values | No | `=`, `!=` | `true`, `false` |
| **Datetime** | Timestamps | Yes | `=`, `!=`, `>`, `>=`, `<`, `<=`, `BETWEEN` | `'2025-01-01T00:00:00Z'` |
| **KeywordList** | Array of keywords | Yes | `=`, `IN` | `'tag1'`, `IN ('tag1', 'tag2')` |

---

## Field Naming Rules

### Valid Characters

**Alphanumeric + underscore only** (no backticks needed):
```bash
CustomerId
TenantId
customer_id
tenant_id123
```

**Special characters** (backticks required):
```bash
`customer-id`      # Contains hyphen
`user.email`       # Contains dot
`tenant-name`      # Contains hyphen
`api-version`      # Contains hyphen
`my@field`         # Contains @
```

### Naming Conventions

**Recommended patterns:**
- CamelCase: `CustomerId`, `IsUrgent`, `RetryCount`
- snake_case: `customer_id`, `is_urgent`, `retry_count`
- Avoid: hyphens, dots, spaces (require backticks)

---

## Backtick Escaping

### When to Use Backticks

Use backticks when field names contain:
- Hyphens: `-`
- Dots: `.`
- Spaces: ` `
- Special characters: `@`, `#`, etc.

### Examples

```bash
# ✅ No backticks needed (alphanumeric + underscore)
temporal --env prod -o json --time-format iso workflow list \
  --query "CustomerId = 'value'"

# ✅ Backticks required (contains hyphen)
temporal --env prod -o json --time-format iso workflow list \
  --query "\`customer-id\` = 'value'"

# ✅ Backticks required (contains dot)
temporal --env staging -o json --time-format iso workflow list \
  --query "\`user.email\` = 'user@example.com'"

# ✅ Backticks required (contains hyphen)
temporal --env prod -o json --time-format iso workflow list \
  --query "\`tenant-id\` = 'tenant-123'"
```

### Bash Escaping

In bash, use backslash before backticks:

```bash
# Correct bash escaping
temporal --env prod -o json --time-format iso workflow list \
  --query "\`my-field\` = 'value'"

# Or use single quotes for the whole query
temporal --env prod -o json --time-format iso workflow list \
  --query '`my-field` = '"'"'value'"'"''
```

---

## Querying by Type

### Keyword Type

**Characteristics:**
- Case-sensitive strings
- Supports prefix matching with `STARTS_WITH`
- Best for IDs, codes, enums

**Examples:**

```bash
# Exact match
temporal --env prod -o json --time-format iso workflow list \
  --query "CustomerId = 'customer-abc-123'"

# Prefix matching
temporal --env staging -o json --time-format iso workflow list \
  --query "CustomerId STARTS_WITH 'customer-'"

# Multiple values
temporal --env prod -o json --time-format iso workflow list \
  --query "Environment IN ('staging', 'prod', 'dev')"

# Not equal
temporal --env staging -o json --time-format iso workflow list \
  --query "Region != 'us-east-1'"

# Combined with standard fields
temporal --env prod -o json --time-format iso workflow list \
  --query "CustomerId = 'cust-123' AND ExecutionStatus = 'Running'"
```

### Text Type

**Characteristics:**
- Full-text searchable
- `STARTS_WITH` NOT supported
- Best for descriptions, notes

**Examples:**

```bash
# Exact match
temporal --env prod -o json --time-format iso workflow list \
  --query "Description = 'Patient onboarding workflow'"

# Multiple values
temporal --env staging -o json --time-format iso workflow list \
  --query "Category IN ('urgent', 'normal', 'low-priority')"

# Note: STARTS_WITH not supported on Text fields
# ❌ This will error:
# --query "Description STARTS_WITH 'Patient'"
```

### Int Type

**Characteristics:**
- Integer numbers only
- No quotes
- Supports comparisons and ranges

**Examples:**

```bash
# Exact match
temporal --env prod -o json --time-format iso workflow list \
  --query "Priority = 1"

# Comparison
temporal --env staging -o json --time-format iso workflow list \
  --query "RetryCount > 5"

temporal --env prod -o json --time-format iso workflow list \
  --query "AttemptNumber >= 3"

temporal --env staging -o json --time-format iso workflow list \
  --query "CustomIntField < 100"

# Range
temporal --env prod -o json --time-format iso workflow list \
  --query "Priority BETWEEN 1 AND 5"

temporal --env staging -o json --time-format iso workflow list \
  --query "Age >= 18 AND Age <= 65"

# Multiple values
temporal --env prod -o json --time-format iso workflow list \
  --query "Priority IN (1, 2, 3)"
```

### Double Type

**Characteristics:**
- Floating-point numbers
- No quotes
- Supports decimals, scientific notation

**Examples:**

```bash
# Exact match
temporal --env prod -o json --time-format iso workflow list \
  --query "Amount = 99.99"

# Comparison
temporal --env staging -o json --time-format iso workflow list \
  --query "Price > 10.50"

temporal --env prod -o json --time-format iso workflow list \
  --query "Discount <= 0.15"

# Range
temporal --env staging -o json --time-format iso workflow list \
  --query "Amount BETWEEN 10.0 AND 100.0"

# Combined
temporal --env prod -o json --time-format iso workflow list \
  --query "Amount > 1000.0 AND ExecutionStatus = 'Running'"
```

### Bool Type

**Characteristics:**
- `true` or `false` (lowercase)
- No quotes
- Only `=` and `!=` operators

**Examples:**

```bash
# True condition
temporal --env prod -o json --time-format iso workflow list \
  --query "IsUrgent = true"

# False condition
temporal --env staging -o json --time-format iso workflow list \
  --query "HasErrors = false"

# Combined conditions
temporal --env prod -o json --time-format iso workflow list \
  --query "IsUrgent = true AND RequiresApproval = false"

temporal --env staging -o json --time-format iso workflow list \
  --query "IsCompleted = true AND HasErrors = false"

# NOT operator simulation
temporal --env prod -o json --time-format iso workflow list \
  --query "RequiresApproval != true"
```

### Datetime Type

**Characteristics:**
- ISO 8601 format
- Must use quotes
- Supports comparisons and ranges

**Examples:**

```bash
# After date
temporal --env prod -o json --time-format iso workflow list \
  --query "CustomCreatedAt > '2025-01-01T00:00:00Z'"

# Before date
temporal --env staging -o json --time-format iso workflow list \
  --query "LastUpdatedAt <= '2025-11-22T23:59:59Z'"

# Range
temporal --env prod -o json --time-format iso workflow list \
  --query "DueDate BETWEEN '2025-11-01T00:00:00Z' AND '2025-11-30T23:59:59Z'"

# Time-sensitive workflows
temporal --env staging -o json --time-format iso workflow list \
  --query "DueDate < '2025-11-23T00:00:00Z' AND CloseTime IS NULL"

# Exact timestamp
temporal --env prod -o json --time-format iso workflow list \
  --query "ScheduledTime = '2025-11-22T10:00:00Z'"
```

### KeywordList Type

**Characteristics:**
- Array of keyword strings
- Use `=` for exact array match
- Use `IN` to match any element

**Examples:**

```bash
# Match any tag in the list
temporal --env prod -o json --time-format iso workflow list \
  --query "Tags = 'urgent'"

# Match any of several values
temporal --env staging -o json --time-format iso workflow list \
  --query "Tags IN ('urgent', 'customer-facing', 'production')"

# Combined with other fields
temporal --env prod -o json --time-format iso workflow list \
  --query "Tags = 'high-priority' AND ExecutionStatus = 'Running'"
```

---

## Real-World Use Cases

### E-Commerce

```bash
# High-value orders
temporal --env prod -o json --time-format iso workflow list \
  --query "WorkflowType = 'OrderProcessing' AND Amount > 1000.0"

# Orders by customer
temporal --env staging -o json --time-format iso workflow list \
  --query "CustomerId = 'cust-456' AND StartTime > '2025-11-01T00:00:00Z'"

# Urgent unfulfilled orders
temporal --env prod -o json --time-format iso workflow list \
  --query "IsUrgent = true AND IsFulfilled = false AND ExecutionStatus = 'Running'"

# Orders in specific region
temporal --env staging -o json --time-format iso workflow list \
  --query "Region = 'us-west-2' AND ExecutionStatus IN ('Running', 'Failed')"
```

### Healthcare/Patient Onboarding

```bash
# Patient workflows by priority
temporal --env prod -o json --time-format iso workflow list \
  --query "WorkflowType STARTS_WITH 'patient' AND Priority = 1"

# Failed onboardings with retries
temporal --env staging -o json --time-format iso workflow list \
  --query "WorkflowType = 'PatientOnboarding' AND ExecutionStatus = 'Failed' AND RetryCount > 3"

# Onboarding by clinic
temporal --env prod -o json --time-format iso workflow list \
  --query "ClinicId = 'clinic-789' AND ExecutionStatus = 'Running'"

# Urgent patient cases
temporal --env staging -o json --time-format iso workflow list \
  --query "IsUrgent = true AND PatientAge >= 65"
```

### Multi-Tenant SaaS

```bash
# Workflows by tenant
temporal --env prod -o json --time-format iso workflow list \
  --query "\`tenant-id\` = 'tenant-abc'"

# Tenant failures in production
temporal --env prod -o json --time-format iso workflow list \
  --query "\`tenant-id\` = 'tenant-xyz' AND Environment = 'prod' AND ExecutionStatus = 'Failed'"

# All tenants in specific region
temporal --env staging -o json --time-format iso workflow list \
  --query "Region = 'eu-west-1' AND ExecutionStatus = 'Running'"

# Premium tier customers
temporal --env prod -o json --time-format iso workflow list \
  --query "TierLevel = 'premium' AND IsActive = true"
```

### Financial Services

```bash
# Transactions above threshold
temporal --env prod -o json --time-format iso workflow list \
  --query "TransactionAmount > 10000.0 AND RequiresApproval = true"

# Failed payment workflows
temporal --env staging -o json --time-format iso workflow list \
  --query "WorkflowType = 'PaymentProcessing' AND ExecutionStatus = 'Failed'"

# Compliance review needed
temporal --env prod -o json --time-format iso workflow list \
  --query "RequiresCompliance = true AND ReviewStatus = 'pending'"

# High-risk transactions
temporal --env staging -o json --time-format iso workflow list \
  --query "RiskScore > 75.0 AND ExecutionStatus = 'Running'"
```

### DevOps/CI-CD

```bash
# Deployments by environment
temporal --env prod -o json --time-format iso workflow list \
  --query "WorkflowType = 'Deployment' AND Environment = 'prod'"

# Failed builds in last hour
temporal --env staging -o json --time-format iso workflow list \
  --query "WorkflowType = 'BuildPipeline' AND ExecutionStatus = 'Failed' AND CloseTime > '2025-11-22T14:00:00Z'"

# Deployments by build ID
temporal --env prod -o json --time-format iso workflow list \
  --query "BuildIds = 'build-v1.2.3' AND Environment IN ('staging', 'prod')"

# Long-running deployments
temporal --env staging -o json --time-format iso workflow list \
  --query "WorkflowType = 'Deployment' AND ExecutionStatus = 'Running' AND StartTime < '2025-11-22T12:00:00Z'"
```

---

## Best Practices

### 1. Use Meaningful Names

```bash
# ✅ GOOD: Clear, descriptive
CustomerId
TenantId
IsUrgent
Priority
Environment

# ❌ AVOID: Vague or abbreviated
cid
tid
u
p
env
```

### 2. Choose the Right Type

```bash
# ✅ GOOD: Int for numeric priority
Priority = 1

# ❌ WRONG: Keyword for numbers
Priority = '1'

# ✅ GOOD: Bool for flags
IsUrgent = true

# ❌ WRONG: Keyword for boolean
IsUrgent = 'true'
```

### 3. Avoid Special Characters

```bash
# ✅ GOOD: CamelCase (no backticks needed)
CustomerId = 'value'
TenantId = 'value'

# ⚠️ ACCEPTABLE: But requires backticks
`customer-id` = 'value'
`tenant-id` = 'value'
```

### 4. Index Frequently Queried Fields

Ensure your most-used custom attributes are indexed in the Temporal cluster for performance.

**Common indexes:**
- `CustomerId` (Keyword)
- `TenantId` (Keyword)
- `Priority` (Int)
- `Environment` (Keyword)
- `IsUrgent` (Bool)

### 5. Combine with Standard Fields

```bash
# ✅ GOOD: Narrow results with standard + custom
temporal --env prod -o json --time-format iso workflow list \
  --query "WorkflowType = 'OrderProcessing' AND CustomerId = 'cust-123' AND ExecutionStatus = 'Running'"
```

### 6. Use STARTS_WITH for Flexible Matching

```bash
# ✅ GOOD: Find all customers with prefix
temporal --env prod -o json --time-format iso workflow list \
  --query "CustomerId STARTS_WITH 'enterprise-'"

# Find all tenants in region
temporal --env staging -o json --time-format iso workflow list \
  --query "TenantId STARTS_WITH 'us-west-'"
```

### 7. Validate Custom Attributes

Before querying, verify:
1. Attribute exists in cluster config
2. Attribute type matches query operators
3. Field name uses correct casing/escaping

---

## Configuration Example

Custom attributes must be configured in your Temporal cluster. Example configuration:

```yaml
# Example: Temporal cluster search attributes config
customSearchAttributes:
  CustomerId:
    type: Keyword
  TenantId:
    type: Keyword
  Priority:
    type: Int
  Amount:
    type: Double
  IsUrgent:
    type: Bool
  DueDate:
    type: Datetime
  Tags:
    type: KeywordList
  Environment:
    type: Keyword
  Region:
    type: Keyword
```

**Note:** Consult your Temporal cluster administrator for the exact configuration method.

---

## Troubleshooting

### Unknown Field Error

```bash
# Error: "unknown field CustomerId"
# Solution: Verify field is configured in cluster
```

### Type Mismatch

```bash
# Error: Priority = '1'  (using quotes on Int field)
# Solution: Remove quotes for numeric types
Priority = 1
```

### STARTS_WITH on Text Field

```bash
# Error: STARTS_WITH on Text field
# Solution: Text fields don't support STARTS_WITH, use = or IN
Description = 'exact match'
```

### Backtick Errors

```bash
# Error: customer-id = 'value'  (missing backticks)
# Solution: Use backticks for special characters
`customer-id` = 'value'
```

## See Also

- [Query Construction](02-query-construction.md) - Complete query syntax
- [Command Patterns](01-command-patterns.md) - How to execute queries
- [Error Handling](07-error-handling.md) - Troubleshooting query errors
