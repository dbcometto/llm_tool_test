"""Entry point: the CLI chat. Reads user input and hands it to the agent."""
import sys

import ollama

import config
from agent import stream_reply, warm_up



# Force UTF-8 output.
sys.stdout.reconfigure(encoding="utf-8")

DIM = "\033[2m"    # terminal escape code: dim text (used for thinking)
RESET = "\033[0m"  # back to normal text



# Print token callback
def render(kind, data):
    """Decide how each event from the agent looks on screen."""
    if kind == "thinking":
        print(f"{DIM}{data}{RESET}", end="", flush=True)
    elif kind == "content":
        print(data, end="", flush=True)
    elif kind == "stats":
        print(f"\n{DIM}[{data['tokens']} tokens, {data['rate']:.1f} tok/s]{RESET}", end="")
    elif kind == "interrupted":
        print(f"\n{DIM}[interrupted]{RESET}", end="")


# Main loop
def main():
    think = config.THINK
    messages = [{"role": "system", "content": config.SYSTEM_PROMPT}]

    # Status Info
    print(f"Model: {config.MODEL} | thinking: {think} | commands: /think, /quit")

    # Load the model before first question
    print("Loading model...", end="", flush=True)
    try:
        warm_up(messages)
    except ConnectionError:
        print("\nCould not reach Ollama. Is it running? (start the app, or run `ollama serve`)")
        return
    except ollama.ResponseError as e:  # e.g. model name not found
        print(f"\nOllama returned an error: {e.error}. Check MODEL in config.py against `ollama list`.")
        return
    except KeyboardInterrupt:
        print("\n[cancelled]")
        return
    print(" ready.")

    # Main Loop
    while True:
        # Get input from user
        try:
            user_text = input("\nYou> ").strip()
        except (EOFError, KeyboardInterrupt):  # Ctrl+Z / Ctrl+C at the prompt
            break

        # Handle Input
        if not user_text:
            continue
        if user_text == "/quit":
            break
        if user_text == "/think":
            think = not think
            print(f"thinking: {think}")
            continue

        # Interact with model
        messages.append({"role": "user", "content": user_text})
        print("\nAssistant> ", end="", flush=True)

        reply = stream_reply(messages, think, render)
        print()  # end the output line

        if reply["content"]:
            messages.append(reply)


if __name__ == "__main__":
    main()
