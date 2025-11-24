---
title: Advanced examples
description: Explore advanced scenarios and integration patterns with the Microsoft Sentinel Log Aggregator.
author: Alistair Ross
ms.author: community
ms.service: sentinel
ms.topic: tutorial
ms.date: 2025-11-01
---

# Advanced examples

This article demonstrates advanced scenarios and integration patterns with the Microsoft Sentinel Log Aggregator, including complex data transformations, automated workflows, and enterprise-scale deployments.

## Example 1: Long-running operations with progress tracking

Implement batch operations with comprehensive progress monitoring and cancellation support.

```python
import asyncio
import signal
from datetime import datetime, timezone, timedelta
from azure.identity.aio import DefaultAzureCredential
from sentinel_log_aggregator import (
    SentinelAggregatorClient,
    SentinelAggregatorClientOptions,
    WorkspaceManager,
    BatchStatus
)

class BatchOperationManager:
    """Manages long-running batch operations with progress tracking."""
    
    def __init__(self, client, workspace_manager):
        self.client = client
        self.workspace_manager = workspace_manager
        self.is_cancelled = False
        self.current_poller = None
    
    async def execute_comprehensive_batch(self, lookback_period="P30D", batch_time_size="PT24H"):
        """Execute comprehensive batch operation with full progress tracking."""
        
        print(f"Starting comprehensive batch operation...")
        print(f"  Workspaces: {self.workspace_manager.count()}")
        print(f"  Lookback period: {lookback_period}")
        print(f"  Batch time size: {batch_time_size}"))
        
        # Prepare query list
        queries = [
            "query_incident_summary",
            "query_user_summary", 
            "query_security_alerts",
            "query_compliance_events"
        ]
        
        # Filter workspaces that support all queries
        supported_workspaces = []
        for query in queries:
            query_workspaces = self.workspace_manager.for_query(query)
            if query_workspaces.count() > 0:
                supported_workspaces.extend(query_workspaces.workspaces)
        
        # Remove duplicates while preserving order
        unique_workspaces = []
        seen_ids = set()
        for ws in supported_workspaces:
            if ws.customer_id not in seen_ids:
                unique_workspaces.append(ws)
                seen_ids.add(ws.customer_id)
        
        print(f"  Filtered to {len(unique_workspaces)} workspaces with query support")
        
        try:
            # Start batch operation
            self.current_poller = await self.client.begin_batch_operation(
                workspaces=unique_workspaces,
                queries=queries,
                lookback_period=lookback_period,
                batch_time_size=batch_time_size
            )
            
            print(f"Batch operation started: {self.current_poller.get_status()}")
            
            # Monitor progress with detailed reporting
            start_time = datetime.now()
            last_report_time = start_time
            report_interval = 30  # seconds
            
            while not self.current_poller.done() and not self.is_cancelled:
                try:
                    # Get current status with timeout
                    result = await asyncio.wait_for(
                        self.current_poller.result(timeout=10),
                        timeout=15
                    )
                    
                    current_time = datetime.now()
                    
                    # Report progress periodically
                    if (current_time - last_report_time).seconds >= report_interval:
                        await self._report_progress(result, start_time, current_time)
                        last_report_time = current_time
                    
                    # Process any completed operations
                    if result.partial_results:
                        await self._process_partial_results(result.partial_results)
                    
                    # Brief pause to avoid busy waiting
                    await asyncio.sleep(5)
                
                except asyncio.TimeoutError:
                    print("⏳ Operation still in progress...")
                except Exception as e:
                    print(f"❌ Error monitoring progress: {e}")
                    break
            
            # Get final results
            if self.is_cancelled:
                print("🛑 Operation cancelled by user")
                return None
            
            final_result = await self.current_poller.result()
            
            # Generate comprehensive report
            await self._generate_final_report(final_result, start_time)
            
            return final_result
        
        except Exception as e:
            print(f"❌ Batch operation failed: {e}")
            raise
    
    async def _report_progress(self, result, start_time, current_time):
        """Generate detailed progress report."""
        
        elapsed = current_time - start_time
        progress_pct = (result.completed_operations / result.total_operations) * 100
        
        print(f"\n📊 Progress Report ({current_time.strftime('%H:%M:%S')})")
        print(f"  Elapsed time: {elapsed}")
        print(f"  Progress: {result.completed_operations}/{result.total_operations} ({progress_pct:.1f}%)")
        print(f"  Successful: {result.success_count}")
        print(f"  Failed: {result.error_count}")
        
        # Estimate completion time
        if result.completed_operations > 0:
            ops_per_second = result.completed_operations / elapsed.total_seconds()
            remaining_ops = result.total_operations - result.completed_operations
            estimated_remaining = timedelta(seconds=remaining_ops / ops_per_second)
            estimated_completion = current_time + estimated_remaining
            
            print(f"  Estimated completion: {estimated_completion.strftime('%H:%M:%S')}")
            print(f"  Estimated remaining: {estimated_remaining}")
    
    async def _process_partial_results(self, partial_results):
        """Process completed operations as they finish."""
        
        for partial in partial_results:
            if partial.succeeded:
                workspace_alias = partial.workspace_alias or partial.workspace_id[:8]
                print(f"  ✅ {workspace_alias} - {partial.query}: {partial.record_count} records ({partial.execution_time:.1f}s)")
            else:
                workspace_alias = partial.workspace_alias or partial.workspace_id[:8]
                print(f"  ❌ {workspace_alias} - {partial.query}: {partial.error_message}")
    
    async def _generate_final_report(self, final_result, start_time):
        """Generate comprehensive final execution report."""
        
        end_time = datetime.now()
        total_duration = end_time - start_time
        
        print(f"\n🎯 Batch Operation Complete")
        print(f"  Total duration: {total_duration}")
        print(f"  Status: {final_result.status}")
        print(f"  Total operations: {final_result.total_operations}")
        print(f"  Successful: {final_result.success_count}")
        print(f"  Failed: {final_result.error_count}")
        print(f"  Success rate: {(final_result.success_count / final_result.total_operations) * 100:.1f}%")
        
        # Calculate statistics
        total_records = sum(exec.record_count for exec in final_result.executions if exec.succeeded)
        avg_execution_time = sum(exec.execution_time for exec in final_result.executions if exec.succeeded) / max(final_result.success_count, 1)
        
        print(f"  Total records processed: {total_records:,}")
        print(f"  Average query time: {avg_execution_time:.2f}s")
        print(f"  Records per second: {total_records / total_duration.total_seconds():.1f}")
        
        # Breakdown by workspace
        workspace_stats = {}
        for execution in final_result.executions:
            workspace = execution.workspace_alias or execution.workspace_id[:8]
            if workspace not in workspace_stats:
                workspace_stats[workspace] = {'successful': 0, 'failed': 0, 'records': 0}
            
            if execution.succeeded:
                workspace_stats[workspace]['successful'] += 1
                workspace_stats[workspace]['records'] += execution.record_count
            else:
                workspace_stats[workspace]['failed'] += 1
        
        print(f"\n📈 Workspace Summary:")
        for workspace, stats in workspace_stats.items():
            total_ops = stats['successful'] + stats['failed']
            success_rate = (stats['successful'] / total_ops) * 100 if total_ops > 0 else 0
            print(f"  {workspace}: {stats['successful']}/{total_ops} ops ({success_rate:.1f}% success), {stats['records']:,} records")
        
        # Create summary for upload
        summary_data = {
            "TimeGenerated": end_time.isoformat(),
            "BatchOperationId": getattr(final_result, 'operation_id', 'unknown'),
            "TotalDurationSeconds": total_duration.total_seconds(),
            "TotalOperations": final_result.total_operations,
            "SuccessfulOperations": final_result.success_count,
            "FailedOperations": final_result.error_count,
            "SuccessRate": (final_result.success_count / final_result.total_operations) * 100,
            "TotalRecordsProcessed": total_records,
            "AverageQueryTimeSeconds": avg_execution_time,
            "RecordsPerSecond": total_records / total_duration.total_seconds(),
            "WorkspacesProcessed": len(workspace_stats),
            "ReportType": "batch_operation_summary"
        }
        
        try:
            upload_result = await self.client.upload_logs(
                data=[summary_data],
                stream_name="Custom-BatchOperationSummary_CL"
            )
            
            if upload_result.succeeded:
                print(f"  ✅ Summary uploaded to BatchOperationSummary_CL")
        
        except Exception as e:
            print(f"  ⚠️ Failed to upload summary: {e}")
    
    def cancel_operation(self):
        """Cancel the current batch operation."""
        self.is_cancelled = True
        if self.current_poller:
            # Note: Actual cancellation depends on Azure SDK LRO implementation
            print("🛑 Cancellation requested...")

async def advanced_batch_operations():
    """Demonstrate advanced batch operations with full monitoring."""
    
    options = SentinelAggregatorClientOptions.from_environment()
    credential = DefaultAzureCredential()
    
    async with SentinelAggregatorClient(
        dcr_logs_ingestion_endpoint=options.dcr_logs_ingestion_endpoint,
        credential=credential,
        options=options
    ) as client:
        
        # Load workspace configuration
        workspace_manager = WorkspaceManager.from_file("workspaces.yaml")
        
        # Create batch operation manager
        batch_manager = BatchOperationManager(client, workspace_manager)
        
        # Set up signal handler for graceful cancellation
        def signal_handler(signum, frame):
            print(f"\n🛑 Received signal {signum}, initiating graceful shutdown...")
            batch_manager.cancel_operation()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Execute comprehensive batch operation
            result = await batch_manager.execute_comprehensive_batch(
                lookback_period="P7D",
                batch_time_size="PT12H"
            )
            
            if result:
                print(f"\n🎉 Batch operation completed successfully!")
                return result
        
        except KeyboardInterrupt:
            print(f"\n🛑 Operation interrupted by user")
        except Exception as e:
            print(f"\n❌ Batch operation failed: {e}")
            raise

asyncio.run(advanced_batch_operations())
```

## Example 2: Advanced data transformation and analytics

Implement sophisticated data processing pipelines with custom analytics.

```python
import asyncio
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from azure.identity.aio import DefaultAzureCredential
from sentinel_log_aggregator import (
    SentinelAggregatorClient,
    SentinelAggregatorClientOptions,
    WorkspaceManager
)

@dataclass
class ThreatIntelligence:
    """Threat intelligence data structure."""
    indicator: str
    indicator_type: str
    threat_level: str
    confidence: float
    source: str
    first_seen: datetime
    last_seen: datetime

class SecurityAnalyticsEngine:
    """Advanced security analytics and data transformation engine."""
    
    def __init__(self, client):
        self.client = client
        self.threat_intel = self._load_threat_intelligence()
    
    def _load_threat_intelligence(self) -> List[ThreatIntelligence]:
        """Load threat intelligence data (mock implementation)."""
        return [
            ThreatIntelligence(
                indicator="185.220.101.42",
                indicator_type="ip",
                threat_level="high",
                confidence=0.95,
                source="internal_analysis",
                first_seen=datetime.now() - timedelta(days=30),
                last_seen=datetime.now() - timedelta(hours=2)
            ),
            ThreatIntelligence(
                indicator="malicious-domain.com",
                indicator_type="domain",
                threat_level="medium",
                confidence=0.75,
                source="threat_feed",
                first_seen=datetime.now() - timedelta(days=15),
                last_seen=datetime.now() - timedelta(hours=6)
            )
        ]
    
    async def comprehensive_security_analysis(self, workspace_manager: WorkspaceManager, days_back: int = 7):
        """Perform comprehensive security analysis across all workspaces."""
        
        print(f"🔍 Starting comprehensive security analysis...")
        
        # Define analysis queries
        analysis_queries = {
            "failed_logons": """
                SecurityEvent
                | where TimeGenerated > ago({days}d)
                | where EventID == 4625
                | summarize 
                    FailedAttempts = count(),
                    UniqueAccounts = dcount(Account),
                    UniqueSourceIPs = dcount(IpAddress),
                    FirstAttempt = min(TimeGenerated),
                    LastAttempt = max(TimeGenerated)
                    by Computer, IpAddress
                | where FailedAttempts >= 10
                | order by FailedAttempts desc
            """,
            
            "suspicious_processes": """
                SecurityEvent
                | where TimeGenerated > ago({days}d)
                | where EventID in (4688, 4689)
                | where Process has_any ("powershell.exe", "cmd.exe", "wscript.exe", "cscript.exe")
                | summarize 
                    ProcessCount = count(),
                    UniqueCommands = dcount(CommandLine),
                    Computers = make_set(Computer)
                    by Process, Account
                | where ProcessCount >= 50
                | order by ProcessCount desc
            """,
            
            "network_anomalies": """
                CommonSecurityLog
                | where TimeGenerated > ago({days}d)
                | where DeviceAction == "Deny"
                | summarize 
                    DeniedConnections = count(),
                    UniqueDestinations = dcount(DestinationIP),
                    UniqueSources = dcount(SourceIP)
                    by SourceIP, DestinationPort
                | where DeniedConnections >= 100
                | order by DeniedConnections desc
            """,
            
            "privilege_escalation": """
                SecurityEvent
                | where TimeGenerated > ago({days}d)
                | where EventID in (4672, 4673, 4674)
                | summarize 
                    PrivilegeUseCount = count(),
                    UniquePrivileges = dcount(PrivilegeList),
                    Computers = make_set(Computer)
                    by Account
                | where PrivilegeUseCount >= 20
                | order by PrivilegeUseCount desc
            """
        }
        
        # Execute analysis across all workspaces
        all_results = {}
        
        for workspace in workspace_manager.workspaces:
            workspace_alias = workspace.parameters.get('row_level_security_tag', workspace.customer_id[:8])
            workspace_results = {}
            
            print(f"  📊 Analyzing workspace: {workspace_alias}")
            
            for analysis_name, query_template in analysis_queries.items():
                try:
                    # Format query with parameters
                    query = query_template.format(days=days_back)
                    
                    result = await self.client.query_workspace(workspace.customer_id, query)
                    
                    if result.succeeded and result.data:
                        # Convert to DataFrame for analysis
                        df = pd.DataFrame(result.data)
                        
                        # Apply advanced transformations
                        enhanced_df = await self._enhance_with_threat_intel(df, analysis_name)
                        risk_scored_df = self._calculate_risk_scores(enhanced_df, analysis_name)
                        
                        workspace_results[analysis_name] = {
                            'raw_data': result.data,
                            'dataframe': risk_scored_df,
                            'record_count': result.record_count,
                            'execution_time': result.execution_time
                        }
                        
                        print(f"    ✅ {analysis_name}: {result.record_count} records")
                    else:
                        print(f"    ⚠️ {analysis_name}: No data or query failed")
                
                except Exception as e:
                    print(f"    ❌ {analysis_name}: {e}")
            
            all_results[workspace_alias] = workspace_results
        
        # Generate cross-workspace analytics
        analytics_summary = self._generate_analytics_summary(all_results)
        
        # Upload analytics results
        await self._upload_analytics_results(analytics_summary)
        
        return analytics_summary
    
    async def _enhance_with_threat_intel(self, df: pd.DataFrame, analysis_type: str) -> pd.DataFrame:
        """Enhance data with threat intelligence."""
        
        if df.empty:
            return df
        
        # Create threat intelligence lookup
        threat_lookup = {}
        for intel in self.threat_intel:
            threat_lookup[intel.indicator] = {
                'threat_level': intel.threat_level,
                'confidence': intel.confidence,
                'source': intel.source
            }
        
        # Add threat intelligence columns
        df['threat_level'] = 'unknown'
        df['threat_confidence'] = 0.0
        df['threat_source'] = 'none'
        
        # Match based on analysis type
        if analysis_type in ['failed_logons', 'network_anomalies']:
            # Look for IP address matches
            if 'IpAddress' in df.columns:
                for idx, row in df.iterrows():
                    ip = row.get('IpAddress') or row.get('SourceIP')
                    if ip and ip in threat_lookup:
                        threat_info = threat_lookup[ip]
                        df.at[idx, 'threat_level'] = threat_info['threat_level']
                        df.at[idx, 'threat_confidence'] = threat_info['confidence']
                        df.at[idx, 'threat_source'] = threat_info['source']
        
        return df
    
    def _calculate_risk_scores(self, df: pd.DataFrame, analysis_type: str) -> pd.DataFrame:
        """Calculate risk scores based on various factors."""
        
        if df.empty:
            return df
        
        # Initialize risk score
        df['risk_score'] = 0.0
        
        if analysis_type == 'failed_logons':
            # Risk score based on failed attempts, unique accounts, and threat intel
            if 'FailedAttempts' in df.columns:
                # Normalize failed attempts (0-50 scale)
                max_attempts = df['FailedAttempts'].max() if df['FailedAttempts'].max() > 0 else 1
                df['risk_score'] += (df['FailedAttempts'] / max_attempts) * 50
            
            if 'UniqueAccounts' in df.columns:
                # Add points for targeting multiple accounts
                df['risk_score'] += df['UniqueAccounts'] * 10
            
            if 'threat_level' in df.columns:
                # Add threat intelligence scoring
                threat_scores = {'high': 30, 'medium': 20, 'low': 10, 'unknown': 0}
                df['risk_score'] += df['threat_level'].map(threat_scores)
        
        elif analysis_type == 'suspicious_processes':
            # Risk score based on process count and command diversity
            if 'ProcessCount' in df.columns:
                max_processes = df['ProcessCount'].max() if df['ProcessCount'].max() > 0 else 1
                df['risk_score'] += (df['ProcessCount'] / max_processes) * 40
            
            if 'UniqueCommands' in df.columns:
                df['risk_score'] += df['UniqueCommands'] * 5
        
        elif analysis_type == 'network_anomalies':
            # Risk score based on denied connections and destinations
            if 'DeniedConnections' in df.columns:
                max_denied = df['DeniedConnections'].max() if df['DeniedConnections'].max() > 0 else 1
                df['risk_score'] += (df['DeniedConnections'] / max_denied) * 35
            
            if 'UniqueDestinations' in df.columns:
                df['risk_score'] += df['UniqueDestinations'] * 3
            
            if 'threat_level' in df.columns:
                threat_scores = {'high': 25, 'medium': 15, 'low': 5, 'unknown': 0}
                df['risk_score'] += df['threat_level'].map(threat_scores)
        
        elif analysis_type == 'privilege_escalation':
            # Risk score based on privilege use frequency
            if 'PrivilegeUseCount' in df.columns:
                max_priv_use = df['PrivilegeUseCount'].max() if df['PrivilegeUseCount'].max() > 0 else 1
                df['risk_score'] += (df['PrivilegeUseCount'] / max_priv_use) * 60
            
            if 'UniquePrivileges' in df.columns:
                df['risk_score'] += df['UniquePrivileges'] * 8
        
        # Categorize risk levels
        df['risk_category'] = pd.cut(
            df['risk_score'], 
            bins=[0, 25, 50, 75, 100], 
            labels=['Low', 'Medium', 'High', 'Critical'],
            include_lowest=True
        )
        
        return df
    
    def _generate_analytics_summary(self, all_results: Dict) -> Dict[str, Any]:
        """Generate comprehensive analytics summary."""
        
        summary = {
            'analysis_timestamp': datetime.now(timezone.utc).isoformat(),
            'workspaces_analyzed': len(all_results),
            'total_records_analyzed': 0,
            'high_risk_findings': [],
            'workspace_summaries': {},
            'cross_workspace_patterns': {},
            'recommendations': []
        }
        
        # Aggregate data across workspaces
        all_failed_logons = []
        all_suspicious_processes = []
        all_network_anomalies = []
        all_privilege_escalations = []
        
        for workspace_alias, workspace_results in all_results.items():
            workspace_summary = {
                'total_findings': 0,
                'high_risk_findings': 0,
                'critical_risk_findings': 0,
                'analysis_types': {}
            }
            
            for analysis_type, analysis_data in workspace_results.items():
                if 'dataframe' in analysis_data and not analysis_data['dataframe'].empty:
                    df = analysis_data['dataframe']
                    
                    # Count findings by risk level
                    risk_counts = df['risk_category'].value_counts().to_dict()
                    workspace_summary['analysis_types'][analysis_type] = {
                        'total_findings': len(df),
                        'risk_breakdown': risk_counts,
                        'avg_risk_score': df['risk_score'].mean(),
                        'max_risk_score': df['risk_score'].max()
                    }
                    
                    workspace_summary['total_findings'] += len(df)
                    workspace_summary['high_risk_findings'] += risk_counts.get('High', 0)
                    workspace_summary['critical_risk_findings'] += risk_counts.get('Critical', 0)
                    
                    summary['total_records_analyzed'] += analysis_data['record_count']
                    
                    # Collect high-risk findings
                    high_risk_findings = df[df['risk_category'].isin(['High', 'Critical'])]
                    for _, finding in high_risk_findings.iterrows():
                        summary['high_risk_findings'].append({
                            'workspace': workspace_alias,
                            'analysis_type': analysis_type,
                            'risk_score': finding['risk_score'],
                            'risk_category': finding['risk_category'],
                            'details': finding.to_dict()
                        })
                    
                    # Aggregate for cross-workspace analysis
                    if analysis_type == 'failed_logons':
                        all_failed_logons.extend(df.to_dict('records'))
                    elif analysis_type == 'suspicious_processes':
                        all_suspicious_processes.extend(df.to_dict('records'))
                    elif analysis_type == 'network_anomalies':
                        all_network_anomalies.extend(df.to_dict('records'))
                    elif analysis_type == 'privilege_escalation':
                        all_privilege_escalations.extend(df.to_dict('records'))
            
            summary['workspace_summaries'][workspace_alias] = workspace_summary
        
        # Cross-workspace pattern analysis
        summary['cross_workspace_patterns'] = self._analyze_cross_workspace_patterns({
            'failed_logons': all_failed_logons,
            'suspicious_processes': all_suspicious_processes,
            'network_anomalies': all_network_anomalies,
            'privilege_escalations': all_privilege_escalations
        })
        
        # Generate recommendations
        summary['recommendations'] = self._generate_recommendations(summary)
        
        return summary
    
    def _analyze_cross_workspace_patterns(self, aggregated_data: Dict) -> Dict[str, Any]:
        """Analyze patterns that span across multiple workspaces."""
        
        patterns = {}
        
        # Analyze failed logons
        if aggregated_data['failed_logons']:
            df = pd.DataFrame(aggregated_data['failed_logons'])
            if 'IpAddress' in df.columns:
                # Find IPs attacking multiple workspaces
                ip_attacks = df.groupby('IpAddress').agg({
                    'FailedAttempts': 'sum',
                    'UniqueAccounts': 'sum'
                }).reset_index()
                
                patterns['cross_workspace_attacks'] = {
                    'total_attacking_ips': len(ip_attacks),
                    'top_attacking_ips': ip_attacks.nlargest(5, 'FailedAttempts').to_dict('records')
                }
        
        # Analyze suspicious processes
        if aggregated_data['suspicious_processes']:
            df = pd.DataFrame(aggregated_data['suspicious_processes'])
            if 'Process' in df.columns and 'Account' in df.columns:
                # Find accounts using suspicious processes across workspaces
                account_processes = df.groupby('Account').agg({
                    'ProcessCount': 'sum',
                    'UniqueCommands': 'sum'
                }).reset_index()
                
                patterns['cross_workspace_suspicious_accounts'] = {
                    'total_suspicious_accounts': len(account_processes),
                    'top_suspicious_accounts': account_processes.nlargest(5, 'ProcessCount').to_dict('records')
                }
        
        return patterns
    
    def _generate_recommendations(self, summary: Dict[str, Any]) -> List[str]:
        """Generate security recommendations based on analysis."""
        
        recommendations = []
        
        # High-level recommendations
        total_high_risk = len([f for f in summary['high_risk_findings'] if f['risk_category'] in ['High', 'Critical']])
        
        if total_high_risk > 0:
            recommendations.append(f"🚨 {total_high_risk} high-risk security findings require immediate investigation")
        
        # Workspace-specific recommendations
        for workspace, workspace_summary in summary['workspace_summaries'].items():
            if workspace_summary['critical_risk_findings'] > 0:
                recommendations.append(f"⚠️ Workspace '{workspace}' has {workspace_summary['critical_risk_findings']} critical risk findings")
        
        # Cross-workspace patterns
        if 'cross_workspace_attacks' in summary['cross_workspace_patterns']:
            attacking_ips = summary['cross_workspace_patterns']['cross_workspace_attacks']['total_attacking_ips']
            if attacking_ips > 0:
                recommendations.append(f"🌐 {attacking_ips} IP addresses are attacking multiple workspaces - consider blocking")
        
        # General recommendations
        if summary['total_records_analyzed'] > 10000:
            recommendations.append("📊 Large volume of security events detected - consider tuning alert thresholds")
        
        if len(summary['high_risk_findings']) == 0:
            recommendations.append("✅ No high-risk findings detected in current analysis period")
        
        return recommendations
    
    async def _upload_analytics_results(self, analytics_summary: Dict[str, Any]):
        """Upload analytics results to Azure Monitor."""
        
        try:
            # Prepare summary record for upload
            upload_data = {
                "TimeGenerated": analytics_summary['analysis_timestamp'],
                "WorkspacesAnalyzed": analytics_summary['workspaces_analyzed'],
                "TotalRecordsAnalyzed": analytics_summary['total_records_analyzed'],
                "HighRiskFindingsCount": len(analytics_summary['high_risk_findings']),
                "CriticalRiskFindingsCount": len([f for f in analytics_summary['high_risk_findings'] if f['risk_category'] == 'Critical']),
                "RecommendationsCount": len(analytics_summary['recommendations']),
                "CrossWorkspaceAttackingIPs": analytics_summary['cross_workspace_patterns'].get('cross_workspace_attacks', {}).get('total_attacking_ips', 0),
                "ReportType": "security_analytics_summary"
            }
            
            # Upload summary
            upload_result = await self.client.upload_logs(
                data=[upload_data],
                stream_name="Custom-SecurityAnalyticsSummary_CL"
            )
            
            if upload_result.succeeded:
                print(f"  ✅ Analytics summary uploaded to SecurityAnalyticsSummary_CL")
            
            # Upload individual high-risk findings
            if analytics_summary['high_risk_findings']:
                findings_data = []
                for finding in analytics_summary['high_risk_findings']:
                    finding_record = {
                        "TimeGenerated": analytics_summary['analysis_timestamp'],
                        "Workspace": finding['workspace'],
                        "AnalysisType": finding['analysis_type'],
                        "RiskScore": finding['risk_score'],
                        "RiskCategory": finding['risk_category'],
                        "FindingDetails": str(finding['details']),
                        "ReportType": "high_risk_finding"
                    }
                    findings_data.append(finding_record)
                
                findings_upload = await self.client.upload_logs(
                    data=findings_data,
                    stream_name="Custom-HighRiskFindings_CL"
                )
                
                if findings_upload.succeeded:
                    print(f"  ✅ {len(findings_data)} high-risk findings uploaded to HighRiskFindings_CL")
        
        except Exception as e:
            print(f"  ⚠️ Failed to upload analytics results: {e}")

async def advanced_analytics_example():
    """Demonstrate advanced security analytics capabilities."""
    
    options = SentinelAggregatorClientOptions.from_environment()
    credential = DefaultAzureCredential()
    
    async with SentinelAggregatorClient(
        dcr_logs_ingestion_endpoint=options.dcr_logs_ingestion_endpoint,
        credential=credential,
        options=options
    ) as client:
        
        # Load workspace configuration
        workspace_manager = WorkspaceManager.from_file("workspaces.yaml")
        
        # Create analytics engine
        analytics_engine = SecurityAnalyticsEngine(client)
        
        # Perform comprehensive analysis
        print(f"🚀 Starting advanced security analytics...")
        
        analytics_summary = await analytics_engine.comprehensive_security_analysis(
            workspace_manager,
            days_back=7
        )
        
        # Display results
        print(f"\n📋 Analytics Summary:")
        print(f"  Workspaces analyzed: {analytics_summary['workspaces_analyzed']}")
        print(f"  Total records analyzed: {analytics_summary['total_records_analyzed']:,}")
        print(f"  High-risk findings: {len(analytics_summary['high_risk_findings'])}")
        
        # Display recommendations
        if analytics_summary['recommendations']:
            print(f"\n💡 Recommendations:")
            for rec in analytics_summary['recommendations']:
                print(f"  {rec}")
        
        # Display top high-risk findings
        if analytics_summary['high_risk_findings']:
            print(f"\n🔥 Top High-Risk Findings:")
            sorted_findings = sorted(
                analytics_summary['high_risk_findings'], 
                key=lambda x: x['risk_score'], 
                reverse=True
            )[:5]
            
            for finding in sorted_findings:
                print(f"  {finding['risk_category']}: {finding['workspace']} - {finding['analysis_type']} (Score: {finding['risk_score']:.1f})")

asyncio.run(advanced_analytics_example())
```

## Example 3: Enterprise automation workflow

Implement a complete enterprise automation workflow with scheduling, monitoring, and alerting.

```python
import asyncio
import schedule
import threading
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from azure.identity.aio import DefaultAzureCredential
from sentinel_log_aggregator import (
    SentinelAggregatorClient,
    SentinelAggregatorClientOptions,
    WorkspaceManager,
    SentinelQueryEngine
)

@dataclass
class WorkflowConfig:
    """Workflow configuration."""
    name: str
    description: str
    schedule: str
    enabled: bool
    workspace_config_file: str
    queries: List[str]
    notification_webhooks: List[str]
    retention_days: int = 30
    max_retries: int = 3
    timeout_minutes: int = 60

@dataclass 
class WorkflowExecution:
    """Workflow execution record."""
    workflow_name: str
    execution_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "running"
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    total_records_processed: int = 0
    error_message: Optional[str] = None
    
class EnterpriseWorkflowOrchestrator:
    """Enterprise-grade workflow orchestration system."""
    
    def __init__(self, config_file: str):
        self.config_file = Path(config_file)
        self.workflows = self._load_workflows()
        self.executions: List[WorkflowExecution] = []
        self.client = None
        self.running = False
        self.scheduler_thread = None
    
    def _load_workflows(self) -> Dict[str, WorkflowConfig]:
        """Load workflow configurations."""
        
        with open(self.config_file, 'r') as f:
            config_data = json.load(f)
        
        workflows = {}
        for workflow_data in config_data.get('workflows', []):
            workflow = WorkflowConfig(**workflow_data)
            workflows[workflow.name] = workflow
        
        return workflows
    
    async def initialize(self):
        """Initialize the orchestrator."""
        
        print(f"🚀 Initializing Enterprise Workflow Orchestrator...")
        
        # Initialize Azure client
        options = SentinelAggregatorClientOptions.from_environment()
        credential = DefaultAzureCredential()
        
        self.client = SentinelAggregatorClient(
            dcr_logs_ingestion_endpoint=options.dcr_logs_ingestion_endpoint,
            credential=credential,
            options=options
        )
        
        print(f"  ✅ Azure client initialized")
        print(f"  📋 Loaded {len(self.workflows)} workflows")
        
        # Validate workflows
        for name, workflow in self.workflows.items():
            if workflow.enabled:
                try:
                    # Validate workspace configuration file exists
                    if not Path(workflow.workspace_config_file).exists():
                        print(f"  ⚠️ Workflow '{name}': workspace config file not found: {workflow.workspace_config_file}")
                        continue
                    
                    # Validate workspace configuration
                    workspace_manager = WorkspaceManager.from_file(workflow.workspace_config_file)
                    errors = workspace_manager.validate_configuration()
                    
                    if errors:
                        print(f"  ⚠️ Workflow '{name}': workspace configuration errors:")
                        for error in errors:
                            print(f"    - {error}")
                    else:
                        print(f"  ✅ Workflow '{name}': configuration valid")
                
                except Exception as e:
                    print(f"  ❌ Workflow '{name}': validation failed: {e}")
    
    def start_scheduler(self):
        """Start the workflow scheduler."""
        
        if self.running:
            print("⚠️ Scheduler is already running")
            return
        
        print(f"⏰ Starting workflow scheduler...")
        
        # Schedule enabled workflows
        for name, workflow in self.workflows.items():
            if workflow.enabled:
                schedule.every().day.at(workflow.schedule).do(
                    lambda w=workflow: asyncio.create_task(self._execute_workflow(w))
                )
                print(f"  📅 Scheduled '{name}' at {workflow.schedule}")
        
        self.running = True
        
        # Start scheduler thread
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        print(f"✅ Workflow scheduler started")
    
    def _run_scheduler(self):
        """Run the scheduling loop."""
        
        while self.running:
            schedule.run_pending()
            threading.Event().wait(60)  # Check every minute
    
    def stop_scheduler(self):
        """Stop the workflow scheduler."""
        
        print(f"🛑 Stopping workflow scheduler...")
        self.running = False
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=10)
        
        schedule.clear()
        print(f"✅ Workflow scheduler stopped")
    
    async def execute_workflow_now(self, workflow_name: str) -> WorkflowExecution:
        """Execute a workflow immediately."""
        
        if workflow_name not in self.workflows:
            raise ValueError(f"Workflow '{workflow_name}' not found")
        
        workflow = self.workflows[workflow_name]
        return await self._execute_workflow(workflow)
    
    async def _execute_workflow(self, workflow: WorkflowConfig) -> WorkflowExecution:
        """Execute a workflow."""
        
        execution_id = f"{workflow.name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        execution = WorkflowExecution(
            workflow_name=workflow.name,
            execution_id=execution_id,
            start_time=datetime.now(timezone.utc)
        )
        
        self.executions.append(execution)
        
        print(f"🔄 Starting workflow execution: {execution_id}")
        
        try:
            # Load workspace configuration
            workspace_manager = WorkspaceManager.from_file(workflow.workspace_config_file)
            
            # Create query engine
            options = SentinelAggregatorClientOptions.from_environment()
            query_engine = SentinelQueryEngine(options, self.client)
            
            # Execute batch queries
            summary = await asyncio.wait_for(
                query_engine.execute_batch_queries_with_streaming_upload(
                    workspaces=workspace_manager.workspaces,
                    query_names=workflow.queries,
                    lookback_period="P7D",
                    batch_time_size="PT24H"
                ),
                timeout=workflow.timeout_minutes * 60
            )
            
            # Update execution status
            execution.end_time = datetime.now(timezone.utc)
            execution.status = "completed"
            execution.total_operations = summary.total_queries
            execution.successful_operations = summary.successful_queries
            execution.failed_operations = summary.failed_queries
            execution.total_records_processed = summary.total_records_processed
            
            print(f"✅ Workflow execution completed: {execution_id}")
            print(f"  📊 Operations: {execution.successful_operations}/{execution.total_operations} successful")
            print(f"  📋 Records processed: {execution.total_records_processed:,}")
            
            # Send success notification
            await self._send_notification(workflow, execution, "success")
            
            # Upload execution summary
            await self._upload_execution_summary(execution)
        
        except asyncio.TimeoutError:
            execution.end_time = datetime.now(timezone.utc)
            execution.status = "timeout"
            execution.error_message = f"Workflow execution timed out after {workflow.timeout_minutes} minutes"
            
            print(f"⏰ Workflow execution timed out: {execution_id}")
            
            # Send timeout notification
            await self._send_notification(workflow, execution, "timeout")
        
        except Exception as e:
            execution.end_time = datetime.now(timezone.utc)
            execution.status = "failed"
            execution.error_message = str(e)
            
            print(f"❌ Workflow execution failed: {execution_id}: {e}")
            
            # Send failure notification
            await self._send_notification(workflow, execution, "failure")
        
        return execution
    
    async def _send_notification(self, workflow: WorkflowConfig, execution: WorkflowExecution, notification_type: str):
        """Send workflow execution notification."""
        
        if not workflow.notification_webhooks:
            return
        
        # Prepare notification payload
        payload = {
            "workflow_name": workflow.name,
            "execution_id": execution.execution_id,
            "status": execution.status,
            "notification_type": notification_type,
            "start_time": execution.start_time.isoformat(),
            "end_time": execution.end_time.isoformat() if execution.end_time else None,
            "duration_minutes": (execution.end_time - execution.start_time).total_seconds() / 60 if execution.end_time else None,
            "total_operations": execution.total_operations,
            "successful_operations": execution.successful_operations,
            "failed_operations": execution.failed_operations,
            "total_records_processed": execution.total_records_processed,
            "error_message": execution.error_message
        }
        
        # Send to all configured webhooks
        for webhook_url in workflow.notification_webhooks:
            try:
                # In a real implementation, you would use aiohttp or similar
                print(f"📧 Sending {notification_type} notification to {webhook_url}")
                print(f"   Payload: {json.dumps(payload, indent=2)}")
                
                # Simulate webhook call
                await asyncio.sleep(0.1)
                print(f"✅ Notification sent successfully")
            
            except Exception as e:
                print(f"❌ Failed to send notification to {webhook_url}: {e}")
    
    async def _upload_execution_summary(self, execution: WorkflowExecution):
        """Upload workflow execution summary."""
        
        try:
            upload_data = {
                "TimeGenerated": execution.start_time.isoformat(),
                "WorkflowName": execution.workflow_name,
                "ExecutionId": execution.execution_id,
                "Status": execution.status,
                "StartTime": execution.start_time.isoformat(),
                "EndTime": execution.end_time.isoformat() if execution.end_time else None,
                "DurationMinutes": (execution.end_time - execution.start_time).total_seconds() / 60 if execution.end_time else None,
                "TotalOperations": execution.total_operations,
                "SuccessfulOperations": execution.successful_operations,
                "FailedOperations": execution.failed_operations,
                "TotalRecordsProcessed": execution.total_records_processed,
                "ErrorMessage": execution.error_message,
                "ReportType": "workflow_execution_summary"
            }
            
            upload_result = await self.client.upload_logs(
                data=[upload_data],
                stream_name="Custom-WorkflowExecutionSummary_CL"
            )
            
            if upload_result.succeeded:
                print(f"  ✅ Execution summary uploaded to WorkflowExecutionSummary_CL")
        
        except Exception as e:
            print(f"  ⚠️ Failed to upload execution summary: {e}")
    
    def get_execution_history(self, workflow_name: Optional[str] = None, days: int = 30) -> List[WorkflowExecution]:
        """Get workflow execution history."""
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        filtered_executions = [
            execution for execution in self.executions
            if execution.start_time >= cutoff_date
            and (workflow_name is None or execution.workflow_name == workflow_name)
        ]
        
        return sorted(filtered_executions, key=lambda x: x.start_time, reverse=True)
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """Get overall workflow system status."""
        
        recent_executions = self.get_execution_history(days=7)
        
        status = {
            "scheduler_running": self.running,
            "total_workflows": len(self.workflows),
            "enabled_workflows": len([w for w in self.workflows.values() if w.enabled]),
            "recent_executions": len(recent_executions),
            "successful_executions": len([e for e in recent_executions if e.status == "completed"]),
            "failed_executions": len([e for e in recent_executions if e.status == "failed"]),
            "timeout_executions": len([e for e in recent_executions if e.status == "timeout"]),
            "last_execution": recent_executions[0].execution_id if recent_executions else None,
            "uptime_hours": None  # Would calculate based on when scheduler started
        }
        
        return status
    
    async def cleanup(self):
        """Cleanup resources."""
        
        print(f"🧹 Cleaning up workflow orchestrator...")
        
        self.stop_scheduler()
        
        if self.client:
            await self.client.close()
        
        print(f"✅ Cleanup completed")

# Example workflow configuration file (workflows.json)
SAMPLE_WORKFLOW_CONFIG = {
    "workflows": [
        {
            "name": "daily_security_summary",
            "description": "Daily security incident and user activity summary",
            "schedule": "02:00",
            "enabled": True,
            "workspace_config_file": "workspaces.yaml",
            "queries": ["query_incident_summary", "query_user_summary"],
            "notification_webhooks": [
                "https://hooks.slack.com/your-slack-webhook",
                "https://your-teams-webhook.office.com"
            ],
            "retention_days": 90,
            "max_retries": 3,
            "timeout_minutes": 60
        },
        {
            "name": "weekly_compliance_report",
            "description": "Weekly compliance and audit report",
            "schedule": "06:00",
            "enabled": True,
            "workspace_config_file": "compliance-workspaces.yaml",
            "queries": ["query_compliance_events", "query_audit_summary"],
            "notification_webhooks": [
                "https://compliance-webhook.company.com"
            ],
            "retention_days": 365,
            "max_retries": 5,
            "timeout_minutes": 120
        },
        {
            "name": "threat_intelligence_update",
            "description": "Threat intelligence and security alerts update",
            "schedule": "14:00",
            "enabled": False,
            "workspace_config_file": "threat-workspaces.yaml",
            "queries": ["query_security_alerts", "query_threat_indicators"],
            "notification_webhooks": [
                "https://security-ops-webhook.company.com"
            ],
            "retention_days": 30,
            "max_retries": 3,
            "timeout_minutes": 45
        }
    ]
}

async def enterprise_workflow_example():
    """Demonstrate enterprise workflow orchestration."""
    
    # Create sample configuration file
    config_file = Path("workflow-config.json")
    with open(config_file, 'w') as f:
        json.dump(SAMPLE_WORKFLOW_CONFIG, f, indent=2)
    
    print(f"📄 Created sample workflow configuration: {config_file}")
    
    # Initialize orchestrator
    orchestrator = EnterpriseWorkflowOrchestrator(config_file)
    
    try:
        await orchestrator.initialize()
        
        # Start scheduler (in real scenario, this would run continuously)
        orchestrator.start_scheduler()
        
        # Execute a workflow immediately for demonstration
        print(f"\n🚀 Executing workflow immediately for demonstration...")
        execution = await orchestrator.execute_workflow_now("daily_security_summary")
        
        # Get workflow status
        status = orchestrator.get_workflow_status()
        print(f"\n📊 Workflow System Status:")
        for key, value in status.items():
            print(f"  {key}: {value}")
        
        # Get execution history
        history = orchestrator.get_execution_history(days=1)
        print(f"\n📋 Recent Executions:")
        for exec in history:
            duration = (exec.end_time - exec.start_time).total_seconds() / 60 if exec.end_time else 0
            print(f"  {exec.execution_id}: {exec.status} ({duration:.1f} min)")
        
        # Simulate running for a short time
        print(f"\n⏳ Simulating scheduler operation (press Ctrl+C to stop)...")
        try:
            await asyncio.sleep(30)  # In real scenario, this would run indefinitely
        except KeyboardInterrupt:
            print(f"\n🛑 Stopping due to user interrupt...")
    
    finally:
        await orchestrator.cleanup()

# Run the example
asyncio.run(enterprise_workflow_example())
```

## Next steps

These advanced examples demonstrate sophisticated usage patterns including:

- **Long-running operations** with comprehensive progress tracking and cancellation
- **Advanced analytics** with threat intelligence integration and risk scoring
- **Enterprise workflows** with scheduling, monitoring, and automated notifications

For production deployments, consider:

- [Best practices](../best-practices.md) - Production deployment guidance
- [Troubleshooting](../troubleshooting.md) - Common issues and solutions
- [API reference](../api-reference.md) - Complete API documentation
- [Performance tuning](../performance-tuning.md) - Optimization guidelines
