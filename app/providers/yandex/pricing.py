"""
Yandex Cloud Pricing Calculator
Based on official Yandex Cloud pricing documentation
https://yandex.cloud/en/docs/compute/pricing
"""
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class YandexPricing:
    """
    Yandex Cloud pricing calculator using documented rates
    
    Pricing is based on official Yandex Cloud documentation.
    Rates are platform-specific and updated as of October 2025.
    """
    
    # Compute pricing (₽/hour) for different platforms
    # Source: https://yandex.cloud/en/docs/compute/pricing#prices-instance-resources
    PLATFORM_PRICING = {
        'standard-v3': {  # Intel Ice Lake / AMD EPYC
            'cpu_100': 1.1200,  # 100% vCPU
            'cpu_50': 0.5600,   # 50% vCPU
            'cpu_20': 0.3360,   # 20% vCPU
            'cpu_5': 0.1680,    # 5% vCPU
            'ram_gb': 0.3000,   # Per GB RAM
        },
        'standard-v2': {  # Intel Cascade Lake
            'cpu_100': 1.0800,
            'cpu_50': 0.5400,
            'cpu_20': 0.3240,
            'cpu_5': 0.1620,
            'ram_gb': 0.2900,
        },
        'standard-v1': {  # Intel Broadwell
            'cpu_100': 0.9600,
            'cpu_50': 0.4800,
            'cpu_20': 0.2880,
            'cpu_5': 0.1440,
            'ram_gb': 0.2560,
        },
        'highfreq-v3': {  # High frequency Intel Ice Lake
            'cpu_100': 1.3440,
            'ram_gb': 0.3600,
        },
        'gpu-standard-v3': {  # GPU instances
            'cpu_100': 1.1200,
            'ram_gb': 0.3000,
        },
    }
    
    # Storage pricing (₽/GB/month)
    # Source: https://yandex.cloud/en/docs/compute/pricing#prices-storage
    STORAGE_PRICING = {
        'network-hdd': 2.2400,      # Standard HDD
        'network-ssd': 9.1104,      # Fast SSD
        'network-ssd-nonreplicated': 7.6800,  # Non-replicated SSD
        'network-ssd-io-m3': 12.2976,  # Ultra-fast SSD
    }
    
    # Public IP pricing (₽/hour)
    # Source: https://yandex.cloud/en/docs/vpc/pricing
    # SKU: dn229q5mnmp58t58tfel (network.public_fips)
    VPC_PRICING = {
        'public_ip_inactive': 0.1920,  # Inactive public IP (reserved but unused)
        'public_ip_active': 0.2592,    # Active public IP (attached to VM) - NOT FREE!
    }
    
    # Managed PostgreSQL pricing (₽/day)
    # Source: HAR file analysis of actual billing data (Oct 27, 2024)
    # Note: Managed services have overhead costs (backups, monitoring, management)
    # that make them more expensive than raw Compute VMs
    POSTGRESQL_PRICING = {
        'cpu_per_day': 42.25,     # Per vCPU per day (100% fraction)
        'ram_per_gb_day': 11.41,  # Per GB RAM per day
        'storage_hdd_per_gb_day': 0.1152,  # network-hdd storage per GB per day
        'storage_ssd_per_gb_day': 0.43,    # network-ssd storage per GB per day (estimated)
    }
    
    # Managed Kafka pricing (₽/day)
    # Source: HAR file analysis of actual billing data (Oct 27, 2024)
    # Cluster: 2 vCPUs, 4GB RAM, 100GB HDD, 1 public IP = 198.14₽/day
    # Breakdown: CPU 87.09₽, RAM 93.31₽, HDD 11.52₽, Public IP 6.22₽
    KAFKA_PRICING = {
        'cpu_per_day': 43.545,    # 87.09 ÷ 2 vCPUs = Per vCPU per day (100% fraction)
        'ram_per_gb_day': 23.3275, # 93.31 ÷ 4 GB = Per GB RAM per day (2x PostgreSQL!)
        'storage_hdd_per_gb_day': 0.1152,  # 11.52 ÷ 100 GB = Per GB HDD storage per day
        'storage_ssd_per_gb_day': 0.43,    # network-ssd storage per GB per day (estimated)
        'public_ip_per_day': 6.22,  # Public IP for Kafka cluster
    }
    
    @classmethod
    def calculate_vm_cost(cls, vcpus: int, ram_gb: float, storage_gb: float = 0,
                          platform_id: str = 'standard-v3', 
                          core_fraction: int = 100,
                          disk_type: str = 'network-ssd',
                          has_public_ip: bool = False) -> Dict[str, float]:
        """
        Calculate VM cost based on official Yandex pricing
        
        Args:
            vcpus: Number of vCPUs
            ram_gb: RAM in GB
            storage_gb: Boot disk size in GB (if attached)
            platform_id: Platform ID (standard-v3, standard-v2, etc.)
            core_fraction: CPU fraction (5, 20, 50, 100)
            disk_type: Disk type (network-hdd, network-ssd, etc.)
            has_public_ip: Whether VM has public IP
            
        Returns:
            Dict with hourly, daily, and monthly costs
        """
        try:
            # Get platform pricing
            platform = cls.PLATFORM_PRICING.get(platform_id, cls.PLATFORM_PRICING['standard-v3'])
            
            # Get CPU price based on core fraction
            cpu_key = f'cpu_{core_fraction}'
            cpu_hourly_rate = platform.get(cpu_key, platform.get('cpu_100', 1.12))
            ram_hourly_rate = platform.get('ram_gb', 0.30)
            
            # Calculate compute cost
            cpu_cost_hourly = vcpus * cpu_hourly_rate
            ram_cost_hourly = ram_gb * ram_hourly_rate
            
            # Calculate storage cost (convert monthly to hourly)
            storage_hourly_rate = cls.STORAGE_PRICING.get(disk_type, 9.1104) / 730  # 730 hours/month
            storage_cost_hourly = storage_gb * storage_hourly_rate
            
            # VPC cost (public IP)
            vpc_cost_hourly = cls.VPC_PRICING['public_ip_active'] if has_public_ip else 0
            
            # Total
            total_hourly = cpu_cost_hourly + ram_cost_hourly + storage_cost_hourly + vpc_cost_hourly
            total_daily = total_hourly * 24
            total_monthly = total_hourly * 730  # Yandex uses 730 hours/month
            
            return {
                'hourly_cost': round(total_hourly, 4),
                'daily_cost': round(total_daily, 2),
                'monthly_cost': round(total_monthly, 2),
                'breakdown': {
                    'cpu': round(cpu_cost_hourly * 730, 2),
                    'ram': round(ram_cost_hourly * 730, 2),
                    'storage': round(storage_cost_hourly * 730, 2),
                    'vpc': round(vpc_cost_hourly * 730, 2)
                }
            }
        
        except Exception as e:
            logger.error(f"Error calculating VM cost: {e}")
            return {
                'hourly_cost': 0,
                'daily_cost': 0,
                'monthly_cost': 0,
                'breakdown': {}
            }
    
    @classmethod
    def calculate_disk_cost(cls, size_gb: float, disk_type: str = 'network-ssd') -> Dict[str, float]:
        """
        Calculate standalone disk cost
        
        Args:
            size_gb: Disk size in GB
            disk_type: Disk type (network-hdd, network-ssd, etc.)
            
        Returns:
            Dict with hourly, daily, and monthly costs
        """
        try:
            monthly_rate = cls.STORAGE_PRICING.get(disk_type, 9.1104)
            monthly_cost = size_gb * monthly_rate
            hourly_cost = monthly_cost / 730
            daily_cost = hourly_cost * 24
            
            return {
                'hourly_cost': round(hourly_cost, 4),
                'daily_cost': round(daily_cost, 2),
                'monthly_cost': round(monthly_cost, 2)
            }
        
        except Exception as e:
            logger.error(f"Error calculating disk cost: {e}")
            return {
                'hourly_cost': 0,
                'daily_cost': 0,
                'monthly_cost': 0
            }
    
    @classmethod
    def calculate_cluster_cost(cls, total_vcpus: int, total_ram_gb: float,
                               total_storage_gb: float, cluster_type: str = 'kubernetes',
                               platform_id: str = 'standard-v3', 
                               disk_type: str = 'network-hdd') -> Dict[str, float]:
        """
        Calculate cluster cost (Kubernetes, databases)
        
        For PostgreSQL, uses HAR-derived pricing for accuracy.
        For other services, uses platform pricing + storage.
        
        Args:
            total_vcpus: Total vCPUs across all nodes/hosts
            total_ram_gb: Total RAM in GB
            total_storage_gb: Total storage in GB
            cluster_type: Type of cluster (kubernetes, postgresql, mysql, etc.)
            platform_id: Platform ID
            disk_type: Disk type (network-hdd, network-ssd)
            
        Returns:
            Dict with hourly, daily, and monthly costs
        """
        try:
            # PostgreSQL has special pricing from HAR analysis
            if cluster_type == 'postgresql':
                cpu_cost_daily = total_vcpus * cls.POSTGRESQL_PRICING['cpu_per_day']
                ram_cost_daily = total_ram_gb * cls.POSTGRESQL_PRICING['ram_per_gb_day']
                
                # Choose storage pricing based on disk type
                if 'ssd' in disk_type.lower():
                    storage_cost_daily = total_storage_gb * cls.POSTGRESQL_PRICING['storage_ssd_per_gb_day']
                else:  # HDD
                    storage_cost_daily = total_storage_gb * cls.POSTGRESQL_PRICING['storage_hdd_per_gb_day']
                
                total_daily = cpu_cost_daily + ram_cost_daily + storage_cost_daily
                total_hourly = total_daily / 24
                total_monthly = total_daily * 30
                
                return {
                    'hourly_cost': round(total_hourly, 4),
                    'daily_cost': round(total_daily, 2),
                    'monthly_cost': round(total_monthly, 2),
                    'breakdown': {
                        'cpu': round(cpu_cost_daily, 2),
                        'ram': round(ram_cost_daily, 2),
                        'storage': round(storage_cost_daily, 2),
                    },
                    'accuracy': 'har_based'
                }
            
            # Kafka has special pricing from HAR analysis
            if cluster_type == 'kafka':
                cpu_cost_daily = total_vcpus * cls.KAFKA_PRICING['cpu_per_day']
                ram_cost_daily = total_ram_gb * cls.KAFKA_PRICING['ram_per_gb_day']
                
                # Choose storage pricing based on disk type
                if 'ssd' in disk_type.lower():
                    storage_cost_daily = total_storage_gb * cls.KAFKA_PRICING['storage_ssd_per_gb_day']
                else:  # HDD
                    storage_cost_daily = total_storage_gb * cls.KAFKA_PRICING['storage_hdd_per_gb_day']
                
                # Note: Public IP cost is per cluster, not per host
                # We'll add it in the service processing layer based on actual config
                total_daily = cpu_cost_daily + ram_cost_daily + storage_cost_daily
                total_hourly = total_daily / 24
                total_monthly = total_daily * 30
                
                return {
                    'hourly_cost': round(total_hourly, 4),
                    'daily_cost': round(total_daily, 2),
                    'monthly_cost': round(total_monthly, 2),
                    'breakdown': {
                        'cpu': round(cpu_cost_daily, 2),
                        'ram': round(ram_cost_daily, 2),
                        'storage': round(storage_cost_daily, 2),
                    },
                    'accuracy': 'har_based'
                }
            
            # For other cluster types, use generic compute pricing
            platform = cls.PLATFORM_PRICING.get(platform_id, cls.PLATFORM_PRICING['standard-v3'])
            
            # Use 100% vCPU for managed services
            cpu_hourly_rate = platform.get('cpu_100', 1.12)
            ram_hourly_rate = platform.get('ram_gb', 0.30)
            
            cpu_cost_hourly = total_vcpus * cpu_hourly_rate
            ram_cost_hourly = total_ram_gb * ram_hourly_rate
            
            # Storage for managed services typically uses network-ssd or better
            storage_rate = cls.STORAGE_PRICING.get('network-ssd', 9.1104)
            storage_monthly = total_storage_gb * storage_rate
            storage_hourly = storage_monthly / 730
            
            # Kubernetes has additional master node cost
            master_cost_hourly = 0
            if cluster_type == 'kubernetes':
                # Zonal master: free, Regional master: ~3500 ₽/month = ~4.79 ₽/hour
                master_cost_hourly = 4.79  # Assume regional master
            
            total_hourly = cpu_cost_hourly + ram_cost_hourly + storage_hourly + master_cost_hourly
            total_daily = total_hourly * 24
            total_monthly = total_hourly * 730
            
            return {
                'hourly_cost': round(total_hourly, 4),
                'daily_cost': round(total_daily, 2),
                'monthly_cost': round(total_monthly, 2),
                'breakdown': {
                    'cpu': round(cpu_cost_hourly * 730, 2),
                    'ram': round(ram_cost_hourly * 730, 2),
                    'storage': round(storage_monthly, 2),
                    'master': round(master_cost_hourly * 730, 2) if cluster_type == 'kubernetes' else 0
                }
            }
        
        except Exception as e:
            logger.error(f"Error calculating cluster cost: {e}")
            return {
                'hourly_cost': 0,
                'daily_cost': 0,
                'monthly_cost': 0,
                'breakdown': {}
            }

