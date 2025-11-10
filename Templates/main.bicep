param workspaceName string
param location string = resourceGroup().location

@minValue(-1)
@maxValue(730)
@description('	The table retention in days, between 4 and 730. Setting this property to -1 will default to the workspace retention.')
param retentionDays int = -1

@minValue(-1)
@maxValue(4383)
@description('The table total retention in days, between 4 and 4383. Setting this property to -1 will default to table retention.')
param totalRetentionDays int = -1

var healthTableName = 'SentinelAggregator_Health_CL'
var healthTableStream = 'Custom-${healthTableName}'

var dataCollectionRuleName = 'DCR-SentinelLogAggregator'

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2021-06-01' existing = {
  name: workspaceName
}

resource healthTable 'Microsoft.OperationalInsights/workspaces/tables@2025-02-01' = {
  parent: logAnalyticsWorkspace
  name: healthTableName
  properties: {
    tableType: 'Custom'
    retentionInDays: retentionDays
    totalRetentionInDays: totalRetentionDays
    schema: {
      columns: [
        {
          name: 'TimeGenerated'
          type: 'datetime'
        }
        {
          name: 'OperationName'
          type: 'string'
        }
        {
          name: 'OperationStatus'
          type: 'string'
        }
        {
          name: 'JobId'
          type: 'string'
        }
        {
          name: 'WorkspaceId'
          type: 'string'
        }
        {
          name: 'QueryName'
          type: 'string'
        }
        {
          name: 'ExtendedProperties'
          type: 'dynamic'
        }
      ]
      name: healthTableName
    }
  }
}

resource dataCollectionRule 'Microsoft.Insights/dataCollectionRules@2023-03-11' = {
  name: dataCollectionRuleName
  dependsOn: [
    healthTable
  ]
  location: location
  kind: 'Direct'
  properties: {
    streamDeclarations: {
      '${healthTableStream}': {
        columns: [
          {
            name: 'TimeGenerated'
            type: 'datetime'
          }
          {
            name: 'OperationName'
            type: 'string'
          }
          {
            name: 'OperationStatus'
            type: 'string'
          }
          {
            name: 'JobId'
            type: 'string'
          }
          {
            name: 'WorkspaceId'
            type: 'string'
          }
          {
            name: 'QueryName'
            type: 'string'
          }
          {
            name: 'ExtendedProperties'
            type: 'dynamic'
          }
        ]
      }
    }
    destinations: {
      logAnalytics: [
        {
          workspaceResourceId: logAnalyticsWorkspace.id
          name: 'workspaceDestination'
        }
      ]
    }
    dataFlows: [
      {
        streams: [
          healthTableName
        ]
        destinations: [
          'workspaceDestination'
        ]
        transformKql: 'source'
        outputStream: healthTableStream
      }
    ]
  }
}

output dcrRuleId string = dataCollectionRule.id
output dcrEndpoint string = dataCollectionRule.properties.immutableId
output healthTableName string = healthTableName
output workspaceId string = logAnalyticsWorkspace.properties.customerId
