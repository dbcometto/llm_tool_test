"""Definition of the agentic loop. No printing here; it reports through `emit` (see main.py)."""
import ollama

import config
from tools import TOOLS, run_tool

# Defined once and used for every request. If the warm-up and the real calls
# used different options, Ollama would reload the model and the warm-up would be wasted.
OPTIONS = {"num_ctx": config.NUM_CTX, "temperature": config.TEMPERATURE}


def warm_up(messages):
    """Load the model into RAM and process the starting prompt, before the user types.

    Asks for at most 1 token, so it returns almost immediately after loading.
    """
    ollama.chat(
        model=config.MODEL,
        messages=messages,
        tools=TOOLS,  # same tools as real calls, so the cached prompt prefix matches
        options={**OPTIONS, "num_predict": 1},  # same options, plus: generate 1 token at most
        keep_alive=config.KEEP_ALIVE,
    )


def stream_reply(messages, think, emit):
    """One model call: send the conversation, report tokens as they arrive.

    Returns (message, interrupted). The message is ready to append to the history
    and includes "tool_calls" if the model asked for any.
    """

    # Interact with model (returns generator)
    stream = ollama.chat(
        model=config.MODEL,
        messages=messages,
        tools=TOOLS,                          # the tool descriptions the model can choose from
        stream=True,                          # yield small chunks instead of one big reply
        think=think,                          # ask the model to expose its reasoning (or not)
        options=OPTIONS,                      # context window size, temperature
        keep_alive=config.KEEP_ALIVE,         # each request resets the unload timer
    )

    content = ""      # the answer text, accumulated chunk by chunk
    thinking = ""     # the reasoning text, accumulated the same way
    tool_calls = []   # tool requests; they arrive as whole objects inside chunks
    last = None       # the final chunk carries timing statistics
    interrupted = False

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
            if chunk.message.tool_calls:
                tool_calls.extend(chunk.message.tool_calls)

    except KeyboardInterrupt:
        # Stop generating but keep what arrived so far; it still goes into history.
        interrupted = True
        emit("interrupted", None)
        if content:
            # Tell the model its reply was cut off, so it doesn't treat it as complete.
            content += " [interrupted by user]"

    if last and last.eval_count and last.eval_duration:
        rate = last.eval_count / (last.eval_duration / 1e9)  # duration is in nanoseconds
        emit("stats", {"tokens": last.eval_count, "rate": rate})

    # Only the answer goes into history, not the thinking.
    message = {"role": "assistant", "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return message, interrupted


def run_agent_turn(messages, think, emit):
    """The agentic loop: handle one user message, which may take several model calls.

    Appends everything that happens (assistant replies, tool results) to `messages`.
    `emit(kind, data)` receives, besides the kinds from stream_reply:
        ("loop", dict)         a model call is starting (iteration and maximum)
        ("tool_call", dict)    the model asked for a tool (name, arguments)
        ("tool_result", dict)  what the tool returned (name, result)
        ("limit", None)        stopped because MAX_ITERATIONS was reached
    """
    for iteration in range(1, config.MAX_ITERATIONS + 1):
        emit("loop", {"iteration": iteration, "max": config.MAX_ITERATIONS})

        reply, interrupted = stream_reply(messages, think, emit)

        if interrupted:
            # Don't act on a request that was cut off; keep only the partial text.
            reply.pop("tool_calls", None)
            if reply["content"]:
                messages.append(reply)
            return

        if reply["content"] or reply.get("tool_calls"):
            messages.append(reply)

        # No tool calls means the model has finished its answer.
        if not reply.get("tool_calls"):
            return

        # Otherwise run each requested tool and feed the results back.
        for call in reply["tool_calls"]:
            name = call.function.name
            arguments = call.function.arguments
            emit("tool_call", {"name": name, "arguments": arguments})

            result = run_tool(name, arguments)
            emit("tool_result", {"name": name, "result": result})

            messages.append({"role": "tool", "tool_name": name, "content": result})
        # ...and loop: the model is called again and sees the results.

    emit("limit", None)
