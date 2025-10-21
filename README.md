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
- sample/                     # Sample JSON files and their generated outputs


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
