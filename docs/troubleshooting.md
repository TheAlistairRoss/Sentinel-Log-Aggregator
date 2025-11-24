---
title: Troubleshooting guide
description: Common issues, solutions, and debugging techniques for the Microsoft Sentinel Log Aggregator.
author: Alistair Ross
ms.author: community
ms.service: sentinel
ms.topic: troubleshooting
ms.date: 2025-11-01
---

# Troubleshooting guide

This article provides solutions to common issues and debugging techniques for the Microsoft Sentinel Log Aggregator.

## Authentication issues

### Problem: Authentication failed with DefaultAzureCredential

**Symptoms:**
```
ERROR: Authentication failed: DefaultAzureCredential failed to retrieve a token
```

**Solutions:**

#### 1. Check authentication chain order

The `DefaultAzureCredential` tries authentication methods in this order:
1. Environment variables (service principal)
2. Managed identity
3. Azure CLI
4. Azure PowerShell
5. Interactive browser

**Debugging steps:**

```python
import os
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ClientAuthenticationError

async def debug_authentication():
    """Debug authentication issues step by step."""
    
    print("🔍 Debugging Azure authentication...")
    
    # Check environment variables
    env_vars = ['AZURE_CLIENT_ID', 'AZURE_CLIENT_SECRET', 'AZURE_TENANT_ID']
    env_configured = all(os.getenv(var) for var in env_vars)
    
    print(f"Environment variables configured: {env_configured}")
    if env_configured:
        for var in env_vars:
            value = os.getenv(var, 'Not set')
            masked_value = value[:8] + '...' if len(value) > 8 else 'Not set'
            print(f"  {var}: {masked_value}")
    
    # Test credential chain
    try:
        credential = DefaultAzureCredential(logging_enable=True)
        token = await credential.get_token("https://management.azure.com/.default")
        print(f"✅ Authentication successful")
        print(f"Token expires: {token.expires_on}")
        return True
    
    except ClientAuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
        return False

# Run debugging
asyncio.run(debug_authentication())
```

#### 2. Service principal configuration

For environment variable authentication:

```bash
# Windows PowerShell
$env:AZURE_CLIENT_ID = "your-client-id"
$env:AZURE_CLIENT_SECRET = "your-client-secret"  
$env:AZURE_TENANT_ID = "your-tenant-id"

# Linux/macOS
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
export AZURE_TENANT_ID="your-tenant-id"
```

#### 3. Azure CLI authentication

```bash
# Login to Azure CLI
az login

# Verify current account
az account show

# Set specific subscription
az account set --subscription "your-subscription-id"
```

#### 4. Managed identity configuration

For Azure-hosted resources, ensure managed identity is enabled:

```bash
# Enable system-assigned managed identity (Azure VM)
az vm identity assign --name your-vm --resource-group your-rg

# Enable managed identity (Azure Function)
az functionapp identity assign --name your-function --resource-group your-rg
```

### Problem: Token expired or invalid

**Symptoms:**
```
ERROR: The access token expiry UTC time is before the current UTC time
```

**Solutions:**

1. **Clear cached tokens:**
   ```bash
   # Clear Azure CLI cache
   az account clear
   az login
   ```

2. **Implement token refresh:**
   ```python
   from azure.identity.aio import DefaultAzureCredential
   
   class RefreshableCredential:
       """Wrapper for automatic token refresh."""
       
       def __init__(self):
           self.credential = DefaultAzureCredential()
           self.cached_token = None
           self.token_expires_at = 0
       
       async def get_token(self, scopes):
           """Get token with automatic refresh."""
           import time
           
           current_time = time.time()
           
           # Refresh if token expires within 5 minutes
           if (self.cached_token is None or 
               current_time >= (self.token_expires_at - 300)):
               
               self.cached_token = await self.credential.get_token(scopes)
               self.token_expires_at = self.cached_token.expires_on
           
           return self.cached_token
   ```

## Connectivity issues

### Problem: Connection timeout to Azure Monitor

**Symptoms:**
```
ERROR: Request timeout: Connection to monitor.azure.com timed out
```

**Solutions:**

#### 1. Network connectivity test

```python
import asyncio
import aiohttp
from azure.core.exceptions import ServiceRequestError

async def test_connectivity():
    """Test network connectivity to Azure services."""
    
    endpoints = [
        "https://management.azure.com",
        "https://monitor.azure.com", 
        "https://api.loganalytics.io",
        "https://your-dce-endpoint.eastus-1.ingest.monitor.azure.com"
    ]
    
    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints:
            try:
                start_time = time.time()
                async with session.get(endpoint, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    duration = time.time() - start_time
                    print(f"✅ {endpoint}: {response.status} ({duration:.2f}s)")
            
            except asyncio.TimeoutError:
                print(f"⏰ {endpoint}: Timeout")
            except Exception as e:
                print(f"❌ {endpoint}: {e}")
```

#### 2. Firewall and proxy configuration

```python
import aiohttp
from azure.core.pipeline.transport import AioHttpTransport

# Configure proxy
proxy_transport = AioHttpTransport(
    session=aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(
            use_dns_cache=False,
            ttl_dns_cache=300,
            limit=100,
            limit_per_host=10
        ),
        timeout=aiohttp.ClientTimeout(total=300)
    )
)

# Use with Azure client
options = SentinelAggregatorClientOptions(
    transport=proxy_transport,
    retry_total=5,
    retry_backoff_factor=2.0
)
```

#### 3. DNS resolution issues

```bash
# Test DNS resolution
nslookup monitor.azure.com
nslookup api.loganalytics.io

# Windows - flush DNS cache
ipconfig /flushdns

# Linux - restart DNS service
sudo systemctl restart systemd-resolved
```

### Problem: SSL/TLS certificate errors

**Symptoms:**
```
ERROR: SSL: CERTIFICATE_VERIFY_FAILED
```

**Solutions:**

1. **Update certificates:**
   ```bash
   # Update CA certificates (Ubuntu/Debian)
   sudo apt-get update && sudo apt-get install ca-certificates
   
   # Update certificates (RHEL/CentOS)
   sudo yum update ca-certificates
   ```

2. **Configure SSL context:**
   ```python
   import ssl
   import aiohttp
   
   # Create SSL context with updated certificates
   ssl_context = ssl.create_default_context()
   ssl_context.check_hostname = True
   ssl_context.verify_mode = ssl.CERT_REQUIRED
   
   # Use with client
   connector = aiohttp.TCPConnector(ssl=ssl_context)
   session = aiohttp.ClientSession(connector=connector)
   ```

## Query execution issues

### Problem: KQL query syntax errors

**Symptoms:**
```
ERROR: Query failed: BadRequest - Syntax error at line 3
```

**Solutions:**

#### 1. Query validation tool

```python
import re
from typing import List, Dict

class KQLValidator:
    """Validate KQL queries before execution."""
    
    def __init__(self):
        self.common_errors = {
            r'\bwhere\s+and\b': 'Use "where condition1 and condition2" instead of "where and"',
            r'\bsummarize\s+by\s*$': 'Summarize clause is incomplete',
            r'\bmake_set\s*\(\s*\)': 'make_set() requires a parameter',
            r'\btake\s+[^0-9]': 'take operator requires a numeric value',
            r'\bago\s*\(\s*[^0-9]': 'ago() requires a time value like ago(1h)',
            r'\bTimeGenerated\s*>\s*ago\s*$': 'ago() function call is incomplete'
        }
    
    def validate_query(self, query: str) -> List[str]:
        """Validate KQL query for common syntax errors."""
        
        errors = []
        
        # Check for common syntax errors
        for pattern, message in self.common_errors.items():
            if re.search(pattern, query, re.IGNORECASE):
                errors.append(f"Syntax error: {message}")
        
        # Check for balanced parentheses
        if query.count('(') != query.count(')'):
            errors.append("Unbalanced parentheses in query")
        
        # Check for required operators
        if 'summarize' in query.lower() and 'by' not in query.lower():
            errors.append("Summarize query should include 'by' clause")
        
        # Check for table references
        tables = re.findall(r'^(\w+)\s*\|', query, re.MULTILINE)
        if not tables:
            errors.append("Query should start with a table name")
        
        return errors
    
    def suggest_fixes(self, query: str) -> List[str]:
        """Suggest fixes for common query issues."""
        
        suggestions = []
        
        # Suggest time range filters
        if 'TimeGenerated' not in query and any(table in query for table in ['SecurityEvent', 'Syslog', 'CommonSecurityLog']):
            suggestions.append("Consider adding time range filter: | where TimeGenerated > ago(1h)")
        
        # Suggest take limit for large queries
        if 'take' not in query.lower() and 'summarize' not in query.lower():
            suggestions.append("Consider adding | take 100 to limit results")
        
        # Suggest projection for wide tables
        if any(table in query for table in ['SecurityEvent', 'W3CIISLog']) and 'project' not in query.lower():
            suggestions.append("Consider using | project to select specific columns")
        
        return suggestions

# Usage example
validator = KQLValidator()

def validate_and_fix_query(query: str) -> str:
    """Validate and suggest fixes for KQL query."""
    
    print(f"Validating query:")
    print(f"  {query}")
    
    errors = validator.validate_query(query)
    if errors:
        print(f"❌ Validation errors:")
        for error in errors:
            print(f"  - {error}")
        return None
    
    suggestions = validator.suggest_fixes(query)
    if suggestions:
        print(f"💡 Suggestions:")
        for suggestion in suggestions:
            print(f"  - {suggestion}")
    
    print(f"✅ Query validation passed")
    return query
```

#### 2. Query debugging with dry run

```python
async def debug_query_execution(client, workspace_id: str, query: str):
    """Debug query execution step by step."""
    
    print(f"🔍 Debugging query execution...")
    print(f"Workspace: {workspace_id[:8]}...")
    print(f"Query: {query}")
    
    try:
        # Test with a simple query first
        test_query = "print 'connection test'"
        test_result = await client.query_workspace(workspace_id, test_query)
        
        if not test_result.succeeded:
            print(f"❌ Basic connectivity failed: {test_result.error_message}")
            return
        
        print(f"✅ Basic connectivity successful")
        
        # Test with limited version of main query
        limited_query = f"{query} | take 1"
        limited_result = await client.query_workspace(workspace_id, limited_query)
        
        if not limited_result.succeeded:
            print(f"❌ Limited query failed: {limited_result.error_message}")
            print(f"💡 Check query syntax and table availability")
            return
        
        print(f"✅ Limited query successful: {limited_result.record_count} records")
        
        # Execute full query
        full_result = await client.query_workspace(workspace_id, query)
        
        if full_result.succeeded:
            print(f"✅ Full query successful: {full_result.record_count} records")
            print(f"Execution time: {full_result.execution_time:.2f}s")
        else:
            print(f"❌ Full query failed: {full_result.error_message}")
    
    except Exception as e:
        print(f"❌ Exception during debugging: {e}")
```

### Problem: Query timeout errors

**Symptoms:**
```
ERROR: Query execution timed out after 300 seconds
```

**Solutions:**

#### 1. Query optimization

```python
class QueryOptimizer:
    """Optimize KQL queries for better performance."""
    
    @staticmethod
    def optimize_time_range(query: str, hours: int = 24) -> str:
        """Add optimal time range filtering."""
        
        if 'TimeGenerated' not in query:
            time_filter = f"| where TimeGenerated > ago({hours}h)"
            
            # Insert after table name
            lines = query.split('\n')
            if lines:
                lines.insert(1, time_filter)
                return '\n'.join(lines)
        
        return query
    
    @staticmethod
    def add_early_filtering(query: str, filters: Dict[str, str]) -> str:
        """Add early filtering to reduce data processed."""
        
        early_filters = []
        for column, value in filters.items():
            if isinstance(value, str):
                early_filters.append(f"| where {column} has '{value}'")
            else:
                early_filters.append(f"| where {column} == {value}")
        
        if early_filters:
            lines = query.split('\n')
            # Insert after time range filter
            insert_index = 1
            for i, line in enumerate(lines):
                if 'TimeGenerated' in line:
                    insert_index = i + 1
                    break
            
            for filter_line in early_filters:
                lines.insert(insert_index, filter_line)
                insert_index += 1
            
            return '\n'.join(lines)
        
        return query
    
    @staticmethod
    def add_progressive_sampling(query: str, sample_rate: float = 0.1) -> str:
        """Add sampling for large datasets."""
        
        if 'sample' not in query.lower():
            sample_line = f"| sample {sample_rate}"
            
            lines = query.split('\n')
            # Add sampling early in the pipeline
            lines.insert(-1, sample_line)  # Before final operations
            return '\n'.join(lines)
        
        return query

# Example usage
optimizer = QueryOptimizer()

original_query = """
SecurityEvent
| summarize count() by Account, Computer
| order by count_ desc
"""

optimized_query = optimizer.optimize_time_range(original_query, hours=1)
optimized_query = optimizer.add_early_filtering(optimized_query, {
    'EventID': '4625',  # Failed logons only
    'LogonType': '3'    # Network logons only
})

print("Optimized query:")
print(optimized_query)
```

#### 2. Batch processing for large queries

```python
async def execute_large_query_with_batching(
    client,
    workspace_id: str,
    base_query: str,
    total_hours: int = 168,  # 1 week
    batch_hours: int = 24,
    max_timeout: int = 300
):
    """Execute large time range queries in batches."""
    
    print(f"🔄 Executing large query in {batch_hours}h batches...")
    
    all_results = []
    current_offset = 0
    
    while current_offset < total_hours:
        batch_end = min(current_offset + batch_hours, total_hours)
        
        # Create time-bounded query
        time_bounded_query = f"""
        {base_query}
        | where TimeGenerated > ago({batch_end}h) and TimeGenerated <= ago({current_offset}h)
        """
        
        print(f"  Batch: {current_offset}h to {batch_end}h ago")
        
        try:
            result = await asyncio.wait_for(
                client.query_workspace(workspace_id, time_bounded_query),
                timeout=max_timeout
            )
            
            if result.succeeded:
                all_results.extend(result.data or [])
                print(f"    ✅ {result.record_count} records ({result.execution_time:.1f}s)")
            else:
                print(f"    ❌ Batch failed: {result.error_message}")
        
        except asyncio.TimeoutError:
            print(f"    ⏰ Batch timed out")
        except Exception as e:
            print(f"    ❌ Batch error: {e}")
        
        current_offset = batch_end
        
        # Brief pause between batches
        await asyncio.sleep(1)
    
    print(f"✅ Batched execution complete: {len(all_results)} total records")
    return all_results
```

## Data ingestion issues

### Problem: Data ingestion failures

**Symptoms:**
```
ERROR: Data ingestion failed: 400 Bad Request - Invalid data format
```

**Solutions:**

#### 1. Data validation and formatting

```python
import json
from datetime import datetime, timezone
from typing import List, Dict, Any

class DataValidator:
    """Validate data before ingestion to Azure Monitor."""
    
    @staticmethod
    def validate_log_entry(entry: Dict[str, Any]) -> List[str]:
        """Validate a single log entry."""
        
        errors = []
        
        # Check required TimeGenerated field
        if 'TimeGenerated' not in entry:
            errors.append("Missing required 'TimeGenerated' field")
        else:
            time_value = entry['TimeGenerated']
            if not isinstance(time_value, str):
                errors.append("'TimeGenerated' must be a string in ISO 8601 format")
            else:
                try:
                    datetime.fromisoformat(time_value.replace('Z', '+00:00'))
                except ValueError:
                    errors.append("'TimeGenerated' is not in valid ISO 8601 format")
        
        # Check for null values in non-nullable fields
        for key, value in entry.items():
            if value is None and key in ['TimeGenerated']:
                errors.append(f"Field '{key}' cannot be null")
        
        # Check field name format
        for key in entry.keys():
            if not key.replace('_', '').replace('-', '').isalnum():
                errors.append(f"Field name '{key}' contains invalid characters")
            
            if key.startswith('_'):
                errors.append(f"Field name '{key}' cannot start with underscore")
        
        # Check data types
        for key, value in entry.items():
            if isinstance(value, (dict, list)) and key != 'AdditionalFields':
                errors.append(f"Field '{key}' contains complex data type that may not be supported")
        
        return errors
    
    @staticmethod
    def format_for_ingestion(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format data for Azure Monitor ingestion."""
        
        formatted_data = []
        
        for entry in data:
            formatted_entry = {}
            
            for key, value in entry.items():
                # Ensure TimeGenerated is properly formatted
                if key == 'TimeGenerated':
                    if isinstance(value, datetime):
                        formatted_entry[key] = value.isoformat()
                    else:
                        formatted_entry[key] = value
                
                # Convert complex objects to strings
                elif isinstance(value, (dict, list)):
                    formatted_entry[key] = json.dumps(value) if value else ""
                
                # Handle None values
                elif value is None:
                    formatted_entry[key] = ""
                
                # Ensure strings are properly encoded
                elif isinstance(value, str):
                    formatted_entry[key] = value.encode('utf-8', 'replace').decode('utf-8')
                
                else:
                    formatted_entry[key] = value
            
            formatted_data.append(formatted_entry)
        
        return formatted_data

# Usage example
async def safe_data_ingestion(client, data: List[Dict[str, Any]], stream_name: str):
    """Safely ingest data with validation."""
    
    validator = DataValidator()
    
    # Validate all entries
    all_errors = []
    valid_entries = []
    
    for i, entry in enumerate(data):
        errors = validator.validate_log_entry(entry)
        if errors:
            all_errors.extend([f"Entry {i}: {error}" for error in errors])
        else:
            valid_entries.append(entry)
    
    if all_errors:
        print(f"❌ Data validation errors:")
        for error in all_errors[:10]:  # Show first 10 errors
            print(f"  - {error}")
        
        if len(all_errors) > 10:
            print(f"  ... and {len(all_errors) - 10} more errors")
        
        print(f"💡 Fix validation errors before ingesting data")
        return None
    
    # Format data for ingestion
    formatted_data = validator.format_for_ingestion(valid_entries)
    
    # Attempt ingestion
    try:
        result = await client.upload_logs(
            data=formatted_data,
            stream_name=stream_name
        )
        
        if result.succeeded:
            print(f"✅ Successfully ingested {len(formatted_data)} records")
        else:
            print(f"❌ Ingestion failed: {result.error_message}")
        
        return result
    
    except Exception as e:
        print(f"❌ Ingestion exception: {e}")
        return None
```

#### 2. DCR configuration validation

```python
async def validate_dcr_configuration(client, dcr_endpoint: str, stream_name: str):
    """Validate Data Collection Rule configuration."""
    
    print(f"🔍 Validating DCR configuration...")
    print(f"DCR Endpoint: {dcr_endpoint}")
    print(f"Stream Name: {stream_name}")
    
    try:
        # Test with minimal data
        test_data = [{
            "TimeGenerated": datetime.now(timezone.utc).isoformat(),
            "Message": "DCR validation test",
            "TestField": "test_value"
        }]
        
        result = await client.upload_logs(
            data=test_data,
            stream_name=stream_name
        )
        
        if result.succeeded:
            print(f"✅ DCR configuration is valid")
            return True
        else:
            print(f"❌ DCR configuration error: {result.error_message}")
            
            # Common DCR issues and solutions
            if "stream name" in result.error_message.lower():
                print(f"💡 Check that stream name '{stream_name}' is correctly configured in DCR")
            
            if "endpoint" in result.error_message.lower():
                print(f"💡 Verify DCR endpoint URL is correct")
            
            if "unauthorized" in result.error_message.lower():
                print(f"💡 Check authentication and DCR permissions")
            
            return False
    
    except Exception as e:
        print(f"❌ DCR validation failed: {e}")
        return False
```

### Problem: Rate limiting and throttling

**Symptoms:**
```
ERROR: 429 Too Many Requests - Rate limit exceeded
```

**Solutions:**

#### 1. Implement exponential backoff

```python
import asyncio
import random
from azure.core.exceptions import HttpResponseError

class RateLimitHandler:
    """Handle rate limiting with exponential backoff."""
    
    def __init__(self, max_retries: int = 5, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    async def execute_with_rate_limiting(self, operation, *args, **kwargs):
        """Execute operation with rate limiting handling."""
        
        for attempt in range(self.max_retries):
            try:
                return await operation(*args, **kwargs)
            
            except HttpResponseError as e:
                if e.status_code == 429:  # Rate limited
                    if attempt == self.max_retries - 1:
                        raise e
                    
                    # Extract retry-after header if available
                    retry_after = e.response.headers.get('Retry-After', self.base_delay)
                    try:
                        delay = float(retry_after)
                    except (ValueError, TypeError):
                        delay = self.base_delay * (2 ** attempt)
                    
                    # Add jitter
                    jitter = random.uniform(0.1, 0.3) * delay
                    total_delay = delay + jitter
                    
                    print(f"⏳ Rate limited, retrying in {total_delay:.1f}s (attempt {attempt + 1}/{self.max_retries})")
                    await asyncio.sleep(total_delay)
                else:
                    raise e
        
        raise Exception(f"Max retries exceeded for rate limiting")
```

#### 2. Request batching and queuing

```python
import asyncio
from collections import deque
from typing import Callable, Any

class RequestQueue:
    """Queue requests to respect rate limits."""
    
    def __init__(self, max_requests_per_minute: int = 60):
        self.max_requests_per_minute = max_requests_per_minute
        self.request_times = deque()
        self.semaphore = asyncio.Semaphore(max_requests_per_minute)
        self.lock = asyncio.Lock()
    
    async def execute_request(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute request with rate limiting."""
        
        async with self.semaphore:
            async with self.lock:
                now = time.time()
                
                # Remove requests older than 1 minute
                while self.request_times and (now - self.request_times[0]) > 60:
                    self.request_times.popleft()
                
                # Check if we need to wait
                if len(self.request_times) >= self.max_requests_per_minute:
                    wait_time = 60 - (now - self.request_times[0])
                    if wait_time > 0:
                        print(f"⏳ Rate limit reached, waiting {wait_time:.1f}s")
                        await asyncio.sleep(wait_time)
                
                # Record this request
                self.request_times.append(now)
            
            # Execute the operation
            return await operation(*args, **kwargs)
```

## Configuration issues

### Problem: Workspace configuration errors

**Symptoms:**
```
ERROR: Workspace configuration validation failed
```

**Solutions:**

#### 1. Configuration validation tool

```python
import yaml
from pathlib import Path
from typing import List, Dict, Any

class WorkspaceConfigValidator:
    """Validate workspace configuration files."""
    
    def validate_config_file(self, config_path: str) -> List[str]:
        """Validate workspace configuration file."""
        
        errors = []
        config_file = Path(config_path)
        
        # Check file exists
        if not config_file.exists():
            errors.append(f"Configuration file not found: {config_path}")
            return errors
        
        try:
            # Load YAML
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
        
        except yaml.YAMLError as e:
            errors.append(f"Invalid YAML syntax: {e}")
            return errors
        
        # Validate structure
        if not isinstance(config, dict):
            errors.append("Configuration must be a YAML object")
            return errors
        
        if 'workspaces' not in config:
            errors.append("Configuration must contain 'workspaces' section")
            return errors
        
        workspaces = config['workspaces']
        if not isinstance(workspaces, list):
            errors.append("'workspaces' must be a list")
            return errors
        
        # Validate each workspace
        customer_ids = set()
        aliases = set()
        
        for i, workspace in enumerate(workspaces):
            workspace_errors = self._validate_workspace(workspace, i)
            errors.extend(workspace_errors)
            
            # Check for duplicates
            customer_id = workspace.get('customer_id')
            if customer_id:
                if customer_id in customer_ids:
                    errors.append(f"Duplicate customer_id in workspace {i}: {customer_id}")
                customer_ids.add(customer_id)
            
            alias = workspace.get('alias')
            if alias:
                if alias in aliases:
                    errors.append(f"Duplicate alias in workspace {i}: {alias}")
                aliases.add(alias)
        
        return errors
    
    def _validate_workspace(self, workspace: Dict[str, Any], index: int) -> List[str]:
        """Validate individual workspace configuration."""
        
        errors = []
        
        # Required fields
        if 'customer_id' not in workspace:
            errors.append(f"Workspace {index}: Missing required 'customer_id'")
        else:
            customer_id = workspace['customer_id']
            if not isinstance(customer_id, str) or len(customer_id) != 36:
                errors.append(f"Workspace {index}: 'customer_id' must be a valid GUID")
        
        # Optional but recommended fields
        if 'alias' not in workspace:
            errors.append(f"Workspace {index}: Consider adding 'alias' for easier identification")
        
        # Validate parameters
        if 'parameters' in workspace:
            parameters = workspace['parameters']
            if not isinstance(parameters, dict):
                errors.append(f"Workspace {index}: 'parameters' must be an object")
            else:
                # Validate parameter values
                for key, value in parameters.items():
                    if not isinstance(key, str):
                        errors.append(f"Workspace {index}: Parameter key must be string: {key}")
                    
                    if key == 'row_level_security_tag' and not isinstance(value, str):
                        errors.append(f"Workspace {index}: 'row_level_security_tag' must be a string")
        
        return errors

# Usage example
def validate_workspace_config(config_path: str) -> bool:
    """Validate workspace configuration and report errors."""
    
    validator = WorkspaceConfigValidator()
    errors = validator.validate_config_file(config_path)
    
    if errors:
        print(f"❌ Configuration validation failed for {config_path}:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print(f"✅ Configuration validation passed for {config_path}")
        return True
```

#### 2. Environment variable debugging

```python
import os
from typing import Dict, List

def debug_environment_configuration() -> Dict[str, Any]:
    """Debug environment variable configuration."""
    
    print("🔍 Debugging environment configuration...")
    
    # Required environment variables
    required_vars = [
        'DCR_LOGS_INGESTION_ENDPOINT',
        'DCR_RULE_ID',
        'DCR_STREAM_NAME'
    ]
    
    # Optional environment variables
    optional_vars = [
        'AZURE_CLIENT_ID',
        'AZURE_CLIENT_SECRET', 
        'AZURE_TENANT_ID',
        'LOG_LEVEL',
        'MAX_CONCURRENT_QUERIES',
        'BATCH_HOURS',
        'RETRY_MAX_ATTEMPTS'
    ]
    
    config_status = {
        'required_vars': {},
        'optional_vars': {},
        'missing_required': [],
        'issues': []
    }
    
    # Check required variables
    for var in required_vars:
        value = os.getenv(var)
        config_status['required_vars'][var] = {
            'configured': value is not None,
            'value_preview': value[:20] + '...' if value and len(value) > 20 else value
        }
        
        if not value:
            config_status['missing_required'].append(var)
    
    # Check optional variables
    for var in optional_vars:
        value = os.getenv(var)
        config_status['optional_vars'][var] = {
            'configured': value is not None,
            'value_preview': value[:20] + '...' if value and len(value) > 20 else value
        }
    
    # Validate DCR endpoint format
    dcr_endpoint = os.getenv('DCR_LOGS_INGESTION_ENDPOINT')
    if dcr_endpoint:
        if not dcr_endpoint.startswith('https://'):
            config_status['issues'].append("DCR_LOGS_INGESTION_ENDPOINT should start with 'https://'")
        
        if not '.ingest.monitor.azure.com' in dcr_endpoint:
            config_status['issues'].append("DCR_LOGS_INGESTION_ENDPOINT should contain '.ingest.monitor.azure.com'")
    
    # Validate numeric values
    numeric_vars = ['MAX_CONCURRENT_QUERIES', 'BATCH_HOURS', 'RETRY_MAX_ATTEMPTS']
    for var in numeric_vars:
        value = os.getenv(var)
        if value:
            try:
                int(value)
            except ValueError:
                config_status['issues'].append(f"{var} should be a numeric value, got: {value}")
    
    # Print summary
    print(f"Required variables: {len(required_vars) - len(config_status['missing_required'])}/{len(required_vars)} configured")
    print(f"Optional variables: {sum(1 for v in config_status['optional_vars'].values() if v['configured'])}/{len(optional_vars)} configured")
    
    if config_status['missing_required']:
        print(f"❌ Missing required variables:")
        for var in config_status['missing_required']:
            print(f"  - {var}")
    
    if config_status['issues']:
        print(f"⚠️ Configuration issues:")
        for issue in config_status['issues']:
            print(f"  - {issue}")
    
    return config_status
```

## Performance issues

### Problem: Slow query execution

**Symptoms:**
```
Query execution time: 45.3 seconds (expected < 10 seconds)
```

**Solutions:**

#### 1. Query performance analysis

```python
import time
from typing import Dict, Any

async def analyze_query_performance(
    client,
    workspace_id: str, 
    query: str,
    iterations: int = 3
) -> Dict[str, Any]:
    """Analyze query performance over multiple iterations."""
    
    print(f"🔬 Analyzing query performance...")
    print(f"Query: {query[:100]}...")
    
    execution_times = []
    record_counts = []
    
    for i in range(iterations):
        print(f"  Iteration {i + 1}/{iterations}")
        
        start_time = time.time()
        result = await client.query_workspace(workspace_id, query)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        if result.succeeded:
            execution_times.append(execution_time)
            record_counts.append(result.record_count)
            print(f"    ✅ {execution_time:.2f}s, {result.record_count} records")
        else:
            print(f"    ❌ Failed: {result.error_message}")
    
    if execution_times:
        avg_time = sum(execution_times) / len(execution_times)
        min_time = min(execution_times)
        max_time = max(execution_times)
        avg_records = sum(record_counts) / len(record_counts)
        
        analysis = {
            'avg_execution_time': avg_time,
            'min_execution_time': min_time,
            'max_execution_time': max_time,
            'time_variance': max_time - min_time,
            'avg_record_count': avg_records,
            'records_per_second': avg_records / avg_time if avg_time > 0 else 0
        }
        
        print(f"\n📊 Performance Analysis:")
        print(f"  Average time: {avg_time:.2f}s")
        print(f"  Time range: {min_time:.2f}s - {max_time:.2f}s")
        print(f"  Average records: {avg_records:.0f}")
        print(f"  Records/second: {analysis['records_per_second']:.0f}")
        
        # Performance recommendations
        if avg_time > 30:
            print(f"\n💡 Performance Recommendations:")
            print(f"  - Query is slow (>{avg_time:.1f}s), consider:")
            print(f"    • Adding time range filters")
            print(f"    • Using more selective where clauses")
            print(f"    • Adding take/limit clauses")
            print(f"    • Breaking into smaller time batches")
        
        return analysis
    
    else:
        print(f"❌ No successful executions for analysis")
        return {}
```

#### 2. Memory usage monitoring

```python
import psutil
import gc
from typing import Dict

class MemoryMonitor:
    """Monitor memory usage during operations."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.initial_memory = self.get_memory_usage()
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage."""
        
        memory_info = self.process.memory_info()
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,  # Resident Set Size
            'vms_mb': memory_info.vms / 1024 / 1024,  # Virtual Memory Size
            'percent': self.process.memory_percent()
        }
    
    async def monitor_operation(self, operation, *args, **kwargs):
        """Monitor memory usage during operation."""
        
        print(f"🧠 Starting memory monitoring...")
        
        start_memory = self.get_memory_usage()
        print(f"Initial memory: {start_memory['rss_mb']:.1f} MB")
        
        try:
            result = await operation(*args, **kwargs)
            
            end_memory = self.get_memory_usage()
            memory_delta = end_memory['rss_mb'] - start_memory['rss_mb']
            
            print(f"Final memory: {end_memory['rss_mb']:.1f} MB")
            print(f"Memory delta: {memory_delta:+.1f} MB")
            
            # Trigger garbage collection
            gc.collect()
            
            post_gc_memory = self.get_memory_usage()
            gc_recovered = end_memory['rss_mb'] - post_gc_memory['rss_mb']
            
            if gc_recovered > 10:  # More than 10MB recovered
                print(f"GC recovered: {gc_recovered:.1f} MB")
            
            return result
        
        except Exception as e:
            error_memory = self.get_memory_usage()
            print(f"Error memory: {error_memory['rss_mb']:.1f} MB")
            raise e
```

## Getting help and support

### Enable detailed logging

```python
import logging

# Enable detailed logging for debugging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable Azure SDK logging
logging.getLogger('azure').setLevel(logging.DEBUG)
logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.DEBUG)
```

### Collect diagnostic information

```python
async def collect_diagnostic_info(client, workspace_manager):
    """Collect comprehensive diagnostic information."""
    
    print("🩺 Collecting diagnostic information...")
    
    diagnostic_info = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'environment': {},
        'configuration': {},
        'connectivity': {},
        'performance': {}
    }
    
    # Environment information
    diagnostic_info['environment'] = {
        'python_version': sys.version,
        'platform': platform.platform(),
        'hostname': socket.gethostname(),
        'environment_variables': debug_environment_configuration()
    }
    
    # Configuration validation
    try:
        config_validator = WorkspaceConfigValidator()
        config_errors = config_validator.validate_config_file("workspaces.yaml")
        diagnostic_info['configuration'] = {
            'workspace_count': len(workspace_manager.workspaces),
            'validation_errors': config_errors
        }
    except Exception as e:
        diagnostic_info['configuration'] = {'error': str(e)}
    
    # Connectivity tests
    try:
        connectivity_results = await test_connectivity()
        diagnostic_info['connectivity'] = connectivity_results
    except Exception as e:
        diagnostic_info['connectivity'] = {'error': str(e)}
    
    # Performance baseline
    try:
        if workspace_manager.workspaces:
            test_workspace = workspace_manager.workspaces[0]
            perf_results = await analyze_query_performance(
                client, 
                test_workspace.customer_id,
                "print 'performance test'",
                iterations=1
            )
            diagnostic_info['performance'] = perf_results
    except Exception as e:
        diagnostic_info['performance'] = {'error': str(e)}
    
    # Save diagnostic report
    report_file = f"diagnostic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(diagnostic_info, f, indent=2, default=str)
    
    print(f"✅ Diagnostic report saved: {report_file}")
    return diagnostic_info
```

### Report issues

When reporting issues, include:

1. **Error message and stack trace**
2. **Diagnostic information** (from above script)
3. **Steps to reproduce**
4. **Expected vs actual behavior**
5. **Configuration files** (sanitized)
6. **Environment details**

## Next steps

- [Best practices](best-practices.md) - Prevention and optimization guidance
- [Performance tuning](performance-tuning.md) - Advanced optimization techniques
- [API reference](api-reference.md) - Complete API documentation
- [Examples](examples/) - Working code examples