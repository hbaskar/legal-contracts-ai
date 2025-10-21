"""
AI Services and Document Processing Module
Handles OpenAI integration, Azure Search, and document processing functionality
"""

import os
import json
import logging
import tempfile
from typing import List, Dict, Any, Optional
from datetime import datetime
import base64
import uuid
import re
from io import BytesIO

# AI and Search imports
try:
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient
    from openai import AzureOpenAI
except ImportError as e:
    logging.error(f"Missing required Azure/OpenAI packages: {e}")

# Document processing imports
try:
    from docx import Document
    import PyPDF2
except ImportError as e:
    logging.error(f"Missing required document processing packages: {e}")

from config.config import config

# Database imports - using lazy import to avoid circular dependencies
DatabaseManagerClass = None
_database_manager_instance = None

def get_database_manager_class():
    """Get the DatabaseManager class for creating new instances"""
    global DatabaseManagerClass
    
    if DatabaseManagerClass is None:
        try:
            from config.database import DatabaseManager as DbMgrClass
            DatabaseManagerClass = DbMgrClass
        except ImportError as e:
            logging.error(f"Missing database manager: {e}")
            return None
    
    return DatabaseManagerClass

def get_database_manager():
    """Lazy import and instantiation of DatabaseManager to avoid circular dependencies"""
    global _database_manager_instance
    
    db_class = get_database_manager_class()
    if db_class is None:
        return None
    
    # Return cached instance or create new one
    if _database_manager_instance is None:
        try:
            _database_manager_instance = db_class()
            logging.info("Database manager instance created successfully")
        except Exception as e:
            logging.error(f"Failed to create database manager instance: {e}")
            return None
    
    return _database_manager_instance

# Configure logging
logger = logging.getLogger(__name__)

# Global clients (initialized lazily)
openai_client = None
search_client = None

def get_openai_client():
    """Initialize OpenAI client lazily"""
    global openai_client
    if openai_client is None:
        if not config.AZURE_OPENAI_ENDPOINT:
            raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is required")
        if not config.AZURE_OPENAI_KEY:
            raise ValueError("AZURE_OPENAI_KEY environment variable is required")
        
        logger.info(f"🤖 Initializing OpenAI client with endpoint: {config.AZURE_OPENAI_ENDPOINT}")
        try:
            openai_client = AzureOpenAI(
                azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
                api_key=config.AZURE_OPENAI_KEY,
                api_version=config.AZURE_OPENAI_API_VERSION,
            )
            logger.info("✅ OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize OpenAI client: {e}")
            raise
    return openai_client

def get_search_client():
    """Initialize Search client lazily and ensure index exists"""
    global search_client
    if search_client is None:
        if not config.AZURE_SEARCH_ENDPOINT:
            raise ValueError("AZURE_SEARCH_ENDPOINT environment variable is required")
        if not config.AZURE_SEARCH_KEY:
            raise ValueError("AZURE_SEARCH_KEY environment variable is required")
        
        logger.info(f"🔍 Initializing Search client with endpoint: {config.AZURE_SEARCH_ENDPOINT}")
        search_client = SearchClient(
            endpoint=config.AZURE_SEARCH_ENDPOINT,
            index_name=config.AZURE_SEARCH_DOC_INDEX,
            credential=AzureKeyCredential(config.AZURE_SEARCH_KEY)
        )
        logger.info("✅ Search client initialized successfully")
        
        # Ensure the index exists when initializing the client
        try:
            from contracts.index_creation import create_document_index_if_not_exists
            index_result = create_document_index_if_not_exists()
            logger.info(f"🏗️ Index status: {index_result['message']}")
        except Exception as e:
            logger.warning(f"⚠️ Could not verify index existence: {str(e)}")
    
    return search_client

def sanitize_document_key(filename: str) -> str:
    """Sanitize filename for use as document key"""
    base_name = os.path.splitext(filename)[0]
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', base_name)
    return sanitized.lower()

def simple_chunk_text(text: str, max_chunk_size: int) -> List[str]:
    """
    Simple fixed-size text chunking without AI processing
    Used as a baseline for comparison
    """
    if not text:
        return []
    
    chunks = []
    for i in range(0, len(text), max_chunk_size):
        chunk = text[i:i + max_chunk_size]
        # Try to break at word boundaries if possible
        if i + max_chunk_size < len(text) and not text[i + max_chunk_size].isspace():
            # Find the last space within the chunk
            last_space = chunk.rfind(' ')
            if last_space > max_chunk_size * 0.7:  # Don't break too early
                chunk = chunk[:last_space]
        chunks.append(chunk.strip())
    
    return [c for c in chunks if c]  # Remove empty chunks

def safe_openai_call(operation_name: str, api_call_func, *args, **kwargs):
    """Safely execute OpenAI API calls with proper error handling"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"🔄 Attempting {operation_name} (attempt {attempt + 1}/{max_retries})")
            response = api_call_func(*args, **kwargs)
            
            if hasattr(response, 'choices') and response.choices:
                # Check if response has valid content
                if hasattr(response.choices[0], 'message') and response.choices[0].message.content:
                    content = response.choices[0].message.content
                    if content and content.strip():
                        logger.info(f"✅ {operation_name} completed successfully")
                        return response
                    else:
                        logger.warning(f"⚠️ {operation_name} returned empty content (attempt {attempt + 1}/{max_retries})")
                else:
                    logger.warning(f"⚠️ {operation_name} returned response without message content (attempt {attempt + 1}/{max_retries})")
            elif hasattr(response, 'data') and response.data:
                logger.info(f"✅ {operation_name} completed successfully")
                return response
            else:
                logger.warning(f"⚠️ {operation_name} returned unexpected response format (attempt {attempt + 1}/{max_retries})")
                logger.debug(f"   Response type: {type(response)}, has choices: {hasattr(response, 'choices')}, has data: {hasattr(response, 'data')}")
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ {operation_name} JSON parsing failed (attempt {attempt + 1}/{max_retries}): {e}")
            logger.error(f"   This is the 'Failed to parse OpenAI response as JSON' error you're seeing")
            logger.error(f"   Raw response content preview: {str(response)[:500] if 'response' in locals() else 'No response captured'}")
            
            # For JSON decode errors, try a different approach
            if attempt < max_retries - 1:
                logger.info(f"   Retrying with different parameters...")
                # Modify the call to potentially avoid the JSON issue
                if hasattr(api_call_func, '__name__'):
                    logger.info(f"   Function: {api_call_func.__name__}")
            
        except ConnectionError as e:
            logger.error(f"❌ {operation_name} connection failed (attempt {attempt + 1}/{max_retries}): {e}")
            logger.error(f"   Check your internet connection and Azure OpenAI endpoint")
            
        except TimeoutError as e:
            logger.error(f"❌ {operation_name} timed out (attempt {attempt + 1}/{max_retries}): {e}")
            logger.error(f"   Consider increasing timeout or checking Azure OpenAI service status")
            
        except Exception as e:
            logger.error(f"❌ {operation_name} failed (attempt {attempt + 1}/{max_retries}): {e}")
            logger.error(f"   Error type: {type(e).__name__}")
            
        if attempt == max_retries - 1:
            logger.error(f"❌ {operation_name} failed after {max_retries} attempts, giving up")
            raise
            
        # Wait before retry (exponential backoff)
        import time
        wait_time = 2 ** attempt
        logger.info(f"⏳ Waiting {wait_time} seconds before retry...")
        time.sleep(wait_time)
    
    raise Exception(f"Failed to complete {operation_name} after {max_retries} attempts")

def generate_text_embedding(text: str) -> List[float]:
    """Generate text embedding using Azure OpenAI"""
    try:
        client = get_openai_client()
        
        def embedding_call():
            return client.embeddings.create(
                input=text,
                model=config.AZURE_OPENAI_EMBEDDING_DEPLOYMENT
            )
        
        response = safe_openai_call("Text Embedding", embedding_call)
        return response.data[0].embedding
        
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        return [0.0] * 1536  # Return dummy embedding

def intelligent_chunk_with_openai(document_text: str, document_type: str = "legal", max_chunk_size: int = 1000) -> List[str]:
    """Use OpenAI to intelligently determine optimal chunk boundaries based on semantic meaning"""
    
    # First, let OpenAI analyze the document structure and suggest chunking strategy
    analysis_prompt = f'''
You are an expert document analyst. Analyze this {document_type} document and determine the optimal way to break it into semantic chunks while preserving ALL original content.

CRITICAL REQUIREMENTS:
- Find natural topic boundaries without modifying any text
- Preserve ALL original content, formatting, and structure
- Focus on logical flow and semantic coherence
- Identify where content naturally divides into topics
- Consider maximum chunk size of approximately {max_chunk_size} characters

Consider these structural elements:
- Natural topic boundaries and transitions
- Legal sections, clauses, or provisions  
- Paragraph breaks and logical divisions
- Related concepts that should stay together
- Introductory vs detailed content

Document to analyze (length: {len(document_text)} characters):
{document_text[:3000]}{'...' if len(document_text) > 3000 else ''}

Return a JSON object with boundary suggestions (character positions) that will preserve content integrity:
{{
    "strategy": "Brief description of boundary-finding approach",
    "boundaries": [0, 500, 1200, 2000],
    "chunk_themes": ["Topic/theme for each chunk section"]
}}

IMPORTANT: Boundaries should split at natural content divisions, not modify the actual text content.
'''

    try:
        client = get_openai_client()
        
        # Get AI analysis of optimal chunking strategy
        def analysis_call():
            return client.chat.completions.create(
                model=config.AZURE_OPENAI_MODEL_DEPLOYMENT,
                messages=[{"role": "user", "content": analysis_prompt}],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=800,
                timeout=45  # Longer timeout for analysis
            )
        
        analysis_response = safe_openai_call("Document Analysis", analysis_call)
        
        # Safe JSON parsing with error handling
        response_content = analysis_response.choices[0].message.content
        if not response_content or not response_content.strip():
            logger.warning("⚠️ OpenAI returned empty response, using fallback chunking")
            analysis = {"boundaries": [], "strategy": "fallback"}
        else:
            try:
                analysis = json.loads(response_content)
            except json.JSONDecodeError as e:
                logger.error(f"❌ Failed to parse OpenAI response as JSON: {e}")
                logger.error(f"   Raw response: {response_content[:200]}...")
                # Use fallback analysis
                analysis = {"boundaries": [], "strategy": "fallback due to JSON parse error"}
        logger.info(f"🧠 AI Chunking Strategy: {analysis.get('strategy', 'Standard approach')}")
        
        # Use AI-suggested boundaries to create initial chunks
        boundaries = analysis.get('boundaries', [])
        themes = analysis.get('chunk_themes', [])
        
        if not boundaries or len(boundaries) < 2:
            # Fallback to size-based chunking if AI analysis failed
            boundaries = list(range(0, len(document_text), max_chunk_size))
            boundaries.append(len(document_text))
        
        # Create chunks based on AI-suggested boundaries
        chunks = []
        for i in range(len(boundaries) - 1):
            start = boundaries[i]
            end = min(boundaries[i + 1], len(document_text))
            
            if end > start:
                raw_chunk = document_text[start:end].strip()
                
                # Preserve original content - only adjust boundaries to natural breaks
                # Find the best sentence boundaries within a small window
                adjustment_prompt = f'''
You are a document processing expert. Given this text chunk, find the best natural boundary points to start and end the chunk WITHOUT changing any content.

CRITICAL RULES:
1. DO NOT modify, clean up, or rewrite any text
2. DO NOT remove any content 
3. DO NOT add any content
4. ONLY suggest where to start and end the chunk at natural sentence boundaries
5. Preserve ALL original formatting, spacing, and punctuation exactly

Text chunk (length {len(raw_chunk)}):
{raw_chunk}

Analyze the first and last 100 characters to suggest optimal start/end positions:
- First 100 chars: "{raw_chunk[:100]}"
- Last 100 chars: "{raw_chunk[-100:]}"

Return a JSON object with:
{{
    "suggested_start_offset": 0,
    "suggested_end_offset": {len(raw_chunk)},
    "reasoning": "Brief explanation of boundary choices"
}}

If the current boundaries are already optimal, return the same start (0) and end ({len(raw_chunk)}) positions.
'''

                try:
                    def boundary_call():
                        return client.chat.completions.create(
                            model=config.AZURE_OPENAI_MODEL_DEPLOYMENT,
                            messages=[{"role": "user", "content": adjustment_prompt}],
                            response_format={"type": "json_object"},
                            temperature=0.1,
                            max_tokens=300,
                            timeout=20  # Shorter timeout for boundary analysis
                        )
                    
                    boundary_response = safe_openai_call("Boundary Analysis", boundary_call)
                    
                    # Safe JSON parsing for boundary analysis
                    boundary_content = boundary_response.choices[0].message.content
                    if not boundary_content or not boundary_content.strip():
                        logger.warning(f"⚠️ OpenAI returned empty boundary response for chunk {i}")
                        boundary_analysis = {"suggested_start_offset": 0, "suggested_end_offset": len(raw_chunk)}
                    else:
                        try:
                            boundary_analysis = json.loads(boundary_content)
                        except json.JSONDecodeError as e:
                            logger.error(f"❌ Failed to parse boundary response as JSON: {e}")
                            logger.error(f"   Raw response: {boundary_content[:200]}...")
                            boundary_analysis = {"suggested_start_offset": 0, "suggested_end_offset": len(raw_chunk)}
                    start_offset = max(0, boundary_analysis.get('suggested_start_offset', 0))
                    end_offset = min(len(raw_chunk), boundary_analysis.get('suggested_end_offset', len(raw_chunk)))
                    
                    # Apply boundary adjustments while preserving original content
                    if end_offset > start_offset:
                        adjusted_chunk = raw_chunk[start_offset:end_offset].strip()
                    else:
                        adjusted_chunk = raw_chunk.strip()
                    
                    # Use the boundary-adjusted chunk (no content modification)
                    if len(adjusted_chunk) > 50:
                        chunks.append(adjusted_chunk)
                    else:
                        # Use original chunk if adjustment resulted in too small chunk
                        chunks.append(raw_chunk)
                        
                except Exception as e:
                    logger.warning(f"Boundary adjustment failed: {e}, using original chunk")
                    chunks.append(raw_chunk)
        
        # Final validation and cleanup
        final_chunks = []
        for chunk in chunks:
            if len(chunk.strip()) > 50:  # Minimum meaningful chunk size
                final_chunks.append(chunk.strip())
        
        logger.info(f"✅ AI Intelligent Chunking: {len(final_chunks)} semantic chunks created")
        return final_chunks
        
    except Exception as e:
        logger.error(f"Error in intelligent chunking: {str(e)}")
        # Fallback to sentence-based chunking
        return fallback_sentence_chunking(document_text, max_chunk_size)

def fallback_sentence_chunking(document_text: str, max_chunk_size: int = 1000) -> List[str]:
    """Fallback method: Split by sentences when AI chunking fails"""
    import re
    
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', document_text)
    
    chunks = []
    current_chunk = []
    current_size = 0
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        if current_size + len(sentence) > max_chunk_size and current_chunk:
            chunks.append(' '.join(current_chunk))
            current_chunk = [sentence]
            current_size = len(sentence)
        else:
            current_chunk.append(sentence)
            current_size += len(sentence) + 1  # +1 for space
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    # Validate content preservation (returns metrics but we don't need them here)
    validate_content_preservation(document_text, chunks, "sentence-based chunking")
    
    return chunks

def validate_content_preservation(original_text: str, chunks: List[str], method_name: str) -> Dict[str, Any]:
    """Validate that chunking preserves all content without loss or duplication"""
    
    # Calculate original content metrics
    original_length = len(original_text)
    original_words = len(original_text.split())
    
    # Calculate chunked content metrics  
    combined_chunks = ' '.join(chunks)
    combined_length = len(combined_chunks)
    combined_words = len(combined_chunks.split())
    
    # Calculate content preservation ratio
    length_ratio = combined_length / original_length if original_length > 0 else 0
    word_ratio = combined_words / original_words if original_words > 0 else 0
    
    # Additional validation: Check for significant content overlap or gaps
    total_chunk_chars = sum(len(chunk) for chunk in chunks)
    
    # Log validation results
    logger.info(f"📊 Content Validation for {method_name}:")
    logger.info(f"   Original: {original_length:,} chars, {original_words:,} words")
    logger.info(f"   Chunked:  {combined_length:,} chars, {combined_words:,} words")
    logger.info(f"   Individual chunks total: {total_chunk_chars:,} chars")
    logger.info(f"   Preservation: {length_ratio:.1%} chars, {word_ratio:.1%} words")
    
    # Check for content integrity issues
    issues = []
    
    # Adjust thresholds based on chunking method
    if method_name.lower().find("intelligent") != -1:
        # More lenient for intelligent chunking since AI cleanup is expected
        min_threshold = 0.85  # Allow up to 15% content loss for AI cleanup
        max_threshold = 1.15
    else:
        # Stricter for mechanical chunking methods
        min_threshold = 0.95  # Only 5% variance for simple chunking
        max_threshold = 1.10
    
    # Check for significant content loss
    if length_ratio < min_threshold:
        issues.append(f"Content loss: {original_length - combined_length} chars missing")
    
    # Check for unexpected content expansion (potential duplication)
    if length_ratio > max_threshold:
        issues.append(f"Content expansion: {combined_length - original_length} extra chars")
    
    # Check for empty chunks
    empty_chunks = [i for i, chunk in enumerate(chunks) if not chunk.strip()]
    if empty_chunks:
        issues.append(f"Empty chunks found at positions: {empty_chunks}")
    
    # Determine validation result
    validation_passed = len(issues) == 0
    acceptable = length_ratio >= (min_threshold - 0.05) and length_ratio <= (max_threshold + 0.05)
    
    # Log results
    if validation_passed:
        logger.info(f"✅ Content preservation validated for {method_name}")
    else:
        logger.warning(f"⚠️ Content integrity issues detected in {method_name}:")
        for issue in issues:
            logger.warning(f"   - {issue}")
        
        if acceptable:
            logger.info(f"📋 Issues within acceptable range for {method_name}")
    
    # Return detailed validation metrics
    return {
        "method": method_name,
        "original_chars": original_length,
        "original_words": original_words,
        "chunked_chars": combined_length,
        "chunked_words": combined_words,
        "total_chunk_chars": total_chunk_chars,
        "char_preservation_ratio": round(length_ratio, 3),
        "word_preservation_ratio": round(word_ratio, 3),
        "validation_passed": validation_passed,
        "acceptable": acceptable,
        "issues": issues,
        "chunks_count": len(chunks)
    }

def heading_based_chunking(document_text: str) -> List[str]:
    """Chunk document based on headings and sections"""
    import re
    
    # Split document into lines for analysis
    lines = document_text.split('\n')
    chunks = []
    current_chunk_lines = []
    
    # Patterns to detect headings and sections
    heading_patterns = [
        # Numbered sections: "1.", "1.1", "2.3.4", etc.
        re.compile(r'^\s*(\d+\.)+\s*[A-Z]'),
        # ALL CAPS headings (minimum 3 words, not too long)
        re.compile(r'^\s*[A-Z][A-Z\s]{10,80}[A-Z]\s*$'),
        # Roman numerals: "I.", "II.", "III.", etc.
        re.compile(r'^\s*[IVX]+\.\s*[A-Z]'),
        # Letters: "A.", "B.", "(a)", "(b)", etc.
        re.compile(r'^\s*\(?[A-Za-z]\)?\.\s*[A-Z]'),
        # Section keywords
        re.compile(r'^\s*(SECTION|ARTICLE|CHAPTER|PART|EXHIBIT)\s+\d+', re.IGNORECASE),
        # Legal document patterns
        re.compile(r'^\s*(WHEREAS|NOW THEREFORE|IN WITNESS WHEREOF)', re.IGNORECASE),
    ]
    
    def is_heading(line: str) -> bool:
        """Check if a line is likely a heading"""
        line = line.strip()
        
        # Skip empty lines
        if not line:
            return False
            
        # Skip very long lines (likely paragraph text)
        if len(line) > 100:
            return False
            
        # Check against heading patterns
        for pattern in heading_patterns:
            if pattern.match(line):
                return True
                
        # Additional heuristics for headings
        # Short lines that are mostly uppercase
        if len(line) < 50 and len([c for c in line if c.isupper()]) > len(line) * 0.7:
            return True
            
        return False
    
    def should_start_new_chunk(line: str, current_chunk_lines: List[str]) -> bool:
        """Determine if we should start a new chunk"""
        # Always start new chunk on headings
        if is_heading(line):
            return True
            
        # Don't split if current chunk is too small (less than 200 chars)
        current_size = sum(len(l) for l in current_chunk_lines)
        if current_size < 200:
            return False
            
        # Don't split if current chunk would be too large (more than 2000 chars)
        if current_size > 2000:
            return True
            
        return False
    
    logger.info(f"📋 Processing {len(lines)} lines for heading-based chunking")
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Skip completely empty lines at chunk boundaries
        if not line and not current_chunk_lines:
            continue
            
        # Check if we should start a new chunk
        if current_chunk_lines and should_start_new_chunk(line, current_chunk_lines):
            # Finalize current chunk
            chunk_text = '\n'.join(current_chunk_lines).strip()
            if chunk_text:
                chunks.append(chunk_text)
            current_chunk_lines = []
        
        # Add line to current chunk
        if line:  # Only add non-empty lines
            current_chunk_lines.append(line)
    
    # Add final chunk
    if current_chunk_lines:
        chunk_text = '\n'.join(current_chunk_lines).strip()
        if chunk_text:
            chunks.append(chunk_text)
    
    logger.info(f"✅ Created {len(chunks)} heading-based chunks")
    
    # Validate content preservation (returns metrics but we don't need them here)
    validate_content_preservation(document_text, chunks, "heading-based chunking")
    
    # Log chunk details for debugging
    for i, chunk in enumerate(chunks[:5]):  # Show first 5 chunks
        logger.info(f"   Chunk {i+1}: {len(chunk)} chars - {chunk[:60]}...")
    
    return chunks

def extract_simple_keyphrases(text: str) -> List[str]:
    """Fallback method: Simple keyword extraction"""
    legal_terms = [
        "contract", "agreement", "terms", "conditions", "obligations", "rights",
        "payment", "delivery", "warranty", "liability", "indemnification",
        "confidentiality", "intellectual property", "termination", "breach",
        "damages", "jurisdiction", "governing law", "dispute resolution"
    ]
    
    found_terms = []
    text_lower = text.lower()
    
    for term in legal_terms:
        if term in text_lower:
            found_terms.append(term)
    
    # Add capitalized words
    words = re.findall(r'\b[A-Z][a-z]+\b', text)
    found_terms.extend(words[:3])
    
    return found_terms[:6] if found_terms else ["document", "content"]

def extract_keyphrases_with_openai(text: str, document_type: str = "legal") -> List[str]:
    """Use OpenAI to intelligently extract key phrases from text"""
    
    prompt = f'''
You are an expert at extracting key phrases from {document_type} documents. 

Analyze the provided text and extract 5-8 key phrases that are most important for search and categorization. Focus on:

For Legal Documents:
- Legal terms and concepts
- Important names, entities, companies
- Dates, deadlines, time periods
- Contract clauses and obligations
- Monetary amounts or percentages
- Jurisdictions or legal references

For General Documents:
- Main topics and themes
- Important entities or names
- Key concepts and terminology
- Action items or requirements
- Technical terms specific to the domain

Return ONLY a simple JSON array of key phrases as strings. No explanations.

Example output format:
["phrase1", "phrase2", "phrase3", "phrase4", "phrase5"]

Text to analyze:
{text[:2000]}
'''

    try:
        client = get_openai_client()
        def keyphrase_call():
            return client.chat.completions.create(
                model=config.AZURE_OPENAI_MODEL_DEPLOYMENT,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=200,
                timeout=30  # Add timeout
            )
        
        response = safe_openai_call("Keyphrase Extraction", keyphrase_call)
        
        # Get the response content and clean it
        response_content = response.choices[0].message.content.strip()
        
        # Try to fix common JSON issues
        if response_content:
            # Remove any leading/trailing whitespace or non-JSON content
            if response_content.startswith('```json'):
                response_content = response_content.replace('```json', '').replace('```', '').strip()
            elif response_content.startswith('```'):
                response_content = response_content.replace('```', '').strip()
            
            # Try to find JSON content if it's wrapped in other text
            import re
            json_match = re.search(r'[\[\{].*[\]\}]', response_content, re.DOTALL)
            if json_match:
                response_content = json_match.group(0)
        
        try:
            result = json.loads(response_content)
        except json.JSONDecodeError as json_error:
            logger.warning(f"Failed to parse OpenAI response as JSON: {json_error}")
            logger.debug(f"Raw response content: {response_content[:200]}...")
            
            # Try to extract keyphrases from non-JSON response
            if isinstance(response_content, str):
                # Look for quoted strings or simple lists
                import re
                phrases = re.findall(r'"([^"]+)"', response_content)
                if not phrases:
                    phrases = re.findall(r'(\w+(?:\s+\w+)*)', response_content)
                if phrases:
                    return phrases[:8]
            
            # Fall back to simple extraction
            return extract_simple_keyphrases(text)
        
        if isinstance(result, list):
            keyphrases = result
        elif isinstance(result, dict):
            keyphrases = result.get('keyphrases', result.get('phrases', result.get('key_phrases', [])))
            if not keyphrases and len(result) == 1:
                keyphrases = list(result.values())[0]
        else:
            keyphrases = []
        
        if not isinstance(keyphrases, list):
            keyphrases = []
            
        cleaned_phrases = []
        for phrase in keyphrases[:8]:
            if isinstance(phrase, str) and phrase.strip():
                cleaned_phrases.append(phrase.strip())
        
        return cleaned_phrases if cleaned_phrases else ["document", "content"]
        
    except Exception as e:
        logger.error(f"Error extracting keyphrases with OpenAI: {str(e)}")
        return extract_simple_keyphrases(text)

def extract_true_paragraphs_method2(file_path: str) -> str:
    """Method 2: Use paragraph styles and formatting to identify true paragraphs"""
    try:
        doc = Document(file_path)
        
        paragraphs = []
        current_paragraph = []
        
        for para in doc.paragraphs:
            text = para.text.strip()
            
            if not text:
                continue
                
            is_new_paragraph = (
                para.style.name.startswith(('Heading', 'Title')) or
                len(current_paragraph) == 0
            )
            
            if is_new_paragraph and current_paragraph:
                paragraphs.append(' '.join(current_paragraph))
                current_paragraph = [text]
            else:
                current_paragraph.append(text)
        
        if current_paragraph:
            paragraphs.append(' '.join(current_paragraph))
        
        return '\n\n'.join(paragraphs)
        
    except Exception as e:
        logger.error(f"Error in paragraph extraction: {str(e)}")
        return None

def process_document_content(file_path: str, file_extension: str) -> str:
    """Extract document content with properly reconstructed paragraphs"""
    if file_extension == 'txt':
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    
    elif file_extension == 'docx':
        return extract_true_paragraphs_method2(file_path)
    
    elif file_extension == 'pdf':
        try:
            # First, check if the file is actually a valid PDF
            with open(file_path, 'rb') as file:
                # Read first few bytes to check PDF header
                header = file.read(5)
                if not header.startswith(b'%PDF-'):
                    logger.warning(f"File {file_path} has .pdf extension but is not a valid PDF file")
                    # Try to read as text instead
                    try:
                        with open(file_path, 'r', encoding='utf-8') as text_file:
                            content = text_file.read()
                            logger.info("Successfully read PDF file as text content")
                            return content
                    except Exception as text_error:
                        logger.error(f"Failed to read as text: {text_error}")
                        return None
                
                # Reset file pointer and process as PDF
                file.seek(0)
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Check if PDF has pages
                if len(pdf_reader.pages) == 0:
                    logger.error("PDF file has no pages")
                    return None
                
                text = ""
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text.strip():  # Only add non-empty pages
                            text += page_text + "\n"
                        else:
                            logger.warning(f"Page {page_num + 1} contains no extractable text")
                    except Exception as page_error:
                        logger.error(f"Error extracting text from page {page_num + 1}: {page_error}")
                        continue
            
            if not text.strip():
                logger.error("No text could be extracted from PDF")
                return None
            
            # Basic paragraph reconstruction for PDFs
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            paragraphs = []
            current_paragraph = []
            
            for line in lines:
                current_paragraph.append(line)
                if line.endswith(('.', '!', '?')) or len(' '.join(current_paragraph)) > 200:
                    paragraphs.append(' '.join(current_paragraph))
                    current_paragraph = []
            
            if current_paragraph:
                paragraphs.append(' '.join(current_paragraph))
            
            result_text = '\n\n'.join(paragraphs)
            logger.info(f"Successfully extracted {len(result_text)} characters from PDF")
            return result_text
            
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            logger.error(f"PDF processing failed for file: {file_path}")
            return None
    
    else:
        logger.error(f"Unsupported file type: {file_extension}")
        return None

def delete_document_from_index(filename: str) -> Dict:
    """Delete all chunks of a document from the index by filename"""
    try:
        client = get_search_client()
        results = client.search(
            search_text="*",
            filter=f"filename eq '{filename}'",
            select="id"
        )
        
        document_ids = [doc["id"] for doc in results]
        
        if not document_ids:
            return {
                "status": "not_found",
                "message": f"No documents found with filename: {filename}"
            }
        
        delete_docs = [{"id": doc_id} for doc_id in document_ids]
        result = client.delete_documents(delete_docs)
        
        successful_deletes = sum(1 for r in result if r.succeeded)
        
        return {
            "status": "success",
            "message": f"Deleted {successful_deletes} chunks for document {filename}",
            "deleted_chunks": successful_deletes
        }
        
    except Exception as e:
        logger.error(f"Error deleting document {filename}: {str(e)}")
        return {"status": "error", "message": str(e)}


def delete_document_by_content_hash(filename: str, content_hash: str, document_text: str) -> Dict:
    """Delete documents with the same content hash (same exact content) - smarter deletion"""
    try:
        client = get_search_client()
        
        # Search for documents with the same filename
        results = client.search(
            search_text="*",
            filter=f"filename eq '{filename}'",
            select="id,paragraph"
        )
        
        # Find documents with matching content by comparing text similarity
        documents_to_delete = []
        import hashlib
        
        for doc in results:
            if 'paragraph' in doc:
                # Calculate hash of existing document content
                existing_content_hash = hashlib.sha256(doc['paragraph'].encode('utf-8')).hexdigest()[:16]
                new_content_hash = hashlib.sha256(document_text.encode('utf-8')).hexdigest()[:16]
                
                # Delete if content hashes match (same exact content)
                if existing_content_hash == new_content_hash:
                    documents_to_delete.append(doc['id'])
                    logger.debug(f"Found matching content for deletion: {doc['id']}")
        
        if not documents_to_delete:
            return {
                "status": "not_found",
                "message": f"No documents found with same content hash for {filename}"
            }
        
        delete_docs = [{"id": doc_id} for doc_id in documents_to_delete]
        result = client.delete_documents(delete_docs)
        
        successful_deletes = sum(1 for r in result if r.succeeded)
        
        logger.info(f"🗑️ Deleted {successful_deletes} documents with matching content, preserved other versions")
        
        return {
            "status": "success",
            "message": f"Deleted {successful_deletes} chunks with same content for document {filename}",
            "deleted_chunks": successful_deletes
        }
        
    except Exception as e:
        logger.error(f"Error deleting document by content hash {filename}: {str(e)}")
        return {"status": "error", "message": str(e)}


def delete_document_by_id(document_id: str) -> Dict:
    """Delete a specific document chunk from the index by document ID"""
    try:
        client = get_search_client()
        
        # First check if the document exists
        try:
            doc = client.get_document(key=document_id)
            if not doc:
                return {
                    "status": "not_found",
                    "message": f"Document with ID '{document_id}' not found"
                }
        except Exception:
            return {
                "status": "not_found", 
                "message": f"Document with ID '{document_id}' not found"
            }
        
        # Delete the specific document
        delete_docs = [{"id": document_id}]
        result = client.delete_documents(delete_docs)
        
        successful_deletes = sum(1 for r in result if r.succeeded)
        
        if successful_deletes > 0:
            return {
                "status": "success",
                "message": f"Successfully deleted document with ID: {document_id}",
                "deleted_chunks": successful_deletes
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to delete document with ID: {document_id}"
            }
        
    except Exception as e:
        logger.error(f"Error deleting document by ID {document_id}: {str(e)}")
        return {"status": "error", "message": str(e)}


def delete_multiple_documents_by_ids(document_ids: List[str]) -> Dict:
    """Delete multiple specific document chunks from the index by document IDs"""
    try:
        client = get_search_client()
        
        if not document_ids:
            return {
                "status": "error",
                "message": "No document IDs provided"
            }
        
        # Validate that all documents exist first (optional, can be removed for performance)
        existing_docs = []
        for doc_id in document_ids:
            try:
                doc = client.get_document(key=doc_id)
                if doc:
                    existing_docs.append(doc_id)
            except Exception:
                logger.warning(f"Document {doc_id} not found, will skip")
        
        if not existing_docs:
            return {
                "status": "not_found",
                "message": f"None of the provided document IDs were found"
            }
        
        # Delete the documents in batches
        batch_size = 100  # Azure Search batch limit
        total_deleted = 0
        failed_deletions = 0
        
        for i in range(0, len(existing_docs), batch_size):
            batch_ids = existing_docs[i:i + batch_size]
            delete_docs = [{"id": doc_id} for doc_id in batch_ids]
            
            try:
                result = client.delete_documents(delete_docs)
                successful_deletes = sum(1 for r in result if r.succeeded)
                failed_deletes = len(result) - successful_deletes
                
                total_deleted += successful_deletes
                failed_deletions += failed_deletes
                
                logger.info(f"Batch {i//batch_size + 1}: Deleted {successful_deletes}/{len(batch_ids)} documents")
                
            except Exception as e:
                logger.error(f"Error deleting batch starting at {i}: {str(e)}")
                failed_deletions += len(batch_ids)
        
        return {
            "status": "success" if total_deleted > 0 else "error",
            "message": f"Deleted {total_deleted} documents" + 
                      (f" ({failed_deletions} failed)" if failed_deletions > 0 else ""),
            "deleted_chunks": total_deleted,
            "failed_deletions": failed_deletions,
            "requested_count": len(document_ids),
            "found_count": len(existing_docs)
        }
        
    except Exception as e:
        logger.error(f"Error deleting multiple documents: {str(e)}")
        return {"status": "error", "message": str(e)}

def get_documents_from_azure_search_index(filename: str = None, document_id: str = None, limit: int = 50) -> Dict:
    """
    Retrieve documents directly from Azure Search index with their actual content
    
    Args:
        filename: Filter by specific filename
        document_id: Get specific document by ID
        limit: Maximum number of documents to retrieve
        
    Returns:
        Dictionary with status and list of documents with full content
    """
    try:
        logger.info("🔍 Retrieving documents directly from Azure Search index...")
        client = get_search_client()
        
        # Build search parameters
        search_params = {
            "top": limit,
            "select": "id,title,paragraph,summary,keyphrases,filename,ParagraphId,date,group,department,language,isCompliant"
        }
        
        # Handle document_id search differently since 'id' is not filterable
        if document_id:
            # Search for specific document by ID using search_text
            search_params["search_text"] = f"id:{document_id}"
            search_params["search_mode"] = "all"
        else:
            # Build filter for other parameters
            filters = []
            if filename:
                filters.append(f"filename eq '{filename}'")
            
            if filters:
                search_params["filter"] = " and ".join(filters)
                search_params["search_text"] = "*"  # Get all matching documents
            else:
                search_params["search_text"] = "*"  # Get all documents
        
        logger.info(f"📊 Searching with parameters: {search_params}")
        
        # Execute search or get document directly
        if document_id:
            # For specific document, get it directly by key
            try:
                doc = client.get_document(key=document_id)
                results = [doc]  # Make it iterable like search results
            except Exception as e:
                logger.warning(f"Document {document_id} not found: {e}")
                results = []
        else:
            # For general search
            results = client.search(**search_params)
        
        # Collect documents with full content
        documents = []
        for doc in results:
            documents.append({
                "id": doc.get("id"),
                "title": doc.get("title"),
                "content": doc.get("paragraph"),  # This is the actual content in Azure Search
                "content_length": len(doc.get("paragraph", "")),
                "summary": doc.get("summary"),
                "keyphrases": doc.get("keyphrases", []),
                "filename": doc.get("filename"),
                "paragraph_id": doc.get("ParagraphId"),
                "date": doc.get("date"),
                "group": doc.get("group", []),
                "department": doc.get("department"),
                "language": doc.get("language"),
                "is_compliant": doc.get("isCompliant"),
                "search_score": getattr(doc, '@search.score', None)
            })
        
        logger.info(f"✅ Retrieved {len(documents)} documents from Azure Search index")
        
        return {
            "status": "success",
            "message": f"Retrieved {len(documents)} documents from Azure Search index",
            "documents": documents,
            "total_documents": len(documents),
            "filters": {
                "filename": filename,
                "document_id": document_id,
                "limit": limit
            },
            "index_name": config.AZURE_SEARCH_DOC_INDEX
        }
        
    except Exception as e:
        logger.error(f"Error retrieving documents from Azure Search index: {str(e)}")
        return {"status": "error", "message": str(e), "documents": []}

def reset_azure_search_index() -> Dict:
    """Delete all documents from the Azure Search index"""
    try:
        logger.info("🗑️ Starting Azure Search index reset...")
        client = get_search_client()
        
        # Get all documents in the index
        results = client.search(
            search_text="*",
            select="id",
            top=1000  # Adjust if you have more than 1000 documents
        )
        
        document_ids = [doc["id"] for doc in results]
        
        if not document_ids:
            return {
                "status": "success",
                "message": "Azure Search index is already empty",
                "deleted_documents": 0
            }
        
        logger.info(f"📊 Found {len(document_ids)} documents to delete")
        
        # Delete documents in batches (Azure Search has batch limits)
        batch_size = 100
        total_deleted = 0
        failed_deletions = 0
        
        for i in range(0, len(document_ids), batch_size):
            batch_ids = document_ids[i:i + batch_size]
            delete_docs = [{"id": doc_id} for doc_id in batch_ids]
            
            try:
                result = client.delete_documents(delete_docs)
                successful_deletes = sum(1 for r in result if r.succeeded)
                failed_deletes = len(result) - successful_deletes
                
                total_deleted += successful_deletes
                failed_deletions += failed_deletes
                
                logger.info(f"🗑️ Batch {i//batch_size + 1}: Deleted {successful_deletes}/{len(batch_ids)} documents")
                
            except Exception as e:
                logger.error(f"Failed to delete batch {i//batch_size + 1}: {e}")
                failed_deletions += len(batch_ids)
        
        return {
            "status": "success" if failed_deletions == 0 else "partial_success",
            "message": f"Deleted {total_deleted} documents from Azure Search index" + 
                      (f" ({failed_deletions} failed)" if failed_deletions > 0 else ""),
            "deleted_documents": total_deleted,
            "failed_deletions": failed_deletions,
            "total_found": len(document_ids)
        }
        
    except Exception as e:
        logger.error(f"Error resetting Azure Search index: {str(e)}")
        return {"status": "error", "message": str(e)}

async def process_document_with_ai_keyphrases(file_path: str, filename: str, force_reindex: bool = False, chunking_method: str = None) -> Dict:
    """Enhanced version that uses OpenAI to extract intelligent key phrases and saves chunks to database"""
    try:
        # Import config to get default chunking method
        from config.config import config
        
        # Use environment variable default if no chunking method provided
        if chunking_method is None:
            chunking_method = config.DEFAULT_CHUNKING_METHOD
            
        logger.info(f"🔄 Processing document: {filename} with chunking method: {chunking_method}")
        
        # Initialize database manager to save chunks locally
        db_mgr = None
        file_id = None
        DatabaseManagerClass = get_database_manager_class()
        if DatabaseManagerClass:
            try:
                db_mgr = DatabaseManagerClass()
                await db_mgr.initialize()
                
                # Try to find existing file by filename or create placeholder
                # For now, we'll create a placeholder since we don't have the original file metadata
                from contracts.models import FileMetadata
                import os
                
                placeholder_metadata = FileMetadata(
                    filename=filename,
                    original_filename=filename,
                    file_size=os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                    content_type=f"application/{filename.split('.')[-1]}",
                    blob_url=f"processed://{filename}",
                    container_name="processed-documents",
                    upload_timestamp=datetime.now(),
                    checksum="processed",
                    user_id="document-processor"
                )
                
                # Check if file already exists to avoid duplicates
                # For now, we'll create a new record each time since we don't have unique filename constraint
                file_id = await db_mgr.save_file_metadata(placeholder_metadata)
                logger.info(f"📝 Created/found file record with ID: {file_id}")
                
            except Exception as e:
                logger.warning(f"Failed to initialize database for chunk saving: {e}")
                db_mgr = None
        
        # Step 1: Extract content with proper paragraphs
        logger.info("📄 Extracting content with proper paragraph reconstruction...")
        file_extension = filename.lower().split('.')[-1]
        document_text = process_document_content(file_path, file_extension)
        
        # Calculate content hash for intelligent document handling
        import hashlib
        document_content_hash = hashlib.sha256(document_text.encode('utf-8')).hexdigest()[:12]  # Short hash for IDs
        
        if not document_text:
            logger.error(f"Content extraction failed for {filename} (extension: {file_extension})")
            return {
                "status": "error", 
                "message": f"Failed to extract content from {file_extension.upper()} file. Please ensure the file is valid and contains extractable text."
            }
        
        # Step 2: Choose chunking method based on parameter
        validation_metrics = None
        if chunking_method == "intelligent":
            logger.info("🧠 Using OpenAI for intelligent semantic chunking...")
            chunks = intelligent_chunk_with_openai(document_text, "legal", max_chunk_size=1200)
            logger.info(f"✅ Created {len(chunks)} intelligent semantic chunks")
            chunk_method_used = "AI_semantic_analysis"
            enhancement_type = "OpenAI_intelligent_chunking_with_semantic_boundaries"
            validation_metrics = validate_content_preservation(document_text, chunks, "intelligent chunking")
        elif chunking_method == "heading":
            logger.info("📋 Using heading-based structural chunking...")
            chunks = heading_based_chunking(document_text)
            logger.info(f"✅ Created {len(chunks)} heading-based chunks")
            chunk_method_used = "heading_based_chunking"
            enhancement_type = "structural_heading_chunking"
            validation_metrics = validate_content_preservation(document_text, chunks, "heading-based chunking")
        else:  # basic or sentence-based
            logger.info("📝 Using basic sentence-based chunking...")
            chunks = fallback_sentence_chunking(document_text, max_chunk_size=500)  # Smaller chunks for more chunks
            logger.info(f"✅ Created {len(chunks)} sentence-based chunks")
            chunk_method_used = "sentence_based_chunking"
            enhancement_type = "basic_sentence_chunking"
            validation_metrics = validate_content_preservation(document_text, chunks, "sentence-based chunking")
        
        # Step 3: Create enhanced chunks with AI key phrase extraction
        logger.info("🧠 Creating chunks with AI-powered key phrase extraction...")
        documents = []
        chunk_id_mapping = {}  # Map document index to chunk_id
        base_key = sanitize_document_key(filename)
        
        # Create a unique processing timestamp for document IDs
        processing_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
        
        for i, chunk_text in enumerate(chunks, 1):
            if len(chunk_text.strip()) > 50:  # Only meaningful chunks
                logger.info(f"📝 Processing chunk {i}/{len(chunks)}...")
                
                # Generate AI-powered key phrases
                keyphrases = extract_keyphrases_with_openai(chunk_text, "legal")
                
                # Generate embedding
                embedding = generate_text_embedding(chunk_text)
                
                # Create enhanced summary using OpenAI
                summary_prompt = f"Create a concise 1-2 sentence summary of this legal text: {chunk_text[:500]}..."
                try:
                    client = get_openai_client()
                    
                    def summary_call():
                        return client.chat.completions.create(
                            model=config.AZURE_OPENAI_MODEL_DEPLOYMENT,
                            messages=[{"role": "user", "content": summary_prompt}],
                            max_tokens=100,
                            temperature=0.1,
                            timeout=20
                        )
                    
                    summary_response = safe_openai_call("Summary Generation", summary_call)
                    ai_summary = summary_response.choices[0].message.content.strip()
                    summary = ai_summary if ai_summary else chunk_text[:100] + "..."
                except Exception as e:
                    logger.warning(f"Failed to generate AI summary: {e}")
                    # Fallback summary
                    sentences = chunk_text.split('. ')
                    summary = sentences[0] + "." if len(sentences) > 1 else chunk_text[:100] + "..."
                
                # Create descriptive title using OpenAI
                title_prompt = f"Create a short descriptive title (3-6 words) for this legal text: {chunk_text[:200]}..."
                try:
                    client = get_openai_client()
                    
                    def title_call():
                        return client.chat.completions.create(
                            model=config.AZURE_OPENAI_MODEL_DEPLOYMENT,
                            messages=[{"role": "user", "content": title_prompt}],
                            max_tokens=20,
                            temperature=0.1,
                            timeout=20
                        )
                    
                    title_response = safe_openai_call("Title Generation", title_call)
                    ai_title = title_response.choices[0].message.content.strip().strip('"')
                    title = ai_title if ai_title else f"Section {i}"
                except Exception as e:
                    logger.warning(f"Failed to generate AI title: {e}")
                    title = f"Section {i}"
                
                # Create document for indexing with unique timestamp and content-based ID
                document = {
                    "id": f"{base_key}_{document_content_hash}_{i}",
                    "title": title,
                    "paragraph": chunk_text.strip(),
                    "summary": summary,
                    "keyphrases": keyphrases,
                    "filename": filename,
                    "ParagraphId": str(i),
                    "date": datetime.now().isoformat(),
                    "group": ["legal"],
                    "department": "legal",
                    "language": "en",
                    "isCompliant": True,
                    "IrrelevantCollection": [],
                    "NonCompliantCollection": [],
                    "CompliantCollection": [str(i)],
                    "embedding": embedding
                }
                documents.append(document)
                
                # Save chunk to local database if available
                if db_mgr and file_id:
                    try:
                        chunk_id = await db_mgr.save_document_chunk(
                            file_id=file_id,
                            chunk_index=i-1,  # 0-based index
                            chunk_method=chunking_method,
                            chunk_text=chunk_text.strip(),
                            keyphrases=keyphrases,
                            ai_summary=summary,
                            ai_title=title
                        )
                        logger.debug(f"💾 Saved chunk {i} to database with ID: {chunk_id}")
                        
                        # Store the chunk_id mapping separately (not in the document)
                        chunk_id_mapping[len(documents)-1] = chunk_id
                        
                    except Exception as e:
                        logger.warning(f"Failed to save chunk {i} to database: {e}")
        
        logger.info(f"✅ Created {len(documents)} AI-enhanced chunks with intelligent boundaries")
        
        # Step 2.5: Save chunks to local database summary
        if db_mgr and file_id:
            saved_chunks = await db_mgr.get_document_chunks(file_id, chunking_method)
            logger.info(f"💾 Saved {len(saved_chunks)} chunks to local SQLite database")
        
        # Step 3: Handle existing documents intelligently
        existing_docs_count = 0
        
        if force_reindex:
            logger.info(f"🗑️ Force reindex requested - removing documents with same content (hash: {document_content_hash})...")
            
            delete_result = delete_document_by_content_hash(filename, document_content_hash, document_text)
            if delete_result['status'] == 'success':
                logger.info(f"✅ Removed {delete_result['deleted_chunks']} existing chunks with same content")
            elif delete_result['status'] == 'not_found':
                logger.info(f"📝 No existing documents found with same content")
            else:
                logger.warning(f"⚠️ Failed to delete existing documents: {delete_result.get('message', 'Unknown error')}")
        else:
            # Check if documents already exist for this filename
            try:
                client = get_search_client()
                existing_results = client.search(
                    search_text="*",
                    filter=f"filename eq '{filename}'",
                    select="id",
                    top=1
                )
                existing_docs = list(existing_results)
                existing_docs_count = len(existing_docs)
                
                if existing_docs_count > 0:
                    logger.info(f"📋 Found existing documents for {filename} - will add new chunks alongside existing ones")
                else:
                    logger.info(f"📝 No existing documents found for {filename} - this is a new document")
                    
            except Exception as e:
                logger.warning(f"⚠️ Could not check for existing documents: {str(e)} - proceeding with upload")
        
        # Step 4: Ensure Azure Search index exists before uploading
        logger.info("🔍 Ensuring Azure Search index exists...")
        try:
            from contracts.index_creation import create_document_index_if_not_exists
            index_result = create_document_index_if_not_exists()
            if index_result["status"] in ["created", "exists"]:
                logger.info(f"✅ Index ready: {index_result['message']}")
            else:
                logger.error(f"❌ Index creation failed: {index_result['message']}")
                return {
                    "status": "error",
                    "message": f"Failed to create/verify Azure Search index: {index_result['message']}"
                }
        except Exception as e:
            logger.error(f"❌ Error checking/creating index: {str(e)}")
            return {
                "status": "error", 
                "message": f"Failed to verify Azure Search index: {str(e)}"
            }
        
        # Step 5: Upload to Azure Search
        logger.info(f"☁️ Uploading {len(documents)} enhanced documents to Azure Search...")
        client = get_search_client()
        result = client.upload_documents(documents=documents)
        
        successful_uploads = sum(1 for r in result if r.succeeded)
        failed_uploads = len(result) - successful_uploads
        
        # Step 5.5: Save Azure Search chunk records to local database
        if db_mgr and file_id and chunk_id_mapping:
            logger.info("💾 Saving Azure Search chunk records...")
            for i, (doc, upload_result) in enumerate(zip(documents, result)):
                local_chunk_id = chunk_id_mapping.get(i)
                if local_chunk_id:
                    try:
                        upload_status = 'success' if upload_result.succeeded else 'failed'
                        error_message = None if upload_result.succeeded else str(getattr(upload_result, 'error_message', 'Upload failed'))
                        
                        azure_chunk_id = await db_mgr.save_azure_search_chunk(
                            document_chunk_id=local_chunk_id,
                            search_document_id=doc['id'],
                            index_name=client._index_name,  # Get index name from search client
                            upload_status=upload_status,
                            upload_response=str(upload_result) if upload_result else None,
                            embedding_dimensions=len(doc['embedding']) if doc.get('embedding') else None,
                            error_message=error_message,
                            # Persist paragraph data from Azure Search document
                            paragraph_content=doc.get('paragraph'),
                            paragraph_title=doc.get('title'),
                            paragraph_summary=doc.get('summary'),
                            paragraph_keyphrases=json.dumps(doc.get('keyphrases', [])) if doc.get('keyphrases') else None,
                            filename=doc.get('filename'),
                            paragraph_id=doc.get('ParagraphId'),
                            date_uploaded=datetime.fromisoformat(doc.get('date').replace('Z', '+00:00')) if doc.get('date') else None,
                            group_tags=json.dumps(doc.get('group', [])) if doc.get('group') else None,
                            department=doc.get('department'),
                            language=doc.get('language'),
                            is_compliant=doc.get('isCompliant'),
                            content_length=len(doc.get('paragraph', '')) if doc.get('paragraph') else None
                        )
                        logger.debug(f"💾 Saved Azure Search chunk record with ID: {azure_chunk_id}")
                        
                    except Exception as e:
                        logger.warning(f"Failed to save Azure Search chunk record for doc {doc['id']}: {e}")
            
            logger.info(f"💾 Saved Azure Search chunk records for {len(chunk_id_mapping)} chunks")
        
        # Prepare chunk details for response (full content included)
        chunk_details = []
        for i, doc in enumerate(documents):
            # No need to clean up internal fields since we're not adding them to documents anymore
            
            upload_result = result[i] if i < len(result) else None
            chunk_details.append({
                "chunk_id": doc["id"],
                "title": doc["title"],
                "content": doc["paragraph"].strip(),  # Full content without truncation
                "content_size": len(doc["paragraph"]),
                "keyphrases": doc["keyphrases"],
                "status": "success" if (upload_result and upload_result.succeeded) else "failed",
                "error": None if (upload_result and upload_result.succeeded) else str(getattr(upload_result, 'error_message', 'Upload failed'))
            })
        
        # Create informative message about document processing
        if force_reindex:
            process_message = f"Successfully processed {filename} with {chunking_method} chunking (replaced existing documents)"
        elif existing_docs_count > 0:
            process_message = f"Successfully processed {filename} with {chunking_method} chunking (added to existing documents)"
        else:
            process_message = f"Successfully processed {filename} with {chunking_method} chunking (new document)"

        return {
            "status": "success",
            "message": process_message,
            "filename": filename,
            "chunks_created": len(documents),
            "successful_uploads": successful_uploads,
            "failed_uploads": failed_uploads,
            "enhancement": enhancement_type,
            "chunking_method": chunk_method_used,
            "chunk_details": chunk_details,
            "content_validation": validation_metrics,
            "existing_documents_found": existing_docs_count if not force_reindex else 0,
            "force_reindex": force_reindex
        }
        
    except Exception as e:
        logger.error(f"Error in AI keyphrase processing: {str(e)}")
        return {"status": "error", "message": str(e)}