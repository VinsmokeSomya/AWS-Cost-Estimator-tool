import logging
import sys
from cost_estimator import CostEstimator

def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Check command line arguments
    if len(sys.argv) != 2:
        print("Usage: python main.py <input_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    estimator = CostEstimator()
    costs = estimator.estimate_costs(input_file)
    
    # Print results
    print("\nCost Estimation Results:")
    print("=======================")
    for service, cost in costs.items():
        print(f"{service}: ${cost:.2f}")

if __name__ == "__main__":
    main() 