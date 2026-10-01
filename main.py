"""Entry point: the CLI chat. Reads user input and hands it to the agent."""
import sys

import ollama

import config
from agent import run_agent_turn, warm_up



# Force UTF-8 output.
sys.stdout.reconfigure(encoding="utf-8")

DIM = "\033[2m"    # terminal escape code: dim text (used for thinking)
RESET = "\033[0m"  # back to normal text



# Print token callback
def render(kind, data):
    """Decide how each event from the agent looks on screen."""
    if kind == "loop":  # a model call starts: label it, then the reply streams in after it
        print(f"\n{DIM}[loop {data['iteration']}/{data['max']}]{RESET}")
        print("Assistant> ", end="", flush=True)
    elif kind == "thinking":
        print(f"{DIM}{data}{RESET}", end="", flush=True)
    elif kind == "content":
        print(data, end="", flush=True)
    elif kind == "stats":
        print(f"\n{DIM}[{data['tokens']} tokens, {data['rate']:.1f} tok/s]{RESET}")
    elif kind == "interrupted":
        print(f"\n{DIM}[interrupted]{RESET}")
    elif kind == "tool_call":
        print(f"{DIM}[tool call] {data['name']}({data['arguments']}){RESET}")
    elif kind == "tool_result":
        print(f"{DIM}[tool result] {data['result']}{RESET}")
    elif kind == "limit":
        print(f"{DIM}[stopped: reached the maximum of {config.MAX_ITERATIONS} loops]{RESET}")


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
        run_agent_turn(messages, think, render)  # runs the agentic loop; appends to messages


if __name__ == "__main__":
    main()
