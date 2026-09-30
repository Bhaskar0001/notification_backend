from abc import ABC, abstractmethod
from typing import Tuple, Optional, Dict, Any


class NotificationProvider(ABC):
    """
    Abstract Base Class for notification providers.
    Every provider must implement the send method returning:
      (success: bool, provider_response: dict | None, error_message: str | None)
    """

    @abstractmethod
    def send(self, notification) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Deliver notification to provider.
        """
        pass
