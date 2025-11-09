# Clarifications and Notes

This file tracks any clarifications needed during implementation.

## Implementation Notes

1. **Naming**: The system is called "CrewKan" but we kept backward compatibility with "ai_board" naming in some CLI arguments and default paths.

2. **Board Registry**: The board registry is optional but recommended for multi-board scenarios. It's stored at `boards/registry.yaml` by convention.

3. **Agent Kind**: Agents can be "ai" or "human". Default is "ai" when creating via CLI.

4. **Workspace Symlinks**: Workspaces use symlinks to canonical task files. This keeps the board as the source of truth while providing per-agent views.

5. **Storage Backend**: Currently only filesystem/YAML implementation is complete. NoSQL and other backends are documented but not implemented.

6. **Test Framework**: The test framework simulates realistic agent behavior:
   - CEO agent creates and assigns many tasks
   - Other agents work on tasks, add comments, create related tasks
   - Multi-board scenarios are tested
   - Tasks move through columns naturally

## Future Enhancements

- Implement NoSQL backend adapter
- Add PostgreSQL backend adapter
- Add board summarization tools
- Add dependency tracking and validation
- Add WIP limit enforcement
- Add task templates
- Add board archiving automation

