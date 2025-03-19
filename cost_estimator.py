import json
import os
import logging
from typing import Dict, Any, Optional, Iterator, List
import ijson  # For streaming JSON parsing
import boto3
from datetime import datetime
from aws_pricing_api import AWSPricingAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PricingDataLoader:
    def __init__(self, region: str = 'ap-south-1'):
        self.region = region
        self.pricing_api = AWSPricingAPI(region)
        self.pricing_cache = {
            'ec2': {},
            'rds': {},
            'lambda': {
                'request_price': 0.0,
                'compute_price': 0.0
            },
            's3': {
                'storage_price': 0.0,
                'request_price': 0.0
            },
            'dynamodb': {
                'storage_price': 0.0,
                'read_capacity': 0.0,
                'write_capacity': 0.0
            },
            'route53': {
                'hosted_zone': 0.0,
                'query_price': 0.0
            },
            'cloudfront': {
                'data_transfer': 0.0,
                'request_price': 0.0
            },
            'sns': {
                'notification_price': 0.0
            },
            'elasticache': {},
            'config': {
                'config_item': 0.0,
                'rule_evaluation': 0.0
            }
        }
        self._load_pricing_data()

    def _load_pricing_data(self):
        """Load pricing data from AWS Pricing API"""
        try:
            # Load EC2 prices
            self.pricing_cache['ec2']['t3.medium'] = self.pricing_api.get_ec2_price('t3.medium')
            
            # Load RDS prices
            self.pricing_cache['rds']['db.t3.medium'] = self.pricing_api.get_rds_price('db.t3.medium')
            
            # Load Lambda prices (using sample values to get base prices)
            lambda_cost = self.pricing_api.get_lambda_price(128, 100, 1000000)
            self.pricing_cache['lambda']['compute_price'] = lambda_cost / (128/1024 * 100/1000 * 1000000)
            self.pricing_cache['lambda']['request_price'] = lambda_cost / (1000000/1000000)
            
            # Load S3 prices (using sample values to get base prices)
            s3_cost = self.pricing_api.get_s3_price(100, 1000000)
            self.pricing_cache['s3']['storage_price'] = s3_cost / 100
            self.pricing_cache['s3']['request_price'] = s3_cost / (1000000/1000)
            
            # Load DynamoDB prices (using sample values to get base prices)
            dynamodb_cost = self.pricing_api.get_dynamodb_price(5, 5, 25)
            self.pricing_cache['dynamodb']['storage_price'] = dynamodb_cost / 25
            self.pricing_cache['dynamodb']['read_capacity'] = dynamodb_cost / (5 * 24 * 30)
            self.pricing_cache['dynamodb']['write_capacity'] = dynamodb_cost / (5 * 24 * 30)
            
            # Load Route53 prices (using sample values to get base prices)
            route53_cost = self.pricing_api.get_route53_price(1000000)
            self.pricing_cache['route53']['hosted_zone'] = route53_cost / 2  # Assuming half is hosted zone cost
            self.pricing_cache['route53']['query_price'] = route53_cost / (1000000/1000000)
            
            # Load CloudFront prices (using sample values to get base prices)
            cloudfront_cost = self.pricing_api.get_cloudfront_price(100, 1000000)
            self.pricing_cache['cloudfront']['data_transfer'] = cloudfront_cost / 100
            self.pricing_cache['cloudfront']['request_price'] = cloudfront_cost / (1000000/10000)
            
            # Load SNS prices (using sample values to get base prices)
            sns_cost = self.pricing_api.get_sns_price(1000000)
            self.pricing_cache['sns']['notification_price'] = sns_cost / (1000000/1000000)
            
            # Load ElastiCache prices
            self.pricing_cache['elasticache']['cache.t3.small'] = self.pricing_api.get_elasticache_price('cache.t3.small')
            
            # Load AWS Config prices (using sample values to get base prices)
            config_cost = self.pricing_api.get_config_price(100, 1000)
            self.pricing_cache['config']['config_item'] = config_cost / 100
            self.pricing_cache['config']['rule_evaluation'] = config_cost / 1000
            
        except Exception as e:
            logging.error(f"Error loading pricing data: {str(e)}")
            raise

    def get_ec2_instance_price(self, instance_type: str) -> float:
        """Get hourly price for EC2 instance type."""
        return self.pricing_cache['ec2'].get(instance_type, 0.0)

    def get_rds_price(self, instance_type: str) -> float:
        """Get hourly price for RDS instance type."""
        return self.pricing_cache['rds'].get(instance_type, 0.0)

    def get_lambda_prices(self) -> Dict[str, float]:
        """Get Lambda pricing (per GB-second and per request)."""
        return self.pricing_cache['lambda']

    def get_s3_prices(self) -> Dict[str, float]:
        """Get S3 pricing (storage, requests)."""
        return self.pricing_cache['s3']

    def get_dynamodb_prices(self) -> Dict[str, float]:
        """Get DynamoDB pricing."""
        return self.pricing_cache['dynamodb']

    def get_route53_prices(self) -> Dict[str, float]:
        """Get Route53 pricing."""
        return self.pricing_cache['route53']

    def get_cloudfront_prices(self) -> Dict[str, float]:
        """Get CloudFront pricing."""
        return self.pricing_cache['cloudfront']

    def get_lambda_compute_price(self) -> float:
        """Get Lambda compute price per GB-second."""
        return self.pricing_cache['lambda']['compute_price']

    def get_lambda_request_price(self) -> float:
        """Get Lambda request price per million requests."""
        return self.pricing_cache['lambda']['request_price']

    def get_s3_storage_price(self) -> float:
        """Get S3 storage price per GB-month."""
        return self.pricing_cache['s3']['storage_price']

    def get_s3_put_price(self) -> float:
        """Get S3 PUT request price per 1000 requests."""
        return self.pricing_cache['s3']['request_price']

    def get_dynamodb_storage_price(self) -> float:
        """Get DynamoDB storage price per GB-month."""
        return self.pricing_cache['dynamodb']['storage_price']

    def get_dynamodb_rcu_price(self) -> float:
        """Get DynamoDB read capacity unit price per RCU-hour."""
        return self.pricing_cache['dynamodb']['read_capacity']

    def get_dynamodb_wcu_price(self) -> float:
        """Get DynamoDB write capacity unit price per WCU-hour."""
        return self.pricing_cache['dynamodb']['write_capacity']

    def get_cloudfront_transfer_price(self) -> float:
        """Get CloudFront data transfer price per GB."""
        return self.pricing_cache['cloudfront']['data_transfer']

    def get_cloudfront_request_price(self) -> float:
        """Get CloudFront request price per 10,000 requests."""
        return self.pricing_cache['cloudfront']['request_price']

    def get_sns_price(self) -> float:
        """Get SNS price per million requests."""
        return self.pricing_cache['sns']['notification_price']

    def get_emr_service_charge(self) -> float:
        """Get EMR service charge percentage."""
        return self.pricing_cache['emr']['service_charge_percentage']

    def get_emr_pricing(self, instance_type):
        """Get EMR pricing for a specific instance type.
        Uses EC2 pricing as base and adds EMR service charge."""
        try:
            # Get base EC2 price for the instance
            base_price = self.get_ec2_instance_price(instance_type)
            if base_price == 0.0:
                logger.warning(f"Could not find EC2 pricing for EMR instance type {instance_type}")
                return 0.0
            
            # Calculate EMR service charge for this instance
            service_charge = base_price * self.pricing_cache['emr']['service_charge_percentage']
            
            # Total price is base price plus service charge
            total_price = base_price + service_charge
            logger.info(f"EMR pricing for {instance_type}: Base EC2 price ${base_price:.3f}/hr + Service charge ${service_charge:.3f}/hr = ${total_price:.3f}/hr")
            return total_price
        except Exception as e:
            logger.error(f"Error getting EMR pricing for {instance_type}: {str(e)}")
            return 0.0

    def get_elasticache_instance_price(self, instance_type: str) -> float:
        """Get hourly price for ElastiCache instance type."""
        return self.pricing_cache['elasticache'].get(instance_type, 0.0)

    def get_config_prices(self) -> Dict[str, float]:
        """Get AWS Config pricing."""
        return self.pricing_cache['config']

class AWSCostEstimator:
    def __init__(self):
        """Initialize the cost estimator."""
        self.pricing_api = AWSPricingAPI()
        self.cache = {}

    def calculate_rds_cost(self, instance_type: str) -> float:
        """Calculate monthly cost for RDS instance."""
        try:
            hourly_price = self.pricing_api.get_rds_price(instance_type)
            monthly_cost = hourly_price * 24 * 30  # Assuming 30 days per month
            logging.info(f"RDS cost calculation: instance_type={instance_type}, monthly_cost=${monthly_cost:.2f}")
            return monthly_cost
        except Exception as e:
            logging.error(f"Error calculating RDS cost: {str(e)}")
            return 0.0

    def calculate_vpc_cost(self) -> float:
        """Calculate monthly cost for VPC."""
        # VPC itself is free, costs are only incurred for resources within it
        logging.info("VPC cost calculation: VPC itself is free")
        return 0.0

    def calculate_route53_cost(self) -> float:
        """Calculate monthly cost for Route53."""
        try:
            prices = self.pricing_api.get_route53_price()
            hosted_zone_cost = prices['hosted_zone']
            queries_cost = prices['query_price'] * 1000000  # Assuming 1M queries per month
            total_cost = hosted_zone_cost + queries_cost
            logging.info(f"Route53 cost calculation: hosted_zone_cost=${hosted_zone_cost:.2f}, queries_cost=${queries_cost:.2f}")
            return total_cost
        except Exception as e:
            logging.error(f"Error calculating Route53 cost: {str(e)}")
            return 0.0

    def estimate_costs(self, architecture):
        """Estimate costs for the given architecture."""
        try:
            costs = {}
            
            # Extract nodes from the architecture
            nodes = architecture.get('nodes', [])
            if not nodes:
                logging.warning("No nodes found in the architecture")
                return costs

            for node in nodes:
                service_type = node.get('type')
                if not service_type:
                    logging.warning(f"Service type not specified for node: {node}")
                    continue

                try:
                    if service_type == 'AmazonEC2':
                        costs['EC2'] = self._estimate_ec2_cost({
                            'config': {'instance_type': node.get('InstanceType', 't3.medium')}
                        })
                    elif service_type == 'AmazonRDS':
                        costs['RDS'] = self._estimate_rds_cost({
                            'config': {'instance_type': node.get('DBInstanceClass', 'db.t3.medium')}
                        })
                    elif service_type == 'AmazonS3':
                        costs['S3'] = self._estimate_s3_cost({
                            'config': {
                                'storage_gb': 100,  # Default value
                                'requests_per_month': 1000000  # Default value
                            }
                        })
                    elif service_type == 'AmazonElastiCache':
                        costs['ElastiCache'] = self._estimate_elasticache_cost({
                            'config': {'instance_type': node.get('InstanceType', 'cache.t3.small')}
                        })
                    elif service_type == 'AmazonRoute53':
                        costs['Route53'] = self._estimate_route53_cost({
                            'config': {'queries_per_month': 1000000}  # Default value
                        })
                    elif service_type == 'AmazonCloudFront':
                        costs['CloudFront'] = self._estimate_cloudfront_cost({
                            'config': {
                                'data_transfer_gb': 1000,  # Default value
                                'requests_per_month': 1000000  # Default value
                            }
                        })
                    elif service_type == 'AWSLambda':
                        memory_mb = float(node.get('Memory', '512').replace('MB', ''))
                        timeout_s = float(node.get('Timeout', '10').replace('s', ''))
                        costs['Lambda'] = self._estimate_lambda_cost({
                            'config': {
                                'memory_mb': memory_mb,
                                'duration_ms': timeout_s * 1000,
                                'requests_per_month': 1000000  # Default value
                            }
                        })
                    elif service_type == 'AmazonSNS':
                        costs['SNS'] = self._estimate_sns_cost({
                            'config': {'messages_per_month': 1000000}  # Default value
                        })
                    elif service_type == 'AWSConfig':
                        costs['AWS Config'] = self._estimate_config_cost({
                            'config': {
                                'config_items': 100000,  # Default value
                                'rule_evaluations': 100000  # Default value
                            }
                        })
                    elif service_type == 'AmazonVPC':
                        costs['VPC'] = self._estimate_vpc_cost({
                            'config': {'subnets': node.get('Subnets', '').split(' & ')}
                        })
                    elif service_type == 'AmazonDynamoDB':
                        throughput = node.get('Throughput', '5 Read / 5 Write')
                        read_cu = float(throughput.split('Read')[0].strip())
                        write_cu = float(throughput.split('/')[-1].split('Write')[0].strip())
                        costs['DynamoDB'] = self._estimate_dynamodb_cost({
                            'config': {
                                'read_capacity': read_cu,
                                'write_capacity': write_cu,
                                'storage_gb': 25  # Default value
                            }
                        })
                    else:
                        logging.warning(f"Unknown service type: {service_type}")
                except Exception as e:
                    logging.error(f"Error estimating cost for {service_type}: {str(e)}")
                    costs[service_type.replace('Amazon', '').replace('AWS', '')] = 0.0

            return costs
        except Exception as e:
            logging.error(f"Error in cost estimation: {str(e)}")
            return {}

    def calculate_ec2_cost(self, instance_type: str) -> float:
        """Calculate monthly cost for EC2 instance."""
        try:
            hourly_price = self.pricing_api.get_ec2_price(instance_type)
            monthly_cost = hourly_price * 24 * 30  # Assuming 30 days per month
            logging.info(f"EC2 cost calculation: instance_type={instance_type}, monthly_cost=${monthly_cost:.2f}")
            return monthly_cost
        except Exception as e:
            logging.error(f"Error calculating EC2 cost: {str(e)}")
            return 0.0

    def calculate_cloudfront_cost(self) -> float:
        """Calculate monthly cost for CloudFront."""
        try:
            data_transfer_gb = 100  # Assuming 100GB transfer per month
            requests = 1000000  # Assuming 1M requests per month
            return self.pricing_api.get_cloudfront_price(data_transfer_gb, requests)
        except Exception as e:
            logging.error(f"Error calculating CloudFront cost: {str(e)}")
            return 0.0

    def calculate_lambda_cost(self, node: dict) -> float:
        """Calculate monthly cost for Lambda function."""
        try:
            memory_mb = float(node.get('memory_mb', 128))
            duration_ms = float(node.get('duration_ms', 100))
            invocations = float(node.get('invocations', 1000000))
            return self.pricing_api.get_lambda_price(memory_mb, duration_ms, invocations)
        except Exception as e:
            logging.error(f"Error calculating Lambda cost: {str(e)}")
            return 0.0

    def calculate_s3_cost(self, node: dict) -> float:
        """Calculate monthly cost for S3 bucket."""
        try:
            storage_gb = float(node.get('storage_gb', 100))
            requests = float(node.get('requests', 1000000))
            return self.pricing_api.get_s3_price(storage_gb, requests)
        except Exception as e:
            logging.error(f"Error calculating S3 cost: {str(e)}")
            return 0.0

    def calculate_dynamodb_cost(self, node: dict) -> float:
        """Calculate monthly cost for DynamoDB table."""
        try:
            storage_gb = float(node.get('storage_gb', 25))
            read_capacity = float(node.get('read_capacity', 5))
            write_capacity = float(node.get('write_capacity', 5))
            return self.pricing_api.get_dynamodb_price(read_capacity, write_capacity, storage_gb)
        except Exception as e:
            logging.error(f"Error calculating DynamoDB cost: {str(e)}")
            return 0.0

    def calculate_sns_cost(self, node: dict) -> float:
        """Calculate monthly cost for SNS notifications."""
        try:
            notifications = float(node.get('notifications', 1000000))
            return self.pricing_api.get_sns_price(notifications)
        except Exception as e:
            logging.error(f"Error calculating SNS cost: {str(e)}")
            return 0.0

    def calculate_config_cost(self) -> float:
        """Calculate monthly cost for AWS Config."""
        try:
            config_items = 100  # Assuming 100 config items
            rule_evaluations = 1000  # Assuming 1000 rule evaluations per month
            return self.pricing_api.get_config_price(config_items, rule_evaluations)
        except Exception as e:
            logging.error(f"Error calculating AWS Config cost: {str(e)}")
            return 0.0

    def generate_detailed_cost_report(self, architecture: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed cost report with hourly, daily, and monthly costs"""
        costs = self.estimate_costs(architecture)
        
        # Calculate detailed costs for each service
        detailed_costs = {}
        
        # EC2 Costs
        if 'EC2' in costs:
            ec2_monthly = costs['EC2']
            instance_type = 't3.medium'  # Default instance type
            specs = self.pricing_api.get_instance_specifications(instance_type)
            detailed_costs['EC2'] = {
                'instance_type': instance_type,
                'hourly_cost': round(ec2_monthly / (30 * 24), 4),
                'daily_cost': round(ec2_monthly / 30, 4),
                'monthly_cost': round(ec2_monthly, 4),
                'specifications': specs
            }
        
        # RDS Costs
        if 'RDS' in costs:
            rds_monthly = costs['RDS']
            instance_type = 'db.t3.medium'  # Default instance type
            specs = self.pricing_api.get_rds_specifications(instance_type)
            detailed_costs['RDS'] = {
                'instance_type': instance_type,
                'hourly_cost': round(rds_monthly / (30 * 24), 4),
                'daily_cost': round(rds_monthly / 30, 4),
                'monthly_cost': round(rds_monthly, 4),
                'specifications': specs
            }
        
        # S3 Costs
        if 'S3' in costs:
            s3_monthly = costs['S3']
            specs = self.pricing_api.get_s3_specifications()
            detailed_costs['S3'] = {
                'storage_class': 'Standard',
                'hourly_cost': round(s3_monthly / (30 * 24), 4),
                'daily_cost': round(s3_monthly / 30, 4),
                'monthly_cost': round(s3_monthly, 4),
                'specifications': specs
            }
        
        # ElastiCache Costs
        if 'ElastiCache' in costs:
            elasticache_monthly = costs['ElastiCache']
            instance_type = 'cache.t3.small'  # Default instance type
            specs = self.pricing_api.get_elasticache_specifications(instance_type)
            detailed_costs['ElastiCache'] = {
                'instance_type': instance_type,
                'hourly_cost': round(elasticache_monthly / (30 * 24), 4),
                'daily_cost': round(elasticache_monthly / 30, 4),
                'monthly_cost': round(elasticache_monthly, 4),
                'specifications': specs
            }
        
        # Route53 Costs
        if 'Route53' in costs:
            route53_monthly = costs['Route53']
            specs = self.pricing_api.get_route53_specifications()
            detailed_costs['Route53'] = {
                'hourly_cost': round(route53_monthly / (30 * 24), 4),
                'daily_cost': round(route53_monthly / 30, 4),
                'monthly_cost': round(route53_monthly, 4),
                'specifications': specs
            }
        
        # CloudFront Costs
        if 'CloudFront' in costs:
            cloudfront_monthly = costs['CloudFront']
            specs = self.pricing_api.get_cloudfront_specifications()
            detailed_costs['CloudFront'] = {
                'hourly_cost': round(cloudfront_monthly / (30 * 24), 4),
                'daily_cost': round(cloudfront_monthly / 30, 4),
                'monthly_cost': round(cloudfront_monthly, 4),
                'specifications': specs
            }
        
        # Lambda Costs
        if 'Lambda' in costs:
            lambda_monthly = costs['Lambda']
            specs = self.pricing_api.get_lambda_specifications()
            detailed_costs['Lambda'] = {
                'hourly_cost': round(lambda_monthly / (30 * 24), 4),
                'daily_cost': round(lambda_monthly / 30, 4),
                'monthly_cost': round(lambda_monthly, 4),
                'specifications': specs
            }
        
        # SNS Costs
        if 'SNS' in costs:
            sns_monthly = costs['SNS']
            specs = self.pricing_api.get_sns_specifications()
            detailed_costs['SNS'] = {
                'hourly_cost': round(sns_monthly / (30 * 24), 4),
                'daily_cost': round(sns_monthly / 30, 4),
                'monthly_cost': round(sns_monthly, 4),
                'specifications': specs
            }
        
        # AWS Config Costs
        if 'AWS Config' in costs:
            config_monthly = costs['AWS Config']
            specs = self.pricing_api.get_config_specifications()
            detailed_costs['AWS Config'] = {
                'hourly_cost': round(config_monthly / (30 * 24), 4),
                'daily_cost': round(config_monthly / 30, 4),
                'monthly_cost': round(config_monthly, 4),
                'specifications': specs
            }
        
        # VPC is free
        specs = self.pricing_api.get_vpc_specifications()
        detailed_costs['VPC'] = {
            'hourly_cost': 0.0,
            'daily_cost': 0.0,
            'monthly_cost': 0.0,
            'specifications': specs
        }
        
        # Generate summary
        total_monthly = sum(cost['monthly_cost'] for cost in detailed_costs.values())
        
        return {
            'architecture_name': architecture.get('title', 'Multi-Tier Architecture'),
            'region': self.pricing_api.region,
            'generation_date': datetime.now().isoformat(),
            'total_monthly_cost': round(total_monthly, 4),
            'services': detailed_costs
        }

    def save_cost_report(self, architecture: Dict[str, Any], output_file: str = 'cost_report.json'):
        """Generate and save cost report to JSON file"""
        report = self.generate_detailed_cost_report(architecture)
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=4)
        
        logging.info(f"Cost report saved to {output_file}")
        return report

    def _estimate_vpc_cost(self, node):
        """Estimate VPC costs."""
        return self.pricing_api.get_vpc_price()

    def _estimate_route53_cost(self, node):
        """Estimate Route53 costs."""
        queries_per_month = node['config'].get('queries_per_month', 1000000)
        return self.pricing_api.get_route53_price(queries_per_month)

    def _estimate_cloudfront_cost(self, node):
        """Estimate CloudFront costs."""
        data_transfer_gb = node['config'].get('data_transfer_gb', 1000)
        requests_per_month = node['config'].get('requests_per_month', 1000000)
        return self.pricing_api.get_cloudfront_price(data_transfer_gb, requests_per_month)

    def _estimate_ec2_cost(self, node):
        """Estimate EC2 instance costs."""
        instance_type = node['config'].get('instance_type', 't3.medium')
        return self.pricing_api.get_ec2_price(instance_type)

    def _estimate_s3_cost(self, node):
        """Estimate S3 storage and request costs."""
        storage_gb = node['config'].get('storage_gb', 100)
        requests_per_month = node['config'].get('requests_per_month', 1000000)
        return self.pricing_api.get_s3_price(storage_gb, requests_per_month)

    def _estimate_rds_cost(self, node):
        """Estimate RDS instance costs."""
        instance_type = node['config'].get('instance_type', 'db.t3.medium')
        return self.pricing_api.get_rds_price(instance_type)

    def _estimate_dynamodb_cost(self, node):
        """Estimate DynamoDB costs."""
        read_capacity = node['config'].get('read_capacity', 5)
        write_capacity = node['config'].get('write_capacity', 5)
        storage_gb = node['config'].get('storage_gb', 25)
        return self.pricing_api.get_dynamodb_price(read_capacity, write_capacity, storage_gb)

    def _estimate_lambda_cost(self, node):
        """Estimate Lambda costs."""
        memory_mb = node['config'].get('memory_mb', 128)
        duration_ms = node['config'].get('duration_ms', 100)
        requests_per_month = node['config'].get('requests_per_month', 1000000)
        return self.pricing_api.get_lambda_price(memory_mb, duration_ms, requests_per_month)

    def _estimate_sns_cost(self, node):
        """Estimate SNS costs."""
        messages_per_month = node['config'].get('messages_per_month', 1000000)
        return self.pricing_api.get_sns_price(messages_per_month)

    def _estimate_elasticache_cost(self, node):
        """Estimate ElastiCache costs."""
        instance_type = node['config'].get('instance_type', 'cache.t3.small')
        return self.pricing_api.get_elasticache_price(instance_type)

    def _estimate_config_cost(self, node):
        """Estimate AWS Config costs."""
        config_items = node['config'].get('config_items', 100000)
        rule_evaluations = node['config'].get('rule_evaluations', 100000)
        return self.pricing_api.get_config_price(config_items, rule_evaluations)

class CostEstimator:
    def __init__(self, region: str = 'ap-south-1'):
        """Initialize the cost estimator with AWS region."""
        self.region = region
        self.pricing_api = AWSPricingAPI(region=region)
        self.logger = logging.getLogger(__name__)

    def estimate_ec2_cost(self, instance_type: str) -> Dict[str, Any]:
        """Estimate EC2 instance cost."""
        try:
            monthly_price = self.pricing_api.get_ec2_price(instance_type)
            specs = self.pricing_api.get_instance_specifications(instance_type)
            
            return {
                'instance_type': instance_type,
                'monthly_price': monthly_price,
                'specifications': specs,
                'region': self.region
            }
        except Exception as e:
            self.logger.error(f"Error estimating EC2 cost: {str(e)}")
            return {}

    def estimate_rds_cost(self, instance_type: str) -> Dict[str, Any]:
        """Estimate RDS instance cost."""
        try:
            monthly_price = self.pricing_api.get_rds_price(instance_type)
            specs = self.pricing_api.get_rds_specifications(instance_type)
            
            return {
                'instance_type': instance_type,
                'monthly_price': monthly_price,
                'specifications': specs,
                'region': self.region
            }
        except Exception as e:
            self.logger.error(f"Error estimating RDS cost: {str(e)}")
            return {}

    def estimate_lambda_cost(self, memory_mb: float, duration_ms: float, requests_per_month: int) -> Dict[str, Any]:
        """Estimate Lambda function cost."""
        try:
            monthly_price = self.pricing_api.get_lambda_price(memory_mb, duration_ms, requests_per_month)
            specs = self.pricing_api.get_lambda_specifications()
            
            return {
                'memory_mb': memory_mb,
                'duration_ms': duration_ms,
                'requests_per_month': requests_per_month,
                'monthly_price': monthly_price,
                'specifications': specs,
                'region': self.region
            }
        except Exception as e:
            self.logger.error(f"Error estimating Lambda cost: {str(e)}")
            return {}

    def estimate_s3_cost(self, storage_gb: float, requests_per_month: int) -> Dict[str, Any]:
        """Estimate S3 storage cost."""
        try:
            monthly_price = self.pricing_api.get_s3_price(storage_gb, requests_per_month)
            specs = self.pricing_api.get_s3_specifications()
            
            return {
                'storage_gb': storage_gb,
                'requests_per_month': requests_per_month,
                'monthly_price': monthly_price,
                'specifications': specs,
                'region': self.region
            }
        except Exception as e:
            self.logger.error(f"Error estimating S3 cost: {str(e)}")
            return {}

    def estimate_dynamodb_cost(self, read_capacity: int, write_capacity: int, storage_gb: float) -> Dict[str, Any]:
        """Estimate DynamoDB cost."""
        try:
            monthly_price = self.pricing_api.get_dynamodb_price(read_capacity, write_capacity, storage_gb)
            
            return {
                'read_capacity': read_capacity,
                'write_capacity': write_capacity,
                'storage_gb': storage_gb,
                'monthly_price': monthly_price,
                'region': self.region
            }
        except Exception as e:
            self.logger.error(f"Error estimating DynamoDB cost: {str(e)}")
            return {}

    def estimate_route53_cost(self, queries_per_month: int) -> Dict[str, Any]:
        """Estimate Route53 cost."""
        try:
            monthly_price = self.pricing_api.get_route53_price(queries_per_month)
            specs = self.pricing_api.get_route53_specifications()
            
            return {
                'queries_per_month': queries_per_month,
                'monthly_price': monthly_price,
                'specifications': specs,
                'region': self.region
            }
        except Exception as e:
            self.logger.error(f"Error estimating Route53 cost: {str(e)}")
            return {}

    def estimate_cloudfront_cost(self, data_transfer_gb: float, requests_per_month: int) -> Dict[str, Any]:
        """Estimate CloudFront cost."""
        try:
            monthly_price = self.pricing_api.get_cloudfront_price(data_transfer_gb, requests_per_month)
            specs = self.pricing_api.get_cloudfront_specifications()
            
            return {
                'data_transfer_gb': data_transfer_gb,
                'requests_per_month': requests_per_month,
                'monthly_price': monthly_price,
                'specifications': specs,
                'region': self.region
            }
        except Exception as e:
            self.logger.error(f"Error estimating CloudFront cost: {str(e)}")
            return {}

    def estimate_sns_cost(self, messages_per_month: int) -> Dict[str, Any]:
        """Estimate SNS cost."""
        try:
            monthly_price = self.pricing_api.get_sns_price(messages_per_month)
            specs = self.pricing_api.get_sns_specifications()
            
            return {
                'messages_per_month': messages_per_month,
                'monthly_price': monthly_price,
                'specifications': specs,
                'region': self.region
            }
        except Exception as e:
            self.logger.error(f"Error estimating SNS cost: {str(e)}")
            return {}

    def estimate_elasticache_cost(self, instance_type: str) -> Dict[str, Any]:
        """Estimate ElastiCache cost."""
        try:
            monthly_price = self.pricing_api.get_elasticache_price(instance_type)
            specs = self.pricing_api.get_elasticache_specifications(instance_type)
            
            return {
                'instance_type': instance_type,
                'monthly_price': monthly_price,
                'specifications': specs,
                'region': self.region
            }
        except Exception as e:
            self.logger.error(f"Error estimating ElastiCache cost: {str(e)}")
            return {}

    def estimate_config_cost(self, config_items: int, rule_evaluations: int) -> Dict[str, Any]:
        """Estimate AWS Config cost."""
        try:
            monthly_price = self.pricing_api.get_config_price(config_items, rule_evaluations)
            specs = self.pricing_api.get_config_specifications()
            
            return {
                'config_items': config_items,
                'rule_evaluations': rule_evaluations,
                'monthly_price': monthly_price,
                'specifications': specs,
                'region': self.region
            }
        except Exception as e:
            self.logger.error(f"Error estimating Config cost: {str(e)}")
            return {}

    def estimate_vpc_cost(self) -> Dict[str, Any]:
        """Estimate VPC cost."""
        try:
            monthly_price = self.pricing_api.get_vpc_price()
            specs = self.pricing_api.get_vpc_specifications()
            
            return {
                'monthly_price': monthly_price,
                'specifications': specs,
                'region': self.region
            }
        except Exception as e:
            self.logger.error(f"Error estimating VPC cost: {str(e)}")
            return {}

    def estimate_total_cost(self, resources: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate total cost for multiple resources."""
        try:
            total_cost = 0
            estimates = {}
            
            # EC2 instances
            if 'ec2_instances' in resources:
                for instance in resources['ec2_instances']:
                    estimate = self.estimate_ec2_cost(instance['instance_type'])
                    estimates[f"ec2_{instance['instance_type']}"] = estimate
                    total_cost += estimate.get('monthly_price', 0)
            
            # RDS instances
            if 'rds_instances' in resources:
                for instance in resources['rds_instances']:
                    estimate = self.estimate_rds_cost(instance['instance_type'])
                    estimates[f"rds_{instance['instance_type']}"] = estimate
                    total_cost += estimate.get('monthly_price', 0)
            
            # Lambda functions
            if 'lambda_functions' in resources:
                for func in resources['lambda_functions']:
                    estimate = self.estimate_lambda_cost(
                        func['memory_mb'],
                        func['duration_ms'],
                        func['requests_per_month']
                    )
                    estimates[f"lambda_{func['memory_mb']}mb"] = estimate
                    total_cost += estimate.get('monthly_price', 0)
            
            # S3 storage
            if 's3_storage' in resources:
                for storage in resources['s3_storage']:
                    estimate = self.estimate_s3_cost(
                        storage['storage_gb'],
                        storage['requests_per_month']
                    )
                    estimates[f"s3_{storage['storage_gb']}gb"] = estimate
                    total_cost += estimate.get('monthly_price', 0)
            
            # DynamoDB tables
            if 'dynamodb_tables' in resources:
                for table in resources['dynamodb_tables']:
                    estimate = self.estimate_dynamodb_cost(
                        table['read_capacity'],
                        table['write_capacity'],
                        table['storage_gb']
                    )
                    estimates[f"dynamodb_{table['read_capacity']}rcu"] = estimate
                    total_cost += estimate.get('monthly_price', 0)
            
            # Route53 hosted zones
            if 'route53_zones' in resources:
                for zone in resources['route53_zones']:
                    estimate = self.estimate_route53_cost(zone['queries_per_month'])
                    estimates[f"route53_{zone['queries_per_month']}queries"] = estimate
                    total_cost += estimate.get('monthly_price', 0)
            
            # CloudFront distributions
            if 'cloudfront_distributions' in resources:
                for dist in resources['cloudfront_distributions']:
                    estimate = self.estimate_cloudfront_cost(
                        dist['data_transfer_gb'],
                        dist['requests_per_month']
                    )
                    estimates[f"cloudfront_{dist['data_transfer_gb']}gb"] = estimate
                    total_cost += estimate.get('monthly_price', 0)
            
            # SNS topics
            if 'sns_topics' in resources:
                for topic in resources['sns_topics']:
                    estimate = self.estimate_sns_cost(topic['messages_per_month'])
                    estimates[f"sns_{topic['messages_per_month']}msgs"] = estimate
                    total_cost += estimate.get('monthly_price', 0)
            
            # ElastiCache clusters
            if 'elasticache_clusters' in resources:
                for cluster in resources['elasticache_clusters']:
                    estimate = self.estimate_elasticache_cost(cluster['instance_type'])
                    estimates[f"elasticache_{cluster['instance_type']}"] = estimate
                    total_cost += estimate.get('monthly_price', 0)
            
            # AWS Config
            if 'config' in resources:
                estimate = self.estimate_config_cost(
                    resources['config']['config_items'],
                    resources['config']['rule_evaluations']
                )
                estimates['config'] = estimate
                total_cost += estimate.get('monthly_price', 0)
            
            # VPC
            if 'vpc' in resources:
                estimate = self.estimate_vpc_cost()
                estimates['vpc'] = estimate
                total_cost += estimate.get('monthly_price', 0)
            
            return {
                'total_monthly_cost': total_cost,
                'estimates': estimates,
                'region': self.region
            }
        except Exception as e:
            self.logger.error(f"Error estimating total cost: {str(e)}")
            return {}

# Example usage:
"""
estimator = AWSCostEstimator(region="us-east-1")
with open('architecture.json', 'r') as f:
    architecture = json.load(f)
cost_estimate = estimator.estimate_total_cost(architecture)
print(json.dumps(cost_estimate, indent=2))
""" 