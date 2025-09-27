# InfraZen FinOps Platform - Comprehensive Design Specification

## Executive Summary

InfraZen is a multi-cloud FinOps platform designed specifically for the Russian market, providing centralized cost control, analytics, and recommendations for cloud expense optimization. This document consolidates all design requirements, visual references, and functional specifications gathered from the pitch deck, dashboard mockups, landing page designs, and cloud connections interface.

## Brand Identity & Visual Design

### Logo & Branding
- **Brand Name:** InfraZen
- **Tagline:** FinOps Platform
- **Logo:** Blue cloud icon with modern typography
- **Primary Message:** "Мультиоблачный FinOps для российского рынка" (Multi-cloud FinOps for the Russian market)

### Color Palette
- **Primary Blue:** #1E40AF (buttons, accents, active states)
- **Secondary Blue:** #3B82F6 (links, secondary elements)
- **Success Green:** #10B981 (positive metrics, active status)
- **Warning Orange:** #F59E0B (alerts, pending states)
- **Error Red:** #EF4444 (delete actions, critical alerts)
- **Background:** #FFFFFF (main content areas)
- **Light Gray:** #F8FAFC (sidebar, card backgrounds)
- **Text Primary:** #1F2937 (headings, primary text)
- **Text Secondary:** #6B7280 (descriptions, metadata)

### Typography
- **Primary Font:** Modern sans-serif (system fonts)
- **Hierarchy:** Clear distinction between headings, body text, and metadata
- **Readability:** High contrast, appropriate sizing for diverse user roles

## Core Value Propositions

### Key Metrics (from Pitch Deck & Landing Page)
- **30-70% потенциальной экономии** (30-70% potential savings)
- **5+ облачных провайдеров** (5+ cloud providers)
- **1 день быстрый запуск** (1 day quick start)

### Problem Statement (Translated)
- Companies do not control the growth of expenses in the cloud
- Multi-cloud environments lack a single point of control
- Insufficient transparency: difficult to link resources to business goals
- No Russian FinOps solution at the level of world leaders
- **Consequences:** Losses of up to 30-70% due to inefficiency, budget overrun risks, lack of control and trust from business

### Solution Features
1. **Centralized cost control**
2. **Analytics and recommendations for decision-making**
3. **Integration with multiple clouds**
4. **Clear reports for both DevOps and CFOs**
5. **Quick start without complex implementation**

## Application Architecture

### Navigation Structure
```
InfraZen FinOps Platform
├── Dashboard (Дашборд) ★ Primary landing page
├── Cloud Connections (Подключения облаков)
├── Resources (Ресурсы)
├── Cost Analytics (Аналитика расходов)
├── Recommendations (Рекомендации)
├── Business Context (Бизнес-контекст)
├── Reports (Отчёты)
└── Settings (Настройки)
```

### Layout Structure
- **Left Sidebar:** Navigation menu with icons and labels
- **Main Content Area:** Dynamic content based on selected module
- **Header:** Module title, subtitle, and action buttons
- **User Profile:** Bottom of sidebar with name, email, and logout

## Detailed Module Specifications

### 1. Dashboard (Дашборд)
**Title:** "Обзор расходов" (Cost Overview)
**Subtitle:** "Мультиоблачная аналитика ваших ресурсов" (Multi-cloud analytics of your resources)

#### Key Widgets
1. **Total Expenses (Общие расходы)**
   - Display: Large monetary value (e.g., "0 ₽")
   - Trend: Percentage change from previous month (e.g., "-12.5% за месяц")
   - Icon: Ruble symbol or currency icon

2. **Potential Savings (Потенциальная экономия)**
   - Display: Monetary value and percentage of total expenses
   - Icon: Savings/optimization icon
   - Color: Green for positive savings

3. **Active Resources (Активные ресурсы)**
   - Display: Number of active resources
   - Subtext: Number of unused resources (e.g., "0 неиспользуемых")
   - Icon: Server/resource icon

4. **Cloud Providers (Облачных провайдеров)**
   - Display: Number of connected services
   - Subtext: "подключенных сервисов" (connected services)
   - Icon: Cloud icon

#### Connected Cloud Providers Section
- **Title:** "Подключенные облачные провайдеры" (Connected Cloud Providers)
- **Provider Cards:** Show GCP, Selectel, etc. with status badges
- **Status Types:** "Подключен" (Connected), "Ожидает синхронизации" (Awaiting synchronization)
- **Add Button:** Prominent "Добавить провайдера" (Add Provider) button

#### Expense Dynamics Chart
- **Title:** "Динамика расходов" (Expense Dynamics)
- **Time Filters:** 30д, 90д, 1г (30 days, 90 days, 1 year)
- **Metrics Display:** 
  - Прошлый месяц (Last month): ₽968,450
  - Текущий месяц (Current month): ₽847,320
  - Экономия (Savings): ₽121,130

#### Resource Usage Section
- **Title:** "Использование ресурсов" (Resource Usage)
- **Progress Bars for:**
  - Процессоры (CPU): 67% (234 vCPU / 350 vCPU)
  - Память (RAM): 81% (1.2 TB / 1.5 TB)
  - Хранилище (Storage): 43% (8.6 TB / 20 TB)
  - Сетевой трафик (Network Traffic): 29% (2.9 TB / 10 TB)

#### Optimization Recommendations
- **Title:** "Рекомендации по оптимизации" (Optimization Recommendations)
- **Empty State:** "Рекомендации не найдены" (Recommendations not found)
- **Message:** "Все ваши ресурсы оптимально настроены" (All your resources are optimally configured)

#### Resource Inventory
- **Title:** "Инвентарь ресурсов" (Resource Inventory)
- **Search Bar:** "Поиск ресурсов..." (Search resources...)
- **Filters:** Все провайдеры, Все типы, Все статусы (All providers, All types, All statuses)
- **Empty State:** "Нет ресурсов" (No resources)

### 2. Cloud Connections (Подключения облаков)
**Title:** "Подключения облаков" (Cloud Connections)
**Subtitle:** "Управление подключениями к облачным провайдерам" (Manage connections to cloud providers)

#### Provider Cards
- **Layout:** Grid of cards showing connected providers
- **Card Elements:**
  - Provider logo and name (GCP, Selectel, etc.)
  - Status badge (Активен/Active, Ожидает синхронизации/Awaiting sync)
  - Connection type
  - Added date (Добавлен: 21.09.2025)
  - Action buttons (Settings gear icon, Delete trash icon)

#### Add Provider Modal
- **Title:** "Подключить облачного провайдера" (Connect Cloud Provider)
- **Subtitle:** "Настройте безопасное подключение к вашему облаку" (Configure secure connection to your cloud)
- **Form Fields:**
  - Provider Selection Dropdown
  - Connection Name (optional)
  - API Key (required)
  - Organization ID (optional)
  - Security checkbox: "Безопасное хранение учетных данных" (Secure storage of credentials)
- **Actions:** Cancel, Connect buttons

### 3. Landing Page Elements
**Hero Section:**
- Main headline with "FinOps" highlighted in blue
- Value proposition subtitle
- Primary CTA: "Начать работу" (Get Started)
- Secondary CTA: "Посмотреть демо" (Watch Demo)

**Feature Grid:**
- Мультиоблачность (Multi-cloud)
- Умная аналитика (Smart Analytics)
- Оптимизация (Optimization)
- Безопасность (Security)
- Быстрый старт (Quick Start)
- Бизнес-контекст (Business Context)

## Technical Implementation Notes

### Flask Application Structure
```
finops-app/
├── app.py                 # Main Flask application
├── templates/
│   ├── base.html         # Base template with sidebar
│   ├── dashboard.html    # Dashboard view
│   ├── connections.html  # Cloud connections view
│   └── landing.html      # Landing page
├── static/
│   ├── css/
│   │   └── style.css     # Main stylesheet
│   ├── js/
│   │   └── app.js        # JavaScript functionality
│   └── images/           # Logo and icons
└── data/
    └── mock_data.py      # Mock data for prototype
```

### Mock Data Requirements
- Cloud provider connections with various statuses
- Cost metrics with historical trends
- Resource utilization data
- Optimization recommendations
- Multi-currency support (Rubles)

### Responsive Design
- Mobile-first approach
- Collapsible sidebar for smaller screens
- Responsive grid layouts for cards and charts
- Touch-friendly interactive elements

## Key Differentiators to Highlight

1. **Multi-cloud out-of-the-box:** Unified dashboard without switching interfaces
2. **Works without tags:** Smart auto-allocation and predictive categorization
3. **Business orientation:** Unit economics and clear CFO reports
4. **Russian market focus:** Local cloud providers (Yandex.Cloud, VK Cloud, Selectel)
5. **Quick implementation:** 1-day connection promise
6. **Transparent budgeting:** Plan-fact analysis and scenario-based forecasts

## Next Steps

1. Set up Flask application foundation
2. Implement base template with sidebar navigation
3. Create dashboard view with mock data
4. Develop cloud connections interface
5. Add interactive elements and data visualization
6. Implement responsive design
7. Deploy prototype for demonstration

This specification serves as the complete blueprint for developing the InfraZen FinOps Platform prototype, ensuring consistency with the established brand identity and user experience expectations.
