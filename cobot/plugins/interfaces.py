"""Capability interfaces for plugins.

Plugins that provide specific capabilities must implement these interfaces.
This ensures interchangeability (e.g., ppq and ollama both implement LLMProvider).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


# --- LLM Provider Interface ---

@dataclass
class LLMResponse:
    """Standard response from LLM providers."""
    content: str
    tool_calls: Optional[list] = None
    model: str = ""
    usage: Optional[dict] = None
    
    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)
    
    @property
    def tokens_in(self) -> int:
        if self.usage:
            return self.usage.get("prompt_tokens", 0)
        return 0
    
    @property
    def tokens_out(self) -> int:
        if self.usage:
            return self.usage.get("completion_tokens", 0)
        return 0


class LLMError(Exception):
    """Error from LLM provider."""
    pass


class LLMProvider(ABC):
    """Interface for LLM plugins (ppq, ollama, etc.).
    
    Any plugin with capability ["llm"] must implement this interface.
    """
    
    @abstractmethod
    def chat(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        model: Optional[str] = None,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Chat completion with optional tool support.
        
        Args:
            messages: List of {"role": "...", "content": "..."} dicts
            tools: Optional list of tool definitions (OpenAI format)
            model: Model override (uses default if None)
            max_tokens: Maximum tokens in response
        
        Returns:
            LLMResponse with content and optional tool_calls
        """
        pass
    
    def simple_chat(self, prompt: str, system: Optional[str] = None) -> str:
        """Simple chat without tools - convenience method."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = self.chat(messages)
        return response.content


# --- Communication Provider Interface ---

@dataclass
class Message:
    """Standard message from communication providers."""
    id: str
    sender: str
    content: str
    timestamp: int


class CommunicationError(Exception):
    """Error from communication provider."""
    pass


class CommunicationProvider(ABC):
    """Interface for communication plugins (nostr, etc.).
    
    Any plugin with capability ["communication"] must implement this interface.
    """
    
    @abstractmethod
    def get_identity(self) -> dict:
        """Get own identity information.
        
        Returns:
            Dict with identity info (e.g., {"npub": "...", "hex": "..."})
        """
        pass
    
    @abstractmethod
    def receive(self, since_minutes: int = 5) -> list[Message]:
        """Receive messages from the last N minutes.
        
        Args:
            since_minutes: Time window for messages
        
        Returns:
            List of Message objects
        """
        pass
    
    @abstractmethod
    def send(self, recipient: str, message: str) -> str:
        """Send a message to a recipient.
        
        Args:
            recipient: Recipient identifier (npub, address, etc.)
            message: Message content
        
        Returns:
            Message/event ID
        """
        pass


# --- Wallet Provider Interface ---

class WalletError(Exception):
    """Error from wallet provider."""
    pass


class WalletProvider(ABC):
    """Interface for wallet plugins.
    
    Any plugin with capability ["wallet"] must implement this interface.
    """
    
    @abstractmethod
    def get_balance(self) -> int:
        """Get wallet balance in sats.
        
        Returns:
            Balance in satoshis
        """
        pass
    
    @abstractmethod
    def pay(self, invoice: str) -> dict:
        """Pay a Lightning invoice.
        
        Args:
            invoice: BOLT11 invoice string
        
        Returns:
            Result dict with "success" bool and details
        """
        pass
    
    @abstractmethod
    def get_receive_address(self) -> str:
        """Get address/invoice for receiving payments.
        
        Returns:
            Lightning address or invoice
        """
        pass


# --- Tool Provider Interface ---

@dataclass
class ToolResult:
    """Result of tool execution."""
    success: bool
    output: str
    error: Optional[str] = None


class ToolProvider(ABC):
    """Interface for tool plugins.
    
    Any plugin with capability ["tools"] must implement this interface.
    """
    
    @abstractmethod
    def get_definitions(self) -> list[dict]:
        """Get tool definitions for LLM.
        
        Returns:
            List of tool definitions in OpenAI format
        """
        pass
    
    @abstractmethod
    def execute(self, tool_name: str, args: dict) -> str:
        """Execute a tool.
        
        Args:
            tool_name: Name of the tool to execute
            args: Tool arguments
        
        Returns:
            Result string
        """
        pass
    
    @property
    @abstractmethod
    def restart_requested(self) -> bool:
        """Check if restart was requested via tool."""
        pass
