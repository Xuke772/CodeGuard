import pytest
from unittest.mock import patch, MagicMock
from codeguard.cli import create_agent_from_config, get_api_key


class TestGetApiKey:
    def test_get_key_from_keyring(self, mocker):
        mocker.patch("codeguard.cli._has_keyring", True)
        mock_keyring = mocker.patch("codeguard.cli.keyring")
        mock_keyring.get_password.return_value = "test-key-123"
        key = get_api_key()
        assert key == "test-key-123"

    def test_get_key_from_env_fallback(self, mocker):
        mocker.patch("codeguard.cli._has_keyring", True)
        mock_keyring = mocker.patch("codeguard.cli.keyring")
        mock_keyring.get_password.return_value = None
        mocker.patch.dict("os.environ", {"DEEPSEEK_API_KEY": "env-key-456"})
        key = get_api_key()
        assert key == "env-key-456"

    def test_no_key_found_raises(self, mocker):
        mocker.patch("codeguard.cli._has_keyring", True)
        mock_keyring = mocker.patch("codeguard.cli.keyring")
        mock_keyring.get_password.return_value = None
        mocker.patch.dict("os.environ", {}, clear=True)
        with pytest.raises(RuntimeError, match="API key not found"):
            get_api_key()


class TestCreateAgent:
    def test_create_agent_from_config(self, mocker, temp_workspace):
        from codeguard.config import Config
        mocker.patch("codeguard.cli.get_api_key", return_value="test-key")
        config = Config()
        agent = create_agent_from_config(config, temp_workspace)
        assert agent is not None
        assert agent.project_root == temp_workspace