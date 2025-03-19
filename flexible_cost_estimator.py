import json
import os
from datetime import datetime
from typing import Dict, Any, List
from cost_estimator import CostEstimator
import logging
import argparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FlexibleArchitectureParser:
    """Parses any AWS architecture JSON and converts it to a standardized format for cost estimation."""
    
    def __init__(self):
        self.supported_services = {
            "EC2": ["AmazonEC2", "EC2", "ec2"],
            "RDS": ["AmazonRDS", "RDS", "rds"],
            "S3": ["AmazonS3", "S3", "s3"],
            "CloudFront": ["AmazonCloudFront", "CloudFront", "cloudfront"],
            "APIGateway": ["AmazonAPIGateway", "APIGateway", "api-gateway", "api"],
            "Lambda": ["AWSLambda", "Lambda", "lambda"],
            "DynamoDB": ["AmazonDynamoDB", "DynamoDB", "dynamodb"],
            "ElastiCache": ["AmazonElastiCache", "ElastiCache", "elasticache"],
            "SNS": ["AmazonSNS", "SNS", "sns"],
            "IAM": ["AWSIdentityAndAccessManagement", "IAM", "iam"]
        }

    def _identify_service_type(self, node: Dict[str, Any]) -> str:
        """Identifies AWS service type from node properties."""
        # Check common service type fields
        type_fields = ["type", "service", "serviceType", "Type", "ServiceType"]
        
        for field in type_fields:
            if field in node:
                service_type = node[field]
                # Match against supported services
                for service, aliases in self.supported_services.items():
                    if any(alias.lower() in service_type.lower() for alias in aliases):
                        return service
        
        # Try to infer from other fields or properties
        if any(field in node for field in ["InstanceType", "EC2Instance"]):
            return "EC2"
        elif any(field in node for field in ["DBInstanceClass", "DatabaseEngine"]):
            return "RDS"
        elif any(field in node for field in ["BucketName", "StorageSize"]):
            return "S3"
        elif any(field in node for field in ["Memory", "Runtime", "ExecutionTime"]):
            return "Lambda"
        elif any(field in node for field in ["TopicCount", "NotificationDelivery"]):
            return "SNS"
        elif any(field in node for field in ["AnalyzerCount", "AccessAnalyzer"]):
            return "IAM"
        
        return "Unknown"

    def _extract_config_value(self, node: Dict[str, Any], fields: List[str], default_value: Any = None) -> Any:
        """Extracts a configuration value from various possible fields in the node."""
        for field in fields:
            # Check direct field
            if field in node:
                return node[field]
            # Check in CostBreakdown
            if "CostBreakdown" in node and field in node["CostBreakdown"]:
                return node["CostBreakdown"][field]
            # Check in attributes
            if "attributes" in node and field in node["attributes"]:
                return node["attributes"][field]
        return default_value

    def transform_architecture(self, architecture: Dict[str, Any]) -> Dict[str, Any]:
        """Transforms any architecture JSON into standardized format."""
        transformed = {}
        
        # Handle different JSON structures
        nodes = []
        if "nodes" in architecture:
            nodes = architecture["nodes"]
        elif "resources" in architecture:
            nodes = architecture["resources"]
        elif "services" in architecture:
            nodes = architecture["services"]
        elif isinstance(architecture, list):
            nodes = architecture
        else:
            # Assume the architecture itself is a dict of services
            nodes = [{"type": k, **v} for k, v in architecture.items()]

        for node in nodes:
            service_type = self._identify_service_type(node)
            node_label = node.get("label") or node.get("name") or node.get("id") or f"{service_type}_{len(transformed)}"
            
            if service_type == "Lambda":
                transformed[node_label] = {
                    "memory_mb": int(self._extract_config_value(node, ["Memory", "memory_mb", "MemorySize"], 128)),
                    "invocations": int(self._extract_config_value(node, ["InvocationCost", "invocations", "MonthlyInvocations"], 0)),
                    "avg_duration_ms": int(self._extract_config_value(node, ["ExecutionTimeCost", "Duration", "avg_duration_ms"], 100))
                }
            
            elif service_type == "DynamoDB":
                throughput = int(self._extract_config_value(node, ["Throughput", "ProvisionedThroughput"], 0))
                transformed[node_label] = {
                    "storage_gb": float(self._extract_config_value(node, ["Storage", "StorageSize", "Size"], 0)),
                    "read_capacity": throughput,
                    "write_capacity": throughput
                }
            
            elif service_type == "APIGateway":
                transformed[node_label] = {
                    "requests_per_month": float(self._extract_config_value(node, 
                        ["CostPerRequest", "RequestCount", "MonthlyRequests", "CostPerMillionRequests"], 0))
                }
            
            elif service_type == "S3":
                transformed[node_label] = {
                    "storage_gb": float(self._extract_config_value(node, ["Size", "StorageSize", "Storage"], 0)),
                    "requests_per_month": float(self._extract_config_value(node, ["RequestCount", "MonthlyRequests"], 0))
                }
            
            elif service_type == "SNS":
                transformed[node_label] = {
                    "notifications_per_month": int(self._extract_config_value(node, ["TopicCost", "NotificationCount", "MonthlyNotifications"], 0))
                }
            
            elif service_type == "IAM":
                transformed[node_label] = {
                    "analyzer_count": int(self._extract_config_value(node, ["AnalyzerCount", "Analyzers"], 1))
                }
            
            elif service_type == "EC2":
                transformed[node_label] = {
                    "instance_type": self._extract_config_value(node, ["InstanceType", "instance_type"], "t3.micro"),
                    "hours_per_month": float(self._extract_config_value(node, ["HoursPerMonth", "hours"], 730))
                }
            
            elif service_type == "RDS":
                transformed[node_label] = {
                    "instance_type": self._extract_config_value(node, ["DBInstanceClass", "InstanceType"], "db.t3.micro"),
                    "storage_gb": float(self._extract_config_value(node, ["Storage", "AllocatedStorage"], 20)),
                    "hours_per_month": float(self._extract_config_value(node, ["HoursPerMonth", "hours"], 730))
                }

        return transformed

def estimate_architecture_cost(architecture_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Estimates cost for any AWS architecture JSON.
    
    Args:
        architecture_json: Dict containing AWS architecture description
        
    Returns:
        Dict containing cost breakdown and details
    """
    try:
        # Parse and transform architecture
        parser = FlexibleArchitectureParser()
        transformed_architecture = parser.transform_architecture(architecture_json)
        
        # Initialize cost estimator
        estimator = CostEstimator()
        
        # Calculate costs
        cost_breakdown = estimator.estimate_total_cost(transformed_architecture)
        
        # Prepare detailed output
        result = {
            "architecture_name": architecture_json.get("title", "AWS Architecture"),
            "cost_breakdown": cost_breakdown,
            "service_details": {
                service: {
                    "configuration": transformed_architecture[service],
                    "monthly_cost": cost_breakdown.get(service, 0)
                }
                for service in transformed_architecture
            },
            "monthly_total_cost": cost_breakdown.get("Total", 0),
            "currency": "USD",
            "timestamp": datetime.now().isoformat(),
            "region": "us-east-1"
        }
        
        # Save results
        output_file = "cost_estimate_result.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        return result
        
    except Exception as e:
        logger.error(f"Error estimating architecture cost: {str(e)}")
        raise

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='AWS Architecture Cost Estimator')
    parser.add_argument('architecture_file', help='Path to the architecture JSON file')
    parser.add_argument('--region', default='ap-south-1', 
                      choices=[
                          'ap-south-1',     # Mumbai
                          # 'ap-northeast-1',  # Tokyo
                          # 'us-east-1',       # N. Virginia
                          # 'us-east-2',       # Ohio
                          # 'us-west-1',       # N. California
                          # 'us-west-2',       # Oregon
                      ],
                      help='AWS region for pricing (default: ap-south-1)')

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=logging.INFO,
                       format='%(levelname)s:%(name)s:%(message)s')
    logger = logging.getLogger('cost_estimator')

    try:
        # Load architecture configuration
        with open(args.architecture_file, 'r') as f:
            architecture = json.load(f)

        # Initialize cost estimator with selected region
        estimator = CostEstimator(region=args.region)
        
        # Print selected region
        logger.info(f"\nUsing pricing data from {args.region} region")
        
        # Calculate costs
        total_cost = 0
        results = {"architecture": architecture["title"], "region": args.region, "services": {}}

        print(f"\nCalculating costs for each service:")
        print("===================================\n")

        # Convert nodes to services format
        services = {}
        for node in architecture["nodes"]:
            service_name = node["label"]
            config = {
                "type": node["type"],
                "description": node.get("Description", ""),
            }
            
            # Add specific configurations based on node type
            if node["type"] == "Lambda":
                config.update({
                    "memory_mb": node["Memory"],
                    "invocations": node["CostBreakdown"]["InvocationCost"],
                    "avg_duration_ms": node["CostBreakdown"]["ExecutionTimeCost"]
                })
            elif node["type"] == "S3":
                config.update({
                    "storage_gb": node["Size"],
                    "requests_per_month": node["RequestCount"]
                })
            elif node["type"] == "DynamoDB":
                config.update({
                    "storage_gb": node["Storage"],
                    "read_capacity": node["Throughput"],
                    "write_capacity": node["Throughput"]
                })
            elif node["type"] == "RDS":
                config.update({
                    "instance_type": node["instance_type"],
                    "storage_gb": node["storage_gb"],
                    "hours_per_month": node["hours_per_month"]
                })
            elif node["type"] == "SNS":
                config.update({
                    "notifications_per_month": node["CostBreakdown"]["TopicCost"]
                })
            
            services[service_name] = config

        # Calculate costs for each service
        for service_name, config in services.items():
            cost = estimator.calculate_service_cost(service_name, config)
            total_cost += cost
            results["services"][service_name] = {
                "configuration": config,
                "monthly_cost": cost
            }
            
        results["total_monthly_cost"] = total_cost
        results["currency"] = "USD"

        # Save results to file
        with open('cost_estimate_result.json', 'w') as f:
            json.dump(results, f, indent=2)

        print("\nCost Estimation Results:")
        print("=======================")
        print(f"Architecture: {architecture['title']}")
        print(f"Region: {args.region}\n")
        print("Service Breakdown:\n")
        
        for service_name, details in results["services"].items():
            print(f"{service_name}:")
            print(f"  Configuration: {details['configuration']}")
            print(f"  Monthly Cost: ${details['monthly_cost']:.2f}\n")

        print(f"Total Monthly Cost: ${total_cost:.2f}")
        print(f"Currency: {results['currency']}\n")
        print("Results have been saved to 'cost_estimate_result.json'")

    except FileNotFoundError:
        logger.error(f"Architecture file '{args.architecture_file}' not found")
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in architecture file '{args.architecture_file}'")
    except Exception as e:
        logger.error(f"Error during cost estimation: {str(e)}")

if __name__ == "__main__":
    main() 