# Notes

## Status: 1 Oct 26 / Stage 1-2 done (chat + agentic loop + toy tools)

### Files
- `main.py`: UI. Chat loop, `/think` and `/quit`, `render()` (the only place that prints), model warm-up with error handling.
- `agent.py`: no printing. `stream_reply()` = one model call; `run_agent_turn()` = the agentic loop. Reports everything through `emit(kind, data)` callback.
- `tools.py`: tool functions + schemas (`TOOLS`) + `REGISTRY` + `run_tool()`.
- `config.py`: model, `NUM_CTX`, `THINK`, `TEMPERATURE`, `MAX_ITERATIONS`, `KEEP_ALIVE`, system prompt.

### Concepts
- Two loops: chat loop (once per user message, in main.py) vs agentic loop (once per model call, in agent.py). Model stops looping by making no tool calls; `MAX_ITERATIONS` is the backstop.
- The model only emits tokens. Tool calls are generated text; Ollama's `RENDERER`/`PARSER qwen3.5` (see `ollama show --modelfile`) build the prompt and split the output into `thinking` / `content` / `tool_calls`.
- Roles: `system`, `user`, `assistant`, `tool` (industry convention, not Ollama-specific). Tool result = `{"role": "tool", "tool_name": ..., "content": ...}`.
- Streaming: `stream=True` returns a generator; `print(..., end="", flush=True)` makes it appear live.
- A tool = function (we run it) + schema (the only thing the model sees). Description wording drives when it gets called.
- Errors are returned to the model as tool-result text, never raised.
- History is the model's only memory and is resent every call, so it grows (context + speed cost).

### Decisions
- Turn-based loop. Considered "agent calls a wait-for-user tool"; deferred (small model might never yield). Possible hybrid later: implicit wait + optional `ask_user`.
- Ctrl+C mid-reply keeps the partial text, tagged ` [interrupted by user]`; any tool calls in the cut-off reply are dropped, not run.
- Warm-up request at startup (`num_predict: 1`). `OPTIONS` must be identical in warm-up and real calls or Ollama reloads the model. `keep_alive` 30m (default unloads after 5m).
- `temperature` 0.5 (model default is 1) for steadier tool calls.
- Docker/sandboxing deferred until file tools exist.

### Tools (tabletop theme)
`get_current_time`, `add`, `multiply`, `divide`, `roll_dice`, `random_number`, `change_counter`, `get_counter`, `remember`, `recall`. Counters and memory are in-process dicts (lost on exit).

### Things to watch / test
- Does the model send numbers as strings? (`"2" + "3"` would silently give `"23"`.)
- Tool choice with 10 tools; chaining (roll then add); remember then recall across turns.
- Ten schemas eat context on every call.
- Still missing: JSONL event log, error handling around chat calls in the main loop (only warm-up is guarded), handling Ctrl+C during a slow tool.
- `requirements.txt` is UTF-16 (PowerShell `>`); regenerate with `Out-File -Encoding utf8` if pip complains.

### Next
Run the experiments above, give feedback, then document in CLAUDE.md; later: file tools with path sandboxing, the librarian itself.



## Status: 1 Oct 26 / 0955

Project started.


Qwen3.5:4b test:

```bash
PS C:\Users\benja> ollama list
NAME          ID              SIZE      MODIFIED
qwen3.5:4b    2a654d98e6fb    3.4 GB    6 weeks ago
PS C:\Users\benja> ollama run qwen3.5:4b --verbose
>>> Hi, how are you today?
Thinking...
Thinking Process:

1.  **Analyze the Request:**
    *   Input: "Hi, how are you today?"
    *   Intent: Greeting and inquiry about well-being.
    *   Tone: Friendly, casual.
    *   Role: AI Assistant.

2.  **Determine Appropriate Response:**
    *   Acknowledge the greeting ("Hi!".)
    *   Address the "how are you" question (as an AI).
        *   Option A: Lie about feeling (e.g., "I'm great!"). -> Avoid personal feelings, but can use personified
language.
        *   Option B: State functional status (e.g., "Operating normally."). -> Too robotic.
        *   Option C: Polite AI response (e.g., "Doing well, thank you! How about you?"). -> Best balance of
friendliness and accuracy.
    *   Offer assistance ("How can I help?").

3.  **Drafting the Response:**
    *   "Hi there! I'm doing great, thanks for asking." (A bit too simple)
    *   "Hello! I'm functioning well and ready to chat with you today." -> Better clarity on capabilities.
    *   Let's go for a warm, helpful tone: "Hi! I'm doing well, thank you. How about you? Is there anything
specific I can help you with today?"

4.  **Refining the Response:**
    *   Make it sound natural.
    *   Ensure no false claims of consciousness (important nuance).
    *   Keep it concise.

    Draft: "Hi! Doing well, thanks for asking. How about you? Is there anything on your mind or something I can
help you with today?"

5.  **Final Polish:**
    *   Add a friendly emoji if appropriate (optional but nice).
    *   Ensure the response is safe and neutral regarding time/location/etc. since I don't have personal
experiences in this chat context beyond system instructions.

6.  **Selected Output:** "Hi! I'm doing well, thank you for asking. How about you? Is there anything I can help
you with today?" (Simple, polite, invites further interaction).

    *Self-Correction during thought:* Actually, as an AI, it's often better to frame the answer as ready and
helpful rather than implying a state of "being". But people expect a conversational feel. Let's keep it friendly
but clear about my purpose.

    Revised: "Hi there! I'm doing well. How are you? Is there anything interesting or important going on in your
day that I can help with?" (Wait, let's make sure not to assume too much context).

    Final choice: "Hello! I'm doing very well—thanks for asking. And how about you? Anything specific on your mind
today, or do you need any help getting started?"

7.  **Final Decision:** Keep it warm and open-ended.

    *Response:* "Hi there! I'm doing well, thank you. How are things with you? Is there anything specific I can
help you work on today?"
...done thinking.

Hi there! I am doing well—thanks for asking.

How about you? Anything exciting going on in your day, or is there something specific you'd like to tackle
together?

total duration:       1m44.0187577s
load duration:        256.5482ms
prompt eval count:    17 token(s)
prompt eval duration: 558.639ms
prompt eval rate:     30.43 tokens/s
eval count:           709 token(s)
eval duration:        1m43.178204s
eval rate:            6.87 tokens/s
```

```bash
PS C:\Users\benja> ollama ps
NAME          ID              SIZE      PROCESSOR    CONTEXT    UNTIL
qwen3.5:4b    2a654d98e6fb    3.1 GB    100% CPU     4096       3 minutes from now
```

Takeaways: CPU only, ~7 tok/s. Thinking is the main cost (~700 tokens to say hi, 1m44s). Default context is 4096 (Ollama truncates silently).


