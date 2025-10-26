"""
Base Agent Class
================
Lightweight base class for all specialized agents.

Design Principle:
- Agents are thin wrappers (~5-20 lines)
- Skills do heavy lifting (HTTP, cache, validation)
- Skills execute OUTSIDE context (0 tokens)
- Agents just coordinate skill invocations
"""

import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class BaseAgent:
    """
    Base class for all agents.

    Provides common skill invocation interface.
    Agents inherit and add domain-specific methods.
    """

    def __init__(self, agent_name: str = "base_agent"):
        self.agent_name = agent_name
        self.project_root = Path(__file__).parent.parent
        self.python_bin = self.project_root / "venv" / "bin" / "python3"

    def invoke_skill(self, skill_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke a Claude Skill and return the result.

        This is the KEY method - agents just call skills.

        Args:
            skill_name: Name of the skill (e.g., "hyperliquid-fetch-and-cache")
            parameters: Parameters to pass to the skill

        Returns:
            Dict with 'success', 'data', 'metadata', and optionally 'error'

        Raises:
            Exception: If skill execution fails
        """
        # Construct path to skill script
        skill_script = self.project_root / "skills" / skill_name / "scripts" / "fetch_hyperliquid.py"

        if not skill_script.exists():
            raise FileNotFoundError(f"Skill script not found: {skill_script}")

        # Pass parameters as JSON to stdin
        try:
            result = subprocess.run(
                [str(self.python_bin), str(skill_script)],
                input=json.dumps(parameters),
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )

            if result.returncode != 0:
                raise Exception(f"Skill execution failed: {result.stderr}")

            # Parse and return result
            return json.loads(result.stdout)

        except subprocess.TimeoutExpired:
            raise Exception(f"Skill execution timed out after 30 seconds")
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse skill output: {e}")
        except Exception as e:
            raise Exception(f"Skill invocation error: {str(e)}")

    def handle_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Common error handling for all agents.

        Args:
            error: The exception that occurred
            context: Context information (endpoint, params, etc.)

        Returns:
            Error response dict
        """
        return {
            "success": False,
            "error": str(error),
            "error_type": type(error).__name__,
            "context": context,
            "agent": self.agent_name,
            "timestamp": datetime.now().isoformat()
        }

    def validate_response(self, response: Dict[str, Any]) -> None:
        """
        Validate skill response has required fields.

        Args:
            response: Response from skill invocation

        Raises:
            ValueError: If response is invalid
        """
        if not isinstance(response, dict):
            raise ValueError(f"Expected dict response, got {type(response)}")

        if "success" not in response:
            raise ValueError("Response missing 'success' field")

        if response["success"] and "data" not in response:
            raise ValueError("Successful response missing 'data' field")

        if not response["success"] and "error" not in response:
            raise ValueError("Failed response missing 'error' field")
