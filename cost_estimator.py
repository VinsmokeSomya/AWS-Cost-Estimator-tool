import json
import logging
from aws_pricing_api import AWSPricingAPI
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AWSCostEstimator:
    def __init__(self, region='ap-south-1'):
        """Initialize the cost estimator with AWS Pricing API."""
        self.region = region
        self.pricing_api = AWSPricingAPI(region)
        self.logger = logging.getLogger(__name__)
        
        # Define usage-based services with their pricing components
        self.usage_based_services = {
            'AmazonS3': {
                'description': 'Storage, requests, and data transfer',
                'components': [
                    'Storage (per GB per month)',
                    'Data Transfer (per GB)',
                    'Requests (per 1000 requests)',
                    'Lifecycle Transitions'
                ]
            },
            'AWSLambda': {
                'description': 'Compute time and requests',
                'components': [
                    'Compute (per 100ms)',
                    'Requests (per 1M requests)',
                    'Data Transfer (per GB)'
                ]
            },
            'AmazonDynamoDB': {
                'description': 'Read/write capacity and storage',
                'components': [
                    'Read Capacity (per RCU)',
                    'Write Capacity (per WCU)',
                    'Storage (per GB per month)',
                    'Data Transfer (per GB)'
                ]
            },
            'AmazonSNS': {
                'description': 'Message delivery and data transfer',
                'components': [
                    'Message Delivery (per 1M messages)',
                    'Data Transfer (per GB)',
                    'HTTP/HTTPS Delivery'
                ]
            },
            'AmazonSQS': {
                'description': 'Message requests and data transfer',
                'components': [
                    'Requests (per 1M requests)',
                    'Data Transfer (per GB)'
                ]
            },
            'AmazonCloudWatch': {
                'description': 'Metrics, logs, and alarms',
                'components': [
                    'Metrics (per metric per month)',
                    'Logs (per GB ingested)',
                    'Alarms (per alarm per month)'
                ]
            },
            'AmazonAPIGateway': {
                'description': 'API calls and data transfer',
                'components': [
                    'API Calls (per 1M calls)',
                    'Data Transfer (per GB)',
                    'Cache (per GB per hour)'
                ]
            },
            'AmazonElastiCache': {
                'description': 'Cache nodes and data transfer',
                'components': [
                    'Cache Nodes (per hour)',
                    'Data Transfer (per GB)',
                    'Backup Storage (per GB per month)'
                ]
            }
        }

    def calculate_total_cost(self, architecture_file):
        """Calculate total cost for an AWS architecture."""
        try:
            # Load architecture from file
            with open(architecture_file, 'r') as file:
                architecture = json.load(file)

            total_hourly_cost = 0.0
            total_monthly_cost = 0.0
            service_details = []
            services_json = {}

            # Process each service in the architecture
            for node in architecture['nodes']:
                service_type = node['type']
                
                # Check if it's a usage-based service
                if service_type in self.usage_based_services:
                    service_details.append({
                        'Service': service_type,
                        'Instance Type': 'N/A',
                        'Region': self.region,
                        'Hourly Cost (USD)': '0.00000000',
                        'Monthly Cost (USD)': '0.00',
                        'Is Usage Based': True,
                        'Usage Type': self.usage_based_services[service_type]['description'],
                        'Components': self.usage_based_services[service_type]['components']
                    })
                    
                    # Add to JSON structure
                    services_json[service_type] = {
                        'usage_type': self.usage_based_services[service_type]['description'],
                        'hourly_cost': 0.0,
                        'daily_cost': 0.0,
                        'monthly_cost': 0.0,
                        'specifications': {
                            'pricing_components': self.usage_based_services[service_type]['components']
                        }
                    }
                    continue
                
                # Get instance type from node if available
                instance_type = node.get('InstanceType') or node.get('DBInstanceClass') or node.get('LaunchConfiguration', {}).get('InstanceType')
                
                # Calculate cost for non-usage-based services
                cost_info = self.pricing_api.calculate_service_cost(service_type, instance_type)
                
                if cost_info['hourly_cost'] > 0:
                    total_hourly_cost += cost_info['hourly_cost']
                    total_monthly_cost += cost_info['monthly_cost']
                    
                    service_details.append({
                        'Service': service_type,
                        'Instance Type': cost_info['details'].get('Instance Type', 'N/A'),
                        'Region': cost_info['details']['Region'],
                        'Hourly Cost (USD)': f"{cost_info['hourly_cost']:.8f}",
                        'Monthly Cost (USD)': f"{cost_info['monthly_cost']:.2f}",
                        'Specifications': cost_info['details'].get('Attributes', {}),
                        'Is Usage Based': False
                    })
                    
                    # Add to JSON structure
                    services_json[service_type] = {
                        'instance_type': cost_info['details'].get('Instance Type', 'N/A'),
                        'hourly_cost': float(cost_info['hourly_cost']),
                        'daily_cost': float(cost_info['hourly_cost'] * 24),
                        'monthly_cost': float(cost_info['monthly_cost']),
                        'specifications': cost_info['details'].get('Attributes', {})
                    }
                else:
                    self.logger.warning(f"No pricing data found for {service_type}")

            # Create JSON report
            report_json = {
                'architecture_name': architecture.get('name', 'AWS_Architecture'),
                'region': self.region,
                'generation_date': datetime.now().isoformat(),
                'total_hourly_cost': float(total_hourly_cost),
                'total_daily_cost': float(total_hourly_cost * 24),
                'total_monthly_cost': float(total_monthly_cost),
                'services': services_json
            }

            # Save JSON report
            with open('cost_report.json', 'w') as f:
                json.dump(report_json, f, indent=4)

            # Print cost report
            self._print_cost_report(service_details, total_hourly_cost, total_monthly_cost)
            return True

        except FileNotFoundError:
            self.logger.error(f"Architecture file not found: {architecture_file}")
            return False
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON in architecture file: {architecture_file}")
            return False
        except Exception as e:
            self.logger.error(f"Error calculating costs: {e}")
            return False

    def _print_cost_report(self, service_details, total_hourly_cost, total_monthly_cost):
        """Print a detailed cost report."""
        print(f"\nCost Report for AWS Architecture")
        print(f"Region: {self.region}")
        print("-" * 60)
        
        # Print all services
        if service_details:
            print("\nServices:")
            print("-" * 40)
            for service in service_details:
                print(f"\n{service['Service']}:")
                print(f"Region: {service['Region']}")
                
                if not service['Is Usage Based']:
                    print(f"Instance Type: {service['Instance Type']}")
                    print(f"Hourly Cost: ${service['Hourly Cost (USD)']}")
                    print(f"Monthly Cost: ${service['Monthly Cost (USD)']}")
                    
                    # Print specifications if available
                    specs = service.get('Specifications', {})
                    if specs:
                        print("Specifications:")
                        for key, value in specs.items():
                            print(f"  {key}: {value}")
                else:
                    print(f"Usage Type: {service['Usage Type']}")
                    print("Pricing Components:")
                    for component in service['Components']:
                        print(f"  - {component}")
                    print("Note: Cost depends on actual usage")
                
                print("-" * 40)
        
        print("\nSummary:")
        print("-" * 60)
        print(f"Total Hourly Cost: ${total_hourly_cost:.8f}")
        print(f"Total Daily Cost: ${total_hourly_cost * 24:.8f}")
        print(f"Total Monthly Cost: ${total_monthly_cost:.2f}")
        print("\nNote: Usage-based services require actual usage data for accurate pricing.")
        print(f"\nDetailed report saved to cost_report.json") 