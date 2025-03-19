import json
import os
import logging
from typing import Dict, Any, Optional, Iterator
import ijson  # For streaming JSON parsing

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PricingDataLoader:
    def __init__(self, pricing_dir: str = "aws_pricing_data", region: str = "ap-south-1"):
        """Initialize the pricing data loader."""
        self.pricing_dir = pricing_dir
        self.region = region
        # Initialize empty cache structure without any default values
        self.pricing_cache = {
            'ec2': {},      # instance_type -> price
            'rds': {},      # instance_type -> price
            'lambda': {
                'request_price': 0.0,
                'compute_price': 0.0
            },
            's3': {
                'storage': 0.0,
                'requests': {
                    'PUT': 0.0,
                    'GET': 0.0
                }
            },
            'dynamodb': {
                'storage': 0.0,
                'rcu': 0.0,
                'wcu': 0.0
            },
            'route53': {
                'hosted_zone': 0.0,
                'queries': 0.0
            },
            'cloudfront': {
                'data_transfer': 0.0,
                'requests': 0.0
            },
            'sns': {
                'requests': 0.0
            },
            'elasticache': {},  # instance_type -> price
            'config': {
                'config_items': 0.0,
                'rule_evaluations': 0.0
            }
        }
        self._load_pricing_data()

    def _stream_json_file(self, file_path: str):
        """Stream a JSON file and yield product-price pairs."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                
                # Process each product
                for product_id, product in data.get('products', {}).items():
                    # Get the corresponding pricing terms
                    terms = data.get('terms', {}).get('OnDemand', {}).get(product_id, {})
                    
                    for term_id, term_info in terms.items():
                        # Get price dimensions for this term
                        price_dimensions = term_info.get('priceDimensions', {})
                        
                        for dimension_id, dimension in price_dimensions.items():
                            price_per_unit = dimension.get('pricePerUnit', {}).get('USD', '0')
                            try:
                                price = float(price_per_unit)
                            except (ValueError, TypeError):
                                price = 0.0
                                
                            if price > 0:
                                product_info = {
                                    'sku': product.get('sku'),
                                    'attributes': product.get('attributes', {}),
                                    'price': price,
                                    'description': dimension.get('description', ''),
                                    'unit': dimension.get('unit', '')
                                }
                                yield product_info
                                
        except Exception as e:
            logging.error(f"Error processing {file_path}: {str(e)}")
            yield None

    def _load_pricing_data(self):
        """Load pricing data from JSON files."""
        logging.basicConfig(level=logging.INFO)
        logging.info("Loading AWS pricing data...")
        
        # Load EC2 pricing
        ec2_file = os.path.join(self.pricing_dir, self.region, 'AmazonEC2_pricing.json')
        logging.info(f"Looking for EC2 pricing file at: {ec2_file}")
        if os.path.exists(ec2_file):
            for product in self._stream_json_file(ec2_file):
                if product and 'attributes' in product:
                    instance_type = product['attributes'].get('instanceType')
                    if instance_type:
                        self.pricing_cache['ec2'][instance_type] = product['price']
                        logging.info(f"Found EC2 price for {instance_type}: ${product['price']}/hour")
            logging.info(f"Loaded {len(self.pricing_cache['ec2'])} EC2 instance types")
        else:
            logging.warning(f"EC2 pricing file not found at {ec2_file}")
        
        # Load RDS pricing
        rds_file = os.path.join(self.pricing_dir, self.region, 'AmazonRDS_pricing.json')
        logging.info(f"Looking for RDS pricing file at: {rds_file}")
        if os.path.exists(rds_file):
            for product in self._stream_json_file(rds_file):
                if product and 'attributes' in product:
                    instance_type = product['attributes'].get('instanceType')
                    if instance_type:
                        self.pricing_cache['rds'][instance_type] = product['price']
                        logging.info(f"Found RDS price for {instance_type}: ${product['price']}/hour")
            logging.info(f"Loaded {len(self.pricing_cache['rds'])} RDS instance types")
        else:
            logging.warning(f"RDS pricing file not found at {rds_file}")
        
        # Load Lambda pricing
        lambda_file = os.path.join(self.pricing_dir, self.region, 'AWSLambda_pricing.json')
        logging.info(f"Looking for Lambda pricing file at: {lambda_file}")
        if os.path.exists(lambda_file):
            for product in self._stream_json_file(lambda_file):
                if product and 'attributes' in product:
                    if 'Request' in product['description']:
                        self.pricing_cache['lambda']['request_price'] = product['price']
                        logging.info(f"Found Lambda request price: ${product['price']}/million requests")
                    elif 'GB-Second' in product['description']:
                        self.pricing_cache['lambda']['compute_price'] = product['price']
                        logging.info(f"Found Lambda compute price: ${product['price']}/GB-second")
            logging.info(f"Loaded Lambda pricing: {self.pricing_cache['lambda']}")
        else:
            logging.warning(f"Lambda pricing file not found at {lambda_file}")
        
        # Load S3 pricing
        s3_file = os.path.join(self.pricing_dir, self.region, 'AmazonS3_pricing.json')
        logging.info(f"Looking for S3 pricing file at: {s3_file}")
        if os.path.exists(s3_file):
            for product in self._stream_json_file(s3_file):
                if product and 'attributes' in product:
                    if 'Storage' in product['description']:
                        self.pricing_cache['s3']['storage'] = product['price']
                        logging.info(f"Found S3 storage price: ${product['price']}/GB-month")
                    elif 'PUT' in product['description']:
                        self.pricing_cache['s3']['requests']['PUT'] = product['price']
                        logging.info(f"Found S3 PUT request price: ${product['price']}/1000 requests")
                    elif 'GET' in product['description']:
                        self.pricing_cache['s3']['requests']['GET'] = product['price']
                        logging.info(f"Found S3 GET request price: ${product['price']}/1000 requests")
            logging.info(f"Loaded S3 pricing: {self.pricing_cache['s3']}")
        else:
            logging.warning(f"S3 pricing file not found at {s3_file}")
        
        # Load DynamoDB pricing
        dynamodb_file = os.path.join(self.pricing_dir, self.region, 'AmazonDynamoDB_pricing.json')
        logging.info(f"Looking for DynamoDB pricing file at: {dynamodb_file}")
        if os.path.exists(dynamodb_file):
            for product in self._stream_json_file(dynamodb_file):
                if product and 'attributes' in product:
                    if 'Storage' in product['description']:
                        self.pricing_cache['dynamodb']['storage'] = product['price']
                        logging.info(f"Found DynamoDB storage price: ${product['price']}/GB-month")
                    elif 'RCU' in product['description']:
                        self.pricing_cache['dynamodb']['rcu'] = product['price']
                        logging.info(f"Found DynamoDB RCU price: ${product['price']}/RCU-hour")
                    elif 'WCU' in product['description']:
                        self.pricing_cache['dynamodb']['wcu'] = product['price']
                        logging.info(f"Found DynamoDB WCU price: ${product['price']}/WCU-hour")
            logging.info(f"Loaded DynamoDB pricing: {self.pricing_cache['dynamodb']}")
        else:
            logging.warning(f"DynamoDB pricing file not found at {dynamodb_file}")
        
        # Load SNS pricing
        sns_file = os.path.join(self.pricing_dir, self.region, 'AmazonSNS_pricing.json')
        logging.info(f"Looking for SNS pricing file at: {sns_file}")
        if os.path.exists(sns_file):
            for product in self._stream_json_file(sns_file):
                if product and 'attributes' in product:
                    if 'API Requests' in product['description']:
                        self.pricing_cache['sns']['requests'] = product['price']
                        logging.info(f"Found SNS request price: ${product['price']}/million requests")
            logging.info(f"Loaded SNS pricing: {self.pricing_cache['sns']}")
        else:
            logging.warning(f"SNS pricing file not found at {sns_file}")
        
        # Load ElastiCache pricing
        elasticache_file = os.path.join(self.pricing_dir, self.region, 'AmazonElastiCache_pricing.json')
        logging.info(f"Looking for ElastiCache pricing file at: {elasticache_file}")
        if os.path.exists(elasticache_file):
            for product in self._stream_json_file(elasticache_file):
                if product and 'attributes' in product:
                    instance_type = product['attributes'].get('instanceType')
                    if instance_type:
                        self.pricing_cache['elasticache'][instance_type] = product['price']
                        logging.info(f"Found ElastiCache price for {instance_type}: ${product['price']}/hour")
            logging.info(f"Loaded {len(self.pricing_cache['elasticache'])} ElastiCache instance types")
        else:
            logging.warning(f"ElastiCache pricing file not found at {elasticache_file}")
        
        # Log final summary
        logging.info("\nPricing data summary:")
        for service, data in self.pricing_cache.items():
            if isinstance(data, dict):
                if service in ['ec2', 'rds', 'elasticache']:
                    logging.info(f"{service}: {len(data)} instance types loaded")
                else:
                    logging.info(f"{service}: {data}")
        
        logging.info("\nFinished loading AWS pricing data")

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
        return self.pricing_cache['s3']['storage']

    def get_s3_put_price(self) -> float:
        """Get S3 PUT request price per 1000 requests."""
        return self.pricing_cache['s3']['requests']['PUT']

    def get_s3_get_price(self) -> float:
        """Get S3 GET request price per 1000 requests."""
        return self.pricing_cache['s3']['requests']['GET']

    def get_dynamodb_storage_price(self) -> float:
        """Get DynamoDB storage price per GB-month."""
        return self.pricing_cache['dynamodb']['storage']

    def get_dynamodb_rcu_price(self) -> float:
        """Get DynamoDB read capacity unit price per RCU-hour."""
        return self.pricing_cache['dynamodb']['rcu']

    def get_dynamodb_wcu_price(self) -> float:
        """Get DynamoDB write capacity unit price per WCU-hour."""
        return self.pricing_cache['dynamodb']['wcu']

    def get_cloudfront_transfer_price(self) -> float:
        """Get CloudFront data transfer price per GB."""
        return self.pricing_cache['cloudfront']['data_transfer']

    def get_cloudfront_request_price(self) -> float:
        """Get CloudFront request price per 10,000 requests."""
        return self.pricing_cache['cloudfront']['requests']

    def get_sns_price(self) -> float:
        """Get SNS price per million requests."""
        return self.pricing_cache['sns']['requests']

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

class CostEstimator:
    def __init__(self, pricing_dir: str = 'aws_pricing_data', region: str = 'ap-south-1'):
        """Initialize the cost estimator with pricing data directory and region."""
        self.region = region
        self.pricing = PricingDataLoader(pricing_dir=pricing_dir, region=region)

    def calculate_rds_cost(self, instance_type: str) -> float:
        """Calculate monthly cost for RDS instance."""
        try:
            hourly_price = self.pricing.get_rds_price(instance_type)
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
            prices = self.pricing.get_route53_prices()
            hosted_zone_cost = prices['hosted_zone']
            queries_cost = prices['queries'] * 1000000  # Assuming 1M queries per month
            total_cost = hosted_zone_cost + queries_cost
            logging.info(f"Route53 cost calculation: hosted_zone_cost=${hosted_zone_cost:.2f}, queries_cost=${queries_cost:.2f}")
            return total_cost
        except Exception as e:
            logging.error(f"Error calculating Route53 cost: {str(e)}")
            return 0.0

    def estimate_costs(self, input_file: str) -> dict:
        """Estimate costs for AWS resources defined in the input file."""
        try:
            with open(input_file, 'r') as f:
                architecture = json.load(f)
            
            total_cost = 0.0
            costs = {}
            
            # Process each node in the architecture
            for node in architecture.get('nodes', []):
                name = node.get('label', 'Unknown')
                service = node.get('type', '').lower()
                
                if service == 'amazonvpc':
                    cost = self.calculate_vpc_cost()
                
                elif service == 'amazonroute53':
                    cost = self.calculate_route53_cost()
                    
                elif service == 'amazoncloudfront':
                    cost = self.calculate_cloudfront_cost()
                    
                elif service == 'amazonec2':
                    instance_type = node.get('InstanceType')
                    cost = self.calculate_ec2_cost(instance_type)
                    
                elif service == 'amazons3':
                    storage_gb = 100  # Assuming 100GB storage
                    requests = 100000  # Assuming 100K requests per month
                    
                    node_data = {
                        'storage_gb': storage_gb,
                        'requests': requests
                    }
                    cost = self.calculate_s3_cost(node_data)
                    
                elif service == 'amazonrds':
                    instance_type = node.get('DBInstanceClass')
                    cost = self.calculate_rds_cost(instance_type)
                    
                elif service == 'amazondynamodb':
                    throughput = node.get('Throughput', '5 Read / 5 Write')
                    read_cu = float(throughput.split('Read')[0].strip())
                    write_cu = float(throughput.split('/')[-1].split('Write')[0].strip())
                    storage_gb = 100  # Assuming 100GB storage
                    
                    node_data = {
                        'storage_gb': storage_gb,
                        'read_capacity_units': read_cu,
                        'write_capacity_units': write_cu
                    }
                    cost = self.calculate_dynamodb_cost(node_data)
                    
                elif service == 'awslambda':
                    memory_mb = float(node.get('Memory', '512').replace('MB', ''))
                    invocations = 100000  # Assuming 100K invocations per month
                    duration_ms = float(node.get('Timeout', '10').replace('s', '')) * 1000
                    
                    node_data = {
                        'memory_mb': memory_mb,
                        'duration_ms': duration_ms,
                        'invocations': invocations
                    }
                    cost = self.calculate_lambda_cost(node_data)
                    
                elif service == 'amazonsns':
                    notifications = 100000  # Assuming 100K notifications per month
                    node_data = {
                        'notifications': notifications
                    }
                    cost = self.calculate_sns_cost(node_data)
                    
                elif service == 'amazonelasticache':
                    instance_type = node.get('InstanceType')
                    cost = self.calculate_elasticache_cost(instance_type)
                    
                elif service == 'awsconfig':
                    cost = self.calculate_config_cost()
                    
                else:
                    logging.warning(f"Unsupported service: {service}")
                    cost = 0.0
                
                costs[name] = cost
                total_cost += cost
            
            costs["Total"] = total_cost
            
            # Save results to file
            with open('cost_estimate_result.json', 'w') as f:
                json.dump(costs, f, indent=2)
            
            # Print results in a nice format
            print("\nCost Estimation Results:")
            print("=======================")
            for name, cost in costs.items():
                print(f"{name}: ${cost:.2f}")
            
            return costs
            
        except Exception as e:
            logging.error(f"Error in cost estimation: {str(e)}")
            return {"Total": 0.00}

    def calculate_ec2_cost(self, instance_type: str) -> float:
        """Calculate monthly cost for EC2 instance."""
        try:
            hourly_price = self.pricing.get_ec2_instance_price(instance_type)
            monthly_cost = hourly_price * 24 * 30  # Assuming 30 days per month
            logging.info(f"EC2 cost calculation: instance_type={instance_type}, monthly_cost=${monthly_cost:.2f}")
            return monthly_cost
        except Exception as e:
            logging.error(f"Error calculating EC2 cost: {str(e)}")
            return 0.0

    def calculate_cloudfront_cost(self) -> float:
        """Calculate monthly cost for CloudFront."""
        try:
            prices = self.pricing.get_cloudfront_prices()
            data_transfer_gb = 100  # Assuming 100GB transfer per month
            requests = 1000000  # Assuming 1M requests per month
            data_transfer_cost = prices['data_transfer'] * data_transfer_gb
            requests_cost = prices['requests'] * (requests / 10000)
            total_cost = data_transfer_cost + requests_cost
            logging.info(f"CloudFront cost calculation: data_transfer_cost=${data_transfer_cost:.2f}, requests_cost=${requests_cost:.2f}")
            return total_cost
        except Exception as e:
            logging.error(f"Error calculating CloudFront cost: {str(e)}")
            return 0.0

    def calculate_lambda_cost(self, node: dict) -> float:
        """Calculate monthly cost for Lambda function."""
        try:
            memory_mb = float(node.get('memory_mb', 128))
            duration_ms = float(node.get('duration_ms', 100))
            invocations = float(node.get('invocations', 0))
            
            # Convert memory to GB and duration to seconds
            memory_gb = memory_mb / 1024
            duration_sec = duration_ms / 1000
            
            # Calculate GB-seconds
            gb_seconds = memory_gb * duration_sec * invocations
            
            # Get pricing
            compute_price = self.pricing.get_lambda_compute_price()
            request_price = self.pricing.get_lambda_request_price()
            
            # Calculate monthly costs
            compute_cost = gb_seconds * compute_price
            request_cost = (invocations / 1000000) * request_price  # Price is per million requests
            
            total_cost = compute_cost + request_cost
            logging.info(f"Lambda cost calculation: GB-seconds={gb_seconds}, compute_cost=${compute_cost:.2f}, request_cost=${request_cost:.2f}")
            return total_cost
            
        except Exception as e:
            logging.error(f"Error calculating Lambda cost: {str(e)}")
            return 0.0

    def calculate_s3_cost(self, node: dict) -> float:
        """Calculate monthly cost for S3 bucket."""
        try:
            storage_gb = float(node.get('storage_gb', 0))
            requests = float(node.get('requests', 0))
            
            # Get pricing
            storage_price = self.pricing.get_s3_storage_price()
            put_price = self.pricing.get_s3_put_price()
            get_price = self.pricing.get_s3_get_price()
            
            # Calculate monthly costs
            storage_cost = storage_gb * storage_price  # Price is per GB-month
            request_cost = (requests / 1000) * ((put_price + get_price) / 2)  # Assume 50/50 split between GET and PUT
            
            total_cost = storage_cost + request_cost
            logging.info(f"S3 cost calculation: storage_cost=${storage_cost:.2f}, request_cost=${request_cost:.2f}")
            return total_cost
            
        except Exception as e:
            logging.error(f"Error calculating S3 cost: {str(e)}")
            return 0.0

    def calculate_dynamodb_cost(self, node: dict) -> float:
        """Calculate monthly cost for DynamoDB table."""
        try:
            storage_gb = float(node.get('storage_gb', 0))
            read_capacity_units = float(node.get('read_capacity_units', 0))
            write_capacity_units = float(node.get('write_capacity_units', 0))
            
            # Get pricing
            storage_price = self.pricing.get_dynamodb_storage_price()
            rcu_price = self.pricing.get_dynamodb_rcu_price()
            wcu_price = self.pricing.get_dynamodb_wcu_price()
            
            # Calculate monthly costs
            storage_cost = storage_gb * storage_price  # Price is per GB-month
            rcu_cost = read_capacity_units * rcu_price * 730  # Convert hourly to monthly
            wcu_cost = write_capacity_units * wcu_price * 730  # Convert hourly to monthly
            
            total_cost = storage_cost + rcu_cost + wcu_cost
            logging.info(f"DynamoDB cost calculation: storage_cost=${storage_cost:.2f}, rcu_cost=${rcu_cost:.2f}, wcu_cost=${wcu_cost:.2f}")
            return total_cost
            
        except Exception as e:
            logging.error(f"Error calculating DynamoDB cost: {str(e)}")
            return 0.0

    def calculate_sns_cost(self, node: dict) -> float:
        """Calculate monthly cost for SNS notifications."""
        try:
            notifications = float(node.get('notifications', 0))
            
            # Get pricing
            request_price = self.pricing.get_sns_price()
            
            # Calculate monthly cost (price is per million notifications)
            total_cost = (notifications / 1000000) * request_price
            logging.info(f"SNS cost calculation: notifications={notifications}, cost=${total_cost:.2f}")
            return total_cost
            
        except Exception as e:
            logging.error(f"Error calculating SNS cost: {str(e)}")
            return 0.0

    def calculate_elasticache_cost(self, instance_type: str) -> float:
        """Calculate monthly cost for ElastiCache."""
        try:
            hourly_price = self.pricing.get_elasticache_instance_price(instance_type)
            monthly_cost = hourly_price * 24 * 30  # Assuming 30 days per month
            logging.info(f"ElastiCache cost calculation: instance_type={instance_type}, monthly_cost=${monthly_cost:.2f}")
            return monthly_cost
        except Exception as e:
            logging.error(f"Error calculating ElastiCache cost: {str(e)}")
            return 0.0

    def calculate_config_cost(self) -> float:
        """Calculate monthly cost for AWS Config."""
        try:
            prices = self.pricing.get_config_prices()
            config_items = 100  # Assuming 100 config items
            rule_evaluations = 1000  # Assuming 1000 rule evaluations per month
            config_items_cost = prices['config_items'] * config_items
            rule_evaluations_cost = prices['rule_evaluations'] * rule_evaluations
            total_cost = config_items_cost + rule_evaluations_cost
            logging.info(f"AWS Config cost calculation: config_items_cost=${config_items_cost:.2f}, rule_evaluations_cost=${rule_evaluations_cost:.2f}")
            return total_cost
        except Exception as e:
            logging.error(f"Error calculating AWS Config cost: {str(e)}")
            return 0.0

# Example usage:
"""
estimator = CostEstimator(region="us-east-1")
with open('architecture.json', 'r') as f:
    architecture = json.load(f)
cost_estimate = estimator.estimate_total_cost(architecture)
print(json.dumps(cost_estimate, indent=2))
""" 