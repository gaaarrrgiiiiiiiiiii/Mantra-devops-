terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "mantra-terraform-state-657157860151"
    key            = "prod/mantra.tfstate"
    region         = "us-east-1"
    dynamodb_table = "mantra-terraform-locks"
  }
}
