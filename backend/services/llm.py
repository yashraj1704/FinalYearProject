from __future__ import annotations

import asyncio
from typing import AsyncGenerator, List

from config import settings
from utils.logger import logger


class LLMClient:
    def __init__(self):
        self.provider = settings.llm_provider.lower()
        self._openai_async = None
        if self.provider == "openai" and settings.openai_api_key:
            try:  # pragma: no cover - optional
                from openai import AsyncOpenAI  # type: ignore
                self._openai_async = AsyncOpenAI(api_key=settings.openai_api_key)
                logger.info(f"Using OpenAI LLM: {settings.openai_model}")
            except Exception as e:
                logger.error(f"Failed to init OpenAI client: {e}")

    async def stream_chat(self, system_prompt: str, user_prompt: str) -> AsyncGenerator[str, None]:
        if self._openai_async is not None:
            try:  # pragma: no cover - optional
                stream = await self._openai_async.chat.completions.create(
                    model=settings.openai_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.2,
                    stream=True,
                )
                async for event in stream:
                    for choice in event.choices:
                        delta = getattr(choice, "delta", None) or getattr(choice, "message", None)
                        content = getattr(delta, "content", None) if delta else None
                        if content:
                            yield content
            except Exception as e:
                logger.error(f"OpenAI streaming failed, falling back to dummy: {e}")
                async for token in self._dummy_stream(system_prompt, user_prompt):
                    yield token
            return
        # HuggingFace or dummy fallback: synthesize a response deterministically
        async for token in self._dummy_stream(system_prompt, user_prompt):
            yield token

    async def _dummy_stream(self, system_prompt: str, user_prompt: str) -> AsyncGenerator[str, None]:
        # Extract context and question from the prompt
        import re
        
        # Extract context between <context> tags
        context_match = re.search(r'<context>\n(.*?)\n</context>', user_prompt, re.DOTALL)
        context_text = context_match.group(1).strip() if context_match else ""
        
        # Extract the actual question
        question_match = re.search(r'User Question: (.+)', user_prompt)
        actual_question = question_match.group(1).strip() if question_match else user_prompt
        
        # Handle follow-up questions
        follow_up_phrases = ["tell me more", "explain more", "more info", "more information", "elaborate", "expand", "details", "continue", "go on"]
        is_follow_up = any(phrase in actual_question.lower() for phrase in follow_up_phrases)
        
        if context_text:
            if is_follow_up:
                response = "Here's more information from your documents:\n\n"
                bullet_points = self._get_clean_sentences(context_text, max_points=6)
                for point in bullet_points:
                    response += f"• {point}\n"
            else:
                response = f"Based on your uploaded documents, here's what I found about '{actual_question}':\n\n"
                bullet_points = self._get_clean_sentences(context_text, max_points=5)
                
                for point in bullet_points:
                    response += f"• {point}\n"
                
                if len(bullet_points) > 0:
                    response += f"\nFound {len(bullet_points)} relevant points in your documents."
                else:
                    response += "No readable content found. Try rephrasing your question."
        else:
            response = f"I don't have information about '{actual_question}' in the uploaded documents."
        
        # Stream the response
        words = response.split()
        for i, word in enumerate(words):
            await asyncio.sleep(0.03)
            yield word + (" " if i < len(words) - 1 else "")

    def _get_clean_sentences(self, text: str, max_points: int = 5) -> list:
        """Get clean sentences from document text"""
        import re
        
        # Split by common sentence endings
        sentences = re.split(r'[.!?]+', text)
        clean_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            
            # Skip if too short or too long
            if len(sentence) < 10 or len(sentence) > 200:
                continue
            
            # Remove obvious technical symbols and fix spacing
            cleaned = re.sub(r'[|∃∈∀∧∨¬→↔≤≥≠={}()[\]\\\\]', ' ', sentence)
            cleaned = re.sub(r'\s+', ' ', cleaned)
            cleaned = cleaned.strip()
            
            # Skip if still has weird patterns
            if re.search(r'[a-z][A-Z][a-z]', cleaned):  # Mixed case patterns
                continue
            if re.search(r'\w\s\w\s\w\s\w\s\w\s\w', cleaned):  # Too many single letters
                continue
            
            # Must have mostly letters
            letter_count = sum(1 for c in cleaned if c.isalpha())
            if letter_count < len(cleaned) * 0.6:  # At least 60% letters
                continue
            
            # Must have normal words
            words = cleaned.split()
            if len(words) < 3:  # Need at least 3 words
                continue
            
            # Check if words look normal (not just random characters)
            normal_words = 0
            for word in words:
                if len(word) > 1 and word.isalpha():
                    normal_words += 1
            
            if normal_words < len(words) * 0.5:  # At least 50% normal words
                continue
            
            # Format it properly
            cleaned = cleaned[0].upper() + cleaned[1:] if cleaned else cleaned
            if not cleaned.endswith('.'):
                cleaned += '.'
            
            # Avoid duplicates
            if cleaned.lower() not in [s.lower() for s in clean_sentences]:
                clean_sentences.append(cleaned)
                if len(clean_sentences) >= max_points:
                    break
        
        return clean_sentences
