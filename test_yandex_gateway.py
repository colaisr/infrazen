#!/usr/bin/env python3
"""
Test Yandex Cloud Billing Gateway API

This script demonstrates how to fetch real billing data from Yandex Cloud
using the internal gateway API that powers the Yandex Console UI.

Requirements:
1. User must be logged into https://center.yandex.cloud in a browser
2. User must extract cookies from browser DevTools
3. Cookies must be provided to this script

How to get cookies:
1. Open https://center.yandex.cloud in Chrome/Firefox
2. Press F12 to open DevTools
3. Go to Application → Cookies → https://center.yandex.cloud
4. Copy values for: Session_id, sessionid2, yandexuid
5. Paste below
"""

import requests
import json
from datetime import datetime, timedelta

# ========================================
# CONFIGURATION
# ========================================

# Billing Account ID (from URL: center.yandex.cloud/billing/accounts/{ACCOUNT_ID}/detail)
BILLING_ACCOUNT_ID = "dn2mqqf5ahht646mov3m"

# Browser cookies (REQUIRED - get from browser DevTools)
COOKIES = {
    'Session_id': '',  # ← PASTE HERE
    'sessionid2': '',  # ← PASTE HERE
    'yandexuid': '',   # ← PASTE HERE
}

# Date range for billing data
today = datetime.now()
START_DATE = (today - timedelta(days=7)).strftime('%Y-%m-%d')
END_DATE = today.strftime('%Y-%m-%d')

# ========================================
# GATEWAY CLIENT
# ========================================

class YandexGatewayClient:
    """Client for Yandex Cloud internal gateway API"""
    
    def __init__(self, cookies):
        self.base_url = 'https://center.yandex.cloud/gateway/root'
        self.cookies = cookies
        self.session = requests.Session()
        self.session.cookies.update(cookies)
    
    def get_service_usage(self, account_id, start_date, end_date, aggregation='day'):
        """
        Get service usage (costs) for a billing account
        
        Args:
            account_id: Billing account ID
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            aggregation: 'day', 'week', or 'month'
        
        Returns:
            Dict with usage report
        """
        url = f'{self.base_url}/billing/getServiceUsage'
        
        payload = {
            'accountId': account_id,
            'startDate': start_date,
            'endDate': end_date,
            'aggregationPeriod': aggregation,
            'labels': {},
            'skuIds': [],
            'cloudIds': [],
            'folderIds': []
        }
        
        response = self.session.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        return response.json()
    
    def get_account(self, account_id):
        """Get billing account details"""
        url = f'{self.base_url}/billing/getAccount'
        
        response = self.session.post(url, json={'accountId': account_id}, timeout=30)
        response.raise_for_status()
        
        return response.json()
    
    def list_billable_entities(self, account_id):
        """List all resources that generate costs"""
        url = f'{self.base_url}/billing/batchListBillableEntities'
        
        response = self.session.post(url, json={'accountId': account_id}, timeout=30)
        response.raise_for_status()
        
        return response.json()

# ========================================
# TEST SCRIPT
# ========================================

def main():
    print("\\n" + "="*80)
    print("🔍 Yandex Cloud Billing Gateway API Test")
    print("="*80 + "\\n")
    
    # Check if cookies are provided
    if not COOKIES['Session_id'] or not COOKIES['sessionid2']:
        print("❌ ERROR: Cookies not provided!")
        print("\\n📝 How to get cookies:")
        print("   1. Open https://center.yandex.cloud in your browser")
        print("   2. Press F12 to open DevTools")
        print("   3. Go to Application → Cookies → https://center.yandex.cloud")
        print("   4. Copy Session_id, sessionid2, yandexuid")
        print("   5. Paste them in this script (COOKIES dict)")
        print("\\n")
        return
    
    # Initialize client
    client = YandexGatewayClient(COOKIES)
    
    # Test 1: Get Account Info
    print("📊 Test 1: Get Billing Account Info")
    print("-" * 80)
    try:
        account = client.get_account(BILLING_ACCOUNT_ID)
        print(f"✅ Account Name: {account.get('account', {}).get('name', 'N/A')}")
        print(f"✅ Account ID: {account.get('account', {}).get('id', 'N/A')}")
        print(f"✅ Currency: {account.get('account', {}).get('currency', 'N/A')}")
        print(f"✅ Balance: {account.get('account', {}).get('balance', 'N/A')}")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("❌ Authentication failed! Cookies may be expired.")
            print("   Please get fresh cookies from your browser.")
            return
        else:
            print(f"❌ Error: {e}")
            return
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    print()
    
    # Test 2: Get Service Usage (Real Costs!)
    print("💰 Test 2: Get Service Usage (Real Billing Data)")
    print("-" * 80)
    print(f"📅 Date Range: {START_DATE} to {END_DATE}")
    print()
    
    try:
        usage = client.get_service_usage(BILLING_ACCOUNT_ID, START_DATE, END_DATE)
        
        report = usage.get('usageReport', {})
        entities = report.get('entitiesData', {})
        
        print(f"📊 Services Found: {len(entities)}")
        print()
        
        total_cost = 0
        
        for entity_id, entity_data in entities.items():
            service_name = entity_data.get('meta', {}).get('description', 'Unknown')
            service_code = entity_data.get('meta', {}).get('name', 'unknown')
            entity_cost = entity_data.get('entityCost', 0)
            entity_credit = entity_data.get('entityCredit', 0)
            entity_expense = entity_data.get('entityExpense', 0)
            
            total_cost += entity_cost
            
            print(f"📦 {service_name} ({service_code})")
            print(f"   Cost:    {entity_cost:.2f} ₽")
            print(f"   Credit:  {entity_credit:.2f} ₽")
            print(f"   Expense: {entity_expense:.2f} ₽")
            
            # Show daily breakdown for last 3 days
            periodic = entity_data.get('periodic', [])
            if periodic:
                print(f"   Daily breakdown (last 3 days):")
                for day in periodic[-3:]:
                    date = day.get('period', 'N/A')
                    cost = day.get('cost', 0)
                    print(f"      {date}: {cost:.2f} ₽")
            print()
        
        print("-" * 80)
        print(f"💵 TOTAL COST: {total_cost:.2f} ₽")
        print(f"💳 TOTAL CREDIT: {report.get('totalCredit', 0):.2f} ₽")
        print(f"💰 TOTAL EXPENSE: {report.get('totalExpense', 0):.2f} ₽")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Test 3: List Billable Entities (Optional)
    print("\\n🔍 Test 3: List Billable Entities")
    print("-" * 80)
    print("(Skipped - uncomment code below to test)")
    
    # Uncomment to test:
    # try:
    #     entities_response = client.list_billable_entities(BILLING_ACCOUNT_ID)
    #     entities_list = entities_response.get('billableEntities', [])
    #     print(f"✅ Found {len(entities_list)} billable entities")
    #     
    #     # Show first 5
    #     for entity in entities_list[:5]:
    #         print(f"   - {entity.get('type', 'unknown')}: {entity.get('id', 'N/A')}")
    # except Exception as e:
    #     print(f"❌ Error: {e}")
    
    print("\\n" + "="*80)
    print("✅ Test Complete!")
    print("="*80 + "\\n")


if __name__ == '__main__':
    main()

