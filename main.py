import json
import logging
import sys
from cost_estimator import AWSCostEstimator

logging.basicConfig(level=logging.INFO)

def main():
    # Check command line arguments
    if len(sys.argv) != 2:
        print("Usage: python main.py <architecture_file>")
        sys.exit(1)

    architecture_file = sys.argv[1]
    
    try:
        # Load architecture configuration
        with open(architecture_file, 'r') as f:
            architecture = json.load(f)
        
        # Initialize cost estimator
        estimator = AWSCostEstimator()
        
        # Generate and save detailed cost report
        report = estimator.save_cost_report(architecture)
        
        # Print summary
        print("\nCost Estimation Summary:")
        print("=======================")
        print(f"Architecture: {report['architecture_name']}")
        print(f"Region: {report['region']}")
        print(f"Total Monthly Cost: ${report['total_monthly_cost']:.2f}")
        print(f"Report Generated: {report['generation_date']}")
        
        print("\nDetailed Service Costs:")
        print("======================")
        for service, details in report['services'].items():
            print(f"\n{service}:")
            print(f"  Monthly Cost: ${details['monthly_cost']:.2f}")
            print(f"  Daily Cost: ${details['daily_cost']:.2f}")
            print(f"  Hourly Cost: ${details['hourly_cost']:.4f}")
            print("  Specifications:")
            for key, value in details['specifications'].items():
                print(f"    {key}: {value}")
        
        print("\nNote: Other services (RDS, S3, Lambda, SNS) show $0.00 as their costs need to be calculated based on usage")
    
    except FileNotFoundError:
        print(f"Error: Architecture file '{architecture_file}' not found")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in architecture file '{architecture_file}'")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 