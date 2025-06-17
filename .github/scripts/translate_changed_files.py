import os
import yaml
import sys
from pathlib import Path
from gpt_translator import OpenaiTranslator


OPENAI_API_KEY = os.getenv("API_KEY")
CONFIG_PATH = Path(".github/translation-list.yml")

def translate_file(translator:OpenaiTranslator, input_path: Path, output_path: Path) -> None:
    """
    Translate a Markdown file and write the result to another file.
    """

    with open(input_path, "r", encoding="utf-8") as f:
        original_content = f.read()

    # Translate content using OpenAI translator
    translated_content = translator.translate_text(original_content)

    # Write translated content to output file
    with output_path.open("w", encoding="utf-8") as f:
        f.write(translated_content)


if __name__ == "__main__":

    # argv[1] is the file list needed translation
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        files = [line.strip() for line in f.readlines() if line.strip()]

    if(len(files)==0):
        exit(0)

    openai_translator = OpenaiTranslator(api_key=OPENAI_API_KEY)

    with open(CONFIG_PATH, "r") as f:
        file_mapping = dict(yaml.safe_load(f)["monitored_files"])
    
    for fname in files:
        translate_file(
            openai_translator,
            Path(fname),
            Path(file_mapping[fname])) # output
        
    translated = [file_mapping[f] for f in files]

    if translated:
        print("\n".join(translated))
