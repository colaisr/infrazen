# InfraZen Pricing Implementation Plan

## 🎯 **Vision**
Create intelligent cross-provider price comparison capabilities to identify 20-40% cost savings opportunities by comparing current cloud resources against similar offerings from other providers.

## **Original Simple Plan (6 Steps)**

### **Step 1: Data Structure** 🔄 NEXT
- Create database models for price storage (not simplified)
- `ProviderPrice` table for storing provider-specific pricing
- `PriceHistory` table for tracking price changes over time

### **Step 2: Provider Architecture Extension**
- Extend provider base class with `get_pricing_data()` method
- Can be scheduled daily (initially triggered manually)

### **Step 3: Start with Beget**
- Get pricelist for Beget first (simpler provider with fewer offerings)
- Manually map all Beget products (VPS, hosting, VDS, storage)

### **Step 4: Then Selectel**
- Get pricelist for Selectel
- Extract pricing from existing billing data + official price lists

### **Step 5: UI for Smart Matching**
- Implement UI for smart matching to compare resources
- Provide suggestions based on similarity scoring for first 2 providers

### **Step 6: Admin Page for Provider Management** ✅ COMPLETED
- Admin page to list available providers with "enabled" checkbox
- Each provider has "sync" button to trigger refresh mechanism
- Filter connections page to show only enabled providers

## **Current Status**
- ✅ **Step 6 COMPLETED** - Provider catalog system working
- 🔄 **Ready for Step 1** - Create price storage data structure

## **Key Architecture Decisions**

### **Dual-Layer Storage**
- **SKU-Level Prices**: Store provider-specific product names and prices (e.g., "Beget VPS-S" = 150 RUB/month)
- **Specification-Based Prices**: Normalized resource specifications for cross-provider matching

### **Universal Resource Taxonomy**
- `server` - Virtual machines, VPS, compute instances
- `volume` - Block storage, disks
- `database` - Managed databases (PostgreSQL, MySQL, etc.)
- `storage` - Object storage (S3-compatible)
- `network` - Load balancers, floating IPs
- `kubernetes` - Managed Kubernetes clusters
- `backup` - Backup services
- `other` - Specialized services

### **Similarity Scoring Algorithm**
- **CPU similarity**: 0-30 points (exact match = 30, ±1 core = 25, ±2 cores = 15)
- **RAM similarity**: 0-30 points (exact match = 30, within 25% = 20, within 50% = 10)
- **Storage similarity**: 0-20 points (exact match = 20, within 40% = 15)
- **Region match**: 0-20 points (exact region = 20, same country = 10, different = 0)
- **Total Score**: 0-100
  - 90-100: Excellent match (highlight green)
  - 70-89: Good match (show with confidence)
  - 50-69: Fair match (show with caveats)
  - <50: Poor match (hide by default)

### **Price Collection Methods**
- **Beget**: Manual mapping → Web scraping → HAR file analysis
- **Selectel**: Extract from billing data (100% accurate) + Official price lists
- **Future Providers**: Official APIs + Web scraping + Manual validation

## **Database Schema**

### **Provider Prices Table**
```sql
CREATE TABLE provider_prices (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,              -- 'beget', 'selectel', 'aws', etc.
    resource_type VARCHAR(100) NOT NULL,        -- Universal taxonomy type
    provider_sku VARCHAR(200),                  -- Provider-specific SKU/plan name
    region VARCHAR(50),                         -- Normalized region code
    
    -- Core specifications
    cpu_cores INTEGER,
    ram_gb INTEGER,
    storage_gb INTEGER,
    storage_type VARCHAR(20),                   -- 'SSD', 'HDD', 'NVMe'
    
    -- Extended specifications (JSON for flexibility)
    extended_specs JSONB,
    
    -- Pricing
    hourly_cost DECIMAL(10, 4),
    monthly_cost DECIMAL(10, 2),
    currency VARCHAR(3) DEFAULT 'RUB',
    
    -- Commitment pricing (future)
    yearly_cost DECIMAL(10, 2),
    three_year_cost DECIMAL(10, 2),
    commitment_discount_percent DECIMAL(5, 2),
    
    -- Metadata
    last_updated TIMESTAMP DEFAULT NOW(),
    confidence_score DECIMAL(3, 2),             -- 0.0 to 1.0 data quality
    source VARCHAR(50),                         -- 'billing_api', 'official_price_list', 'scraped', 'manual'
    source_url TEXT,
    notes TEXT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### **Price History Table**
```sql
CREATE TABLE price_history (
    id SERIAL PRIMARY KEY,
    price_id INTEGER REFERENCES provider_prices(id),
    old_monthly_cost DECIMAL(10, 2),
    new_monthly_cost DECIMAL(10, 2),
    change_percent DECIMAL(6, 2),
    change_date TIMESTAMP DEFAULT NOW(),
    change_reason VARCHAR(200),                 -- 'market_adjustment', 'promotion', 'hardware_upgrade'
    created_at TIMESTAMP DEFAULT NOW()
);
```

## **Next Action**
Create `ProviderPrice` and `PriceHistory` database models to start storing pricing data for Beget and Selectel comparison.

## **Implementation Notes**
- Start with Beget due to simpler offerings
- Use manual mapping initially, then automate with scraping
- Focus on core specifications (CPU, RAM, Storage, Region) for Phase 1
- Store both SKU-level and spec-based prices for comprehensive matching
- Track price history for trend analysis and competitive intelligence
