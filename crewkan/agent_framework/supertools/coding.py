"""
Coding supertools: Cline and Continue integrations.
"""

import logging
import subprocess
import json
from pathlib import Path
from typing import Any, Dict
from crewkan.agent_framework.base import (
    Supertool,
    SupertoolContext,
    SupertoolResult,
    SupertoolError,
)
from crewkan.agent_framework.registry import register_supertool

logger = logging.getLogger(__name__)


@register_supertool("cline")
class ClineSupertool(Supertool):
    """
    Supertool for using Cline coding assistant.
    
    Cline is a CLI-based coding assistant that can help with code generation,
    refactoring, and debugging.
    """
    
    def __init__(self):
        super().__init__(
            tool_id="cline",
            name="Cline Coding Assistant",
            description="Use Cline CLI for code generation, refactoring, and debugging",
        )
    
    def get_required_credentials(self) -> list[str]:
        return []  # Cline CLI doesn't require credentials
    
    async def execute(self, context: SupertoolContext) -> SupertoolResult:
        """
        Execute Cline with the given prompt.
        
        Expected in additional_context:
        - prompt: The coding task or question
        - file_path: Optional file path to work on
        """
        try:
            prompt = context.metadata.get("prompt")
            if not prompt:
                raise SupertoolError("Missing 'prompt' in additional_context")
            
            file_path = context.metadata.get("file_path")
            
            # Build Cline command
            cmd = ["cline", prompt]
            if file_path:
                cmd.extend(["--file", str(context.workspace_path / file_path)])
            
            # Execute Cline
            result = subprocess.run(
                cmd,
                cwd=context.workspace_path,
                capture_output=True,
                text=True,
                timeout=context.constraints.get("max_execution_time", 300),
            )
            
            if result.returncode != 0:
                return SupertoolResult(
                    success=False,
                    output=result.stdout,
                    error=result.stderr or f"Cline exited with code {result.returncode}",
                )
            
            return SupertoolResult(
                success=True,
                output=result.stdout,
                data={"stderr": result.stderr} if result.stderr else None,
            )
            
        except subprocess.TimeoutExpired:
            return SupertoolResult(
                success=False,
                output="",
                error="Cline execution timed out",
            )
        except FileNotFoundError:
            return SupertoolResult(
                success=False,
                output="",
                error="Cline CLI not found. Please ensure Cline is installed and in PATH.",
            )
        except Exception as e:
            logger.exception("Error executing Cline")
            return SupertoolResult(
                success=False,
                output="",
                error=f"Unexpected error: {str(e)}",
            )


@register_supertool("continue")
class ContinueSupertool(Supertool):
    """
    Supertool for using Continue.dev coding assistant.
    
    Continue is a VS Code extension that provides AI-powered code completion
    and assistance. This supertool interfaces with Continue's API.
    """
    
    def __init__(self):
        super().__init__(
            tool_id="continue",
            name="Continue.dev Assistant",
            description="Use Continue.dev for AI-powered code completion and assistance",
        )
    
    def get_required_credentials(self) -> list[str]:
        return ["continue_api_key", "continue_endpoint"]  # May need API credentials
    
    async def execute(self, context: SupertoolContext) -> SupertoolResult:
        """
        Execute Continue with the given prompt.
        
        Expected in additional_context:
        - prompt: The coding task or question
        - file_path: Optional file path to work on
        """
        try:
            prompt = context.metadata.get("prompt")
            if not prompt:
                raise SupertoolError("Missing 'prompt' in additional_context")
            
            # For now, this is a placeholder implementation
            # Continue.dev integration would require API access
            api_key = context.credentials.get("continue_api_key")
            endpoint = context.credentials.get("continue_endpoint", "https://api.continue.dev")
            
            if not api_key:
                return SupertoolResult(
                    success=False,
                    output="",
                    error="Continue API key not provided",
                )
            
            # TODO: Implement actual Continue API integration
            # This would involve making HTTP requests to Continue's API
            
            return SupertoolResult(
                success=True,
                output=f"Continue integration placeholder - would process: {prompt}",
                data={"endpoint": endpoint},
            )
            
        except Exception as e:
            logger.exception("Error executing Continue")
            return SupertoolResult(
                success=False,
                output="",
                error=f"Unexpected error: {str(e)}",
            )




