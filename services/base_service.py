from abc import ABC
import logging

logger = logging.getLogger(__name__)

class BaseService(ABC):
    """Base class for all services with common functionality"""
    
    def __init__(self):
        self.is_available = False
        try:
            self.initialize()
            self.is_available = True
            logger.info(f"{self.__class__.__name__} initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize {self.__class__.__name__}: {str(e)}")
            self.is_available = False

    def initialize(self):
        """Override this method in child classes to implement specific initialization logic"""
        pass
