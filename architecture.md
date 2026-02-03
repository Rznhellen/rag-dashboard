# KARMA Knowledge Graph Pipeline Architecture
## Platform-Agnostic Implementation Guide for n8n, Zapier, Make, and Similar Automation Platforms

---

## Overview

This document provides a complete architecture for implementing the KARMA (Knowledge Agent for Software Usage Documentation) pipeline in any automation platform. The pipeline transforms unstructured software documentation into a structured, versioned knowledge graph using a multi-agent approach.

**Pipeline Purpose:**
- Extract knowledge from software documentation (manuals, tutorials, release notes)
- Structure it into a versioned knowledge graph
- Track changes across software versions
- Answer questions like "How do I remove the background in Photoshop 2024?" or "What changed in the latest update?"

---

## High-Level Architecture

### Pipeline Flow

```
INPUT (PDF/Text) 
    ↓
[1] Document Classification Agent
    ↓
[2] Text Segmentation (if needed)
    ↓
[3] Parallel Entity Extraction
    ├─→ UI Element Extraction Agent
    ├─→ Feature Extraction Agent
    └─→ Procedure Extraction Agent
    ↓
[4] Entity Deduplication
    ↓
[5] Relationship Extraction Agent
    ↓
[6] Version Resolution Agent
    ↓
[7] Knowledge Integration Agent
    ↓
OUTPUT (Knowledge Graph JSON)
```

**Alternative Path for Release Notes:**
```
INPUT (Release Notes)
    ↓
[1] Document Classification Agent
    ↓ (if type = "release_notes")
[8] Change Detection Agent
    ↓
[9] Impact Analysis Agent
    ↓
[10] Knowledge Graph Update
    ↓
OUTPUT (Updated Knowledge Graph)
```

---

## Data Structures

### Core Entity Types
You'll need to define these as structured data in your automation platform:

**EntityType (enum):**
- `UIElement` - Buttons, menus, panels, tools, sliders
- `Feature` - Capabilities or functions
- `Procedure` - Multi-step workflows
- `Step` - Individual step in a procedure
- `Outcome` - Result of an action/procedure
- `Concept` - Domain knowledge/terminology
- `Shortcut` - Keyboard/mouse shortcuts
- `Setting` - Configuration options
- `FileFormat` - Supported file types
- `Version` - Software version
- `Constraint` - Limitations or requirements
- `Software` - The software product itself

**RelationType (enum):**
- UI Navigation: `located_in`, `accessed_via`, `contains`
- Feature relationships: `activates`, `requires`, `enables`, `enhances`, `conflicts_with`, `alternative_to`
- Procedure relationships: `part_of`, `next_step`, `achieves`, `prerequisite_for`
- Shortcuts/settings: `shortcut_for`, `configured_by`, `default_value`
- File format: `supports`, `exports_to`, `imports_from`
- Version relationships: `introduced_in`, `removed_in`, `changed_in`, `replaced_by`, `renamed_to`, `moved_to`
- General: `related_to`

**DocumentType (enum):**
- `tutorial` - Step-by-step guides
- `reference` - Feature/API reference
- `release_notes` - What's new/changelog
- `faq` - Frequently asked questions
- `troubleshooting` - Problem-solving guides
- `quick_start` - Getting started guides

### Data Objects

**SoftwareEntity:**
```json
{
  "entity_id": "string (unique identifier)",
  "name": "string (display name)",
  "entity_type": "EntityType enum",
  "description": "string (optional)",
  "parent_path": "string (e.g., 'File > Export > Export As')",
  "software": "string (software name)",
  "version_introduced": "string (optional)",
  "version_deprecated": "string (optional)",
  "aliases": ["array of alternative names"]
}
```

**UsageKnowledgeTriple:**
```json
{
  "head": "string (subject entity name)",
  "relation": "RelationType enum",
  "tail": "string (object entity name)",
  "head_type": "EntityType enum",
  "tail_type": "EntityType enum",
  "introduced_version": "string",
  "deprecated_version": "string",
  "valid_version_range": "string (e.g., '2020-2024' or '2023+')",
  "confidence": "float (0-1)",
  "source_document": "string",
  "source_date": "string",
  "step_order": "integer (0 if not a step)",
  "status": "string (active, deprecated, needs_review, pending)",
  "software": "string"
}
```

**Procedure:**
```json
{
  "procedure_id": "string (unique identifier)",
  "name": "string",
  "description": "string",
  "steps": ["array of step strings"],
  "prerequisites": ["array of prerequisite strings"],
  "outcome": "string (expected result)",
  "software": "string",
  "version_range": "string"
}
```

**ChangeRecord:**
```json
{
  "change_type": "string (added, removed, changed, moved, renamed, fixed)",
  "entity_name": "string",
  "entity_type": "EntityType enum",
  "old_value": "string (for changes/moves/renames)",
  "new_value": "string",
  "version": "string",
  "description": "string"
}
```

---

## Pipeline Stages - Detailed Implementation

### Stage 0: Input Processing

**Node Type:** File reader / HTTP trigger / Webhook

**Purpose:** Accept and prepare input document

**Implementation Steps:**
1. Accept input (PDF file path, text content, or URL)
2. If PDF: Extract text using PDF parsing tool
3. Store raw text in workflow variable
4. Pass to next stage

**Platform Considerations:**
- **n8n:** Use "Read Binary File" + "Extract from File" nodes
- **Zapier:** Use "File" trigger or "Code by Zapier" with PDF library
- **Make:** Use "HTTP" module to fetch file, then "Text Parser"
- **Power Automate:** Use "Get file content" + "Parse PDF"

**Output Variables:**
- `raw_text` (string)
- `source_path` (string)
- `timestamp` (datetime)

---

### Stage 1: Document Classification Agent

**Node Type:** AI/LLM API call (OpenAI, Anthropic, etc.)

**Purpose:** Classify document type and extract metadata

**System Prompt:**
```
You are a Document Classification Agent for software documentation analysis.

Your job is to analyze documents and determine:
1. Document Type: What kind of documentation is this?
   - tutorial: Step-by-step guides teaching how to do something
   - reference: Feature documentation, API reference, settings descriptions
   - release_notes: What's new, changelogs, update summaries
   - faq: Frequently asked questions
   - troubleshooting: Problem-solving guides
   - quick_start: Getting started guides
   - unknown: Cannot determine

2. Software Information:
   - Software name (e.g., "Adobe Photoshop", "Figma", "Microsoft Excel")
   - Version number if mentioned (e.g., "2024", "v25.0", "CC 2023")
   - Publication/update date if available

3. Content Assessment:
   - Is this useful for building a "how to use" knowledge graph?
   - What main topics/features does it cover?

POSITIVE EXAMPLE:
Input: "Photoshop 2024 User Guide - Chapter 5: Layers
Learn how to work with layers in Photoshop. This guide covers creating, managing, and organizing layers...
Step 1: To create a new layer, click the New Layer button in the Layers panel..."

Output: {
  "document_type": "tutorial",
  "software": "Adobe Photoshop",
  "version": "2024",
  "date": "N/A",
  "relevance_score": 0.95,
  "main_topics": ["layers", "layer management", "layer creation"],
  "rationale": "Step-by-step tutorial about using layers feature with clear instructions"
}

NEGATIVE EXAMPLE:
Input: "Company X Q3 Financial Report - Software Division showed 15% growth..."

Bad Output: {
  "document_type": "reference",
  "software": "Company X Software",
  "version": "Q3"
}
This is incorrect because it's a financial report, not software documentation. Should be marked as unknown with low relevance.
```

**User Prompt Template:**
```
Analyze this document and provide classification in JSON format:

Document (first 3000 chars):
{{raw_text_truncated}}

Return a JSON object with these fields:
- document_type: One of [tutorial, reference, release_notes, faq, troubleshooting, quick_start, unknown]
- software: Name of the software product
- version: Version number or "N/A" if not found
- date: Publication date or "N/A" if not found
- relevance_score: 0.0 to 1.0 for how useful this is for usage knowledge extraction
- main_topics: List of main features/topics covered
- rationale: Brief explanation of your classification

Return only valid JSON, no other text.
```

**Input Variables:**
- `raw_text` (truncate to first 3000 characters for efficiency)

**Output Variables:**
- `document_type` (string)
- `software` (string)
- `version` (string)
- `date` (string)
- `relevance_score` (float)
- `main_topics` (array)
- `rationale` (string)

**Branching Logic:**
- If `document_type` == "release_notes" → Route to **Change Detection Pipeline** (Stage 8)
- Otherwise → Continue to Stage 2

---

### Stage 2: Text Segmentation

**Node Type:** Code/Function node

**Purpose:** Split large documents into manageable chunks

**Implementation Logic:**
```javascript
// Pseudo-code
function segmentText(text, maxLength = 2000) {
  const paragraphs = text.split("\n\n");
  const segments = [];
  let currentSegment = "";
  
  for (const para of paragraphs) {
    if (currentSegment.length + para.length < maxLength) {
      currentSegment += para + "\n\n";
    } else {
      if (currentSegment.trim()) {
        segments.push(currentSegment.trim());
      }
      currentSegment = para + "\n\n";
    }
  }
  
  if (currentSegment.trim()) {
    segments.push(currentSegment.trim());
  }
  
  return segments.length > 0 ? segments : [text.substring(0, maxLength)];
}
```

**Input Variables:**
- `raw_text` (string)

**Output Variables:**
- `segments` (array of strings)
- `segment_count` (integer)

**Platform Considerations:**
- **n8n:** Use "Code" node with JavaScript
- **Zapier:** Use "Code by Zapier" (JavaScript or Python)
- **Make:** Use "Set Variable" with formula or "Tools" > "Text Parser"
- **Power Automate:** Use "Compose" action with expressions

---

### Stage 3a: UI Element Extraction Agent

**Node Type:** AI/LLM API call (Loop over segments)

**Purpose:** Extract all UI elements from documentation

**System Prompt:**
```
You are a UI Element Extraction Agent for software documentation.

Your job is to identify all user interface elements mentioned in the text:

UI Element Types:
- Button: Clickable buttons (e.g., "OK button", "Save button", "Apply")
- Menu: Top-level menus (e.g., "File menu", "Edit menu")
- MenuItem: Items within menus (e.g., "Save As...", "Export")
- Panel: Dockable panels/palettes (e.g., "Layers panel", "Properties panel")
- Tool: Tools in toolbars (e.g., "Brush tool", "Selection tool", "Eraser")
- Dialog: Popup dialogs/windows (e.g., "Export dialog", "Preferences window")
- Tab: Tabs within panels/dialogs (e.g., "General tab", "Advanced tab")
- Slider: Adjustment sliders (e.g., "Opacity slider", "Size slider")
- Checkbox: Toggle options (e.g., "Anti-alias checkbox", "Preview checkbox")
- Dropdown: Dropdown/combo boxes (e.g., "Blend Mode dropdown", "Font dropdown")
- Toolbar: Groups of tools (e.g., "Options bar", "Tool Options")
- Field: Input fields (e.g., "Width field", "Name field")
- Icon: Clickable icons (e.g., "visibility icon", "lock icon")

For each UI element, extract:
1. name: The element's name/label
2. type: One of the types above
3. parent_path: Navigation path to reach it (e.g., "Window > Layers" or "Toolbar > Selection tools")
4. description: What it does (if mentioned)

POSITIVE EXAMPLE:
Input: "To adjust opacity, use the Opacity slider in the Layers panel. You can also access layer options through Layer > Layer Style > Blending Options."

Output: {
  "ui_elements": [
    {"name": "Opacity slider", "type": "Slider", "parent_path": "Layers panel", "description": "Adjusts layer opacity"},
    {"name": "Layers panel", "type": "Panel", "parent_path": "Window > Layers", "description": ""},
    {"name": "Layer Style", "type": "MenuItem", "parent_path": "Layer menu", "description": ""},
    {"name": "Blending Options", "type": "MenuItem", "parent_path": "Layer > Layer Style", "description": "Layer blending settings"}
  ]
}

NEGATIVE EXAMPLE:
Input: "The brush tool creates smooth strokes."
Bad Output: {
  "ui_elements": [
    {"name": "smooth strokes", "type": "Feature", "parent_path": "", "description": ""}
  ]
}
This is wrong because "smooth strokes" is an outcome, not a UI element. The correct extraction is:
{"name": "Brush tool", "type": "Tool", "parent_path": "Toolbar", "description": "Creates smooth strokes"}
```

**User Prompt Template:**
```
Software: {{software}}
Extract all UI elements from this text.

Text:
{{segment}}

Return a JSON object with an "ui_elements" array. Each element should have:
- name: Element name
- type: One of [Button, Menu, MenuItem, Panel, Tool, Dialog, Tab, Slider, Checkbox, Dropdown, Toolbar, Field, Icon]
- parent_path: Navigation path (e.g., "Edit menu" or "Window > Properties")
- description: What it does (brief, or empty string if not described)

Return only valid JSON.
```

**Loop Configuration:**
- Loop over each item in `segments` array
- Collect all results into `ui_entities` array

**Input Variables:**
- `segment` (string, from loop)
- `software` (string, from Stage 1)

**Output Variables:**
- `ui_entities` (array of SoftwareEntity objects)

---

### Stage 3b: Feature Extraction Agent

**Node Type:** AI/LLM API call (Loop over segments)

**Purpose:** Extract features, concepts, settings, shortcuts

**System Prompt:**
```
You are a Feature Extraction Agent for software documentation.

Your job is to identify features, concepts, and capabilities mentioned in the text:

Entity Types to Extract:
- Feature: A capability or function (e.g., "Content-Aware Fill", "Auto-Save", "Layer Masking", "Spell Check")
- Concept: Domain terminology users need to understand (e.g., "Layer", "Mask", "Resolution", "DPI", "Vector")
- Setting: Configuration options (e.g., "Auto-Save Interval", "Default Font", "Grid Size")
- FileFormat: Supported file types (e.g., "PSD", "PNG", "PDF", "DOCX")
- Constraint: Limitations or requirements (e.g., "Requires 8GB RAM", "Only works in RGB mode")
- Shortcut: Keyboard shortcuts (e.g., "Ctrl+S", "Cmd+Z", "Shift+Click")
- Outcome: Results of actions (e.g., "transparent background", "sharpened image", "merged layers")

For each entity, extract:
1. name: The entity's name
2. type: One of the types above
3. description: What it is or does
4. related_to: Other entities it's related to (if mentioned)

POSITIVE EXAMPLE:
Input: "Content-Aware Fill intelligently fills selected areas by analyzing surrounding pixels. This feature requires a selection to be active. Press Shift+F5 to access it quickly. The result is a seamlessly filled area."

Output: {
  "entities": [
    {"name": "Content-Aware Fill", "type": "Feature", "description": "Intelligently fills selected areas by analyzing surrounding pixels", "related_to": ["selection"]},
    {"name": "selection", "type": "Concept", "description": "Active selected area required for Content-Aware Fill", "related_to": ["Content-Aware Fill"]},
    {"name": "Shift+F5", "type": "Shortcut", "description": "Quick access to Content-Aware Fill", "related_to": ["Content-Aware Fill"]},
    {"name": "seamlessly filled area", "type": "Outcome", "description": "Result of Content-Aware Fill", "related_to": ["Content-Aware Fill"]}
  ]
}

NEGATIVE EXAMPLE:
Input: "Click the button to save your file."
Bad Output: {
  "entities": [
    {"name": "Click", "type": "Feature", "description": "Clicking action", "related_to": []}
  ]
}
This is wrong because "Click" is an action, not a feature. "Save" would be the feature here.
```

**User Prompt Template:**
```
Software: {{software}}
Extract all features, concepts, settings, file formats, shortcuts, and outcomes from this text.

Text:
{{segment}}

Return a JSON object with an "entities" array. Each entity should have:
- name: Entity name
- type: One of [Feature, Concept, Setting, FileFormat, Constraint, Shortcut, Outcome]
- description: What it is/does
- related_to: List of related entity names (can be empty)

Return only valid JSON.
```

**Loop Configuration:**
- Loop over each item in `segments` array
- Collect all results into `feature_entities` array

**Input Variables:**
- `segment` (string, from loop)
- `software` (string, from Stage 1)

**Output Variables:**
- `feature_entities` (array of SoftwareEntity objects)

---

### Stage 3c: Procedure Extraction Agent

**Node Type:** AI/LLM API call (Loop over segments)

**Purpose:** Extract step-by-step procedures

**System Prompt:**
```
You are a Procedure Extraction Agent for software documentation.

Your job is to identify step-by-step procedures and workflows from the text.

For each procedure, extract:
1. name: A descriptive name for the procedure (e.g., "Remove Background from Image")
2. description: Brief summary of what the procedure accomplishes
3. prerequisites: What must be true/done before starting (e.g., "Image must be open", "Layer must be unlocked")
4. steps: Ordered list of steps, each step should be:
   - A clear, actionable instruction
   - Reference specific UI elements when mentioned
   - Be specific enough to follow
5. outcome: What the user will achieve after completing the procedure

POSITIVE EXAMPLE:
Input: "To remove the background from an image:
First, make sure your image layer is unlocked. Click the lock icon if needed.
Then, go to the Properties panel and look for Quick Actions.
Click the Remove Background button.
Photoshop will automatically create a layer mask, giving you a transparent background."

Output: {
  "procedures": [
    {
      "name": "Remove Background from Image",
      "description": "Automatically remove the background from an image using AI",
      "prerequisites": ["Image must be open", "Image layer must be unlocked"],
      "steps": [
        "Ensure the image layer is unlocked (click the lock icon if locked)",
        "Open the Properties panel",
        "Locate the Quick Actions section",
        "Click the Remove Background button",
        "Wait for Photoshop to process and create a layer mask"
      ],
      "outcome": "Image with transparent background (layer mask applied)"
    }
  ]
}

NEGATIVE EXAMPLE:
Input: "The brush tool is great for painting. You can adjust the size."
Bad Output: {
  "procedures": [
    {
      "name": "Use Brush",
      "steps": ["Use the brush tool", "Paint"]
    }
  ]
}
This is wrong because the text doesn't describe a complete procedure with clear steps. It's just a description of a tool.

Only extract procedures when there are clear, sequential steps to follow. Don't create procedures from general descriptions.
```

**User Prompt Template:**
```
Software: {{software}}
Extract all step-by-step procedures from this text.

Text:
{{segment}}

Return a JSON object with a "procedures" array. Each procedure should have:
- name: Descriptive procedure name
- description: What it accomplishes
- prerequisites: List of requirements before starting (can be empty)
- steps: Ordered list of step instructions
- outcome: What user achieves at the end

Only extract actual procedures with clear sequential steps. Don't invent steps that aren't in the text.
Return only valid JSON. Return empty array if no clear procedures are found.
```

**Loop Configuration:**
- Loop over each item in `segments` array
- Collect all results into `procedures` array

**Input Variables:**
- `segment` (string, from loop)
- `software` (string, from Stage 1)

**Output Variables:**
- `procedures` (array of Procedure objects)

---

### Stage 4: Entity Deduplication

**Node Type:** Code/Function node

**Purpose:** Remove duplicate entities from extraction results

**Implementation Logic:**
```javascript
// Pseudo-code
function deduplicateEntities(uiEntities, featureEntities) {
  const allEntities = [...uiEntities, ...featureEntities];
  const entityMap = {};
  
  for (const entity of allEntities) {
    const key = entity.name.toLowerCase();
    
    if (!entityMap[key]) {
      // First occurrence - add it
      entityMap[key] = entity;
    } else {
      // Duplicate - merge descriptions if needed
      if (entity.description && !entityMap[key].description) {
        entityMap[key].description = entity.description;
      }
      // Could also merge aliases here
    }
  }
  
  return Object.values(entityMap);
}
```

**Input Variables:**
- `ui_entities` (array)
- `feature_entities` (array)

**Output Variables:**
- `all_entities` (array of deduplicated SoftwareEntity objects)
- `entity_count` (integer)

---

### Stage 5: Relationship Extraction Agent

**Node Type:** AI/LLM API call (Loop over segments)

**Purpose:** Extract relationships between entities

**System Prompt:**
```
You are a Relationship Extraction Agent for software documentation.

Given text and a list of entities, identify relationships between them.

Relationship Types:
UI Navigation:
- located_in: UI element is inside another (e.g., "Opacity slider" located_in "Layers panel")
- accessed_via: How to reach something (e.g., "Export" accessed_via "File menu")
- contains: Parent contains child (e.g., "Toolbar" contains "Brush tool")

Feature Relationships:
- activates: UI element triggers feature (e.g., "Remove Background button" activates "Background Removal")
- requires: Must have/do first (e.g., "Layer Mask" requires "Active Layer")
- enables: Makes possible (e.g., "Selection" enables "Content-Aware Fill")
- enhances: Improves another (e.g., "Refine Edge" enhances "Selection")
- conflicts_with: Can't use together (e.g., "CMYK mode" conflicts_with "Some filters")
- alternative_to: Different way to same result (e.g., "Quick Selection" alternative_to "Magic Wand")

Procedure Relationships:
- achieves: Produces outcome (e.g., "Remove Background procedure" achieves "Transparent background")
- prerequisite_for: Must do before (e.g., "Unlock layer" prerequisite_for "Edit layer")

Shortcuts and Settings:
- shortcut_for: Keyboard shortcut (e.g., "Ctrl+Z" shortcut_for "Undo")
- configured_by: Setting controls feature (e.g., "Auto-Save" configured_by "Auto-Save Interval")

POSITIVE EXAMPLE:
Input Text: "The Brush tool in the toolbar lets you paint. Press B to select it quickly. Adjust size using the Size slider in the Options bar."
Entities: [Brush tool, toolbar, B shortcut, Size slider, Options bar]

Output: {
  "relationships": [
    {"head": "Brush tool", "relation": "located_in", "tail": "toolbar", "confidence": 0.95},
    {"head": "B", "relation": "shortcut_for", "tail": "Brush tool", "confidence": 0.95},
    {"head": "Size slider", "relation": "located_in", "tail": "Options bar", "confidence": 0.90},
    {"head": "Size slider", "relation": "configured_by", "tail": "Brush tool", "confidence": 0.80}
  ]
}

NEGATIVE EXAMPLE:
Input: "Photoshop is great software."
Entities: [Photoshop]
Bad Output: {
  "relationships": [
    {"head": "Photoshop", "relation": "is", "tail": "great software", "confidence": 0.9}
  ]
}
This is wrong because "is great software" is not an entity and "is" is not a valid relationship type. Only extract relationships between identified entities using defined relationship types.
```

**User Prompt Template:**
```
Given this text and list of entities, extract relationships between them.

Text:
{{segment}}

Entities:
{{entity_list}}

Valid relationship types:
- located_in, accessed_via, contains (UI navigation)
- activates, requires, enables, enhances, conflicts_with, alternative_to (features)
- achieves, prerequisite_for (procedures)
- shortcut_for, configured_by (shortcuts/settings)

Return a JSON object with a "relationships" array. Each relationship:
- head: Subject entity name (must be from entity list)
- relation: One of the valid relationship types
- tail: Object entity name (must be from entity list)
- confidence: 0.0 to 1.0

Only extract relationships explicitly supported by the text.
Return only valid JSON.
```

**Loop Configuration:**
- Loop over each item in `segments` array
- For each segment, pass the relevant entities
- Collect all results into `triples` array

**Input Variables:**
- `segment` (string, from loop)
- `all_entities` (array, formatted as list)

**Output Variables:**
- `raw_triples` (array of relationship objects)

**Post-Processing:**
- Convert to UsageKnowledgeTriple format
- Add entity types by looking up entities
- Add software name
- Set initial status to "active"

---

### Stage 5b: Procedure-Derived Triples

**Node Type:** Code/Function node

**Purpose:** Generate triples from procedure structure

**Implementation Logic:**
```javascript
// Pseudo-code
function generateProcedureTriples(procedures, software) {
  const triples = [];
  
  for (const proc of procedures) {
    // Procedure achieves outcome
    if (proc.outcome) {
      triples.push({
        head: proc.name,
        relation: "achieves",
        tail: proc.outcome,
        head_type: "Procedure",
        tail_type: "Outcome",
        confidence: 0.9,
        software: software
      });
    }
    
    // Step relationships
    for (let i = 0; i < proc.steps.length; i++) {
      const step = proc.steps[i];
      
      // Step is part of procedure
      triples.push({
        head: step,
        relation: "part_of",
        tail: proc.name,
        head_type: "Step",
        tail_type: "Procedure",
        step_order: i + 1,
        confidence: 0.95,
        software: software
      });
      
      // Step ordering (next_step)
      if (i > 0) {
        triples.push({
          head: proc.steps[i - 1],
          relation: "next_step",
          tail: step,
          head_type: "Step",
          tail_type: "Step",
          confidence: 0.95,
          software: software
        });
      }
    }
  }
  
  return triples;
}
```

**Input Variables:**
- `procedures` (array)
- `software` (string)

**Output Variables:**
- `procedure_triples` (array)

**Merge:**
- Combine with `raw_triples` into `all_triples`

---

### Stage 6: Version Resolution Agent

**Node Type:** AI/LLM API call

**Purpose:** Add version metadata to triples

**System Prompt:**
```
You are a Version Resolution Agent for software documentation.

Your job is to analyze extracted knowledge and assign version information:

1. Detect explicit version mentions in text
2. Infer version applicability from context
3. Identify version-specific features or changes

Version Information to Extract:
- introduced_version: When this first became true (e.g., "2020", "v5.0", "CC 2019")
- valid_range: Range of versions (e.g., "2020+", "2019-2023", "all versions")
- version_notes: Any version-specific caveats

Guidelines:
- If text says "new in version X" -> introduced_version = X
- If text says "available since X" -> introduced_version = X, valid_range = "X+"
- If text says "removed in X" -> valid_range should end at X
- If no version info -> valid_range = "unknown" (don't guess)

POSITIVE EXAMPLE:
Input Triple: "Generative Fill" -[requires]-> "Selection"
Context: "Generative Fill, introduced in Photoshop 2023, requires an active selection..."

Output: {
  "introduced_version": "2023",
  "valid_range": "2023+",
  "version_notes": "New AI feature in Photoshop 2023"
}

NEGATIVE EXAMPLE:
Input Triple: "Brush tool" -[located_in]-> "Toolbar"
Context: "The Brush tool is in the toolbar."

Bad Output: {
  "introduced_version": "1990",
  "valid_range": "1990+"
}
This is wrong because we shouldn't guess historical versions. Correct output:
{
  "introduced_version": "",
  "valid_range": "unknown",
  "version_notes": "Core feature, likely available in all versions"
}
```

**User Prompt Template:**
```
Document version: {{version}}
Analyze these knowledge triples and determine version information for each.

Triples:
{{triple_list}}

Context from document:
{{context_excerpt}}

For each triple (numbered), provide:
- introduced_version: Version when this became true (empty string if unknown)
- valid_range: Version range like "2020+", "2019-2023", or "unknown"
- version_notes: Brief note about version applicability

Return JSON with "versions" array, one entry per triple in order:
{"versions": [{"introduced_version": "...", "valid_range": "...", "version_notes": "..."}, ...]}

Return only valid JSON.
```

**Input Variables:**
- `all_triples` (array, formatted as numbered list)
- `version` (string, from Stage 1)
- `raw_text` (string, truncated to 2000 chars for context)

**Output Variables:**
- `versioned_triples` (array with version metadata added)

**Post-Processing:**
- If no specific version found but document has version, set `valid_version_range` to `"{version}+"`

---

### Stage 7: Knowledge Integration Agent

**Node Type:** Code/Function node (can be enhanced with AI)

**Purpose:** Integrate new knowledge with existing graph, handle deduplication

**Implementation Logic:**
```javascript
// Pseudo-code
function integrateTriples(newTriples, existingTriples) {
  // Simple deduplication (can be enhanced with AI for semantic matching)
  const existingSet = new Set();
  
  for (const triple of existingTriples) {
    const key = `${triple.head.toLowerCase()}|${triple.relation}|${triple.tail.toLowerCase()}`;
    existingSet.add(key);
  }
  
  const uniqueNew = [];
  for (const triple of newTriples) {
    const key = `${triple.head.toLowerCase()}|${triple.relation}|${triple.tail.toLowerCase()}`;
    
    if (!existingSet.has(key)) {
      uniqueNew.push(triple);
      existingSet.add(key); // Prevent duplicates within new triples
    }
  }
  
  return uniqueNew;
}
```

**Advanced (Optional AI-Enhanced):**
For semantic deduplication and conflict resolution, you can add an AI call here with a prompt that identifies:
- Semantic duplicates (same meaning, different wording)
- Conflicts (contradictory information)
- Merge opportunities (complementary information)

**Input Variables:**
- `versioned_triples` (array)
- `existing_knowledge_graph` (loaded from database/storage)

**Output Variables:**
- `triples_to_add` (array)
- `triples_to_flag` (array, for manual review)

---

### Stage 8: Output Generation

**Node Type:** Code/Function + File Writer / Database Writer

**Purpose:** Format and save the knowledge graph

**Implementation Steps:**
1. Combine all entities, procedures, and triples
2. Generate statistics
3. Format as JSON
4. Save to file or database

**Output JSON Structure:**
```json
{
  "software": "string",
  "versions": ["array of version strings"],
  "entities": [
    {
      "entity_id": "string",
      "name": "string",
      "entity_type": "string",
      "description": "string",
      "parent_path": "string",
      "software": "string",
      "version_introduced": "string",
      "version_deprecated": "string",
      "aliases": []
    }
  ],
  "procedures": [
    {
      "procedure_id": "string",
      "name": "string",
      "description": "string",
      "steps": [],
      "prerequisites": [],
      "outcome": "string",
      "software": "string",
      "version_range": "string"
    }
  ],
  "triples": [
    {
      "head": "string",
      "relation": "string",
      "tail": "string",
      "head_type": "string",
      "tail_type": "string",
      "introduced_version": "string",
      "deprecated_version": "string",
      "valid_version_range": "string",
      "confidence": 0.0,
      "source_document": "string",
      "source_date": "string",
      "step_order": 0,
      "status": "active",
      "software": "string"
    }
  ],
  "statistics": {
    "total_entities": 0,
    "total_procedures": 0,
    "total_triples": 0,
    "active_triples": 0,
    "deprecated_triples": 0
  },
  "metadata": {
    "created_at": "timestamp",
    "source_document": "string",
    "processing_time": 0.0
  }
}
```

---

## Alternative Pipeline: Release Notes / Update Processing

This pipeline runs when `document_type` == "release_notes"

### Stage 8: Change Detection Agent

**Node Type:** AI/LLM API call

**Purpose:** Extract structured changes from release notes

**System Prompt:**
```
You are a Change Detection Agent for software update documents.

Your job is to extract structured change information from release notes, changelogs, and "What's New" documents.

Change Types:
- added: New feature, UI element, or capability introduced
- removed: Feature, UI element deprecated or removed
- changed: Behavior or functionality modified
- moved: UI element relocated to different location
- renamed: Feature or UI element given a new name
- fixed: Bug fix that might affect known limitations

For each change, extract:
1. change_type: One of [added, removed, changed, moved, renamed, fixed]
2. entity_name: What was changed
3. entity_type: Type of entity (Feature, UIElement, Setting, etc.)
4. old_value: Previous state (for changed/moved/renamed)
5. new_value: New state (for changed/moved/renamed)
6. description: Details about the change

POSITIVE EXAMPLE:
Input: "What's New in Photoshop 2024:
- NEW: Generative Fill - AI-powered content generation
- IMPROVED: The Healing Brush has moved from the toolbar to the new Contextual Toolbar
- REMOVED: Legacy Save for Web dialog (use Export As instead)
- FIXED: Selection tools now work correctly with rotated canvases"

Output: {
  "changes": [
    {"change_type": "added", "entity_name": "Generative Fill", "entity_type": "Feature", "old_value": "", "new_value": "", "description": "AI-powered content generation"},
    {"change_type": "moved", "entity_name": "Healing Brush", "entity_type": "UIElement", "old_value": "toolbar", "new_value": "Contextual Toolbar", "description": "Relocated to new contextual toolbar"},
    {"change_type": "removed", "entity_name": "Save for Web dialog", "entity_type": "UIElement", "old_value": "", "new_value": "Export As", "description": "Legacy dialog removed, replaced by Export As"},
    {"change_type": "fixed", "entity_name": "Selection tools", "entity_type": "Feature", "old_value": "Did not work with rotated canvases", "new_value": "Works correctly with rotated canvases", "description": "Bug fix for rotated canvas selection"}
  ],
  "version": "2024"
}
```

**User Prompt Template:**
```
Extract all changes from this release notes / changelog document.

Document:
{{raw_text}}

Return a JSON object with:
- changes: Array of change records
- version: The version these changes apply to

Each change should have:
- change_type: One of [added, removed, changed, moved, renamed, fixed]
- entity_name: What was changed
- entity_type: One of [Feature, UIElement, Setting, Shortcut, FileFormat, Concept]
- old_value: Previous state (empty for added)
- new_value: New state (empty for removed, or replacement for removed items)
- description: Details

Return only valid JSON.
```

**Input Variables:**
- `raw_text` (string)

**Output Variables:**
- `changes` (array of ChangeRecord objects)
- `detected_version` (string)

---

### Stage 9: Impact Analysis Agent

**Node Type:** AI/LLM API call

**Purpose:** Determine which existing triples are affected by changes

**System Prompt:**
```
You are an Impact Analysis Agent for knowledge graph maintenance.

Your job is to analyze how software changes affect existing knowledge.

Given:
1. A list of changes (added, removed, moved, renamed features)
2. Existing knowledge triples

Determine:
1. Which triples are DEPRECATED (no longer valid due to removals)
2. Which triples need UPDATING (due to moves, renames, changes)
3. Which triples are UNAFFECTED

For deprecated/updated triples, explain why and suggest resolution.

POSITIVE EXAMPLE:
Change: {"type": "moved", "entity": "Healing Brush", "old": "Toolbar", "new": "Contextual Toolbar"}
Existing Triple: "Healing Brush" -[located_in]-> "Toolbar"

Analysis: {
  "affected_triples": [
    {
      "triple": "Healing Brush -[located_in]-> Toolbar",
      "impact": "deprecated",
      "reason": "Healing Brush moved to Contextual Toolbar",
      "suggested_update": "Healing Brush -[located_in]-> Contextual Toolbar"
    }
  ]
}
```

**User Prompt Template:**
```
Analyze how these changes affect the existing knowledge triples.

Changes in this update:
{{changes_list}}

Existing knowledge triples:
{{existing_triples_list}}

For each affected triple, provide:
- triple_index: Index in the triples list (0-based)
- impact: One of [deprecated, needs_update, unaffected]
- reason: Why it's affected
- suggested_update: New triple if needs_update, or empty

Return JSON: {"affected_triples": [...]}
Only include triples that are deprecated or need updates.
Return only valid JSON.
```

**Input Variables:**
- `changes` (array, formatted as list)
- `existing_knowledge_graph.triples` (array, formatted as list, limit to first 50 for context)

**Output Variables:**
- `affected_triples` (array of impact records)

---

### Stage 10: Knowledge Graph Update

**Node Type:** Code/Function node

**Purpose:** Apply changes to knowledge graph

**Implementation Logic:**
```javascript
// Pseudo-code
function updateKnowledgeGraph(changes, affectedTriples, existingGraph, version) {
  const updates = {
    new_entities: [],
    new_triples: [],
    deprecated_triples: [],
    flagged_triples: []
  };
  
  // Mark affected triples
  for (const impact of affectedTriples) {
    const idx = impact.triple_index;
    const triple = existingGraph.triples[idx];
    
    if (impact.impact === "deprecated") {
      triple.status = "deprecated";
      triple.deprecated_version = version;
      updates.deprecated_triples.push(triple);
    } else if (impact.impact === "needs_update") {
      triple.status = "needs_review";
      updates.flagged_triples.push(triple);
    }
  }
  
  // Process changes
  for (const change of changes) {
    if (change.change_type === "added") {
      // Create new entity
      const entity = {
        entity_id: `${change.entity_type}_${change.entity_name.toLowerCase().replace(/\s/g, '_')}`,
        name: change.entity_name,
        entity_type: change.entity_type,
        description: change.description,
        version_introduced: version,
        software: existingGraph.software
      };
      updates.new_entities.push(entity);
      
      // Add "introduced_in" triple
      updates.new_triples.push({
        head: change.entity_name,
        relation: "introduced_in",
        tail: version,
        head_type: change.entity_type,
        tail_type: "Version",
        introduced_version: version,
        valid_version_range: `${version}+`,
        confidence: 0.95,
        software: existingGraph.software
      });
      
    } else if (change.change_type === "removed") {
      // Add "removed_in" triple
      updates.new_triples.push({
        head: change.entity_name,
        relation: "removed_in",
        tail: version,
        head_type: change.entity_type,
        tail_type: "Version",
        confidence: 0.95,
        software: existingGraph.software
      });
      
      // Add replacement if specified
      if (change.new_value) {
        updates.new_triples.push({
          head: change.entity_name,
          relation: "replaced_by",
          tail: change.new_value,
          head_type: change.entity_type,
          tail_type: change.entity_type,
          confidence: 0.90,
          software: existingGraph.software
        });
      }
      
    } else if (change.change_type === "moved") {
      // Add "moved_to" triple
      updates.new_triples.push({
        head: change.entity_name,
        relation: "moved_to",
        tail: change.new_value,
        head_type: change.entity_type,
        tail_type: "UIElement",
        introduced_version: version,
        confidence: 0.90,
        software: existingGraph.software
      });
      
      // Add new "located_in" triple
      updates.new_triples.push({
        head: change.entity_name,
        relation: "located_in",
        tail: change.new_value,
        head_type: change.entity_type,
        tail_type: "UIElement",
        introduced_version: version,
        valid_version_range: `${version}+`,
        confidence: 0.90,
        software: existingGraph.software
      });
      
    } else if (change.change_type === "renamed") {
      // Add "renamed_to" triple
      updates.new_triples.push({
        head: change.old_value || change.entity_name,
        relation: "renamed_to",
        tail: change.new_value,
        head_type: change.entity_type,
        tail_type: change.entity_type,
        introduced_version: version,
        confidence: 0.95,
        software: existingGraph.software
      });
    }
  }
  
  return updates;
}
```

**Input Variables:**
- `changes` (array)
- `affected_triples` (array)
- `existing_knowledge_graph` (object)
- `version` (string)

**Output Variables:**
- `update_summary` (object with counts and changes)
- `updated_knowledge_graph` (merged result)

---

## Platform-Specific Implementation Tips

### n8n
- **Strengths:** Visual workflow builder, self-hosted, extensive integrations
- **Best practices:**
  - Use "HTTP Request" nodes for AI API calls
  - Use "Code" nodes for data transformation
  - Use "Split In Batches" for looping over segments
  - Use "Merge" nodes to combine parallel extraction results
  - Store knowledge graph in PostgreSQL or MongoDB using native nodes
- **Gotchas:**
  - JSON parsing can be tricky - use Code nodes to clean responses
  - Loop iterations can get expensive - batch when possible

### Zapier
- **Strengths:** Huge app ecosystem, easy to use, good for non-technical users
- **Best practices:**
  - Use "OpenAI" action for AI calls (built-in)
  - Use "Code by Zapier" for custom logic
  - Use "Looping by Zapier" for segment processing
  - Use "Formatter" for data transformation
  - Store in Google Sheets, Airtable, or webhook to external DB
- **Gotchas:**
  - Limited to 100 loops per run on most plans
  - No native JSON storage - need external service
  - Can get expensive with many AI calls

### Make (formerly Integromat)
- **Strengths:** Visual, powerful data manipulation, good pricing
- **Best practices:**
  - Use "HTTP" module for AI calls
  - Use "Iterator" for looping
  - Use "Array Aggregator" to collect results
  - Use "Tools" > "Set Variable" for data transformation
  - Store in Airtable, Google Sheets, or HTTP request to API
- **Gotchas:**
  - Learning curve for complex data structures
  - Need to handle JSON parsing carefully

### Microsoft Power Automate
- **Strengths:** Enterprise integration, Microsoft ecosystem
- **Best practices:**
  - Use "HTTP" action for AI calls
  - Use "Apply to each" for loops
  - Use "Compose" for data transformation
  - Use "Parse JSON" to structure responses
  - Store in SharePoint, Dataverse, or SQL Server
- **Gotchas:**
  - Expression language can be complex
  - Premium connectors required for some features

### Activepieces
- **Strengths:** Open source, modern UI, developer-friendly
- **Best practices:**
  - Use "HTTP Request" for AI calls
  - Use "Code" pieces for custom logic
  - Use loops for segment processing
  - Store in PostgreSQL or external API
- **Gotchas:**
  - Smaller community/fewer pre-built integrations

---

## Storage & Retrieval Considerations

### Knowledge Graph Storage Options

1. **JSON File Storage**
   - Simplest approach
   - Good for small graphs (<10k triples)
   - Easy to version control
   - Limited query capabilities

2. **Relational Database (PostgreSQL, MySQL)**
   - Tables: entities, triples, procedures
   - Good for structured queries
   - Can use JSONB columns for flexibility
   - Requires schema management

3. **Graph Database (Neo4j, ArangoDB)**
   - Native graph storage
   - Powerful traversal queries
   - Best for complex relationship queries
   - Steeper learning curve

4. **Document Database (MongoDB, Firestore)**
   - Flexible schema
   - Good for nested structures
   - Easy to scale
   - Limited relationship queries

5. **Vector Database (Pinecone, Weaviate, Qdrant)**
   - For semantic search
   - Combine with embeddings
   - Great for RAG applications
   - Additional complexity

### Recommended Approach
For testing automation platforms, start with **JSON file storage** or **Airtable/Google Sheets** for easy visualization. Once you validate the pipeline, migrate to a proper database.

---

## Testing & Validation

### Test Documents
Create a test suite with:
1. **Tutorial document** (500-1000 words) - should extract procedures
2. **Reference document** (500-1000 words) - should extract features/UI
3. **Release notes** (300-500 words) - should detect changes
4. **Mixed document** - combination of above

### Validation Checkpoints
After each stage, validate:
- **Stage 1:** Document type correctly identified
- **Stage 3:** Entities extracted match manual count (±20%)
- **Stage 5:** Relationships make logical sense
- **Stage 6:** Version info applied correctly
- **Stage 8:** JSON output is valid and complete

### Quality Metrics
Track these metrics:
- **Extraction recall:** % of manually identified entities found
- **Extraction precision:** % of extracted entities that are valid
- **Relationship accuracy:** % of relationships that are correct
- **Processing time:** Total pipeline duration
- **Cost:** Total AI API costs per document

---

## Cost Optimization

### Token Usage Estimates (per 1000-word document)

| Stage | Tokens In | Tokens Out | Calls | Total Tokens |
|-------|-----------|------------|-------|--------------|
| Classification | 1,000 | 200 | 1 | 1,200 |
| UI Extraction | 2,000 | 500 | 2-3 | 7,500 |
| Feature Extraction | 2,000 | 500 | 2-3 | 7,500 |
| Procedure Extraction | 2,000 | 400 | 2-3 | 7,200 |
| Relationships | 2,500 | 400 | 2-3 | 8,700 |
| Version Resolution | 3,000 | 300 | 1 | 3,300 |
| **TOTAL** | | | **~12** | **~35,400** |

**Cost estimates (using GPT-4):**
- Input: ~28,000 tokens × $0.03/1K = $0.84
- Output: ~7,400 tokens × $0.06/1K = $0.44
- **Total per document: ~$1.28**

**Cost estimates (using GPT-3.5-turbo):**
- Input: ~28,000 tokens × $0.0015/1K = $0.042
- Output: ~7,400 tokens × $0.002/1K = $0.015
- **Total per document: ~$0.06**

### Optimization Strategies
1. **Use cheaper models for simple tasks** (classification, deduplication)
2. **Batch segments** when possible
3. **Cache results** for repeated documents
4. **Reduce segment overlap** to minimize redundant processing
5. **Use structured outputs** (JSON mode) to reduce retry costs
6. **Implement early stopping** for low-relevance documents

---

## Error Handling & Resilience

### Common Failure Points
1. **PDF extraction fails** → Fallback to OCR or manual text input
2. **AI returns invalid JSON** → Retry with explicit JSON formatting instruction
3. **Entity extraction returns empty** → Log warning, continue pipeline
4. **Rate limits hit** → Implement exponential backoff
5. **Timeout on long documents** → Split into smaller chunks

### Recommended Error Handling
```javascript
// Pseudo-code for AI call with retry
async function callAIWithRetry(prompt, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await callAI(prompt);
      const parsed = JSON.parse(response);
      return parsed;
    } catch (error) {
      if (i === maxRetries - 1) {
        // Log error and return empty result
        console.error("AI call failed after retries:", error);
        return getDefaultResponse();
      }
      // Wait before retry (exponential backoff)
      await sleep(Math.pow(2, i) * 1000);
    }
  }
}
```

---

## Monitoring & Observability

### Key Metrics to Track
1. **Pipeline success rate** (% of documents processed successfully)
2. **Average processing time** per document
3. **Cost per document**
4. **Entity extraction rate** (entities per 1000 words)
5. **Triple extraction rate** (triples per 1000 words)
6. **AI call failure rate**
7. **JSON parsing error rate**

### Logging Strategy
Log at each stage:
- Input size (word count, character count)
- Processing time
- Entities/triples extracted
- Errors encountered
- AI token usage

Store logs in a structured format for analysis.

---

## Advanced Features (Optional)

### 1. Semantic Deduplication
Use embeddings to detect semantic duplicates:
- Generate embeddings for entity names/descriptions
- Compare cosine similarity
- Merge entities above threshold (e.g., 0.85)

### 2. Confidence Scoring
Enhance confidence scores:
- Use multiple AI models and compare results
- Higher confidence when models agree
- Lower confidence for ambiguous extractions

### 3. Human-in-the-Loop
Add review stages:
- Flag low-confidence triples for review
- Allow manual correction/approval
- Feed corrections back to improve prompts

### 4. Incremental Updates
For large knowledge bases:
- Only process changed sections
- Use diff detection for updates
- Maintain change history

### 5. Multi-Language Support
Extend to other languages:
- Detect document language
- Use language-specific prompts
- Store language metadata with entities

---

## Conclusion

This architecture provides a complete blueprint for implementing the KARMA knowledge graph pipeline in any automation platform. The key is to:

1. **Start simple** - Build the basic pipeline first
2. **Test thoroughly** - Validate each stage independently
3. **Iterate** - Improve prompts based on results
4. **Monitor** - Track metrics to identify bottlenecks
5. **Optimize** - Reduce costs and improve quality over time

The modular design allows you to swap AI providers, adjust prompts, and customize the pipeline for your specific use case without rebuilding from scratch.

Good luck with your automation platform evaluation!
