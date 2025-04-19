import requests
import zipfile
import os
import warnings
import pandas as pd
import glob
import shutil
import google.auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials
import base64
import json

# Toronto Open Data is stored in a CKAN instance. It's APIs are documented here:
# https://docs.ckan.org/en/latest/api/

# To hit our API, you'll be making requests to:
base_url = "https://ckan0.cf.opendata.inter.prod-toronto.ca"

# Datasets are called "packages". Each package can contain many "resources"
# To retrieve the metadata for this package and its resources, use the package name in this page's URL:
url = base_url + "/api/3/action/package_show"
params = { "id": "311-service-requests-customer-initiated"}
package = requests.get(url, params = params).json()

# To get resource data:
for idx, resource in enumerate(package["result"]["resources"]):

    # To get metadata for non datastore_active resources:
    if not resource["datastore_active"]:
        url = base_url + "/api/3/action/resource_show?id=" + resource["id"]
        resource_metadata = requests.get(url).json()
        print(resource_metadata)
        # From here, you can use the "url" attribute to download this file
            # For example, to download the first resource:

    if idx == 0:
        url = resource_metadata["result"]["url"]
        response = requests.get(url)
        # Save the file locally
        with open("311_data.zip", "wb") as file:
            file.write(response.content)
            print("Downloaded:", url)

if os.path.exists("311_data/"):
    shutil.rmtree("311_data/")

# Extract the zip file
with zipfile.ZipFile("311_data.zip", "r") as zip_ref:
    zip_ref.extractall("311_data")
    print("Extracted 311 data to '311_data' directory")

# Clean up the zip file
os.remove("311_data.zip")
print("Removed zip file")

# Prune the CSV file
# Keep only rows where column "Ward" is "Spadina-Fort York (10)"

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
# Set the path to the directory containing the CSV files
directory_path = "311_data"
# Get a list of all CSV files in the directory
csv_files = glob.glob(os.path.join(directory_path, "*.csv"))
# Loop through each CSV file
for csv_file in csv_files:
    try:
        # Read the CSV file into a DataFrame
        try:
            df = pd.read_csv(csv_file, low_memory=False, on_bad_lines='skip', encoding='latin1')
        except pd.errors.ParserError as parse_error:
            print(f"Parser error in {csv_file}: {parse_error}")
            continue

        # Check if both "Ward" and "Service Request Type" columns exist in the DataFrame
        if "Ward" in df.columns and "Service Request Type" in df.columns:
            # Filter the DataFrame to keep only rows where "Ward" is "Spadina-Fort York (10)"
            # and "Service Request Type" contains "Coyote"
            filtered_df = df[
                (df["Ward"] == "Spadina-Fort York (10)") &
                (df["Service Request Type"].astype(str).str.contains("Coyote", na=False))
            ]
            # Overwrite the original file with the filtered DataFrame
            filtered_df.to_csv(csv_file, index=False)
            print(f"Filtered data saved to: {csv_file}")
        else:
            missing_columns = []
            if "Ward" not in df.columns:
                missing_columns.append("Ward")
            if "Service Request Type" not in df.columns:
                missing_columns.append("Service Request Type")
            print(f"Missing columns {missing_columns} in {csv_file}. Skipping this file.")
    except Exception as e:
        print(f"Error processing {csv_file}: {e}")

# Upload the filtered data to Google Drive as a Google Sheets file using Google API and credentials

def upload_files_to_drive_as_sheets(folder_id, file_path):
    # Load credentials from service account key file or environment variable
    try:
        if os.path.exists("services_account.json"):
            creds = Credentials.from_service_account_file("services_account.json")
            print("Using credentials from 'services_account.json'")
        else:
            encoded_creds = os.getenv(' GOOGLE_SECRET ')
            if not encoded_creds:
                print("Error: ' GOOGLE_SECRET ' environment variable not found. Please set it in your environment.")
                return
            decoded_creds = base64.b64decode(encoded_creds).decode('utf-8')
            creds_dict = json.loads(decoded_creds)
            creds = Credentials.from_service_account_info(creds_dict)
            print("Using credentials from ' GOOGLE_SECRET ' environment variable")
    except Exception as e:
        print(f"Error loading credentials: {e}")
        return

    # Authenticate and create the Drive API client
    drive_service = build('drive', 'v3', credentials=creds)

    # Check if a file with the same name already exists in the folder
    query = f"'{folder_id}' in parents and name='{os.path.basename(file_path).replace('.csv', '')}' and trashed=false"
    response = drive_service.files().list(q=query, fields="files(id)").execute()
    existing_files = response.get('files', [])

    if existing_files:
        # If a file exists, update its contents
        file_id = existing_files[0]['id']
        media = MediaFileUpload(file_path, mimetype='text/csv')
        drive_service.files().update(fileId=file_id, media_body=media).execute()
        print(f"Updated existing Google Sheets file with ID: {file_id}")
    else:
        # If no file exists, upload a new file as Google Sheets
        file_metadata = {
            'name': os.path.basename(file_path).replace('.csv', ''),
            'parents': [folder_id],
            'mimeType': 'application/vnd.google-apps.spreadsheet'
        }
        media = MediaFileUpload(file_path, mimetype='text/csv')
        file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f"Uploaded {file_path} as Google Sheets to Google Drive with ID: {file.get('id')}")

# Replace with your Google Drive folder ID
# Replace with your actual Google Drive folder ID and ensure the service account has access
folder_id = '1o5nGvVRB918RqwOzFSkdH0FCj708nKZ1'
# Upload each filtered CSV file to Google Drive as Google Sheets
for csv_file in csv_files:
    upload_files_to_drive_as_sheets(folder_id, csv_file)
    print(f"Uploaded {csv_file} as Google Sheets to Google Drive")