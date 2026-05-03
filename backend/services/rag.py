from __future__ import annotations

from typing import AsyncGenerator, List
import re

from utils.text import join_context
from utils.logger import logger
from services.retriever import Retriever
from services.llm import LLMClient
from config import settings


SYSTEM_PROMPT = (
    "You are a professional AI assistant specialized in document-based question answering.\n"
    "CRITICAL: Your answers MUST be based ONLY on the information provided in the retrieved context documents.\n"
    "If the answer cannot be found in the provided context, you MUST say: 'I cannot find information about this in the provided documents.'\n"
    "NEVER invent, hallucinate, or provide information not present in the context.\n"
    "NEVER answer based on general knowledge - only use the specific text provided.\n\n"
    "Guidelines:\n"
    "- Read the context carefully and extract only relevant information\n"
    "- If the context doesn't contain the answer, clearly state that\n"
    "- Be concise and factual - 2-4 sentences maximum\n"
    "- Do not make assumptions or inferences beyond the text\n"
    "- If multiple documents mention the topic, synthesize information from all relevant sources\n"
    "- Always base your answer on the exact words and facts from the context\n\n"
    "Context will always be provided in the following format:\n"
    "<context>\n[Top-k retrieved passages go here]\n</context>\n\n"
    "User Question: {user_query}"
)


class RAGPipeline:
    def __init__(self, retriever: Retriever, llm: LLMClient):
        self.retriever = retriever
        self.llm = llm
        self.last_context = ""  # Store last retrieved context for follow-ups
        self.last_question = ""  # Store last question for context

    async def stream_answer(self, query: str) -> AsyncGenerator[str, None]:
        # Allow lightweight small talk without retrieval
        q = query.strip().lower()
        if q in {"hi", "hello", "hey", "hey there", "hii", "hiii"}:
            msg = "Hello! Ask me questions about your documents."
            yield msg
            return

        # Check if this is a follow-up question (with typo tolerance)
        follow_up_phrases = ["tell me more", "explain more", "more info", "more information", "elaborate", "expand", "details", "continue", "go on", "tell me nore", "tell mmore", "tell me mor"]
        is_follow_up = any(phrase in q for phrase in follow_up_phrases)

        if is_follow_up and self.last_context:
            # For follow-up questions, use the previous context
            logger.info("Using previous context for follow-up question")
            context_text = self.last_context
            scores = [0.8]  # Dummy high score for follow-ups
        else:
            # Retrieve with scores for gating
            pairs = self.retriever.top_k_with_scores(query)
            contexts: List[str] = [t for t, _ in pairs]
            scores: List[float] = [s for _, s in pairs]
            context_text = join_context(contexts)
            
            # Store context and question for potential follow-ups
            self.last_context = context_text
            self.last_question = query
            
            logger.debug(f"Context length: {len(context_text)} chars")

        # Gate by relevance (only for new questions, not follow-ups)
        if not is_follow_up:
            # Check if we have any good matches
            high_score_docs = [s for s in scores if s >= 0.4]
            medium_score_docs = [s for s in scores if 0.3 <= s < 0.4]
            low_score_docs = [s for s in scores if s < 0.3]
            
            # If no documents match at all, reject
            if not high_score_docs and not medium_score_docs:
                msg = "I cannot find information about this in the provided documents."
                yield msg
                return
            
            # If only low-quality matches, be more lenient for basic questions
            if low_score_docs and not high_score_docs and not medium_score_docs:
                context_text = join_context(contexts)  # Still try with low scores

        # Build prompt
        if is_follow_up:
            # For follow-ups, modify the question to include context
            user_prompt = (
                f"<context>\n{context_text}\n</context>\n\n"
                f"User Question: {self.last_question} (follow-up: {query})"
            )
        else:
            user_prompt = (
                f"<context>\n{context_text}\n</context>\n\n"
                f"User Question: {query}"
            )

        # Stream from LLM
        async for token in self.llm.stream_chat(SYSTEM_PROMPT, user_prompt):
            yield token
