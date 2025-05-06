import os
import httpx
from functools import lru_cache

from gradio_client import Client

from alexlab_if.alexlab_models import LanguageEnum


class TranslationService:
    def __init__(self, gradio_src: str, hf_token: str):
        self.gradio_src = gradio_src
        self.hf_token = hf_token

    @lru_cache
    def _get_gradio_client(self):
        # URL is https://aiforensics-opus-mt-translation-ce.hf.space
        # HF_TOKEN isn't needed as long as the space is public (default None)
        return Client(src=self.gradio_src, hf_token=self.hf_token)   


    @lru_cache(maxsize=5000)
    def _cached_translate(self, text: str, target_lang: LanguageEnum, source_lang=LanguageEnum.en):
        try:
            return self._get_gradio_client().predict(
                text=text,
                source_lang=source_lang.value,
                target_lang=target_lang.value,
                api_name="/predict"
            )
        except httpx.ReadTimeout:
            raise Exception("Translation service timed out, the HuggingFace Space might need a bit more time to boot. Please try again later.")


    def translate(self, text: str, target_lang: LanguageEnum, source_lang=LanguageEnum.en):
        if target_lang == source_lang:
            return text
        return self._cached_translate(text, target_lang, source_lang)
