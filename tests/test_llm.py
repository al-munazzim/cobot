"""Tests for PPQ LLM plugin."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from cobot.plugins.ppq.plugin import PPQPlugin, InsufficientFundsError, create_plugin
from cobot.plugins.interfaces import LLMResponse, LLMError


class TestLLMResponse:
    """Test LLMResponse dataclass."""
    
    def test_has_tool_calls_false_when_none(self):
        response = LLMResponse(content="hello", model="test")
        assert response.has_tool_calls is False
    
    def test_has_tool_calls_true_when_present(self):
        response = LLMResponse(content="", tool_calls=[{"id": "1"}], model="test")
        assert response.has_tool_calls is True
    
    def test_tokens_in_from_usage(self):
        response = LLMResponse(
            content="hello",
            model="test",
            usage={"prompt_tokens": 100, "completion_tokens": 50}
        )
        assert response.tokens_in == 100
    
    def test_tokens_out_from_usage(self):
        response = LLMResponse(
            content="hello",
            model="test",
            usage={"prompt_tokens": 100, "completion_tokens": 50}
        )
        assert response.tokens_out == 50
    
    def test_tokens_zero_when_no_usage(self):
        response = LLMResponse(content="hello", model="test")
        assert response.tokens_in == 0
        assert response.tokens_out == 0


class TestPPQPlugin:
    """Test PPQPlugin with mocked HTTP."""
    
    @pytest.fixture
    def plugin(self):
        p = create_plugin()
        p.configure({
            "ppq": {
                "api_key": "test-key",
                "model": "test-model",
            }
        })
        return p
    
    @pytest.fixture
    def mock_response(self):
        """Create a mock HTTP response."""
        return {
            "choices": [{
                "message": {
                    "content": "Hello from LLM",
                    "tool_calls": None
                }
            }],
            "model": "test-model",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5}
        }
    
    def test_create_plugin(self):
        plugin = create_plugin()
        assert isinstance(plugin, PPQPlugin)
    
    def test_plugin_meta(self):
        plugin = create_plugin()
        assert plugin.meta.id == "ppq"
        assert "llm" in plugin.meta.capabilities
    
    def test_chat_success(self, plugin, mock_response):
        with patch('httpx.post') as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=Mock(return_value=mock_response),
                raise_for_status=Mock()
            )
            
            response = plugin.chat([{"role": "user", "content": "Hi"}])
            
            assert response.content == "Hello from LLM"
            assert response.tokens_in == 10
            assert response.tokens_out == 5
    
    def test_chat_with_tools(self, plugin):
        tool_response = {
            "choices": [{
                "message": {
                    "content": None,
                    "tool_calls": [
                        {"id": "1", "function": {"name": "read_file", "arguments": "{}"}}
                    ]
                }
            }],
            "model": "test-model",
            "usage": {"prompt_tokens": 20, "completion_tokens": 10}
        }
        
        with patch('httpx.post') as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=Mock(return_value=tool_response),
                raise_for_status=Mock()
            )
            
            response = plugin.chat(
                [{"role": "user", "content": "Read file"}],
                tools=[{"type": "function", "function": {"name": "read_file"}}]
            )
            
            assert response.has_tool_calls is True
            assert response.tool_calls[0]["function"]["name"] == "read_file"
    
    def test_chat_insufficient_funds(self, plugin):
        with patch('httpx.post') as mock_post:
            mock_post.return_value = Mock(status_code=402)
            
            with pytest.raises(InsufficientFundsError):
                plugin.chat([{"role": "user", "content": "Hi"}])
    
    def test_chat_api_error(self, plugin):
        import httpx
        
        with patch('httpx.post') as mock_post:
            mock_resp = Mock(status_code=500, text="Server error")
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "500 error", request=Mock(), response=mock_resp
            )
            mock_post.return_value = mock_resp
            
            with pytest.raises(LLMError) as exc_info:
                plugin.chat([{"role": "user", "content": "Hi"}])
            assert "500" in str(exc_info.value)
    
    def test_chat_no_api_key(self, monkeypatch):
        # Clear env var to test missing API key
        monkeypatch.delenv("PPQ_API_KEY", raising=False)
        
        plugin = create_plugin()
        plugin.configure({"ppq": {}})  # No API key
        
        with pytest.raises(LLMError) as exc_info:
            plugin.chat([{"role": "user", "content": "Hi"}])
        assert "not configured" in str(exc_info.value).lower()


class TestPPQPluginConfig:
    """Test PPQPlugin configuration."""
    
    def test_configure_sets_api_key(self):
        plugin = create_plugin()
        plugin.configure({"ppq": {"api_key": "my-key"}})
        assert plugin._api_key == "my-key"
    
    def test_configure_sets_model(self):
        plugin = create_plugin()
        plugin.configure({"ppq": {"model": "gpt-5"}})
        assert plugin._model == "gpt-5"
    
    def test_configure_sets_api_base(self):
        plugin = create_plugin()
        plugin.configure({"ppq": {"api_base": "https://custom.api/v1/"}})
        assert plugin._api_base == "https://custom.api/v1"  # Trailing slash removed
    
    def test_default_model(self):
        plugin = create_plugin()
        plugin.configure({"ppq": {}})
        assert plugin._model == "gpt-5-nano"
