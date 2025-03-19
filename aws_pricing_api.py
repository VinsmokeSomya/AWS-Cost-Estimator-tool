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
        """Initialize the AWS Pricing API client."""
        self.region = region
        self.client = boto3.client('pricing', region_name='us-east-1')  # Pricing API is only available in us-east-1
        self.pricing_cache = {}

    def _get_pricing_data(self, service_code: str, filters: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Get pricing data from AWS Pricing API."""
        try:
            response = self.client.get_products(
                ServiceCode=service_code,
                Filters=filters
            )
            return response.get('PriceList', [])
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDeniedException':
                logging.error(f"Access denied to AWS Pricing API. Please ensure your IAM user has the following permissions:\n"
                            f"{{\n"
                            f"    \"Version\": \"2012-10-17\",\n"
                            f"    \"Statement\": [\n"
                            f"        {{\n"
                            f"            \"Effect\": \"Allow\",\n"
                            f"            \"Action\": [\n"
                            f"                \"pricing:GetProducts\",\n"
                            f"                \"pricing:DescribeServices\",\n"
                            f"                \"pricing:GetAttributeValues\"\n"
                            f"            ],\n"
                            f"            \"Resource\": \"*\"\n"
                            f"        }}\n"
                            f"    ]\n"
                            f"}}")
            else:
                logging.error(f"Error fetching {self.region} pricing: {str(e)}")
            return []

    def get_ec2_price(self, instance_type: str) -> float:
        """Get EC2 instance price."""
        try:
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': 'Linux'},
                {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': 'Shared'},
                {'Type': 'TERM_MATCH', 'Field': 'capacitystatus', 'Value': 'Used'},
                {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': self.region},
                {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw', 'Value': 'NA'},
                {'Type': 'TERM_MATCH', 'Field': 'licenseModel', 'Value': 'No License required'},
                {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Compute Instance'}
            ]
            pricing_data = self._get_pricing_data('AmazonEC2', filters)
            if pricing_data:
                price_list = json.loads(pricing_data[0])
                terms = price_list.get('terms', {}).get('OnDemand', {})
                for term in terms.values():
                    price_dimensions = term.get('priceDimensions', {})
                    for dimension in price_dimensions.values():
                        hourly_price = float(dimension.get('pricePerUnit', {}).get('USD', 0))
                        return hourly_price * 24 * 30  # Convert to monthly price
            return 0.0
        except Exception as e:
            logging.error(f"Error getting EC2 price for {instance_type}: {str(e)}")
            return 0.0

    def get_rds_price(self, instance_type: str) -> float:
        """Get RDS instance price."""
        try:
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                {'Type': 'TERM_MATCH', 'Field': 'databaseEngine', 'Value': 'PostgreSQL'},
                {'Type': 'TERM_MATCH', 'Field': 'deploymentOption', 'Value': 'Single-AZ'},
                {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': self.region},
                {'Type': 'TERM_MATCH', 'Field': 'licenseModel', 'Value': 'PostgreSQL license'},
                {'Type': 'TERM_MATCH', 'Field': 'databaseEdition', 'Value': 'Standard'},
                {'Type': 'TERM_MATCH', 'Field': 'databaseVersion', 'Value': '13.7'},
                {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Database Instance'}
            ]
            pricing_data = self._get_pricing_data('AmazonRDS', filters)
            if pricing_data:
                price_list = json.loads(pricing_data[0])
                terms = price_list.get('terms', {}).get('OnDemand', {})
                for term in terms.values():
                    price_dimensions = term.get('priceDimensions', {})
                    for dimension in price_dimensions.values():
                        hourly_price = float(dimension.get('pricePerUnit', {}).get('USD', 0))
                        return hourly_price * 24 * 30  # Convert to monthly price
            return 0.0
        except Exception as e:
            logging.error(f"Error getting RDS price for {instance_type}: {str(e)}")
            return 0.0

    def get_lambda_price(self, memory_mb: float, duration_ms: float, requests_per_month: int) -> float:
        """Get Lambda function price."""
        try:
            # Get compute price per GB-second
            compute_filters = [
                {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': self.region},
                {'Type': 'TERM_MATCH', 'Field': 'group', 'Value': 'AWS-Lambda-Duration'},
                {'Type': 'TERM_MATCH', 'Field': 'groupDescription', 'Value': 'Lambda Duration'},
                {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': 'Lambda-GB-Second'},
                {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Serverless'}
            ]
            
            # Get request price per million requests
            request_filters = [
                {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': self.region},
                {'Type': 'TERM_MATCH', 'Field': 'group', 'Value': 'AWS-Lambda-Requests'},
                {'Type': 'TERM_MATCH', 'Field': 'groupDescription', 'Value': 'Lambda Requests'},
                {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': 'Lambda-Request'},
                {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Serverless'}
            ]
            
            compute_price = self._get_price_from_filters('AWSLambda', compute_filters)
            request_price = self._get_price_from_filters('AWSLambda', request_filters)
            
            # Calculate costs
            gb_seconds = (memory_mb / 1024) * (duration_ms / 1000) * requests_per_month
            compute_cost = gb_seconds * compute_price
            request_cost = (requests_per_month / 1000000) * request_price
            
            return compute_cost + request_cost
        except Exception as e:
            logging.error(f"Error getting Lambda price: {str(e)}")
            return 0.0

    def get_s3_price(self, storage_gb: float, requests_per_month: int) -> float:
        """Get S3 storage and request price."""
        try:
            # Get storage price per GB-month
            storage_filters = [
                {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': self.region},
                {'Type': 'TERM_MATCH', 'Field': 'storageClass', 'Value': 'General Purpose'},
                {'Type': 'TERM_MATCH', 'Field': 'volumeType', 'Value': 'Storage'},
                {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': 'StorageObjectCount'},
                {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Storage'},
                {'Type': 'TERM_MATCH', 'Field': 'serviceCode', 'Value': 'AmazonS3'},
                {'Type': 'TERM_MATCH', 'Field': 'storageClass', 'Value': 'Standard'}
            ]
            
            # Get request price per 1000 requests
            request_filters = [
                {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': self.region},
                {'Type': 'TERM_MATCH', 'Field': 'requestType', 'Value': 'PUT'},
                {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': 'Requests-Tier2'},
                {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'API Request'},
                {'Type': 'TERM_MATCH', 'Field': 'serviceCode', 'Value': 'AmazonS3'}
            ]
            
            storage_price = self._get_price_from_filters('AmazonS3', storage_filters)
            request_price = self._get_price_from_filters('AmazonS3', request_filters)
            
            total_storage_cost = storage_gb * storage_price
            total_request_cost = (requests_per_month / 1000) * request_price
            
            return total_storage_cost + total_request_cost
        except Exception as e:
            logging.error(f"Error getting S3 price: {str(e)}")
            return 0.0

    def get_dynamodb_price(self, read_capacity: int, write_capacity: int, storage_gb: float) -> float:
        """Get DynamoDB price."""
        try:
            # Get storage price per GB-month
            storage_filters = [
                {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': self.region},
                {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': 'StorageByteHrs'}
            ]
            
            # Get read capacity price per RCU-hour
            read_filters = [
                {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': self.region},
                {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': 'ReadRequestUnitHrs'}
            ]
            
            # Get write capacity price per WCU-hour
            write_filters = [
                {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': self.region},
                {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': 'WriteRequestUnitHrs'}
            ]
            
            storage_price = self._get_price_from_filters('AmazonDynamoDB', storage_filters)
            read_price = self._get_price_from_filters('AmazonDynamoDB', read_filters)
            write_price = self._get_price_from_filters('AmazonDynamoDB', write_filters)
            
            monthly_read_cost = read_capacity * read_price * 24 * 30
            monthly_write_cost = write_capacity * write_price * 24 * 30
            monthly_storage_cost = storage_gb * storage_price
            
            return monthly_read_cost + monthly_write_cost + monthly_storage_cost
        except Exception as e:
            logging.error(f"Error getting DynamoDB price: {str(e)}")
            return 0.0

    def get_route53_price(self, queries_per_month: int) -> float:
        """Get Route53 price."""
        try:
            # Get hosted zone price
            zone_filters = [
                {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': 'HostedZone'}
            ]
            
            # Get query price per million queries
            query_filters = [
                {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': 'QueryHrs'}
            ]
            
            zone_price = self._get_price_from_filters('AmazonRoute53', zone_filters)
            query_price = self._get_price_from_filters('AmazonRoute53', query_filters)
            
            total_query_cost = (queries_per_month / 1000000) * query_price
            
            return zone_price + total_query_cost
        except Exception as e:
            logging.error(f"Error getting Route53 price: {str(e)}")
            return 0.0

    def get_cloudfront_price(self, data_transfer_gb: float, requests_per_month: int) -> float:
        """Get CloudFront price."""
        try:
            # Get data transfer price per GB
            transfer_filters = [
                {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': 'DataTransfer-Out-Bytes'},
                {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': 'us-east-1'},  # CloudFront prices are in us-east-1
                {'Type': 'TERM_MATCH', 'Field': 'operation', 'Value': 'DataTransfer-Out-Bytes'},
                {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Data Transfer'},
                {'Type': 'TERM_MATCH', 'Field': 'transferType', 'Value': 'CloudFront-Out-Bytes'}
            ]
            
            # Get request price per 10,000 requests
            request_filters = [
                {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': 'Requests-Tier1'},
                {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': 'us-east-1'},  # CloudFront prices are in us-east-1
                {'Type': 'TERM_MATCH', 'Field': 'operation', 'Value': 'Requests-Tier1'},
                {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Request'},
                {'Type': 'TERM_MATCH', 'Field': 'requestType', 'Value': 'CloudFront-Request-Tier1'}
            ]
            
            transfer_price = self._get_price_from_filters('AmazonCloudFront', transfer_filters)
            request_price = self._get_price_from_filters('AmazonCloudFront', request_filters)
            
            total_data_cost = data_transfer_gb * transfer_price
            total_request_cost = (requests_per_month / 10000) * request_price
            
            return total_data_cost + total_request_cost
        except Exception as e:
            logging.error(f"Error getting CloudFront price: {str(e)}")
            return 0.0

    def get_sns_price(self, messages_per_month: int) -> float:
        """Get SNS price."""
        try:
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': 'Requests-Tier1'}
            ]
            
            price_per_million = self._get_price_from_filters('AmazonSNS', filters)
            return (messages_per_month / 1000000) * price_per_million
        except Exception as e:
            logging.error(f"Error getting SNS price: {str(e)}")
            return 0.0

    def get_elasticache_price(self, instance_type: str) -> float:
        """Get ElastiCache price."""
        try:
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': self.region}
            ]
            pricing_data = self._get_pricing_data('AmazonElastiCache', filters)
            if pricing_data:
                price_list = json.loads(pricing_data[0])
                terms = price_list.get('terms', {}).get('OnDemand', {})
                for term in terms.values():
                    price_dimensions = term.get('priceDimensions', {})
                    for dimension in price_dimensions.values():
                        return float(dimension.get('pricePerUnit', {}).get('USD', 0))
            return 0.0
        except Exception as e:
            logging.error(f"Error getting ElastiCache price for {instance_type}: {str(e)}")
            return 0.0

    def get_config_price(self, config_items: int, rule_evaluations: int) -> float:
        """Get AWS Config price."""
        try:
            # Get config item price
            item_filters = [
                {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': 'ConfigurationItemRecord'}
            ]
            
            # Get rule evaluation price
            rule_filters = [
                {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': 'RuleEvaluation'}
            ]
            
            item_price = self._get_price_from_filters('AWSConfig', item_filters)
            rule_price = self._get_price_from_filters('AWSConfig', rule_filters)
            
            monthly_item_cost = config_items * item_price
            monthly_rule_cost = rule_evaluations * rule_price
            
            return monthly_item_cost + monthly_rule_cost
        except Exception as e:
            logging.error(f"Error getting Config price: {str(e)}")
            return 0.0

    def get_vpc_price(self) -> float:
        """Get VPC price."""
        # VPC itself is free, costs are only incurred for resources within it
        return 0.0

    def _get_price_from_filters(self, service_code: str, filters: List[Dict[str, str]]) -> float:
        """Helper method to get price from filters"""
        try:
            pricing_data = self._get_pricing_data(service_code, filters)
            if pricing_data:
                price_list = json.loads(pricing_data[0])
                terms = price_list.get('terms', {}).get('OnDemand', {})
                for term in terms.values():
                    price_dimensions = term.get('priceDimensions', {})
                    for dimension in price_dimensions.values():
                        return float(dimension.get('pricePerUnit', {}).get('USD', 0))
            return 0.0
        except Exception as e:
            logging.error(f"Error getting price from filters: {str(e)}")
            return 0.0

    def get_instance_specifications(self, instance_type: str) -> Dict[str, Any]:
        """Get EC2 instance specifications from AWS API."""
        try:
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': self.region}
            ]
            pricing_data = self._get_pricing_data('AmazonEC2', filters)
            if pricing_data:
                price_list = json.loads(pricing_data[0])
                attributes = price_list.get('product', {}).get('attributes', {})
                memory_str = attributes.get('memory', '0 GiB')
                memory_value = float(memory_str.split()[0])  # Extract numeric value
                return {
                    'vCPU': int(attributes.get('vcpu', 0)),
                    'memory': f"{memory_value} GiB",
                    'network_bandwidth': attributes.get('networkPerformance', 'Unknown'),
                    'storage': attributes.get('storage', 'EBS only'),
                    'sku': price_list.get('product', {}).get('sku', 'Unknown')
                }
            return {}
        except Exception as e:
            logging.error(f"Error getting EC2 specifications: {str(e)}")
            return {}

    def get_rds_specifications(self, instance_type: str) -> Dict[str, Any]:
        """Get RDS instance specifications from AWS API."""
        try:
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': self.region}
            ]
            pricing_data = self._get_pricing_data('AmazonRDS', filters)
            if pricing_data:
                price_list = json.loads(pricing_data[0])
                attributes = price_list.get('product', {}).get('attributes', {})
                memory_str = attributes.get('memory', '0 GiB')
                memory_value = float(memory_str.split()[0])  # Extract numeric value
                storage_str = attributes.get('storage', 'EBS Only')
                try:
                    storage_value = float(storage_str.split()[0]) if storage_str != 'EBS Only' else 20  # Default to 20GB for EBS
                except (ValueError, IndexError):
                    storage_value = 20  # Default to 20GB if parsing fails
                return {
                    'vCPU': int(attributes.get('vcpu', 0)),
                    'memory': f"{memory_value} GiB",
                    'storage': f"{storage_value} GB",
                    'engine': attributes.get('databaseEngine', 'Unknown'),
                    'sku': price_list.get('product', {}).get('sku', 'Unknown')
                }
            return {}
        except Exception as e:
            logging.error(f"Error getting RDS specifications: {str(e)}")
            return {}

    def get_s3_specifications(self) -> Dict[str, Any]:
        """Get S3 specifications from AWS API."""
        try:
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': self.region},
                {'Type': 'TERM_MATCH', 'Field': 'storageClass', 'Value': 'General Purpose'}
            ]
            pricing_data = self._get_pricing_data('AmazonS3', filters)
            if pricing_data:
                price_list = json.loads(pricing_data[0])
                terms = price_list.get('terms', {}).get('OnDemand', {})
                for term in terms.values():
                    price_dimensions = term.get('priceDimensions', {})
                    for dimension in price_dimensions.values():
                        price_per_unit = dimension.get('pricePerUnit', {}).get('USD', 0)
                        return {
                            'storage_price_per_gb': f"${float(price_per_unit):.4f}",
                            'request_price_per_1000': f"${float(price_per_unit) * 1000:.4f}",
                            'storage_class': 'Standard',
                            'sku': price_list.get('product', {}).get('sku', 'Unknown')
                        }
            return {}
        except Exception as e:
            logging.error(f"Error getting S3 specifications: {str(e)}")
            return {}

    def get_elasticache_specifications(self, instance_type: str) -> Dict[str, Any]:
        """Get ElastiCache instance specifications from AWS API."""
        try:
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': self.region}
            ]
            pricing_data = self._get_pricing_data('AmazonElastiCache', filters)
            if pricing_data:
                price_list = json.loads(pricing_data[0])
                attributes = price_list.get('product', {}).get('attributes', {})
                memory_str = attributes.get('memory', '0 GiB')
                memory_value = float(memory_str.split()[0])  # Extract numeric value
                return {
                    'vCPU': int(attributes.get('vcpu', 0)),
                    'memory': f"{memory_value} GiB",
                    'network_bandwidth': attributes.get('networkPerformance', 'Unknown'),
                    'engine': attributes.get('cacheEngine', 'Unknown'),
                    'sku': price_list.get('product', {}).get('sku', 'Unknown')
                }
            return {}
        except Exception as e:
            logging.error(f"Error getting ElastiCache specifications: {str(e)}")
            return {}

    def get_route53_specifications(self) -> Dict[str, Any]:
        """Get Route53 specifications from AWS API."""
        try:
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': 'HostedZone'}
            ]
            pricing_data = self._get_pricing_data('AmazonRoute53', filters)
            if pricing_data:
                price_list = json.loads(pricing_data[0])
                terms = price_list.get('terms', {}).get('OnDemand', {})
                for term in terms.values():
                    price_dimensions = term.get('priceDimensions', {})
                    for dimension in price_dimensions.values():
                        hosted_zone_price = dimension.get('pricePerUnit', {}).get('USD', 0)
                        return {
                            'hosted_zone': f"${float(hosted_zone_price):.2f} per zone",
                            'queries': f"${float(hosted_zone_price) * 0.0004:.4f} per query",
                            'sku': price_list.get('product', {}).get('sku', 'Unknown')
                        }
            return {}
        except Exception as e:
            logging.error(f"Error getting Route53 specifications: {str(e)}")
            return {}

    def get_cloudfront_specifications(self) -> Dict[str, Any]:
        """Get CloudFront specifications from AWS API."""
        try:
            # Get data transfer pricing
            transfer_filters = [
                {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': 'DataTransfer-Out-Bytes'},
                {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': 'us-east-1'},  # CloudFront prices are in us-east-1
                {'Type': 'TERM_MATCH', 'Field': 'operation', 'Value': 'DataTransfer-Out-Bytes'},
                {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Data Transfer'},
                {'Type': 'TERM_MATCH', 'Field': 'transferType', 'Value': 'CloudFront-Out-Bytes'}
            ]
            transfer_data = self._get_pricing_data('AmazonCloudFront', transfer_filters)
            
            # Get request pricing
            request_filters = [
                {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': 'Requests-Tier1'},
                {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': 'us-east-1'},  # CloudFront prices are in us-east-1
                {'Type': 'TERM_MATCH', 'Field': 'operation', 'Value': 'Requests-Tier1'},
                {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Request'},
                {'Type': 'TERM_MATCH', 'Field': 'requestType', 'Value': 'CloudFront-Request-Tier1'}
            ]
            request_data = self._get_pricing_data('AmazonCloudFront', request_filters)
            
            specs = {
                'data_transfer': 'Unknown',
                'requests': 'Unknown',
                'edge_locations': '225+ globally',
                'ssl_certificates': 'Free with CloudFront',
                'cache_behavior': 'Customizable',
                'origin_types': ['S3', 'EC2', 'ELB', 'Custom Origin'],
                'features': ['DDoS Protection', 'WAF Integration', 'Field-Level Encryption'],
                'sku': 'Unknown'
            }
            
            if transfer_data:
                price_list = json.loads(transfer_data[0])
                terms = price_list.get('terms', {}).get('OnDemand', {})
                for term in terms.values():
                    price_dimensions = term.get('priceDimensions', {})
                    for dimension in price_dimensions.values():
                        transfer_price = dimension.get('pricePerUnit', {}).get('USD', 0)
                        specs['data_transfer'] = f"${float(transfer_price):.3f} per GB"
                        specs['sku'] = price_list.get('product', {}).get('sku', 'Unknown')
                        break
                    break
            
            if request_data:
                price_list = json.loads(request_data[0])
                terms = price_list.get('terms', {}).get('OnDemand', {})
                for term in terms.values():
                    price_dimensions = term.get('priceDimensions', {})
                    for dimension in price_dimensions.values():
                        request_price = dimension.get('pricePerUnit', {}).get('USD', 0)
                        specs['requests'] = f"${float(request_price):.4f} per request"
                        break
                    break
            
            return specs
        except Exception as e:
            logging.error(f"Error getting CloudFront specifications: {str(e)}")
            return {}

    def get_lambda_specifications(self) -> Dict[str, Any]:
        """Get Lambda specifications from AWS API."""
        try:
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'group', 'Value': 'AWS-Lambda-Duration'}
            ]
            pricing_data = self._get_pricing_data('AWSLambda', filters)
            if pricing_data:
                price_list = json.loads(pricing_data[0])
                terms = price_list.get('terms', {}).get('OnDemand', {})
                for term in terms.values():
                    price_dimensions = term.get('priceDimensions', {})
                    for dimension in price_dimensions.values():
                        compute_price = dimension.get('pricePerUnit', {}).get('USD', 0)
                        return {
                            'memory': '128 MB to 10,240 MB',
                            'timeout': 'Up to 15 minutes',
                            'runtime': 'Multiple supported',
                            'compute_price': f"${float(compute_price):.6f} per GB-second",
                            'sku': price_list.get('product', {}).get('sku', 'Unknown')
                        }
            return {}
        except Exception as e:
            logging.error(f"Error getting Lambda specifications: {str(e)}")
            return {}

    def get_sns_specifications(self) -> Dict[str, Any]:
        """Get SNS specifications from AWS API."""
        try:
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': 'Requests-Tier1'}
            ]
            pricing_data = self._get_pricing_data('AmazonSNS', filters)
            if pricing_data:
                price_list = json.loads(pricing_data[0])
                terms = price_list.get('terms', {}).get('OnDemand', {})
                for term in terms.values():
                    price_dimensions = term.get('priceDimensions', {})
                    for dimension in price_dimensions.values():
                        message_price = dimension.get('pricePerUnit', {}).get('USD', 0)
                        return {
                            'message_price': f"${float(message_price):.6f} per message",
                            'delivery_protocols': ['HTTP/HTTPS', 'Email', 'SMS', 'Mobile Push'],
                            'sku': price_list.get('product', {}).get('sku', 'Unknown')
                        }
            return {}
        except Exception as e:
            logging.error(f"Error getting SNS specifications: {str(e)}")
            return {}

    def get_config_specifications(self) -> Dict[str, Any]:
        """Get AWS Config specifications from AWS API."""
        try:
            # Get configuration item pricing
            item_filters = [
                {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': 'ConfigurationItemRecord'},
                {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': self.region},
                {'Type': 'TERM_MATCH', 'Field': 'deploymentOption', 'Value': 'Regional'},
                {'Type': 'TERM_MATCH', 'Field': 'operation', 'Value': 'ConfigurationItemRecord'},
                {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'AWS Config'}
            ]
            item_data = self._get_pricing_data('AWSConfig', item_filters)
            
            # Get rule evaluation pricing
            rule_filters = [
                {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': 'ConfigRuleEvaluation'},
                {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': self.region},
                {'Type': 'TERM_MATCH', 'Field': 'deploymentOption', 'Value': 'Regional'},
                {'Type': 'TERM_MATCH', 'Field': 'operation', 'Value': 'ConfigRuleEvaluation'},
                {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'AWS Config'}
            ]
            rule_data = self._get_pricing_data('AWSConfig', rule_filters)
            
            specs = {
                'config_item_price': 'Unknown',
                'rule_evaluation_price': 'Unknown',
                'monitored_resources': [
                    'EC2', 'S3', 'RDS', 'IAM', 'VPC', 'Lambda', 'CloudFront',
                    'DynamoDB', 'ElastiCache', 'SNS', 'CloudWatch'
                ],
                'features': [
                    'Multi-Account Support',
                    'Conformance Packs',
                    'Organization Rules',
                    'Custom Rules'
                ],
                'compliance_frameworks': [
                    'CIS AWS Foundations',
                    'PCI DSS',
                    'HIPAA',
                    'SOC 2'
                ],
                'sku': 'Unknown'
            }
            
            if item_data:
                price_list = json.loads(item_data[0])
                terms = price_list.get('terms', {}).get('OnDemand', {})
                for term in terms.values():
                    price_dimensions = term.get('priceDimensions', {})
                    for dimension in price_dimensions.values():
                        item_price = dimension.get('pricePerUnit', {}).get('USD', 0)
                        specs['config_item_price'] = f"${float(item_price):.4f} per item"
                        specs['sku'] = price_list.get('product', {}).get('sku', 'Unknown')
                        break
                    break
            
            if rule_data:
                price_list = json.loads(rule_data[0])
                terms = price_list.get('terms', {}).get('OnDemand', {})
                for term in terms.values():
                    price_dimensions = term.get('priceDimensions', {})
                    for dimension in price_dimensions.values():
                        rule_price = dimension.get('pricePerUnit', {}).get('USD', 0)
                        specs['rule_evaluation_price'] = f"${float(rule_price):.4f} per evaluation"
                        break
                    break
            
            return specs
        except Exception as e:
            logging.error(f"Error getting Config specifications: {str(e)}")
            return {}

    def get_vpc_specifications(self) -> Dict[str, Any]:
        """Get VPC specifications from AWS API."""
        try:
            return {
                'features': ['NAT Gateway', 'Internet Gateway', 'VPC Endpoints'],
                'network_features': ['VPC Peering', 'Transit Gateway', 'Direct Connect'],
                'security_features': ['Security Groups', 'Network ACLs', 'Flow Logs'],
                'sku': 'VPC-Base'  # VPC itself doesn't have a SKU as it's free
            }
        except Exception as e:
            logging.error(f"Error getting VPC specifications: {str(e)}")
            return {} 