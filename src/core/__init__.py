"""
Core package for Alpha Machine.

Contains configuration, models, utilities, and other core components.
"""

from .config import Config
from .models import (
    LinearProject, LinearMilestone, LinearIssue, LinearContext,
    GeneratedIssue, GeneratedIssuesResponse, ProcessingResult
)
from .utils import print_separator, load_prompts

__all__ = [
    "Config",
    "LinearProject", "LinearMilestone", "LinearIssue", "LinearContext",
    "GeneratedIssue", "GeneratedIssuesResponse", "ProcessingResult",
    "print_separator", "load_prompts"
] 