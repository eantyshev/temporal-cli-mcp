"""Pydantic models for input validation."""

from datetime import datetime
from typing import List, Optional, Union
from pydantic import BaseModel, Field, validator, model_validator
from enum import Enum


class WorkflowListRequest(BaseModel):
    """Model for list_workflows parameters."""
    query: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=1000)


class WorkflowDescribeRequest(BaseModel):
    """Model for describe_workflow parameters."""
    workflow_id: str = Field(..., min_length=1)


class WorkflowStartRequest(BaseModel):
    """Model for start_workflow parameters."""
    workflow_type: str = Field(..., min_length=1)
    task_queue: str = Field(..., min_length=1)
    workflow_id: Optional[str] = None
    input_data: Optional[str] = None


class WorkflowSignalRequest(BaseModel):
    """Model for signal_workflow parameters."""
    workflow_id: str = Field(..., min_length=1)
    signal_name: str = Field(..., min_length=1)
    input_data: Optional[str] = None


class WorkflowQueryRequest(BaseModel):
    """Model for query_workflow parameters."""
    workflow_id: str = Field(..., min_length=1)
    query_type: str = Field(..., min_length=1)
    input_data: Optional[str] = None


class WorkflowCancelRequest(BaseModel):
    """Model for cancel_workflow parameters."""
    workflow_id: str = Field(..., min_length=1)


class WorkflowTerminateRequest(BaseModel):
    """Model for terminate_workflow parameters."""
    workflow_id: str = Field(..., min_length=1)
    reason: Optional[str] = None


class WorkflowHistoryRequest(BaseModel):
    """Model for get_workflow_history parameters."""
    workflow_id: str = Field(..., min_length=1)
    run_id: Optional[str] = None
    decode_payloads: bool = True


class WorkflowStackRequest(BaseModel):
    """Model for trace_workflow parameters."""
    workflow_id: str = Field(..., min_length=1)
    run_id: Optional[str] = None


class FieldFilter(BaseModel):
    """Model for a single field filter in workflow queries."""
    field: str = Field(..., min_length=1)
    operator: str = Field(..., min_length=1)
    value: str = Field(..., min_length=1)

    @validator('operator')
    def validate_operator(cls, v):
        valid_operators = ["=", "!=", ">", ">=", "<", "<=", "STARTS_WITH"]
        if v not in valid_operators:
            raise ValueError(f"Operator must be one of: {valid_operators}")
        return v

    @validator('field')
    def validate_field(cls, v):
        valid_fields = ["WorkflowId", "WorkflowType", "ExecutionStatus", "StartTime", "CloseTime", "ExecutionTime"]
        if v not in valid_fields:
            raise ValueError(f"Field must be one of: {valid_fields}")
        return v


class TimeRangeFilter(BaseModel):
    """Model for time range filters in workflow queries."""
    field: str = Field(..., min_length=1)
    start_time: Union[datetime, str]
    end_time: Union[datetime, str]

    @validator('field')
    def validate_time_field(cls, v):
        valid_time_fields = ["StartTime", "CloseTime", "ExecutionTime"]
        if v not in valid_time_fields:
            raise ValueError(f"Time field must be one of: {valid_time_fields}")
        return v


class InFilter(BaseModel):
    """Model for IN filters in workflow queries."""
    field: str = Field(..., min_length=1)
    values: List[str] = Field(..., min_items=1)

    @validator('field')
    def validate_field(cls, v):
        valid_fields = ["WorkflowId", "WorkflowType", "ExecutionStatus"]
        if v not in valid_fields:
            raise ValueError(f"IN filter field must be one of: {valid_fields}")
        return v


class StructuredQuery(BaseModel):
    """Model for structured workflow query building."""
    field_filters: Optional[List[FieldFilter]] = None
    time_range_filters: Optional[List[TimeRangeFilter]] = None
    in_filters: Optional[List[InFilter]] = None
    logical_operator: str = Field(default="AND")

    @validator('logical_operator')
    def validate_logical_operator(cls, v):
        if v not in ["AND", "OR"]:
            raise ValueError("Logical operator must be 'AND' or 'OR'")
        return v


class QueryBuildRequest(BaseModel):
    """Model for build_workflow_query parameters."""
    structured_query: Optional[StructuredQuery] = None
    raw_conditions: Optional[List[str]] = None
    logical_operator: str = Field(default="AND")

    @validator('logical_operator')
    def validate_logical_operator(cls, v):
        if v not in ["AND", "OR"]:
            raise ValueError("Logical operator must be 'AND' or 'OR'")
        return v


class QueryValidationRequest(BaseModel):
    """Model for validate_workflow_query parameters."""
    query: str = Field(..., min_length=1)


class EnhancedWorkflowListRequest(BaseModel):
    """Enhanced model for list_workflows with structured query support."""
    query: Optional[str] = None
    structured_query: Optional[StructuredQuery] = None
    limit: int = Field(default=10, ge=1, le=1000)

    @model_validator(mode='before')
    def validate_query_options(cls, values):
        if isinstance(values, dict):
            query = values.get('query')
            structured_query = values.get('structured_query')
            
            if query and structured_query:
                raise ValueError("Cannot specify both 'query' and 'structured_query'")
        
        return values