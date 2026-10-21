terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "mantra-terraform-state-2026"
    key            = "prod/mantra.tfstate"
    region         = "us-east-1"
    dynamodb_table = "mantra-terraform-locks"
  }
}
