data "aws_caller_identity" "current" {}

resource "aws_iam_role_policy_attachment" "ssm_agent" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_cloudwatch_log_group" "application_sessions" {
  name              = "/mantra/application-sessions"
  retention_in_days = 14
}

resource "aws_ssm_document" "application_shell" {
  name            = "${var.project_name}-application-shell"
  document_type   = "Session"
  document_format = "JSON"
  content = jsonencode({
    schemaVersion = "1.0"
    description   = "Application engineer shell as the dedicated non-admin Linux account"
    sessionType   = "Standard_Stream"
    inputs = {
      s3BucketName                = ""
      s3KeyPrefix                 = ""
      s3EncryptionEnabled         = true
      cloudWatchLogGroupName      = aws_cloudwatch_log_group.application_sessions.name
      cloudWatchEncryptionEnabled = false
      cloudWatchStreamingEnabled  = true
      kmsKeyId                    = ""
      runAsEnabled                = true
      runAsDefaultUser            = "mantra-app"
      idleSessionTimeout          = "20"
      maxSessionDuration          = "60"
      shellProfile = {
        windows = ""
        linux   = "cd /home/mantra-app/work; umask 077"
      }
    }
  })
}

resource "aws_iam_user_policy" "application_ec2_sessions" {
  name = "${var.project_name}-application-ec2-sessions"
  user = aws_iam_user.engineer1.name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "StartOnlyApprovedApplicationSession"
        Effect   = "Allow"
        Action   = "ssm:StartSession"
        Resource = [aws_instance.app_server.arn, aws_ssm_document.application_shell.arn]
        Condition = {
          BoolIfExists = { "ssm:SessionDocumentAccessCheck" = "true" }
        }
      },
      {
        Sid         = "DenyOtherTargetsAndSessionDocuments"
        Effect      = "Deny"
        Action      = "ssm:StartSession"
        NotResource = [aws_instance.app_server.arn, aws_ssm_document.application_shell.arn]
      },
      {
        Sid      = "OwnSessionChannels"
        Effect   = "Allow"
        Action   = ["ssmmessages:OpenDataChannel", "ssm:ResumeSession", "ssm:TerminateSession"]
        Resource = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:session/${aws_iam_user.engineer1.name}-*"
      },
      {
        Sid      = "ReadApprovedDocument"
        Effect   = "Allow"
        Action   = ["ssm:GetDocument", "ssm:DescribeDocument"]
        Resource = aws_ssm_document.application_shell.arn
      },
      {
        Sid    = "ReadConnectionMetadata"
        Effect = "Allow"
        Action = [
          "ssm:DescribeInstanceInformation", "ssm:DescribeInstanceProperties",
          "ssm:DescribeSessions", "ssm:GetConnectionStatus", "ssm:ListDocuments",
          "ec2:DescribeInstances", "ec2:DescribeInstanceStatus"
        ]
        Resource = "*"
      }
    ]
  })
}

output "application_session_document" {
  value = aws_ssm_document.application_shell.name
}
