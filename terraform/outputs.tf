output "ec2_public_ip" {
  description = "Public IP address of the Mantra application server"
  value       = aws_instance.app_server.public_ip
}

output "ec2_instance_id" {
  description = "ID of the Mantra EC2 instance"
  value       = aws_instance.app_server.id
}

output "vpc_id" {
  description = "ID of the Mantra VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_id" {
  description = "ID of the public subnet"
  value       = aws_subnet.public.id
}

output "s3_bucket_name" {
  description = "Name of the S3 documents bucket"
  value       = aws_s3_bucket.documents.id
}

output "s3_bucket_arn" {
  description = "ARN of the S3 documents bucket"
  value       = aws_s3_bucket.documents.arn
}

output "engineer1_iam_policy_arn" {
  description = "ARN of the IAM developer policy to attach to Engineer 1"
  value       = aws_iam_policy.developer_policy.arn
}
