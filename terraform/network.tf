# Using the default VPC to keep this scoped to a portfolio-sized project.
# Note: default VPC subnets are public. RDS access is still restricted by
# security group, not subnet isolation. Real production would use private
# subnets + a NAT gateway for the app tier. See README "what's simplified".

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}
