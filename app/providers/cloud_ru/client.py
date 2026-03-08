"""
Cloud.ru API Client
Basic client for Cloud.ru API integration
"""
import hashlib
import hmac
import logging
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from urllib.parse import quote, unquote

logger = logging.getLogger(__name__)


class CloudRuClient:
    """Client for interacting with Cloud.ru API"""
    
    # Base API URLs from Cloud.ru documentation
    IAM_URL = "https://iam.api.cloud.ru/api/v1"
    COMPUTE_URL = "https://compute.api.cloud.ru"  # Compute API for VMs
    BILLING_URL = "https://organization.api.cloud.ru"  # Billing/Consumption API
    BASE_URL = "https://api.cloud.ru"  # Main API
    
    def __init__(self, credentials: Dict[str, Any]):
        """
        Initialize Cloud.ru API client
        
        Args:
            credentials: Dictionary containing:
                - api_key: API key for authentication
                - api_secret: API secret for authentication
                - account_id: Optional account ID
                - agreement_id: Optional agreement ID (contract ID) for billing API
                - project_id: Optional project ID (can be extracted from token or provided)
        """
        self.api_key = credentials.get('api_key')
        self.api_secret = credentials.get('api_secret')
        self.account_id = credentials.get('account_id')
        self.agreement_id = credentials.get('agreement_id')
        self.project_id = credentials.get('project_id')
        self.customer_id = credentials.get('customer_id')  # Extracted from JWT
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Session for connection pooling
        self.session = requests.Session()
        self._access_token = None
        self._token_expires_at = None
        self._last_auth_error = None
        self._setup_session()
    
    def _setup_session(self):
        """Setup HTTP session with authentication headers"""
        # Cloud.ru uses Bearer token authentication
        # Token will be obtained via _get_access_token() when needed
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def _get_access_token(self) -> Optional[str]:
        """
        Get or refresh access token from Cloud.ru IAM API
        
        Returns:
            Access token string or None if failed
        """
        # Check if we have a valid cached token
        if self._access_token and self._token_expires_at:
            if datetime.now() < self._token_expires_at - timedelta(minutes=5):
                return self._access_token
        
        # Exchange keyId/secret for access token
        try:
            token_url = f"{self.IAM_URL}/auth/token"
            response = requests.post(
                token_url,
                json={
                    'keyId': self.api_key,
                    'secret': self.api_secret
                },
                timeout=30,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self._access_token = token_data.get('access_token')
                if not self._access_token:
                    self.logger.error(f"Token response missing access_token: {token_data}")
                    return None
                
                # Extract project_id from JWT token
                try:
                    import base64
                    import json as json_lib
                    parts = self._access_token.split('.')
                    if len(parts) >= 2:
                        payload = parts[1]
                        # Add padding if needed
                        payload += '=' * (4 - len(payload) % 4)
                        decoded = base64.urlsafe_b64decode(payload)
                        token_payload = json_lib.loads(decoded)
                        project_id = token_payload.get('project_id') or token_payload.get('projectId')
                        if project_id:
                            self.project_id = project_id
                            if not self.account_id:
                                self.account_id = project_id
                            self.logger.info(f"Extracted project_id from token: {project_id}")
                        customer_id = token_payload.get('customer_id') or token_payload.get('customerId')
                        if customer_id:
                            self.customer_id = customer_id
                            self.logger.info(f"Extracted customer_id from token: {customer_id}")
                        agreement_id = (token_payload.get('agreement_id') or token_payload.get('agreementId') or
                                        token_payload.get('agreement') or token_payload.get('contract_id'))
                        if agreement_id:
                            self.agreement_id = str(agreement_id)
                            self.logger.info(f"Extracted agreement_id from token: {self.agreement_id}")
                except Exception as e:
                    self.logger.debug(f"Could not extract project_id from token: {e}")
                
                # Token expires in 1 hour (3600 seconds)
                self._token_expires_at = datetime.now() + timedelta(seconds=3600)
                self.logger.info("Successfully obtained Cloud.ru access token")
                return self._access_token
            else:
                # Parse error message for better user feedback
                error_detail = response.text
                user_friendly_message = None
                
                try:
                    error_json = response.json()
                    error_code = error_json.get('code')
                    error_message = error_json.get('message', '')
                    
                    # Cloud.ru error format: {"code": 16, "message": "invalid_client: client not found", "details": []}
                    if error_code == 16 or 'invalid_client' in error_message or 'client not found' in error_message:
                        user_friendly_message = "Invalid Key ID or Key Secret. Please verify your credentials from the Cloud.ru service account access key."
                    elif error_code:
                        user_friendly_message = f"Authentication error (code {error_code}): {error_message}"
                    else:
                        user_friendly_message = error_message or error_detail
                        
                except:
                    user_friendly_message = error_detail
                
                # Store error for test_connection to use
                self._last_auth_error = user_friendly_message
                self.logger.error(f"Failed to get access token: {response.status_code} - {user_friendly_message}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting access token: {str(e)}")
            return None
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to Cloud.ru API
        
        Returns:
            Dictionary with:
                - success: Boolean indicating if connection was successful
                - message: Human-readable message
                - account_info: Account information if available
        """
        try:
            self.logger.info("Testing Cloud.ru API connection...")
            
            # First, get access token - this is the main test
            access_token = self._get_access_token()
            if not access_token:
                # Use detailed error message if available
                error_message = self._last_auth_error or 'Failed to obtain access token. Please check your Key ID and Secret are correct.'
                return {
                    'success': False,
                    'message': error_message,
                    'account_info': {}
                }
            
            # Token obtained successfully - connection is working!
            # For now, we'll return success even without account info endpoint
            # Account info endpoint will be discovered during actual API testing
            self.logger.info("Successfully obtained access token - authentication working")
            
            # Try to get account info if we have a token
            # Set authorization header for future API calls
            self.session.headers['Authorization'] = f'Bearer {access_token}'
            
            # Try common account info endpoints (will fail gracefully if not available)
            account_info = {}
            account_endpoints = [
                f"{self.BASE_URL}/api/v1/account",
                f"{self.BASE_URL}/api/v1/user/info",
                f"{self.BASE_URL}/api/account",
                f"https://api.cloud.ru/v1/account"
            ]
            
            for endpoint in account_endpoints:
                try:
                    response = self.session.get(endpoint, timeout=10)
                    if response.status_code == 200:
                        account_data = response.json()
                        account_info = {
                            'account_id': account_data.get('id') or account_data.get('account_id') or self.account_id or '',
                            'account_name': account_data.get('name') or account_data.get('username') or account_data.get('login') or '',
                            'email': account_data.get('email', ''),
                            'status': account_data.get('status', 'active'),
                            'balance': account_data.get('balance', 0),
                            'currency': account_data.get('currency', 'RUB')
                        }
                        self.logger.info(f"Successfully retrieved account info from {endpoint}")
                        break
                except Exception as e:
                    self.logger.debug(f"Account endpoint {endpoint} not available: {str(e)}")
                    continue
            
            # Try to auto-discover agreement_id (for full contract billing)
            discovered_agreement_id = self.discover_agreement_id()
            if discovered_agreement_id:
                account_info = account_info or {}
                account_info['agreement_id'] = discovered_agreement_id
                self.logger.info(f"Auto-discovered agreement_id during connection test")
            
            # If we got a token, connection is successful even without account info
            if access_token:
                return {
                    'success': True,
                    'message': 'Connection successful - access token obtained',
                    'account_info': account_info if account_info else {
                        'account_id': self.account_id or '',
                        'status': 'authenticated',
                        'note': 'Account details endpoint to be determined'
                    }
                }
                
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'message': 'Could not connect to Cloud.ru API. Please check your internet connection and API endpoint.',
                'account_info': {}
            }
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'message': 'Connection to Cloud.ru API timed out. Please try again.',
                'account_info': {}
            }
        except Exception as e:
            self.logger.error(f"Cloud.ru connection test error: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'Connection test failed: {str(e)}',
                'account_info': {}
            }
    
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """
        Get detailed account information
        
        Returns:
            Account information dictionary or None if failed
        """
        try:
            # Ensure we have a valid token
            access_token = self._get_access_token()
            if not access_token:
                return None
            
            self.session.headers['Authorization'] = f'Bearer {access_token}'
            
            # Try common account info endpoints
            account_endpoints = [
                f"{self.BASE_URL}/api/v1/account",
                f"{self.BASE_URL}/api/v1/user/info",
                f"{self.BASE_URL}/api/account",
                f"https://api.cloud.ru/v1/account"
            ]
            
            for endpoint in account_endpoints:
                try:
                    response = self.session.get(endpoint, timeout=30)
                    if response.status_code == 200:
                        return response.json()
                except:
                    continue
            
            return None
        except Exception as e:
            self.logger.error(f"Failed to get account info: {str(e)}")
            return None
    
    def _extract_agreement_id_from_response(self, data: Any, _depth: int = 0) -> Optional[str]:
        """
        Recursively search for agreement_id in API response (consumption, projects, etc).
        Handles nested dicts, lists, and common field names.
        """
        if _depth > 10:
            return None
        if isinstance(data, dict):
            for key in ('agreement_id', 'agreementId'):
                v = data.get(key)
                if v and isinstance(v, str) and len(v) > 10:
                    return v
            ag = data.get('agreement')
            if isinstance(ag, dict):
                aid = ag.get('id') or ag.get('agreement_id') or ag.get('agreementId')
                if aid:
                    return str(aid)
            for v in data.values():
                found = self._extract_agreement_id_from_response(v, _depth + 1)
                if found:
                    return found
        elif isinstance(data, list):
            for item in data[:50]:  # Limit search
                found = self._extract_agreement_id_from_response(item, _depth + 1)
                if found:
                    return found
        return None

    def discover_agreement_id(self) -> Optional[str]:
        """
        Discover agreement_id via API - no manual input. Tries (in order):
        1. Consumption API with project_ids - extract agreement_id from response (same auth as billing)
        2. JWT token (user tokens may include it; service accounts often do not)
        3. BFF Console API (requires user/session auth; 403 for service accounts)
        4. Organization API (agreements, projects - may return 403 for service accounts)
        """
        if not self._ensure_authenticated():
            return None
        if not self.customer_id:
            self.logger.debug("No customer_id in JWT - attempting project-based discovery")

        # 1. Consumption-first: fetch with project_ids, extract agreement_id from response.
        # Same auth as billing - most reliable path when BFF/org API return 403.
        project_ids = []
        if self.project_id:
            project_ids = [self.project_id]
        elif self.account_id:
            project_ids = [self.account_id]
        else:
            projects = self.get_projects()
            for p in projects:
                pid = (p.get('id') or p.get('project_id') or p.get('projectId')) if isinstance(p, dict) else None
                if pid:
                    project_ids.append(pid)
        if project_ids:
            try:
                from datetime import date, timedelta, datetime, time
                end_day = date.today() - timedelta(days=1)
                start_dt = datetime.combine(end_day, time(0, 0, 0))
                end_dt = datetime.combine(end_day, time(23, 59, 59))
                url = f"{self.BILLING_URL}/v1/consumption"
                params = {
                    'start_date': start_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'end_date': end_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'page_filter.page': 1,
                    'page_filter.limit': 10,
                    'project_ids': project_ids[:1],
                }
                r = self.session.get(url, params=params, timeout=30)
                if r.status_code == 200:
                    data = r.json()
                    aid = self._extract_agreement_id_from_response(data)
                    if aid:
                        self.logger.info(f"Discovered agreement_id via consumption response: {aid}")
                        return aid
            except Exception as e:
                self.logger.debug(f"discover_agreement_id consumption-first: {e}")
        # Try BFF Console: customers/{customer_id}/agreements (when customer_id in JWT)
        if self.customer_id:
            endpoints = [
                f"https://advanced.cloud.ru/u-api/bff-console/v1/customers/{self.customer_id}/agreements",
                f"https://console.cloud.ru/u-api/bff-console/v1/customers/{self.customer_id}/agreements",
            ]
            for url in endpoints:
                try:
                    r = self.session.get(url, timeout=15)
                    if r.status_code == 200:
                        data = r.json()
                        agreements = data if isinstance(data, list) else (data.get('agreements') or data.get('items') or [])
                        if agreements and isinstance(agreements, list):
                            first = agreements[0] if isinstance(agreements[0], dict) else None
                            aid = first.get('id') or first.get('agreement_id') or first.get('agreementId') if first else None
                            if aid:
                                self.logger.info(f"Discovered agreement_id via customers/agreements: {aid}")
                                return aid
                except Exception as e:
                    self.logger.debug(f"discover_agreement_id {url}: {e}")
        # Try BFF: simple-projects - may include agreement_id per project (works with customer_id)
        if self.customer_id:
            for base in ["https://advanced.cloud.ru", "https://console.cloud.ru"]:
                try:
                    url = f"{base}/u-api/bff-console/v1/simple-projects?customerId={self.customer_id}"
                    r = self.session.get(url, timeout=15)
                    if r.status_code == 200:
                        data = r.json()
                        projects = data if isinstance(data, list) else (data.get('projects') or data.get('items') or [])
                        if projects and isinstance(projects, list):
                            for p in projects:
                                if isinstance(p, dict):
                                    aid = p.get('agreement_id') or p.get('agreementId') or p.get('agreement', {}).get('id') if isinstance(p.get('agreement'), dict) else None
                                    if aid:
                                        self.logger.info(f"Discovered agreement_id via simple-projects: {aid}")
                                        return aid
                except Exception as e:
                    self.logger.debug(f"discover_agreement_id simple-projects: {e}")
        # Try BFF: project/{project_id} - may return agreement for the project
        if self.project_id:
            for base in ["https://advanced.cloud.ru", "https://console.cloud.ru"]:
                try:
                    url = f"{base}/u-api/bff-console/v1/project/{self.project_id}"
                    r = self.session.get(url, timeout=15)
                    if r.status_code == 200:
                        data = r.json()
                        if isinstance(data, dict):
                            aid = data.get('agreement_id') or data.get('agreementId') or (data.get('agreement', {}).get('id') if isinstance(data.get('agreement'), dict) else None)
                            if aid:
                                self.logger.info(f"Discovered agreement_id via project/{self.project_id}: {aid}")
                                return aid
                except Exception as e:
                    self.logger.debug(f"discover_agreement_id project: {e}")
        # Try organization API: agreements/projects endpoints (same auth as consumption)
        for path in ["/v1/agreements", "/v1/customers/agreements", "/v1/me", "/v1/me/agreements"]:
            try:
                url = f"{self.BILLING_URL}{path}"
                r = self.session.get(url, timeout=15)
                if r.status_code == 200:
                    data = r.json()
                    agreements = data if isinstance(data, list) else (data.get('agreements') or data.get('items') or [])
                    if agreements and isinstance(agreements, list):
                        first = agreements[0] if isinstance(agreements[0], dict) else None
                        aid = first.get('id') or first.get('agreement_id') or first.get('agreementId') if first else None
                        if aid:
                            self.logger.info(f"Discovered agreement_id via organization API {path}: {aid}")
                            return aid
                    if isinstance(data, dict):
                        aid = data.get('agreement_id') or data.get('agreementId') or data.get('agreement')
                        if aid:
                            self.logger.info(f"Discovered agreement_id via organization API {path}: {aid}")
                            return str(aid) if not isinstance(aid, dict) else aid.get('id') or aid.get('agreement_id')
            except Exception as e:
                self.logger.debug(f"discover_agreement_id org API {path}: {e}")
        # Try organization API: projects list (may include agreement_id per project)
        try:
            url = f"{self.BILLING_URL}/v1/projects"
            r = self.session.get(url, timeout=15)
            if r.status_code == 200:
                data = r.json()
                aid = self._extract_agreement_id_from_response(data)
                if aid:
                    self.logger.info(f"Discovered agreement_id via organization API /v1/projects: {aid}")
                    return aid
        except Exception as e:
            self.logger.debug(f"discover_agreement_id org API /v1/projects: {e}")
        # Try organization API: project detail (may include agreement_id)
        if self.project_id:
            for path in [f"/v1/projects/{self.project_id}", f"/v1/project/{self.project_id}"]:
                try:
                    url = f"{self.BILLING_URL}{path}"
                    r = self.session.get(url, timeout=15)
                    if r.status_code == 200:
                        data = r.json()
                        if isinstance(data, dict):
                            aid = data.get('agreement_id') or data.get('agreementId') or (data.get('agreement', {}).get('id') if isinstance(data.get('agreement'), dict) else None)
                            if aid:
                                self.logger.info(f"Discovered agreement_id via project/{self.project_id}: {aid}")
                                return aid
                except Exception as e:
                    self.logger.debug(f"discover_agreement_id project API: {e}")
        return None
    
    def _ensure_authenticated(self) -> bool:
        """Ensure we have a valid access token"""
        access_token = self._get_access_token()
        if access_token:
            self.session.headers['Authorization'] = f'Bearer {access_token}'
            return True
        return False
    
    def get_projects(self) -> List[Dict[str, Any]]:
        """
        Get list of projects from Cloud.ru API
        
        Returns:
            List of project dictionaries with project IDs
        """
        if not self._ensure_authenticated():
            self.logger.error("Cannot get projects: authentication failed")
            return []
        
        try:
            # BFF Console: simple-projects by customer_id (from JWT token)
            if self.customer_id:
                bff_url = f"https://advanced.cloud.ru/u-api/bff-console/v1/simple-projects?customerId={self.customer_id}"
                try:
                    self.logger.info(f"Trying BFF simple-projects: {bff_url}")
                    response = self.session.get(bff_url, timeout=30)
                    if response.status_code == 200:
                        data = response.json()
                        projects = data if isinstance(data, list) else (data.get('projects') or data.get('items') or data.get('data', []))
                        if projects and isinstance(projects, list):
                            out = []
                            for p in projects:
                                pid = (p.get('id') or p.get('project_id') or p.get('projectId')) if isinstance(p, dict) else str(p)
                                if pid:
                                    out.append({'id': pid, 'project_id': pid})
                            if out:
                                self.logger.info(f"Found {len(out)} project(s) via BFF simple-projects")
                                return out
                except Exception as e:
                    self.logger.debug(f"BFF simple-projects failed: {e}")

            # Fallback: generic project endpoints
            endpoints = [
                f"{self.BASE_URL}/api/v1/projects",
                f"{self.BASE_URL}/v1/projects",
                f"https://resource-manager.api.cloud.ru/api/v1/projects",
                f"https://resource-manager.api.cloud.ru/v1/projects",
                f"https://billing.api.cloud.ru/api/v1/projects",
                f"https://billing.api.cloud.ru/v1/projects",
            ]
            for endpoint in endpoints:
                try:
                    self.logger.info(f"Trying projects endpoint: {endpoint}")
                    response = self.session.get(endpoint, timeout=30)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if isinstance(data, list):
                            self.logger.info(f"Found {len(data)} projects")
                            return data
                        elif isinstance(data, dict):
                            projects = data.get('projects') or data.get('items') or data.get('data', [])
                            if projects:
                                self.logger.info(f"Found {len(projects)} projects")
                                return projects if isinstance(projects, list) else []
                        return []
                    elif response.status_code == 404:
                        continue
                except Exception as e:
                    self.logger.debug(f"Projects endpoint {endpoint} failed: {str(e)}")
                    continue
            
            # Try to extract project ID from token or account info
            # Check if account_id in credentials can be used as project_id
            if self.account_id:
                self.logger.info(f"Using account_id as project_id: {self.account_id}")
                return [{'id': self.account_id, 'project_id': self.account_id}]
            
            self.logger.warning("No working projects endpoint found")
            return []
        except Exception as e:
            self.logger.error(f"Failed to get projects: {str(e)}")
            return []
    
    def get_vms(self, project_id: str = None) -> List[Dict[str, Any]]:
        """
        Get list of virtual machines from Cloud.ru Compute API
        
        Args:
            project_id: Optional project ID. If not provided, will try to discover projects first.
        
        Returns:
            List of VM dictionaries
        """
        if not self._ensure_authenticated():
            self.logger.error("Cannot get VMs: authentication failed")
            return []
        
        try:
            # If no project_id provided, try to get it from token or projects
            project_ids = []
            if project_id:
                project_ids = [project_id]
            else:
                # First try to use project_id from token (extracted during authentication)
                if self.account_id:
                    self.logger.info(f"Using project_id from token/account: {self.account_id}")
                    project_ids = [self.account_id]
                else:
                    # Try to discover projects via API
                    projects = self.get_projects()
                    if projects:
                        # Extract project IDs
                        for project in projects:
                            pid = project.get('id') or project.get('project_id') or project.get('projectId')
                            if pid:
                                project_ids.append(pid)
                        self.logger.info(f"Found {len(project_ids)} project(s) via API")
                    else:
                        self.logger.warning("Could not discover projects")
            
            if not project_ids:
                self.logger.warning("No project_id available - cannot query VMs")
                return []
            
            all_vms = []
            
            # Try the endpoint that requires project_id
            endpoint = f"{self.COMPUTE_URL}/api/v1/vms"
            
            for pid in project_ids:
                try:
                    params = {}
                    if pid:
                        params['project_id'] = pid
                        self.logger.info(f"Querying VMs for project_id: {pid}")
                    else:
                        self.logger.info("Querying VMs without project_id")
                    
                    response = self.session.get(endpoint, params=params, timeout=30)
                    self.logger.info(f"Response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        self.logger.info(f"Response data type: {type(data)}")
                        
                        # Handle different response formats
                        if isinstance(data, list):
                            self.logger.info(f"Found {len(data)} VMs in list response")
                            all_vms.extend(data)
                        elif isinstance(data, dict):
                            # Try common keys for VM lists
                            vms = data.get('instances') or data.get('servers') or data.get('vms') or data.get('items') or data.get('data', [])
                            if vms and isinstance(vms, list):
                                self.logger.info(f"Found {len(vms)} VMs in dict response")
                                all_vms.extend(vms)
                            elif vms:
                                all_vms.append(vms)
                            else:
                                self.logger.warning(f"200 response but no VMs found. Response keys: {list(data.keys())}")
                    elif response.status_code == 422:
                        error_data = response.json()
                        self.logger.debug(f"422 response: {error_data}")
                        # If it's a missing project_id error, continue to next project
                        continue
                    else:
                        self.logger.debug(f"Response {response.status_code}: {response.text[:200]}")
                except Exception as e:
                    self.logger.debug(f"Error querying VMs for project {pid}: {str(e)}")
                    continue
            
            self.logger.info(f"Total VMs found across all projects: {len(all_vms)}")
            return all_vms
            
        except Exception as e:
            self.logger.error(f"Failed to get VMs: {str(e)}", exc_info=True)
            return []
    
    def get_volumes(self) -> List[Dict[str, Any]]:
        """
        Get list of storage volumes
        
        Returns:
            List of volume dictionaries
        """
        if not self._ensure_authenticated():
            self.logger.error("Cannot get volumes: authentication failed")
            return []
        
        try:
            # TODO: Replace with actual Cloud.ru API endpoint
            endpoints = [
                f"{self.BASE_URL}/api/v1/storage/volumes",
                f"{self.BASE_URL}/api/v1/volumes",
                f"https://api.cloud.ru/v1/storage/volumes"
            ]
            
            for endpoint in endpoints:
                try:
                    response = self.session.get(endpoint, timeout=30)
                    if response.status_code == 200:
                        data = response.json()
                        if isinstance(data, list):
                            return data
                        elif isinstance(data, dict):
                            return data.get('volumes', [])
                        return []
                except Exception as e:
                    self.logger.debug(f"Volume endpoint {endpoint} failed: {str(e)}")
                    continue
            
            self.logger.warning("No working volume endpoint found - returning empty list")
            return []
        except Exception as e:
            self.logger.error(f"Failed to get volumes: {str(e)}")
            return []
    
    def get_disk_to_vm_mapping(self) -> Dict[str, Dict[str, str]]:
        """
        Build disk_id -> {vm_id, vm_name} mapping from Compute API.
        VM detail (GET /api/v1/vms/{vm_id}) includes disks[] with disk id.
        Used for volume-to-server grouping instead of name heuristics.
        
        Returns:
            Dict mapping disk_id (str) -> {vm_id, vm_name}
        """
        result: Dict[str, Dict[str, str]] = {}
        if not self._ensure_authenticated():
            self.logger.warning("Cannot get disk mapping: authentication failed")
            return result
        
        project_ids = []
        if self.project_id:
            project_ids = [self.project_id]
        else:
            projects = self.get_projects()
            for p in projects:
                pid = (p.get('id') or p.get('project_id') or p.get('projectId')) if isinstance(p, dict) else None
                if pid:
                    project_ids.append(pid)
        
        if not project_ids:
            self.logger.warning("No project_id for disk mapping")
            return result
        
        for project_id in project_ids:
            try:
                vms_url = f"{self.COMPUTE_URL}/api/v1/vms"
                r = self.session.get(vms_url, params={'project_id': project_id}, timeout=30)
                if r.status_code != 200:
                    self.logger.debug(f"VMs list returned {r.status_code} for project {project_id}")
                    continue
                data = r.json()
                vms = data if isinstance(data, list) else (
                    data.get('vms') or data.get('instances') or data.get('items') or []
                )
                if not isinstance(vms, list):
                    continue
                for vm in vms:
                    vm_id = vm.get('id') if isinstance(vm, dict) else None
                    vm_name = (vm.get('name') or '').strip() if isinstance(vm, dict) else ''
                    if not vm_id:
                        continue
                    try:
                        detail_url = f"{self.COMPUTE_URL}/api/v1/vms/{vm_id}"
                        dr = self.session.get(detail_url, params={'project_id': project_id}, timeout=15)
                        if dr.status_code != 200:
                            continue
                        vd = dr.json()
                        disks = vd.get('disks') if isinstance(vd, dict) else []
                        if not isinstance(disks, list):
                            continue
                        for d in disks:
                            disk_id = d.get('id') if isinstance(d, dict) else None
                            if disk_id:
                                result[disk_id] = {'vm_id': vm_id, 'vm_name': vm_name}
                    except Exception as e:
                        self.logger.debug(f"VM detail for {vm_id}: {e}")
                        continue
            except Exception as e:
                self.logger.warning(f"Disk mapping for project {project_id}: {e}")
        
        self.logger.info(f"Disk-to-VM mapping: {len(result)} disks from Compute API")
        return result
    
    def get_networks(self) -> List[Dict[str, Any]]:
        """
        Get list of networks
        
        Returns:
            List of network dictionaries
        """
        if not self._ensure_authenticated():
            self.logger.error("Cannot get networks: authentication failed")
            return []
        
        try:
            # TODO: Replace with actual Cloud.ru API endpoint
            endpoints = [
                f"{self.BASE_URL}/api/v1/networks",
                f"{self.BASE_URL}/api/v1/vpc/networks",
                f"https://api.cloud.ru/v1/networks"
            ]
            
            for endpoint in endpoints:
                try:
                    response = self.session.get(endpoint, timeout=30)
                    if response.status_code == 200:
                        data = response.json()
                        if isinstance(data, list):
                            return data
                        elif isinstance(data, dict):
                            return data.get('networks', [])
                        return []
                except Exception as e:
                    self.logger.debug(f"Network endpoint {endpoint} failed: {str(e)}")
                    continue
            
            self.logger.warning("No working network endpoint found - returning empty list")
            return []
        except Exception as e:
            self.logger.error(f"Failed to get networks: {str(e)}")
            return []
    
    def get_billing_data(self, days: int = 30) -> Dict[str, Any]:
        """
        Get billing/cost data
        
        Args:
            days: Number of days to fetch billing data for
            
        Returns:
            Dictionary containing billing information
        """
        if not self._ensure_authenticated():
            self.logger.error("Cannot get billing data: authentication failed")
            return {}
        
        try:
            # Ensure we're authenticated and project_id is set
            # project_id is extracted from JWT token during authentication
            if not self._ensure_authenticated():
                self.logger.error("Cannot get billing data: authentication failed")
                return {}
            
            # After authentication, project_id should be set (from JWT token)
            # If not, try to get token again, then discover projects via API
            if not self.project_id:
                self.logger.warning("project_id not set after authentication, trying to get token again...")
                self._get_access_token()
                if not self.project_id:
                    # Try to discover projects via API (ideal: get all projects and query automatically)
                    projects = self.get_projects()
                    if projects:
                        pids = []
                        for p in projects:
                            pid = p.get('id') or p.get('project_id') or p.get('projectId')
                            if pid:
                                pids.append(pid)
                        if pids:
                            self.project_id = pids[0]  # Use first for primary; we'll query all below
                            self.logger.info(f"Discovered {len(pids)} project(s) via API, using for billing")
                    if not self.project_id:
                        self.logger.error("Failed to extract project_id from token or discover projects")
                        return {}
            
            # Cloud.ru billing API endpoint
            # Based on docs: https://cloud.ru/docs/billing/ug/topics/api-ref
            # Endpoint: GET /v1/consumption
            # Base URL: https://organization.api.cloud.ru
            from datetime import datetime, timedelta, date, time
            
            endpoint = f"{self.BILLING_URL}/v1/consumption"
            
            # Use calendar-day boundaries (not rolling 24h) to match console totals.
            # Rolling window (now - 1 day to now) spans 2 calendar days and inflates cost.
            # Console uses single day: 2026-02-15 00:00 - 23:59 -> 140,233 ₽
            end_day = date.today() - timedelta(days=1)  # Yesterday (most recent complete day)
            start_day = end_day - timedelta(days=days - 1)
            start_date = datetime.combine(start_day, time(0, 0, 0))
            end_date = datetime.combine(end_day, time(23, 59, 59))
            
            # Format dates as ISO 8601 (required by API)
            params = {
                'start_date': start_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'end_date': end_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'page_filter.page': 1,  # Page number (required, must be >= 1)
                'page_filter.limit': 10000  # Max recommended limit
            }
            
            # Prefer agreement_id for full contract view (all projects, matches console "Проекты: Все")
            # Try to discover agreement_id automatically if not set
            agreement_id = self.agreement_id
            if not agreement_id:
                agreement_id = self.discover_agreement_id()
                if agreement_id:
                    self.agreement_id = agreement_id  # Cache for subsequent calls
            if agreement_id:
                params['agreement_id'] = agreement_id
                self.logger.info(f"Using agreement_id {agreement_id} for billing API (full contract)")
            else:
                project_ids = []
                if self.project_id:
                    project_ids = [self.project_id]
                else:
                    projects = self.get_projects()
                    for p in projects:
                        pid = p.get('id') or p.get('project_id') or p.get('projectId')
                        if pid:
                            project_ids.append(pid)
                if project_ids:
                    params['project_ids'] = project_ids
                    self.logger.info(f"Using {len(project_ids)} project(s) for billing API")
                else:
                    self.logger.warning("No agreement_id or project_ids available for billing API")
            
            try:
                self.logger.info(f"Fetching billing data from {endpoint} for {days} days")
                self.logger.info(f"Request params: {params}")
                
                response = self.session.get(endpoint, params=params, timeout=60)
                
                # Log the actual request URL for debugging
                if hasattr(response, 'request') and hasattr(response.request, 'url'):
                    self.logger.info(f"Actual request URL: {response.request.url[:400]}")
                
                self.logger.info(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    consumptions = data.get('consumptions', [])
                    self.logger.info(f"Successfully fetched billing data: {len(consumptions)} consumption records")
                    if len(consumptions) == 0:
                        self.logger.warning("Billing API returned 200 but with 0 consumption records")
                        self.logger.warning(f"Response data keys: {list(data.keys())}")
                        import json as json_lib
                        self.logger.debug(f"Full response: {json_lib.dumps(data, indent=2)[:1000]}")
                    
                    # If we used project_ids and got data, extract agreement_id from response and retry for full contract
                    if not params.get('agreement_id') and consumptions:
                        aid = self._extract_agreement_id_from_response(data)
                        if aid:
                            self.agreement_id = aid
                            self.logger.info(f"Extracted agreement_id from consumption response: {aid}")
                            retry_params = {
                                'start_date': params['start_date'],
                                'end_date': params['end_date'],
                                'page_filter.page': 1,
                                'page_filter.limit': params.get('page_filter.limit', 10000),
                                'agreement_id': aid
                            }
                            self.logger.info(f"Retrying with agreement_id for full contract view")
                            r2 = self.session.get(endpoint, params=retry_params, timeout=60)
                            if r2.status_code == 200:
                                data = r2.json()
                                consumptions = data.get('consumptions', [])
                                self.logger.info(f"Full contract: {len(consumptions)} consumption records")
                                return data
                        else:
                            self.logger.info("No agreement_id in consumption response - using project-scoped data. First record keys: %s",
                                            list(consumptions[0].keys())[:15] if consumptions else [])
                    
                    return data
                elif response.status_code == 401:
                    error_text = response.text[:500]
                    self.logger.error(f"Authentication failed for billing API - check token. Error: {error_text}")
                    return {}
                elif response.status_code == 403:
                    error_text = response.text[:500]
                    self.logger.error(f"Access forbidden for billing API - check service account permissions. Error: {error_text}")
                    self.logger.error(f"Request was: {response.request.url[:400] if hasattr(response, 'request') else 'unknown'}")
                    return {}
                elif response.status_code == 400:
                    # Log full error for debugging
                    error_text = response.text[:500]
                    self.logger.warning(f"Billing API returned status 400: {error_text}")
                    # Check if it's the "must provide" error
                    if "Either agreement_id or project_ids must be provided" in error_text:
                        self.logger.warning(f"API didn't receive agreement_id/project_ids. Request params were: {params}")
                        self.logger.warning(f"Request URL was: {response.url[:400] if hasattr(response, 'url') else 'unknown'}")
                    return {}
                else:
                    error_text = response.text[:500]
                    self.logger.warning(f"Billing API returned status {response.status_code}: {error_text}")
                    return {}
            except Exception as e:
                self.logger.error(f"Failed to get billing data from {endpoint}: {str(e)}")
                return {}
        except Exception as e:
            self.logger.error(f"Failed to get billing data: {str(e)}")
            return {}
    
    def get_account_billing(self) -> Dict[str, Any]:
        """
        Get account-level billing summary
        
        Returns:
            Dictionary containing account billing summary
        """
        if not self._ensure_authenticated():
            self.logger.error("Cannot get account billing: authentication failed")
            return {}
        
        try:
            # Try to get account info which might include billing
            account_info = self.get_account_info()
            if account_info:
                return {
                    'balance': account_info.get('balance', 0),
                    'currency': account_info.get('currency', 'RUB'),
                    'status': account_info.get('status', 'unknown')
                }
            
            # Try dedicated billing endpoints
            endpoints = [
                f"{self.BASE_URL}/api/v1/billing/account",
                f"{self.BASE_URL}/api/v1/account/billing",
                f"https://api.cloud.ru/v1/billing/account"
            ]
            
            for endpoint in endpoints:
                try:
                    response = self.session.get(endpoint, timeout=30)
                    if response.status_code == 200:
                        return response.json()
                except Exception as e:
                    self.logger.debug(f"Account billing endpoint {endpoint} failed: {str(e)}")
                    continue
            
            # Return minimal structure if no endpoint works
            return {
                'balance': 0,
                'currency': 'RUB',
                'status': 'unknown',
                'note': 'Billing endpoint to be determined'
            }
        except Exception as e:
            self.logger.error(f"Failed to get account billing: {str(e)}")
            return {}


class CloudRuAdvancedClient:
    """
    Client for Cloud.ru Advanced (Huawei-based) APIs.
    Uses AK/SK HMAC-SHA256 request signing.
    Each instance is scoped to a single tenant/project.
    """

    REGION = "ru-moscow-1"

    # Service endpoint templates
    _SERVICE_HOSTS = {
        'ecs': 'ecs.{region}.hc.sbercloud.ru',
        'evs': 'evs.{region}.hc.sbercloud.ru',
        'cce': 'cce.{region}.hc.sbercloud.ru',
        'vpc': 'vpc.{region}.hc.sbercloud.ru',
        'elb': 'elb.{region}.hc.sbercloud.ru',
        'rds': 'rds.{region}.hc.sbercloud.ru',
        'ces': 'ces.{region}.hc.sbercloud.ru',
        'sfs-turbo': 'sfs-turbo.{region}.hc.sbercloud.ru',
    }

    # CES namespace → dimension key for each resource type
    _CES_NAMESPACES = {
        'ecs': ('SYS.ECS', 'instance_id'),
        'evs': ('SYS.EVS', 'disk_name'),
        'efs': ('SYS.EFS', 'efs_instance_id'),
        'elb': ('SYS.ELB', 'lbaas_instance_id'),
        'rds': ('SYS.RDS', 'postgresql_cluster_id'),
        'cbr': ('SYS.CBR', 'instance_id'),
        'obs': ('SYS.OBS', 'bucket_name'),
        'nat': ('SYS.NAT', 'nat_gateway_id'),
        'vpc': ('SYS.VPC', 'publicip_id'),
        'sfs': ('SYS.SFS', 'share_id'),
    }

    # Key FinOps metrics per namespace — kept minimal for batch efficiency.
    # With 10 queries per batch call: fewer metrics = fewer API calls.
    _CES_FINOPS_METRICS = {
        'SYS.ECS': ['cpu_util',
                     'network_incoming_bytes_aggregate_rate',
                     'network_outgoing_bytes_aggregate_rate'],
        'SYS.EFS': ['used_capacity', 'used_capacity_percent', 'iops'],
        'SYS.ELB': ['m2_act_conn', 'm22_in_bandwidth', 'm23_out_bandwidth'],
        'SYS.RDS': ['rds001_cpu_util', 'rds002_mem_util', 'rds039_disk_util'],
        'SYS.CBR': ['vault_util', 'used_vault_size'],
        'SYS.OBS': ['capacity_total'],
        'SYS.NAT': ['snat_connection', 'inbound_bandwidth', 'outbound_bandwidth'],
        'SYS.VPC': ['upstream_bandwidth', 'downstream_bandwidth'],
    }

    def __init__(self, ak: str, sk: str, region: str = "ru-moscow-1"):
        self.ak = ak
        self.sk = sk
        self.region = region
        self.logger = logging.getLogger(f"{__name__}.CloudRuAdvancedClient")

    # ------------------------------------------------------------------
    # AK/SK signing (Huawei Cloud SDK-HMAC-SHA256 algorithm)
    # ------------------------------------------------------------------

    @staticmethod
    def _canonical_uri(raw_path: str) -> str:
        """Encode URI path per Huawei Cloud canonical-request rules and ensure trailing slash."""
        segments = unquote(raw_path).split("/")
        encoded = [quote(seg, safe="-_.~") for seg in segments]
        result = "/".join(encoded)
        if not result.endswith("/"):
            result += "/"
        return result

    def _sign_request(self, method: str, host: str, path: str,
                      query_params: Dict[str, Any], body: str = "") -> Dict[str, str]:
        """
        Build signed headers for a Huawei Cloud AK/SK request.
        Returns a headers dict ready to use in requests.
        """
        now = datetime.utcnow()
        x_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_str = x_date[:8]

        # Canonical query string: sorted, URL-encoded
        sorted_params = sorted(query_params.items())
        canonical_qs = "&".join(
            f"{quote(str(k), safe='-_.~')}={quote(str(v), safe='-_.~')}"
            for k, v in sorted_params
        )

        # Payload hash
        body_bytes = body.encode("utf-8") if isinstance(body, str) else body
        payload_hash = hashlib.sha256(body_bytes).hexdigest()

        # Signed headers
        signed_headers = "content-type;host;x-sdk-date"
        canonical_headers = (
            f"content-type:application/json\n"
            f"host:{host}\n"
            f"x-sdk-date:{x_date}\n"
        )

        canonical_request = "\n".join([
            method.upper(),
            self._canonical_uri(path),
            canonical_qs,
            canonical_headers,
            signed_headers,
            payload_hash,
        ])

        # String to sign
        algorithm = "SDK-HMAC-SHA256"
        cr_hash = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        string_to_sign = f"{algorithm}\n{x_date}\n{cr_hash}"

        # HMAC signature
        signature = hmac.new(
            self.sk.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        authorization = (
            f"{algorithm} Access={self.ak}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )

        return {
            "Content-Type": "application/json",
            "Host": host,
            "X-Sdk-Date": x_date,
            "Authorization": authorization,
        }

    def _get(self, service: str, path: str, project_id: str,
             query_params: Optional[Dict] = None, timeout: int = 30) -> Optional[Any]:
        """
        Perform a signed GET request to an Advanced API service.
        Returns parsed JSON or None on error.
        """
        host = self._SERVICE_HOSTS[service].format(region=self.region)
        params = dict(query_params or {})
        headers = self._sign_request("GET", host, path, params)
        url = f"https://{host}{path}"

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
            self.logger.debug(
                f"Advanced API {service} {path} → {resp.status_code}: {resp.text[:300]}"
            )
        except Exception as e:
            self.logger.warning(f"Advanced API {service} {path} error: {e}")
        return None

    # ------------------------------------------------------------------
    # Resource fetchers
    # ------------------------------------------------------------------

    def get_vms(self, project_id: str) -> List[Dict]:
        """Fetch all ECS servers for the given project.

        The v1 ``/cloudservers/detail`` endpoint silently ignores the
        ``offset`` parameter (returns 0 results for offset > 0), so
        offset-based pagination is unusable.  Use ``limit=1000`` to
        retrieve all servers in a single call.  If the project has more
        than 1000 VMs, fall back to the v2 Nova endpoint which supports
        proper marker-based pagination.
        """
        path = f"/v1/{project_id}/cloudservers/detail"
        data = self._get("ecs", path, project_id, {"limit": 1000})
        if data:
            servers = data.get("servers", [])
            total = data.get("count", len(servers))
            if len(servers) >= total:
                self.logger.info(f"Advanced ECS: {len(servers)} VMs for project {project_id}")
                return servers
            self.logger.info(
                f"Advanced ECS v1 returned {len(servers)}/{total} VMs, "
                f"falling back to v2 paginated endpoint"
            )

        # Fallback: v2 Nova API with marker-based pagination
        v2_path = f"/v2/{project_id}/servers/detail"
        all_vms: List[Dict] = []
        params: Dict[str, Any] = {"limit": 200}
        while True:
            page = self._get("ecs", v2_path, project_id, params)
            if not page:
                break
            servers = page.get("servers", [])
            all_vms.extend(servers)
            links = page.get("servers_links", [])
            next_link = next((l for l in links if l.get("rel") == "next"), None)
            if not next_link or len(servers) < 200:
                break
            last_id = servers[-1].get("id", "")
            params["marker"] = last_id
        self.logger.info(f"Advanced ECS (v2): {len(all_vms)} VMs for project {project_id}")
        return all_vms

    def get_volumes(self, project_id: str) -> List[Dict]:
        """Fetch all EVS volumes for the given project.

        Uses ``limit=1000`` for the first call; if the project has more,
        falls back to offset-based pagination with ``limit=1000``.
        """
        path = f"/v2/{project_id}/volumes/detail"
        all_vols: List[Dict] = []
        offset = 0
        limit = 1000
        while True:
            data = self._get("evs", path, project_id,
                             {"limit": limit, "offset": offset})
            if not data:
                break
            vols = data.get("volumes", [])
            all_vols.extend(vols)
            if len(vols) < limit:
                break
            offset += limit
        self.logger.info(f"Advanced EVS: {len(all_vols)} volumes for project {project_id}")
        return all_vols

    def get_clusters(self, project_id: str) -> List[Dict]:
        """Fetch all CCE clusters for the given project."""
        path = f"/api/v3/projects/{project_id}/clusters"
        data = self._get("cce", path, project_id)
        if not data:
            return []
        items = data.get("items", [])
        self.logger.info(f"Advanced CCE: {len(items)} clusters for project {project_id}")
        return items

    def get_load_balancers(self, project_id: str) -> List[Dict]:
        """Fetch all ELB load balancers for the given project."""
        path = f"/v3/{project_id}/elb/loadbalancers"
        all_lbs: List[Dict] = []
        marker = None
        limit = 100
        while True:
            params: Dict[str, Any] = {"limit": limit}
            if marker:
                params["marker"] = marker
            data = self._get("elb", path, project_id, params)
            if not data:
                break
            lbs = data.get("loadbalancers", [])
            all_lbs.extend(lbs)
            page_info = data.get("page_info", {})
            next_marker = page_info.get("next_marker")
            if not next_marker or len(lbs) < limit:
                break
            marker = next_marker
        self.logger.info(f"Advanced ELB: {len(all_lbs)} LBs for project {project_id}")
        return all_lbs

    def get_databases(self, project_id: str) -> List[Dict]:
        """Fetch all RDS instances for the given project."""
        path = f"/v3/{project_id}/instances"
        all_dbs: List[Dict] = []
        offset = 0
        limit = 100
        while True:
            data = self._get("rds", path, project_id,
                             {"limit": limit, "offset": offset})
            if not data:
                break
            instances = data.get("instances", [])
            all_dbs.extend(instances)
            if len(instances) < limit:
                break
            offset += limit
        self.logger.info(f"Advanced RDS: {len(all_dbs)} DB instances for project {project_id}")
        return all_dbs

    # ------------------------------------------------------------------
    # ID relationship map
    # ------------------------------------------------------------------

    def build_id_map(self, project_id: str) -> Dict[str, Any]:
        """
        Build ID-relationship maps for a single project tenant.

        Returns::

            {
              'disk_to_vm': {
                  '<volume-uuid>': {
                      'vm_id': '...', 'vm_name': '...',
                      'vm_data': {...}
                  }
              },
              'vm_to_cluster': {
                  '<server-uuid>': {
                      'cluster_id': '...', 'cluster_name': '...'
                  }
              },
              'vm_details': {
                  '<server-uuid>': {
                      'cpu_cores': N, 'ram_mb': N, 'disk_gb': N,
                      'external_ip': '...', 'status': '...', ...
                  }
              },
              'cluster_details': {
                  '<cluster-uid>': { ... }
              },
            }
        """
        disk_to_vm: Dict[str, Dict] = {}
        vm_to_cluster: Dict[str, Dict] = {}
        vm_details: Dict[str, Dict] = {}
        cluster_details: Dict[str, Dict] = {}
        vm_name_to_id: Dict[str, str] = {}  # lowercase name → vm_id

        # --- ECS VMs ---
        try:
            vms = self.get_vms(project_id)
        except Exception as e:
            self.logger.warning(f"build_id_map ECS failed for {project_id}: {e}")
            vms = []

        for vm in vms:
            vm_id = vm.get("id")
            if not vm_id:
                continue
            vm_name = (vm.get("name") or "").strip()
            if vm_name:
                vm_name_to_id[vm_name.lower()] = vm_id
            flavor = vm.get("flavor") or {}
            vcpus = int(flavor.get("vcpus") or 0)
            ram_mb = int(flavor.get("ram") or 0)

            # Extract floating IP from addresses
            external_ip = ""
            addresses = vm.get("addresses") or {}
            for net_addrs in addresses.values():
                if not isinstance(net_addrs, list):
                    continue
                for addr in net_addrs:
                    if addr.get("OS-EXT-IPS:type") == "floating":
                        external_ip = addr.get("addr", "")
                        break
                if external_ip:
                    break

            vm_details[vm_id] = {
                "cpu_cores": vcpus,
                "vcpus": vcpus,
                "ram_mb": ram_mb,
                "disk_gb": 0,  # Filled from EVS volumes below
                "external_ip": external_ip,
                "status": (vm.get("status") or "").upper(),
                "flavor_name": flavor.get("name", ""),
                "availability_zone": vm.get("OS-EXT-AZ:availability_zone", ""),
                "vm_name": vm.get("name", ""),
                "attached_volume_ids": [],
            }

        # --- EVS Volumes (authoritative for disk→VM mapping) ---
        try:
            volumes = self.get_volumes(project_id)
        except Exception as e:
            self.logger.warning(f"build_id_map EVS failed for {project_id}: {e}")
            volumes = []

        for vol in volumes:
            vol_id = vol.get("id")
            if not vol_id:
                continue
            attachments = vol.get("attachments") or []
            for att in attachments:
                server_id = att.get("server_id")
                if server_id:
                    vm_name = vm_details.get(server_id, {}).get("vm_name", "")
                    disk_to_vm[vol_id] = {
                        "vm_id": server_id,
                        "vm_name": vm_name,
                        "vm_data": vm_details.get(server_id, {}),
                    }
                    # Accumulate disk size on the VM
                    size_gb = int(vol.get("size") or 0)
                    if server_id in vm_details:
                        vm_details[server_id]["disk_gb"] += size_gb
                        vm_details[server_id]["attached_volume_ids"].append(vol_id)
                    break  # A volume has at most one attachment

        # --- CCE Clusters ---
        try:
            clusters = self.get_clusters(project_id)
        except Exception as e:
            self.logger.warning(f"build_id_map CCE failed for {project_id}: {e}")
            clusters = []

        for cluster in clusters:
            meta = cluster.get("metadata") or {}
            cluster_uid = meta.get("uid") or meta.get("id")
            cluster_name = meta.get("name", "")
            if not cluster_uid:
                continue

            status_obj = cluster.get("status") or {}
            spec = cluster.get("spec") or {}

            cluster_details[cluster_uid] = {
                "cluster_name": cluster_name,
                "status": status_obj.get("phase", ""),
                "version": spec.get("version", ""),
                "flavor": spec.get("flavor", ""),
                "node_count": spec.get("hostNetwork", {}).get("vpcId", ""),
            }

            # Map cluster nodes to this cluster via node pool naming convention.
            # Advanced API node names typically follow: <cluster-name>-<nodepool>-<suffix>
            for vm_id, vd in vm_details.items():
                vm_name_lower = (vd.get("vm_name") or "").lower()
                cluster_name_lower = cluster_name.lower()
                if cluster_name_lower and vm_name_lower.startswith(cluster_name_lower):
                    vm_to_cluster[vm_id] = {
                        "cluster_id": cluster_uid,
                        "cluster_name": cluster_name,
                    }

        self.logger.info(
            f"build_id_map project={project_id}: "
            f"{len(disk_to_vm)} disk→vm, {len(vm_to_cluster)} vm→cluster, "
            f"{len(vm_details)} vm_details, {len(cluster_details)} clusters"
        )
        return {
            "disk_to_vm": disk_to_vm,
            "vm_to_cluster": vm_to_cluster,
            "vm_details": vm_details,
            "cluster_details": cluster_details,
            "vm_name_to_id": vm_name_to_id,
        }

    # ------------------------------------------------------------------
    # Cloud Eye (CES) — utilization metrics
    # ------------------------------------------------------------------

    def get_sfs_turbo_shares(self, project_id: str) -> List[Dict]:
        """Fetch all SFS Turbo shares for the project."""
        path = f"/v1/{project_id}/sfs-turbo/shares/detail"
        data = self._get("sfs-turbo", path, project_id)
        shares = (data or {}).get("shares", [])
        self.logger.info(f"SFS Turbo: {len(shares)} shares for project {project_id}")
        return shares

    def _post(self, service: str, path: str, project_id: str,
              body: str, timeout: int = 30) -> Optional[Any]:
        """Perform a signed POST request to an Advanced API service."""
        host = self._SERVICE_HOSTS[service].format(region=self.region)
        headers = self._sign_request("POST", host, path, {}, body)
        url = f"https://{host}{path}"
        try:
            resp = requests.post(url, headers=headers, data=body, timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
            self.logger.debug(
                f"Advanced API POST {service} {path} → {resp.status_code}: "
                f"{resp.text[:300]}"
            )
        except Exception as e:
            self.logger.warning(f"Advanced API POST {service} {path} error: {e}")
        return None

    def get_ces_metrics_batch(
        self, project_id: str, namespace: str, dim_name: str,
        dim_values: List[str], metric_names: Optional[List[str]] = None,
        hours: int = 24,
    ) -> Dict[str, Dict[str, Dict[str, float]]]:
        """
        Fetch CES metrics for a batch of resources using the batch API.

        Uses POST /V1.0/{project_id}/batch-query-metric-data which accepts
        up to 10 metric queries per call, dramatically reducing API calls.

        Returns::

            {
                '<dim_value>': {
                    'cpu_util': {'avg': 3.2, 'max': 14.5, ...},
                    ...
                },
                ...
            }
        """
        import time, json as json_lib
        if not dim_values:
            return {}
        if metric_names is None:
            metric_names = self._CES_FINOPS_METRICS.get(namespace, [])
        if not metric_names:
            return {}

        now_ms = int(time.time() * 1000)
        from_ms = now_ms - hours * 3600 * 1000
        batch_path = f"/V1.0/{project_id}/batch-query-metric-data"
        max_per_batch = 10

        # Build all metric queries
        all_queries = []
        for dim_val in dim_values:
            for metric in metric_names:
                all_queries.append({
                    "namespace": namespace,
                    "metric_name": metric,
                    "dimensions": [{"name": dim_name, "value": dim_val}],
                })

        result: Dict[str, Dict] = {}
        total_batches = (len(all_queries) + max_per_batch - 1) // max_per_batch

        for i in range(0, len(all_queries), max_per_batch):
            chunk = all_queries[i:i + max_per_batch]
            body = json_lib.dumps({
                "metrics": chunk,
                "from": from_ms,
                "to": now_ms,
                "period": "3600",
                "filter": "average",
            })
            data = self._post("ces", batch_path, project_id, body, timeout=30)
            if not data:
                continue
            for m in data.get("metrics", []):
                dps = m.get("datapoints", [])
                if not dps:
                    continue
                dims = m.get("dimensions", [])
                dim_val = dims[0].get("value", "") if dims else ""
                metric_name = m.get("metric_name", "")
                if not dim_val or not metric_name:
                    continue
                vals = [dp.get("average", 0) for dp in dps]
                if dim_val not in result:
                    result[dim_val] = {}
                result[dim_val][metric_name] = {
                    "avg": round(sum(vals) / len(vals), 2) if vals else 0,
                    "max": round(max(vals), 2) if vals else 0,
                    "latest": round(vals[-1], 2) if vals else 0,
                    "points": len(vals),
                }

        self.logger.info(
            f"CES batch {namespace}: {len(result)}/{len(dim_values)} "
            f"resources with metrics ({total_batches} API calls)"
        )
        return result

    def build_ces_utilization_map(
        self, project_id: str, vm_ids: List[str] = None,
        sfs_share_ids: List[str] = None,
        elb_ids: List[str] = None,
        rds_ids: List[str] = None,
        hours: int = 24,
    ) -> Dict[str, Dict]:
        """
        Build a flat utilization map keyed by resource ID.

        Keys are resource IDs (VM UUID, share UUID, etc.).
        Values are dicts of metric → {avg, max, latest}.

        This is the main entry point for the sync plugin.
        """
        utilization: Dict[str, Dict] = {}

        if vm_ids:
            ns, dim = self._CES_NAMESPACES['ecs']
            data = self.get_ces_metrics_batch(
                project_id, ns, dim, vm_ids, hours=hours)
            utilization.update(data)

        if sfs_share_ids:
            ns, dim = self._CES_NAMESPACES['efs']
            data = self.get_ces_metrics_batch(
                project_id, ns, dim, sfs_share_ids, hours=hours)
            utilization.update(data)

        if elb_ids:
            ns, dim = self._CES_NAMESPACES['elb']
            data = self.get_ces_metrics_batch(
                project_id, ns, dim, elb_ids, hours=hours)
            utilization.update(data)

        if rds_ids:
            ns, dim = self._CES_NAMESPACES['rds']
            data = self.get_ces_metrics_batch(
                project_id, ns, dim, rds_ids, hours=hours)
            utilization.update(data)

        self.logger.info(
            f"CES utilization map for project {project_id}: "
            f"{len(utilization)} resources with metrics"
        )
        return utilization

