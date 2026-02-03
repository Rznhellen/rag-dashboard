# karma_pipeline.py
"""
KARMA: Knowledge Agent for Software Usage Documentation

This module implements a pipeline of specialized agents that collaborate to:
1. Extract knowledge from software documentation (manuals, tutorials, release notes)
2. Structure it into a versioned knowledge graph for software usage
3. Track changes across software versions for easy maintenance

Designed to answer questions like:
- "How do I remove the background in Photoshop 2024?"
- "Where is the Export button located?"
- "What changed in the latest update?"

Original biomedical version by: Yuxing Lu
Refactored for software usage by: KARMA Team
"""

import os
import logging
import time
import json
from typing import List, Dict, Tuple, Union, Set, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
import PyPDF2
from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("KARMA")

##############################################################################
# Enums for Type Safety
##############################################################################

class EntityType(str, Enum):
    """Types of entities in a software usage knowledge graph."""
    UI_ELEMENT = "UIElement"        # Buttons, menus, panels, tools, sliders, etc.
    FEATURE = "Feature"             # Capabilities or functions
    PROCEDURE = "Procedure"         # Multi-step workflows
    STEP = "Step"                   # Individual step in a procedure
    OUTCOME = "Outcome"             # Result of an action/procedure
    CONCEPT = "Concept"             # Domain knowledge/terminology
    SHORTCUT = "Shortcut"           # Keyboard/mouse shortcuts
    SETTING = "Setting"             # Configuration options
    FILE_FORMAT = "FileFormat"      # Supported file types
    VERSION = "Version"             # Software version
    CONSTRAINT = "Constraint"       # Limitations or requirements
    SOFTWARE = "Software"           # The software product itself
    UNKNOWN = "Unknown"

class RelationType(str, Enum):
    """Types of relationships in a software usage knowledge graph."""
    # UI Navigation
    LOCATED_IN = "located_in"               # UI hierarchy
    ACCESSED_VIA = "accessed_via"           # How to reach something
    CONTAINS = "contains"                   # Parent contains child

    # Feature relationships
    ACTIVATES = "activates"                 # UI element triggers feature
    REQUIRES = "requires"                   # Dependency/prerequisite
    ENABLES = "enables"                     # Makes something possible
    ENHANCES = "enhances"                   # Improves another feature
    CONFLICTS_WITH = "conflicts_with"       # Incompatible
    ALTERNATIVE_TO = "alternative_to"       # Different way to same result

    # Procedure relationships
    PART_OF = "part_of"                     # Step belongs to procedure
    NEXT_STEP = "next_step"                 # Step ordering
    ACHIEVES = "achieves"                   # Produces outcome
    PREREQUISITE_FOR = "prerequisite_for"   # Must do before

    # Shortcuts and settings
    SHORTCUT_FOR = "shortcut_for"           # Keyboard shortcut mapping
    CONFIGURED_BY = "configured_by"         # Setting controls feature
    DEFAULT_VALUE = "default_value"         # Default setting value

    # File format
    SUPPORTS = "supports"                   # File format compatibility
    EXPORTS_TO = "exports_to"               # Can export as
    IMPORTS_FROM = "imports_from"           # Can import from

    # Version relationships
    INTRODUCED_IN = "introduced_in"         # When first appeared
    REMOVED_IN = "removed_in"               # When removed
    CHANGED_IN = "changed_in"               # When modified
    REPLACED_BY = "replaced_by"             # Successor
    RENAMED_TO = "renamed_to"               # Name change
    MOVED_TO = "moved_to"                   # Location change

    # General
    RELATED_TO = "related_to"               # General relationship

class DocumentType(str, Enum):
    """Types of documentation that can be processed."""
    TUTORIAL = "tutorial"           # Step-by-step guides
    REFERENCE = "reference"         # Feature/API reference
    RELEASE_NOTES = "release_notes" # What's new/changelog
    FAQ = "faq"                     # Frequently asked questions
    TROUBLESHOOTING = "troubleshooting"  # Problem-solving guides
    QUICK_START = "quick_start"     # Getting started guides
    UNKNOWN = "unknown"

class TripleStatus(str, Enum):
    """Status of a knowledge triple."""
    ACTIVE = "active"               # Currently valid
    DEPRECATED = "deprecated"       # No longer valid
    NEEDS_REVIEW = "needs_review"   # Flagged for verification
    PENDING = "pending"             # Not yet verified

##############################################################################
# Data Structures
##############################################################################

@dataclass
class SoftwareEntity:
    """
    Represents an entity in the software usage knowledge graph.

    Attributes:
        entity_id: Unique identifier
        name: Display name
        entity_type: Type of entity (UIElement, Feature, etc.)
        description: Optional description
        parent_path: UI navigation path (e.g., "File > Export > Export As")
        software: Which software this belongs to
        version_introduced: Version when this entity first appeared
        version_deprecated: Version when this entity was removed (None if active)
        aliases: Alternative names for this entity
    """
    entity_id: str
    name: str
    entity_type: EntityType = EntityType.UNKNOWN
    description: str = ""
    parent_path: str = ""
    software: str = ""
    version_introduced: str = ""
    version_deprecated: str = ""
    aliases: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        return f"{self.name} ({self.entity_type.value})"

    def __hash__(self):
        return hash(self.entity_id)

@dataclass
class UsageKnowledgeTriple:
    """
    A versioned knowledge triple for software usage.

    Captures relationships between software entities with full version
    tracking to support maintenance and updates.

    Attributes:
        head: Subject entity name
        relation: Relationship type
        tail: Object entity name
        head_type: Entity type of head
        tail_type: Entity type of tail
        introduced_version: First version where this is true
        deprecated_version: Version where this became false (empty if still valid)
        valid_version_range: Human-readable version range (e.g., "2020-2024" or "2023+")
        confidence: Extraction confidence score [0-1]
        source_document: Where this was extracted from
        source_date: When source was published
        step_order: Position in procedure (0 if not a step)
        status: Current status (active, deprecated, needs_review)
        software: Which software this applies to
    """
    head: str
    relation: str
    tail: str
    head_type: EntityType = EntityType.UNKNOWN
    tail_type: EntityType = EntityType.UNKNOWN
    introduced_version: str = ""
    deprecated_version: str = ""
    valid_version_range: str = ""
    confidence: float = 0.0
    source_document: str = ""
    source_date: str = ""
    step_order: int = 0
    status: TripleStatus = TripleStatus.ACTIVE
    software: str = ""

    def __str__(self) -> str:
        version_info = f" [{self.valid_version_range}]" if self.valid_version_range else ""
        return f"({self.head}) -[{self.relation}]-> ({self.tail}){version_info}"

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "head": self.head,
            "relation": self.relation,
            "tail": self.tail,
            "head_type": self.head_type.value if isinstance(self.head_type, EntityType) else self.head_type,
            "tail_type": self.tail_type.value if isinstance(self.tail_type, EntityType) else self.tail_type,
            "introduced_version": self.introduced_version,
            "deprecated_version": self.deprecated_version,
            "valid_version_range": self.valid_version_range,
            "confidence": self.confidence,
            "source_document": self.source_document,
            "source_date": self.source_date,
            "step_order": self.step_order,
            "status": self.status.value if isinstance(self.status, TripleStatus) else self.status,
            "software": self.software
        }

@dataclass
class Procedure:
    """
    Represents a multi-step procedure/workflow.

    Attributes:
        procedure_id: Unique identifier
        name: Name of the procedure
        description: What this procedure accomplishes
        steps: Ordered list of steps
        prerequisites: What's needed before starting
        outcome: Expected result
        software: Which software this is for
        version_range: Versions where this procedure is valid
    """
    procedure_id: str
    name: str
    description: str = ""
    steps: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    outcome: str = ""
    software: str = ""
    version_range: str = ""

    def __str__(self) -> str:
        return f"{self.name} ({len(self.steps)} steps)"

@dataclass
class ChangeRecord:
    """
    Records a change detected from release notes/updates.

    Attributes:
        change_type: Type of change (added, removed, changed, moved, renamed)
        entity_name: What was changed
        entity_type: Type of entity
        old_value: Previous state (for changes/moves/renames)
        new_value: New state
        version: Version where change occurred
        description: Details about the change
    """
    change_type: str  # "added", "removed", "changed", "moved", "renamed", "fixed"
    entity_name: str
    entity_type: EntityType = EntityType.UNKNOWN
    old_value: str = ""
    new_value: str = ""
    version: str = ""
    description: str = ""

@dataclass
class IntermediateOutput:
    """
    Stores intermediate outputs from each pipeline stage.

    Tracks the full pipeline state for debugging and analysis.
    """
    raw_text: str = ""
    document_type: DocumentType = DocumentType.UNKNOWN
    detected_version: str = ""
    detected_software: str = ""
    segments: List[Dict] = field(default_factory=list)
    entities: List[SoftwareEntity] = field(default_factory=list)
    procedures: List[Procedure] = field(default_factory=list)
    triples: List[UsageKnowledgeTriple] = field(default_factory=list)
    changes: List[ChangeRecord] = field(default_factory=list)
    deprecated_triples: List[UsageKnowledgeTriple] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    processing_time: float = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "raw_text": self.raw_text[:1000] + "..." if len(self.raw_text) > 1000 else self.raw_text,
            "document_type": self.document_type.value,
            "detected_version": self.detected_version,
            "detected_software": self.detected_software,
            "segments": self.segments,
            "entities": [asdict(e) for e in self.entities] if self.entities else [],
            "procedures": [asdict(p) for p in self.procedures] if self.procedures else [],
            "triples": [t.to_dict() for t in self.triples] if self.triples else [],
            "changes": [asdict(c) for c in self.changes] if self.changes else [],
            "deprecated_triples": [t.to_dict() for t in self.deprecated_triples] if self.deprecated_triples else [],
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "processing_time": self.processing_time
        }

##############################################################################
# Agent Classes
##############################################################################

class DocumentClassifierAgent:
    """
    Classifies incoming documents and extracts metadata.

    Determines:
    - Document type (tutorial, reference, release notes, etc.)
    - Software name and version
    - Publication date
    - Relevance for knowledge extraction
    """

    def __init__(self, client: OpenAI, model_name: str):
        self.client = client
        self.model_name = model_name
        self.system_prompt = """You are a Document Classification Agent for software documentation analysis.

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
"""

    def classify_document(self, text: str) -> Tuple[Dict, int, int, float]:
        """
        Classify a document and extract metadata.

        Args:
            text: Document text to classify

        Returns:
            Tuple of (classification_dict, prompt_tokens, completion_tokens, processing_time)
        """
        prompt = f"""Analyze this document and provide classification in JSON format:

Document (first 3000 chars):
{text[:3000]}

Return a JSON object with these fields:
- document_type: One of [tutorial, reference, release_notes, faq, troubleshooting, quick_start, unknown]
- software: Name of the software product
- version: Version number or "N/A" if not found
- date: Publication date or "N/A" if not found
- relevance_score: 0.0 to 1.0 for how useful this is for usage knowledge extraction
- main_topics: List of main features/topics covered
- rationale: Brief explanation of your classification

Return only valid JSON, no other text."""

        start_time = time.time()
        try:
            response = self.client.responses.create(
                model=self.model_name,
                instructions=self.system_prompt,
                input=prompt
            )

            content = response.output_text.strip()
            prompt_tokens = response.usage.input_tokens if response.usage else 0
            completion_tokens = response.usage.output_tokens if response.usage else 0
            processing_time = time.time() - start_time

            # Parse JSON response
            try:
                # Handle markdown code blocks
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                result = json.loads(content)
                return result, prompt_tokens, completion_tokens, processing_time
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse classification JSON: {content[:200]}")
                return {
                    "document_type": "unknown",
                    "software": "Unknown",
                    "version": "N/A",
                    "date": "N/A",
                    "relevance_score": 0.5,
                    "main_topics": [],
                    "rationale": "Failed to parse response"
                }, prompt_tokens, completion_tokens, processing_time

        except Exception as e:
            logger.error(f"Document classification failed: {str(e)}")
            return {
                "document_type": "unknown",
                "software": "Unknown",
                "version": "N/A",
                "date": "N/A",
                "relevance_score": 0.0,
                "main_topics": [],
                "rationale": f"Error: {str(e)}"
            }, 0, 0, time.time() - start_time


class UIElementExtractionAgent:
    """
    Extracts UI elements and their navigation paths from documentation.

    Identifies:
    - Buttons, menus, panels, tools, dialogs
    - Navigation paths (Menu > Submenu > Item)
    - UI hierarchy relationships
    """

    def __init__(self, client: OpenAI, model_name: str):
        self.client = client
        self.model_name = model_name
        self.system_prompt = """You are a UI Element Extraction Agent for software documentation.

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
"""

    def extract_ui_elements(self, text: str, software: str = "") -> Tuple[List[SoftwareEntity], int, int, float]:
        """
        Extract UI elements from text.

        Args:
            text: Text to extract from
            software: Software name for context

        Returns:
            Tuple of (entity_list, prompt_tokens, completion_tokens, processing_time)
        """
        software_context = f"Software: {software}\n" if software else ""

        prompt = f"""{software_context}Extract all UI elements from this text.

Text:
{text}

Return a JSON object with an "ui_elements" array. Each element should have:
- name: Element name
- type: One of [Button, Menu, MenuItem, Panel, Tool, Dialog, Tab, Slider, Checkbox, Dropdown, Toolbar, Field, Icon]
- parent_path: Navigation path (e.g., "Edit menu" or "Window > Properties")
- description: What it does (brief, or empty string if not described)

Return only valid JSON."""

        start_time = time.time()
        try:
            response = self.client.responses.create(
                model=self.model_name,
                instructions=self.system_prompt,
                input=prompt
            )

            content = response.output_text.strip()
            prompt_tokens = response.usage.input_tokens if response.usage else 0
            completion_tokens = response.usage.output_tokens if response.usage else 0
            processing_time = time.time() - start_time

            entities = []
            try:
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                data = json.loads(content)
                ui_elements = data.get("ui_elements", [])

                for elem in ui_elements:
                    entity = SoftwareEntity(
                        entity_id=f"ui_{elem.get('name', '').lower().replace(' ', '_')}",
                        name=elem.get("name", ""),
                        entity_type=EntityType.UI_ELEMENT,
                        description=elem.get("description", ""),
                        parent_path=elem.get("parent_path", ""),
                        software=software
                    )
                    if entity.name:
                        entities.append(entity)

            except json.JSONDecodeError:
                logger.warning(f"Failed to parse UI elements JSON")

            return entities, prompt_tokens, completion_tokens, processing_time

        except Exception as e:
            logger.error(f"UI element extraction failed: {str(e)}")
            return [], 0, 0, time.time() - start_time


class FeatureExtractionAgent:
    """
    Extracts software features, capabilities, and concepts.

    Identifies:
    - Features and capabilities
    - Concepts and terminology
    - Settings and configuration options
    - File formats supported
    - Constraints and requirements
    """

    def __init__(self, client: OpenAI, model_name: str):
        self.client = client
        self.model_name = model_name
        self.system_prompt = """You are a Feature Extraction Agent for software documentation.

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
"""

    def extract_features(self, text: str, software: str = "") -> Tuple[List[SoftwareEntity], int, int, float]:
        """
        Extract features and concepts from text.

        Args:
            text: Text to extract from
            software: Software name for context

        Returns:
            Tuple of (entity_list, prompt_tokens, completion_tokens, processing_time)
        """
        software_context = f"Software: {software}\n" if software else ""

        prompt = f"""{software_context}Extract all features, concepts, settings, file formats, shortcuts, and outcomes from this text.

Text:
{text}

Return a JSON object with an "entities" array. Each entity should have:
- name: Entity name
- type: One of [Feature, Concept, Setting, FileFormat, Constraint, Shortcut, Outcome]
- description: What it is/does
- related_to: List of related entity names (can be empty)

Return only valid JSON."""

        start_time = time.time()
        try:
            response = self.client.responses.create(
                model=self.model_name,
                instructions=self.system_prompt,
                input=prompt
            )

            content = response.output_text.strip()
            prompt_tokens = response.usage.input_tokens if response.usage else 0
            completion_tokens = response.usage.output_tokens if response.usage else 0
            processing_time = time.time() - start_time

            entities = []
            try:
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                data = json.loads(content)
                entity_list = data.get("entities", [])

                type_mapping = {
                    "Feature": EntityType.FEATURE,
                    "Concept": EntityType.CONCEPT,
                    "Setting": EntityType.SETTING,
                    "FileFormat": EntityType.FILE_FORMAT,
                    "Constraint": EntityType.CONSTRAINT,
                    "Shortcut": EntityType.SHORTCUT,
                    "Outcome": EntityType.OUTCOME
                }

                for elem in entity_list:
                    entity_type = type_mapping.get(elem.get("type", ""), EntityType.UNKNOWN)
                    entity = SoftwareEntity(
                        entity_id=f"{entity_type.value.lower()}_{elem.get('name', '').lower().replace(' ', '_')}",
                        name=elem.get("name", ""),
                        entity_type=entity_type,
                        description=elem.get("description", ""),
                        software=software
                    )
                    if entity.name:
                        entities.append(entity)

            except json.JSONDecodeError:
                logger.warning(f"Failed to parse features JSON")

            return entities, prompt_tokens, completion_tokens, processing_time

        except Exception as e:
            logger.error(f"Feature extraction failed: {str(e)}")
            return [], 0, 0, time.time() - start_time


class ProcedureExtractionAgent:
    """
    Extracts step-by-step procedures and workflows.

    Identifies:
    - Complete procedures with ordered steps
    - Prerequisites for procedures
    - Expected outcomes
    """

    def __init__(self, client: OpenAI, model_name: str):
        self.client = client
        self.model_name = model_name
        self.system_prompt = """You are a Procedure Extraction Agent for software documentation.

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
"""

    def extract_procedures(self, text: str, software: str = "") -> Tuple[List[Procedure], int, int, float]:
        """
        Extract procedures from text.

        Args:
            text: Text to extract from
            software: Software name for context

        Returns:
            Tuple of (procedure_list, prompt_tokens, completion_tokens, processing_time)
        """
        software_context = f"Software: {software}\n" if software else ""

        prompt = f"""{software_context}Extract all step-by-step procedures from this text.

Text:
{text}

Return a JSON object with a "procedures" array. Each procedure should have:
- name: Descriptive procedure name
- description: What it accomplishes
- prerequisites: List of requirements before starting (can be empty)
- steps: Ordered list of step instructions
- outcome: What user achieves at the end

Only extract actual procedures with clear sequential steps. Don't invent steps that aren't in the text.
Return only valid JSON. Return empty array if no clear procedures are found."""

        start_time = time.time()
        try:
            response = self.client.responses.create(
                model=self.model_name,
                instructions=self.system_prompt,
                input=prompt
            )

            content = response.output_text.strip()
            prompt_tokens = response.usage.input_tokens if response.usage else 0
            completion_tokens = response.usage.output_tokens if response.usage else 0
            processing_time = time.time() - start_time

            procedures = []
            try:
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                data = json.loads(content)
                proc_list = data.get("procedures", [])

                for i, proc in enumerate(proc_list):
                    procedure = Procedure(
                        procedure_id=f"proc_{i}_{proc.get('name', 'unknown').lower().replace(' ', '_')[:30]}",
                        name=proc.get("name", ""),
                        description=proc.get("description", ""),
                        steps=proc.get("steps", []),
                        prerequisites=proc.get("prerequisites", []),
                        outcome=proc.get("outcome", ""),
                        software=software
                    )
                    if procedure.name and procedure.steps:
                        procedures.append(procedure)

            except json.JSONDecodeError:
                logger.warning(f"Failed to parse procedures JSON")

            return procedures, prompt_tokens, completion_tokens, processing_time

        except Exception as e:
            logger.error(f"Procedure extraction failed: {str(e)}")
            return [], 0, 0, time.time() - start_time


class RelationshipExtractionAgent:
    """
    Extracts relationships between entities.

    Identifies:
    - UI navigation relationships (located_in, contains)
    - Feature dependencies (requires, enables)
    - Procedural relationships (achieves, prerequisite_for)
    - Shortcut mappings
    """

    def __init__(self, client: OpenAI, model_name: str):
        self.client = client
        self.model_name = model_name
        self.system_prompt = """You are a Relationship Extraction Agent for software documentation.

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
"""

    def extract_relationships(self, text: str, entities: List[SoftwareEntity]) -> Tuple[List[UsageKnowledgeTriple], int, int, float]:
        """
        Extract relationships between entities.

        Args:
            text: Source text
            entities: List of entities to find relationships between

        Returns:
            Tuple of (triple_list, prompt_tokens, completion_tokens, processing_time)
        """
        if not entities:
            return [], 0, 0, 0.0

        entity_list = "\n".join([f"- {e.name} ({e.entity_type.value})" for e in entities])

        prompt = f"""Given this text and list of entities, extract relationships between them.

Text:
{text}

Entities:
{entity_list}

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
Return only valid JSON."""

        start_time = time.time()
        try:
            response = self.client.responses.create(
                model=self.model_name,
                instructions=self.system_prompt,
                input=prompt
            )

            content = response.output_text.strip()
            prompt_tokens = response.usage.input_tokens if response.usage else 0
            completion_tokens = response.usage.output_tokens if response.usage else 0
            processing_time = time.time() - start_time

            triples = []
            entity_map = {e.name.lower(): e for e in entities}

            try:
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                data = json.loads(content)
                relationships = data.get("relationships", [])

                for rel in relationships:
                    head_name = rel.get("head", "")
                    tail_name = rel.get("tail", "")

                    # Look up entity types
                    head_entity = entity_map.get(head_name.lower())
                    tail_entity = entity_map.get(tail_name.lower())

                    triple = UsageKnowledgeTriple(
                        head=head_name,
                        relation=rel.get("relation", "related_to"),
                        tail=tail_name,
                        head_type=head_entity.entity_type if head_entity else EntityType.UNKNOWN,
                        tail_type=tail_entity.entity_type if tail_entity else EntityType.UNKNOWN,
                        confidence=float(rel.get("confidence", 0.5)),
                        status=TripleStatus.ACTIVE
                    )
                    if triple.head and triple.tail:
                        triples.append(triple)

            except json.JSONDecodeError:
                logger.warning(f"Failed to parse relationships JSON")

            return triples, prompt_tokens, completion_tokens, processing_time

        except Exception as e:
            logger.error(f"Relationship extraction failed: {str(e)}")
            return [], 0, 0, time.time() - start_time


class VersionResolutionAgent:
    """
    Assigns version metadata to extracted knowledge.

    Determines:
    - When features/UI elements were introduced
    - Version ranges where knowledge is valid
    - Version-specific variations
    """

    def __init__(self, client: OpenAI, model_name: str):
        self.client = client
        self.model_name = model_name
        self.system_prompt = """You are a Version Resolution Agent for software documentation.

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
"""

    def resolve_versions(self, triples: List[UsageKnowledgeTriple], context: str, detected_version: str = "") -> Tuple[List[UsageKnowledgeTriple], int, int, float]:
        """
        Add version metadata to triples.

        Args:
            triples: Triples to add version info to
            context: Source text for version clues
            detected_version: Version detected from document

        Returns:
            Tuple of (updated_triples, prompt_tokens, completion_tokens, processing_time)
        """
        if not triples:
            return [], 0, 0, 0.0

        triple_descriptions = "\n".join([f"{i+1}. {t}" for i, t in enumerate(triples)])
        version_context = f"Document version: {detected_version}\n" if detected_version else ""

        prompt = f"""{version_context}Analyze these knowledge triples and determine version information for each.

Triples:
{triple_descriptions}

Context from document:
{context[:2000]}

For each triple (numbered), provide:
- introduced_version: Version when this became true (empty string if unknown)
- valid_range: Version range like "2020+", "2019-2023", or "unknown"
- version_notes: Brief note about version applicability

Return JSON with "versions" array, one entry per triple in order:
{{"versions": [{{"introduced_version": "...", "valid_range": "...", "version_notes": "..."}}, ...]}}

Return only valid JSON."""

        start_time = time.time()
        try:
            response = self.client.responses.create(
                model=self.model_name,
                instructions=self.system_prompt,
                input=prompt
            )

            content = response.output_text.strip()
            prompt_tokens = response.usage.input_tokens if response.usage else 0
            completion_tokens = response.usage.output_tokens if response.usage else 0
            processing_time = time.time() - start_time

            try:
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                data = json.loads(content)
                versions = data.get("versions", [])

                for i, triple in enumerate(triples):
                    if i < len(versions):
                        v = versions[i]
                        triple.introduced_version = v.get("introduced_version", "")
                        triple.valid_version_range = v.get("valid_range", "unknown")

                    # If document has a detected version and no specific version found,
                    # use document version as reference
                    if not triple.introduced_version and detected_version:
                        triple.valid_version_range = f"{detected_version}+"

            except json.JSONDecodeError:
                logger.warning(f"Failed to parse version JSON")
                # Default: use document version if available
                for triple in triples:
                    if detected_version:
                        triple.valid_version_range = f"{detected_version}+"

            return triples, prompt_tokens, completion_tokens, processing_time

        except Exception as e:
            logger.error(f"Version resolution failed: {str(e)}")
            return triples, 0, 0, time.time() - start_time


class ChangeDetectionAgent:
    """
    Detects changes from release notes and update documents.

    Identifies:
    - New features/UI added
    - Removed features/UI
    - Changed/moved/renamed items
    - Bug fixes affecting known limitations
    """

    def __init__(self, client: OpenAI, model_name: str):
        self.client = client
        self.model_name = model_name
        self.system_prompt = """You are a Change Detection Agent for software update documents.

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
"""

    def detect_changes(self, text: str) -> Tuple[List[ChangeRecord], str, int, int, float]:
        """
        Extract changes from release notes.

        Args:
            text: Release notes text

        Returns:
            Tuple of (change_list, version, prompt_tokens, completion_tokens, processing_time)
        """
        prompt = f"""Extract all changes from this release notes / changelog document.

Document:
{text}

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

Return only valid JSON."""

        start_time = time.time()
        try:
            response = self.client.responses.create(
                model=self.model_name,
                instructions=self.system_prompt,
                input=prompt
            )

            content = response.output_text.strip()
            prompt_tokens = response.usage.input_tokens if response.usage else 0
            completion_tokens = response.usage.output_tokens if response.usage else 0
            processing_time = time.time() - start_time

            changes = []
            version = ""

            try:
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                data = json.loads(content)
                version = data.get("version", "")
                change_list = data.get("changes", [])

                type_mapping = {
                    "Feature": EntityType.FEATURE,
                    "UIElement": EntityType.UI_ELEMENT,
                    "Setting": EntityType.SETTING,
                    "Shortcut": EntityType.SHORTCUT,
                    "FileFormat": EntityType.FILE_FORMAT,
                    "Concept": EntityType.CONCEPT
                }

                for c in change_list:
                    change = ChangeRecord(
                        change_type=c.get("change_type", "changed"),
                        entity_name=c.get("entity_name", ""),
                        entity_type=type_mapping.get(c.get("entity_type", ""), EntityType.UNKNOWN),
                        old_value=c.get("old_value", ""),
                        new_value=c.get("new_value", ""),
                        version=version,
                        description=c.get("description", "")
                    )
                    if change.entity_name:
                        changes.append(change)

            except json.JSONDecodeError:
                logger.warning(f"Failed to parse changes JSON")

            return changes, version, prompt_tokens, completion_tokens, processing_time

        except Exception as e:
            logger.error(f"Change detection failed: {str(e)}")
            return [], "", 0, 0, time.time() - start_time


class ImpactAnalysisAgent:
    """
    Analyzes impact of changes on existing knowledge graph.

    Identifies:
    - Triples affected by changes
    - Procedures that need updating
    - Deprecated knowledge
    """

    def __init__(self, client: OpenAI, model_name: str):
        self.client = client
        self.model_name = model_name
        self.system_prompt = """You are an Impact Analysis Agent for knowledge graph maintenance.

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
"""

    def analyze_impact(self, changes: List[ChangeRecord], existing_triples: List[UsageKnowledgeTriple]) -> Tuple[List[Dict], int, int, float]:
        """
        Analyze impact of changes on existing knowledge.

        Args:
            changes: List of detected changes
            existing_triples: Existing knowledge graph triples

        Returns:
            Tuple of (impact_list, prompt_tokens, completion_tokens, processing_time)
        """
        if not changes or not existing_triples:
            return [], 0, 0, 0.0

        changes_desc = "\n".join([
            f"- {c.change_type.upper()}: {c.entity_name} ({c.entity_type.value})"
            + (f" from '{c.old_value}' to '{c.new_value}'" if c.old_value or c.new_value else "")
            + (f" - {c.description}" if c.description else "")
            for c in changes
        ])

        triples_desc = "\n".join([f"- {t}" for t in existing_triples[:50]])  # Limit for context

        prompt = f"""Analyze how these changes affect the existing knowledge triples.

Changes in this update:
{changes_desc}

Existing knowledge triples:
{triples_desc}

For each affected triple, provide:
- triple_index: Index in the triples list (0-based)
- impact: One of [deprecated, needs_update, unaffected]
- reason: Why it's affected
- suggested_update: New triple if needs_update, or empty

Return JSON: {{"affected_triples": [...]}}
Only include triples that are deprecated or need updates.
Return only valid JSON."""

        start_time = time.time()
        try:
            response = self.client.responses.create(
                model=self.model_name,
                instructions=self.system_prompt,
                input=prompt
            )

            content = response.output_text.strip()
            prompt_tokens = response.usage.input_tokens if response.usage else 0
            completion_tokens = response.usage.output_tokens if response.usage else 0
            processing_time = time.time() - start_time

            affected = []
            try:
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                data = json.loads(content)
                affected = data.get("affected_triples", [])

            except json.JSONDecodeError:
                logger.warning(f"Failed to parse impact analysis JSON")

            return affected, prompt_tokens, completion_tokens, processing_time

        except Exception as e:
            logger.error(f"Impact analysis failed: {str(e)}")
            return [], 0, 0, time.time() - start_time


class KnowledgeIntegrationAgent:
    """
    Integrates new knowledge into the existing knowledge graph.

    Handles:
    - Deduplication
    - Conflict resolution
    - Merging related entities
    """

    def __init__(self, client: OpenAI, model_name: str):
        self.client = client
        self.model_name = model_name
        self.system_prompt = """You are a Knowledge Integration Agent for software knowledge graphs.

Your job is to integrate new knowledge while maintaining consistency:

1. DEDUPLICATION: Identify when new entities/triples are duplicates of existing ones
   - Same entity with different names (aliases)
   - Same relationship expressed differently

2. CONFLICT RESOLUTION: When new knowledge conflicts with existing:
   - Version-specific: Both can be true in different versions
   - Correction: New knowledge supersedes old (with reason)
   - Ambiguous: Flag for human review

3. MERGING: Combine related information
   - Add aliases to existing entities
   - Merge partial procedure descriptions
   - Link related concepts

Guidelines:
- Prefer keeping both if they could be version-specific
- Prefer newer source if dates are known
- Flag for review if confidence is low
"""

    def integrate_triples(self, new_triples: List[UsageKnowledgeTriple], existing_triples: List[UsageKnowledgeTriple]) -> Tuple[List[UsageKnowledgeTriple], List[UsageKnowledgeTriple], int, int, float]:
        """
        Integrate new triples with existing knowledge.

        Args:
            new_triples: New triples to integrate
            existing_triples: Existing knowledge graph

        Returns:
            Tuple of (triples_to_add, triples_to_flag, prompt_tokens, completion_tokens, processing_time)
        """
        if not new_triples:
            return [], [], 0, 0, 0.0

        # Simple deduplication first (exact matches)
        existing_set = set()
        for t in existing_triples:
            key = f"{t.head.lower()}|{t.relation}|{t.tail.lower()}"
            existing_set.add(key)

        unique_new = []
        for t in new_triples:
            key = f"{t.head.lower()}|{t.relation}|{t.tail.lower()}"
            if key not in existing_set:
                unique_new.append(t)
                existing_set.add(key)  # Prevent duplicates within new_triples

        # For now, simple integration without LLM (can be enhanced)
        # All unique triples are added, none flagged
        return unique_new, [], 0, 0, 0.0


##############################################################################
# Main Pipeline Class
##############################################################################

class KARMA:
    """
    KARMA: Knowledge Agent for Software Usage Documentation

    A multi-agent pipeline that extracts structured knowledge from software
    documentation to build a versioned knowledge graph.

    Pipeline stages:
    1. Document Classification
    2. Entity Extraction (UI elements, features, concepts)
    3. Procedure Extraction
    4. Relationship Extraction
    5. Version Resolution
    6. Knowledge Integration

    For updates/maintenance:
    - Change Detection (from release notes)
    - Impact Analysis
    - Deprecation and Update
    """

    def __init__(self, api_key: str, base_url: str = None, model_name: str = "gpt-5.2"):
        """
        Initialize KARMA pipeline.

        Args:
            api_key: OpenAI API key
            base_url: Optional API base URL
            model_name: Model identifier
        """
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        self.client = OpenAI(**client_kwargs)
        self.model_name = model_name

        # Initialize agents
        self.doc_classifier = DocumentClassifierAgent(self.client, model_name)
        self.ui_extractor = UIElementExtractionAgent(self.client, model_name)
        self.feature_extractor = FeatureExtractionAgent(self.client, model_name)
        self.procedure_extractor = ProcedureExtractionAgent(self.client, model_name)
        self.relationship_extractor = RelationshipExtractionAgent(self.client, model_name)
        self.version_resolver = VersionResolutionAgent(self.client, model_name)
        self.change_detector = ChangeDetectionAgent(self.client, model_name)
        self.impact_analyzer = ImpactAnalysisAgent(self.client, model_name)
        self.integrator = KnowledgeIntegrationAgent(self.client, model_name)

        # Knowledge graph storage
        self.knowledge_graph = {
            "entities": {},      # entity_id -> SoftwareEntity
            "triples": [],       # List of UsageKnowledgeTriple
            "procedures": {},    # procedure_id -> Procedure
            "software": "",      # Primary software name
            "versions": set()    # Known versions
        }

        # Tracking
        self.output_log: List[str] = []
        self.intermediate = IntermediateOutput()

    def _read_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file."""
        try:
            text = ""
            with open(pdf_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text
        except Exception as e:
            logger.error(f"Failed to read PDF: {pdf_path}, error: {str(e)}")
            return ""

    def _log(self, message: str):
        """Log pipeline message."""
        logger.info(message)
        self.output_log.append(message)

    def _segment_text(self, text: str, max_length: int = 2000) -> List[str]:
        """Split text into manageable segments."""
        paragraphs = text.split("\n\n")
        segments = []
        current_segment = ""

        for para in paragraphs:
            if len(current_segment) + len(para) < max_length:
                current_segment += para + "\n\n"
            else:
                if current_segment.strip():
                    segments.append(current_segment.strip())
                current_segment = para + "\n\n"

        if current_segment.strip():
            segments.append(current_segment.strip())

        return segments if segments else [text[:max_length]]

    def process_document(self, source: Union[str, os.PathLike]) -> Dict:
        """
        Process a document and extract knowledge.

        Main entry point for knowledge extraction.

        Args:
            source: Text content or path to PDF file

        Returns:
            Dict with extraction results
        """
        total_prompt_tokens = 0
        total_completion_tokens = 0
        pipeline_start = time.time()

        # Handle input
        if isinstance(source, str) and source.lower().endswith('.pdf'):
            raw_text = self._read_pdf(source)
        elif isinstance(source, os.PathLike) and str(source).lower().endswith('.pdf'):
            raw_text = self._read_pdf(str(source))
        else:
            raw_text = source

        self.intermediate.raw_text = raw_text

        # === Stage 1: Document Classification ===
        self._log("[1/6] Classifying document...")
        classification, pt, ct, _ = self.doc_classifier.classify_document(raw_text)
        total_prompt_tokens += pt
        total_completion_tokens += ct

        doc_type = DocumentType(classification.get("document_type", "unknown"))
        software = classification.get("software", "Unknown")
        version = classification.get("version", "")

        self.intermediate.document_type = doc_type
        self.intermediate.detected_software = software
        self.intermediate.detected_version = version
        self.knowledge_graph["software"] = software
        if version:
            self.knowledge_graph["versions"].add(version)

        self._log(f"    Document type: {doc_type.value}, Software: {software}, Version: {version}")

        # Check if this is release notes (use update workflow)
        if doc_type == DocumentType.RELEASE_NOTES:
            return self.process_update_document(raw_text, version)

        # === Stage 2: Segment and Extract ===
        segments = self._segment_text(raw_text)
        self.intermediate.segments = [{"text": s} for s in segments]
        self._log(f"[2/6] Processing {len(segments)} text segments...")

        all_entities: List[SoftwareEntity] = []
        all_procedures: List[Procedure] = []

        for i, segment in enumerate(segments):
            # Extract UI elements
            ui_entities, pt, ct, _ = self.ui_extractor.extract_ui_elements(segment, software)
            total_prompt_tokens += pt
            total_completion_tokens += ct
            all_entities.extend(ui_entities)

            # Extract features and concepts
            feature_entities, pt, ct, _ = self.feature_extractor.extract_features(segment, software)
            total_prompt_tokens += pt
            total_completion_tokens += ct
            all_entities.extend(feature_entities)

            # Extract procedures
            procedures, pt, ct, _ = self.procedure_extractor.extract_procedures(segment, software)
            total_prompt_tokens += pt
            total_completion_tokens += ct
            all_procedures.extend(procedures)

        # Deduplicate entities
        entity_map = {}
        for e in all_entities:
            key = e.name.lower()
            if key not in entity_map:
                entity_map[key] = e
        all_entities = list(entity_map.values())

        self.intermediate.entities = all_entities
        self.intermediate.procedures = all_procedures
        self._log(f"    Extracted {len(all_entities)} entities, {len(all_procedures)} procedures")

        # === Stage 3: Relationship Extraction ===
        self._log("[3/6] Extracting relationships...")
        all_triples: List[UsageKnowledgeTriple] = []

        for segment in segments:
            triples, pt, ct, _ = self.relationship_extractor.extract_relationships(segment, all_entities)
            total_prompt_tokens += pt
            total_completion_tokens += ct
            all_triples.extend(triples)

        # Add procedure-derived triples
        for proc in all_procedures:
            # Procedure achieves outcome
            if proc.outcome:
                all_triples.append(UsageKnowledgeTriple(
                    head=proc.name,
                    relation=RelationType.ACHIEVES.value,
                    tail=proc.outcome,
                    head_type=EntityType.PROCEDURE,
                    tail_type=EntityType.OUTCOME,
                    confidence=0.9,
                    software=software
                ))

            # Step relationships
            for i, step in enumerate(proc.steps):
                all_triples.append(UsageKnowledgeTriple(
                    head=step,
                    relation=RelationType.PART_OF.value,
                    tail=proc.name,
                    head_type=EntityType.STEP,
                    tail_type=EntityType.PROCEDURE,
                    step_order=i + 1,
                    confidence=0.95,
                    software=software
                ))

                if i > 0:
                    all_triples.append(UsageKnowledgeTriple(
                        head=proc.steps[i-1],
                        relation=RelationType.NEXT_STEP.value,
                        tail=step,
                        head_type=EntityType.STEP,
                        tail_type=EntityType.STEP,
                        confidence=0.95,
                        software=software
                    ))

        self._log(f"    Extracted {len(all_triples)} relationships")

        # === Stage 4: Version Resolution ===
        self._log("[4/6] Resolving versions...")
        all_triples, pt, ct, _ = self.version_resolver.resolve_versions(all_triples, raw_text, version)
        total_prompt_tokens += pt
        total_completion_tokens += ct

        # === Stage 5: Knowledge Integration ===
        self._log("[5/6] Integrating knowledge...")
        new_triples, flagged, pt, ct, _ = self.integrator.integrate_triples(
            all_triples, self.knowledge_graph["triples"]
        )
        total_prompt_tokens += pt
        total_completion_tokens += ct

        # Add to knowledge graph
        for entity in all_entities:
            self.knowledge_graph["entities"][entity.entity_id] = entity

        for proc in all_procedures:
            self.knowledge_graph["procedures"][proc.procedure_id] = proc

        self.knowledge_graph["triples"].extend(new_triples)
        self.intermediate.triples = new_triples

        self._log(f"    Added {len(new_triples)} new triples to knowledge graph")

        # === Stage 6: Summary ===
        pipeline_time = time.time() - pipeline_start
        self.intermediate.prompt_tokens = total_prompt_tokens
        self.intermediate.completion_tokens = total_completion_tokens
        self.intermediate.processing_time = pipeline_time

        self._log(f"[6/6] Pipeline complete in {pipeline_time:.2f}s")
        self._log(f"    Total entities: {len(self.knowledge_graph['entities'])}")
        self._log(f"    Total triples: {len(self.knowledge_graph['triples'])}")
        self._log(f"    Total procedures: {len(self.knowledge_graph['procedures'])}")

        return {
            "entities": len(all_entities),
            "procedures": len(all_procedures),
            "triples": len(new_triples),
            "software": software,
            "version": version,
            "processing_time": pipeline_time
        }

    def process_update_document(self, text: str, version: str = "") -> Dict:
        """
        Process release notes / update document for knowledge maintenance.

        Identifies changes and updates the knowledge graph accordingly.

        Args:
            text: Release notes text
            version: Version number

        Returns:
            Dict with update results
        """
        total_prompt_tokens = 0
        total_completion_tokens = 0
        pipeline_start = time.time()

        self._log("[Update Pipeline] Processing release notes...")

        # === Detect Changes ===
        self._log("[1/3] Detecting changes...")
        changes, detected_version, pt, ct, _ = self.change_detector.detect_changes(text)
        total_prompt_tokens += pt
        total_completion_tokens += ct

        version = version or detected_version
        if version:
            self.knowledge_graph["versions"].add(version)

        self.intermediate.changes = changes
        self._log(f"    Detected {len(changes)} changes in version {version}")

        for change in changes:
            self._log(f"    - {change.change_type.upper()}: {change.entity_name}")

        # === Analyze Impact ===
        self._log("[2/3] Analyzing impact on existing knowledge...")
        affected, pt, ct, _ = self.impact_analyzer.analyze_impact(
            changes, self.knowledge_graph["triples"]
        )
        total_prompt_tokens += pt
        total_completion_tokens += ct

        deprecated_count = 0
        updated_count = 0

        for impact in affected:
            idx = impact.get("triple_index", -1)
            if 0 <= idx < len(self.knowledge_graph["triples"]):
                triple = self.knowledge_graph["triples"][idx]

                if impact.get("impact") == "deprecated":
                    triple.status = TripleStatus.DEPRECATED
                    triple.deprecated_version = version
                    self.intermediate.deprecated_triples.append(triple)
                    deprecated_count += 1

                elif impact.get("impact") == "needs_update":
                    triple.status = TripleStatus.NEEDS_REVIEW
                    updated_count += 1

        self._log(f"    Deprecated {deprecated_count} triples, flagged {updated_count} for review")

        # === Add New Knowledge from Changes ===
        self._log("[3/3] Adding new knowledge from changes...")
        new_triples = []

        for change in changes:
            if change.change_type == "added":
                # Create entity for new feature
                entity = SoftwareEntity(
                    entity_id=f"{change.entity_type.value.lower()}_{change.entity_name.lower().replace(' ', '_')}",
                    name=change.entity_name,
                    entity_type=change.entity_type,
                    description=change.description,
                    version_introduced=version,
                    software=self.knowledge_graph["software"]
                )
                self.knowledge_graph["entities"][entity.entity_id] = entity

                # Add "introduced_in" triple
                new_triples.append(UsageKnowledgeTriple(
                    head=change.entity_name,
                    relation=RelationType.INTRODUCED_IN.value,
                    tail=version,
                    head_type=change.entity_type,
                    tail_type=EntityType.VERSION,
                    introduced_version=version,
                    valid_version_range=f"{version}+",
                    confidence=0.95,
                    software=self.knowledge_graph["software"]
                ))

            elif change.change_type == "removed":
                # Add "removed_in" triple
                new_triples.append(UsageKnowledgeTriple(
                    head=change.entity_name,
                    relation=RelationType.REMOVED_IN.value,
                    tail=version,
                    head_type=change.entity_type,
                    tail_type=EntityType.VERSION,
                    confidence=0.95,
                    software=self.knowledge_graph["software"]
                ))

                # Add replacement if specified
                if change.new_value:
                    new_triples.append(UsageKnowledgeTriple(
                        head=change.entity_name,
                        relation=RelationType.REPLACED_BY.value,
                        tail=change.new_value,
                        head_type=change.entity_type,
                        tail_type=change.entity_type,
                        confidence=0.90,
                        software=self.knowledge_graph["software"]
                    ))

            elif change.change_type == "moved":
                new_triples.append(UsageKnowledgeTriple(
                    head=change.entity_name,
                    relation=RelationType.MOVED_TO.value,
                    tail=change.new_value,
                    head_type=change.entity_type,
                    tail_type=EntityType.UI_ELEMENT,
                    introduced_version=version,
                    confidence=0.90,
                    software=self.knowledge_graph["software"]
                ))

                # Add new location triple
                new_triples.append(UsageKnowledgeTriple(
                    head=change.entity_name,
                    relation=RelationType.LOCATED_IN.value,
                    tail=change.new_value,
                    head_type=change.entity_type,
                    tail_type=EntityType.UI_ELEMENT,
                    introduced_version=version,
                    valid_version_range=f"{version}+",
                    confidence=0.90,
                    software=self.knowledge_graph["software"]
                ))

            elif change.change_type == "renamed":
                new_triples.append(UsageKnowledgeTriple(
                    head=change.old_value or change.entity_name,
                    relation=RelationType.RENAMED_TO.value,
                    tail=change.new_value,
                    head_type=change.entity_type,
                    tail_type=change.entity_type,
                    introduced_version=version,
                    confidence=0.95,
                    software=self.knowledge_graph["software"]
                ))

        self.knowledge_graph["triples"].extend(new_triples)
        self.intermediate.triples.extend(new_triples)

        pipeline_time = time.time() - pipeline_start
        self.intermediate.processing_time = pipeline_time

        self._log(f"    Added {len(new_triples)} new triples from changes")
        self._log(f"[Update Pipeline] Complete in {pipeline_time:.2f}s")

        return {
            "changes_detected": len(changes),
            "triples_deprecated": deprecated_count,
            "triples_flagged": updated_count,
            "triples_added": len(new_triples),
            "version": version,
            "processing_time": pipeline_time
        }

    def get_outdated_knowledge(self) -> List[UsageKnowledgeTriple]:
        """Get all deprecated or needs-review triples."""
        return [
            t for t in self.knowledge_graph["triples"]
            if t.status in [TripleStatus.DEPRECATED, TripleStatus.NEEDS_REVIEW]
        ]

    def get_knowledge_for_version(self, version: str) -> List[UsageKnowledgeTriple]:
        """Get all active knowledge valid for a specific version."""
        valid_triples = []
        for t in self.knowledge_graph["triples"]:
            if t.status != TripleStatus.ACTIVE:
                continue

            # Check version range
            if not t.valid_version_range or t.valid_version_range == "unknown":
                valid_triples.append(t)
            elif "+" in t.valid_version_range:
                intro_ver = t.valid_version_range.replace("+", "")
                if version >= intro_ver:
                    valid_triples.append(t)
            elif "-" in t.valid_version_range:
                parts = t.valid_version_range.split("-")
                if len(parts) == 2 and parts[0] <= version <= parts[1]:
                    valid_triples.append(t)

        return valid_triples

    def export_knowledge_graph(self, output_path: str = None) -> Dict:
        """Export knowledge graph to JSON."""
        kg_export = {
            "software": self.knowledge_graph["software"],
            "versions": list(self.knowledge_graph["versions"]),
            "entities": [asdict(e) for e in self.knowledge_graph["entities"].values()],
            "procedures": [asdict(p) for p in self.knowledge_graph["procedures"].values()],
            "triples": [t.to_dict() for t in self.knowledge_graph["triples"]],
            "statistics": {
                "total_entities": len(self.knowledge_graph["entities"]),
                "total_procedures": len(self.knowledge_graph["procedures"]),
                "total_triples": len(self.knowledge_graph["triples"]),
                "active_triples": len([t for t in self.knowledge_graph["triples"] if t.status == TripleStatus.ACTIVE]),
                "deprecated_triples": len([t for t in self.knowledge_graph["triples"] if t.status == TripleStatus.DEPRECATED])
            }
        }

        if output_path:
            with open(output_path, 'w') as f:
                json.dump(kg_export, f, indent=2, default=str)
            logger.info(f"Knowledge graph exported to {output_path}")

        return kg_export

    def save_intermediate_results(self, output_path: str):
        """Save intermediate pipeline results."""
        try:
            with open(output_path, 'w') as f:
                json.dump(self.intermediate.to_dict(), f, indent=2, default=str)
            logger.info(f"Intermediate results saved to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save intermediate results: {str(e)}")

    def print_statistics(self):
        """Print knowledge graph statistics."""
        print(f"\nKnowledge Graph Statistics for {self.knowledge_graph['software']}:")
        print(f"  Versions tracked: {sorted(self.knowledge_graph['versions'])}")
        print(f"  Total entities: {len(self.knowledge_graph['entities'])}")
        print(f"  Total procedures: {len(self.knowledge_graph['procedures'])}")
        print(f"  Total triples: {len(self.knowledge_graph['triples'])}")

        # Count by status
        status_counts = {}
        for t in self.knowledge_graph["triples"]:
            status = t.status.value if isinstance(t.status, TripleStatus) else t.status
            status_counts[status] = status_counts.get(status, 0) + 1

        print(f"\n  Triples by status:")
        for status, count in sorted(status_counts.items()):
            print(f"    - {status}: {count}")

        # Count by relation type
        relation_counts = {}
        for t in self.knowledge_graph["triples"]:
            relation_counts[t.relation] = relation_counts.get(t.relation, 0) + 1

        print(f"\n  Top relationship types:")
        for rel, count in sorted(relation_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"    - {rel}: {count}")


##############################################################################
# CLI Entry Point
##############################################################################

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='KARMA: Extract software usage knowledge from documentation'
    )
    parser.add_argument('--input', required=True, help='Path to input document (PDF or text)')
    parser.add_argument('--api_key', required=True, help='OpenAI API key')
    parser.add_argument('--base_url', default=None, help='Optional API base URL')
    parser.add_argument('--model', default='gpt-5.2', help='Model name')
    parser.add_argument('--output', default='karma_knowledge_graph.json', help='Output file path')
    parser.add_argument('--update', action='store_true', help='Process as update/release notes')

    args = parser.parse_args()

    # Initialize KARMA
    karma = KARMA(api_key=args.api_key, base_url=args.base_url, model_name=args.model)

    # Read input
    if args.input.lower().endswith('.pdf'):
        print(f"Processing PDF: {args.input}")
        result = karma.process_document(args.input)
    else:
        with open(args.input, 'r') as f:
            text = f.read()

        if args.update:
            print(f"Processing as update document: {args.input}")
            result = karma.process_update_document(text)
        else:
            print(f"Processing document: {args.input}")
            result = karma.process_document(text)

    # Export results
    karma.export_knowledge_graph(args.output)
    karma.save_intermediate_results(f"intermediate_{args.output}")
    karma.print_statistics()

    print(f"\nResults saved to {args.output}")
