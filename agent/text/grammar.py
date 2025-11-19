"""
Module: agent.text.grammar
Description: Defines the rules for parsing English text.

BNF Grammar for English (WIP)
=============================
<document> ::= <paragraph>+
<paragraph> ::= <sentence>+
<sentence> ::= <clause> <terminator> | <quote> | <single-quote>
<quote> ::= '"' <sentence>+ '"'
<single-quote> ::= "'" <sentence>+ "'"
<clause> ::= <expression> (',' <expression>)*
<expression> ::= <phrase> | <expression> <conjunction> <expression>
<phrase> ::= <word> | <number> | <possession> | <contraction> | <prepositional-phrase> | <phrase> <punctuation> <phrase>
<possession> ::= <word> "'s" | <word> "s'" | <word> "'" <sentence> "'"
<contraction> ::= <contracted-form> | "'" <word>
<number> ::= <digit>+ | <digit>+ '.' <digit>*
<word> ::= [a-zA-Z]+
<punctuation> ::= ',' | ';' | ':' | '-' | '(' <expression> ')' | '[' <expression> ']' | '{' <expression> '}'
<conjunction> ::= 'and' | 'or' | 'but' | 'because'
<preposition> ::= 'in' | 'on' | 'at' | 'between' | 'with' | 'under' | 'over' | 'into' | 'through'
<terminator> ::= '.' | '?' | '!'
<contracted-form> ::= <word> "'" <contraction-suffix>
<contraction-suffix> ::= 'm' | 're' | 've' | 'll' | 'd' | 's' | 't'
<digit> ::= '0' | '1' | '2' | '3' | '4' | '5' | '6' | '7' | '8' | '9'
"""

import string
import unicodedata

import regex as re


class TextPattern:
    # Enable reusable expressions
    PARAGRAPH = r"\n{2,}"
    SENTENCE = r"(?<!\b(?:Dr|Mr|Ms|etc|vs|p|a)\.)([.!?])(\s+|$)"
    WORD = rf"\w+(?:'\w+)?|\d+(?:\.\d+)?|[{re.escape(string.punctuation)}]+"

    # Enable compiling reusable expressions
    def __call__(self, attr: str) -> re.Pattern:
        try:
            return re.compile(getattr(self, attr.upper()))
        except AttributeError:
            print(f"TextPattern has no attribute named {attr}.")

    @staticmethod
    def _normalize_newlines(text: str) -> str:
        """Normalize newlines while preserving paragraph breaks."""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
        return text.lstrip("\ufeff")  # Remove BOM if present

    @staticmethod
    def _normalize_unicode(text: str) -> str:
        """Apply Unicode normalization and replace fancy punctuation with ASCII."""
        quotes = {"‘": "'", "’": "'", "“": '"', "”": '"'}
        text = unicodedata.normalize("NFKC", text)
        for old, new in quotes.items():
            text = text.replace(old, new)
        return text

    def normalize_read(self, file: str) -> str:
        # === Read and Parse the File ===
        with open(file, "r", encoding="utf-8") as file:
            text = file.read().strip()
        text = self._normalize_unicode(text)
        text = self._normalize_newlines(text)
        return text

    def tokenize(self, text: str, mode: str) -> list[str]:
        if mode == "paragraph":
            return [p.strip() for p in self("paragraph").split(text) if p.strip()]

        if mode == "sentence":
            sent_re = self("sentence")
            out = []
            start = 0

            for m in sent_re.finditer(text):
                end = m.end(1)  # include terminator
                chunk = text[start:end].strip()
                if chunk:
                    out.append(chunk)
                start = m.end()

            # trailing fragment?
            tail = text[start:].strip()
            if tail:
                out.append(tail)
            return out

        if mode == "word":
            return self("word").findall(text)

        raise ValueError(f"Invalid mode given: {mode}")


# Example usage in main script
if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument(
        "--file",
        type=str,
        required=True,
        help="The plain text corpus to be parsed.",
    )
    parser.add_argument(
        "--mode",
        choices=["word", "sentence", "paragraph"],
        default="paragraph",
        help="Split text by word, sentence, or paragraph.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
    )
    args = parser.parse_args()

    pattern = TextPattern()

    text = pattern.normalize_read(args.file)
    paragraphs = pattern.tokenize(text, args.mode)

    # Debug Output
    for i, split in enumerate(paragraphs[: args.top_n]):
        print(f"Paragraph {i+1}: {repr(split)}")
