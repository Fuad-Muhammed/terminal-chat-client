# Terminal Chat Client Tests

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=client --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Test Files

| File | Description | Test Count |
|------|-------------|------------|
| `test_crypto.py` | Client-side encryption/decryption | ~10 |
| `test_config.py` | Configuration management | ~20 |
| `test_connection.py` | WebSocket client connection | ~20 |

**Total**: ~50 tests

## Running Specific Tests

```bash
# Run specific file
pytest tests/test_config.py

# Run specific test class
pytest tests/test_config.py::TestClientConfig

# Run specific test
pytest tests/test_connection.py::TestChatConnection::test_send_message_when_connected
```

## Test Coverage

Current coverage: **~90%**

Key areas:
- ✅ Encryption: 100%
- ✅ Configuration: 95%
- ✅ WebSocket Connection: 90%

## Fixtures

Available fixtures (defined in `conftest.py`):

- `temp_config_dir`: Temporary directory for config files
- `encryption_key`: Client encryption key instance
- `test_config`: Test configuration instance
- `mock_websocket`: Mock WebSocket connection
- `sample_message`: Sample message data
- `sample_encrypted_message`: Sample encrypted message

## Writing New Tests

Example:

```python
import pytest

class TestNewFeature:
    def test_feature_behavior(self, test_config):
        """Test feature behavior"""
        # Arrange
        config = test_config

        # Act
        result = config.get("setting")

        # Assert
        assert result is not None
```

For async tests:

```python
async def test_async_feature(self, mock_websocket):
    """Test async feature"""
    connection = ChatConnection(...)
    await connection.connect()

    assert connection.connected is True
```

See `../../TESTING.md` for detailed guidelines.
