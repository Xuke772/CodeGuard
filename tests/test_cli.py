import pytest
from unittest.mock import patch, MagicMock
from codeguard.cli import create_agent_from_config, get_api_key


class TestGetApiKey:
    @patch("codeguard.cli.keyring")
    def test_get_key_from_keyring(self, mock_keyring):
        mock_keyring.get_password.return_value = "test-key-123"
        key = get_api_key()
        assert key == "test-key-123"

    @patch("codeguard.cli.keyring")
    @patch("codeguard.cli.os")
    def test_get_key_from_env_fallback(self, mock_os, mock_keyring):
        mock_keyring.get_password.return_value = None
        mock_os.environ.get.return_value = "env-key-456"
        key = get_api_key()
        assert key == "env-key-456"

    @patch("codeguard.cli.keyring")
    @patch("codeguard.cli.os")
    def test_no_key_found_raises(self, mock_os, mock_keyring):
        mock_keyring.get_password.return_value = None
        mock_os.environ.get.return_value = None
        with pytest.raises(RuntimeError, match="API key not found"):
            get_api_key()


class TestCreateAgent:
    @patch("codeguard.cli.get_api_key")
    def test_create_agent_from_config(self, mock_get_key, temp_workspace):
        from codeguard.config import Config
        mock_get_key.return_value = "test-key"
        config = Config()
        agent = create_agent_from_config(config, temp_workspace)
        assert agent is not None
        assert agent.project_root == temp_workspace