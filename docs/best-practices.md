---
title: Best practices and recommendations
description: Production deployment best practices and security recommendations for the Microsoft Sentinel Log Aggregator.
author: Alistair Ross
ms.author: community
ms.service: sentinel
ms.topic: best-practices
ms.date: 2025-11-01
---

# Best practices and recommendations

This article provides comprehensive best practices and recommendations for production deployment of the Microsoft Sentinel Log Aggregator.

## Security best practices

### Authentication and authorization

#### Use managed identity (recommended)

For Azure-hosted deployments, use Azure Managed Identity for authentication:

```python
# Automatic managed identity authentication
from azure.identity.aio import DefaultAzureCredential

credential = DefaultAzureCredential()
```

**Benefits:**
- No credentials to manage or rotate
- Automatic credential lifecycle management
- Integrated with Azure RBAC
- Audit trail through Azure AD logs

#### Service principal for CI/CD

For automated deployments and CI/CD pipelines:

```bash
# Set environment variables for service principal
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
export AZURE_TENANT_ID="your-tenant-id"
```

**Security considerations:**
- Store secrets in Azure Key Vault or secure credential manager
- Use certificate-based authentication when possible
- Implement regular credential rotation (90 days recommended)
- Follow principle of least privilege

#### Required Azure permissions

Configure these RBAC permissions for the service identity:

```yaml
# Minimum required permissions
permissions:
  - scope: "/subscriptions/{subscription-id}/resourceGroups/{rg}/providers/Microsoft.OperationalInsights/workspaces/{workspace}"
    role: "Microsoft Sentinel Reader"
    
  - scope: "/subscriptions/{subscription-id}/resourceGroups/{rg}/providers/Microsoft.Insights/dataCollectionEndpoints/{dce}"
    role: "Monitoring Metrics Publisher"
    
  - scope: "/subscriptions/{subscription-id}/resourceGroups/{rg}/providers/Microsoft.Insights/dataCollectionRules/{dcr}"
    role: "Monitoring Metrics Publisher"
```

### Data security and privacy

#### Row-level security tagging

Always implement row-level security tags for data isolation:

```python
# Configure row-level security tags
workspace_config = {
    "workspaces": [
        {
            "customer_id": "workspace-1-guid",
            "parameters": {
                "row_level_security_tag": "tenant-a-prod"
            }
        }
    ]
}
```

#### Data encryption and transmission

- All data transmitted over HTTPS/TLS 1.2+
- Data encrypted at rest in Azure Monitor Logs
- Use private endpoints for enhanced network security
- Implement network security groups (NSGs) for traffic filtering

#### Sensitive data handling

```python
# Never log sensitive information
logger.info(f"Processing workspace {workspace_id[:8]}...")  # Truncate IDs
logger.debug("Query parameters", extra={"sanitized_params": sanitize_params(params)})

def sanitize_params(params):
    """Remove sensitive information from parameters."""
    sanitized = params.copy()
    sensitive_keys = ['password', 'secret', 'key', 'token']
    
    for key in list(sanitized.keys()):
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            sanitized[key] = "***REDACTED***"
    
    return sanitized
```

## Performance optimization

### Batch processing configuration

#### Optimal batch sizing

```yaml
# Recommended batch configuration
batch_configuration:
  batch_time_size: "PT24H"  # 24-hour batches for large workspaces
  max_concurrent_queries: 5  # Adjust based on Azure quota limits
  query_timeout_minutes: 30  # Allow sufficient time for large queries
  retry_max_attempts: 3
  retry_delay_seconds: 60
```

#### Memory management

```python
import gc
from typing import AsyncGenerator

async def process_large_datasets() -> AsyncGenerator[Dict, None]:
    """Process large datasets with memory management."""
    
    try:
        # Process data in chunks
        for batch in query_batches:
            result = await execute_batch(batch)
            
            # Yield results immediately
            yield result
            
            # Explicit garbage collection for large datasets
            if result.record_count > 10000:
                gc.collect()
    
    finally:
        # Ensure cleanup
        gc.collect()
```

### Concurrent execution limits

#### Azure service limits

Respect Azure Monitor service limits:

```python
# Service limit recommendations
limits = {
    "max_concurrent_queries_per_workspace": 10,
    "max_query_duration_minutes": 30,
    "max_records_per_query": 500000,
    "max_data_ingestion_per_minute_mb": 100,
    "query_timeout_seconds": 1800
}
```

#### Adaptive concurrency

```python
import asyncio
from asyncio import Semaphore

class AdaptiveConcurrencyManager:
    """Manages adaptive concurrency based on performance metrics."""
    
    def __init__(self, initial_concurrency: int = 5):
        self.semaphore = Semaphore(initial_concurrency)
        self.current_concurrency = initial_concurrency
        self.error_rate = 0.0
        self.avg_response_time = 0.0
        
    async def execute_with_adaptive_concurrency(self, operations):
        """Execute operations with adaptive concurrency control."""
        
        for operation in operations:
            async with self.semaphore:
                start_time = time.time()
                
                try:
                    result = await operation()
                    execution_time = time.time() - start_time
                    
                    # Update performance metrics
                    self._update_metrics(execution_time, success=True)
                    
                    # Adjust concurrency based on performance
                    await self._adjust_concurrency()
                    
                    yield result
                
                except Exception as e:
                    execution_time = time.time() - start_time
                    self._update_metrics(execution_time, success=False)
                    await self._adjust_concurrency()
                    raise
    
    def _update_metrics(self, execution_time: float, success: bool):
        """Update performance metrics."""
        # Exponential moving average
        alpha = 0.1
        self.avg_response_time = (1 - alpha) * self.avg_response_time + alpha * execution_time
        self.error_rate = (1 - alpha) * self.error_rate + alpha * (0 if success else 1)
    
    async def _adjust_concurrency(self):
        """Adjust concurrency based on current performance."""
        
        # Increase concurrency if performing well
        if self.error_rate < 0.05 and self.avg_response_time < 10.0:
            if self.current_concurrency < 10:
                self.current_concurrency += 1
                self.semaphore = Semaphore(self.current_concurrency)
        
        # Decrease concurrency if experiencing issues
        elif self.error_rate > 0.20 or self.avg_response_time > 30.0:
            if self.current_concurrency > 1:
                self.current_concurrency -= 1
                self.semaphore = Semaphore(self.current_concurrency)
```

## Configuration management

### Environment-based configuration

#### Development environment

```yaml
# dev-config.yaml
environment: development
log_level: DEBUG
batch_time_size: "PT1H"
max_concurrent_queries: 2
lookback_period: "P1D"
upload_enabled: false  # Disable uploads in dev
dry_run: true
```

#### Production environment

```yaml
# prod-config.yaml
environment: production
log_level: INFO
batch_time_size: "PT24H"
max_concurrent_queries: 5
lookback_period: "P7D"
upload_enabled: true
dry_run: false
retry_max_attempts: 5
circuit_breaker_enabled: true
```

#### Configuration validation

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ProductionConfig:
    """Production configuration with validation."""
    
    environment: str
    log_level: str
    batch_time_size: str
    max_concurrent_queries: int
    
    def validate(self) -> List[str]:
        """Validate configuration for production use."""
        errors = []
        
        if self.environment != "production":
            errors.append("Environment must be 'production' for production deployments")
        
        if self.log_level == "DEBUG":
            errors.append("DEBUG log level not recommended for production")
        
        if self.batch_time_size in ["PT1H", "PT2H", "PT4H", "PT6H"]:
            errors.append("Batch time size should be >= PT12H for production efficiency")
        
        if self.max_concurrent_queries > 10:
            errors.append("Max concurrent queries should not exceed 10 to avoid throttling")
        
        return errors
```

### Workspace management

#### Workspace organization

Organize workspaces by environment and purpose:

```yaml
# workspaces.yaml - Production structure
workspaces:
  # Production workspaces
  - customer_id: "prod-workspace-1-guid"
    alias: "production-east"
    parameters:
      row_level_security_tag: "prod-east"
      environment: "production"
      region: "eastus"
    
  - customer_id: "prod-workspace-2-guid"
    alias: "production-west"
    parameters:
      row_level_security_tag: "prod-west"
      environment: "production"
      region: "westus"
  
  # Staging workspaces
  - customer_id: "staging-workspace-1-guid"
    alias: "staging-east"
    parameters:
      row_level_security_tag: "staging-east"
      environment: "staging"
      region: "eastus"
```

#### Configuration versioning

```bash
# Version control workspace configurations
git tag v1.0.0-workspaces
git push origin v1.0.0-workspaces

# Track changes with descriptive commits
git commit -m "feat: add new production workspace for west region"
```

## Monitoring and observability

### Comprehensive logging

#### Structured logging configuration

```python
import logging
import json
from datetime import datetime, timezone

class ProductionFormatter(logging.Formatter):
    """Production-ready JSON log formatter."""
    
    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add correlation ID if available
        if hasattr(record, 'correlation_id'):
            log_entry["correlation_id"] = record.correlation_id
        
        # Add workspace context if available
        if hasattr(record, 'workspace_id'):
            log_entry["workspace_id"] = record.workspace_id[:8]  # Truncated for security
        
        # Add performance metrics if available
        if hasattr(record, 'execution_time'):
            log_entry["execution_time_seconds"] = record.execution_time
        
        if hasattr(record, 'record_count'):
            log_entry["record_count"] = record.record_count
        
        return json.dumps(log_entry)

# Configure production logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('sentinel-aggregator.log')
    ]
)

# Set formatter for all handlers
for handler in logging.getLogger().handlers:
    handler.setFormatter(ProductionFormatter())
```

#### Key metrics to monitor

```python
import time
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class PerformanceMetrics:
    """Key performance metrics for monitoring."""
    
    queries_executed: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    total_records_processed: int = 0
    total_execution_time: float = 0.0
    avg_query_time: float = 0.0
    peak_memory_usage_mb: float = 0.0
    concurrent_operations: int = 0
    
    def calculate_derived_metrics(self) -> Dict[str, Any]:
        """Calculate derived performance metrics."""
        
        success_rate = (self.successful_queries / max(self.queries_executed, 1)) * 100
        records_per_second = self.total_records_processed / max(self.total_execution_time, 1)
        
        return {
            "success_rate_percent": success_rate,
            "failure_rate_percent": 100 - success_rate,
            "records_per_second": records_per_second,
            "avg_query_time_seconds": self.avg_query_time,
            "queries_per_minute": (self.queries_executed / max(self.total_execution_time / 60, 1))
        }

class MetricsCollector:
    """Collects and reports performance metrics."""
    
    def __init__(self):
        self.metrics = PerformanceMetrics()
        self.start_time = time.time()
    
    def record_query_execution(self, execution_time: float, record_count: int, success: bool):
        """Record query execution metrics."""
        
        self.metrics.queries_executed += 1
        self.metrics.total_execution_time += execution_time
        self.metrics.total_records_processed += record_count
        
        if success:
            self.metrics.successful_queries += 1
        else:
            self.metrics.failed_queries += 1
        
        # Update average query time
        self.metrics.avg_query_time = (
            self.metrics.total_execution_time / self.metrics.queries_executed
        )
    
    async def upload_metrics(self, client):
        """Upload metrics to Azure Monitor."""
        
        derived_metrics = self.metrics.calculate_derived_metrics()
        
        metrics_data = {
            "TimeGenerated": datetime.now(timezone.utc).isoformat(),
            "QueriesExecuted": self.metrics.queries_executed,
            "SuccessfulQueries": self.metrics.successful_queries,
            "FailedQueries": self.metrics.failed_queries,
            "TotalRecordsProcessed": self.metrics.total_records_processed,
            "TotalExecutionTimeSeconds": self.metrics.total_execution_time,
            "SuccessRatePercent": derived_metrics["success_rate_percent"],
            "RecordsPerSecond": derived_metrics["records_per_second"],
            "AvgQueryTimeSeconds": derived_metrics["avg_query_time_seconds"],
            "ReportType": "performance_metrics"
        }
        
        await client.upload_logs(
            data=[metrics_data],
            stream_name="Custom-PerformanceMetrics_CL"
        )
```

### Health checks and monitoring

#### Health check implementation

```python
import asyncio
from enum import Enum
from typing import Dict, List

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

class HealthChecker:
    """Comprehensive health checker for the aggregator service."""
    
    def __init__(self, client, workspace_manager):
        self.client = client
        self.workspace_manager = workspace_manager
    
    async def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        
        health_results = {
            "overall_status": HealthStatus.HEALTHY,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {}
        }
        
        # Check Azure authentication
        auth_status = await self._check_authentication()
        health_results["checks"]["authentication"] = auth_status
        
        # Check workspace connectivity
        workspace_status = await self._check_workspace_connectivity()
        health_results["checks"]["workspace_connectivity"] = workspace_status
        
        # Check data ingestion endpoint
        ingestion_status = await self._check_data_ingestion()
        health_results["checks"]["data_ingestion"] = ingestion_status
        
        # Check query execution
        query_status = await self._check_query_execution()
        health_results["checks"]["query_execution"] = query_status
        
        # Determine overall status
        all_statuses = [check["status"] for check in health_results["checks"].values()]
        
        if any(status == HealthStatus.UNHEALTHY for status in all_statuses):
            health_results["overall_status"] = HealthStatus.UNHEALTHY
        elif any(status == HealthStatus.DEGRADED for status in all_statuses):
            health_results["overall_status"] = HealthStatus.DEGRADED
        
        return health_results
    
    async def _check_authentication(self) -> Dict[str, Any]:
        """Check Azure authentication."""
        
        try:
            # Test authentication by getting a token
            credential = self.client._credential
            token = await credential.get_token("https://management.azure.com/.default")
            
            if token and token.token:
                return {
                    "status": HealthStatus.HEALTHY,
                    "message": "Authentication successful",
                    "token_expires_at": token.expires_on
                }
            else:
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "message": "Failed to obtain authentication token"
                }
        
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Authentication failed: {str(e)}"
            }
    
    async def _check_workspace_connectivity(self) -> Dict[str, Any]:
        """Check connectivity to Sentinel workspaces."""
        
        try:
            successful_connections = 0
            total_workspaces = len(self.workspace_manager.workspaces)
            
            # Test connectivity to a sample of workspaces
            sample_workspaces = self.workspace_manager.workspaces[:3]  # Test first 3
            
            for workspace in sample_workspaces:
                try:
                    # Simple query to test connectivity
                    test_query = "print 'health check'"
                    result = await asyncio.wait_for(
                        self.client.query_workspace(workspace.customer_id, test_query),
                        timeout=30
                    )
                    
                    if result.succeeded:
                        successful_connections += 1
                
                except Exception:
                    pass  # Count as failed connection
            
            success_rate = successful_connections / len(sample_workspaces) if sample_workspaces else 0
            
            if success_rate >= 1.0:
                status = HealthStatus.HEALTHY
                message = "All tested workspaces accessible"
            elif success_rate >= 0.5:
                status = HealthStatus.DEGRADED
                message = f"Partial workspace connectivity: {successful_connections}/{len(sample_workspaces)}"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Poor workspace connectivity: {successful_connections}/{len(sample_workspaces)}"
            
            return {
                "status": status,
                "message": message,
                "successful_connections": successful_connections,
                "total_tested": len(sample_workspaces),
                "total_configured": total_workspaces
            }
        
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Workspace connectivity check failed: {str(e)}"
            }
    
    async def _check_data_ingestion(self) -> Dict[str, Any]:
        """Check data ingestion endpoint availability."""
        
        try:
            # Test with minimal data upload
            test_data = {
                "TimeGenerated": datetime.now(timezone.utc).isoformat(),
                "Message": "Health check test",
                "ReportType": "health_check"
            }
            
            result = await asyncio.wait_for(
                self.client.upload_logs(
                    data=[test_data],
                    stream_name="Custom-HealthCheck_CL"
                ),
                timeout=60
            )
            
            if result.succeeded:
                return {
                    "status": HealthStatus.HEALTHY,
                    "message": "Data ingestion endpoint accessible",
                    "upload_duration_seconds": getattr(result, 'upload_duration', 0)
                }
            else:
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "message": f"Data ingestion failed: {result.error_message}"
                }
        
        except asyncio.TimeoutError:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": "Data ingestion endpoint timeout"
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Data ingestion check failed: {str(e)}"
            }
    
    async def _check_query_execution(self) -> Dict[str, Any]:
        """Check query execution capability."""
        
        try:
            if not self.workspace_manager.workspaces:
                return {
                    "status": HealthStatus.DEGRADED,
                    "message": "No workspaces configured for testing"
                }
            
            # Test with first available workspace
            test_workspace = self.workspace_manager.workspaces[0]
            test_query = "SecurityEvent | take 1"
            
            start_time = time.time()
            result = await asyncio.wait_for(
                self.client.query_workspace(test_workspace.customer_id, test_query),
                timeout=60
            )
            execution_time = time.time() - start_time
            
            if result.succeeded:
                return {
                    "status": HealthStatus.HEALTHY,
                    "message": "Query execution successful",
                    "execution_time_seconds": execution_time,
                    "test_workspace": test_workspace.customer_id[:8]
                }
            else:
                return {
                    "status": HealthStatus.DEGRADED,
                    "message": f"Query execution failed: {result.error_message}",
                    "test_workspace": test_workspace.customer_id[:8]
                }
        
        except asyncio.TimeoutError:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": "Query execution timeout"
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Query execution check failed: {str(e)}"
            }
```

## Error handling and resilience

### Circuit breaker pattern

```python
import asyncio
from enum import Enum
from typing import Callable, Any

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered

class CircuitBreaker:
    """Circuit breaker pattern implementation for resilient operations."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
        expected_exception: Exception = Exception
    ):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception(f"Circuit breaker OPEN: too many failures")
        
        try:
            result = await func(*args, **kwargs)
            
            # Success - reset circuit breaker
            self._on_success()
            return result
        
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        
        if self.last_failure_time is None:
            return True
        
        return (time.time() - self.last_failure_time) >= self.timeout_seconds
    
    def _on_success(self):
        """Handle successful operation."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
```

### Retry strategies

```python
import asyncio
import random
from typing import Union, Callable, Any

class RetryStrategy:
    """Advanced retry strategy with exponential backoff and jitter."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    async def execute(
        self,
        func: Callable,
        *args,
        retryable_exceptions: tuple = (Exception,),
        **kwargs
    ) -> Any:
        """Execute function with retry logic."""
        
        last_exception = None
        
        for attempt in range(1, self.max_attempts + 1):
            try:
                return await func(*args, **kwargs)
            
            except retryable_exceptions as e:
                last_exception = e
                
                if attempt == self.max_attempts:
                    raise e
                
                # Calculate delay with exponential backoff
                delay = min(
                    self.base_delay * (self.exponential_base ** (attempt - 1)),
                    self.max_delay
                )
                
                # Add jitter to prevent thundering herd
                if self.jitter:
                    delay = delay * (0.5 + random.random() * 0.5)
                
                logger.warning(
                    f"Attempt {attempt} failed, retrying in {delay:.2f}s: {str(e)}"
                )
                
                await asyncio.sleep(delay)
        
        # This should never be reached, but include for completeness
        if last_exception:
            raise last_exception
```

## Deployment best practices

### Container deployment

#### Production Dockerfile

```dockerfile
# Multi-stage build for optimized production image
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Create non-root user
RUN groupadd -r sentinel && useradd -r -g sentinel sentinel

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=sentinel:sentinel . /app
WORKDIR /app

# Switch to non-root user
USER sentinel

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD python -c "import asyncio; from sentinel_log_aggregator.health import health_check; asyncio.run(health_check())" || exit 1

# Default command
CMD ["sentinel-aggregator", "run", "--workspace-config", "/config/workspaces.yaml"]
```

#### Kubernetes deployment

```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sentinel-log-aggregator
  namespace: monitoring
spec:
  replicas: 1  # Single instance for consistent batch processing
  selector:
    matchLabels:
      app: sentinel-log-aggregator
  template:
    metadata:
      labels:
        app: sentinel-log-aggregator
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
    spec:
      serviceAccountName: sentinel-aggregator-sa
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
      - name: aggregator
        image: your-registry/sentinel-log-aggregator:latest
        imagePullPolicy: Always
        env:
        - name: AZURE_CLIENT_ID
          valueFrom:
            secretKeyRef:
              name: azure-credentials
              key: client-id
        - name: DCR_LOGS_INGESTION_ENDPOINT
          valueFrom:
            configMapKeyRef:
              name: aggregator-config
              key: dcr-endpoint
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        volumeMounts:
        - name: config
          mountPath: /config
          readOnly: true
        livenessProbe:
          exec:
            command:
            - python
            - -c
            - "import asyncio; from sentinel_log_aggregator.health import health_check; asyncio.run(health_check())"
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          exec:
            command:
            - python
            - -c
            - "import asyncio; from sentinel_log_aggregator.health import health_check; asyncio.run(health_check())"
          initialDelaySeconds: 10
          periodSeconds: 10
      volumes:
      - name: config
        configMap:
          name: workspace-config
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: workspace-config
  namespace: monitoring
data:
  workspaces.yaml: |
    workspaces:
      - customer_id: "workspace-1-guid"
        alias: "production-east"
        parameters:
          row_level_security_tag: "prod-east"
```

### CI/CD pipeline

#### Azure DevOps pipeline

```yaml
# azure-pipelines.yml
trigger:
  branches:
    include:
    - main
    - develop
  paths:
    exclude:
    - docs/*
    - README.md

pool:
  vmImage: 'ubuntu-latest'

variables:
- group: sentinel-aggregator-secrets
- name: pythonVersion
  value: '3.11'

stages:
- stage: Test
  jobs:
  - job: UnitTests
    steps:
    - task: UsePythonVersion@0
      inputs:
        versionSpec: $(pythonVersion)
    
    - script: |
        python -m pip install --upgrade pip
        pip install -r requirements-dev.txt
      displayName: 'Install dependencies'
    
    - script: |
        python -m pytest tests/ --cov=sentinel_log_aggregator --cov-report=xml
      displayName: 'Run tests with coverage'
    
    - task: PublishCodeCoverageResults@1
      inputs:
        codeCoverageTool: 'Cobertura'
        summaryFileLocation: 'coverage.xml'

- stage: Security
  jobs:
  - job: SecurityScanning
    steps:
    - task: UsePythonVersion@0
      inputs:
        versionSpec: $(pythonVersion)
    
    - script: |
        pip install bandit safety
        bandit -r sentinel_log_aggregator/ -f json -o bandit-report.json
        safety check --json --output safety-report.json
      displayName: 'Security scanning'

- stage: Build
  condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
  jobs:
  - job: BuildContainer
    steps:
    - task: Docker@2
      inputs:
        command: 'buildAndPush'
        repository: '$(containerRegistry)/sentinel-log-aggregator'
        dockerfile: 'Dockerfile'
        tags: |
          $(Build.BuildNumber)
          latest

- stage: Deploy
  condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
  jobs:
  - deployment: DeployToProduction
    environment: 'production'
    strategy:
      runOnce:
        deploy:
          steps:
          - task: KubernetesManifest@0
            inputs:
              action: 'deploy'
              manifests: 'kubernetes/*.yaml'
              namespace: 'monitoring'
```

### Monitoring and alerting

#### Azure Monitor alerts

```json
{
  "alertRules": [
    {
      "name": "SentinelAggregator-HighFailureRate",
      "description": "Alert when query failure rate exceeds 20%",
      "severity": 2,
      "frequency": "PT5M",
      "timeWindow": "PT15M",
      "criteria": {
        "query": "Custom-PerformanceMetrics_CL | where TimeGenerated > ago(15m) | summarize FailureRate = avg(100 - SuccessRatePercent) | where FailureRate > 20",
        "threshold": 1,
        "operator": "GreaterThanOrEqual"
      },
      "actions": [
        {
          "actionGroupId": "/subscriptions/{subscription}/resourceGroups/{rg}/providers/Microsoft.Insights/actionGroups/sentinel-alerts"
        }
      ]
    },
    {
      "name": "SentinelAggregator-LowThroughput",
      "description": "Alert when records per second drops below threshold",
      "severity": 3,
      "frequency": "PT10M",
      "timeWindow": "PT30M",
      "criteria": {
        "query": "Custom-PerformanceMetrics_CL | where TimeGenerated > ago(30m) | summarize AvgThroughput = avg(RecordsPerSecond) | where AvgThroughput < 100",
        "threshold": 1,
        "operator": "GreaterThanOrEqual"
      }
    }
  ]
}
```

## Next steps

- [Troubleshooting guide](troubleshooting.md) - Common issues and solutions
- [Performance tuning](performance-tuning.md) - Advanced optimization techniques
- [API reference](api-reference.md) - Complete API documentation
- [Advanced examples](examples/advanced-examples.md) - Complex integration scenarios