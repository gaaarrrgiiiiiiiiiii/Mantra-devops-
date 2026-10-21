variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name identifier"
  type        = string
  default     = "mantra"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block for the public subnet"
  type        = string
  default     = "10.0.1.0/24"
}

variable "availability_zone" {
  description = "AWS Availability Zone for the subnet"
  type        = string
  default     = "us-east-1a"
}

variable "instance_type" {
  description = "EC2 instance type for application host"
  type        = string
  default     = "t3.medium"
}

variable "ssh_key_name" {
  description = "Name of existing EC2 Key Pair for SSH access"
  type        = string
  default     = "mantra-key"
}

variable "allowed_ssh_cidr" {
  description = "CIDR block allowed to SSH into EC2 instance"
  type        = string
  default     = "0.0.0.0/0"
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket for industrial documents storage"
  type        = string
  default     = "mantra-industrial-docs"
}
