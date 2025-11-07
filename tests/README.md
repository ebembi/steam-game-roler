# Test Suite

End-to-end tests for core functionality. These tests ensure the bot works correctly after refactoring or changes.

## Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_database.py

# Run specific test
pytest tests/test_database.py::test_user_linking
```

## What's Tested

### Database Operations (`test_database.py`)
Tests core data storage and retrieval:
- User-Steam account linking
- Game ownership and playtime tracking
- Role creation with owner counts and avg playtime ranks
- Average playtime rank calculation across users
- Top games queries (sorted by owners, then by playtime rank)
- Updating game stats changes ordering
- Blacklist system
- Multi-user scenarios
- Cleanup operations (removing all or selective games)
- Game role mapping retrieval

### Game Filtering (`test_game_filter.py`)
Tests business logic for which games get roles:
- Minimum player count requirements
- Minimum playtime requirements
- Blacklist filtering
- Multiplayer/co-op detection
- Flexible filtering options

## What's NOT Tested

We intentionally don't test:
- **External API wrappers** - Thin wrappers around Steam/Discord APIs
- **Discord bot commands** - Would require complex Discord.py mocking
- **Network calls** - We mock external dependencies

## Philosophy

Tests focus on **end-to-end functionality** rather than implementation details. They verify that:
1. Data is stored and retrieved correctly
2. Filtering logic produces expected results
3. Core features work after refactoring

Tests are **not pedantic** - they test behavior, not implementation. If we need to be testing the private API, then maybe we should rethink the code structure.

