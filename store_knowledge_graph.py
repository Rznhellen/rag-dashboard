#!/usr/bin/env python3
"""
Knowledge Graph Storage Utility

Store and manage KARMA knowledge graphs in various formats:
- JSON (default, human-readable)
- SQLite (structured database for querying)
- Export to other formats (CSV, GraphML, etc.)
"""

import json
import sqlite3
import argparse
import os
from typing import Dict, List, Optional
from datetime import datetime


class KnowledgeGraphStorage:
    """Store and retrieve knowledge graphs from various backends."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize storage.
        
        Args:
            db_path: Path to SQLite database (optional)
        """
        self.db_path = db_path
    
    def load_from_json(self, json_path: str) -> Dict:
        """Load knowledge graph from JSON file."""
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_to_json(self, kg_data: Dict, output_path: str):
        """Save knowledge graph to JSON file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(kg_data, f, indent=2, default=str)
        print(f"✓ Knowledge graph saved to: {output_path}")
    
    def save_to_sqlite(self, kg_data: Dict, db_path: Optional[str] = None):
        """
        Save knowledge graph to SQLite database.
        
        Creates tables for entities, procedures, and triples.
        """
        db_path = db_path or self.db_path
        if not db_path:
            db_path = "karma_knowledge_graph.db"
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_graphs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                software TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS versions (
                kg_id INTEGER,
                version TEXT,
                FOREIGN KEY (kg_id) REFERENCES knowledge_graphs(id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                kg_id INTEGER,
                entity_id TEXT PRIMARY KEY,
                name TEXT,
                entity_type TEXT,
                description TEXT,
                parent_path TEXT,
                software TEXT,
                version_introduced TEXT,
                version_deprecated TEXT,
                aliases TEXT,
                FOREIGN KEY (kg_id) REFERENCES knowledge_graphs(id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS procedures (
                kg_id INTEGER,
                procedure_id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                steps TEXT,
                software TEXT,
                version_introduced TEXT,
                version_deprecated TEXT,
                FOREIGN KEY (kg_id) REFERENCES knowledge_graphs(id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS triples (
                kg_id INTEGER,
                head TEXT,
                relation TEXT,
                tail TEXT,
                head_type TEXT,
                tail_type TEXT,
                introduced_version TEXT,
                deprecated_version TEXT,
                valid_version_range TEXT,
                confidence REAL,
                source_document TEXT,
                source_date TEXT,
                step_order INTEGER,
                status TEXT,
                software TEXT,
                FOREIGN KEY (kg_id) REFERENCES knowledge_graphs(id)
            )
        """)
        
        # Insert knowledge graph metadata
        metadata = json.dumps({
            "statistics": kg_data.get("statistics", {}),
            "created_at": datetime.now().isoformat()
        })
        
        cursor.execute("""
            INSERT INTO knowledge_graphs (software, metadata)
            VALUES (?, ?)
        """, (kg_data.get("software", "Unknown"), metadata))
        
        kg_id = cursor.lastrowid
        
        # Insert versions
        for version in kg_data.get("versions", []):
            cursor.execute("""
                INSERT INTO versions (kg_id, version)
                VALUES (?, ?)
            """, (kg_id, version))
        
        # Insert entities
        for entity in kg_data.get("entities", []):
            aliases_str = json.dumps(entity.get("aliases", []))
            cursor.execute("""
                INSERT OR REPLACE INTO entities 
                (kg_id, entity_id, name, entity_type, description, parent_path,
                 software, version_introduced, version_deprecated, aliases)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                kg_id,
                entity.get("entity_id"),
                entity.get("name"),
                entity.get("entity_type"),
                entity.get("description"),
                entity.get("parent_path"),
                entity.get("software"),
                entity.get("version_introduced"),
                entity.get("version_deprecated"),
                aliases_str
            ))
        
        # Insert procedures
        for procedure in kg_data.get("procedures", []):
            steps_str = json.dumps(procedure.get("steps", []))
            cursor.execute("""
                INSERT OR REPLACE INTO procedures
                (kg_id, procedure_id, name, description, steps, software,
                 version_introduced, version_deprecated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                kg_id,
                procedure.get("procedure_id"),
                procedure.get("name"),
                procedure.get("description"),
                steps_str,
                procedure.get("software"),
                procedure.get("version_introduced"),
                procedure.get("version_deprecated")
            ))
        
        # Insert triples
        for triple in kg_data.get("triples", []):
            cursor.execute("""
                INSERT INTO triples
                (kg_id, head, relation, tail, head_type, tail_type,
                 introduced_version, deprecated_version, valid_version_range,
                 confidence, source_document, source_date, step_order, status, software)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                kg_id,
                triple.get("head"),
                triple.get("relation"),
                triple.get("tail"),
                triple.get("head_type"),
                triple.get("tail_type"),
                triple.get("introduced_version"),
                triple.get("deprecated_version"),
                triple.get("valid_version_range"),
                triple.get("confidence", 0.0),
                triple.get("source_document"),
                triple.get("source_date"),
                triple.get("step_order", 0),
                triple.get("status", "active"),
                triple.get("software")
            ))
        
        conn.commit()
        conn.close()
        
        print(f"✓ Knowledge graph saved to SQLite database: {db_path}")
        print(f"  - Entities: {len(kg_data.get('entities', []))}")
        print(f"  - Procedures: {len(kg_data.get('procedures', []))}")
        print(f"  - Triples: {len(kg_data.get('triples', []))}")
    
    def export_to_csv(self, kg_data: Dict, output_dir: str = "exports"):
        """Export knowledge graph components to CSV files."""
        import csv
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Export entities
        entities_file = os.path.join(output_dir, "entities.csv")
        with open(entities_file, 'w', newline='', encoding='utf-8') as f:
            if kg_data.get("entities"):
                writer = csv.DictWriter(f, fieldnames=kg_data["entities"][0].keys())
                writer.writeheader()
                writer.writerows(kg_data["entities"])
        print(f"✓ Entities exported to: {entities_file}")
        
        # Export triples
        triples_file = os.path.join(output_dir, "triples.csv")
        with open(triples_file, 'w', newline='', encoding='utf-8') as f:
            if kg_data.get("triples"):
                writer = csv.DictWriter(f, fieldnames=kg_data["triples"][0].keys())
                writer.writeheader()
                writer.writerows(kg_data["triples"])
        print(f"✓ Triples exported to: {triples_file}")
        
        # Export procedures
        procedures_file = os.path.join(output_dir, "procedures.csv")
        with open(procedures_file, 'w', newline='', encoding='utf-8') as f:
            if kg_data.get("procedures"):
                writer = csv.DictWriter(f, fieldnames=kg_data["procedures"][0].keys())
                writer.writeheader()
                writer.writerows(kg_data["procedures"])
        print(f"✓ Procedures exported to: {procedures_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Store and manage KARMA knowledge graphs'
    )
    parser.add_argument(
        'input',
        help='Path to input JSON knowledge graph file'
    )
    parser.add_argument(
        '--format', '-f',
        choices=['json', 'sqlite', 'csv', 'all'],
        default='all',
        help='Output format (default: all)'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output file path (for JSON/SQLite) or directory (for CSV)'
    )
    parser.add_argument(
        '--db',
        help='SQLite database path (default: karma_knowledge_graph.db)'
    )
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"Error: File not found: {args.input}")
        return
    
    storage = KnowledgeGraphStorage(db_path=args.db)
    
    print(f"Loading knowledge graph from: {args.input}")
    kg_data = storage.load_from_json(args.input)
    
    software = kg_data.get("software", "Unknown")
    stats = kg_data.get("statistics", {})
    print(f"\nKnowledge Graph: {software}")
    print(f"  - Entities: {stats.get('total_entities', 0)}")
    print(f"  - Procedures: {stats.get('total_procedures', 0)}")
    print(f"  - Triples: {stats.get('total_triples', 0)}")
    print()
    
    # Save in requested format(s)
    if args.format in ['json', 'all']:
        output_path = args.output or f"{software.lower().replace(' ', '_')}_kg.json"
        storage.save_to_json(kg_data, output_path)
    
    if args.format in ['sqlite', 'all']:
        db_path = args.output or args.db or "karma_knowledge_graph.db"
        storage.save_to_sqlite(kg_data, db_path)
    
    if args.format in ['csv', 'all']:
        output_dir = args.output or "exports"
        storage.export_to_csv(kg_data, output_dir)
    
    print("\n✓ Storage complete!")


if __name__ == "__main__":
    main()
