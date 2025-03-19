# AWS Architecture Cost Estimator

A flexible tool for estimating AWS architecture costs across various services. This tool can handle different JSON formats and provides detailed cost breakdowns for AWS architectures.

## Features

- **Flexible Architecture Parsing**: Handles various JSON formats for AWS architecture definitions
- **Multiple Service Support**: Estimates costs for:
  - AWS Lambda Functions
  - Amazon DynamoDB
  - Amazon S3
  - Amazon API Gateway
  - Amazon SNS
  - AWS IAM Access Analyzer
  - Amazon EC2
  - Amazon RDS
  - Amazon CloudFront
  - Amazon ElastiCache
- **Detailed Cost Breakdown**: Provides itemized costs per service and total monthly cost
- **Real-time AWS Pricing**: Can fetch and use current AWS pricing data
- **JSON Output**: Saves detailed cost estimates in JSON format

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd aws-architecture-cost-estimator
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python flexible_cost_estimator.py your_architecture.json
```

### Architecture JSON Format

The tool accepts various JSON formats. Here are some examples:

1. Node-based format:
```json
{
  "nodes": [
    {
      "id": "lambda1",
      "type": "Lambda",
      "Memory": 1024,
      "CostBreakdown": {
        "InvocationCost": 1000000,
        "ExecutionTimeCost": 1000
      }
    },
    {
      "id": "db1",
      "type": "DynamoDB",
      "Storage": 100,
      "Throughput": 25
    }
  ]
}
```

2. Service-based format:
```json
{
  "services": {
    "WebApp": {
      "type": "EC2",
      "instance_type": "t3.micro",
      "hours_per_month": 730
    },
    "Database": {
      "type": "RDS",
      "instance_type": "db.t3.micro",
      "storage_gb": 20
    }
  }
}
```

### Example Architectures

The repository includes two example architectures:
- `ai_chatbot_architecture.json`: AI Chatbot using Lambda, DynamoDB, API Gateway, etc.
- `ecommerce_architecture.json`: E-commerce platform using EC2, RDS, S3, etc.

## Project Structure

```
.
├── flexible_cost_estimator.py   # Main script for cost estimation
├── cost_estimator.py           # Core cost calculation logic
├── aws_price_downloader.py     # AWS pricing data downloader
├── delta_downloader.py         # Delta pricing data handler
├── requirements.txt            # Project dependencies
├── aws_pricing_data/          # Directory for AWS pricing data
├── logs/                      # Log files directory
└── examples/
    ├── ai_chatbot_architecture.json
    └── ecommerce_architecture.json
```

## Core Components

### flexible_cost_estimator.py
- Main entry point for cost estimation
- Handles various JSON formats
- Transforms architecture definitions into standardized format
- Provides detailed cost breakdowns

### cost_estimator.py
- Core cost calculation logic
- Service-specific pricing calculations
- Handles AWS pricing data

## AWS Pricing Data

The system can use either:
1. Real-time AWS pricing data (requires AWS credentials)
2. Cached pricing data (included in aws_pricing_data/)

To update pricing data:
```bash
python aws_price_downloader.py
```

## Output Format

The cost estimation results are saved in `cost_estimate_result.json` with the following structure:
```json
{
  "architecture_name": "Example Architecture",
  "cost_breakdown": {
    "Service1": 10.50,
    "Service2": 25.75,
    "Total": 36.25
  },
  "service_details": {
    "Service1": {
      "configuration": {},
      "monthly_cost": 10.50
    }
  },
  "monthly_total_cost": 36.25,
  "currency": "USD",
  "timestamp": "2024-03-19T12:00:00",
  "region": "us-east-1"
}
```

## Contributing

Feel free to contribute by:
1. Adding support for more AWS services
2. Improving cost calculation accuracy
3. Enhancing the architecture parsing capabilities
4. Adding more example architectures

## License

[Your License Here] 