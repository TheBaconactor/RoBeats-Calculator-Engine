"""
ForceGreats GPU implementation (Taichi/Vulkan).

Production FG uses the response-frontier solver in `response_frontier.py`.
"""

from .response_builder import reconstruct_force_greats_response_trace
from .response_frontier import FgResponseFrontierSolveResult

__all__ = [
    "FgResponseFrontierSolveResult",
    "reconstruct_force_greats_response_trace",
]
