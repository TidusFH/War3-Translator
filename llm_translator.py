"""
LLM Translator Module
Handles translation using OpenAI-compatible APIs (OpenAI, OpenRouter, etc.)
"""

import os
import time
import json
from typing import List, Dict, Optional, Union
from pathlib import Path
import configparser

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

class LLMTranslator:
    def __init__(self, api_key: str = None, base_url: str = None, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.client = None
        
        if not OPENAI_AVAILABLE:
            print("⚠️ OpenAI library not installed. LLM translation unavailable.")
            return

        # Try to load from config if not provided
        if not self.api_key:
            self._load_config()

        if self.api_key:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            print(f"✓ LLM Translator initialized (Model: {self.model})")
        else:
            print("⚠️ No API key found for LLM Translator.")

    def _load_config(self):
        """Load configuration from config.ini or environment variables."""
        # Check environment variables first
        self.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("OPENROUTER_BASE_URL")
        
        # Check config.ini
        config_file = Path("config.ini")
        if config_file.exists():
            try:
                config = configparser.ConfigParser()
                config.read(config_file)
                
                if 'LLM' in config:
                    if not self.api_key:
                        self.api_key = config['LLM'].get('api_key')
                    if not self.base_url:
                        self.base_url = config['LLM'].get('base_url')
                    if 'model' in config['LLM']:
                        self.model = config['LLM'].get('model')
            except Exception as e:
                print(f"⚠️ Error reading config.ini: {e}")

    def translate_batch(self, texts: List[str], src_lang: str, dest_lang: str, context: str = "") -> List[str]:
        """
        Translate a batch of texts using the LLM.
        
        Args:
            texts: List of strings to translate
            src_lang: Source language
            dest_lang: Destination language
            context: Optional context about the game/map
            
        Returns:
            List of translated strings
        """
        if not self.client:
            return texts

        if not texts:
            return []

        # Prepare the prompt
        system_prompt = f"""You are a professional translator for Warcraft III maps. 
Translate the following text from {src_lang} to {dest_lang}.
Maintain all Warcraft III color codes (e.g., |cFFFF0000...|r) and formatting exactly.
Do not translate technical terms like 'u00A', 'h001' if they appear to be raw IDs.
Return ONLY a JSON array of strings, matching the order of the input."""

        if context:
            system_prompt += f"\nContext: {context}"

        user_prompt = json.dumps(texts, ensure_ascii=False)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            try:
                # Parse JSON response
                # Sometimes models wrap JSON in markdown code blocks
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                result = json.loads(content)
                
                # Handle different JSON structures the model might return
                if isinstance(result, list):
                    return result
                elif isinstance(result, dict):
                    # If it returns a dict, try to find the list
                    for key, value in result.items():
                        if isinstance(value, list) and len(value) == len(texts):
                            return value
                    # Fallback: if keys are indices
                    if "0" in result or "1" in result:
                        return [result.get(str(i), texts[i]) for i in range(len(texts))]
                
                print("⚠️ Unexpected JSON structure from LLM")
                return texts

            except json.JSONDecodeError:
                print(f"⚠️ Failed to parse LLM response as JSON: {content[:100]}...")
                return texts

        except Exception as e:
            print(f"❌ LLM Translation Error: {e}")
            return texts

    def translate_text(self, text: str, src_lang: str, dest_lang: str) -> str:
        """Translate a single string."""
        results = self.translate_batch([text], src_lang, dest_lang)
        return results[0] if results else text

