"""
Beget provider service
"""
from .client import BegetAPIClient

class BegetService:
    """Beget provider business logic service"""
    
    def __init__(self, provider_id, credentials):
        self.provider_id = provider_id
        self.credentials = credentials
        self.client = BegetAPIClient(
            credentials.get('username'),
            credentials.get('password'),
            credentials.get('api_url', 'https://api.beget.com')
        )
    
    def sync_resources(self):
        """Sync resources from Beget"""
        return self.client.sync_resources()
