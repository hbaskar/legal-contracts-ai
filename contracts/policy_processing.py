"""
Policy Document Processing Module
Handles policy-specific document processing, analysis, and indexing
"""

import os
import json
import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel

# Import existing AI services components
from contracts.ai_services import (
    get_openai_client, 
    safe_openai_call,
    generate_text_embedding,
    process_document_content,
    get_database_manager
)
from config.config import config

# Configure logging
logger = logging.getLogger(__name__)

# Pydantic model for policy structure
class PolicyClause(BaseModel):
    """Model for structured policy data extracted by OpenAI"""
    title: str
    instruction: str
    summary: str
    tags: List[str]
    severity: int  # 1 = Critical/Mandatory, 2 = Important/Recommended

class PolicyDocument(BaseModel):
    """Model for complete policy document metadata"""
    policy_id: str
    filename: str
    document_type: str = "policy"
    total_clauses: int
    processing_method: str = "ai_policy_analysis"

def analyze_policy_with_openai(policy_text: str) -> PolicyClause:
    """
    Analyze policy text using OpenAI to extract structured information
    This replicates the functionality from policy_indexing.py
    """
    
    prompt = '''
You are a legal policy extraction assistant. Your job is to extract structured information from legal clauses.
Important rules:
- Do not translate or paraphrase.
- Keep the language the same as input.
- Keep all values precise, short and enforceable.
- The summary must be 6-7 words max, capturing the essence of the clause.
- Severity: 1 = Critical/Mandatory, 2 = Important/Recommended
- Tags should be relevant legal categories (max 5 tags)

Return structured data for this policy clause as JSON in this exact format:
{
    "title": "Brief descriptive title",
    "instruction": "The complete policy instruction text",
    "summary": "6-7 word essence",
    "tags": ["tag1", "tag2", "tag3"],
    "severity": 1
}

Policy text to analyze:
'''

    try:
        client = get_openai_client()
        
        def policy_analysis_call():
            return client.chat.completions.create(
                model=config.AZURE_OPENAI_MODEL_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Policy text to analyze:\n{policy_text}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=500,
                timeout=30
            )
        
        response = safe_openai_call("Policy Analysis", policy_analysis_call)
        
        if response and response.choices:
            response_content = response.choices[0].message.content.strip()
            
            # Clean and parse JSON response
            try:
                # Handle common JSON formatting issues
                if response_content.startswith('```json'):
                    response_content = response_content.replace('```json', '').replace('```', '').strip()
                
                parsed_data = json.loads(response_content)
                
                # Validate and create PolicyClause object
                return PolicyClause(
                    title=parsed_data.get('title', 'Untitled Policy'),
                    instruction=parsed_data.get('instruction', policy_text[:500]),
                    summary=parsed_data.get('summary', 'Policy clause')[:50],  # Ensure max length
                    tags=parsed_data.get('tags', ['general'])[:5],  # Max 5 tags
                    severity=min(2, max(1, parsed_data.get('severity', 2)))  # Ensure 1 or 2
                )
                
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse policy analysis JSON: {e}")
                logger.debug(f"Raw response: {response_content[:200]}...")
                # Fall back to structured extraction
                return extract_policy_fallback(policy_text, response_content)
        
        # Fallback if no response
        return create_fallback_policy_clause(policy_text)
        
    except Exception as e:
        logger.error(f"Error analyzing policy: {str(e)}")
        return create_fallback_policy_clause(policy_text)

def extract_policy_fallback(policy_text: str, ai_response: str = None) -> PolicyClause:
    """
    Fallback policy extraction when JSON parsing fails
    """
    try:
        # Try to extract structured data from partial response
        title = "Policy Clause"
        summary = "Policy requirement"
        tags = ["general", "policy"]
        severity = 2
        
        if ai_response:
            # Look for quoted strings that might be titles or summaries
            import re
            quotes = re.findall(r'"([^"]+)"', ai_response)
            if quotes:
                title = quotes[0][:100] if quotes else title
                summary = quotes[1][:50] if len(quotes) > 1 else summary
        
        # Generate a reasonable title from the first sentence
        if not title or title == "Policy Clause":
            sentences = policy_text.split('.')
            if sentences:
                title = sentences[0].strip()[:100]
        
        # Determine severity based on keywords
        critical_keywords = ['must', 'required', 'shall', 'mandatory', 'compliance', 'violation']
        if any(keyword.lower() in policy_text.lower() for keyword in critical_keywords):
            severity = 1
        
        return PolicyClause(
            title=title,
            instruction=policy_text,
            summary=summary,
            tags=tags,
            severity=severity
        )
        
    except Exception as e:
        logger.error(f"Fallback extraction failed: {e}")
        return create_fallback_policy_clause(policy_text)

def create_fallback_policy_clause(policy_text: str) -> PolicyClause:
    """Create a basic policy clause when all AI extraction fails"""
    return PolicyClause(
        title="Policy Analysis Failed",
        instruction=policy_text[:500] + "..." if len(policy_text) > 500 else policy_text,
        summary="Analysis failed",
        tags=["general"],
        severity=2
    )

def chunk_policy_document(policy_text: str) -> List[str]:
    """
    Chunk policy document into individual clauses for separate analysis
    Based on legal policy chunking logic
    """
    import re
    
    lines = policy_text.splitlines()
    chunks = []
    current_chunk = []

    def is_heading(line):
        # Match headings like "SECTION 1:" or "Payment Terms:"
        return bool(re.match(r"^[A-Z][A-Za-z\s\-]*:$", line.strip())) or \
               bool(re.match(r"^[A-Z][A-Za-z\s\-]*$", line.strip())) or \
               bool(re.match(r"^\d+\.", line.strip()))

    def is_definition_clause(line):
        # Match definition clauses like "Payment Terms: All payments must..."
        return bool(re.match(r"^[A-Z][a-zA-Z\s\-]+:\s+", line.strip()))

    def is_numbered_item(line):
        # Match numbered items like "1. ", "2. ", etc.
        return bool(re.match(r"^\d+\.\s+", line.strip()))

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        # Start new chunk on headings, definitions, or numbered items
        if is_heading(line) or is_definition_clause(line) or is_numbered_item(line):
            if current_chunk:
                chunk_text = " ".join(current_chunk).strip()
                if len(chunk_text) >= 30:  # Only add substantial chunks
                    chunks.append(chunk_text)
                current_chunk = []
            current_chunk.append(line)
        else:
            current_chunk.append(line)

    # Add final chunk
    if current_chunk:
        chunk_text = " ".join(current_chunk).strip()
        if len(chunk_text) >= 30:
            chunks.append(chunk_text)

    # If no meaningful chunks found, split by paragraphs
    if not chunks:
        paragraphs = [p.strip() for p in policy_text.split('\n\n') if p.strip()]
        chunks = [p for p in paragraphs if len(p) >= 30]

    # If still no chunks, create one chunk from the entire text
    if not chunks:
        chunks = [policy_text.strip()] if policy_text.strip() else []

    logger.info(f"📋 Policy chunking completed: {len(chunks)} clauses found")
    return chunks

async def process_policy_document(
    policy_text: str, 
    filename: str, 
    policy_id: str = None,
    groups: List[str] = None,
    file_id: int = None
) -> Dict[str, Any]:
    """
    Process a complete policy document: chunk, analyze, and prepare for indexing
    """
    
    logger.info(f"📋 Starting policy document processing: {filename}")
    
    if policy_id is None:
        policy_id = f"{os.path.splitext(filename)[0]}-{str(uuid.uuid4())[:8]}"
    
    if groups is None:
        groups = ["legal-team", "compliance"]
    
    # Step 1: Chunk the policy document
    logger.info(f"🔪 Chunking policy document: {filename}")
    clauses = chunk_policy_document(policy_text)
    logger.info(f"📊 Found {len(clauses)} policy clauses")
    
    if not clauses:
        logger.warning(f"⚠️ No policy clauses found in {filename}")
        return {
            "status": "warning",
            "message": f"No policy clauses could be extracted from {filename}",
            "clauses_processed": 0,
            "policy_records": [],
            "chunk_id_mapping": {}
        }
    
    # Get database manager for chunk persistence
    db_mgr = get_database_manager()
    chunk_id_mapping = {}  # Maps policy_record index to database chunk_id
    
    # Step 2: Analyze each clause with OpenAI
    processed_policies = []
    successful_analyses = 0
    
    for i, clause in enumerate(clauses):
        try:
            logger.info(f"🧠 Analyzing clause {i+1}/{len(clauses)}...")
            
            # Extract structured data using OpenAI
            structured = analyze_policy_with_openai(clause)
            
            # Generate embedding for the instruction text
            try:
                embedding = generate_text_embedding(structured.instruction)
            except Exception as e:
                logger.warning(f"Failed to generate embedding for clause {i+1}: {e}")
                embedding = None
            
            # Save policy clause chunk to local database if available
            chunk_id = None
            if db_mgr and file_id:
                try:
                    chunk_id = await db_mgr.save_document_chunk(
                        file_id=file_id,
                        chunk_index=i,  # 0-based index
                        chunk_method="policy_clause_analysis",
                        chunk_text=clause.strip(),
                        keyphrases=structured.tags,  # Use policy tags as keyphrases
                        ai_summary=structured.summary,
                        ai_title=structured.title
                    )
                    logger.debug(f"💾 Saved policy clause {i+1} to database with ID: {chunk_id}")
                    chunk_id_mapping[successful_analyses] = chunk_id
                    
                except Exception as e:
                    logger.warning(f"Failed to save policy clause {i+1} to database: {e}")
            
            # Prepare policy record for indexing (matches policy index schema)
            policy_record = {
                "id": str(uuid.uuid4()),
                "PolicyId": policy_id,
                "filename": filename,
                "title": structured.title,
                "instruction": structured.instruction,
                "summary": structured.summary,
                "embedding": embedding,  # May be None if embedding failed
                "tags": structured.tags,
                "locked": False,
                "groups": groups,
                "severity": structured.severity,
                "language": "English",  # Could be detected automatically
                "original_text": clause
            }
            
            processed_policies.append(policy_record)
            successful_analyses += 1
            
            logger.info(f"✅ Successfully analyzed clause {i+1}: {structured.title}")
            
        except Exception as e:
            logger.error(f"❌ Error processing clause {i+1}: {str(e)}")
            continue
    
    # Log database chunk persistence summary
    if db_mgr and file_id:
        try:
            saved_chunks = await db_mgr.get_document_chunks(file_id, "policy_clause_analysis")
            logger.info(f"💾 Saved {len(saved_chunks)} policy clauses to local database")
        except Exception as e:
            logger.warning(f"Could not retrieve saved chunks: {e}")
    
    result = {
        "status": "success" if successful_analyses > 0 else "error",
        "message": f"Successfully processed {successful_analyses}/{len(clauses)} policy clauses from {filename}",
        "policy_id": policy_id,
        "filename": filename,
        "total_clauses": len(clauses),
        "clauses_processed": successful_analyses,
        "policy_records": processed_policies,
        "processing_method": "ai_policy_analysis",
        "chunk_id_mapping": chunk_id_mapping  # For Azure Search chunk tracking
    }
    
    logger.info(f"📋 Policy processing completed: {result['message']}")
    return result

async def upload_policies_to_search_index(
    policy_records: List[Dict[str, Any]], 
    chunk_id_mapping: Dict[int, int] = None
) -> Dict[str, Any]:
    """
    Upload processed policy records to Azure Search policy index
    and persist Azure Search chunk records to local database
    """
    try:
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents import SearchClient
        from contracts.index_creation import create_policy_index_if_not_exists
        
        # Ensure policy index exists
        logger.info("🏗️ Ensuring policy index exists...")
        index_result = create_policy_index_if_not_exists()
        logger.info(f"Policy index status: {index_result['message']}")
        
        if index_result['status'] == 'error':
            return {
                "status": "error",
                "message": f"Failed to create/verify policy index: {index_result['message']}",
                "uploaded_count": 0
            }
        
        # Initialize policy search client
        policy_client = SearchClient(
            endpoint=config.AZURE_SEARCH_ENDPOINT,
            index_name=config.AZURE_SEARCH_POLICY_INDEX,
            credential=AzureKeyCredential(config.AZURE_SEARCH_KEY)
        )
        
        # Prepare documents for upload (remove embedding if None)
        upload_docs = []
        for record in policy_records:
            # Create a copy and remove None embeddings since Azure Search doesn't accept them
            doc = record.copy()
            if doc.get('embedding') is None:
                doc.pop('embedding', None)
            upload_docs.append(doc)
        
        if not upload_docs:
            return {
                "status": "warning",
                "message": "No policy records to upload",
                "uploaded_count": 0
            }
        
        # Upload documents in batches
        batch_size = 10
        uploaded_count = 0
        failed_uploads = []
        
        logger.info(f"📤 Uploading {len(upload_docs)} policy documents to Azure Search...")
        
        for i in range(0, len(upload_docs), batch_size):
            batch = upload_docs[i:i + batch_size]
            try:
                result = policy_client.upload_documents(documents=batch)
                batch_uploaded = sum(1 for r in result if r.succeeded)
                batch_failed = sum(1 for r in result if not r.succeeded)
                
                uploaded_count += batch_uploaded
                
                if batch_failed > 0:
                    failed_uploads.extend([r.key for r in result if not r.succeeded])
                    logger.warning(f"⚠️ Batch {i//batch_size + 1}: {batch_failed} failed uploads")
                
                logger.info(f"📤 Batch {i//batch_size + 1}: {batch_uploaded}/{len(batch)} uploaded successfully")
                
            except Exception as e:
                logger.error(f"❌ Failed to upload batch {i//batch_size + 1}: {e}")
                failed_uploads.extend([doc['id'] for doc in batch])
        
        # Step 6: Save Azure Search chunk records to local database
        db_mgr = get_database_manager()
        azure_chunks_saved = 0
        
        if db_mgr and chunk_id_mapping and uploaded_count > 0:
            logger.info("💾 Saving Azure Search policy chunk records...")
            
            # For each uploaded document, save Azure Search chunk record
            for i, policy_doc in enumerate(upload_docs[:uploaded_count]):
                local_chunk_id = chunk_id_mapping.get(i)
                if local_chunk_id:
                    try:
                        azure_chunk_id = await db_mgr.save_azure_search_chunk(
                            document_chunk_id=local_chunk_id,
                            search_document_id=policy_doc['id'],
                            index_name=config.AZURE_SEARCH_POLICY_INDEX,
                            upload_status='success',  # Only saving successful uploads
                            upload_response="Policy upload successful",
                            embedding_dimensions=len(policy_doc['embedding']) if policy_doc.get('embedding') else None,
                            error_message=None,
                            # Persist policy data from Azure Search document
                            paragraph_content=policy_doc.get('instruction'),
                            paragraph_title=policy_doc.get('title'),
                            paragraph_summary=policy_doc.get('summary'),
                            paragraph_keyphrases=json.dumps(policy_doc.get('tags', [])) if policy_doc.get('tags') else None,
                            filename=policy_doc.get('filename'),
                            paragraph_id=policy_doc.get('PolicyId'),
                            date_uploaded=datetime.now(),
                            group_tags=json.dumps(policy_doc.get('groups', [])) if policy_doc.get('groups') else None,
                            department="policy",  # Policy-specific department
                            language=policy_doc.get('language', 'English'),
                            is_compliant=True,  # Policies are generally compliant by definition
                            content_length=len(policy_doc.get('instruction', ''))
                        )
                        azure_chunks_saved += 1
                        logger.debug(f"💾 Saved Azure Search policy chunk {i+1} with ID: {azure_chunk_id}")
                        
                    except Exception as e:
                        logger.warning(f"Failed to save Azure Search policy chunk {i+1}: {e}")
            
            logger.info(f"💾 Saved {azure_chunks_saved} Azure Search policy chunk records to database")
        
        # Prepare result
        result = {
            "status": "success" if uploaded_count > 0 else "error",
            "message": f"Successfully uploaded {uploaded_count}/{len(upload_docs)} policy documents",
            "uploaded_count": uploaded_count,
            "failed_count": len(failed_uploads),
            "index_name": config.AZURE_SEARCH_POLICY_INDEX,
            "azure_chunks_saved": azure_chunks_saved if db_mgr and chunk_id_mapping else 0
        }
        
        if failed_uploads:
            result["failed_uploads"] = failed_uploads[:10]  # Limit to first 10 for brevity
        
        logger.info(f"📋 Policy upload completed: {result['message']}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error uploading policies to search index: {e}")
        return {
            "status": "error",
            "message": f"Failed to upload policies: {str(e)}",
            "uploaded_count": 0
        }

async def process_policy_document_with_ai(
    file_path: str, 
    filename: str, 
    policy_id: str = None,
    groups: List[str] = None,
    upload_to_search: bool = True
) -> Dict[str, Any]:
    """
    Complete policy document processing pipeline:
    1. Extract content from file
    2. Chunk into policy clauses  
    3. Analyze each clause with OpenAI
    4. Upload to Azure Search policy index
    5. Store metadata in database
    """
    
    logger.info(f"🚀 Starting comprehensive policy processing for: {filename}")
    
    try:
        # Step 1: Extract document content
        file_extension = filename.lower().split('.')[-1] if '.' in filename else 'txt'
        policy_text = process_document_content(file_path, file_extension)
        
        if not policy_text:
            return {
                "status": "error",
                "message": f"Could not extract content from {filename}",
                "filename": filename
            }
        
        logger.info(f"📄 Extracted {len(policy_text)} characters from {filename}")
        
        # Step 2: Get or create file_id for database tracking
        file_id = None
        db_mgr = get_database_manager()
        if db_mgr:
            try:
                # Import FileMetadata model
                from contracts.models import FileMetadata
                from datetime import datetime
                
                # Create FileMetadata object
                file_metadata = FileMetadata(
                    filename=filename,
                    original_filename=filename,
                    file_size=len(policy_text),
                    content_type="policy",
                    checksum=str(hash(policy_text)),  # Simple hash for tracking
                    upload_timestamp=datetime.now()
                )
                
                # Save file metadata
                file_id = await db_mgr.save_file_metadata(file_metadata)
                logger.info(f"💾 File record created/found with ID: {file_id}")
            except Exception as e:
                logger.warning(f"Could not save file metadata: {e}")
                logger.debug(f"File metadata error details: {str(e)}")
                import traceback
                logger.debug(traceback.format_exc())
        
        # Step 3: Process policy document
        processing_result = await process_policy_document(
            policy_text=policy_text,
            filename=filename,
            policy_id=policy_id,
            groups=groups,
            file_id=file_id
        )
        
        if processing_result['status'] == 'error':
            return processing_result
        
        policy_records = processing_result['policy_records']
        chunk_id_mapping = processing_result.get('chunk_id_mapping', {})
        
        # Step 4: Upload to Azure Search (if requested)
        search_result = {"uploaded_count": 0, "message": "Skipped search upload"}
        if upload_to_search and policy_records:
            search_result = await upload_policies_to_search_index(policy_records, chunk_id_mapping)
        
        # Step 5: Database integration summary
        db_result = {
            "chunk_persistence": "completed" if file_id and chunk_id_mapping else "not_available",
            "azure_search_persistence": "completed" if search_result.get('azure_chunks_saved', 0) > 0 else "not_available",
            "file_id": file_id,
            "message": f"Database persistence: chunks={len(chunk_id_mapping)}, azure_search={search_result.get('azure_chunks_saved', 0)}"
        }
        
        # Compile final result
        result = {
            "status": "success",
            "message": f"Successfully processed policy document: {filename}",
            "filename": filename,
            "policy_id": processing_result['policy_id'],
            "total_clauses": processing_result['total_clauses'],
            "clauses_processed": processing_result['clauses_processed'],
            "processing_method": processing_result['processing_method'],
            "search_upload": {
                "status": search_result.get('status', 'unknown'),
                "uploaded_count": search_result.get('uploaded_count', 0),
                "index_name": search_result.get('index_name', config.AZURE_SEARCH_POLICY_INDEX)
            },
            "database_storage": db_result,
            "timestamp": datetime.now().isoformat()
        }
        
        if search_result.get('failed_count', 0) > 0:
            result["search_upload"]["failed_count"] = search_result['failed_count']
        
        logger.info(f"✅ Policy processing completed successfully: {filename}")
        logger.info(f"   📋 Processed: {result['clauses_processed']}/{result['total_clauses']} clauses")
        logger.info(f"   📤 Uploaded: {result['search_upload']['uploaded_count']} to search index")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error in comprehensive policy processing: {e}")
        return {
            "status": "error",
            "message": f"Policy processing failed: {str(e)}",
            "filename": filename,
            "timestamp": datetime.now().isoformat()
        }

# Example usage function for testing
def test_policy_processing():
    """
    Test function to demonstrate policy processing capabilities
    """
    sample_policy_text = '''
Payment Terms and Conditions

1. Payment Schedule
All payments must be made within 30 days of invoice date unless otherwise specified in the contract.

2. Late Payment Penalties  
Failure to pay within the specified timeframe will result in a 1.5% monthly penalty fee applied to the outstanding balance.

3. Payment Methods
Acceptable payment methods include wire transfer, certified check, or ACH transfer. Credit card payments require prior approval.

4. Currency Requirements
All payments must be made in USD unless explicitly agreed otherwise in writing by both parties.
'''

    logger.info("🧪 Testing policy processing with sample data...")
    policy_results = process_policy_document(
        policy_text=sample_policy_text,
        filename="sample_payment_policies.docx",
        groups=["finance-team", "legal-team"]
    )

    logger.info(f"📊 Test Results:")
    logger.info(f"   Status: {policy_results['status']}")
    logger.info(f"   Clauses: {policy_results['clauses_processed']}/{policy_results['total_clauses']}")
    
    for i, policy in enumerate(policy_results['policy_records'][:3]):  # Show first 3
        logger.info(f"   Policy {i+1}:")
        logger.info(f"     Title: {policy['title']}")
        logger.info(f"     Summary: {policy['summary']}")
        logger.info(f"     Tags: {policy['tags']}")
        logger.info(f"     Severity: {policy['severity']}")

    return policy_results

logger.info("📋 Policy processing functions defined successfully!")