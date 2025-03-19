from cost_estimator import AWSCostEstimator
import logging

def main():
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize cost estimator
        estimator = AWSCostEstimator(region='ap-south-1')
        
        # Calculate costs for test architecture
        result = estimator.calculate_total_cost('social_media_architecture.json')
        
        if result:
            logger.info("Cost estimation completed successfully")
        else:
            logger.error("Failed to calculate costs")
            
    except Exception as e:
        logger.error(f"Error during testing: {e}")

if __name__ == "__main__":
    main() 