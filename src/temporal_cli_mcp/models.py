"""Pydantic models for input validation."""

from typing import Optional
from pydantic import BaseModel, Field, validator


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
    follow: bool = False