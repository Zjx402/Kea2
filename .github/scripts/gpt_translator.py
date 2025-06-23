from openai import OpenAI
import logging

class OpenaiTranslator:
    def __init__(self, api_key:str):
        self.logger = logging.getLogger(name=self.__class__.__name__)
        # OpenAI Instance
        self.client = OpenAI(
            api_key=api_key,
            base_url=r"https://api.chatanywhere.tech/v1/"
        )

    def translate_text(self, text):
        response = self.client.chat.completions.create(
            model="gpt-4.1-mini",  # You can use gpt-3.5-turbo, gpt-4, gpt-4o, etc.
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            stream=False
        )

        translated = response.choices[0].message.content

        return translated.strip()    


GLOSSARY = """
property -> 性质
property-based testing -> 基于性质的测试
"""

SYSTEM_PROMPT = f"""
You are a translator. You need to translate some Markdown(.md) files from English into Simplified Chinese.

You need to follow these rules while translation:
1. Output the special info straightly. Don't modify them. Here are some special info examples:
- Techinical Nouns: Android、UI、Fastbot、Kea2
- Person Names: Su Ting、Ma Bo
- Paper References: An Empirical Study of Functional Bugs in Android Apps. ISSTA 2023.
- Email
- URL
- Markdown Code: `@precondition`
- Markdown Code Block: ```python python3 quicktest.py```

2. Just output your translation directly with not explanation.

Here's the glossary for you:
{GLOSSARY}
"""