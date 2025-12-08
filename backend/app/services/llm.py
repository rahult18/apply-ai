from google import genai
import logging

logger = logging.getLogger(__name__)

class LLM():
    def __init__(self):
        self.client = genai.Client()

