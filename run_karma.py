#!/usr/bin/env python3
"""
KARMA Test Script

Run the KARMA pipeline on a document to extract software usage knowledge.

Usage:
    # Set your API key as an environment variable first:
    # Windows (PowerShell): $env:OPENAI_API_KEY = "your-api-key"
    # Windows (CMD): set OPENAI_API_KEY=your-api-key
    # Linux/Mac: export OPENAI_API_KEY="your-api-key"

    python run_karma.py
"""

import os
import sys
from karma_pipeline import KARMA

def main():
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
    model_name = os.environ.get("OPENAI_MODEL", "gpt-5.2")

    # Initialize KARMA
    print(f"Initializing KARMA with model: {model_name}")
    karma = KARMA(
        api_key=api_key,
        base_url=base_url,
        model_name=model_name
    )

    # =========================================================================
    # Example 1: Process a document (tutorial, manual, reference)
    # =========================================================================

    # Option A: Process a PDF file
    # result = karma.process_document(r"D:\path\to\your\document.pdf")

    # Option B: Process text directly
    sample_doc = """
    Photoshop 2024 User Guide - Working with Layers

    Layers are the foundation of image editing in Photoshop. They allow you to
    work on different parts of your image independently.

    Creating a New Layer:
    1. Open the Layers panel by going to Window > Layers (or press F7)
    2. Click the "New Layer" button at the bottom of the Layers panel
    3. In the dialog that appears, enter a name for your layer
    4. Set the opacity and blend mode if desired
    5. Click OK to create the layer

    The new layer will appear above your currently selected layer. You can now
    paint or add content to this layer without affecting other layers.

    Keyboard Shortcuts:
    - Ctrl+Shift+N: Create new layer with dialog
    - Ctrl+J: Duplicate current layer
    - Ctrl+E: Merge layer down

    Layer Opacity:
    Use the Opacity slider in the Layers panel to adjust layer transparency.
    100% is fully opaque, 0% is fully transparent.

    Note: The Background layer is locked by default. Double-click it to convert
    it to a regular layer that can be edited freely.
    """

    print("\n" + "="*60)
    print("Processing sample documentation...")
    print("="*60 + "\n")

    result = karma.process_document(sample_doc)

    print(f"\nExtraction Results:")
    print(f"  - Software: {result.get('software', 'Unknown')}")
    print(f"  - Version: {result.get('version', 'N/A')}")
    print(f"  - Entities extracted: {result.get('entities', 0)}")
    print(f"  - Procedures extracted: {result.get('procedures', 0)}")
    print(f"  - Triples extracted: {result.get('triples', 0)}")
    print(f"  - Processing time: {result.get('processing_time', 0):.2f}s")

    # =========================================================================
    # Example 2: Process release notes (update workflow)
    # =========================================================================

    sample_release_notes = """
    What's New in Photoshop 2025

    NEW FEATURES:
    - Generative Expand: Extend your canvas with AI-generated content
    - Smart Object Improvements: Faster rendering and better quality

    CHANGES:
    - The Healing Brush has moved from the main Toolbar to the Contextual Toolbar
    - Export dialog now remembers your last used settings

    REMOVED:
    - Legacy "Save for Web" dialog has been removed (use Export As instead)

    BUG FIXES:
    - Fixed: Selection tools now work correctly with rotated canvases
    - Fixed: Layer styles no longer reset when duplicating layers
    """

    print("\n" + "="*60)
    print("Processing release notes (update workflow)...")
    print("="*60 + "\n")

    update_result = karma.process_update_document(sample_release_notes, version="2025")

    print(f"\nUpdate Results:")
    print(f"  - Version: {update_result.get('version', 'N/A')}")
    print(f"  - Changes detected: {update_result.get('changes_detected', 0)}")
    print(f"  - Triples deprecated: {update_result.get('triples_deprecated', 0)}")
    print(f"  - Triples flagged for review: {update_result.get('triples_flagged', 0)}")
    print(f"  - New triples added: {update_result.get('triples_added', 0)}")
    print(f"  - Processing time: {update_result.get('processing_time', 0):.2f}s")

    # =========================================================================
    # Export and display results
    # =========================================================================

    # Export knowledge graph to JSON
    output_file = "karma_knowledge_graph.json"
    karma.export_knowledge_graph(output_file)
    print(f"\nKnowledge graph exported to: {output_file}")

    # Save intermediate results for debugging
    karma.save_intermediate_results("karma_intermediate.json")
    print(f"Intermediate results saved to: karma_intermediate.json")

    # Print statistics
    karma.print_statistics()

    # Show any outdated knowledge
    outdated = karma.get_outdated_knowledge()
    if outdated:
        print(f"\nOutdated/Review-needed triples ({len(outdated)}):")
        for triple in outdated[:5]:  # Show first 5
            print(f"  - {triple}")
        if len(outdated) > 5:
            print(f"  ... and {len(outdated) - 5} more")


if __name__ == "__main__":
    main()
