#!/usr/bin/env python3
"""
KARMA Test Script

Run the KARMA pipeline on a PDF document to extract software usage knowledge.
 
Usage:
    # Set your API key as an environment variable first:
    # Windows (PowerShell): $env:OPENAI_API_KEY = "your-api-key"
    # Windows (CMD): set OPENAI_API_KEY=your-api-key
    # Linux/Mac: export OPENAI_API_KEY="your-api-key"
 
    python run_karma.py <path-to-pdf>
    python run_karma.py "D:\\Documents\\Photoshop Manual.pdf"
"""
 
import os
import sys
import argparse
from karma_pipeline import KARMA
 
 
def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='KARMA: Extract software usage knowledge from PDF documentation'
    )
    parser.add_argument(
        'pdf_path',
        help='Path to the PDF document to process'
    )
    parser.add_argument(
        '--output', '-o',
        default='karma_knowledge_graph.json',
        help='Output file path (default: karma_knowledge_graph.json)'
    )
    args = parser.parse_args()
 
    # Validate PDF path
    if not os.path.exists(args.pdf_path):
        print(f"Error: File not found: {args.pdf_path}")
        sys.exit(1)
 
    if not args.pdf_path.lower().endswith('.pdf'):
        print(f"Warning: File does not have .pdf extension: {args.pdf_path}")
 
    # Read API key from environment variable
    api_key = os.environ.get("OPENAI_API_KEY")
    
 
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        print()
        print("Please set it before running this script:")
        print("  Windows (PowerShell): $env:OPENAI_API_KEY = 'your-api-key'")
        print("  Windows (CMD):        set OPENAI_API_KEY=your-api-key")
        print("  Linux/Mac:            export OPENAI_API_KEY='your-api-key'")
        sys.exit(1)
 
    # Optional: Read base URL from environment (for Azure or custom endpoints)
    base_url = os.environ.get("OPENAI_BASE_URL")
 
    # Optional: Read model from environment, default to gpt-5.2
    model_name = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
 
    # Initialize KARMA
    print(f"Initializing KARMA with model: {model_name}")
    karma = KARMA(
        api_key=api_key,
        base_url=base_url,
        model_name=model_name
    )
 
    # =========================================================================
    # Process the PDF document
    # =========================================================================
 
    print("\n" + "="*60)
    print(f"Processing: {args.pdf_path}")
    print("="*60 + "\n")
 
    result = karma.process_document(args.pdf_path)
 
    print(f"\nExtraction Results:")
    print(f"  - Software: {result.get('software', 'Unknown')}")
    print(f"  - Version: {result.get('version', 'N/A')}")
    print(f"  - Entities extracted: {result.get('entities', 0)}")
    print(f"  - Procedures extracted: {result.get('procedures', 0)}")
    print(f"  - Triples extracted: {result.get('triples', 0)}")
    print(f"  - Processing time: {result.get('processing_time', 0):.2f}s")
 
    # =========================================================================
    # Export and display results
    # =========================================================================
 
    # Export knowledge graph to JSON
    karma.export_knowledge_graph(args.output)
    print(f"\nKnowledge graph exported to: {args.output}")
 
    # Save intermediate results for debugging
    intermediate_file = f"intermediate_{args.output}"
    karma.save_intermediate_results(intermediate_file)
    print(f"Intermediate results saved to: {intermediate_file}")

if __name__ == "__main__":
    main()
