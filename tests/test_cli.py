import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from claude_vault.cli import app
from claude_vault.config import Config

runner = CliRunner()


def test_init_command(tmp_path):
    """Test that init command creates necessary files"""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        assert "Claude Vault initialized" in result.stdout

        # Check files were created
        config_dir = Path(".claude-vault")
        assert config_dir.exists()
        assert (config_dir / "config.json").exists()
        assert Path("conversations").exists()

        # Verify config content
        with open(config_dir / "config.json") as f:
            config = json.load(f)
            assert config["version"] == "0.1.0"


def test_init_already_initialized(tmp_path):
    """Test init command when already initialized"""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Run once
        runner.invoke(app, ["init"])

        # Run again
        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        assert "already initialized" in result.stdout


def test_config_command(tmp_path):
    """Test config command output"""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Initialize first
        runner.invoke(app, ["init"])

        # Run config command
        result = runner.invoke(app, ["config"], input="n\n")  # Say no to editing

        assert result.exit_code == 0
        assert "Current Settings" in result.stdout
        assert "llama3.2:3b" in result.stdout  # Default model


@patch("claude_vault.cli.OfflineTagGenerator")
@patch("claude_vault.cli.ClaudeExportParser")
def test_retag_command_no_ollama(mock_parser, mock_tag_gen_cls, tmp_path):
    """Test retag fails when Ollama is not available"""
    # Mock instance
    mock_tag_gen = MagicMock()
    mock_tag_gen_cls.return_value = mock_tag_gen

    # Mock config on the instance
    mock_tag_gen.config = Config()

    # Mock is_available to return False
    mock_tag_gen.is_available.return_value = False

    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(app, ["retag"])

        assert result.exit_code == 1
        assert "Ollama not running" in result.stdout


def test_sync_no_file():
    """Test sync command with missing file"""
    result = runner.invoke(app, ["sync", "nonexistent.json"])
    assert result.exit_code == 1
    assert "Export file not found" in result.stdout
