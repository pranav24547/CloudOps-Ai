"""Backend selection for the AWS MCP server.

``CLOUDOPS_MODE=demo`` (default) uses the simulated environment.
``CLOUDOPS_MODE=live`` uses boto3 and the standard AWS credential chain.
"""

from __future__ import annotations

import os


def get_backend():
    aws_mode = os.getenv("AWS_MODE", "").lower()
    if aws_mode == "demo":
        from .simulated import SimulatedAWSBackend

        return SimulatedAWSBackend()
    if aws_mode == "live":
        from .live import LiveAWSBackend

        return LiveAWSBackend()

    mode = os.getenv("CLOUDOPS_MODE", "demo").lower()
    if mode == "live":
        from .live import LiveAWSBackend

        return LiveAWSBackend()
    from .simulated import SimulatedAWSBackend

    return SimulatedAWSBackend()
