import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config')))
from config.config import config

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from textwrap import wrap
from azure.storage.blob import BlobServiceClient
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ResourceNotFoundError

# Fetch chunks from doc index, fallback to policy index
def fetch_chunks(filename):
    indexes = [config.AZURE_SEARCH_DOC_INDEX, config.AZURE_SEARCH_POLICY_INDEX]
    endpoint = config.AZURE_SEARCH_ENDPOINT
    key = config.AZURE_SEARCH_KEY
    for index_name in indexes:
        try:
            client = SearchClient(endpoint=endpoint, index_name=index_name, credential=AzureKeyCredential(key))
            if index_name == config.AZURE_SEARCH_DOC_INDEX:
                results = client.search("*", filter=f"filename eq '{filename}'", order_by=["ParagraphId asc"], select=["paragraph"])
            else:
                results = client.search("*", filter=f"filename eq '{filename}'", order_by=["InstructionId asc"], select=["instruction"])
            chunks = []
            for result in results:
                # For doc index, extract only 'paragraph'. For policy, extract only 'instruction'.
                if index_name == config.AZURE_SEARCH_DOC_INDEX:
                    paragraph = result.get('paragraph')
                    if paragraph:
                        chunks.append({'paragraph': paragraph, 'ParagraphId': result.get('ParagraphId', 0)})
                else:
                    instruction = result.get('instruction')
                    if instruction:
                        chunks.append({'content': instruction, 'ParagraphId': result.get('ParagraphId', 0)})
            if chunks:
                return chunks
        except ResourceNotFoundError:
            print(f"Index not found: {index_name}, skipping.")
            continue
        except Exception as e:
            print(f"Error accessing index {index_name}: {e}")
            continue
    return []

def generate_pdf_from_chunks(chunks, output_path):
    # Normalize chunks to dicts
    normalized_chunks = []
    for chunk in chunks:
        if isinstance(chunk, dict):
            normalized_chunks.append(chunk)
        else:
            normalized_chunks.append({'content': str(chunk)})
    # Only keep paragraphs and sort by ParagraphId
    sorted_chunks = sorted(
        [c for c in normalized_chunks if c.get('paragraph') or c.get('content')],
        key=lambda c: c.get('ParagraphId', 0)
    )
    c = canvas.Canvas(output_path, pagesize=LETTER)
    width, height = LETTER
    margin = 0.75 * inch
    y = height - margin
    max_line_length = 90
    line_height = 15
    for chunk in sorted_chunks:
        # Prefer 'paragraph' field, fallback to 'content'
        paragraph = chunk.get('paragraph') or chunk.get('content', '')
        c.setFont("Helvetica", 11)
        for line in wrap(paragraph, max_line_length):
            c.drawString(margin, y, line)
            y -= line_height
            if y < margin:
                c.showPage()
                y = height - margin
        # Start each paragraph on a new page if not enough space
        y -= line_height * 2
        if y < margin + line_height * 2:
            c.showPage()
            y = height - margin
    c.save()

def upload_pdf_to_blob(pdf_path, blob_name):
    blob_service_client = BlobServiceClient.from_connection_string(config.AZURE_STORAGE_CONNECTION_STRING)
    container_name = config.AZURE_CONTRACTS_RECONSTRUCT_CONTAINER
    container_client = blob_service_client.get_container_client(container_name)
    try:
        container_client.create_container()
    except Exception:
        pass
    with open(pdf_path, "rb") as data:
        container_client.upload_blob(name=blob_name, data=data, overwrite=True)

def regenerate_pdf(filename):
    chunks = fetch_chunks(filename)
    if not chunks:
        print(f"No chunks found for document: {filename}")
        return
    pdf_filename = f"{filename}.pdf"
    output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), pdf_filename))
    generate_pdf_from_chunks(chunks, output_path)
    upload_pdf_to_blob(output_path, pdf_filename)
    print(f"PDF regenerated and uploaded as {pdf_filename}")

if __name__ == "__main__":
    # Example: replace '20251019_014043_employee.pdfyour_filename' with an actual filename present in your index
    #regenerate_pdf("20251021_172028_employee.pdf")
    regenerate_pdf("Governing Law.docx")