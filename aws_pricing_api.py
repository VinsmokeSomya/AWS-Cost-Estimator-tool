import boto3
import json
import logging
from typing import Dict, List, Any
from dotenv import load_dotenv
import os
from botocore.exceptions import ClientError

# Load environment variables
load_dotenv()

class AWSPricingAPI:
    def __init__(self, region: str = 'ap-south-1'):
        self.region = region
        self.client = boto3.client('pricing', region_name='us-east-1')
        self.pricing_cache = {}

    def _get_pricing_data(self, service_code: str, filters: list) -> list:
        """Helper method to get pricing data from AWS API"""
        try:
            response = self.client.get_products(
                ServiceCode=service_code,
                Filters=filters,
                MaxResults=100
            )
            return response.get('PriceList', [])
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDeniedException':
                logging.error(f"""
Access denied when fetching {service_code} pricing. Please add these permissions to your IAM user:

{
    "Version": "2012-10-17",
    "Statement": [
        {{
            "Effect": "Allow",
            "Action": [
                "pricing:GetProducts",
                "pricing:DescribeServices",
                "pricing:GetAttributeValues"
            ],
            "Resource": "*"
        }}
    ]
}

Steps to add the policy:
1. Go to AWS IAM Console
2. Select your user (EC2Admin)
3. Click "Add permissions"
4. Choose "Attach policies directly"
5. Click "Create policy"
6. Switch to JSON editor
7. Paste the policy above
8. Click "Review policy"
9. Name it "AWSPricingAPIAccess"
10. Click "Create policy"
11. Attach the policy to your user

Note: It may take a few minutes for the permissions to take effect.
""")
            else:
                logging.error(f"Error fetching {service_code} pricing: {str(e)}")
            return []

    def get_ec2_price(self, instance_type: str) -> float:
        """Get EC2 instance price"""
        filters = [
            {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': 'Linux'},
            {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': 'Shared'},
            {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': self.region},
            {'Type': 'TERM_MATCH', 'Field': 'capacitystatus', 'Value': 'Used'},
            {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw', 'Value': 'NA'},
            {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type}
        ]
        
        price_list = self._get_pricing_data('AmazonEC2', filters)
        for price in price_list:
            price_data = json.loads(price)
            for term in price_data.get('terms', {}).get('OnDemand', {}).values():
                for price_dimension in term.get('priceDimensions', {}).values():
                    return float(price_dimension.get('pricePerUnit', {}).get('USD', 0))
        return 0.0

    def get_rds_price(self, instance_type: str, engine: str = 'MySQL') -> float:
        """Get RDS instance price"""
        filters = [
            {'Type': 'TERM_MATCH', 'Field': 'databaseEngine', 'Value': engine},
            {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': self.region},
            {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type}
        ]
        
        price_list = self._get_pricing_data('AmazonRDS', filters)
        for price in price_list:
            price_data = json.loads(price)
            for term in price_data.get('terms', {}).get('OnDemand', {}).values():
                for price_dimension in term.get('priceDimensions', {}).values():
                    return float(price_dimension.get('pricePerUnit', {}).get('USD', 0))
        return 0.0

    def get_lambda_price(self) -> Dict[str, float]:
        """Get Lambda prices"""
        filters = [
            {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': self.region},
            {'Type': 'TERM_MATCH', 'Field': 'group', 'Value': 'AWS-Lambda'},
            {'Type': 'TERM_MATCH', 'Field': 'groupDescription', 'Value': 'Request'}
        ]
        
        price_list = self._get_pricing_data('AWSLambda', filters)
        for price in price_list:
            price_data = json.loads(price)
            for term in price_data.get('terms', {}).get('OnDemand', {}).values():
                for price_dimension in term.get('priceDimensions', {}).values():
                    return {
                        'request_price': float(price_dimension.get('pricePerUnit', {}).get('USD', 0)),
                        'compute_price': float(price_dimension.get('pricePerUnit', {}).get('USD', 0))
                    }
        return {'request_price': 0.0, 'compute_price': 0.0}

    def get_s3_price(self) -> Dict[str, float]:
        """Get S3 prices"""
        storage_filters = [
            {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': self.region},
            {'Type': 'TERM_MATCH', 'Field': 'volumeType', 'Value': 'Standard'},
            {'Type': 'TERM_MATCH', 'Field': 'storageClass', 'Value': 'General Purpose'}
        ]
        
        request_filters = [
            {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': self.region},
            {'Type': 'TERM_MATCH', 'Field': 'group', 'Value': 'S3-API-Request'},
            {'Type': 'TERM_MATCH', 'Field': 'operation', 'Value': 'GetObject'}
        ]
        
        storage_prices = self._get_pricing_data('AmazonS3', storage_filters)
        request_prices = self._get_pricing_data('AmazonS3', request_filters)
        
        storage_price = 0.0
        request_price = 0.0
        
        for price in storage_prices:
            price_data = json.loads(price)
            for term in price_data.get('terms', {}).get('OnDemand', {}).values():
                for price_dimension in term.get('priceDimensions', {}).values():
                    storage_price = float(price_dimension.get('pricePerUnit', {}).get('USD', 0))
        
        for price in request_prices:
            price_data = json.loads(price)
            for term in price_data.get('terms', {}).get('OnDemand', {}).values():
                for price_dimension in term.get('priceDimensions', {}).values():
                    request_price = float(price_dimension.get('pricePerUnit', {}).get('USD', 0))
        
        return {'storage_price': storage_price, 'request_price': request_price}

    def get_elasticache_price(self, instance_type: str) -> float:
        """Get ElastiCache price"""
        filters = [
            {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': self.region},
            {'Type': 'TERM_MATCH', 'Field': 'cacheEngine', 'Value': 'Redis'},
            {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type}
        ]
        
        price_list = self._get_pricing_data('AmazonElastiCache', filters)
        for price in price_list:
            price_data = json.loads(price)
            for term in price_data.get('terms', {}).get('OnDemand', {}).values():
                for price_dimension in term.get('priceDimensions', {}).values():
                    return float(price_dimension.get('pricePerUnit', {}).get('USD', 0))
        return 0.0

    def get_dynamodb_price(self) -> Dict[str, float]:
        """Get DynamoDB prices"""
        filters = [
            {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': self.region},
            {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': 'DynamoDBReadCapacityUnit'},
            {'Type': 'TERM_MATCH', 'Field': 'operation', 'Value': 'Read'}
        ]
        
        try:
            response = self.client.get_products(
                ServiceCode='AmazonDynamoDB',
                Filters=filters,
                MaxResults=1
            )
            
            if response.get('PriceList'):
                price_data = json.loads(response['PriceList'][0])
                for term in price_data.get('terms', {}).get('OnDemand', {}).values():
                    for price_dimension in term.get('priceDimensions', {}).values():
                        return {
                            'read_capacity': float(price_dimension.get('pricePerUnit', {}).get('USD', 0)),
                            'write_capacity': 0.0,  # Add write capacity price calculation if needed
                            'storage_price': 0.0    # Add storage price calculation if needed
                        }
            return {'read_capacity': 0.0, 'write_capacity': 0.0, 'storage_price': 0.0}
        except Exception as e:
            logging.error(f"Error getting DynamoDB price: {str(e)}")
            return {'read_capacity': 0.0, 'write_capacity': 0.0, 'storage_price': 0.0}

    def get_route53_price(self) -> Dict[str, float]:
        """Get Route53 prices"""
        try:
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': self.region},
                {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': 'HostedZone'},
                {'Type': 'TERM_MATCH', 'Field': 'operation', 'Value': 'HostedZone'}
            ]
            
            price_list = self._get_pricing_data('AmazonRoute53', filters)
            if not price_list:
                return {'hosted_zone': 0.50, 'query_price': 0.0004}
                
            for price in price_list:
                price_data = json.loads(price)
                for term in price_data.get('terms', {}).get('OnDemand', {}).values():
                    for price_dimension in term.get('priceDimensions', {}).values():
                        return {
                            'hosted_zone': float(price_dimension.get('pricePerUnit', {}).get('USD', 0)),
                            'query_price': float(price_dimension.get('pricePerUnit', {}).get('USD', 0))
                        }
            
            return {'hosted_zone': 0.50, 'query_price': 0.0004}
        except Exception as e:
            logging.error(f"Error getting Route53 price: {str(e)}")
            return {'hosted_zone': 0.50, 'query_price': 0.0004}

    def get_cloudfront_price(self) -> Dict[str, float]:
        """Get CloudFront prices"""
        try:
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': self.region},
                {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': 'DataTransfer-Out-Bytes'},
                {'Type': 'TERM_MATCH', 'Field': 'operation', 'Value': 'DataTransfer-Out'}
            ]
            
            price_list = self._get_pricing_data('AmazonCloudFront', filters)
            if not price_list:
                return {'data_transfer': 0.085, 'request_price': 0.0001}
                
            for price in price_list:
                price_data = json.loads(price)
                for term in price_data.get('terms', {}).get('OnDemand', {}).values():
                    for price_dimension in term.get('priceDimensions', {}).values():
                        return {
                            'data_transfer': float(price_dimension.get('pricePerUnit', {}).get('USD', 0)),
                            'request_price': float(price_dimension.get('pricePerUnit', {}).get('USD', 0))
                        }
            
            return {'data_transfer': 0.085, 'request_price': 0.0001}
        except Exception as e:
            logging.error(f"Error getting CloudFront price: {str(e)}")
            return {'data_transfer': 0.085, 'request_price': 0.0001}

    def get_sns_price(self) -> Dict[str, float]:
        """Get SNS prices"""
        filters = [
            {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': self.region},
            {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': 'Notification'},
            {'Type': 'TERM_MATCH', 'Field': 'operation', 'Value': 'Notification'}
        ]
        
        try:
            response = self.client.get_products(
                ServiceCode='AmazonSNS',
                Filters=filters,
                MaxResults=1
            )
            
            if response.get('PriceList'):
                price_data = json.loads(response['PriceList'][0])
                for term in price_data.get('terms', {}).get('OnDemand', {}).values():
                    for price_dimension in term.get('priceDimensions', {}).values():
                        return {
                            'notification_price': float(price_dimension.get('pricePerUnit', {}).get('USD', 0))
                        }
            return {'notification_price': 0.0}
        except Exception as e:
            logging.error(f"Error getting SNS price: {str(e)}")
            return {'notification_price': 0.0}

    def get_config_price(self) -> Dict[str, float]:
        """Get AWS Config prices"""
        try:
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': self.region},
                {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': 'ConfigItem'},
                {'Type': 'TERM_MATCH', 'Field': 'operation', 'Value': 'ConfigItem'}
            ]
            
            price_list = self._get_pricing_data('AWSConfig', filters)
            if not price_list:
                return {'config_item': 0.003, 'rule_evaluation': 0.001}
                
            for price in price_list:
                price_data = json.loads(price)
                for term in price_data.get('terms', {}).get('OnDemand', {}).values():
                    for price_dimension in term.get('priceDimensions', {}).values():
                        return {
                            'config_item': float(price_dimension.get('pricePerUnit', {}).get('USD', 0)),
                            'rule_evaluation': float(price_dimension.get('pricePerUnit', {}).get('USD', 0))
                        }
            
            return {'config_item': 0.003, 'rule_evaluation': 0.001}
        except Exception as e:
            logging.error(f"Error getting AWS Config price: {str(e)}")
            return {'config_item': 0.003, 'rule_evaluation': 0.001} 