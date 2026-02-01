# CLAUDE.md - AI Assistant Guide for rag-dashboard

## Project Overview

**rag-dashboard** is a custom RAG (Retrieval-Augmented Generation) data management tool. This project provides a dashboard interface for managing, monitoring, and interacting with RAG-based systems.

### Project Status

This project is in early development. The repository has been initialized but implementation is pending.

---

## Repository Structure

```
rag-dashboard/
├── CLAUDE.md           # This file - AI assistant guidelines
├── README.md           # Project overview and user documentation
└── (pending)           # Implementation structure TBD
```

### Expected Future Structure

As the project develops, expect a structure similar to:

```
rag-dashboard/
├── src/                # Source code
│   ├── backend/        # API server and RAG pipeline
│   ├── frontend/       # Dashboard UI
│   └── shared/         # Shared types and utilities
├── tests/              # Test suites
├── docs/               # Documentation
├── scripts/            # Build and utility scripts
├── config/             # Configuration files
└── data/               # Sample data and schemas
```

---

## Development Guidelines

### Git Workflow

1. **Branch Naming**: Use descriptive branch names
   - Features: `feature/<description>`
   - Bugfixes: `fix/<description>`
   - AI-assisted: `claude/<session-id>`

2. **Commits**:
   - Write clear, descriptive commit messages
   - Use conventional commit format when possible: `type(scope): description`
   - Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

3. **Pull Requests**:
   - Provide clear description of changes
   - Reference related issues
   - Ensure tests pass before merging

### Code Style

#### General Principles

- Write clean, readable, and maintainable code
- Follow the principle of least surprise
- Keep functions small and focused
- Use meaningful variable and function names
- Add comments only when the code isn't self-explanatory

#### When Adding New Technologies

Document the choice in this file with:
- The technology name and version
- Why it was chosen
- Basic usage patterns
- Any project-specific conventions

---

## RAG-Specific Guidelines

### Data Management

- Document all data sources and their schemas
- Implement proper data validation before ingestion
- Log all data processing operations for debugging
- Handle sensitive data according to security requirements

### Vector Store Operations

- Use batch operations for efficiency when possible
- Implement proper error handling for embedding failures
- Document embedding model choices and dimensions
- Consider chunking strategies for large documents

### LLM Integration

- Always set reasonable token limits
- Implement proper error handling and retries
- Log prompts and responses for debugging (with privacy considerations)
- Use streaming responses for better UX when applicable

---

## Common Tasks

### Setting Up Development Environment

```bash
# Clone the repository
git clone <repository-url>
cd rag-dashboard

# Install dependencies (update when package manager is chosen)
# npm install  # for Node.js
# pip install -r requirements.txt  # for Python
# poetry install  # for Python with Poetry

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Start development server
# npm run dev  # for Node.js
# python -m uvicorn main:app --reload  # for FastAPI
```

### Running Tests

```bash
# Run all tests (update when test framework is chosen)
# npm test
# pytest
# make test
```

### Building for Production

```bash
# Build production assets (update when build system is chosen)
# npm run build
# docker build -t rag-dashboard .
```

---

## Environment Variables

Document required environment variables here as they are added:

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `TBD` | To be determined | - | - |

---

## Dependencies

### Core Technologies (To Be Determined)

As the project develops, document major dependencies:

- **Backend Framework**: TBD (e.g., FastAPI, Express, NestJS)
- **Frontend Framework**: TBD (e.g., React, Vue, Svelte)
- **Vector Database**: TBD (e.g., Pinecone, Weaviate, Chroma, Qdrant)
- **Embedding Model**: TBD (e.g., OpenAI, Cohere, local models)
- **LLM Provider**: TBD (e.g., OpenAI, Anthropic, local models)

---

## API Reference

Document API endpoints as they are implemented:

```
(No endpoints implemented yet)
```

---

## Troubleshooting

### Common Issues

Document common issues and solutions as they arise:

```
(No known issues yet)
```

---

## AI Assistant Instructions

### When Working on This Project

1. **Read First**: Always read relevant files before making changes
2. **Understand Context**: Review existing patterns before adding new code
3. **Test Changes**: Ensure changes don't break existing functionality
4. **Update Documentation**: Keep this file and other docs up to date
5. **Small Changes**: Prefer smaller, focused changes over large refactors

### What to Avoid

- Don't add unnecessary dependencies
- Don't over-engineer solutions
- Don't leave debugging code or console logs
- Don't commit sensitive data (API keys, credentials)
- Don't make breaking changes without documenting migration steps

### Security Considerations

- Never hardcode API keys or secrets
- Validate all user inputs
- Sanitize data before storage or display
- Follow OWASP guidelines for web security
- Review security implications of LLM prompts (prompt injection risks)

---

## Update Log

| Date | Description |
|------|-------------|
| 2026-02-01 | Initial CLAUDE.md created |

---

*This file should be updated as the project evolves to reflect current structure, conventions, and guidelines.*
