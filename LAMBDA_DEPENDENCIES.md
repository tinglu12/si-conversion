# Lambda Dependencies Guide

## Current Setup (ZIP Deployment)

The GitHub Actions workflow installs dependencies directly into the deployment package. This works for packages up to:
- **50MB** zipped
- **250MB** unzipped

Pandas + openpyxl should fit within these limits.

## If Package is Too Large

If you get errors about package size, use one of these alternatives:

### Option 1: Lambda Layers (Recommended)

Create a separate layer for dependencies:

1. **Create a layer deployment script** (`deploy-layer.sh`):

```bash
#!/bin/bash
mkdir -p layer/python
pip install -r requirements.txt -t layer/python/
cd layer
zip -r ../layer.zip python/
cd ..

# Publish layer
aws lambda publish-layer-version \
    --layer-name csv-conversion-deps \
    --zip-file fileb://layer.zip \
    --compatible-runtimes python3.11

# Note the Layer ARN from output
```

2. **Attach layer to your Lambda function**:

```bash
aws lambda update-function-configuration \
    --function-name your-function-name \
    --layers arn:aws:lambda:REGION:ACCOUNT:layer:csv-conversion-deps:VERSION
```

3. **Update GitHub Actions** to only package your code (not dependencies)

### Option 2: Container Image

For very large dependencies, use a container image:

1. **Create Dockerfile** (already created in repo)
2. **Build and push to ECR**
3. **Update Lambda to use container image**

## Manual Installation (For Testing)

If you want to test locally or manually deploy:

```bash
# Create build directory
mkdir -p build

# Install dependencies
pip install -r requirements.txt -t build/

# Copy your code
cp -r src/* build/

# Create zip
cd build
zip -r ../lambda.zip .

# Deploy
aws lambda update-function-code \
    --function-name your-function-name \
    --zip-file fileb://lambda.zip
```

## Troubleshooting

### "No module named 'pandas'"
- ✅ Check `requirements.txt` has pandas
- ✅ Verify dependencies are in the zip (unzip and check)
- ✅ Ensure handler is correct: `lambda_function.lambda_handler`

### Package too large
- Use Lambda Layers (Option 1 above)
- Or switch to Container Image (Option 2)

### Import errors with native extensions
- Make sure you're building on Linux (GitHub Actions uses Linux)
- Don't install on Mac/Windows and expect it to work in Lambda

## Verify Installation

After deployment, check CloudWatch logs to see if imports work:
```bash
aws logs tail /aws/lambda/your-function-name --follow
```

