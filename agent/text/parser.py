"""
Module: text.parser
Description: Parses text into paragraphs, sentences, and words using grammar rules.
"""

import regex as re

from text.grammar import TextPattern


class TextParser:
    def __init__(self):
        self.pattern = TextPattern()

    def get_paragraphs(self, text: str) -> list[str]:
        """Splits text into paragraphs based on double newlines."""
        return [p for p in self.pattern("paragraph").split(text)]

    def get_quotes(self, text: str) -> tuple[str, list[str]]:
        """Extract and replace quotes with placeholders to prevent mis-splitting."""
        quotes = []

        def replace_quote(match: re.Match) -> str:
            index = len(quotes)
            quotes.append(match.group(0))  # Store the full quote
            return f"__QUOTE_{index}__"

        text = self.pattern("quote").sub(replace_quote, text)
        return text, quotes

    def set_quotes(self, sentences: list[str], quotes: list[str]) -> list[str]:
        """Replace placeholders with the original quoted text."""
        for i, quote in enumerate(quotes):
            sentences = [s.replace(f"__QUOTE_{i}__", quote) for s in sentences]
        return sentences

    def get_toc(self, paragraphs: list[str]) -> list[str]:
        """Tag the table of contents with a TOC marker."""
        return [f"__TOC__ {p}" if self.pattern.is_toc(p) else p for p in paragraphs]

    def get_sentences(self, paragraph: str, quotes: list[str]) -> list[str]:
        """Splits a paragraph into sentences while handling TOC sections."""
        if paragraph.startswith("__TOC__"):
            print(paragraph)
            return [line.strip() for line in paragraph.splitlines()]

        sentences = []
        start = 0
        for match in self.pattern("sentence").finditer(paragraph):
            end = match.end()
            sentence = paragraph[start:end].strip()
            if sentence:
                sentences.append(sentence)
            start = end
        if start < len(paragraph):
            sentences.append(paragraph[start:].strip())

        return self.set_quotes(sentences, quotes)

    def get_words(self, sentence: str):
        """Extracts words, numbers, and symbols while preserving punctuation and spaces."""
        return self.pattern("word").findall(sentence)

    def parse(self, text: str):
        """Breaks down text into structured components."""
        structured_text = []
        text, quotes = self.get_quotes(text)  # Extract quotes first
        paragraphs = self.get_paragraphs(text)

        for block in paragraphs:
            sentences = self.get_sentences(block, quotes)  # Pass quotes
            structured_text.append([self.get_words(sentence) for sentence in sentences])

        return structured_text


# Example Usage
if __name__ == "__main__":
    from argparse import ArgumentParser

    from text.grammar import TextUnicode

    parser = ArgumentParser()
    parser.add_argument("--file", default="data/owl.md", help="The plain text corpus to be parsed.")
    args = parser.parse_args()

    text = TextUnicode.read_and_normalize(args.file)

    parser = TextParser()
    output = parser.parse(text)
    for i, paragraph in enumerate(output):
        print(f"Paragraph {i}")
        for j, sentence in enumerate(paragraph):
            print(f"Sentence {j}: {sentence}")
