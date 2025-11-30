"""
Example client code to call the API Gateway endpoint and download files
"""
import requests
import base64
import zipfile
from io import BytesIO

# Your API Gateway endpoint URL
API_URL = "https://your-api-id.execute-api.us-east-1.amazonaws.com/prod/convert"

# Read your CSV file
with open("examples/example.csv", "rb") as f:
    csv_content = f.read()

# Encode to base64
csv_base64 = base64.b64encode(csv_content).decode('utf-8')

# Option 1: Get ZIP file with both CSV and Excel (default)
print("Downloading ZIP file...")
response = requests.post(
    API_URL,
    json={"csv_data": csv_base64},
    headers={"Content-Type": "application/json"}
)

if response.status_code == 200:
    zip_data = base64.b64decode(response.content)
    with open("converted_files.zip", "wb") as f:
        f.write(zip_data)
    print("✅ ZIP file saved as converted_files.zip")
    
    # Extract files from ZIP
    with zipfile.ZipFile(BytesIO(zip_data), 'r') as zip_ref:
        zip_ref.extractall("converted")
    print("✅ Files extracted to converted/ directory")
else:
    print(f"Error: {response.status_code}")
    print(response.text)

# Option 2: Get only CSV file
print("\nDownloading CSV file only...")
response = requests.post(
    f"{API_URL}?format=csv",
    json={"csv_data": csv_base64},
    headers={"Content-Type": "application/json"}
)

if response.status_code == 200:
    with open("converted.csv", "wb") as f:
        f.write(base64.b64decode(response.content))
    print("✅ CSV file saved as converted.csv")
else:
    print(f"Error: {response.status_code}")

# Option 3: Get only Excel file
print("\nDownloading Excel file only...")
response = requests.post(
    f"{API_URL}?format=xlsx",
    json={"csv_data": csv_base64},
    headers={"Content-Type": "application/json"}
)

if response.status_code == 200:
    with open("converted.xlsx", "wb") as f:
        f.write(base64.b64decode(response.content))
    print("✅ Excel file saved as converted.xlsx")
else:
    print(f"Error: {response.status_code}")

