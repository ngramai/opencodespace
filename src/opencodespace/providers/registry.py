"""Provider registry for managing deployment providers."""

from typing import Dict, List, Type

from .base import Provider


class ProviderRegistry:
    """
    Registry for managing available providers.
    
    This class maintains a collection of deployment providers and provides
    methods to register, retrieve, and list available providers.
    """
    
    def __init__(self):
        """Initialize an empty provider registry."""
        self._providers: Dict[str, Type[Provider]] = {}
    
    def register(self, provider_class: Type[Provider]) -> None:
        """
        Register a new provider.
        
        Args:
            provider_class: Provider class to register
            
        Raises:
            ValueError: If provider name is already registered
        """
        provider = provider_class()
        name = provider.name
        
        if name in self._providers:
            raise ValueError(f"Provider '{name}' is already registered")
        
        self._providers[name] = provider_class
    
    def unregister(self, name: str) -> None:
        """
        Unregister a provider.
        
        Args:
            name: Provider name to unregister
            
        Raises:
            KeyError: If provider is not found
        """
        if name not in self._providers:
            raise KeyError(f"Provider '{name}' not found")
        
        del self._providers[name]
    
    def get(self, name: str) -> Provider:
        """
        Get a provider instance by name.
        
        Args:
            name: Provider name
            
        Returns:
            Provider instance
            
        Raises:
            ValueError: If provider is not found
        """
        if name not in self._providers:
            available = ", ".join(self._providers.keys())
            raise ValueError(
                f"Unknown provider '{name}'. Available providers: {available}"
            )
        return self._providers[name]()
    
    def list_providers(self) -> List[str]:
        """
        Return list of available provider names.
        
        Returns:
            Sorted list of provider names
        """
        return sorted(self._providers.keys())
    
    def get_provider_info(self) -> Dict[str, str]:
        """
        Get information about all registered providers.
        
        Returns:
            Dictionary mapping provider names to descriptions
        """
        info = {}
        for name, provider_class in self._providers.items():
            provider = provider_class()
            info[name] = provider.description
        return info
    
    def __contains__(self, name: str) -> bool:
        """Check if a provider is registered."""
        return name in self._providers
    
    def __len__(self) -> int:
        """Return the number of registered providers."""
        return len(self._providers)