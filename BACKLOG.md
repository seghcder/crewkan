# CrewKan Backlog

Items to make CrewKan production-ready.

## High Priority

### Testing & Quality
- [ ] Achieve 90%+ test coverage (currently using simulator-based coverage)
- [ ] Add unit tests for edge cases (not just simulation)
- [ ] Add integration tests for CLI commands
- [ ] Add end-to-end tests for Streamlit UI
- [ ] Set up CI/CD pipeline (GitHub Actions / GitLab CI)
- [ ] Add linting (ruff, black, mypy)
- [ ] Add pre-commit hooks

### Code Quality
- [ ] Consolidate duplicate utility functions (load_yaml, save_yaml, now_iso) into `crewkan/utils.py`
- [ ] Refactor CLI to use BoardClient instead of duplicate code
- [ ] Add type hints throughout codebase
- [ ] Add docstrings to all public functions/classes
- [ ] Create API documentation (Sphinx or similar)

### Error Handling
- [ ] Improve error messages with context
- [ ] Add validation for YAML schema
- [ ] Handle corrupted YAML files gracefully
- [ ] Add retry logic for file operations
- [ ] Add transaction-like behavior for multi-file operations

### Performance
- [ ] Add caching for board/agent data
- [ ] Optimize task search (indexing or better algorithms)
- [ ] Add pagination for large task lists
- [ ] Profile and optimize hot paths

## Medium Priority

### Features
- [ ] WIP limit enforcement (warn/block when limit exceeded)
- [ ] Task dependencies validation
- [ ] Task templates
- [ ] Board templates
- [ ] Task search/filtering (full-text search)
- [ ] Task archiving automation
- [ ] Board archiving automation
- [ ] Export/import functionality (JSON, CSV)
- [ ] Task attachments support
- [ ] Task due date reminders

### Multi-Board
- [ ] Board summarization tool (status across sub-boards)
- [ ] Cross-board task references
- [ ] Board hierarchy visualization
- [ ] Board cloning

### UI/UX
- [ ] Improve Streamlit UI design
- [ ] Add task drag-and-drop (if possible in Streamlit)
- [ ] Add board switching in UI
- [ ] Add real-time updates (polling or websockets)
- [ ] Add dark mode
- [ ] Add keyboard shortcuts
- [ ] Mobile-responsive design

### LangChain Integration
- [ ] Add board creation tool to LangChain tools
- [ ] Add board registry query tool
- [ ] Add task search tool
- [ ] Add board summarization tool
- [ ] Example agent implementations
- [ ] Agent orchestration patterns

## Low Priority

### Storage Backends
- [ ] Implement NoSQL backend adapter (MongoDB)
- [ ] Implement PostgreSQL backend adapter
- [ ] Backend abstraction layer (protocol/interface)
- [ ] Backend migration tools
- [ ] Backend comparison/benchmarking

### Security & Access Control
- [ ] Authentication/authorization layer
- [ ] Role-based access control (RBAC)
- [ ] Agent permission system
- [ ] Audit logging
- [ ] Encryption at rest for sensitive data

### Observability
- [ ] Structured logging
- [ ] Metrics collection (Prometheus)
- [ ] Health check endpoints
- [ ] Performance monitoring
- [ ] Error tracking (Sentry)

### Documentation
- [ ] User guide
- [ ] API reference
- [ ] Architecture diagrams
- [ ] Deployment guide
- [ ] Troubleshooting guide
- [ ] Video tutorials

### Developer Experience
- [ ] Setup script for new developers
- [ ] Development environment setup (Docker)
- [ ] Example projects/templates
- [ ] Migration guides
- [ ] Changelog automation

### Distribution
- [ ] PyPI package
- [ ] Docker image
- [ ] Homebrew formula (if applicable)
- [ ] Installation script
- [ ] Upgrade/migration scripts

## Future Considerations

### Advanced Features
- [ ] Task scheduling/automation
- [ ] Workflow engine
- [ ] Integration with external systems (GitHub, Jira, etc.)
- [ ] Webhook support
- [ ] REST API (beyond LangChain tools)
- [ ] GraphQL API
- [ ] Real-time collaboration
- [ ] Conflict resolution for concurrent edits

### Scalability
- [ ] Distributed board storage
- [ ] Sharding for large organizations
- [ ] Replication for high availability
- [ ] Performance testing at scale

### AI/ML Features
- [ ] Task prioritization suggestions
- [ ] Agent workload balancing
- [ ] Predictive task completion times
- [ ] Anomaly detection
- [ ] Automated task assignment

## Notes

- Items are roughly ordered by priority
- Some items may depend on others
- Production readiness requires addressing High Priority items
- Medium Priority items enhance usability and features
- Low Priority items are nice-to-have or future enhancements

