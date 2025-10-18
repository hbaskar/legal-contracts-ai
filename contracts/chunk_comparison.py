#!/usr/bin/env python3
"""
Chunk Comparison Integration
Integration functions to automatically capture and compare document chunks during processing
"""

import sys
import os
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contracts.database import DatabaseManager
from contracts.ai_services import intelligent_chunk_with_openai, simple_chunk_text, heading_based_chunking

logger = logging.getLogger(__name__)

class ChunkComparison:
    """Helper class for capturing and comparing document chunks"""
    
    def __init__(self):
        self.db = DatabaseManager()
        
    async def initialize(self):
        """Initialize database connection"""
        await self.db.initialize()
    
    async def process_document_with_comparison(self, document_text: str, filename: str, 
                                            file_id: int, document_type: str = "legal",
                                            max_chunk_size: int = 1000) -> Dict[str, Any]:
        """
        Process a document using multiple chunking methods and compare results
        
        Args:
            document_text: The full document text
            filename: Original filename
            file_id: Database file ID
            document_type: Type of document for AI processing
            max_chunk_size: Maximum chunk size for fixed-size method
            
        Returns:
            Comprehensive comparison results
        """
        logger.info(f"🔄 Processing document '{filename}' with multiple chunking methods...")
        
        results = {
            'file_id': file_id,
            'filename': filename,
            'document_length': len(document_text),
            'methods': {},
            'comparisons': [],
            'recommended_method': None,
            'processing_summary': {}
        }
        
        try:
            # Method 1: Fixed-size chunking
            logger.info("📏 Processing with fixed-size chunking...")
            fixed_result = await self._process_with_fixed_size(
                document_text, file_id, max_chunk_size, document_type
            )
            results['methods']['fixed_size'] = fixed_result
            
            # Method 2: Intelligent AI-powered chunking
            logger.info("🧠 Processing with intelligent AI chunking...")
            intelligent_result = await self._process_with_intelligent(
                document_text, file_id, max_chunk_size, document_type
            )
            results['methods']['intelligent'] = intelligent_result
            
            # Method 3: Heading-based structural chunking
            logger.info("📋 Processing with heading-based chunking...")
            heading_result = await self._process_with_headings(
                document_text, file_id, document_type
            )
            results['methods']['heading'] = heading_result
            
            # Method 4: Simple paragraph-based chunking (baseline)
            logger.info("📝 Processing with paragraph-based chunking...")
            paragraph_result = await self._process_with_paragraphs(
                document_text, file_id, document_type
            )
            results['methods']['paragraph'] = paragraph_result
            
            # Compare methods
            logger.info("📊 Comparing chunking methods...")
            
            # Fixed vs Intelligent
            comparison_1 = await self.db.compare_chunking_methods(file_id, "fixed_size", "intelligent")
            results['comparisons'].append(comparison_1)
            
            # Fixed vs Heading
            comparison_2 = await self.db.compare_chunking_methods(file_id, "fixed_size", "heading")
            results['comparisons'].append(comparison_2)
            
            # Fixed vs Paragraph
            comparison_3 = await self.db.compare_chunking_methods(file_id, "fixed_size", "paragraph")
            results['comparisons'].append(comparison_3)
            
            # Intelligent vs Heading
            comparison_4 = await self.db.compare_chunking_methods(file_id, "intelligent", "heading")
            results['comparisons'].append(comparison_4)
            
            # Intelligent vs Paragraph
            comparison_5 = await self.db.compare_chunking_methods(file_id, "intelligent", "paragraph")
            results['comparisons'].append(comparison_5)
            
            # Heading vs Paragraph
            comparison_6 = await self.db.compare_chunking_methods(file_id, "heading", "paragraph")
            results['comparisons'].append(comparison_6)
            
            # Determine recommended method
            results['recommended_method'] = self._determine_best_method(results['comparisons'])
            
            # Create processing summary
            results['processing_summary'] = self._create_processing_summary(results)
            
            logger.info(f"✅ Document processing complete. Recommended method: {results['recommended_method']}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Document processing failed: {e}")
            raise
    
    async def _process_with_fixed_size(self, document_text: str, file_id: int, 
                                     max_chunk_size: int, document_type: str) -> Dict[str, Any]:
        """Process document using fixed-size chunking"""
        start_time = time.time()
        
        # Simple fixed-size chunking
        chunks = simple_chunk_text(document_text, max_chunk_size)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Save chunks to database
        chunk_ids = []
        for i, chunk_text in enumerate(chunks):
            chunk_start = i * max_chunk_size
            chunk_end = min(chunk_start + len(chunk_text), len(document_text))
            
            chunk_id = await self.db.save_document_chunk(
                file_id=file_id,
                chunk_index=i,
                chunk_method="fixed_size",
                chunk_text=chunk_text,
                start_pos=chunk_start,
                end_pos=chunk_end,
                keyphrases=[],  # No AI processing for baseline
                ai_summary=f"Fixed-size chunk {i+1}",
                ai_title=f"Section {i+1}",
                processing_time_ms=processing_time // len(chunks)
            )
            chunk_ids.append(chunk_id)
        
        return {
            'method': 'fixed_size',
            'chunks_created': len(chunks),
            'chunk_ids': chunk_ids,
            'processing_time_ms': processing_time,
            'avg_chunk_size': sum(len(c) for c in chunks) / len(chunks),
            'total_characters': sum(len(c) for c in chunks)
        }
    
    async def _process_with_intelligent(self, document_text: str, file_id: int, 
                                      max_chunk_size: int, document_type: str) -> Dict[str, Any]:
        """Process document using intelligent AI chunking"""
        from contracts.ai_services import extract_keyphrases_with_openai
        
        start_time = time.time()
        
        # AI-powered intelligent chunking
        chunks = intelligent_chunk_with_openai(document_text, document_type, max_chunk_size)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Save chunks to database with AI enhancements
        chunk_ids = []
        for i, chunk_text in enumerate(chunks):
            # Extract keyphrases using AI
            keyphrases = extract_keyphrases_with_openai(chunk_text, document_type)
            
            # Generate simple summary and title
            ai_summary = f"AI-processed chunk {i+1}: {chunk_text[:50]}..."
            ai_title = f"Intelligent Section {i+1}"
            
            chunk_id = await self.db.save_document_chunk(
                file_id=file_id,
                chunk_index=i,
                chunk_method="intelligent",
                chunk_text=chunk_text,
                start_pos=None,  # AI chunking doesn't use fixed positions
                end_pos=None,
                keyphrases=keyphrases,
                ai_summary=ai_summary,
                ai_title=ai_title,
                processing_time_ms=processing_time // len(chunks)
            )
            chunk_ids.append(chunk_id)
        
        return {
            'method': 'intelligent',
            'chunks_created': len(chunks),
            'chunk_ids': chunk_ids,
            'processing_time_ms': processing_time,
            'avg_chunk_size': sum(len(c) for c in chunks) / len(chunks),
            'total_characters': sum(len(c) for c in chunks),
            'ai_enhanced': True
        }
    
    async def _process_with_headings(self, document_text: str, file_id: int, 
                                   document_type: str) -> Dict[str, Any]:
        """Process document using heading-based structural chunking"""
        start_time = time.time()
        
        # Use heading-based chunking from ai_services
        chunks = heading_based_chunking(document_text)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Save chunks to database
        chunk_ids = []
        current_pos = 0
        
        for i, chunk_text in enumerate(chunks):
            start_pos = document_text.find(chunk_text, current_pos)
            end_pos = start_pos + len(chunk_text)
            current_pos = end_pos
            
            # Extract potential heading from chunk for better titles
            chunk_lines = chunk_text.strip().split('\n')
            potential_title = chunk_lines[0] if chunk_lines else f"Section {i+1}"
            
            # Limit title length and clean it up
            if len(potential_title) > 100:
                potential_title = potential_title[:97] + "..."
            
            chunk_id = await self.db.save_document_chunk(
                file_id=file_id,
                chunk_index=i,
                chunk_method="heading",
                chunk_text=chunk_text,
                start_pos=start_pos,
                end_pos=end_pos,
                keyphrases=[],  # No AI processing for structural method
                ai_summary=f"Heading-based section {i+1}",
                ai_title=potential_title,
                processing_time_ms=processing_time // len(chunks) if chunks else 0
            )
            chunk_ids.append(chunk_id)
        
        return {
            'method': 'heading',
            'chunks_created': len(chunks),
            'chunk_ids': chunk_ids,
            'processing_time_ms': processing_time,
            'avg_chunk_size': sum(len(c) for c in chunks) / len(chunks) if chunks else 0,
            'total_characters': sum(len(c) for c in chunks),
            'ai_enhanced': False,
            'structural': True
        }
    
    async def _process_with_paragraphs(self, document_text: str, file_id: int, 
                                     document_type: str) -> Dict[str, Any]:
        """Process document using paragraph-based chunking"""
        start_time = time.time()
        
        # Split by paragraphs (double newlines)
        paragraphs = document_text.split('\n\n')
        chunks = [p.strip() for p in paragraphs if p.strip()]
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Save chunks to database
        chunk_ids = []
        current_pos = 0
        
        for i, chunk_text in enumerate(chunks):
            start_pos = document_text.find(chunk_text, current_pos)
            end_pos = start_pos + len(chunk_text)
            current_pos = end_pos
            
            chunk_id = await self.db.save_document_chunk(
                file_id=file_id,
                chunk_index=i,
                chunk_method="paragraph",
                chunk_text=chunk_text,
                start_pos=start_pos,
                end_pos=end_pos,
                keyphrases=[],  # No AI processing for baseline
                ai_summary=f"Paragraph {i+1}",
                ai_title=f"Paragraph {i+1}",
                processing_time_ms=processing_time // len(chunks)
            )
            chunk_ids.append(chunk_id)
        
        return {
            'method': 'paragraph',
            'chunks_created': len(chunks),
            'chunk_ids': chunk_ids,
            'processing_time_ms': processing_time,
            'avg_chunk_size': sum(len(c) for c in chunks) / len(chunks),
            'total_characters': sum(len(c) for c in chunks)
        }
    
    def _determine_best_method(self, comparisons: List[Dict]) -> str:
        """Determine the best chunking method based on comparison results"""
        
        # Score each method based on various factors
        method_scores = {}
        
        for comparison in comparisons:
            method_a = comparison['method_a']
            method_b = comparison['method_b']
            
            # Initialize scores
            if method_a not in method_scores:
                method_scores[method_a] = {'score': 0, 'factors': []}
            if method_b not in method_scores:
                method_scores[method_b] = {'score': 0, 'factors': []}
            
            # Scoring factors
            similarity_score = comparison['similarity_score']
            
            # Prefer methods with better balance of chunk count and size
            chunk_balance_a = 1 / (1 + abs(comparison['avg_chunk_size_a'] - 800))  # Prefer ~800 char chunks
            chunk_balance_b = 1 / (1 + abs(comparison['avg_chunk_size_b'] - 800))
            
            # Consider processing efficiency
            time_efficiency_a = 1 / (1 + comparison['processing_time_a_ms'] / 1000)
            time_efficiency_b = 1 / (1 + comparison['processing_time_b_ms'] / 1000)
            
            # Update scores
            method_scores[method_a]['score'] += chunk_balance_a + time_efficiency_a
            method_scores[method_b]['score'] += chunk_balance_b + time_efficiency_b
            
            # Bonus for AI-enhanced methods
            if 'intelligent' in [method_a, method_b]:
                ai_method = 'intelligent' if method_a == 'intelligent' else method_b
                method_scores[ai_method]['score'] += 0.5  # AI bonus
                method_scores[ai_method]['factors'].append('AI-enhanced')
        
        # Find best method
        best_method = max(method_scores.keys(), key=lambda m: method_scores[m]['score'])
        
        logger.info(f"📊 Method scores: {method_scores}")
        
        return best_method
    
    def _create_processing_summary(self, results: Dict) -> Dict[str, Any]:
        """Create a comprehensive processing summary"""
        
        methods = results['methods']
        comparisons = results['comparisons']
        
        return {
            'document_stats': {
                'total_length': results['document_length'],
                'filename': results['filename']
            },
            'method_performance': {
                method: {
                    'chunks': data['chunks_created'],
                    'avg_size': data['avg_chunk_size'],
                    'processing_time': data['processing_time_ms'],
                    'efficiency_score': data['chunks_created'] / (data['processing_time_ms'] / 1000) if data['processing_time_ms'] > 0 else 0
                } for method, data in methods.items()
            },
            'best_comparison': max(comparisons, key=lambda c: c['similarity_score']) if comparisons else None,
            'recommended_method': results['recommended_method'],
            'processing_timestamp': datetime.now().isoformat()
        }
    
    async def get_comparison_report(self, file_id: int) -> Dict[str, Any]:
        """Generate a comprehensive comparison report for a file"""
        
        try:
            # Get all chunks for the file
            all_chunks = await self.db.get_document_chunks(file_id)
            
            # Get all comparisons for the file  
            comparisons = await self.db.get_chunk_comparisons(file_id)
            
            # Group chunks by method
            chunks_by_method = {}
            for chunk in all_chunks:
                method = chunk['chunk_method']
                if method not in chunks_by_method:
                    chunks_by_method[method] = []
                chunks_by_method[method].append(chunk)
            
            report = {
                'file_id': file_id,
                'methods_analyzed': list(chunks_by_method.keys()),
                'total_chunks': len(all_chunks),
                'comparisons_count': len(comparisons),
                'methods_summary': {},
                'comparison_results': comparisons,
                'recommendations': []
            }
            
            # Summarize each method
            for method, chunks in chunks_by_method.items():
                report['methods_summary'][method] = {
                    'total_chunks': len(chunks),
                    'avg_chunk_size': sum(c['chunk_size'] for c in chunks) / len(chunks),
                    'total_processing_time': sum(c['processing_time_ms'] or 0 for c in chunks),
                    'has_ai_features': any(c['keyphrases'] for c in chunks),
                    'sample_chunk': chunks[0]['chunk_text'][:100] + "..." if chunks else ""
                }
            
            # Generate recommendations
            if comparisons:
                best_comparison = max(comparisons, key=lambda c: c['similarity_score'])
                report['recommendations'].append(
                    f"Best performing comparison: {best_comparison['method_a']} vs {best_comparison['method_b']} "
                    f"(similarity: {best_comparison['similarity_score']:.2f})"
                )
                
                fastest_method = min(chunks_by_method.keys(), 
                                   key=lambda m: report['methods_summary'][m]['total_processing_time'])
                report['recommendations'].append(f"Fastest method: {fastest_method}")
                
                if 'intelligent' in chunks_by_method:
                    report['recommendations'].append("Intelligent chunking provides AI-enhanced features (keyphrases, summaries)")
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate comparison report: {e}")
            raise

# Convenience functions for easy integration
async def compare_document_chunking(document_text: str, filename: str, file_id: int) -> Dict[str, Any]:
    """
    Convenience function to process a document with multiple chunking methods
    """
    comparator = ChunkComparison()
    await comparator.initialize()
    return await comparator.process_document_with_comparison(document_text, filename, file_id)

async def get_chunking_report(file_id: int) -> Dict[str, Any]:
    """
    Convenience function to get a comparison report for a processed file
    """
    comparator = ChunkComparison()
    await comparator.initialize()
    return await comparator.get_comparison_report(file_id)