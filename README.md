# 🎙️ Podcast Transcript Processor by Evan Benoit

This project is an AWS Lambda function that ingests podcast transcripts, validates their schema, and uses AWS Bedrock models (currently Anthropic Claude) to generate structured outputs such as summaries, takeaways, quotes, tags, and fact checks.


## 📋 Features
- Summarization, quotes, takeaways, tagging, fact-checking
- Schema enforcement so transcripts must follow the defined format.
- Robust error handling with detailed logging
- Exposed as an API Gateway endpoint with Terraform.


## 🗂️ Project Structure

- src/lambda/hello/index.py   # Main Lambda handler
- tf/                         # Terraform for deploying Lambda
- sample/                     # Sample JSON files 
- sample/output               # Generated outputs


## ⚙️ Prerequisites
- Python 3.11
- AWS CLI 
- Terraform 


## 🚀 Deployment

1. Set up an AWS account using the AWS console
2. Run `sh bootstrap-terraform.sh` to create the S3 bucket and Dynamo DB to store the Terraform state
3. In the `tf` folder, run `make deploy` to package the lambda and run the Terraform to generate the AWS resources


## 🏃‍♂️ Running 

The parser can be run four different ways:
- Locally in VSCode, using the configuration in `.vscode/launch.json`
- Locally on the command line by running `python test.py <json file name>`
- Remotely by invoking the Lambda using the API using `sh invoke.sh <json file name>`
- Remotely via the API Gateway using `sh curl-api.sh <json file name>`


## 📑 Logs

When run in AWS, all logs go to CloudWatch Logs under the log group named after the Lambda function (/aws/lambda/rmind-hello).

## 🚢 Detailed Deployment Strategy

This application is deployed as a serverless workload on AWS, with its core logic running inside an **AWS Lambda function** fronted by **Amazon API Gateway**. Supporting services include **CloudWatch Logs** for observability and **IAM** for security. Terraform manages the infrastructure as code, ensuring repeatable deployments across environments.

### 💰 Cost Considerations
The design is optimized for **pay-as-you-go** economics. AWS Lambda charges only for compute time (measured in milliseconds) and memory allocation. Given the modest runtime of transcript analysis (typically <60s), operating costs remain low for occasional or batch workloads. API Gateway similarly follows a request-based billing model. The main variable cost driver is **Bedrock API usage**, since model inference is billed per token. To control spend, you can enforce quotas (e.g., API Gateway throttling), add monitoring, or selectively disable expensive features like fact-checking. By packaging dependencies directly in the Lambda or via Layers, no additional compute resources are needed (e.g., EC2), keeping fixed infrastructure costs near zero.

### 📈 Scalability
The system is inherently **elastic**. AWS Lambda automatically scales horizontally by spawning multiple function instances in response to concurrent requests. No manual scaling policies are required. API Gateway provides built-in request handling and can sustain thousands of requests per second, with Lambda concurrency scaling behind it. The stateless design of the function ensures that each request is isolated, so scaling is only bounded by concurrency quotas, which can be increased with AWS support if needed. Persistent data (e.g., tag definitions, schema files) can be externalized into S3 or DynamoDB for near-infinite scalability without increasing Lambda package size.

### 🤨 Fault Tolerance
Fault tolerance is addressed at multiple levels. At the compute layer, Lambda is deployed across multiple **Availability Zones** within the AWS region, ensuring resilience against individual zone failures. API Gateway also operates region-wide, providing high availability out of the box. If Bedrock requests are throttled or fail transiently, the function retries with exponential backoff, reducing the chance of losing work due to temporary service issues. CloudWatch automatically captures errors and logs, enabling alerting and rapid incident response. 

For disaster recovery, the Terraform-managed infrastructure can be redeployed in another region with minimal changes, as long as Bedrock model availability is considered. Versioning of Lambda functions and staged API Gateway deployments (e.g., `dev`, `prod`) allow controlled rollouts and safe rollback in the event of faulty updates.