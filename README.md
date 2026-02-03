# KARMA Knowledge Graph Dashboard

A comprehensive tool for extracting, storing, and visualizing software usage knowledge from documentation using the KARMA (Knowledge Acquisition and Representation for Manuals and Applications) pipeline.

## Features

- **Knowledge Extraction**: Extract structured knowledge (entities, procedures, relationships) from PDF documentation
- **Multiple Storage Formats**: Store knowledge graphs in JSON, SQLite, or CSV formats
- **Interactive Visualization**: Web-based dashboard for exploring knowledge graphs visually
- **Version Tracking**: Track knowledge across different software versions

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set your OpenAI API key:
```powershell
# Windows PowerShell
$env:OPENAI_API_KEY = "your-api-key-here"
```

## Usage

### 1. Extract Knowledge from PDF

Run the KARMA pipeline on a PDF document:

```bash
python run_karma.py "path/to/document.pdf"
```

This will generate:
- `karma_knowledge_graph.json` - The main knowledge graph file
- `intermediate_karma_knowledge_graph.json` - Intermediate processing results

### 2. Store the Knowledge Graph

Store your knowledge graph in various formats:

```bash
# Store in all formats (JSON, SQLite, CSV)
python store_knowledge_graph.py karma_knowledge_graph.json

# Store only in SQLite database
python store_knowledge_graph.py karma_knowledge_graph.json --format sqlite --output my_kg.db

# Export to CSV files
python store_knowledge_graph.py karma_knowledge_graph.json --format csv --output exports/
```

**Storage Options:**
- **JSON**: Human-readable format, easy to version control
- **SQLite**: Structured database for querying and analysis
- **CSV**: Spreadsheet-friendly format for data analysis

### 3. Visualize the Knowledge Graph

Launch an interactive web dashboard:

```bash
python visualize_knowledge_graph.py karma_knowledge_graph.json
```

This will:
- Start a local web server (default: http://localhost:8000)
- Automatically open your browser
- Display an interactive graph visualization

**Visualization Features:**
- Interactive node graph with zoom, pan, and drag
- Filter by relation type or entity type
- Multiple layout algorithms (hierarchical, force-directed, circular)
- Click nodes to view detailed information
- Real-time statistics display

**Customize the server:**
```bash
# Use a different port
python visualize_knowledge_graph.py karma_knowledge_graph.json --port 8080

# Don't auto-open browser
python visualize_knowledge_graph.py karma_knowledge_graph.json --no-browser
```

## Knowledge Graph Structure

The knowledge graph contains:

- **Entities**: UI elements, tools, features (e.g., "Toolbox", "Crop Tool")
- **Procedures**: Step-by-step workflows (e.g., "Creating a New Layer")
- **Triples**: Relationships between entities (e.g., "Crop Tool -[located_in]-> Toolbox")
- **Metadata**: Software name, versions, statistics

## Example Workflow

```bash
# 1. Extract knowledge from PDF
python run_karma.py "photoshop-manual.pdf"

# 2. Store in database for querying
python store_knowledge_graph.py karma_knowledge_graph.json --format sqlite

# 3. Visualize interactively
python visualize_knowledge_graph.py karma_knowledge_graph.json
```

## Files

- `run_karma.py` - Main script to extract knowledge from PDFs
- `karma_pipeline.py` - Core KARMA pipeline implementation
- `store_knowledge_graph.py` - Storage utility for knowledge graphs
- `visualize_knowledge_graph.py` - Web visualization dashboard
- `karma_knowledge_graph.json` - Generated knowledge graph (JSON format)

## Configuration

Set environment variables for customization:

```powershell
# OpenAI API Key (required)
$env:OPENAI_API_KEY = "your-api-key"

# Optional: Custom OpenAI endpoint (for Azure, etc.)
$env:OPENAI_BASE_URL = "https://your-endpoint.com"

# Optional: Model selection (default: gpt-4.1-mini)
$env:OPENAI_MODEL = "gpt-4o"
```

## Troubleshooting

**Server won't start:**
- Check if the port is already in use
- Try a different port with `--port` option

**Graph not loading:**
- Verify the JSON file is valid
- Check browser console for errors

**Storage errors:**
- Ensure you have write permissions in the output directory
- Check disk space availability
