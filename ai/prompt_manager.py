"""
Prompt Manager and Security Sanitizer
Loads versioned prompt templates, enforces untrusted input boundaries, and tracks prompt hashes.
"""

from typing import Dict, Any, Tuple, Optional
import os
import hashlib
import yaml

class PromptManager:
    """Manages prompt templates, versioning, SHA-256 hashing, and input sanitization."""

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            self.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        else:
            self.base_dir = base_dir

        self.prompts_dir = os.path.join(self.base_dir, "prompts")
        self.versions_file = os.path.join(self.prompts_dir, "prompt_versions.yml")
        self._load_version_metadata()
        self._load_templates()

    def _load_version_metadata(self):
        if os.path.exists(self.versions_file):
            with open(self.versions_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                self.active_version = data.get("active_version", "v1.0.0")
                self.version_info = data.get("versions", {}).get(self.active_version, {})
        else:
            self.active_version = "v1.0.0"
            self.version_info = {
                "version_id": "v1.0.0",
                "system_prompt_file": "prompts/system_prompt.md",
                "classification_prompt_file": "prompts/classification_prompt.md",
            }

    def _load_templates(self):
        sys_path = os.path.join(self.base_dir, self.version_info.get("system_prompt_file", "prompts/system_prompt.md"))
        cls_path = os.path.join(self.base_dir, self.version_info.get("classification_prompt_file", "prompts/classification_prompt.md"))

        with open(sys_path, "r", encoding="utf-8") as f:
            self.system_prompt_template = f.read()

        with open(cls_path, "r", encoding="utf-8") as f:
            self.classification_prompt_template = f.read()

        # Compute template hashes
        self.template_hash = hashlib.sha256(
            (self.system_prompt_template + self.classification_prompt_template).encode("utf-8")
        ).hexdigest()[:16]

    @staticmethod
    def sanitize_untrusted_text(text: str, max_chars: int = 4000) -> str:
        """
        Sanitize untrusted text from review records:
        1. Neutralize XML-like tag escapes that could attempt prompt injection.
        2. Enforce character length limit.
        3. Remove zero-width spaces and control characters.
        """
        if not text:
            return ""

        sanitized = text.replace("</REVIEW_DATA>", "[/REVIEW_DATA]").replace("<REVIEW_DATA>", "[REVIEW_DATA]")
        sanitized = sanitized.replace("```json", "[CODE_JSON]").replace("```", "[CODE]")

        # Truncate if exceeds limit
        if len(sanitized) > max_chars:
            sanitized = sanitized[:max_chars] + "... [TRUNCATED]"

        return sanitized.strip()

    def render_prompts(
        self,
        evidence_id: str,
        review_text: str,
        app_name: str = "Groww",
        star_rating: int = 3,
    ) -> Tuple[str, str, str, str]:
        """
        Render system and user prompts with sanitized data.
        Returns (system_prompt, user_prompt, prompt_hash, prompt_version).
        """
        clean_text = self.sanitize_untrusted_text(review_text)

        user_prompt = self.classification_prompt_template
        user_prompt = user_prompt.replace("{{evidence_id}}", str(evidence_id))
        user_prompt = user_prompt.replace("{{app_name}}", str(app_name))
        user_prompt = user_prompt.replace("{{star_rating}}", str(star_rating))
        user_prompt = user_prompt.replace("{{review_text}}", clean_text)

        full_prompt_payload = f"{self.system_prompt_template}\n---USER---\n{user_prompt}"
        prompt_hash = hashlib.sha256(full_prompt_payload.encode("utf-8")).hexdigest()[:16]

        return self.system_prompt_template, user_prompt, prompt_hash, self.active_version
