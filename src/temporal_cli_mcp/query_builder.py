"""Query builder for Temporal workflow list filters."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Tuple
import re


class ComparisonOperator(Enum):
    """Supported comparison operators for Temporal list filters."""
    EQUALS = "="
    NOT_EQUALS = "!="
    GREATER_THAN = ">"
    GREATER_THAN_OR_EQUAL = ">="
    LESS_THAN = "<"
    LESS_THAN_OR_EQUAL = "<="
    STARTS_WITH = "STARTS_WITH"


class LogicalOperator(Enum):
    """Supported logical operators for combining filters."""
    AND = "AND"
    OR = "OR"


class SupportedField(Enum):
    """Supported fields for Temporal workflow queries."""
    WORKFLOW_ID = "WorkflowId"
    WORKFLOW_TYPE = "WorkflowType"
    EXECUTION_STATUS = "ExecutionStatus"
    START_TIME = "StartTime"
    CLOSE_TIME = "CloseTime"
    EXECUTION_TIME = "ExecutionTime"


class ExecutionStatus(Enum):
    """Valid execution status values."""
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELED = "Canceled"
    TERMINATED = "Terminated"
    CONTINUED_AS_NEW = "ContinuedAsNew"
    TIMED_OUT = "TimedOut"


# Mapping of commonly used unsupported operators to suggested alternatives
UNSUPPORTED_OPERATORS = {
    "LIKE": "STARTS_WITH",
    "ILIKE": "STARTS_WITH", 
    "CONTAINS": "STARTS_WITH",
    "MATCH": "STARTS_WITH",
    "REGEXP": "STARTS_WITH",
    "REGEX": "STARTS_WITH",
    "SIMILAR TO": "STARTS_WITH",
    "~": "STARTS_WITH",
    "~~": "STARTS_WITH",
    "!~~": "!=",
    "NOT LIKE": "!=",
    "NOT ILIKE": "!=",
}


class TemporalQueryBuilder:
    """Builder for constructing Temporal workflow list filter queries."""

    def __init__(self):
        self._conditions: List[str] = []

    def workflow_id(self, value: str, operator: ComparisonOperator = ComparisonOperator.EQUALS) -> "TemporalQueryBuilder":
        """Add a WorkflowId filter."""
        return self._add_condition(SupportedField.WORKFLOW_ID, value, operator)

    def workflow_type(self, value: str, operator: ComparisonOperator = ComparisonOperator.EQUALS) -> "TemporalQueryBuilder":
        """Add a WorkflowType filter."""
        return self._add_condition(SupportedField.WORKFLOW_TYPE, value, operator)

    def execution_status(self, status: Union[ExecutionStatus, str], operator: ComparisonOperator = ComparisonOperator.EQUALS) -> "TemporalQueryBuilder":
        """Add an ExecutionStatus filter."""
        status_value = status.value if isinstance(status, ExecutionStatus) else status
        return self._add_condition(SupportedField.EXECUTION_STATUS, status_value, operator)

    def start_time(self, time: Union[datetime, str], operator: ComparisonOperator = ComparisonOperator.GREATER_THAN) -> "TemporalQueryBuilder":
        """Add a StartTime filter."""
        time_value = time.isoformat() if isinstance(time, datetime) else time
        return self._add_condition(SupportedField.START_TIME, time_value, operator)

    def close_time(self, time: Union[datetime, str], operator: ComparisonOperator = ComparisonOperator.LESS_THAN) -> "TemporalQueryBuilder":
        """Add a CloseTime filter."""
        time_value = time.isoformat() if isinstance(time, datetime) else time
        return self._add_condition(SupportedField.CLOSE_TIME, time_value, operator)

    def execution_time(self, time: Union[datetime, str], operator: ComparisonOperator = ComparisonOperator.GREATER_THAN) -> "TemporalQueryBuilder":
        """Add an ExecutionTime filter."""
        time_value = time.isoformat() if isinstance(time, datetime) else time
        return self._add_condition(SupportedField.EXECUTION_TIME, time_value, operator)

    def workflow_id_in(self, workflow_ids: List[str]) -> "TemporalQueryBuilder":
        """Add a WorkflowId IN filter."""
        values = ", ".join([f"'{self._escape_value(wid)}'" for wid in workflow_ids])
        condition = f"{SupportedField.WORKFLOW_ID.value} IN ({values})"
        self._conditions.append(condition)
        return self

    def workflow_type_starts_with(self, prefix: str) -> "TemporalQueryBuilder":
        """Add a WorkflowType STARTS_WITH filter."""
        return self._add_condition(SupportedField.WORKFLOW_TYPE, prefix, ComparisonOperator.STARTS_WITH)

    def time_range(self, field: SupportedField, start: Union[datetime, str], end: Union[datetime, str]) -> "TemporalQueryBuilder":
        """Add a time range filter using BETWEEN."""
        if field not in [SupportedField.START_TIME, SupportedField.CLOSE_TIME, SupportedField.EXECUTION_TIME]:
            raise ValueError(f"Time range filters only supported for time fields, got: {field}")
        
        start_value = start.isoformat() if isinstance(start, datetime) else start
        end_value = end.isoformat() if isinstance(end, datetime) else end
        
        condition = f"{field.value} BETWEEN '{self._escape_value(start_value)}' AND '{self._escape_value(end_value)}'"
        self._conditions.append(condition)
        return self

    def and_condition(self, builder: "TemporalQueryBuilder") -> "TemporalQueryBuilder":
        """Combine with another query using AND."""
        if builder._conditions:
            other_query = builder.build()
            if self._conditions:
                self._conditions = [f"({' AND '.join(self._conditions)}) AND ({other_query})"]
            else:
                self._conditions = [other_query]
        return self

    def or_condition(self, builder: "TemporalQueryBuilder") -> "TemporalQueryBuilder":
        """Combine with another query using OR."""
        if builder._conditions:
            other_query = builder.build()
            if self._conditions:
                self._conditions = [f"({' AND '.join(self._conditions)}) OR ({other_query})"]
            else:
                self._conditions = [other_query]
        return self

    def custom_condition(self, condition: str) -> "TemporalQueryBuilder":
        """Add a custom condition string (use with caution)."""
        if not condition.strip():
            raise ValueError("Custom condition cannot be empty")
        self._conditions.append(condition.strip())
        return self

    def build(self) -> str:
        """Build the final query string."""
        if not self._conditions:
            return ""
        return " AND ".join(self._conditions)

    def _add_condition(self, field: SupportedField, value: str, operator: ComparisonOperator) -> "TemporalQueryBuilder":
        """Add a single condition to the query."""
        escaped_value = self._escape_value(value)
        
        if operator == ComparisonOperator.STARTS_WITH:
            condition = f"{field.value} {operator.value} '{escaped_value}'"
        else:
            condition = f"{field.value} {operator.value} '{escaped_value}'"
        
        self._conditions.append(condition)
        return self

    def _escape_value(self, value: str) -> str:
        """Escape special characters in query values."""
        return value.replace("'", "''").replace("\\", "\\\\")

    @classmethod
    def validate_query(cls, query: str) -> Tuple[bool, List[str]]:
        """Validate a query string for syntax correctness and supported operators.
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        if not query or not query.strip():
            return True, []  # Empty queries are valid
        
        errors = []
        
        # Basic validation - check for balanced quotes and parentheses
        single_quotes = query.count("'")
        if single_quotes % 2 != 0:
            errors.append("Unbalanced single quotes in query")
        
        open_parens = query.count("(")
        close_parens = query.count(")")
        if open_parens != close_parens:
            errors.append("Unbalanced parentheses in query")
        
        # Check for supported fields
        supported_field_names = [field.value for field in SupportedField]
        has_supported_field = any(field_name in query for field_name in supported_field_names)
        
        if not has_supported_field:
            errors.append(f"Query must contain at least one supported field: {', '.join(supported_field_names)}")
        
        # Check for unsupported operators
        unsupported_found = []
        for unsupported_op, suggested_op in UNSUPPORTED_OPERATORS.items():
            # For single character operators, don't use word boundaries
            if len(unsupported_op) == 1:
                pattern = re.escape(unsupported_op)
            else:
                # Use word boundaries for multi-character operators to avoid false positives
                pattern = r'\b' + re.escape(unsupported_op) + r'\b'
            
            if re.search(pattern, query, re.IGNORECASE):
                unsupported_found.append((unsupported_op, suggested_op))
        
        if unsupported_found:
            for unsupported_op, suggested_op in unsupported_found:
                errors.append(f"Unsupported operator '{unsupported_op}'. Use '{suggested_op}' instead.")
        
        # Check for other potentially problematic patterns
        if re.search(r'%', query):
            errors.append("Wildcard '%' is not supported. Use 'STARTS_WITH' for prefix matching.")
        
        if re.search(r'\*', query):
            errors.append("Wildcard '*' is not supported. Use 'STARTS_WITH' for prefix matching.")
        
        return len(errors) == 0, errors

    @classmethod
    def get_validation_help(cls, query: str) -> Dict[str, Any]:
        """Get detailed validation results with helpful suggestions.
        
        Returns:
            Dictionary with validation status, errors, and suggestions
        """
        is_valid, errors = cls.validate_query(query)
        
        suggestions = []
        if not is_valid:
            # Generate specific suggestions based on detected issues
            for error in errors:
                if "LIKE" in error:
                    suggestions.append("For pattern matching, use: WorkflowType STARTS_WITH 'prefix'")
                elif "%" in error or "*" in error:
                    suggestions.append("For prefix matching, use: WorkflowType STARTS_WITH 'onboard'")
                elif "Unbalanced" in error:
                    suggestions.append("Check that all quotes and parentheses are properly closed")
                elif "supported field" in error:
                    suggestions.append(f"Available fields: {', '.join(cls.get_supported_fields())}")
        
        return {
            "is_valid": is_valid,
            "errors": errors,
            "suggestions": suggestions,
            "supported_fields": cls.get_supported_fields(),
            "supported_operators": cls.get_supported_operators(),
            "examples": [
                "WorkflowType = 'OnboardingFlow'",
                "WorkflowType STARTS_WITH 'patient'",
                "ExecutionStatus = 'Failed'",
                "WorkflowId IN ('id1', 'id2')",
                "StartTime > '2025-01-01T00:00:00Z'"
            ]
        }

    @classmethod
    def get_supported_fields(cls) -> List[str]:
        """Get list of all supported field names."""
        return [field.value for field in SupportedField]

    @classmethod
    def get_supported_operators(cls) -> List[str]:
        """Get list of all supported operators."""
        return [op.value for op in ComparisonOperator]

    @classmethod
    def get_execution_statuses(cls) -> List[str]:
        """Get list of all valid execution status values."""
        return [status.value for status in ExecutionStatus]


def create_query_builder() -> TemporalQueryBuilder:
    """Factory function to create a new query builder instance."""
    return TemporalQueryBuilder()