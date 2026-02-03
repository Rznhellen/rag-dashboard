#!/usr/bin/env python3
"""
Knowledge Graph Visualization Dashboard

Start a web server to visualize the KARMA knowledge graph interactively.
"""

import json
import os
import argparse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import webbrowser
import threading
import time


class KnowledgeGraphHandler(SimpleHTTPRequestHandler):
    """HTTP handler that serves the visualization dashboard."""
    
    def __init__(self, *args, kg_data=None, **kwargs):
        self.kg_data = kg_data
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/' or parsed_path.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            html = self.generate_dashboard_html()
            self.wfile.write(html.encode('utf-8'))
        
        elif parsed_path.path == '/api/kg':
            # API endpoint to get knowledge graph data
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(self.kg_data, default=str).encode('utf-8'))
        
        elif parsed_path.path.startswith('/static/'):
            # Serve static files (CSS, JS)
            file_path = parsed_path.path[1:]  # Remove leading /
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-type', self.guess_content_type(file_path))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404)
        
        else:
            self.send_error(404)
    
    def guess_content_type(self, file_path):
        """Guess content type from file extension."""
        ext = os.path.splitext(file_path)[1].lower()
        types = {
            '.js': 'application/javascript',
            '.css': 'text/css',
            '.json': 'application/json',
            '.html': 'text/html'
        }
        return types.get(ext, 'text/plain')
    
    def generate_dashboard_html(self):
        """Generate the HTML dashboard with embedded visualization."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KARMA Knowledge Graph Visualization</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f5f5;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1.5rem 2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .header h1 {{
            font-size: 1.8rem;
            margin-bottom: 0.5rem;
        }}
        
        .header .subtitle {{
            opacity: 0.9;
            font-size: 0.9rem;
        }}
        
        .stats {{
            display: flex;
            gap: 1rem;
            margin-top: 1rem;
            flex-wrap: wrap;
        }}
        
        .stat-card {{
            background: rgba(255,255,255,0.2);
            padding: 0.75rem 1.25rem;
            border-radius: 8px;
            backdrop-filter: blur(10px);
        }}
        
        .stat-card .label {{
            font-size: 0.75rem;
            opacity: 0.8;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .stat-card .value {{
            font-size: 1.5rem;
            font-weight: bold;
            margin-top: 0.25rem;
        }}
        
        .container {{
            display: flex;
            height: calc(100vh - 180px);
            gap: 1rem;
            padding: 1rem;
        }}
        
        .graph-container {{
            flex: 1;
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 20px rgba(0,0,0,0.1);
            position: relative;
            overflow: hidden;
        }}
        
        #graph {{
            width: 100%;
            height: 100%;
        }}
        
        .sidebar {{
            width: 300px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 20px rgba(0,0,0,0.1);
            padding: 1.5rem;
            overflow-y: auto;
        }}
        
        .sidebar h2 {{
            font-size: 1.2rem;
            margin-bottom: 1rem;
            color: #333;
        }}
        
        .controls {{
            margin-bottom: 1.5rem;
        }}
        
        .control-group {{
            margin-bottom: 1rem;
        }}
        
        .control-group label {{
            display: block;
            font-size: 0.85rem;
            color: #666;
            margin-bottom: 0.5rem;
            font-weight: 500;
        }}
        
        .control-group select,
        .control-group input {{
            width: 100%;
            padding: 0.5rem;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 0.9rem;
        }}
        
        .node-info {{
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 8px;
            margin-top: 1rem;
        }}
        
        .node-info h3 {{
            font-size: 1rem;
            margin-bottom: 0.5rem;
            color: #333;
        }}
        
        .node-info p {{
            font-size: 0.85rem;
            color: #666;
            line-height: 1.5;
        }}
        
        .loading {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            text-align: center;
            color: #666;
        }}
        
        .loading::after {{
            content: '';
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-left: 10px;
        }}
        
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>KARMA Knowledge Graph</h1>
        <div class="subtitle" id="software-name">Loading...</div>
        <div class="stats" id="stats">
            <!-- Stats will be populated by JavaScript -->
        </div>
    </div>
    
    <div class="container">
        <div class="graph-container">
            <div id="graph"></div>
            <div class="loading" id="loading">Loading graph...</div>
        </div>
        
        <div class="sidebar">
            <div class="controls">
                <div class="control-group">
                    <label>Filter by Relation Type</label>
                    <select id="relation-filter">
                        <option value="all">All Relations</option>
                    </select>
                </div>
                <div class="control-group">
                    <label>Filter by Entity Type</label>
                    <select id="entity-filter">
                        <option value="all">All Entities</option>
                    </select>
                </div>
                <div class="control-group">
                    <label>Layout Algorithm</label>
                    <select id="layout-algorithm">
                        <option value="hierarchical">Hierarchical</option>
                        <option value="force">Force-Directed</option>
                        <option value="circular">Circular</option>
                    </select>
                </div>
            </div>
            
            <div class="node-info" id="node-info" style="display: none;">
                <h3 id="node-title">Node Information</h3>
                <p id="node-details"></p>
            </div>
        </div>
    </div>
    
    <script>
        let network = null;
        let allNodes = [];
        let allEdges = [];
        let kgData = null;
        
        // Load knowledge graph data
        fetch('/api/kg')
            .then(response => response.json())
            .then(data => {{
                kgData = data;
                initializeVisualization(data);
            }})
            .catch(error => {{
                console.error('Error loading knowledge graph:', error);
                document.getElementById('loading').textContent = 'Error loading graph';
            }});
        
        function initializeVisualization(data) {{
            // Update header
            document.getElementById('software-name').textContent = data.software || 'Unknown Software';
            
            const stats = data.statistics || {{}};
            const statsHtml = `
                <div class="stat-card">
                    <div class="label">Entities</div>
                    <div class="value">${{stats.total_entities || 0}}</div>
                </div>
                <div class="stat-card">
                    <div class="label">Procedures</div>
                    <div class="value">${{stats.total_procedures || 0}}</div>
                </div>
                <div class="stat-card">
                    <div class="label">Triples</div>
                    <div class="value">${{stats.total_triples || 0}}</div>
                </div>
            `;
            document.getElementById('stats').innerHTML = statsHtml;
            
            // Build nodes and edges
            const nodeMap = new Map();
            const edgeSet = new Set();
            
            // Create nodes from entities
            (data.entities || []).forEach((entity, index) => {{
                const nodeId = entity.entity_id || `entity_${{index}}`;
                nodeMap.set(nodeId, {{
                    id: nodeId,
                    label: entity.name || nodeId,
                    type: entity.entity_type || 'Unknown',
                    description: entity.description || '',
                    group: entity.entity_type || 'Unknown'
                }});
            }});
            
            // Create edges from triples
            (data.triples || []).forEach((triple, index) => {{
                const headId = findNodeId(triple.head, nodeMap);
                const tailId = findNodeId(triple.tail, nodeMap);
                
                if (headId && tailId) {{
                    const edgeKey = `${{headId}}-${{triple.relation}}-${{tailId}}`;
                    if (!edgeSet.has(edgeKey)) {{
                        edgeSet.add(edgeKey);
                        allEdges.push({{
                            id: `edge_${{index}}`,
                            from: headId,
                            to: tailId,
                            label: triple.relation,
                            arrows: 'to',
                            color: getRelationColor(triple.relation)
                        }});
                    }}
                }}
            }});
            
            allNodes = Array.from(nodeMap.values());
            
            // Populate filters
            populateFilters(data);
            
            // Create network
            createNetwork(allNodes, allEdges);
            
            document.getElementById('loading').style.display = 'none';
        }}
        
        function findNodeId(name, nodeMap) {{
            for (const [id, node] of nodeMap.entries()) {{
                if (node.label === name) {{
                    return id;
                }}
            }}
            // Create node if not found
            const newId = `node_${{nodeMap.size}}`;
            nodeMap.set(newId, {{
                id: newId,
                label: name,
                type: 'Unknown',
                description: '',
                group: 'Unknown'
            }});
            return newId;
        }}
        
        function getRelationColor(relation) {{
            const colors = {{
                'located_in': '#FF6B6B',
                'part_of': '#4ECDC4',
                'used_for': '#45B7D1',
                'enables': '#96CEB4',
                'requires': '#FFEAA7',
                'precedes': '#DDA0DD',
                'default': '#95A5A6'
            }};
            return colors[relation] || colors.default;
        }}
        
        function populateFilters(data) {{
            // Populate relation filter
            const relationSet = new Set();
            (data.triples || []).forEach(triple => {{
                relationSet.add(triple.relation);
            }});
            
            const relationFilter = document.getElementById('relation-filter');
            Array.from(relationSet).sort().forEach(rel => {{
                const option = document.createElement('option');
                option.value = rel;
                option.textContent = rel;
                relationFilter.appendChild(option);
            }});
            
            // Populate entity type filter
            const entityTypeSet = new Set();
            (data.entities || []).forEach(entity => {{
                entityTypeSet.add(entity.entity_type);
            }});
            
            const entityFilter = document.getElementById('entity-filter');
            Array.from(entityTypeSet).sort().forEach(type => {{
                const option = document.createElement('option');
                option.value = type;
                option.textContent = type;
                entityFilter.appendChild(option);
            }});
        }}
        
        function createNetwork(nodes, edges) {{
            const container = document.getElementById('graph');
            
            const data = {{
                nodes: new vis.DataSet(nodes.map(node => ({{
                    id: node.id,
                    label: node.label,
                    group: node.group,
                    title: `${{node.label}}\\nType: ${{node.type}}\\n${{node.description}}`,
                    shape: 'box',
                    font: {{ size: 12 }},
                    margin: 10
                }}))),
                edges: new vis.DataSet(edges)
            }};
            
            const options = {{
                nodes: {{
                    shape: 'box',
                    font: {{ size: 12 }},
                    borderWidth: 2,
                    shadow: true
                }},
                edges: {{
                    arrows: {{ to: {{ enabled: true, scaleFactor: 0.8 }} }},
                    font: {{ size: 10, align: 'middle' }},
                    smooth: {{ type: 'continuous' }},
                    width: 2
                }},
                physics: {{
                    enabled: true,
                    stabilization: {{ iterations: 200 }}
                }},
                interaction: {{
                    hover: true,
                    tooltipDelay: 100,
                    zoomView: true,
                    dragView: true
                }},
                layout: {{
                    hierarchical: {{
                        enabled: false,
                        direction: 'UD',
                        sortMethod: 'directed'
                    }}
                }}
            }};
            
            network = new vis.Network(container, data, options);
            
            // Handle node selection
            network.on('click', function(params) {{
                if (params.nodes.length > 0) {{
                    const nodeId = params.nodes[0];
                    const node = nodes.find(n => n.id === nodeId);
                    if (node) {{
                        showNodeInfo(node);
                    }}
                }} else {{
                    hideNodeInfo();
                }}
            }});
            
            // Update layout when algorithm changes
            document.getElementById('layout-algorithm').addEventListener('change', function(e) {{
                const algorithm = e.target.value;
                if (algorithm === 'hierarchical') {{
                    options.layout.hierarchical.enabled = true;
                }} else {{
                    options.layout.hierarchical.enabled = false;
                }}
                network.setOptions(options);
            }});
            
            // Filter functionality
            document.getElementById('relation-filter').addEventListener('change', applyFilters);
            document.getElementById('entity-filter').addEventListener('change', applyFilters);
        }}
        
        function applyFilters() {{
            const relationFilter = document.getElementById('relation-filter').value;
            const entityFilter = document.getElementById('entity-filter').value;
            
            let filteredNodes = allNodes;
            let filteredEdges = allEdges;
            
            if (entityFilter !== 'all') {{
                filteredNodes = allNodes.filter(node => node.type === entityFilter);
                const nodeIds = new Set(filteredNodes.map(n => n.id));
                filteredEdges = allEdges.filter(edge => 
                    nodeIds.has(edge.from) && nodeIds.has(edge.to)
                );
            }}
            
            if (relationFilter !== 'all') {{
                filteredEdges = filteredEdges.filter(edge => edge.label === relationFilter);
                const nodeIds = new Set();
                filteredEdges.forEach(edge => {{
                    nodeIds.add(edge.from);
                    nodeIds.add(edge.to);
                }});
                filteredNodes = filteredNodes.filter(node => nodeIds.has(node.id));
            }}
            
            network.setData({{
                nodes: new vis.DataSet(filteredNodes.map(node => ({{
                    id: node.id,
                    label: node.label,
                    group: node.group,
                    title: `${{node.label}}\\nType: ${{node.type}}\\n${{node.description}}`,
                    shape: 'box',
                    font: {{ size: 12 }},
                    margin: 10
                }}))),
                edges: new vis.DataSet(filteredEdges)
            }});
        }}
        
        function showNodeInfo(node) {{
            document.getElementById('node-title').textContent = node.label;
            document.getElementById('node-details').innerHTML = `
                <strong>Type:</strong> ${{node.type}}<br>
                <strong>Description:</strong> ${{node.description || 'No description available'}}
            `;
            document.getElementById('node-info').style.display = 'block';
        }}
        
        function hideNodeInfo() {{
            document.getElementById('node-info').style.display = 'none';
        }}
    </script>
</body>
</html>"""


def create_handler_class(kg_data):
    """Create a handler class with the knowledge graph data."""
    class Handler(KnowledgeGraphHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, kg_data=kg_data, **kwargs)
    return Handler


def main():
    parser = argparse.ArgumentParser(
        description='Visualize KARMA knowledge graph in a web dashboard'
    )
    parser.add_argument(
        'input',
        help='Path to JSON knowledge graph file'
    )
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=8000,
        help='Port to run the server on (default: 8000)'
    )
    parser.add_argument(
        '--no-browser',
        action='store_true',
        help='Do not automatically open browser'
    )
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"Error: File not found: {args.input}")
        return
    
    print(f"Loading knowledge graph from: {args.input}")
    with open(args.input, 'r', encoding='utf-8') as f:
        kg_data = json.load(f)
    
    software = kg_data.get("software", "Unknown")
    stats = kg_data.get("statistics", {})
    print(f"\nKnowledge Graph: {software}")
    print(f"  - Entities: {stats.get('total_entities', 0)}")
    print(f"  - Procedures: {stats.get('total_procedures', 0)}")
    print(f"  - Triples: {stats.get('total_triples', 0)}")
    
    # Create handler with knowledge graph data
    Handler = create_handler_class(kg_data)
    
    server_address = ('', args.port)
    httpd = HTTPServer(server_address, Handler)
    
    url = f"http://localhost:{args.port}"
    print(f"\n✓ Server started at {url}")
    print("  Press Ctrl+C to stop the server\n")
    
    # Open browser after a short delay
    if not args.no_browser:
        def open_browser():
            time.sleep(1)
            webbrowser.open(url)
        threading.Thread(target=open_browser, daemon=True).start()
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        httpd.shutdown()


if __name__ == "__main__":
    main()
