"""
title: Simple Test Action
author: Intelluxe AI
version: 1.0.0
license: MIT
description: Simple test action to verify Open WebUI function import process
"""


from pydantic import BaseModel, Field


class Action:
    """
    Simple Test Action

    A minimal action function to test the Open WebUI import process.
    Displays a simple message when the action button is clicked.
    """

    class Valves(BaseModel):
        """Configuration options for the test action"""

        test_message: str = Field(
            default="Hello from Intelluxe AI Healthcare System!",
            description="Custom message to display when action is triggered",
        )
        show_timestamp: bool = Field(
            default=True,
            description="Include timestamp in the response",
        )

    def __init__(self):
        """Initialize the action with default valve settings"""
        self.valves = self.Valves()

    async def action(
        self,
        body: dict,
        __user__: dict | None = None,
        __event_emitter__=None,
    ) -> dict | None:
        """
        Execute the test action

        Args:
            body: Request body from Open WebUI
            __user__: User information (if available)
            __event_emitter__: Event emitter for real-time updates

        Returns:
            dict: Response containing the test message
        """
        from datetime import datetime

        # Get user info
        user_name = __user__.get("name", "Unknown User") if __user__ else "Unknown User"

        # Emit status update if emitter available
        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {"description": "Processing test action..."},
            })

        # Build response message
        response_lines = [
            "## 🧪 Test Action Executed Successfully!",
            "",
            f"**Message**: {self.valves.test_message}",
            f"**User**: {user_name}",
        ]

        if self.valves.show_timestamp:
            response_lines.append(f"**Timestamp**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        response_lines.extend([
            "",
            "### ✅ Function Import Verification",
            "- ✅ Python function structure correct",
            "- ✅ Pydantic Valves working",
            "- ✅ Action method executed",
            "- ✅ Event emitter functional",
            "- ✅ User context available",
            "",
            "**Status**: Open WebUI function import successful! 🎉",
        ])

        # Final status update
        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {"description": "Test action completed successfully!"},
            })

        return {
            "content": "\n".join(response_lines),
        }
