# Simplified Knowledge Graph Pipeline
## Easy-to-Build Version for Testing Automation Platforms

---

## Overview

This is a **simplified 3-stage pipeline** that extracts basic knowledge from software documentation and creates a simple knowledge graph. Perfect for testing and comparing automation platforms like n8n, Zapier, Make, etc.

**What it does:**
- Takes a text document about software
- Extracts key entities (features, UI elements, concepts)
- Extracts relationships between entities
- Outputs a simple knowledge graph JSON

**Complexity:** ⭐⭐ (Beginner-friendly)
**Build time:** 30-60 minutes per platform
**Cost per run:** ~$0.05-0.15

---

## Simplified Pipeline Flow

```
INPUT (Text)
    ↓
[1] Extract Entities (Single AI Call)
    ↓
[2] Extract Relationships (Single AI Call)
    ↓
[3] Format Output (Simple JSON)
    ↓
OUTPUT (Knowledge Graph)
```

**That's it!** Just 3 stages instead of 10.

---

## Data Structures (Simplified)

### Entity
```json
{
  "name": "string",
  "type": "string (Feature, UIElement, or Concept)",
  "description": "string"
}
```

### Relationship (Triple)
```json
{
  "from": "string (entity name)",
  "relationship": "string (located_in, requires, enables, etc.)",
  "to": "string (entity name)"
}
```

### Knowledge Graph Output
```json
{
  "software": "string",
  "entities": [
    {"name": "Brush Tool", "type": "UIElement", "description": "Tool for painting"},
    {"name": "Layers", "type": "Feature", "description": "Organize content in layers"}
  ],
  "relationships": [
    {"from": "Brush Tool", "relationship": "located_in", "to": "Toolbar"},
    {"from": "Layers", "relationship": "enables", "to": "Non-destructive editing"}
  ]
}
```

---

## Stage 1: Extract Entities

**Node Type:** AI/LLM API call (OpenAI, Claude, etc.)

**Purpose:** Extract all important entities from the text in one shot

**Prompt:**
```
You are extracting knowledge from software documentation.

Extract all important entities (things) mentioned in this file.

For each entity, identify:
- name: The entity's name
- type: One of [Feature, UIElement, Concept]
  - Feature: A capability (e.g., "Auto-Save", "Spell Check")
  - UIElement: A button, menu, panel, or tool (e.g., "Save button", "Layers panel")
  - Concept: A term users need to understand (e.g., "Layer", "Resolution")
- description: Brief description (1 sentence)

Return ONLY a JSON object in this exact format:
{
  "software": "name of the software (if mentioned, otherwise 'Unknown')",
  "entities": [
    {"name": "...", "type": "...", "description": "..."},
    {"name": "...", "type": "...", "description": "..."}
  ]
}

Example:
Input: "Photoshop's Brush Tool lets you paint. Find it in the Toolbar. Layers help organize your work."
Output:
{
  "software": "Photoshop",
  "entities": [
    {"name": "Brush Tool", "type": "UIElement", "description": "Tool for painting on canvas"},
    {"name": "Toolbar", "type": "UIElement", "description": "Container for tools"},
    {"name": "Layers", "type": "Feature", "description": "Organize and manage content"}
  ]
}

Now extract from the text above. Return only valid JSON, no other text.
```

**Input Variables:**
- `input_text` (string, max 2000 characters for simplicity)

**Output Variables:**
- `software` (string)
- `entities` (array)

**Platform Implementation:**
- **n8n:** HTTP Request node → OpenAI API
- **Zapier:** OpenAI action (built-in)
- **Make:** HTTP module → OpenAI
- **Power Automate:** HTTP action → OpenAI

---

## Stage 2: Extract Relationships

**Node Type:** AI/LLM API call

**Purpose:** Find relationships between the extracted entities

**Prompt:**
```
You are extracting relationships between entities in software documentation.

Here are the entities we found:
{{entity_list}}

And here is the original text:
{{input_text}}

Find relationships between these entities. Only use entities from the list above.

Relationship types:
- located_in: UI element is inside another (e.g., "Button" located_in "Toolbar")
- requires: Needs something first (e.g., "Feature A" requires "Feature B")
- enables: Makes something possible (e.g., "Layers" enables "Non-destructive editing")
- part_of: Component of something (e.g., "Save button" part_of "File menu")

Return ONLY a JSON object:
{
  "relationships": [
    {"from": "entity name", "relationship": "type", "to": "entity name"},
    {"from": "entity name", "relationship": "type", "to": "entity name"}
  ]
}

Example:
Entities: ["Brush Tool", "Toolbar", "Layers"]
Text: "The Brush Tool is in the Toolbar. Layers help organize content."
Output:
{
  "relationships": [
    {"from": "Brush Tool", "relationship": "located_in", "to": "Toolbar"}
  ]
}

Only extract relationships that are clearly stated in the text.
Return only valid JSON, no other text.
```

**Input Variables:**
- `entities` (array from Stage 1, formatted as a simple list)
- `input_text` (original text)

**Output Variables:**
- `relationships` (array)

---

## Stage 3: Format Output

**Node Type:** Code/Function node (or just merge in some platforms)

**Purpose:** Combine entities and relationships into final knowledge graph

**Simple Logic:**
```javascript
// Pseudo-code
function formatKnowledgeGraph(software, entities, relationships) {
  return {
    software: software,
    entity_count: entities.length,
    relationship_count: relationships.length,
    entities: entities,
    relationships: relationships,
    created_at: new Date().toISOString()
  };
}
```

**Output JSON:**
```json
{
  "software": "Photoshop",
  "entity_count": 15,
  "relationship_count": 12,
  "entities": [...],
  "relationships": [...],
  "created_at": "2026-02-03T10:30:00Z"
}
```

**Save Options:**
- **File:** Save as JSON file
- **Google Sheets:** One sheet for entities, one for relationships
- **Airtable:** Two tables (Entities, Relationships)
- **Database:** Simple INSERT statements
- **Webhook:** POST to your API

---

## Complete Example

### Input Text:
```
Photoshop's Brush Tool is located in the Toolbar on the left side. 
To use it, select the tool and adjust the size using the Size slider 
in the Options bar. Layers are a fundamental concept that allow you 
to organize your work non-destructively. Create a new layer by clicking 
the New Layer button in the Layers panel.
```

### Stage 1 Output (Entities):
```json
{
  "software": "Photoshop",
  "entities": [
    {"name": "Brush Tool", "type": "UIElement", "description": "Tool for painting"},
    {"name": "Toolbar", "type": "UIElement", "description": "Container for tools on left side"},
    {"name": "Size slider", "type": "UIElement", "description": "Control for adjusting brush size"},
    {"name": "Options bar", "type": "UIElement", "description": "Bar containing tool options"},
    {"name": "Layers", "type": "Concept", "description": "Fundamental concept for organizing work"},
    {"name": "New Layer button", "type": "UIElement", "description": "Button to create layers"},
    {"name": "Layers panel", "type": "UIElement", "description": "Panel for managing layers"}
  ]
}
```

### Stage 2 Output (Relationships):
```json
{
  "relationships": [
    {"from": "Brush Tool", "relationship": "located_in", "to": "Toolbar"},
    {"from": "Size slider", "relationship": "located_in", "to": "Options bar"},
    {"from": "New Layer button", "relationship": "located_in", "to": "Layers panel"},
    {"from": "Layers", "relationship": "enables", "to": "Non-destructive editing"}
  ]
}
```

### Final Output:
```json
{
  "software": "Photoshop",
  "entity_count": 7,
  "relationship_count": 4,
  "entities": [
    {"name": "Brush Tool", "type": "UIElement", "description": "Tool for painting"},
    {"name": "Toolbar", "type": "UIElement", "description": "Container for tools on left side"},
    {"name": "Size slider", "type": "UIElement", "description": "Control for adjusting brush size"},
    {"name": "Options bar", "type": "UIElement", "description": "Bar containing tool options"},
    {"name": "Layers", "type": "Concept", "description": "Fundamental concept for organizing work"},
    {"name": "New Layer button", "type": "UIElement", "description": "Button to create layers"},
    {"name": "Layers panel", "type": "UIElement", "description": "Panel for managing layers"}
  ],
  "relationships": [
    {"from": "Brush Tool", "relationship": "located_in", "to": "Toolbar"},
    {"from": "Size slider", "relationship": "located_in", "to": "Options bar"},
    {"from": "New Layer button", "relationship": "located_in", "to": "Layers panel"},
    {"from": "Layers", "relationship": "enables", "to": "Non-destructive editing"}
  ],
  "created_at": "2026-02-03T10:30:00Z"
}
```

---

## Platform-Specific Quick Start

### n8n (3 nodes)
1. **Manual Trigger** or **Webhook** - Accepts text input
2. **HTTP Request** - Call OpenAI for Stage 1 (entities)
3. **HTTP Request** - Call OpenAI for Stage 2 (relationships)
4. **Code** - Format and combine results
5. **Write Binary File** - Save JSON output

**Total nodes:** 5

### Zapier (3 steps)
1. **Webhook** - Catch text input
2. **OpenAI** - Extract entities (use prompt from Stage 1)
3. **OpenAI** - Extract relationships (use prompt from Stage 2)
4. **Code by Zapier** - Format output
5. **Google Sheets** or **Webhook** - Save results

**Total steps:** 5

### Make (3 modules)
1. **Webhook** - Receive text
2. **HTTP** - OpenAI API for entities
3. **HTTP** - OpenAI API for relationships
4. **JSON** - Create structure
5. **Google Drive** or **HTTP** - Save output

**Total modules:** 5

### Power Automate (3 actions)
1. **Manual trigger** - Input text
2. **HTTP** - OpenAI for entities
3. **HTTP** - OpenAI for relationships
4. **Compose** - Format JSON
5. **OneDrive** or **SharePoint** - Save file

**Total actions:** 5

---

## Testing Strategy

### Test Document 1 (Simple - 100 words)
```
Photoshop's Brush Tool is in the Toolbar. Use the Size slider to adjust 
brush size. Layers help organize your work. Click the New Layer button 
to create a layer.
```

**Expected:** 4-6 entities, 3-4 relationships

### Test Document 2 (Medium - 200 words)
```
Figma is a collaborative design tool. The Frame tool creates containers 
for your designs. Find it in the Toolbar at the top. Components are 
reusable design elements that enable consistency across your project. 
Create a component by selecting an object and clicking "Create Component" 
in the menu. The Layers panel shows your document structure. Auto Layout 
is a feature that enables responsive design by automatically adjusting 
spacing and sizing.
```

**Expected:** 8-12 entities, 6-10 relationships

### Test Document 3 (Your own)
Use a real 200-300 word excerpt from any software documentation.

---

## Validation Checklist

After building in each platform, check:

- [ ] Pipeline runs without errors
- [ ] Entities extracted (at least 50% of obvious ones)
- [ ] Relationships make logical sense
- [ ] JSON output is valid
- [ ] Can save/export results
- [ ] Total time < 30 seconds
- [ ] Cost < $0.20 per run

---

## Platform Comparison Criteria

Rate each platform (1-5 stars) on:

| Criteria | n8n | Zapier | Make | Power Automate | Other |
|----------|-----|--------|------|----------------|-------|
| **Ease of Setup** | | | | | |
| **Visual Clarity** | | | | | |
| **Debugging Tools** | | | | | |
| **Error Handling** | | | | | |
| **JSON Handling** | | | | | |
| **Cost** | | | | | |
| **Speed** | | | | | |
| **Documentation** | | | | | |
| **Overall** | | | | | |

---

## Cost Estimates

### Per Run (using GPT-3.5-turbo)
- Stage 1 (Entities): ~1,500 input + 500 output = 2,000 tokens = **$0.004**
- Stage 2 (Relationships): ~2,000 input + 300 output = 2,300 tokens = **$0.005**
- **Total: ~$0.01 per document**

### Per Run (using GPT-4)
- Stage 1: 2,000 tokens = **$0.09**
- Stage 2: 2,300 tokens = **$0.11**
- **Total: ~$0.20 per document**

**Recommendation:** Use GPT-3.5-turbo for testing, GPT-4 for production if you need higher quality.

---

## Common Issues & Solutions

### Issue 1: AI returns invalid JSON
**Solution:** Add to prompt: "You must return ONLY valid JSON with no markdown formatting, no explanations, no code blocks."

### Issue 2: Entity list too long for Stage 2
**Solution:** Limit Stage 1 to top 20 entities, or truncate the list

### Issue 3: No relationships found
**Solution:** Make sure you're passing both the entity list AND original text to Stage 2

### Issue 4: Duplicate entities
**Solution:** Add a simple deduplication step in Stage 3 (compare lowercase names)

### Issue 5: Platform timeout
**Solution:** Reduce input text to 1000 characters max, or increase timeout settings

---

## Next Steps After Testing

Once you've built this simple version in 2-3 platforms:

1. **Compare experiences** - Which was easiest? Most intuitive?
2. **Test with real docs** - Try 5-10 real documentation excerpts
3. **Measure quality** - How accurate are the extractions?
4. **Check costs** - What's the actual cost per document?
5. **Evaluate debugging** - Which platform made it easiest to fix issues?

### If you want to expand later:
- Add the **Document Classification** stage (from full version)
- Add **Procedure Extraction** for step-by-step workflows
- Add **Version Resolution** for version-specific knowledge
- Implement **Change Detection** for release notes
- Add **Deduplication** logic
- Store in a real database instead of files

But start with this simple 3-stage version first!

---

## Sample Test Results Template

```
Platform: [n8n / Zapier / Make / etc.]
Date: [Date]
Test Document: [Test 1 / Test 2 / Custom]

Build Time: [X minutes]
Run Time: [X seconds]
Cost: [$X.XX]

Entities Extracted: [X]
Relationships Extracted: [X]

Quality (1-5): [X]
Ease of Use (1-5): [X]
Would Use Again (Yes/No): [X]

Notes:
- [Any observations]
- [Issues encountered]
- [What worked well]
```

---

## Conclusion

This simplified pipeline gives you:
- ✅ **Easy to build** (30-60 min per platform)
- ✅ **Easy to test** (3 test documents provided)
- ✅ **Easy to debug** (only 3 stages)
- ✅ **Low cost** (~$0.01-0.20 per run)
- ✅ **Real knowledge graph output**
- ✅ **Clear comparison criteria**

Perfect for evaluating which automation platform works best for your team before committing to building the full complex pipeline!

Start with this, pick your winner, then expand to the full version if needed.
