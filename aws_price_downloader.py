#!/usr/bin/env python3
"""AWS Pricing Data Downloader - Downloads pricing information for AWS services across all regions."""

import requests
import json
import os
from typing import List, Dict, Optional, Tuple
import time
from tqdm import tqdm
import logging
from datetime import datetime
import humanize
import sys
from requests.adapters import HTTPAdapter, Retry
import concurrent.futures
from queue import Queue
from threading import Lock

class AWSPriceDownloader:
    # Base URL for AWS pricing API
    BASE_URL = "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/{service}/current/{region}/index.json"
    
    # List of AWS regions to fetch pricing data from
    REGIONS = [
        "ap-south-1", # ap-south-1 (Mumbai)
        # "ap-northeast-1", # ap-northeast-1 (Tokyo)
        # "us-east-1", # us-east-1 (Virginia)
        # "us-east-2", # us-east-2 (Ohio)
        # "us-west-1", # us-west-1 (N. California)
        # "us-west-2" # us-west-2 (Oregon)
    ]
    
    # List of AWS services to fetch pricing for
    SERVICES = [
        "AmazonEC2",      # For EC2 instances and EMR nodes
        "AmazonS3",       # For data storage
        "AmazonRDS",      # For databases
        "AmazonDynamoDB", # For NoSQL databases
        "AWSLambda",      # For serverless functions
        "AmazonSNS",      # For notifications
        "AmazonEMR",      # For EMR clusters
        "AmazonElastiCache", # For caching
        "AmazonCloudFront", # For content delivery
        "AmazonRoute53",  # For DNS
        "AmazonVPC",      # For networking
        "AWSConfig",      # For configuration tracking
    ]
    
    def __init__(self, base_dir: str = "aws_pricing_data", max_retries: int = 3, max_workers: int = 5):
        """Initialize the downloader with configuration and setup."""
        self.base_dir = base_dir
        self.max_retries = max_retries
        self.max_workers = max_workers
        self.failed_downloads = []
        self.total_data_downloaded = 0
        self.data_lock = Lock()
        self.progress_queue = Queue()
        self.session = self._create_session()
        
        try:
            self.setup_logging()
            self._create_directories()
        except Exception as e:
            logging.critical(f"Failed to initialize: {str(e)}")
            raise SystemExit(1)
    
    def _create_session(self) -> requests.Session:
        """Create an optimized requests session with retry strategy."""
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["HEAD", "GET"]
        )
        # Increase max pool size for concurrent connections
        adapter = HTTPAdapter(
            max_retries=retries,
            pool_connections=self.max_workers,
            pool_maxsize=self.max_workers * 2
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _create_directories(self):
        """Create necessary directories for storing data."""
        try:
            os.makedirs(self.base_dir, exist_ok=True)
            for region in self.REGIONS:
                os.makedirs(os.path.join(self.base_dir, region), exist_ok=True)
        except OSError as e:
            raise Exception(f"Failed to create directories: {str(e)}")
    
    def setup_logging(self):
        """Setup logging configuration."""
        try:
            log_dir = "logs"
            os.makedirs(log_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(log_dir, f"price_download_{timestamp}.log")
            
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(log_file),
                    logging.StreamHandler(sys.stdout)
                ]
            )
        except Exception as e:
            print(f"Failed to setup logging: {str(e)}")
            raise

    def download_pricing_data(self, service: str, region: str) -> Tuple[bool, int]:
        """Download and save pricing data for a service in a region."""
        url = self.BASE_URL.format(service=service, region=region)
        downloaded_size = 0
        
        try:
            # Stream download with larger chunk size
            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            content = bytearray()
            for chunk in response.iter_content(chunk_size=32768):  # Increased chunk size
                if chunk:
                    content.extend(chunk)
                    downloaded_size += len(chunk)
            
            # Parse JSON and save
            try:
                data = json.loads(content)
                if self.save_pricing_data(data, service, region):
                    with self.data_lock:
                        self.total_data_downloaded += downloaded_size
                    return True, downloaded_size
            except json.JSONDecodeError as e:
                logging.error(f"Invalid JSON data for {service} in {region}: {str(e)}")
        
        except Exception as e:
            self._record_failure(service, region, str(e))
            logging.error(f"Error downloading {service} in {region}: {str(e)}")
        
        return False, downloaded_size

    def _record_failure(self, service: str, region: str, error: str):
        """Thread-safe method to record download failures."""
        with self.data_lock:
            self.failed_downloads.append({
                "service": service,
                "region": region,
                "error": error,
                "timestamp": datetime.now().isoformat()
            })

    def save_pricing_data(self, data: Dict, service: str, region: str) -> bool:
        """Save pricing data to JSON file with error handling."""
        if not data:
            return False
            
        try:
            region_dir = os.path.join(self.base_dir, region)
            filename = f"{service}_pricing.json"
            filepath = os.path.join(region_dir, filename)
            
            # Write to temporary file first
            temp_filepath = filepath + '.tmp'
            with open(temp_filepath, 'w') as f:
                json.dump(data, f)  # Removed indent for faster writing
            
            # Atomic rename
            os.replace(temp_filepath, filepath)
            
            file_size = os.path.getsize(filepath)
            human_size = humanize.naturalsize(file_size)
            logging.info(f"Saved {service} in {region} ({human_size})")
            return True
            
        except Exception as e:
            self._record_failure(service, region, f"Save error: {str(e)}")
            return False

    def process_download(self, service: str, region: str) -> Tuple[bool, int]:
        """Process a single download with retries."""
        for attempt in range(self.max_retries):
            try:
                success, size = self.download_pricing_data(service, region)
                if success:
                    return True, size
                time.sleep(2 ** attempt)  # Exponential backoff
            except Exception as e:
                if attempt == self.max_retries - 1:
                    self._record_failure(service, region, str(e))
        return False, 0

    def download_all_pricing(self):
        """Download all pricing data using parallel processing."""
        combinations = [(service, region) 
                       for region in self.REGIONS 
                       for service in self.SERVICES]
        total_combinations = len(combinations)
        successful_downloads = 0
        start_time = time.time()
        
        logging.info(f"Starting parallel downloads with {self.max_workers} workers")
        
        with tqdm(total=total_combinations,
                 desc="Overall Progress",
                 bar_format='Overall Progress: {percentage:3.0f}% |{bar:30} | {n}/{total} [{elapsed}<{remaining}, {rate_fmt}]',
                 unit='file') as pbar:
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_combo = {
                    executor.submit(self.process_download, service, region): (service, region)
                    for service, region in combinations
                }
                
                for future in concurrent.futures.as_completed(future_to_combo):
                    service, region = future_to_combo[future]
                    try:
                        success, _ = future.result()
                        if success:
                            successful_downloads += 1
                    except Exception as e:
                        logging.error(f"Failed to process {service} in {region}: {str(e)}")
                    finally:
                        pbar.update(1)
        
        self._show_summary(total_combinations, successful_downloads, start_time)
    
    def _show_summary(self, total: int, successful: int, start_time: float):
        """Display download summary and statistics."""
        elapsed_time = time.time() - start_time
        total_size_human = humanize.naturalsize(self.total_data_downloaded)
        
        print("\nDownload Summary:")
        print(f"Total data downloaded: {total_size_human}")
        print(f"Total files attempted: {total}")
        print(f"Successful downloads: {successful}")
        print(f"Failed downloads: {len(self.failed_downloads)}")
        print(f"Total time elapsed: {time.strftime('%H:%M:%S', time.gmtime(elapsed_time))}")
        print(f"Average speed: {humanize.naturalsize(self.total_data_downloaded / elapsed_time)}/s")
        
        if self.failed_downloads:
            print("\nFailed Downloads:")
            for failure in self.failed_downloads:
                print(f"- {failure['service']} in {failure['region']}: {failure['error']}")
            
            try:
                failed_file = os.path.join(self.base_dir, "failed_downloads.json")
                with open(failed_file, 'w') as f:
                    json.dump(self.failed_downloads, f, indent=2)
                print(f"\nFailed downloads have been saved to: {failed_file}")
            except Exception as e:
                logging.error(f"Failed to save failed downloads list: {str(e)}")

def download_pricing_data(service: str, region: str = "us-east-1") -> Optional[Dict]:
    """
    Standalone function to download pricing data for a specific service and region.
    Returns the pricing data as a dictionary or None if the download fails.
    """
    downloader = AWSPriceDownloader()
    success, _ = downloader.download_pricing_data(service, region)
    if success:
        try:
            filepath = os.path.join(downloader.base_dir, region, f"{service}_pricing.json")
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error reading pricing data for {service} in {region}: {str(e)}")
    return None

def main():
    """Main entry point with comprehensive error handling."""
    try:
        # Determine optimal number of workers based on CPU cores
        max_workers = min(32, os.cpu_count() * 4)
        downloader = AWSPriceDownloader(max_workers=max_workers)
        downloader.download_all_pricing()
    except KeyboardInterrupt:
        print("\nDownload process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {str(e)}")
        logging.exception("Unexpected error in main")
        sys.exit(1)

if __name__ == "__main__":
    main() 