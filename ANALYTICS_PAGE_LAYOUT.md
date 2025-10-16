# Analytics Page Layout Design
## Visual Mockup and Component Structure

### 🎨 **Page Layout Structure**

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 📊 Analytics Dashboard                                           📤 Export │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ 💰 Monthly     │ │ 📈 Daily       │ │ 🏢 Resources    │ │ 📊 Providers    │ │
│ │ Spend          │ │ Trend          │ │ Active         │ │ Synced         │ │
│ │ 3,541.83 ₽     │ │ +12.5% ↗️      │ │ 11             │ │ 2              │ │
│ │ (+5.2% vs last)│ │ (vs last week)  │ │ (7 Beget, 4 Sel)│ │ (100% success) │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
│                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│ ┌─────────────────────────────────────┐ ┌─────────────────────────────────────┐ │
│ │ 📈 Spending Trend Analysis          │ │ 🏢 Provider Cost Breakdown          │ │
│ │                                     │ │                                     │ │
│ │ [Interactive Line Chart]            │ │ [Pie Chart]                        │ │
│ │ • 30-day view                      │ │ • Beget: 68.14 ₽ (57.7%)           │ │
│ │ • Trend: +12.5% ↗️                 │ │ • Selectel: 49.92 ₽ (42.3%)        │ │
│ │ • Last sync: 2 hours ago           │ │ • Cost per resource: 10.73 ₽        │ │
│ │                                     │ │                                     │ │
│ │ [7d] [30d] [90d] [Custom]          │ │ [View Details] [Export Data]        │ │
│ └─────────────────────────────────────┘ └─────────────────────────────────────┘ │
│                                                                                 │
│ ┌─────────────────────────────────────┐ ┌─────────────────────────────────────┐ │
│ │ 🔧 Service-Level Cost Analysis     │ │ 💡 Optimization Opportunities       │ │
│ │                                     │ │                                     │ │
│ │ [Horizontal Bar Chart]             │ │ 🎯 Quick Wins                       │ │
│ │ • Compute: 38.73 ₽ (32.8%)         │ │ • 2 idle resources: -15.2 ₽/day    │ │
│ │ • Database: 29.00 ₽ (24.6%)        │ │ • 1 over-provisioned: -8.5 ₽/day   │ │
│ │ • DNS: 0.41 ₽ (0.3%)              │ │ • 3 optimization opportunities     │ │
│ │ • Storage: 0.00 ₽ (0.0%)          │ │                                     │ │
│ │                                     │ │ 📋 All Recommendations             │ │
│ │ [Filter by Provider] [Export]      │ │ [View Full Report] [Export]       │ │
│ └─────────────────────────────────────┘ └─────────────────────────────────────┘ │
│                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│ ┌─────────────────────────────────────────────────────────────────────────────┐ │
│ │ 📤 Export & Actions                                                        │ │
│ │                                                                             │ │
│ │ [📄 PDF Report] [📊 Excel Data] [📈 PowerPoint] [📧 Email Report]          │ │
│ │                                                                             │ │
│ │ Last Export: 2 hours ago | Next Auto-Export: Tomorrow 9:00 AM              │ │
│ └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 🎯 **Component Specifications**

#### **1. Executive Summary Cards (Top Row)**
```css
.kpi-card {
    background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    transition: transform 0.2s ease;
}

.kpi-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}

.kpi-value {
    font-size: 2rem;
    font-weight: 700;
    color: #1e40af;
    margin-bottom: 0.5rem;
}

.kpi-trend {
    font-size: 0.875rem;
    color: #10b981;
    display: flex;
    align-items: center;
    gap: 0.25rem;
}
```

#### **2. Main Analytics Grid (2x2 Layout)**
```css
.analytics-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
    margin: 2rem 0;
}

.chart-container {
    background: white;
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    border: 1px solid #e2e8f0;
}

.chart-header {
    display: flex;
    justify-content: between;
    align-items: center;
    margin-bottom: 1rem;
}

.chart-title {
    font-size: 1.125rem;
    font-weight: 600;
    color: #1f2937;
}

.chart-controls {
    display: flex;
    gap: 0.5rem;
}
```

#### **3. Interactive Chart Components**
```javascript
// Spending Trend Chart
const spendingTrendChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: dates,
        datasets: [{
            label: 'Daily Cost (₽)',
            data: costs,
            borderColor: '#1e40af',
            backgroundColor: 'rgba(30, 64, 175, 0.1)',
            tension: 0.4,
            fill: true
        }]
    },
    options: {
        responsive: true,
        plugins: {
            legend: { display: false },
            tooltip: {
                callbacks: {
                    label: (context) => `${context.parsed.y.toFixed(2)} ₽/день`
                }
            }
        },
        scales: {
            y: {
                beginAtZero: true,
                ticks: {
                    callback: (value) => `${value} ₽`
                }
            }
        }
    }
});

// Provider Breakdown Chart
const providerChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
        labels: ['Beget', 'Selectel'],
        datasets: [{
            data: [68.14, 49.92],
            backgroundColor: ['#1e40af', '#3b82f6'],
            borderWidth: 0
        }]
    },
    options: {
        responsive: true,
        plugins: {
            legend: { position: 'bottom' },
            tooltip: {
                callbacks: {
                    label: (context) => `${context.label}: ${context.parsed} ₽/день`
                }
            }
        }
    }
});
```

#### **4. Export & Actions Footer**
```css
.export-footer {
    background: #f8fafc;
    border-top: 1px solid #e2e8f0;
    padding: 1.5rem;
    margin-top: 2rem;
    border-radius: 0 0 12px 12px;
}

.export-buttons {
    display: flex;
    gap: 1rem;
    margin-bottom: 1rem;
}

.export-button {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1.5rem;
    background: white;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    color: #374151;
    text-decoration: none;
    transition: all 0.2s ease;
}

.export-button:hover {
    background: #f3f4f6;
    border-color: #9ca3af;
}
```

### 📱 **Responsive Design Breakpoints**

#### **Desktop (1200px+)**
- 2x2 grid layout for main charts
- Full-width executive summary
- Side-by-side export options

#### **Tablet (768px - 1199px)**
- 1x2 grid layout for main charts
- Stacked executive summary cards
- Vertical export button layout

#### **Mobile (320px - 767px)**
- Single column layout
- Collapsible chart sections
- Touch-friendly controls
- Simplified export options

### 🎨 **Color Palette & Typography**

#### **Colors**
```css
:root {
    --primary-blue: #1e40af;
    --secondary-blue: #3b82f6;
    --success-green: #10b981;
    --warning-orange: #f59e0b;
    --error-red: #ef4444;
    --neutral-gray: #6b7280;
    --light-gray: #f8fafc;
    --border-gray: #e2e8f0;
    --text-primary: #1f2937;
    --text-secondary: #6b7280;
}
```

#### **Typography**
```css
.chart-title {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 1.125rem;
    font-weight: 600;
    line-height: 1.5;
}

.kpi-value {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 2rem;
    font-weight: 700;
    line-height: 1.2;
}

.body-text {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 0.875rem;
    font-weight: 400;
    line-height: 1.6;
}
```

### 🔧 **Interactive Features**

#### **Chart Interactions**
- **Hover Effects**: Highlight data points with tooltips
- **Click Actions**: Drill down to detailed views
- **Zoom & Pan**: Interactive chart navigation
- **Filter Controls**: Real-time data filtering

#### **Export Functionality**
- **PDF Report**: Executive summary with charts
- **Excel Data**: Raw data with pivot tables
- **PowerPoint**: Presentation-ready slides
- **Email Delivery**: Automated report distribution

#### **Real-time Updates**
- **Auto-refresh**: Update when new sync data available
- **Live Indicators**: Show data freshness
- **Notification System**: Alert for significant changes
- **Progress Tracking**: Show sync status and progress

This layout design provides a comprehensive, professional, and user-friendly analytics dashboard that maximizes FinOps value while maintaining excellent UX/UI principles.
