# CrewKan Maintenance Guide

## Versioning

CrewKan uses [Semantic Versioning](https://semver.org/):
- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality in a backwards-compatible manner
- **PATCH**: Backwards-compatible bug fixes

Current version: **0.1.0**

### Version Tags

Tag releases in git:
```bash
git tag -a v0.1.0 -m "Release version 0.1.0"
git push origin v0.1.0
```

### Version Updates

When releasing a new version:
1. Update version in `RELEASE_NOTES.md`
2. Update version in this file
3. Create git tag
4. Update `CHANGELOG.md` (if maintained separately)

## Release Process

1. **Update Documentation**
   - Update `RELEASE_NOTES.md` with new features/changes
   - Update version numbers
   - Review and update `MAINTENANCE.md` if needed

2. **Run Tests**
   ```bash
   source venv/bin/activate
   PYTHONPATH=. python tests/test_all.py --coverage
   ```

3. **Check Coverage**
   - Review coverage report in `htmlcov/index.html`
   - Ensure coverage meets target (currently 50%, goal 90%+)

4. **Create Tag**
   ```bash
   git tag -a v0.1.0 -m "Release version 0.1.0"
   git push origin v0.1.0
   ```

5. **Update Release Notes**
   - Document breaking changes
   - Document new features
   - Document bug fixes

## Testing

### Running All Tests

```bash
# With coverage
PYTHONPATH=. python tests/test_all.py --coverage

# Without coverage
PYTHONPATH=. python tests/test_all.py --no-coverage
```

### Individual Test Suites

```bash
# CLI tests
PYTHONPATH=. python tests/test_cli.py

# UI tests (Playwright)
PYTHONPATH=. pytest tests/test_streamlit_extended.py -v

# Simulation
PYTHONPATH=. python tests/test_simulation.py

# LangChain (requires .env)
PYTHONPATH=. python tests/test_langchain_agent.py

# Coverage
PYTHONPATH=. python tests/test_coverage_comprehensive.py
```

## Logging

CrewKan uses Python's native logging. Configure logging:

```python
from crewkan.logging_config import setup_logging

# Basic setup
setup_logging()

# With file output
setup_logging(log_file=Path("crewkan.log"))

# With custom level
setup_logging(level=logging.DEBUG)
```

Log levels:
- **DEBUG**: Detailed information for debugging
- **INFO**: General informational messages
- **WARNING**: Warning messages
- **ERROR**: Error messages
- **CRITICAL**: Critical errors

## Code Quality

### Type Hints
- Add type hints to all new functions
- Use `typing` module for complex types

### Documentation
- Add docstrings to all public functions/classes
- Update `README.md` for user-facing changes
- Update `docs/` for architectural changes

### Testing
- Add tests for new features
- Maintain or improve coverage percentage
- Use abstracted test framework when possible

## Dependencies

### Updating Dependencies

1. Update `requirements.txt`
2. Update `tests/requirements.txt` if needed
3. Test with updated dependencies
4. Document breaking changes in `RELEASE_NOTES.md`

### Adding Dependencies

1. Add to appropriate `requirements.txt`
2. Document in `RELEASE_NOTES.md`
3. Test compatibility

## Backwards Compatibility

- **MAJOR version**: Breaking changes allowed
- **MINOR version**: New features, no breaking changes
- **PATCH version**: Bug fixes only, no breaking changes

When making breaking changes:
1. Document in `RELEASE_NOTES.md`
2. Provide migration guide if needed
3. Increment MAJOR version

## Board Schema Evolution

Board and agent schemas include version fields:
- `board.yaml`: `version: 1`
- `agents/agents.yaml`: `version: 1`

When changing schemas:
1. Increment version number
2. Provide migration script if needed
3. Document in `RELEASE_NOTES.md`

## Git Workflow

### Branching
- `main`: Stable, production-ready code
- Feature branches: `feature/description`
- Bug fix branches: `fix/description`

### Commits
- Use descriptive commit messages
- Reference issues/PRs when applicable
- Keep commits focused and atomic

### Pull Requests
- Include tests for new features
- Update documentation
- Ensure all tests pass
- Review coverage impact

## Monitoring

### Log Files
- Check logs for errors/warnings
- Monitor for performance issues
- Review user feedback

### Metrics to Track
- Test coverage percentage
- Number of boards/tasks
- API response times (future)
- Error rates (future)

## Support

For issues and questions:
1. Check `BACKLOG.md` for known issues
2. Review `docs/` for documentation
3. Check test files for usage examples

