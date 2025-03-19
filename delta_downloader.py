import json
import os
import hashlib
from datetime import datetime
import logging
from typing import Tuple, Dict, Any, Optional
from aws_price_downloader import download_pricing_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeltaDownloader:
    def __init__(self, cache_dir: str = "aws_pricing_data"):
        """Initialize the DeltaDownloader with a cache directory."""
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
    def _get_cache_path(self, service: str, region: str) -> str:
        """Get the cache file path for a service and region."""
        return os.path.join(self.cache_dir, f"{service}_{region}_cache.json")
        
    def _get_delta_path(self, service: str, region: str) -> str:
        """Get the delta history file path for a service and region."""
        return os.path.join(self.cache_dir, f"{service}_{region}_delta_history.json")
        
    def calculate_hash(self, data: Dict) -> str:
        """Calculate a hash of the pricing data."""
        return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()
        
    def get_cached_data(self, service: str, region: str) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Get cached pricing data and its hash.
        Returns (data, hash) tuple. Both values will be None if no cache exists.
        """
        cache_path = self._get_cache_path(service, region)
        try:
            if os.path.exists(cache_path):
                with open(cache_path, 'r') as f:
                    cached = json.load(f)
                    return cached.get('data'), cached.get('hash')
        except Exception as e:
            logger.error(f"Error reading cache for {service} in {region}: {str(e)}")
        return None, None
        
    def save_to_cache(self, service: str, region: str, data: Dict, data_hash: str):
        """Save pricing data and its hash to cache."""
        cache_path = self._get_cache_path(service, region)
        try:
            with open(cache_path, 'w') as f:
                json.dump({
                    'data': data,
                    'hash': data_hash,
                    'timestamp': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving cache for {service} in {region}: {str(e)}")
            
    def compute_delta(self, old_data: Dict, new_data: Dict) -> Dict:
        """
        Compute the difference between old and new pricing data.
        Returns a dictionary of changes (added, removed, modified prices).
        """
        delta = {
            'added': {},
            'removed': {},
            'modified': {}
        }
        
        old_products = old_data.get('products', {})
        new_products = new_data.get('products', {})
        
        # Find added and modified products
        for product_id, new_product in new_products.items():
            if product_id not in old_products:
                delta['added'][product_id] = new_product
            elif new_product != old_products[product_id]:
                delta['modified'][product_id] = {
                    'old': old_products[product_id],
                    'new': new_product
                }
                
        # Find removed products
        for product_id in old_products:
            if product_id not in new_products:
                delta['removed'][product_id] = old_products[product_id]
                
        return delta
        
    def save_delta_history(self, service: str, region: str, delta: Dict):
        """Save delta history for a service and region."""
        delta_path = self._get_delta_path(service, region)
        try:
            history = []
            if os.path.exists(delta_path):
                with open(delta_path, 'r') as f:
                    history = json.load(f)
                    
            history.append({
                'timestamp': datetime.now().isoformat(),
                'delta': delta
            })
            
            # Keep only last 10 deltas to save space
            history = history[-10:]
            
            with open(delta_path, 'w') as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving delta history for {service} in {region}: {str(e)}")
            
    def process_download(self, service: str, region: str) -> Tuple[bool, Dict]:
        """
        Process a new download, checking for changes and computing deltas if necessary.
        Returns (has_changes, delta) tuple.
        """
        try:
            # Get new pricing data
            new_data = download_pricing_data(service, region)
            if not new_data:
                return False, {}
                
            new_hash = self.calculate_hash(new_data)
            
            # Get cached data
            cached_data, cached_hash = self.get_cached_data(service, region)
            
            # If no cache or hash different, compute and save delta
            if not cached_data or cached_hash != new_hash:
                delta = self.compute_delta(cached_data or {'products': {}}, new_data)
                self.save_to_cache(service, region, new_data, new_hash)
                self.save_delta_history(service, region, delta)
                return True, delta
                
            return False, {}
            
        except Exception as e:
            logger.error(f"Error processing download for {service} in {region}: {str(e)}")
            return False, {} 