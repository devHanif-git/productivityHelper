"""Gemini AI client wrapper for text and vision capabilities."""

import asyncio
import base64
import logging
import time
from typing import Optional

from google import genai
from google.genai import types

from ..config import config

logger = logging.getLogger(__name__)


class GeminiClient:
    """Wrapper for Google Gemini API with text and vision support and automatic key rotation."""

    def __init__(self):
        """Initialize the Gemini client with API key rotation support."""
        self.api_keys = config.get_all_gemini_keys()
        if not self.api_keys:
            raise ValueError("No Gemini API keys configured")

        self.current_key_index = 0
        self.key_cooldowns: dict[int, float] = {}  # key_index -> cooldown_until_timestamp
        self.cooldown_duration = 60  # seconds to wait before retrying a rate-limited key

        # Initialize client with first key
        self.client = genai.Client(api_key=self.api_keys[0])
        self.model = "gemini-flash-latest"  # More quota-friendly
        self.max_retries = 2
        self.retry_delay = 5  # seconds

        logger.info(f"Gemini client initialized with {len(self.api_keys)} API key(s)")

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if the error is a rate limit error."""
        error_str = str(error).lower()
        return any(indicator in error_str for indicator in [
            "429", "rate limit", "quota", "resource exhausted",
            "too many requests", "rate_limit", "resourceexhausted"
        ])

    def _get_available_key_index(self) -> Optional[int]:
        """Find the next available key that's not on cooldown."""
        current_time = time.time()

        # Try all keys starting from current index
        for i in range(len(self.api_keys)):
            key_index = (self.current_key_index + i) % len(self.api_keys)
            cooldown_until = self.key_cooldowns.get(key_index, 0)

            if current_time >= cooldown_until:
                return key_index

        # All keys are on cooldown, return the one that will be available soonest
        soonest_index = min(self.key_cooldowns.keys(), key=lambda k: self.key_cooldowns[k])
        wait_time = self.key_cooldowns[soonest_index] - current_time
        logger.warning(f"All API keys on cooldown. Shortest wait: {wait_time:.1f}s (key {soonest_index + 1})")
        return soonest_index

    def _rotate_key(self, mark_current_limited: bool = True) -> bool:
        """Rotate to the next available API key."""
        if len(self.api_keys) <= 1:
            logger.warning("Only one API key available, cannot rotate")
            return False

        if mark_current_limited:
            # Mark current key as rate-limited
            self.key_cooldowns[self.current_key_index] = time.time() + self.cooldown_duration
            logger.info(f"API key {self.current_key_index + 1} rate-limited, cooldown for {self.cooldown_duration}s")

        # Find next available key
        next_index = self._get_available_key_index()
        if next_index is None or next_index == self.current_key_index:
            # If we can't find a different key, still try to move forward
            next_index = (self.current_key_index + 1) % len(self.api_keys)

        self.current_key_index = next_index
        self.client = genai.Client(api_key=self.api_keys[self.current_key_index])
        logger.info(f"Rotated to API key {self.current_key_index + 1}/{len(self.api_keys)}")
        return True

    async def _execute_with_rotation(self, operation_func, operation_name: str) -> Optional[str]:
        """Execute an operation with automatic key rotation on rate limit."""
        keys_tried = set()

        while len(keys_tried) < len(self.api_keys):
            # Check if current key is on cooldown
            current_time = time.time()
            cooldown_until = self.key_cooldowns.get(self.current_key_index, 0)

            if current_time < cooldown_until:
                wait_time = cooldown_until - current_time
                if wait_time > 0 and len(keys_tried) < len(self.api_keys) - 1:
                    # Try to rotate to another key instead of waiting
                    self._rotate_key(mark_current_limited=False)
                    continue
                else:
                    # All keys tried, wait for cooldown
                    logger.info(f"Waiting {wait_time:.1f}s for key cooldown...")
                    await asyncio.sleep(wait_time)

            keys_tried.add(self.current_key_index)

            for attempt in range(self.max_retries):
                try:
                    result = await operation_func()
                    # Success! Clear cooldown for this key
                    if self.current_key_index in self.key_cooldowns:
                        del self.key_cooldowns[self.current_key_index]
                    return result

                except Exception as e:
                    if self._is_rate_limit_error(e):
                        logger.warning(f"{operation_name} rate limited on key {self.current_key_index + 1}: {e}")
                        if self._rotate_key():
                            break  # Try with new key immediately
                        else:
                            # Only one key, wait and retry
                            await asyncio.sleep(self.retry_delay)
                    else:
                        logger.warning(f"{operation_name} failed (attempt {attempt + 1}): {e}")
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(self.retry_delay)

        logger.error(f"{operation_name} failed after trying all {len(self.api_keys)} keys")
        return None

    def get_key_status(self) -> dict:
        """Get status of all API keys for debugging."""
        current_time = time.time()
        status = {
            "total_keys": len(self.api_keys),
            "current_key": self.current_key_index + 1,
            "keys": []
        }
        for i in range(len(self.api_keys)):
            cooldown_until = self.key_cooldowns.get(i, 0)
            remaining = max(0, cooldown_until - current_time)
            status["keys"].append({
                "index": i + 1,
                "active": i == self.current_key_index,
                "cooldown_remaining": f"{remaining:.0f}s" if remaining > 0 else "ready"
            })
        return status

    async def send_text(self, prompt: str) -> Optional[str]:
        """
        Send a text prompt to Gemini and get a response.

        Args:
            prompt: The text prompt to send.

        Returns:
            The generated text response, or None if failed.
        """
        async def operation():
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model,
                contents=prompt
            )
            return response.text

        return await self._execute_with_rotation(operation, "Gemini text request")

    async def send_image(
        self,
        image_bytes: bytes,
        prompt: str,
        mime_type: str = "image/jpeg"
    ) -> Optional[str]:
        """
        Send an image with a prompt to Gemini for vision analysis.

        Args:
            image_bytes: Raw bytes of the image.
            prompt: The prompt describing what to extract/analyze.
            mime_type: MIME type of the image (default: image/jpeg).

        Returns:
            The generated text response, or None if failed.
        """
        async def operation():
            # Create image part for multimodal input
            image_part = types.Part.from_bytes(
                data=image_bytes,
                mime_type=mime_type
            )
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model,
                contents=[prompt, image_part]
            )
            return response.text

        return await self._execute_with_rotation(operation, "Gemini vision request")

    async def send_image_with_json(
        self,
        image_bytes: bytes,
        prompt: str,
        mime_type: str = "image/jpeg"
    ) -> Optional[str]:
        """
        Send an image with a prompt expecting JSON response.

        Adds JSON formatting instructions to the prompt.

        Args:
            image_bytes: Raw bytes of the image.
            prompt: The prompt describing what to extract.
            mime_type: MIME type of the image.

        Returns:
            The generated JSON string, or None if failed.
        """
        json_prompt = f"""{prompt}

IMPORTANT: Respond ONLY with valid JSON. No markdown code blocks, no explanations.
Just the raw JSON array or object."""

        return await self.send_image(image_bytes, json_prompt, mime_type)

    async def send_audio(
        self,
        audio_bytes: bytes,
        prompt: str,
        mime_type: str = "audio/ogg"
    ) -> Optional[str]:
        """
        Send an audio file with a prompt to Gemini for transcription/analysis.

        Args:
            audio_bytes: Raw bytes of the audio file.
            prompt: The prompt describing what to do with the audio.
            mime_type: MIME type of the audio (default: audio/ogg for Telegram voice).

        Returns:
            The generated text response, or None if failed.
        """
        async def operation():
            # Create audio part for multimodal input
            audio_part = types.Part.from_bytes(
                data=audio_bytes,
                mime_type=mime_type
            )
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model,
                contents=[prompt, audio_part]
            )
            return response.text

        return await self._execute_with_rotation(operation, "Gemini audio request")

    async def transcribe_audio(self, audio_bytes: bytes, mime_type: str = "audio/ogg") -> Optional[str]:
        """
        Transcribe audio to text.

        Args:
            audio_bytes: Raw bytes of the audio file.
            mime_type: MIME type of the audio.

        Returns:
            The transcription text, or None if failed.
        """
        prompt = """Transcribe this audio accurately and completely.
Output ONLY the transcription text, nothing else.
If there are multiple speakers, indicate speaker changes with [Speaker 1], [Speaker 2], etc.
Preserve the original language - do not translate."""

        return await self.send_audio(audio_bytes, prompt, mime_type)

    async def process_audio_content(
        self,
        transcript: str,
        processing_type: str
    ) -> Optional[str]:
        """
        Process a transcript according to the specified type.

        Args:
            transcript: The audio transcription.
            processing_type: One of: summary, minutes, tasks, study, smart

        Returns:
            The processed content, or None if failed.
        """
        prompts = {
            "summary": f"""Create a concise summary of this transcript:

{transcript}

Output a clear, well-structured summary highlighting the main points.
Use bullet points for key takeaways.""",

            "minutes": f"""Create formal meeting minutes from this transcript:

{transcript}

Format as:
## Meeting Minutes

**Date:** [Today's date]
**Duration:** [Estimated from content]

### Attendees
- List participants if mentioned

### Agenda Items Discussed
1. Topic 1
2. Topic 2

### Key Decisions
- Decision 1
- Decision 2

### Action Items
- [ ] Task 1 (Assigned to: Person, Due: Date if mentioned)
- [ ] Task 2

### Notes
Additional important points discussed.""",

            "tasks": f"""Extract all tasks, action items, assignments, and to-dos from this transcript:

{transcript}

Output as a list:
- [ ] Task 1 (context/deadline if mentioned)
- [ ] Task 2

Only include actual actionable items, not general discussion points.""",

            "study": f"""Convert this transcript into structured study notes:

{transcript}

Format as:
# Study Notes

## Key Concepts
- Concept 1: Explanation
- Concept 2: Explanation

## Important Points
1. Point 1
2. Point 2

## Definitions
- Term: Definition

## Summary
Brief overview of main topics covered.

## Review Questions
1. Question to test understanding""",

            "smart": f"""Analyze this transcript and provide the most useful output based on its content:

{transcript}

Determine what type of content this is (lecture, meeting, personal notes, brainstorm, etc.) and format the output appropriately:
- If it's a lecture/class: Create study notes
- If it's a meeting: Create meeting minutes
- If it's personal brainstorming: Create organized summary
- If it contains tasks: Extract and list them

Include:
1. Type of content detected
2. The appropriately formatted output
3. Any extracted action items or tasks at the end"""
        }

        prompt = prompts.get(processing_type, prompts["summary"])
        return await self.send_text(prompt)

    async def get_ai_suggestions(self, data: dict) -> Optional[str]:
        """
        Generate AI-powered suggestions based on user's data.

        Args:
            data: Dictionary containing assignments, tasks, todos, schedule, exams

        Returns:
            Suggestions text, or None if failed.
        """
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        day_name = datetime.now().strftime("%A")

        prompt = f"""You are a helpful student assistant. Analyze this student's current data and provide actionable suggestions.

Today: {today} ({day_name})

PENDING ASSIGNMENTS:
{self._format_items(data.get('assignments', []), 'assignments')}

UPCOMING TASKS:
{self._format_items(data.get('tasks', []), 'tasks')}

PENDING TODOS:
{self._format_items(data.get('todos', []), 'todos')}

WEEKLY SCHEDULE:
{self._format_schedule(data.get('schedule', []))}

UPCOMING EXAMS:
{self._format_items(data.get('exams', []), 'exams')}

Based on this data, provide:

1. **Priority Focus** - What should they work on first and why?
2. **Time Management** - When is the best time today/this week to work on pending items?
3. **Upcoming Deadlines** - Any urgent items needing attention?
4. **Study Suggestions** - If exams are coming, suggest preparation strategies
5. **Quick Wins** - Any small tasks they can complete quickly?

Be concise, practical, and encouraging. Use bullet points."""

        return await self.send_text(prompt)

    def _format_items(self, items: list, item_type: str) -> str:
        """Format items for AI prompt."""
        if not items:
            return "None"

        lines = []
        for item in items[:10]:  # Limit to 10 items
            if item_type == 'assignments':
                lines.append(f"- {item.get('title')} (Due: {item.get('due_date')}) [{item.get('subject_code', 'N/A')}]")
            elif item_type == 'tasks':
                lines.append(f"- {item.get('title')} (Date: {item.get('scheduled_date')} {item.get('scheduled_time', '')})")
            elif item_type == 'todos':
                lines.append(f"- {item.get('title')}")
            elif item_type == 'exams':
                lines.append(f"- {item.get('name_en', item.get('name'))} on {item.get('start_date')}")

        return "\n".join(lines)

    def _format_schedule(self, schedule: list) -> str:
        """Format schedule for AI prompt."""
        if not schedule:
            return "No schedule set"

        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        by_day = {}
        for slot in schedule:
            day = slot.get("day_of_week", 0)
            if day not in by_day:
                by_day[day] = []
            by_day[day].append(f"{slot.get('start_time')}-{slot.get('end_time')}: {slot.get('subject_code')}")

        lines = []
        for day_num in sorted(by_day.keys()):
            lines.append(f"{days[day_num]}: {', '.join(by_day[day_num])}")

        return "\n".join(lines)


# Singleton instance - lazy initialization
_gemini_client = None


def get_gemini_client() -> GeminiClient:
    """Get or create the Gemini client singleton."""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client


# For backward compatibility
gemini_client = None


def _init_client():
    global gemini_client
    if gemini_client is None and config.GEMINI_API_KEY:
        gemini_client = GeminiClient()


# Try to initialize on import, but don't fail if API key not set
try:
    _init_client()
except Exception:
    pass
