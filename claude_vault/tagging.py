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
        return f"""Look at this conversation. Generate tags from the ACTUAL topics discussed.

Title: {title}
Content:
{content[:800]}

Output JSON:
{{"tags": ["tag1", "tag2"], "summary": "What was discussed"}}

Rules:
- Tags MUST come from actual content - what languages, tools, problems are mentioned?
- 3-5 tags, lowercase, hyphenated if needed
- Summary: what did this conversation cover?

Output only the JSON, nothing else."""

    def _note_prompt(self, title: str, content: str) -> str:
        """Prompt for regular markdown notes"""
        return f"""Look at this note. Generate tags from the ACTUAL content.

Title: {title}
Content:
{content[:800]}

Output JSON:
{{"tags": ["tag1", "tag2"], "summary": "What this note contains"}}

Rules:
- Extract tags from what's ACTUALLY in the note - projects, tech, topics, hashtags
- If there are #hashtags in the content, include them as tags
- If specific tech is mentioned (React, Laravel, WordPress), tag it
- If it's about a project, tag with project name
- 3-5 tags, lowercase
- Summary: what does this note actually contain?

Output only the JSON, nothing else."""

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
        """Extract tags from actual content - hashtags, tech terms, project names"""
        import re

        tags = []

        # Get full content
        full_content = conversation.title + " "
        for msg in conversation.messages:
            full_content += msg.content + " "

        # Extract existing hashtags from content (#work_log, #job, etc)
        hashtags = re.findall(r'#(\w+)', full_content)
        for tag in hashtags:
            tag = tag.lower().strip()
            if 2 <= len(tag) <= 30 and tag not in tags:
                tags.append(tag)

        # Extract tech/framework mentions from content
        tech_patterns = [
            r'\b(react|reactjs)\b',
            r'\b(laravel)\b',
            r'\b(wordpress|wp)\b',
            r'\b(python)\b',
            r'\b(javascript|js)\b',
            r'\b(typescript|ts)\b',
            r'\b(docker)\b',
            r'\b(vue|vuejs)\b',
            r'\b(node|nodejs)\b',
            r'\b(sql|mysql|postgres)\b',
            r'\b(api|rest|graphql)\b',
            r'\b(git|github)\b',
            r'\b(php)\b',
            r'\b(symfony)\b',
            r'\b(oauth)\b',
            r'\b(aws)\b',
            r'\b(golang|go)\b',
            r'\b(ruby|rails)\b',
            r'\b(jenkins)\b',
            r'\b(nginx)\b',
            r'\b(redis)\b',
            r'\b(mongodb)\b',
            r'\b(kubernetes|k8s)\b',
            r'\b(ci/cd|cicd)\b',
            r'\b(microservice)\b',
            r'\b(cache|caching)\b',
            r'\b(deploy|deployment)\b',
            r'\b(queue|jobs)\b',
            r'\b(lando)\b',
            r'\b(minio)\b',
            r'\b(frankenphp)\b',
            r'\b(jira)\b',
        ]

        content_lower = full_content.lower()
        for pattern in tech_patterns:
            matches = re.findall(pattern, content_lower)
            for match in matches:
                tag = match.lower().strip()
                if tag not in tags:
                    tags.append(tag)

        # Extract project/company names (look for patterns like "At CompanyName" or "### CompanyName")
        company_pattern = r'(?:at|for|#)\s*([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)'
        companies = re.findall(company_pattern, full_content)
        for company in companies[:2]:
            tag = company.lower().replace(' ', '-')
            if tag not in tags and len(tag) <= 20:
                tags.append(tag)

        # If still no tags, use significant words from title
        if not tags:
            title_words = conversation.title.lower().split()
            # Filter out common words
            skip = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "can", "shall"}
            for word in title_words:
                word = word.strip(".,!?;:")
                if word not in skip and len(word) > 2:
                    tags.append(word)

        return tags[:5]
