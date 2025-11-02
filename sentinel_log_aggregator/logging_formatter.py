"""
Standardized logging formatter for consistent log formatting across the Sentinel Log Aggregator.

This module provides structured logging formatters that ensure consistent message formatting,
proper context tracking, and enhanced traceability for debugging and monitoring.
"""

import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from enum import Enum


class LogEventType(Enum):
    """Standard log event types for consistent categorization."""
    BATCH_START = "BATCH_START"
    BATCH_END = "BATCH_END"
    QUERY_START = "QUERY_START"
    QUERY_END = "QUERY_END"
    UPLOAD_START = "UPLOAD_START"
    UPLOAD_END = "UPLOAD_END"
    WORKSPACE_CONFIG = "WORKSPACE_CONFIG"
    ERROR = "ERROR"
    PROGRESS = "PROGRESS"
    SUMMARY = "SUMMARY"


class SentinelLogFormatter:
    """
    Standardized log message formatter for Sentinel Log Aggregator.
    
    Provides consistent formatting with structured context information
    including job correlation IDs, workspace aliases, query names, and metrics.
    """
    
    @staticmethod
    def format_batch_start(job_id: str, days_back: int, batch_hours: int, workspace_count: int) -> str:
        """Format batch execution start message."""
        return f"[BATCH_START] Job: {job_id} | Range: {days_back}d ({batch_hours}h batches) | Workspaces: {workspace_count}"
    
    @staticmethod
    def format_batch_end(job_id: str, summary: Dict[str, Any]) -> str:
        """Format batch execution summary message."""
        return (f"[BATCH_END] Job: {job_id} | "
                f"Queries: {summary.get('successful_queries', 0)}/{summary.get('total_queries', 0)} | "
                f"Uploads: {summary.get('successful_uploads', 0)}/{summary.get('total_uploads', 0)} | "
                f"Records: {summary.get('total_records', 0):,} retrieved, {summary.get('total_uploaded', 0):,} uploaded | "
                f"Duration: {summary.get('total_duration', 0):.1f}s")
    
    @staticmethod
    def format_query_start(job_id: str, query_name: str, workspace_alias: str, time_range: str) -> str:
        """Format query execution start message."""
        return f"[QUERY_START] Job: {job_id} | Query: {query_name} | Workspace: {workspace_alias} | TimeRange: {time_range}"
    
    @staticmethod
    def format_query_end(job_id: str, query_name: str, workspace_alias: str, 
                        record_count: int, duration: float, success: bool = True) -> str:
        """Format query execution completion message."""
        status = "SUCCESS" if success else "FAILED"
        
        # Handle potential MagicMock objects in format strings
        try:
            duration_str = f"{duration:.2f}s"
        except (TypeError, ValueError):
            duration_str = str(duration)
            
        try:
            record_str = f"{record_count:,}"
        except (TypeError, ValueError):
            record_str = str(record_count)
        
        return (f"[QUERY_END] Job: {job_id} | Query: {query_name} | Workspace: {workspace_alias} | "
                f"Status: {status} | Records: {record_str} | Duration: {duration_str}")
    
    @staticmethod
    def format_upload_start(job_id: str, query_name: str, workspace_alias: str, record_count: int) -> str:
        """Format data upload start message."""
        try:
            record_str = f"{record_count:,}"
        except (TypeError, ValueError):
            record_str = str(record_count)
        return f"[UPLOAD_START] Job: {job_id} | Query: {query_name} | Workspace: {workspace_alias} | Records: {record_str}"
    
    @staticmethod
    def format_upload_end(job_id: str, query_name: str, workspace_alias: str, 
                         uploaded_count: int, duration: float, success: bool = True) -> str:
        """Format data upload completion message."""
        status = "SUCCESS" if success else "FAILED"
        
        # Handle potential MagicMock objects in format strings
        try:
            uploaded_str = f"{uploaded_count:,}"
        except (TypeError, ValueError):
            uploaded_str = str(uploaded_count)
            
        try:
            duration_str = f"{duration:.2f}s"
        except (TypeError, ValueError):
            duration_str = str(duration)
            
        return (f"[UPLOAD_END] Job: {job_id} | Query: {query_name} | Workspace: {workspace_alias} | "
                f"Status: {status} | Uploaded: {uploaded_str} | Duration: {duration_str}")
    
    @staticmethod
    def format_error(job_id: str, component: str, query_name: Optional[str] = None, 
                    workspace_alias: Optional[str] = None, error_message: str = "", 
                    error_type: Optional[str] = None) -> str:
        """Format error message with full context."""
        context_parts = [f"Job: {job_id}", f"Component: {component}"]
        
        if query_name:
            context_parts.append(f"Query: {query_name}")
        if workspace_alias:
            context_parts.append(f"Workspace: {workspace_alias}")
        if error_type:
            context_parts.append(f"ErrorType: {error_type}")
            
        context = " | ".join(context_parts)
        return f"{context} | Message: {error_message}"
    
    @staticmethod
    def format_progress(job_id: str, completed: int, total: int, 
                       additional_info: Optional[str] = None) -> str:
        """Format progress update message."""
        percentage = (completed / total * 100) if total > 0 else 0
        base_msg = f"[PROGRESS] Job: {job_id} | Completed: {completed}/{total} ({percentage:.1f}%)"
        
        if additional_info:
            base_msg += f" | {additional_info}"
            
        return base_msg
    
    @staticmethod
    def format_workspace_config(workspace_count: int, report_count: int, 
                              subscription_count: int, error_count: int = 0) -> str:
        """Format workspace configuration summary."""
        status = "VALID" if error_count == 0 else f"ERRORS ({error_count})"
        return (f"[WORKSPACE_CONFIG] Status: {status} | "
                f"Workspaces: {workspace_count} | Reports: {report_count} | Subscriptions: {subscription_count}")
    
    @staticmethod
    def format_config_validation(component: str, is_valid: bool, 
                               details: Optional[str] = None) -> str:
        """Format configuration validation message."""
        status = "VALID" if is_valid else "INVALID"
        base_msg = f"[CONFIG_VALIDATION] Component: {component} | Status: {status}"
        
        if details:
            base_msg += f" | Details: {details}"
            
        return base_msg
    
    @staticmethod
    def format_batch_summary(job_id: str, summary_data: Dict[str, Any]) -> str:
        """Format batch execution summary."""
        overview = summary_data.get('overview', {})
        
        return (f"[BATCH_SUMMARY] Job: {job_id} | "
                f"Workspaces: {overview.get('total_workspaces', 0)} | "
                f"Queries: {overview.get('total_unique_queries', 0)} | "
                f"Duration: {overview.get('total_duration_seconds', 0):.1f}s | "
                f"Downloaded: {overview.get('total_records_downloaded', 0)} | "
                f"Uploaded: {overview.get('total_records_uploaded', 0)}")
    
    @staticmethod
    def format_workspace_query_detail(workspace_query: Dict[str, Any]) -> str:
        """Format workspace/query detail as key-value pairs."""
        kv_pairs = []
        
        # Core identification
        kv_pairs.append(f"workspaceId={workspace_query.get('workspaceId', 'unknown')}")
        kv_pairs.append(f"query={workspace_query.get('query', 'unknown')}")
        
        # Record statistics
        kv_pairs.append(f"logsDownloaded={workspace_query.get('logsDownloaded', 0)}")
        kv_pairs.append(f"uploadSuccess={workspace_query.get('uploadSuccess', 0)}")
        kv_pairs.append(f"uploadFailure={workspace_query.get('uploadFailure', 0)}")
        
        # Performance metrics
        kv_pairs.append(f"avgQueryTime={workspace_query.get('avgQueryTime', 0):.2f}s")
        kv_pairs.append(f"totalQueryTime={workspace_query.get('totalQueryTime', 0):.2f}s")
        kv_pairs.append(f"queryExecutions={workspace_query.get('queryExecutions', 0)}")
        
        # Time range
        kv_pairs.append(f"startTimeRange={workspace_query.get('startTimeRange', 'unknown')}")
        kv_pairs.append(f"endTimeRange={workspace_query.get('endTimeRange', 'unknown')}")
        
        return " | ".join(kv_pairs)


class ContextualLogger:
    """
    Logger wrapper that maintains context for consistent formatting.
    
    Provides automatic context injection and standardized message formatting
    for better log traceability and debugging.
    """
    
    def __init__(self, logger: Union[logging.Logger, logging.LoggerAdapter], job_id: Optional[str] = None):  # type: ignore[type-arg]
        """
        Initialize contextual logger.
        
        Args:
            logger: Base logger instance or logger adapter
            job_id: Optional job correlation ID for context
        """
        self.logger = logger
        self.job_id = job_id
        self.formatter = SentinelLogFormatter()
    
    def set_job_id(self, job_id: str) -> None:
        """Update the job correlation ID."""
        self.job_id = job_id
    
    def batch_start(self, days_back: int, batch_hours: int, workspace_count: int) -> None:
        """Log batch execution start."""
        if self.job_id:
            msg = self.formatter.format_batch_start(self.job_id, days_back, batch_hours, workspace_count)
            self.logger.info(msg)
    
    def batch_end(self, summary: Dict[str, Any]) -> None:
        """Log batch execution completion."""
        if self.job_id:
            msg = self.formatter.format_batch_end(self.job_id, summary)
            self.logger.info(msg)
    
    def query_start(self, query_name: str, workspace_alias: str, time_range: str) -> None:
        """Log query execution start."""
        if self.job_id:
            msg = self.formatter.format_query_start(self.job_id, query_name, workspace_alias, time_range)
            self.logger.info(msg)
    
    def query_end(self, query_name: str, workspace_alias: str, record_count: int, 
                  duration: float, success: bool = True) -> None:
        """Log query execution completion."""
        if self.job_id:
            msg = self.formatter.format_query_end(
                self.job_id, query_name, workspace_alias, record_count, duration, success
            )
            if success:
                self.logger.info(msg)
            else:
                self.logger.error(msg)
    
    def upload_start(self, query_name: str, workspace_alias: str, record_count: int) -> None:
        """Log upload start."""
        if self.job_id:
            msg = self.formatter.format_upload_start(self.job_id, query_name, workspace_alias, record_count)
            self.logger.debug(msg)
    
    def upload_end(self, query_name: str, workspace_alias: str, uploaded_count: int, 
                   duration: float, success: bool = True) -> None:
        """Log upload completion."""
        if self.job_id:
            msg = self.formatter.format_upload_end(
                self.job_id, query_name, workspace_alias, uploaded_count, duration, success
            )
            if success:
                self.logger.info(msg)
            else:
                self.logger.error(msg)
    
    def error(self, component: str, error_message: str, query_name: Optional[str] = None,
              workspace_alias: Optional[str] = None, error_type: Optional[str] = None,
              exc_info: bool = False) -> None:
        """Log error with full context."""
        if self.job_id:
            msg = self.formatter.format_error(
                self.job_id, component, query_name, workspace_alias, error_message, error_type
            )
            self.logger.error(msg, exc_info=exc_info)
    
    def progress(self, completed: int, total: int, additional_info: Optional[str] = None) -> None:
        """Log progress update."""
        if self.job_id:
            msg = self.formatter.format_progress(self.job_id, completed, total, additional_info)
            self.logger.info(msg)
    
    def workspace_config(self, workspace_count: int, report_count: int, 
                        subscription_count: int, error_count: int = 0) -> None:
        """Log workspace configuration summary."""
        msg = self.formatter.format_workspace_config(
            workspace_count, report_count, subscription_count, error_count
        )
        self.logger.info(msg)
    
    def config_validation(self, component: str, is_valid: bool, details: Optional[str] = None) -> None:
        """Log configuration validation result."""
        msg = self.formatter.format_config_validation(component, is_valid, details)
        if is_valid:
            self.logger.info(msg)
        else:
            self.logger.error(msg)
    
    def batch_summary(self, summary_data: Dict[str, Any]) -> None:
        """Log batch execution summary."""
        if self.job_id:
            msg = self.formatter.format_batch_summary(self.job_id, summary_data)
            self.logger.info(msg)
    
    def workspace_query_details(self, workspace_query_details: List[Dict[str, Any]]) -> None:
        """Log workspace/query details in key-value format."""
        if self.job_id:
            for detail in workspace_query_details:
                kv_detail = self.formatter.format_workspace_query_detail(detail)
                self.logger.info(f"[WORKSPACE_QUERY_DETAIL] Job: {self.job_id} | {kv_detail}")
    
    # Convenience methods for standard logging
    def info(self, message: str) -> None:
        """Log info message."""
        self.logger.info(message)
    
    def warning(self, message: str) -> None:
        """Log warning message."""
        self.logger.warning(message)
    
    def debug(self, message: str) -> None:
        """Log debug message."""
        self.logger.debug(message)