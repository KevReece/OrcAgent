"""
Associate Entity Class

This module defines the Associate class which represents relationships between workers.
"""

from dataclasses import dataclass
from logger.log_wrapper import get_logger

logger = get_logger("agents:entities:associate", __name__)


@dataclass
class Associate:
    """
    Represents an associate relationship between workers.
    
    Attributes:
        name: The name of the associate worker
        relationship: Description of the working relationship
    """
    name: str
    relationship: str
    
 