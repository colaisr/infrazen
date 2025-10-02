# FinOps Resource Tracking Architecture

## 1. Overview

This document outlines the comprehensive data architecture for InfraZen's multi-cloud FinOps platform, designed to track, analyze, and optimize cloud resources across multiple providers. The architecture follows FinOps best practices and FOCUS specification to enable complete resource visibility, cost optimization, and business-aligned analytics.

## 2. Architecture Principles

### 2.1 Core Design Principles
- **Unified Data Model**: Common properties across all providers with provider-specific extensions
- **Incremental Expansion**: Start with one provider, extend systematically to others
- **Business Context First**: Every resource must be mappable to business units and projects
- **Time-Series Analytics**: Historical data for trend analysis and optimization
- **Flexible Tagging**: Support for custom business context and cost allocation
- **Log Integration**: Deep analysis of resource components and usage patterns

### 2.2 FinOps Alignment
- **FOCUS Compliance**: Align with FinOps Open Cost and Usage Specification
- **Multi-Cloud Support**: Unified view across different cloud providers
- **Cost Allocation**: Flexible mapping of costs to business units
- **Optimization Focus**: Data structure optimized for cost optimization analysis

## 3. Data Model Architecture

### 3.1 Core Resource Model

#### 3.1.1 Universal Resource Properties
All resources share these fundamental attributes:

```sql
-- Core resource registry
CREATE TABLE resources (
    id SERIAL PRIMARY KEY,
    resource_id VARCHAR(100) NOT NULL,           -- Provider's internal ID
    resource_name VARCHAR(255) NOT NULL,         -- Human-readable name
    provider VARCHAR(50) NOT NULL,               -- Cloud provider
    region VARCHAR(100) NOT NULL,                -- Deployment region
    account_id VARCHAR(100) NOT NULL,            -- Billing account
    
    -- Classification
    service_name VARCHAR(100) NOT NULL,         -- Compute, Storage, Database, etc.
    resource_type VARCHAR(100) NOT NULL,        -- VM, Bucket, Database, etc.
    status VARCHAR(50) DEFAULT 'active',        -- Running, Stopped, etc.
    
    -- Financial Information
    pricing_model VARCHAR(50),                   -- On-Demand, Reserved, Spot
    list_price DECIMAL(10,4),                   -- Public retail price
    effective_cost DECIMAL(10,4),               -- Actual cost after discounts
    currency VARCHAR(3) DEFAULT 'RUB',           -- Billing currency
    billing_period VARCHAR(20),                 -- Monthly, hourly, etc.
    
    -- Business Context
    business_unit VARCHAR(100),                 -- Department or unit
    project_id VARCHAR(100),                    -- Project identifier
    feature_tag VARCHAR(100),                   -- Feature or application
    cost_center VARCHAR(100),                   -- Financial cost center
    environment VARCHAR(50),                    -- prod, staging, dev
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_sync TIMESTAMP,                         -- Last provider sync
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Constraints
    UNIQUE(provider, resource_id, resource_type)
);
```

#### 3.1.2 Provider-Specific Extensions

**Yandex Cloud Resources:**
```sql
CREATE TABLE yandex_resources (
    resource_id INTEGER REFERENCES resources(id),
    
    -- Compute specific
    instance_type VARCHAR(100),                  -- Standard, High-Memory, etc.
    cpu_cores INTEGER,                          -- Number of CPU cores
    memory_gb INTEGER,                          -- RAM in gigabytes
    operating_system VARCHAR(100),              -- OS and version
    platform VARCHAR(50),                       -- Intel Ice Lake, etc.
    
    -- Storage specific
    disk_type VARCHAR(50),                      -- network-ssd, network-hdd
    disk_size_gb INTEGER,                       -- Disk size
    storage_class VARCHAR(50),                  -- Standard, Cold, Ice
    
    -- Network specific
    ip_addresses JSON,                          -- Associated IP addresses
    security_groups JSON,                       -- Security group IDs
    
    -- Yandex specific
    folder_id VARCHAR(100),                     -- Yandex folder ID
    cloud_id VARCHAR(100),                      -- Yandex cloud ID
    organization_id VARCHAR(100),               -- Organization ID
    
    PRIMARY KEY (resource_id)
);
```

**Selectel Resources:**
```sql
CREATE TABLE selectel_resources (
    resource_id INTEGER REFERENCES resources(id),
    
    -- Compute specific
    flavor VARCHAR(100),                        -- standard-4-8, memory-8-32
    cpu_cores INTEGER,
    memory_gb INTEGER,
    operating_system VARCHAR(100),
    
    -- Storage specific
    volume_type VARCHAR(50),                    -- ssd, hdd
    volume_size_gb INTEGER,
    
    -- Network specific
    ip_addresses JSON,
    security_groups JSON,
    
    -- Selectel specific
    project_id VARCHAR(100),                    -- Selectel project ID
    datacenter VARCHAR(50),                    -- msk-a, spb-a
    
    PRIMARY KEY (resource_id)
);
```

### 3.2 Usage and Performance Metrics

#### 3.2.1 Time-Series Metrics
```sql
CREATE TABLE resource_metrics (
    id SERIAL PRIMARY KEY,
    resource_id INTEGER REFERENCES resources(id),
    metric_name VARCHAR(100) NOT NULL,          -- cpu_utilization, memory_usage, etc.
    metric_value DECIMAL(10,4) NOT NULL,        -- Metric value
    metric_unit VARCHAR(20),                    -- percent, gb, count, etc.
    timestamp TIMESTAMP NOT NULL,               -- When metric was collected
    provider_metric_id VARCHAR(100),            -- Provider's metric ID
    
    -- Indexing for performance
    INDEX idx_resource_metrics_resource_time (resource_id, timestamp),
    INDEX idx_resource_metrics_name_time (metric_name, timestamp)
);
```

#### 3.2.2 Aggregated Usage Data
```sql
CREATE TABLE resource_usage_summary (
    id SERIAL PRIMARY KEY,
    resource_id INTEGER REFERENCES resources(id),
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    
    -- Compute metrics
    avg_cpu_utilization DECIMAL(5,2),          -- Average CPU usage %
    max_cpu_utilization DECIMAL(5,2),           -- Peak CPU usage %
    avg_memory_usage_gb DECIMAL(10,2),          -- Average memory usage
    max_memory_usage_gb DECIMAL(10,2),          -- Peak memory usage
    uptime_hours DECIMAL(8,2),                  -- Total uptime
    
    -- Storage metrics
    storage_used_gb DECIMAL(10,2),              -- Storage consumption
    io_operations BIGINT,                       -- Total I/O operations
    data_transfer_gb DECIMAL(10,2),             -- Data transfer volume
    
    -- Network metrics
    ingress_traffic_gb DECIMAL(10,2),           -- Incoming data
    egress_traffic_gb DECIMAL(10,2),            -- Outgoing data
    connection_count INTEGER,                   -- Active connections
    
    -- Cost metrics
    total_cost DECIMAL(10,2),                   -- Total cost for period
    cost_per_hour DECIMAL(8,4),                 -- Cost per hour
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(resource_id, period_start, period_end)
);
```

### 3.3 Business Context and Tagging

#### 3.3.1 Flexible Tagging System
```sql
CREATE TABLE resource_tags (
    id SERIAL PRIMARY KEY,
    resource_id INTEGER REFERENCES resources(id),
    tag_key VARCHAR(100) NOT NULL,             -- Tag name
    tag_value VARCHAR(255) NOT NULL,            -- Tag value
    tag_category VARCHAR(50),                    -- business, technical, cost
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),                    -- User who created tag
    
    UNIQUE(resource_id, tag_key)
);

-- Predefined tag categories for business context
CREATE TABLE tag_categories (
    id SERIAL PRIMARY KEY,
    category_name VARCHAR(50) NOT NULL,         -- business, technical, cost
    description TEXT,
    is_required BOOLEAN DEFAULT FALSE,          -- Required for cost allocation
    allowed_values JSON,                        -- Predefined values
    
    UNIQUE(category_name)
);
```

#### 3.3.2 Cost Allocation Rules
```sql
CREATE TABLE cost_allocations (
    id SERIAL PRIMARY KEY,
    resource_id INTEGER REFERENCES resources(id),
    
    -- Allocation rules
    allocation_method VARCHAR(50) NOT NULL,     -- direct, proportional, fixed
    business_unit VARCHAR(100),                 -- Target business unit
    project_id VARCHAR(100),                    -- Target project
    cost_center VARCHAR(100),                  -- Target cost center
    allocation_percentage DECIMAL(5,2),         -- Percentage allocation
    fixed_amount DECIMAL(10,2),                -- Fixed amount allocation
    
    -- Rules
    rule_conditions JSON,                      -- Conditions for allocation
    priority INTEGER DEFAULT 0,                -- Rule priority
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100)
);
```

### 3.4 Operational Logs and Component Analysis

#### 3.4.1 Resource Logs
```sql
CREATE TABLE resource_logs (
    id SERIAL PRIMARY KEY,
    resource_id INTEGER REFERENCES resources(id),
    log_type VARCHAR(50) NOT NULL,              -- application, system, access, error
    log_level VARCHAR(20),                      -- info, warning, error, critical
    log_message TEXT NOT NULL,
    log_source VARCHAR(100),                    -- Source application/service
    timestamp TIMESTAMP NOT NULL,
    metadata JSON,                              -- Additional log metadata
    
    INDEX idx_resource_logs_resource_time (resource_id, timestamp),
    INDEX idx_resource_logs_type_time (log_type, timestamp)
);
```

#### 3.4.2 Component Discovery
```sql
CREATE TABLE resource_components (
    id SERIAL PRIMARY KEY,
    resource_id INTEGER REFERENCES resources(id),
    component_type VARCHAR(100) NOT NULL,      -- software, service, dependency
    component_name VARCHAR(255) NOT NULL,      -- Name of component
    component_version VARCHAR(100),             -- Version information
    component_status VARCHAR(50),               -- running, stopped, installed
    installation_path VARCHAR(500),             -- Installation location
    configuration JSON,                         -- Component configuration
    dependencies JSON,                          -- Component dependencies
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(resource_id, component_type, component_name)
);
```

### 3.5 Analytics and Optimization

#### 3.5.1 Cost Trends and Analysis
```sql
CREATE TABLE cost_trends (
    id SERIAL PRIMARY KEY,
    resource_id INTEGER REFERENCES resources(id),
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    
    -- Cost analysis
    total_cost DECIMAL(10,2) NOT NULL,
    cost_trend VARCHAR(20),                     -- increasing, decreasing, stable
    cost_variance DECIMAL(10,2),               -- Variance from previous period
    cost_efficiency_score DECIMAL(5,2),        -- Efficiency score (0-100)
    
    -- Usage correlation
    usage_cost_ratio DECIMAL(8,4),             -- Cost per usage unit
    utilization_efficiency DECIMAL(5,2),        -- Utilization efficiency %
    
    -- Predictions
    predicted_cost DECIMAL(10,2),              -- Predicted next period cost
    confidence_score DECIMAL(5,2),             -- Prediction confidence
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3.5.2 Optimization Recommendations
```sql
CREATE TABLE optimization_recommendations (
    id SERIAL PRIMARY KEY,
    resource_id INTEGER REFERENCES resources(id),
    
    -- Recommendation details
    recommendation_type VARCHAR(100) NOT NULL,  -- rightsize, cleanup, reserved
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(50),                       -- cost, performance, security
    
    -- Financial impact
    estimated_savings DECIMAL(10,2),            -- Estimated monthly savings
    confidence_score DECIMAL(5,2),              -- Confidence in recommendation
    implementation_effort VARCHAR(20),         -- low, medium, high
    
    -- Implementation
    action_required TEXT,                       -- Steps to implement
    prerequisites JSON,                         -- Prerequisites for implementation
    risks JSON,                                 -- Potential risks
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending',     -- pending, approved, implemented
    priority INTEGER DEFAULT 0,                -- Recommendation priority
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP
);
```

## 4. Implementation Strategy

### 4.1 Phase 1: Foundation (Current State)
- ✅ Basic Beget resource tracking
- ✅ Core connection management
- 🔄 Extend to comprehensive resource discovery
- 🔄 Add usage metrics collection

### 4.2 Phase 2: Multi-Cloud Expansion
- 🔄 Implement unified resource model
- 🔄 Add Yandex Cloud and Selectel synchronization
- 🔄 Implement flexible tagging system
- 🔄 Add cost allocation rules

### 4.3 Phase 3: Advanced Analytics
- 🔄 Time-series metrics collection
- 🔄 Trend analysis and predictions
- 🔄 Log analysis and component discovery
- 🔄 AI-powered optimization recommendations

### 4.4 Phase 4: Enterprise Features
- 🔄 Advanced cost allocation and chargeback
- 🔄 Multi-tenant support
- 🔄 API integrations
- 🔄 Custom reporting and dashboards

## 5. Data Ingestion Strategy

### 5.1 Provider API Integration
- **Scheduled Sync**: Regular synchronization with provider APIs
- **Real-time Updates**: Webhook-based updates for critical changes
- **Incremental Sync**: Only sync changed resources to optimize performance
- **Error Handling**: Robust error handling and retry mechanisms

### 5.2 Data Normalization
- **FOCUS Compliance**: Align with FinOps Open Cost and Usage Specification
- **Currency Normalization**: Convert all costs to primary currency (RUB)
- **Unit Standardization**: Standardize units across providers
- **Data Validation**: Comprehensive data validation and quality checks

### 5.3 Performance Optimization
- **Indexing Strategy**: Optimized database indexes for common queries
- **Data Partitioning**: Partition large tables by time and provider
- **Caching**: Implement caching for frequently accessed data
- **Archival**: Archive old data to maintain performance

## 6. Security and Compliance

### 6.1 Data Security
- **Encryption**: Encrypt sensitive data at rest and in transit
- **Access Control**: Role-based access control for data access
- **Audit Logging**: Comprehensive audit logs for all data access
- **Data Retention**: Configurable data retention policies

### 6.2 Compliance
- **GDPR Compliance**: Support for data privacy requirements
- **Financial Regulations**: Compliance with financial reporting standards
- **Data Sovereignty**: Support for data residency requirements
- **Backup and Recovery**: Comprehensive backup and disaster recovery

## 7. Monitoring and Alerting

### 7.1 System Monitoring
- **Resource Sync Status**: Monitor provider synchronization status
- **Data Quality**: Monitor data quality and completeness
- **Performance Metrics**: Monitor system performance and response times
- **Error Rates**: Monitor and alert on error rates

### 7.2 Business Monitoring
- **Cost Anomalies**: Alert on unusual cost patterns
- **Budget Thresholds**: Alert when approaching budget limits
- **Optimization Opportunities**: Alert on new optimization opportunities
- **Resource Utilization**: Alert on underutilized resources

This architecture provides a comprehensive foundation for InfraZen's FinOps platform, enabling complete resource visibility, cost optimization, and business-aligned analytics across multiple cloud providers.
