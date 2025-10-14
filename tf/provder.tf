terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "evcon-tfstate-bucket"
    key    = "rmind/terraform.tfstate"
    region = "us-east-2"
    dynamodb_table = "evcon-tfstate-locks"
  }
}

provider "aws" {
  region = "us-east-2"
}
