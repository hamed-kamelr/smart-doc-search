import os
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

load_dotenv()

connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
container_name = os.getenv("BLOB_CONTAINER_NAME")
local_docs_path = os.path.join(os.path.dirname(__file__), "azure_rag_test_documents", "synthetic_documents")

blob_service_client = BlobServiceClient.from_connection_string(connection_string)
container_client = blob_service_client.get_container_client(container_name)

uploaded = 0
for subfolder in ["pdfs", "csvs", "images"]:
    folder_path = os.path.join(local_docs_path, subfolder)
    if not os.path.isdir(folder_path):
        continue
    for filename in sorted(os.listdir(folder_path)):
        file_path = os.path.join(folder_path, filename)
        if not os.path.isfile(file_path):
            continue
        blob_name = f"{subfolder}/{filename}"
        print(f"Uploading {blob_name}...", end=" ")
        blob_client = container_client.get_blob_client(blob_name)
        with open(file_path, "rb") as f:
            blob_client.upload_blob(f, overwrite=True)
        print("done")
        uploaded += 1

print(f"\nUploaded {uploaded} files to container '{container_name}'.")
