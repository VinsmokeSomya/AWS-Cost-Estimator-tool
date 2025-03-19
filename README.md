# AWS Architecture Cost Estimator

A simple and efficient tool for estimating AWS architecture costs. This tool calculates costs for various AWS services using the AWS Pricing API.

## Features

- **Simple Architecture Format**: Uses a straightforward JSON format for defining AWS architectures
- **Service Support**: Estimates costs for:
  - Amazon EC2 (Elastic Compute Cloud)
  - Amazon RDS (Relational Database Service)
  - Amazon S3 (Simple Storage Service)
  - AWS Lambda
  - Other usage-based services
- **Detailed Cost Breakdown**: Provides itemized costs per service and total costs (hourly and monthly)
- **Real-time AWS Pricing**: Uses AWS Pricing API for accurate, current pricing data
- **Usage-Based Service Support**: Handles services with usage-based pricing models

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

3. Set up your AWS credentials in a `.env` file:
```
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=ap-south-1
```

## Usage

### Basic Usage

```bash
python main.py
```

### Architecture JSON Format

The tool accepts a simple JSON format for architecture definition:

```json
{
  "nodes": [
    {
      "type": "AmazonEC2",
      "instance_type": "c6a.2xlarge"
    },
    {
      "type": "AmazonRDS",
      "instance_type": "db.t3.micro"
    },
    {
      "type": "AmazonS3"
    },
    {
      "type": "AWSLambda"
    }
  ]
}
```

## Project Structure

```
.
├── aws_pricing_api.py     # AWS Pricing API interaction
├── cost_estimator.py      # Core cost estimation logic
├── main.py               # Main entry point
├── test_architecture.json # Sample architecture
├── requirements.txt       # Project dependencies
├── .env                  # Environment configuration
└── README.md             # Documentation
```

## Core Components

### aws_pricing_api.py
- Handles interaction with AWS Pricing API
- Retrieves and processes pricing data
- Supports region-specific pricing

### cost_estimator.py
- Core cost calculation logic
- Handles both fixed-cost and usage-based services
- Generates detailed cost reports

### main.py
- Main entry point for the application
- Handles logging and error management
- Orchestrates the cost estimation process

## Output Format

The cost estimator provides a detailed report including:
- Service-specific details (instance types, specifications)
- Hourly and monthly costs for fixed-cost services
- Usage components for usage-based services
- Total hourly and monthly costs

Example output:
```
Cost Report for AWS Architecture
Region: ap-south-1
------------------------------------------------------------

Services:
----------------------------------------
AmazonEC2:
Instance Type: c6a.2xlarge
Hourly Cost: $0.21970000
Monthly Cost: $158.18
[Specifications...]

AmazonRDS:
Instance Type: db.t3.micro
Hourly Cost: $0.26200000
Monthly Cost: $188.64
[Specifications...]

AmazonS3:
Usage Type: Storage, requests, and data transfer
[Usage Components...]
Note: Cost depends on actual usage

Summary:
------------------------------------------------------------
Total Hourly Cost: $0.48170000
Total Monthly Cost: $346.82
```

## Contributing

Contributions are welcome! Feel free to:
1. Add support for more AWS services
2. Improve cost calculation accuracy
3. Enhance the reporting format
4. Add more example architectures

## License

[Your License Here] 