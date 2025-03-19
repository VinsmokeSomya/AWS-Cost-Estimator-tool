import os
import boto3
import json
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AWSPricingAPI:
    def __init__(self, region='ap-south-1'):
        """Initialize AWS Pricing API client."""
        load_dotenv()
        
        # Validate AWS credentials
        self.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        
        if not self.aws_access_key or not self.aws_secret_key:
            raise ValueError("AWS credentials not found in environment variables")
        
        # Convert region code to region name
        self.region_names = {
            'ap-south-1': 'Asia Pacific (Mumbai)',
            'us-east-1': 'US East (N. Virginia)',
            # Add more mappings as needed
        }
        self.region = self.region_names.get(region, region)
        
        self.pricing_client = boto3.client(
            'pricing',
            region_name='us-east-1',  # Pricing API is only available in us-east-1
            aws_access_key_id=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_key
        )

    def get_pricing(self, service_code, location, instance_type=None):
        """
        Get pricing information for any AWS service.
        Filters by region and optionally by instance type.
        """
        try:
            # Build filters
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': location}
            ]
            
            # Add service-specific filters
            if service_code == 'AmazonRDS':
                filters.extend([
                    {'Type': 'TERM_MATCH', 'Field': 'databaseEngine', 'Value': 'MySQL'},
                    {'Type': 'TERM_MATCH', 'Field': 'deploymentOption', 'Value': 'Single-AZ'}
                ])
                if instance_type:
                    instance_type_value = instance_type if instance_type.startswith('db.') else f'db.{instance_type}'
                    filters.append({
                        'Type': 'TERM_MATCH',
                        'Field': 'usagetype',
                        'Value': f'APS3-InstanceUsage:{instance_type_value}'
                    })
            elif service_code == 'AmazonEBS':
                filters.extend([
                    {'Type': 'TERM_MATCH', 'Field': 'volumeType', 'Value': 'General Purpose'},
                    {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Storage'}
                ])
            elif service_code == 'AWSEFS':
                filters.extend([
                    {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Storage'},
                    {'Type': 'TERM_MATCH', 'Field': 'storageClass', 'Value': 'General Purpose'}
                ])
            elif service_code == 'AmazonEC2':
                filters.extend([
                    {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': 'Linux'},
                    {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': 'Shared'}
                ])
                if instance_type:
                    filters.append({'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type})
            
            # Log the filters being used
            logger.info(f"Using filters for {service_code}: {filters}")
            
            # Get pricing data with filters
            response = self.pricing_client.get_products(
                ServiceCode=service_code,
                Filters=filters
            )
            
            pricing_info = []
            for price_item in response['PriceList']:
                product = json.loads(price_item)
                attributes = product['product']['attributes']
                
                # Get price information
                try:
                    price_dimensions = list(product['terms']['OnDemand'].values())[0]['priceDimensions']
                    price_per_unit = list(price_dimensions.values())[0]['pricePerUnit'].get('USD', 'N/A')
                    
                    # Convert price to hourly if applicable
                    if price_per_unit != 'N/A':
                        if service_code == 'AmazonS3':
                            price_per_hour = float(price_per_unit) / (30 * 24)
                        elif service_code == 'AmazonEBS':
                            price_per_hour = float(price_per_unit) / (30 * 24)  # EBS is billed monthly
                        else:
                            price_per_hour = float(price_per_unit)
                        price_per_hour = f"{price_per_hour:.8f}"
                    else:
                        price_per_hour = 'N/A'
                    
                    pricing_info.append({
                        'Service': service_code,
                        'Instance Type': attributes.get('instanceType', 'N/A'),
                        'Region': attributes.get('location', 'N/A'),
                        'Price per Unit (USD)': price_per_unit,
                        'Price per Hour (USD)': price_per_hour,
                        'Attributes': attributes
                    })
                except (KeyError, IndexError):
                    continue  # Skip if price information is not in expected format
            
            return pricing_info
        
        except (BotoCoreError, ClientError) as error:
            logger.error(f"Error fetching pricing data: {error}")
            return []

    def calculate_service_cost(self, service_code, instance_type=None):
        """
        Calculate the cost for a service based on its pricing.
        """
        pricing_info = self.get_pricing(service_code, self.region, instance_type)
        if not pricing_info:
            return {
                'monthly_cost': 0.0,
                'daily_cost': 0.0,
                'hourly_cost': 0.0,
                'details': {}
            }
        
        # Use the first pricing option
        price_data = pricing_info[0]
        price_per_hour = float(price_data['Price per Hour (USD)']) if price_data['Price per Hour (USD)'] != 'N/A' else 0.0
        
        # Calculate costs
        hourly_cost = price_per_hour
        daily_cost = hourly_cost * 24
        monthly_cost = daily_cost * 30
        
        return {
            'monthly_cost': monthly_cost,
            'daily_cost': daily_cost,
            'hourly_cost': hourly_cost,
            'details': price_data
        }

    def _log_available_values(self, service_code):
        """Log available values for service attributes for debugging."""
        attributes = [
            'regionCode',
            'productFamily',
            'usagetype',
            'storageClass',
            'volumeType',
            'requestType',
            'transferType'
        ]
        
        for attr in attributes:
            try:
                response = self.pricing_client.get_attribute_values(
                    ServiceCode=service_code,
                    AttributeName=attr
                )
                values = [item['Value'] for item in response['AttributeValues']]
                logger.info(f"Available {attr} values for {service_code}: {values}")
            except Exception as e:
                logger.debug(f"Could not get {attr} values for {service_code}: {e}")

    def get_service_specifications(self, service_code, filters=None):
        """
        Get detailed specifications for a service.
        """
        pricing_info = self.get_pricing(service_code, self.region)
        if not pricing_info:
            return {}
        
        specs = pricing_info[0]['Attributes']
        specs['pricing'] = {
            'hourly': pricing_info[0]['Price per Hour (USD)'],
            'monthly': float(pricing_info[0]['Price per Hour (USD)']) * 24 * 30 if pricing_info[0]['Price per Hour (USD)'] != 'N/A' else 0.0
        }
        
        return specs 