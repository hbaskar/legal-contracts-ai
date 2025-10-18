# Document Chunking Methods Reference

## Overview
This document provides a comprehensive reference for all chunking methods available in the Fresh Start Document Processing system, including their corresponding Python functions, use cases, and characteristics.

## Chunking Methods Summary Table

| Method Name | API Parameter | Python Function | Module | Description | Use Case | Typical Chunk Count | Processing Speed |
|-------------|---------------|-----------------|---------|-------------|----------|-------------------|-----------------|
| **Intelligent (AI)** | `"intelligent"` | `intelligent_chunk_with_openai()` | `ai_services.py` | Uses OpenAI to create semantic boundaries with context awareness | Complex documents requiring semantic understanding | 3-8 chunks | Slow (AI processing) |
| **Heading-Based** | `"heading"` | `heading_based_chunking()` | `ai_services.py` | Splits on document structure (headings, sections) | Structured documents with clear hierarchy | 2-6 chunks | Fast |
| **Fixed-Size** | `"basic"` or `"fixed"` | `simple_chunk_text()` | `ai_services.py` | Simple character-based splitting with fixed size | Baseline comparison, consistent chunk sizes | 5-15 chunks | Very Fast |
| **Sentence-Based** | `"sentence"` | `fallback_sentence_chunking()` | `ai_services.py` | Splits on sentence boundaries with size limits | Fallback method, maintains sentence integrity | 8-20 chunks | Fast |
| **Paragraph-Based** | `"paragraph"` | `paragraph_chunking()` | `chunk_comparison.py` | Splits on paragraph boundaries | Documents with clear paragraph structure | 3-10 chunks | Fast |

## Detailed Function Reference

### 1. Intelligent (AI) Chunking
```python
def intelligent_chunk_with_openai(document_text: str, document_type: str = "legal", max_chunk_size: int = 1000) -> List[str]
```
**Location:** `contracts/ai_services.py:195`

**Features:**
- ✅ Uses OpenAI GPT for semantic analysis
- ✅ Maintains context and meaning boundaries
- ✅ Handles complex document structures
- ✅ Best content preservation
- ⚠️ Requires OpenAI API access
- ⚠️ Slowest processing time
- ⚠️ API costs apply

**Method Identifier:** `"AI_semantic_analysis"`

### 2. Heading-Based Chunking
```python
def heading_based_chunking(document_text: str) -> List[str]
```
**Location:** `contracts/ai_services.py:481`

**Features:**
- ✅ Preserves document structure
- ✅ Fast processing
- ✅ Logical organization
- ✅ Good for structured documents
- ⚠️ Requires clear headings in document
- ⚠️ May create uneven chunk sizes

**Method Identifier:** `"heading_based_chunking"`

**Detection Patterns:**
- Lines starting with capital letters and short length
- Lines with numbering (1., 2., Section 1, etc.)
- Lines with special formatting indicators

### 3. Fixed-Size Chunking
```python
def simple_chunk_text(text: str, max_chunk_size: int) -> List[str]
```
**Location:** `contracts/ai_services.py:94`

**Features:**
- ✅ Fastest processing
- ✅ Predictable chunk sizes
- ✅ Good baseline for comparison
- ✅ No external dependencies
- ⚠️ May split words or sentences
- ⚠️ No semantic awareness

**Method Identifier:** `"fixed_size"`

### 4. Sentence-Based Chunking
```python
def fallback_sentence_chunking(document_text: str, max_chunk_size: int = 1000) -> List[str]
```
**Location:** `contracts/ai_services.py:366`

**Features:**
- ✅ Maintains sentence integrity
- ✅ Fast processing
- ✅ Good fallback option
- ✅ Respects natural language boundaries
- ⚠️ May create very small or large chunks
- ⚠️ Limited semantic understanding

**Method Identifier:** `"sentence_based_chunking"`

### 5. Paragraph-Based Chunking
```python
async def _process_with_paragraph(self, document_text: str, file_id: int, document_type: str) -> Dict[str, Any]
```
**Location:** `contracts/chunk_comparison.py:270`

**Features:**
- ✅ Preserves paragraph structure
- ✅ Natural document boundaries
- ✅ Good for well-formatted documents
- ⚠️ Variable chunk sizes
- ⚠️ Depends on document formatting

**Method Identifier:** `"paragraph"`

## Main Processing Function

### Document Processing Entry Point
```python
async def process_document_with_ai_keyphrases(file_path: str, filename: str, force_reindex: bool = False, chunking_method: str = "intelligent") -> Dict
```
**Location:** `contracts/ai_services.py:858`

**Supported chunking_method values:**
- `"intelligent"` → Uses `intelligent_chunk_with_openai()`
- `"heading"` → Uses `heading_based_chunking()`
- `"basic"`, `"sentence"`, or other → Uses `fallback_sentence_chunking()`

## Chunk Comparison System

### Comprehensive Analysis Function
```python
async def process_document_with_all_methods(self, document_text: str, filename: str, file_id: int, document_type: str = "legal") -> Dict[str, Any]
```
**Location:** `contracts/chunk_comparison.py:60`

**Processes document with all 4 methods:**
1. Fixed-size chunking
2. Intelligent AI chunking  
3. Heading-based chunking
4. Paragraph-based chunking

**Creates 6 comparisons:**
- Fixed vs Intelligent
- Fixed vs Heading  
- Fixed vs Paragraph
- Intelligent vs Heading
- Intelligent vs Paragraph
- Heading vs Paragraph

## Content Validation

### Validation Function
```python
def validate_content_preservation(original_text: str, chunks: List[str], method_name: str) -> Dict[str, Any]
```
**Location:** `contracts/ai_services.py:398`

**Validation Metrics:**
- Content preservation percentage
- Total chunks created
- Average chunk size
- Size distribution analysis

## Database Integration

### Chunk Storage
All chunks are saved to the `document_chunks` table with:
- `file_id` - Links to file metadata
- `chunk_method` - Method identifier
- `chunk_text` - Full chunk content
- `keyphrases` - AI-extracted keywords
- `ai_summary` - AI-generated summary
- `ai_title` - AI-generated title

### Azure Search Integration
Azure Search uploads are tracked in `azure_search_chunks` table with:
- `document_chunk_id` - Links to local chunk
- `search_document_id` - Azure Search document ID
- `upload_status` - Success/failure status
- `embedding_dimensions` - Vector dimensions

## Configuration

### Environment Variable
You can set the default chunking method for your application using the environment variable:

```bash
DEFAULT_CHUNKING_METHOD=intelligent
```

**Available Options:**
- `intelligent` - AI-powered semantic chunking (default)
- `heading` - Structure-based chunking using document headings
- `sentence` - Sentence boundary-aware chunking  
- `basic` - Simple fixed-size chunking
- `paragraph` - Paragraph boundary-based chunking

### Configuration Files
Add to your `.env` file:
```bash
# === DOCUMENT PROCESSING CONFIGURATION ===
# Default chunking method for document processing
# Options: 'intelligent', 'heading', 'sentence', 'basic', 'paragraph'
DEFAULT_CHUNKING_METHOD=intelligent
```

Add to your `local.settings.json` file:
```json
{
  "Values": {
    "DEFAULT_CHUNKING_METHOD": "intelligent"
  }
}
```

### Runtime Behavior
1. **API Parameter**: If `chunking_method` is provided in the API request, it takes precedence
2. **Environment Variable**: If no API parameter is provided, uses `DEFAULT_CHUNKING_METHOD` from environment
3. **Fallback**: If environment variable is not set, defaults to `"intelligent"`

## Usage Examples

### API Endpoints
```bash
# Intelligent chunking (default)
POST /api/process_document
{
  "file_content": "base64_content",
  "filename": "document.pdf",
  "chunking_method": "intelligent"
}

# Heading-based chunking
POST /api/process_document
{
  "file_content": "base64_content", 
  "filename": "document.pdf",
  "chunking_method": "heading"
}

# Fixed-size chunking
POST /api/process_document
{
  "file_content": "base64_content",
  "filename": "document.pdf", 
  "chunking_method": "basic"
}
```

### Postman Collection
The included Postman collection provides tests for:
- All chunking methods individually
- Comprehensive chunk comparison
- Error handling validation
- Method performance comparison

## Performance Characteristics

| Method | Speed | Quality | Consistency | Dependencies |
|--------|-------|---------|-------------|--------------|
| **Intelligent** | ⭐ (Slow) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | OpenAI API |
| **Heading** | ⭐⭐⭐⭐ (Fast) | ⭐⭐⭐⭐ | ⭐⭐⭐ | None |
| **Fixed-Size** | ⭐⭐⭐⭐⭐ (Fastest) | ⭐⭐ | ⭐⭐⭐⭐⭐ | None |
| **Sentence** | ⭐⭐⭐⭐ (Fast) | ⭐⭐⭐ | ⭐⭐⭐ | None |
| **Paragraph** | ⭐⭐⭐⭐ (Fast) | ⭐⭐⭐⭐ | ⭐⭐ | None |

## Recommendations

### When to Use Each Method

1. **Intelligent (AI)** - Best for:
   - Legal documents requiring precise semantic boundaries
   - Complex technical documentation
   - Documents where context is critical
   - When processing quality is more important than speed

2. **Heading-Based** - Best for:
   - Well-structured documents with clear headings
   - Reports and formal documents
   - When logical organization is important
   - Fast processing with good quality

3. **Fixed-Size** - Best for:
   - Baseline performance testing
   - When consistent chunk sizes are required
   - Resource-constrained environments
   - Simple text processing

4. **Sentence-Based** - Best for:
   - Fallback when other methods fail
   - Documents without clear structure
   - When sentence integrity is important
   - General-purpose text processing

5. **Paragraph-Based** - Best for:
   - Well-formatted documents with clear paragraphs
   - Narrative text and articles
   - When natural document flow should be preserved
   - Comparison analysis

---

*Last Updated: October 17, 2025*
*Fresh Start Document Processing System v1.0*