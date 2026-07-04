'''
unified LLM client Groq (llama 3.3 70B) primary , Gemini 2.0 flashback 
provides async completion and streaming interfaces 
'''

import logging 
import asyncio
from typing import AsyncIterator, Optional
from groq import AsyncGroq
import google.generativeai as genai
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class LLMClient:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._groq = None
            cls._instance._gemini = None 
        return cls._instance 
    
    def _get_groq(self) -> AsyncGroq:
        if self._groq is None:
            self._groq = AsyncGroq(api_key=settings.groq_api_key)
        return self._groq
    
    def _get_gemini(self):
        if self._gemini is None:
            genai.configure(api_key=settings.google_api_key)
            self._gemini = genai.GenerativeModel("gemini-2.0-flash")
        return self._gemini
    
    async def complete(self, prompt: str, temperature: float= 0.1, max_tokens: int = 3000, use_groq: bool = True) -> str:
        if use_groq: 
            try: 
                return await self._groq_complete(prompt, temperature, max_tokens)
            except Exception as e:
                logger.warning(f"Groq failed ({e}), falling back to Gemini")
                return await self._gemini_complete(prompt, temperature)
        else:
            return await self._gemini_complete(prompt, temperature)
        
    async def _groq_complete(self, prompt:str, temperature: float, max_tokens: int) -> str:
        client = self._get_groq()
        resp = await client.chat.completions.create(
            model= settings.reasoning_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content 
    
    async def _gemini_complete(self, prompt: str, temperature: float) -> str:
        model = self._get_gemini()
        config = genai.types.GenerationConfig(temperature=temperature)
        resp = await asyncio.to_thread(model.generate_content, prompt, generation_config=config)
        return resp.text
    
    async def stream_complete(self, prompt: str, temperature: float = 0.1, max_tokens: int = 3000)-> AsyncIterator[str]:
        client = self._get_groq()
        try:
            stream = await client.chat.completions.create(
                model=settings.reasoning_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content 
        
        except Exception as e:
            logger.warning(f"Groq streaming failed ({e}), using Gemini non-streaming")
            result = await self._gemini_complete(prompt, temperature)
            yield result
            
    async def classify(self, text: str, task: str) -> str:
        prompt = f"Task {task}\n\nText: {text}\n\nRespond with only the classification label."
        return await self._gemini_complete(prompt, temperature=0.0)
    

_llm_client = LLMClient()

def get_llm_client() -> LLMClient:
    return _llm_client 
