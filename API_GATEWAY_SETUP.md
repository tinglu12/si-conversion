# API Gateway Setup Guide

This guide walks you through setting up API Gateway to work with your Lambda function for CSV conversion.

## Prerequisites

- AWS Lambda function deployed (via GitHub Actions)
- AWS CLI configured (optional, for CLI setup)
- AWS Console access

## Option 1: AWS Console Setup (Recommended for First Time)

### Step 1: Create REST API

1. Go to **API Gateway** in AWS Console
2. Click **Create API**
3. Choose **REST API** → **Build**
4. Select **New API**
5. Enter:
   - **API name**: `csv-conversion-api`
   - **Description**: `API for CSV conversion service`
   - **Endpoint Type**: Regional (or Edge if you want CloudFront)
6. Click **Create API**

### Step 2: Create Resource and Method

1. In the API, click **Actions** → **Create Resource**
2. Enter:
   - **Resource Name**: `convert`
   - **Resource Path**: `convert`
   - Check **Enable API Gateway CORS**
3. Click **Create Resource**

4. With `/convert` selected, click **Actions** → **Create Method**
5. Select **POST** from dropdown → Click checkmark
6. Configure:
   - **Integration type**: Lambda Function
   - **Use Lambda Proxy integration**: ✅ Check this
   - **Lambda Region**: Your region (e.g., `us-east-1`)
   - **Lambda Function**: `csv-conversion` (or your function name)
7. Click **Save** → **OK** (when prompted to give API Gateway permission)

### Step 3: Configure Binary Media Types

**Critical for file downloads!**

1. Click on your API name (root)
2. Go to **Settings** tab
3. Under **Binary Media Types**, click **Add Binary Media Type**
4. Add these types (one at a time or comma-separated):
   - `application/zip`
   - `text/csv`
   - `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
   - `*/*` (optional, accepts all binary types)
5. Click **Save Changes**

### Step 4: Enable CORS

1. Select the `/convert` resource
2. Click **Actions** → **Enable CORS**
3. Configure:
   - **Access-Control-Allow-Origin**: `*` (or your domain)
   - **Access-Control-Allow-Headers**: `Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token`
   - **Access-Control-Allow-Methods**: `POST,OPTIONS`
4. Click **Enable CORS and replace existing CORS headers**

### Step 5: Deploy API

1. Click **Actions** → **Deploy API**
2. Select:
   - **Deployment stage**: `[New Stage]` (first time) or existing stage
   - **Stage name**: `prod` (or `dev`, `staging`)
   - **Stage description**: `Production deployment`
3. Click **Deploy**
4. **Copy the Invoke URL** - you'll need this!

Your API endpoint will be: `https://{api-id}.execute-api.{region}.amazonaws.com/prod/convert`

### Step 6: Test the API

1. Select the `/convert` resource → **POST** method
2. Click **TEST**
3. In **Request Body**, enter:
   ```json
   {
     "csv_data": "base64_encoded_csv_here"
   }
   ```
4. Click **Test**
5. Check the response - should return base64-encoded file

## Option 2: AWS CLI Setup

Save this as `setup-api-gateway.sh`:

```bash
#!/bin/bash

# Configuration
API_NAME="csv-conversion-api"
LAMBDA_FUNCTION_NAME="csv-conversion"
REGION="us-east-1"
STAGE_NAME="prod"

# Create REST API
API_ID=$(aws apigateway create-rest-api \
    --name $API_NAME \
    --description "API for CSV conversion service" \
    --endpoint-configuration types=REGIONAL \
    --region $REGION \
    --query 'id' \
    --output text)

echo "Created API: $API_ID"

# Get root resource ID
ROOT_RESOURCE_ID=$(aws apigateway get-resources \
    --rest-api-id $API_ID \
    --region $REGION \
    --query 'items[?path==`/`].id' \
    --output text)

echo "Root resource ID: $ROOT_RESOURCE_ID"

# Create /convert resource
CONVERT_RESOURCE_ID=$(aws apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $ROOT_RESOURCE_ID \
    --path-part convert \
    --region $REGION \
    --query 'id' \
    --output text)

echo "Created /convert resource: $CONVERT_RESOURCE_ID"

# Get Lambda function ARN
LAMBDA_ARN=$(aws lambda get-function \
    --function-name $LAMBDA_FUNCTION_NAME \
    --region $REGION \
    --query 'Configuration.FunctionArn' \
    --output text)

echo "Lambda ARN: $LAMBDA_ARN"

# Give API Gateway permission to invoke Lambda
aws lambda add-permission \
    --function-name $LAMBDA_FUNCTION_NAME \
    --statement-id apigateway-invoke \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:$REGION:*:$API_ID/*/*" \
    --region $REGION

# Create POST method
aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $CONVERT_RESOURCE_ID \
    --http-method POST \
    --authorization-type NONE \
    --region $REGION

# Set up Lambda integration
aws apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $CONVERT_RESOURCE_ID \
    --http-method POST \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri "arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/$LAMBDA_ARN/invocations" \
    --region $REGION

# Configure binary media types
aws apigateway update-rest-api \
    --rest-api-id $API_ID \
    --patch-ops \
        op=add,path=/binaryMediaTypes,value=application/zip \
        op=add,path=/binaryMediaTypes,value=text/csv \
        op=add,path=/binaryMediaTypes,value=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet \
    --region $REGION

# Enable CORS
aws apigateway put-method-response \
    --rest-api-id $API_ID \
    --resource-id $CONVERT_RESOURCE_ID \
    --http-method OPTIONS \
    --status-code 200 \
    --response-parameters method.response.header.Access-Control-Allow-Headers=false,method.response.header.Access-Control-Allow-Methods=false,method.response.header.Access-Control-Allow-Origin=false \
    --region $REGION

# Create OPTIONS method for CORS preflight
aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $CONVERT_RESOURCE_ID \
    --http-method OPTIONS \
    --authorization-type NONE \
    --region $REGION

# Create mock integration for OPTIONS
aws apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $CONVERT_RESOURCE_ID \
    --http-method OPTIONS \
    --type MOCK \
    --request-templates '{"application/json":"{\"statusCode\":200}"}' \
    --region $REGION

# Set CORS response headers
aws apigateway put-integration-response \
    --rest-api-id $API_ID \
    --resource-id $CONVERT_RESOURCE_ID \
    --http-method OPTIONS \
    --status-code 200 \
    --response-parameters '{"method.response.header.Access-Control-Allow-Headers":"'\''Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'\''","method.response.header.Access-Control-Allow-Origin":"'\''*'\''","method.response.header.Access-Control-Allow-Methods":"'\''POST,OPTIONS'\''"}' \
    --region $REGION

# Deploy API
aws apigateway create-deployment \
    --rest-api-id $API_ID \
    --stage-name $STAGE_NAME \
    --region $REGION

echo ""
echo "✅ API Gateway setup complete!"
echo "API ID: $API_ID"
echo "Endpoint: https://$API_ID.execute-api.$REGION.amazonaws.com/$STAGE_NAME/convert"
```

Make it executable and run:

```bash
chmod +x setup-api-gateway.sh
./setup-api-gateway.sh
```

## Option 3: Terraform Setup

If you prefer Infrastructure as Code, here's a Terraform configuration:

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "lambda_function_name" {
  default = "csv-conversion"
}

variable "region" {
  default = "us-east-1"
}

data "aws_lambda_function" "csv_conversion" {
  function_name = var.lambda_function_name
}

resource "aws_api_gateway_rest_api" "csv_conversion_api" {
  name        = "csv-conversion-api"
  description = "API for CSV conversion service"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  binary_media_types = [
    "application/zip",
    "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
  ]
}

resource "aws_api_gateway_resource" "convert" {
  rest_api_id = aws_api_gateway_rest_api.csv_conversion_api.id
  parent_id   = aws_api_gateway_rest_api.csv_conversion_api.root_resource_id
  path_part   = "convert"
}

resource "aws_api_gateway_method" "post" {
  rest_api_id   = aws_api_gateway_rest_api.csv_conversion_api.id
  resource_id   = aws_api_gateway_resource.convert.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lambda" {
  rest_api_id = aws_api_gateway_rest_api.csv_conversion_api.id
  resource_id = aws_api_gateway_resource.convert.id
  http_method = aws_api_gateway_method.post.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = data.aws_lambda_function.csv_conversion.invoke_arn
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.csv_conversion_api.execution_arn}/*/*"
}

resource "aws_api_gateway_method" "options" {
  rest_api_id   = aws_api_gateway_rest_api.csv_conversion_api.id
  resource_id   = aws_api_gateway_resource.convert.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options" {
  rest_api_id = aws_api_gateway_rest_api.csv_conversion_api.id
  resource_id = aws_api_gateway_resource.convert.id
  http_method = aws_api_gateway_method.options.http_method
  type        = "MOCK"
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "options" {
  rest_api_id = aws_api_gateway_rest_api.csv_conversion_api.id
  resource_id = aws_api_gateway_resource.convert.id
  http_method = aws_api_gateway_method.options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods"   = true
    "method.response.header.Access-Control-Allow-Origin"    = true
  }
}

resource "aws_api_gateway_integration_response" "options" {
  rest_api_id = aws_api_gateway_rest_api.csv_conversion_api.id
  resource_id = aws_api_gateway_resource.convert.id
  http_method = aws_api_gateway_method.options.http_method
  status_code = aws_api_gateway_method_response.options.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

resource "aws_api_gateway_deployment" "prod" {
  depends_on = [
    aws_api_gateway_integration.lambda,
    aws_api_gateway_integration.options,
  ]

  rest_api_id = aws_api_gateway_rest_api.csv_conversion_api.id
  stage_name   = "prod"
}

output "api_endpoint" {
  value = "${aws_api_gateway_deployment.prod.invoke_url}/convert"
}
```

## Testing Your API

### Using curl:

```bash
# Get ZIP file (default)
curl -X POST https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/prod/convert \
  -H "Content-Type: application/json" \
  -d '{"csv_data":"base64_encoded_csv"}' \
  --output converted_files.zip

# Get CSV only
curl -X POST "https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/prod/convert?format=csv" \
  -H "Content-Type: application/json" \
  -d '{"csv_data":"base64_encoded_csv"}' \
  --output converted.csv

# Get Excel only
curl -X POST "https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/prod/convert?format=xlsx" \
  -H "Content-Type: application/json" \
  -d '{"csv_data":"base64_encoded_csv"}' \
  --output converted.xlsx
```

### Using Python (from example_client.py):

Update the `API_URL` in `example_client.py` with your endpoint URL.

## Important Notes

1. **Binary Media Types**: Must be configured for file downloads to work properly
2. **Lambda Proxy Integration**: Required for proper request/response handling
3. **CORS**: Enable if calling from a web browser
4. **Deployment**: Must deploy after any changes for them to take effect
5. **API Keys/Usage Plans**: Optional, but recommended for production

## Troubleshooting

### Files download as text instead of binary

- Check that binary media types are configured
- Verify `isBase64Encoded: true` in Lambda response

### CORS errors

- Ensure CORS is enabled on the resource
- Check that OPTIONS method is configured
- Verify response headers include CORS headers

### 502 Bad Gateway

- Check CloudWatch logs for Lambda errors
- Verify Lambda function has proper permissions
- Check that integration type is AWS_PROXY

### 403 Forbidden

- Verify API Gateway has permission to invoke Lambda
- Check if API keys are required (if so, include in request)

## Next Steps

1. Set up API keys and usage plans for rate limiting
2. Configure custom domain (optional)
3. Set up CloudWatch alarms for monitoring
4. Add API Gateway caching if needed
5. Set up WAF rules for security
