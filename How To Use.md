# AWS Cost Estimator - How To Use Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Project Structure](#project-structure)
5. [Configuration](#configuration)
6. [Architecture Definition](#architecture-definition)
7. [Running the Cost Estimator](#running-the-cost-estimator)
8. [Understanding the Results](#understanding-the-results)
9. [Supported Services](#supported-services)
10. [Troubleshooting](#troubleshooting)

## Introduction

The AWS Cost Estimator is a Python-based tool that helps you estimate costs for AWS architectures. It uses the AWS Pricing API to provide accurate cost estimates for various AWS services, including both fixed-cost and usage-based services.

## Prerequisites

- Python 3.6 or higher
- pip (Python package installer)
- AWS credentials (Access Key and Secret Key)
- Basic understanding of AWS services

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd aws-cost-estimator
```

2. Install required Python packages:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your AWS credentials:
```
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=ap-south-1
```

## Project Structure

```
aws-cost-estimator/
├── aws_pricing_api.py      # AWS Pricing API interaction
├── cost_estimator.py       # Core cost estimation logic
├── main.py                # Main entry point
├── test_architecture.json  # Sample architecture
├── requirements.txt        # Project dependencies
├── .env                   # Environment configuration
└── README.md              # Documentation
```

## Configuration

The tool uses environment variables for configuration. Create a `.env` file with:
- AWS_ACCESS_KEY_ID: Your AWS access key
- AWS_SECRET_ACCESS_KEY: Your AWS secret key
- AWS_REGION: Your preferred AWS region (default: ap-south-1)

## Architecture Definition

Create a JSON file defining your AWS architecture. The file should follow this structure:

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

### Supported Service Types:
- AmazonEC2
- AmazonRDS
- AmazonS3
- AWSLambda
- Other usage-based services

## Running the Cost Estimator

1. Basic usage:
```bash
python main.py
```

The script will:
1. Load your architecture from test_architecture.json
2. Calculate costs using the AWS Pricing API
3. Display a detailed cost report

## Understanding the Results

The tool provides a detailed cost report with:

1. Fixed-Cost Services (e.g., EC2, RDS):
   - Instance type
   - Hourly cost
   - Monthly cost
   - Detailed specifications

2. Usage-Based Services (e.g., S3, Lambda):
   - Service type
   - Usage components
   - Pricing factors
   - Note about usage-based pricing

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

AmazonS3:
Usage Type: Storage, requests, and data transfer
Pricing Components:
  - Storage (per GB per month)
  - Data Transfer (per GB)
  - Requests (per 1000 requests)
Note: Cost depends on actual usage

Summary:
------------------------------------------------------------
Total Hourly Cost: $0.48170000
Total Monthly Cost: $346.82
```

## Supported Services

### Fixed-Cost Services
- EC2: All instance types
- RDS: All instance types

### Usage-Based Services
- S3: Storage, requests, data transfer
- Lambda: Compute time, requests
- DynamoDB: Storage, read/write capacity
- SNS: Message delivery, data transfer
- CloudWatch: Metrics, logs, alarms
- API Gateway: API calls, data transfer
- ElastiCache: Cache nodes, data transfer

## Troubleshooting

### Common Issues

1. AWS Credentials
   - Verify credentials in .env file
   - Check AWS region setting
   - Ensure AWS Pricing API access

2. Invalid Architecture File
   - Check JSON syntax
   - Verify service types
   - Check instance type names

3. Zero Costs
   - Verify service configuration
   - Check if service is usage-based
   - Verify AWS Pricing API response

### Getting Help

If you encounter issues:
1. Check error messages
2. Verify AWS credentials
3. Review architecture file format
4. Check supported services list

## Best Practices

1. Use correct service types
2. Specify instance types where applicable
3. Document architecture assumptions
4. Review cost estimates regularly
5. Consider usage patterns for usage-based services

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 