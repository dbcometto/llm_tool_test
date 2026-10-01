"""Definition of the agentic loop: talking to the model. No printing here; see main.py."""
import ollama

import config

# Defined once and used for every request. If the warm-up and the real calls
# used different options, Ollama would reload the model and the warm-up would be wasted.
OPTIONS = {"num_ctx": config.NUM_CTX}


def warm_up(messages):
    """Load the model into RAM and process the starting prompt, before the user types.

    Asks for at most 1 token, so it returns almost immediately after loading.
    """
    ollama.chat(
        model=config.MODEL,
        messages=messages,
        options={**OPTIONS, "num_predict": 1},  # same options, plus: generate 1 token at most
        keep_alive=config.KEEP_ALIVE,
    )


def stream_reply(messages, think, emit):
    """Send the whole conversation to the model and report tokens as they arrive.

    `emit(kind, data)` is supplied by the caller (the UI). We call it with:
        ("thinking", text)  a reasoning token
        ("content", text)   an answer token
        ("stats", dict)     token count and speed, once generation finishes
        ("interrupted", None)  the user pressed Ctrl+C

    Returns the finished assistant message, ready to append to the history.
    """

    # Interact with model (returns generator)
    stream = ollama.chat(
        model=config.MODEL,
        messages=messages,
        stream=True,                          # yield small chunks instead of one big reply
        think=think,                          # ask the model to expose its reasoning (or not)
        options=OPTIONS,                      # context window size
        keep_alive=config.KEEP_ALIVE,         # each request resets the unload timer
    )

    content = ""   # the answer text, accumulated chunk by chunk
    thinking = ""  # the reasoning text, accumulated the same way
    last = None    # the final chunk carries timing statistics

    # Iterate through tokens
    try:
        for chunk in stream:
            last = chunk
            if chunk.message.thinking:
                thinking += chunk.message.thinking
                emit("thinking", chunk.message.thinking)
            if chunk.message.content:
                content += chunk.message.content
                emit("content", chunk.message.content)

    except KeyboardInterrupt:
        # Stop generating but keep what arrived so far; it still goes into history.
        emit("interrupted", None)
        if content:
            # Tell the model its reply was cut off, so it doesn't treat it as complete.
            content += " [interrupted by user]"

    if last and last.eval_count and last.eval_duration:
        rate = last.eval_count / (last.eval_duration / 1e9)  # duration is in nanoseconds
        emit("stats", {"tokens": last.eval_count, "rate": rate})

    # Only the answer goes into history, not the thinking.
    return {"role": "assistant", "content": content}
