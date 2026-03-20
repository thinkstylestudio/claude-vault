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
        Generate relevant tags and summary for any markdown content
        Uses LLM if available, falls back to keyword extraction
        """
        if not self.is_available():
            return self._fallback_metadata(conversation)

        # Get content for analysis
        title = conversation.title
        content = ""
        for msg in conversation.messages:
            content += msg.content + "\n"
        content = content[:2000]

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
                        "temperature": self.config.ollama.temperature,
                        "num_predict": 200,
                        "top_p": 0.9,
                    },
                },
                timeout=self.config.ollama.timeout,
            )

            if response.status_code == 200:
                response_json = response.json()
                content = response_json.get("response", "").strip()

                if isinstance(content, dict):
                    return self._validate_metadata(content)

                import json

                try:
                    data = json.loads(content)
                    return self._validate_metadata(data)
                except json.JSONDecodeError:
                    tags = self._parse_tags(content)
                    return {"tags": tags[:5], "summary": None}

        except requests.exceptions.Timeout:
            print("⚠️  Ollama request timed out. Using fallback.")
        except Exception as e:
            print(f"⚠️  Error generating metadata: {e}. Using fallback.")

        return self._fallback_metadata(conversation)

    def _conversation_prompt(self, title: str, content: str) -> str:
        """Prompt for conversation-style content"""
        return f"""Analyze this conversation and output JSON with relevant tags and a summary.

Title: {title}
Content: {content[:800]}

RULES:
- Output valid JSON only: {{"tags": ["tag1", "tag2"], "summary": "Brief summary"}}
- Tags: 3-5 specific lowercase tags about the TOPICS discussed
- Focus on: programming languages, frameworks, tools, concepts, problems solved
- Do NOT use meta-tags like "conversation-analysis" or "natural-language-processing"
- Summary: 1-2 sentences about what was discussed or solved

Example: {{"tags": ["python", "flask", "authentication", "jwt"], "summary": "Discussion about implementing JWT authentication in a Flask API."}}"""

    def _note_prompt(self, title: str, content: str) -> str:
        """Prompt for regular markdown notes"""
        return f"""Analyze this note and output JSON with relevant tags and a summary.

Title: {title}
Content: {content[:800]}

RULES:
- Output valid JSON only: {{"tags": ["tag1", "tag2"], "summary": "Brief summary"}}
- Tags: 3-5 specific lowercase tags about the ACTUAL CONTENT topics
- Look for: existing hashtags (#job #sales), technologies (React, Laravel), activities
- Do NOT use generic tags like "notes", "markdown", "general", "conversation-analysis"
- Summary: 1-2 sentences about what this note contains

Example: {{"tags": ["react", "performance", "job-search", "spanish", "sales"], "summary": "Job listings for React roles, Spanish vocabulary notes, and sales tips."}}"""

    def _validate_metadata(self, data: dict) -> dict:
        """Validate and clean metadata"""
        tags = data.get("tags", [])
        summary = data.get("summary")

        # Bad tags to reject
        bad_tags = {
            "conversation-analysis", "natural-language-processing", "dialogue-interpretation",
            "dialogue-modeling", "text-summarization", "conversation-analyzer",
            "output-format", "debugging", "notes", "markdown", "general", "content",
        }

        valid_tags = []
        if isinstance(tags, list):
            for tag in tags:
                if isinstance(tag, str):
                    tag = tag.strip().lower()
                    if (
                        2 <= len(tag) <= 30
                        and all(c.isalnum() or c in ["-", "_"] for c in tag)
                        and tag not in bad_tags
                    ):
                        valid_tags.append(tag)

        return {"tags": valid_tags[:5], "summary": str(summary) if summary else None}

    def _parse_tags(self, tags_text: str) -> List[str]:
        """Legacy helper for parsing simple tag lists"""
        tags_text = tags_text.replace("Your tags (comma-separated):", "").replace(
            "tags:", ""
        )
        tags_text = (
            tags_text.replace("{", "")
            .replace("}", "")
            .replace("[", "")
            .replace("]", "")
        )
        tags_text = tags_text.strip()

        tags = [tag.strip().lower() for tag in tags_text.split(",")]

        valid_tags = []
        for tag in tags:
            tag = tag.strip(".\"'")
            if 2 <= len(tag) <= 25 and all(c.isalnum() or c in ["-", "_"] for c in tag):
                valid_tags.append(tag)

        return valid_tags

    def _fallback_metadata(self, conversation: Conversation) -> dict:
        """Fallback when LLM unavailable"""
        return {"tags": self._fallback_tags(conversation), "summary": None}

    def _fallback_tags(self, conversation: Conversation) -> List[str]:
        """Simple keyword extraction as fallback when LLM unavailable"""
        keywords = {
            "python": ["python", "py", "django", "flask", "pip"],
            "javascript": ["javascript", "js", "react", "node", "npm", "typescript"],
            "api": ["api", "rest", "graphql", "endpoint"],
            "debugging": ["debug", "error", "bug", "fix", "issue"],
            "code": ["code", "coding", "programming", "development"],
            "tutorial": ["tutorial", "learn", "guide", "how-to"],
            "export": ["export", "download", "backup"],
            "design": ["design", "ui", "ux", "interface"],
            "research": ["research", "study", "analysis"],
            "data": ["data", "database", "sql", "analytics"],
            "web": ["web", "website", "html", "css"],
            "machine-learning": ["ml", "machine learning", "ai", "model"],
            "testing": ["test", "testing", "qa", "unit test"],
            "laravel": ["laravel", "eloquent", "artisan"],
            "wordpress": ["wordpress", "wp", "woocommerce"],
            "react": ["react", "jsx", "component", "hooks"],
            "vue": ["vue", "vuex", "nuxt"],
            "docker": ["docker", "container", "dockerfile"],
            "git": ["git", "github", "commit", "branch"],
            "sales": ["sales", "selling", "leads", "prospects"],
            "habits": ["habit", "routine", "daily", "morning"],
            "spanish": ["spanish", "español", "adiós", "dios"],
            "job": ["job", "career", "hiring", "interview", "resume", "#job"],
            "links": ["http", "youtube", "link", "url"],
            "wordpress-dev": ["wordpress", "wp-", "plugin", "theme"],
        }

        if self.config.custom_keywords:
            keywords.update(self.config.custom_keywords)

        title_lower = conversation.title.lower()
        content_lower = ""
        for msg in conversation.messages:
            content_lower += msg.content[:500].lower() + " "

        combined = f"{title_lower} {content_lower}"

        tags = []
        for tag, patterns in keywords.items():
            if any(pattern in combined for pattern in patterns):
                tags.append(tag)

        return tags[:5] if tags else ["notes"]
