# AWS Cost Estimator - How To Use Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Directory Structure](#directory-structure)
5. [AWS Pricing Data](#aws-pricing-data)
6. [Architecture Definition](#architecture-definition)
7. [Running the Cost Estimator](#running-the-cost-estimator)
8. [Understanding the Results](#understanding-the-results)
9. [Supported AWS Services](#supported-aws-services)
10. [Troubleshooting](#troubleshooting)

## Introduction

The AWS Cost Estimator is a Python-based tool that helps you estimate the monthly costs of your AWS infrastructure based on your architecture definition. It uses actual AWS pricing data to provide accurate cost estimates for various AWS services.

## Prerequisites

- Python 3.6 or higher
- pip (Python package installer)
- AWS Pricing API access (for downloading pricing data)
- Basic understanding of AWS services and their pricing models

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

3. Create the necessary directories:
```bash
mkdir -p aws_pricing_data/ap-south-1
```

## Directory Structure

```
aws-cost-estimator/
├── main.py
├── cost_estimator.py
├── requirements.txt
├── aws_pricing_data/
│   └── ap-south-1/
│       ├── AmazonEC2_pricing.json
│       ├── AmazonRDS_pricing.json
│       ├── AmazonS3_pricing.json
│       └── ... (other pricing files)
└── examples/
    ├── ai_chatbot_architecture.json
    └── multi_tier_architecture.json
```

## AWS Pricing Data

1. Download AWS pricing data files for your region:
   - EC2 pricing
   - RDS pricing
   - S3 pricing
   - Lambda pricing
   - DynamoDB pricing
   - Route53 pricing
   - CloudFront pricing
   - SNS pricing
   - ElastiCache pricing
   - AWS Config pricing

2. Place the pricing files in the `aws_pricing_data/ap-south-1/` directory

## Architecture Definition

Create a JSON file defining your AWS architecture. The file should follow this structure:

```json
{
  "nodes": [
    {
      "id": "vpc-1",
      "type": "AmazonVPC",
      "label": "Virtual Private Cloud",
      "group": "network"
    },
    {
      "id": "ec2-1",
      "type": "AmazonEC2",
      "label": "Application Server",
      "InstanceType": "t3.medium",
      "group": "compute"
    }
    // ... other nodes
  ],
  "edges": [
    {
      "from": "vpc-1",
      "to": "ec2-1"
    }
    // ... other connections
  ]
}
```

### Supported Node Types:
- AmazonVPC
- AmazonEC2
- AmazonRDS
- AmazonS3
- AmazonDynamoDB
- AWSLambda
- AmazonSNS
- AmazonElastiCache
- AmazonRoute53
- AmazonCloudFront
- AWSConfig

## Running the Cost Estimator

1. Basic usage:
```bash
python main.py examples/your_architecture.json
```

2. Specify a different region:
```bash
python main.py examples/your_architecture.json --region us-east-1
```

3. Specify a different pricing data directory:
```bash
python main.py examples/your_architecture.json --pricing-dir /path/to/pricing/data
```

## Understanding the Results

The tool will output:
1. A detailed breakdown of costs for each service
2. Total estimated monthly cost
3. A JSON file (`cost_estimate_result.json`) with the complete results

Example output:
```
Cost Estimation Results:
=======================
Virtual Private Cloud: $0.00
Application Server: $32.26
Storage Bucket: $0.20
Relational Database: $141.12
NoSQL Database: $0.00
Serverless Function: $0.00
Notification Service: $0.00
Caching Service: $30.96
Configuration Management: $0.00
Total: $204.54
```

## Supported AWS Services

### Compute Services
- EC2: Supports all instance types
- Lambda: Calculates based on memory, duration, and invocations
- RDS: Supports all instance types

### Storage Services
- S3: Calculates storage and request costs
- DynamoDB: Calculates storage, read capacity, and write capacity costs

### Network Services
- VPC: Free (costs only for resources within)
- Route53: Calculates hosted zone and query costs
- CloudFront: Calculates data transfer and request costs

### Database Services
- RDS: Supports all instance types
- DynamoDB: Supports provisioned capacity
- ElastiCache: Supports all instance types

### Other Services
- SNS: Calculates notification costs
- AWS Config: Calculates config item and rule evaluation costs

## Troubleshooting

### Common Issues

1. Missing Pricing Data
   - Ensure all required pricing files are in the correct directory
   - Check file permissions
   - Verify file format is correct

2. Invalid Architecture File
   - Check JSON syntax
   - Verify all required fields are present
   - Ensure service types are correct

3. Zero Costs
   - Check if pricing data is loaded correctly
   - Verify service configurations
   - Check logs for warnings

### Logging

The tool provides detailed logging. To enable debug logging:
```bash
export PYTHONPATH=.
python -m logging -l DEBUG main.py examples/your_architecture.json
```

### Getting Help

If you encounter issues:
1. Check the logs for error messages
2. Verify your pricing data files
3. Review the architecture file format
4. Check the supported services list

## Best Practices

1. Always use the latest pricing data
2. Keep architecture files in version control
3. Document assumptions in architecture files
4. Review cost estimates regularly
5. Use appropriate instance types
6. Consider reserved instances for long-term workloads
7. Monitor actual costs vs. estimates

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 