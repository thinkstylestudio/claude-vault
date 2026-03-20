from typing import List

import requests

from .config import load_config
from .models import Conversation


class OfflineTagGenerator:
    """Generate tags using local Ollama LLM"""

    def __init__(self):
        self.config = load_config()
        self.ollama_url = self.config.ollama.url

    def is_available(self) -> bool:
        """Check if Ollama is running"""
        try:
            base_url = self.ollama_url.split("/api")[0]
            response = requests.get(base_url, timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    def generate_metadata(self, conversation: Conversation) -> dict:
        """
        Generate tags and summary using LLM.
        Falls back to simple extraction if Ollama unavailable.
        """
        if not self.is_available():
            return self._fallback_metadata(conversation)

        # Get full content - let LLM see everything
        title = conversation.title
        content = ""
        for msg in conversation.messages:
            content += msg.content + "\n"
        content = content[:3000]

        # Detect if this is a conversation or a regular note
        is_conversation = "## 👤 You" in content or "## 🤖 Claude" in content

        if is_conversation:
            prompt = self._conversation_prompt(title, content)
        else:
            prompt = self._note_prompt(title, content)

        try:
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.config.ollama.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 200,
                    },
                },
                timeout=self.config.ollama.timeout,
            )

            if response.status_code == 200:
                import json

                response_json = response.json()
                raw = response_json.get("response", "").strip()

                try:
                    data = json.loads(raw)
                    return self._validate_metadata(data, content)
                except json.JSONDecodeError:
                    return self._fallback_metadata(conversation)

        except Exception:
            pass

        return self._fallback_metadata(conversation)

    def _conversation_prompt(self, title: str, content: str) -> str:
        """Prompt for conversation-style content"""
        return f"""Generate tags from this conversation. Look at what was ACTUALLY discussed.

Title: {title}
Content:
{content[:2000]}

Output JSON: {{"tags": ["tag1", "tag2"], "summary": "What was discussed"}}

Look for: languages, frameworks, tools, problems solved, topics.
Never use generic tags like "conversation-analysis" or "natural-language-processing".
Output only JSON."""

    def _note_prompt(self, title: str, content: str) -> str:
        """Prompt for regular markdown notes"""
        return f"""Generate tags from this note's ACTUAL content.

Title: {title}
Content:
{content[:2000]}

Output JSON: {{"tags": ["tag1", "tag2"], "summary": "One sentence about what this contains"}}

RULES:
- Tags must describe the TOPICS/ACTIVITIES in the note
- Include hashtags found in content (#job becomes job)
- Include tech mentioned (WordPress, Laravel, React, PHP)
- Include project names (StMarys, BeTheCure, cafe-api)
- Include people/companies mentioned
- Do NOT tag "communication" just because there's a Communication section
- Do NOT tag "work_log" or "personal_log" just because of section headers
- If note is mostly about ONE thing (job search, work task, personal), tag that
- 2-5 tags

Output only JSON."""

    def _validate_metadata(self, data: dict, content: str = "") -> dict:
        """Validate and clean metadata"""
        tags = data.get("tags", [])
        summary = data.get("summary")

        # Clean summary - remove HTML tags, system reminders, artifacts
        if summary:
            import re
            summary = str(summary)
            # Remove HTML/system tags
            summary = re.sub(r'<[^>]+>', '', summary)
            # Remove anything after system-reminder patterns
            summary = re.sub(r'\[?system-reminder\]?.*', '', summary, flags=re.IGNORECASE)
            # Remove operational mode changes
            summary = re.sub(r'Your operational mode.*', '', summary, flags=re.DOTALL)
            summary = re.sub(r'You are no longer.*', '', summary, flags=re.DOTALL)
            summary = re.sub(r'You are permitted.*', '', summary, flags=re.DOTALL)
            # Remove hallucinated prompt instructions - entire phrases
            bad_phrases = [
                r'^One sentence about what this contains\.?$',
                r'^Note contains.*$',
                r'^What this contains\.?$',
                r'^Notes about a project\.?$',
                r'^Notes?\.?$',
                r'^Summary.*$',
            ]
            for pattern in bad_phrases:
                if re.match(pattern, summary, re.IGNORECASE):
                    summary = None
                    break
            
            if summary:
                # Clean up whitespace
                summary = summary.strip()
                # Truncate if too long
                if len(summary) > 200:
                    summary = summary[:197] + "..."
                # Skip if empty after cleaning
                if not summary:
                    summary = None

        # Bad tags to reject
        bad_tags = {
            "conversation-analysis", "natural-language-processing", "dialogue-interpretation",
            "dialogue-modeling", "text-summarization", "conversation-analyzer",
            "output-format", "debugging", "notes", "markdown", "general", "content",
            "text-processing", "dialogue-understanding", "dialogue-summarization",
            "dialogue-system", "dialogue-patterns", "conversation", "analysis",
            "work_log", "personal_log", "communication",
        }

        valid_tags = []
        if isinstance(tags, list):
            for tag in tags:
                if isinstance(tag, str):
                    tag = tag.strip().lower().lstrip("#")
                    if (
                        2 <= len(tag) <= 30
                        and all(c.isalnum() or c in ["-", "_"] for c in tag)
                        and tag not in bad_tags
                    ):
                        valid_tags.append(tag)

        # If no valid tags, extract hashtags from original content
        if not valid_tags and content:
            import re
            hashtags = re.findall(r'#(\w+)', content)
            valid_tags = list(dict.fromkeys([h.lower() for h in hashtags]))[:5]

        return {"tags": valid_tags[:5], "summary": str(summary) if summary else None}

    def _fallback_metadata(self, conversation: Conversation) -> dict:
        """Simple fallback when Ollama unavailable - just extract hashtags"""
        import re

        tags = []
        full_content = conversation.title + " "
        for msg in conversation.messages:
            full_content += msg.content + " "

        # Extract hashtags
        hashtags = re.findall(r'#(\w+)', full_content)
        for tag in hashtags:
            tag = tag.lower()
            if tag not in tags:
                tags.append(tag)

        return {"tags": tags[:5], "summary": None}
