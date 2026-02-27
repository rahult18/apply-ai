"""
Job provider factory and exports.
"""
from typing import Dict, Type
from app.services.job_providers.base import BaseJobProvider, NormalizedJob
from app.services.job_providers.ashby import AshbyProvider
from app.services.job_providers.lever import LeverProvider
from app.services.job_providers.greenhouse import GreenhouseProvider

# Provider name to class mapping
PROVIDER_REGISTRY: Dict[str, Type[BaseJobProvider]] = {
    "ashby": AshbyProvider,
    "lever": LeverProvider,
    "greenhouse": GreenhouseProvider,
}

# Singleton instances
_provider_instances: Dict[str, BaseJobProvider] = {}


def get_provider(provider_name: str) -> BaseJobProvider:
    """
    Get singleton provider instance by name.

    Args:
        provider_name: One of 'ashby', 'lever', 'greenhouse'

    Returns:
        Provider instance

    Raises:
        ValueError: If provider_name is not recognized
    """
    if provider_name not in PROVIDER_REGISTRY:
        raise ValueError(f"Unknown provider: {provider_name}. Valid options: {list(PROVIDER_REGISTRY.keys())}")

    if provider_name not in _provider_instances:
        _provider_instances[provider_name] = PROVIDER_REGISTRY[provider_name]()

    return _provider_instances[provider_name]


__all__ = [
    "BaseJobProvider",
    "NormalizedJob",
    "AshbyProvider",
    "LeverProvider",
    "GreenhouseProvider",
    "get_provider",
    "PROVIDER_REGISTRY",
]
