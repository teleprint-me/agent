"""
Script: agent.__main__
"""

import requests


def ask_local_model(
    prompt,
    system="You are a helpful assistant.",
    base_url="http://localhost:8080/v1/chat/completions",
):
    payload = {
        "model": "qwen3",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 256,
        "stream": False,
    }

    response = requests.post(base_url, json=payload)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def main():
    print("Ask your local agent a question (Ctrl+C to quit):")
    try:
        while True:
            query = input("> ")
            response = ask_local_model(query)
            print(f"\nAssistant:\n{response}\n")
    except KeyboardInterrupt:
        print("\nExiting.")


if __name__ == "__main__":
    main()
