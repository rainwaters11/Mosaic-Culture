import logging
from typing import Dict, Optional, Type
from .base_service import BaseService

logger = logging.getLogger(__name__)

class ServiceRegistry:
    """Registry to manage all application services"""
    
    def __init__(self):
        self._services: Dict[str, Optional[BaseService]] = {}

    def register_service(self, service_name: str, service_class: Type[BaseService]) -> None:
        """Register and initialize a service"""
        try:
            service_instance = service_class()
            self._services[service_name] = service_instance
            logger.info(f"Service {service_name} registered successfully")
        except Exception as e:
            logger.error(f"Failed to register service {service_name}: {str(e)}")
            self._services[service_name] = None

    def get_service(self, service_name: str) -> Optional[BaseService]:
        """Get a service by name"""
        return self._services.get(service_name)

    def is_service_available(self, service_name: str) -> bool:
        """Check if a service is available"""
        service = self.get_service(service_name)
        return service is not None and service.is_available

service_registry = ServiceRegistry()
