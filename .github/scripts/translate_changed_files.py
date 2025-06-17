import os
import sys
from pathlib import Path
from gpt_translator import OpenaiTranslator


OPENAI_API_KEY = os.getenv("API_KEY")


def translate_file(translator:OpenaiTranslator, input_path: Path, output_path: Path) -> None:
    """
    Translate a Markdown file and write the result to another file.
    """

    # Read original file content
    if not os.path.exists(input_path):
        print(f"❌ File {input_path} not found.")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        original_content = f.read()

    # Translate content using OpenAI translator
    translated_content = translator.translate_text(original_content)

    # Write translated content to output file
    with output_path.open("w", encoding="utf-8") as f:
        f.write(translated_content)

    print(f"✅ Translation complete: {input_path.name} → {output_path.name}")


if __name__ == "__main__":

    # argv[1] is the file list needed translation
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        files = [line.strip() for line in f.readlines() if line.strip()]

    if(len(files)==0):
        print("No monitored file changed. Skipping translation.")
        exit(0)

    openai_translator = OpenaiTranslator(api_key=OPENAI_API_KEY)
    
    print(f"found {len(files)} untranslated files.")

    for fname in files:
        translate_file(
            openai_translator,
            Path(fname),
            Path(fname).with_name(Path(fname).stem + "_cn.md") # output path
        )