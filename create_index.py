import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
)

load_dotenv()

endpoint = os.getenv("SEARCH_ENDPOINT")
admin_key = os.getenv("SEARCH_ADMIN_KEY")
index_name = os.getenv("SEARCH_INDEX_NAME")

client = SearchIndexClient(endpoint=endpoint, credential=AzureKeyCredential(admin_key))

fields = [
    SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
    SearchableField(name="content", type=SearchFieldDataType.String),
    SimpleField(name="source_file", type=SearchFieldDataType.String, filterable=True),
    SimpleField(name="file_type", type=SearchFieldDataType.String, filterable=True),
    SimpleField(name="chunk_index", type=SearchFieldDataType.Int32, filterable=True),
    SearchField(
        name="embedding",
        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
        searchable=True,
        vector_search_dimensions=1536,
        vector_search_profile_name="default-profile",
    ),
]

vector_search = VectorSearch(
    algorithms=[HnswAlgorithmConfiguration(name="default-algorithm")],
    profiles=[VectorSearchProfile(name="default-profile", algorithm_configuration_name="default-algorithm")],
)

index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search)

result = client.create_or_update_index(index)
print(f"Index '{result.name}' created successfully.")
