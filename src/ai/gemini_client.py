"""Gemini AI client wrapper for text and vision capabilities."""

import asyncio
import base64
import logging
from typing import Optional

from google import genai
from google.genai import types

from ..config import config

logger = logging.getLogger(__name__)


class GeminiClient:
    """Wrapper for Google Gemini API with text and vision support."""

    def __init__(self):
        """Initialize the Gemini client with API key."""
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.model = "gemini-flash-latest"  # More quota-friendly
        self.max_retries = 2
        self.retry_delay = 5  # seconds

    async def send_text(self, prompt: str) -> Optional[str]:
        """
        Send a text prompt to Gemini and get a response.

        Args:
            prompt: The text prompt to send.

        Returns:
            The generated text response, or None if failed.
        """
        for attempt in range(self.max_retries):
            try:
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model,
                    contents=prompt
                )
                return response.text
            except Exception as e:
                logger.warning(f"Gemini text request failed (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)

        logger.error("Gemini text request failed after all retries")
        return None

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
        for attempt in range(self.max_retries):
            try:
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
            except Exception as e:
                logger.warning(f"Gemini vision request failed (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)

        logger.error("Gemini vision request failed after all retries")
        return None

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
        for attempt in range(self.max_retries):
            try:
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
            except Exception as e:
                logger.warning(f"Gemini audio request failed (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)

        logger.error("Gemini audio request failed after all retries")
        return None

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
