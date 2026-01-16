# agent/text/smoke.py
"""
Copyright (C) 2023 Austin Berrio

Description: Runs a smoke test on a generated dataset to detect discrepancies and determine max sequence length.

Discrepancies include:
- Extremely short sequences (≤ 3 characters).
- Sequences beginning/ending with a quote or apostrophe.
- Sequences starting with a terminal symbol.
- Unusual tokenization issues.

It also computes the **maximum sequence length** across all input-target pairs.
"""

import argparse
import json
import logging
import re
from typing import Dict, List

TERMINALS = {".", "!", "?", "‼", "‽", "⁇", "⁈", "⁉"}
# Matches common contractions (e.g., "don't", "I'll", "it's")
CONTRACTIONS = re.compile(r"\b(?:n't|'s|'re|'m|'ve|'d|'ll|'am|'em)\b", re.IGNORECASE)


def load_dataset(filepath: str) -> List[Dict[str, str]]:
    """Load dataset from JSON file."""
    with open(filepath, "r", encoding="utf-8") as file:
        return json.load(file)


def validate_enclosed_quotes(sequence: str) -> bool:
    """
    Checks if a sequence has properly enclosed double and single quotes.

    - Ignores apostrophes used in contractions and possessives.
    - Ensures all opening quotes have closing counterparts.
    - Handles single quotes used for emphasis within double quotes.

    Returns:
        True  → Quotes are properly paired.
        False → Unmatched/missing quote detected.
    """
    quote_flag = False  # Tracks double quotes
    single_quote_flag = False  # Tracks single quotes

    i = 0
    while i < len(sequence):
        char = sequence[i]

        # Handle double quotes
        if char == '"':
            quote_flag = not quote_flag  # Toggle open/close state

        # Handle single quotes (only if it's not part of a contraction or possessive)
        elif char == "'":
            # If within a double-quoted section, treat as valid
            if quote_flag:
                pass  # Ignore single quotes inside double quotes
            elif i > 0 and sequence[i - 1].isalpha():
                match = CONTRACTIONS.match(sequence[i:])
                if match:
                    i += len(match.group()) - 1  # Skip over contraction
                # If it's part of a possessive noun (e.g., John's)
                elif i + 1 < len(sequence) and sequence[i + 1].isalpha():
                    pass  # Ignore possessive apostrophe
                # If it's a possessive apostrophe at the end of a word (e.g., "Jones'")
                elif i + 1 < len(sequence) and sequence[i - 1].isalpha():
                    pass  # Ignore possessives
                else:
                    single_quote_flag = not single_quote_flag  # Toggle open/close state
            else:
                single_quote_flag = not single_quote_flag  # Toggle open/close state

        i += 1

    # True = All quotes are matched; False = Unmatched quote(s) detected.
    return not quote_flag and not single_quote_flag


def validate_pairs(dataset: List[Dict[str, str]]) -> List[str]:
    """
    Check dataset for common formatting discrepancies.

    Returns:
        List of warnings (if any).
    """
    warnings = []
    for idx, pair in enumerate(dataset):
        input_text = pair["input"].strip()
        target_text = pair["target"].strip()

        if len(input_text) <= 3 or len(target_text) <= 3:
            warnings.append(f"Pair {idx}: Extremely short sequence detected.")
            warnings.append(f"Input {idx}: {input_text}")
            warnings.append(f"Target {idx}: {target_text}")

        if input_text[0] in TERMINALS:
            warnings.append(
                f"Pair {idx}: Input starts with a terminal symbol ({input_text[0]})."
            )

        if input_text[0] == "'" or target_text[0] == "'":
            warnings.append(f"Pair {idx}: Sequence begins with an apostrophe.")
            warnings.append(f"Input {idx}: {input_text}")
            warnings.append(f"Target {idx}: {target_text}")

        # Use validate_enclosed_quotes() for more accurate quote validation
        if not validate_enclosed_quotes(input_text):
            warnings.append(f"Pair {idx}: Input contains an unmatched quote.")
            warnings.append(f"Input {idx}: {input_text}")

        if not validate_enclosed_quotes(target_text):
            warnings.append(f"Pair {idx}: Target contains an unmatched quote.")
            warnings.append(f"Target {idx}: {target_text}")

    return warnings


def calc_max_seq(dataset: List[Dict[str, str]], tokenizer) -> int:
    """
    Calculate the maximum sequence length in dataset.
    - Ensures max length is power-of-2 aligned.
    """
    logging.info("Calculating the maximum sequence length.")
    max_seq = 0

    for pair in dataset:
        source = tokenizer.encode(pair["input"], add_bos=True)
        target = tokenizer.encode(pair["target"], add_eos=True)
        max_seq = max(len(source) + len(target), max_seq)

    # Log the real maximum sequence length
    logging.info(f"Calculated Maximum sequence length is {max_seq}")

    # Round up to nearest power of 2
    max_seq = 2 ** ((max_seq - 1).bit_length())

    # Log the recommended maximum sequence length
    logging.info(f"Recommended maximum sequence length set to {max_seq}")
    return max_seq


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Run a smoke test on a dataset.")
    parser.add_argument("--dataset", required=True, help="Path to dataset JSON file.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    return parser.parse_args()


def main():
    """Main execution flow."""
    args = parse_args()

    # Set up logging
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    logging.info("Loading dataset...")
    dataset = load_dataset(args.dataset)

    logging.info("Validating dataset...")
    issues = validate_pairs(dataset)
    if issues:
        logging.warning(f"{len(issues)} issues found:")
        for issue in issues:
            logging.warning(issue)
    else:
        logging.info("No issues found in dataset!")

    # Dummy tokenizer for now (replace with real tokenizer)
    class DummyTokenizer:
        def encode(self, text, add_bos=False, add_eos=False):
            return text.split()  # Simple token split for testing

    tokenizer = DummyTokenizer()
    max_seq = calc_max_seq(dataset, tokenizer)

    logging.info(f"Final Maximum Sequence Length: {max_seq}")


if __name__ == "__main__":
    main()
