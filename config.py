"""Configuration"""

MODEL = "qwen3.5:4b"  # must match a name shown by `ollama list`
NUM_CTX = 4096        # context window in tokens; Ollama silently truncates beyond this
THINK = False         # show the model's reasoning? True is much slower on a CPU
TEMPERATURE = 0.5     # randomness of token choice; lower is steadier, which helps tool calls
MAX_ITERATIONS = 5    # most model calls allowed per user message (stops runaway loops)
KEEP_ALIVE = "30m"   # how long Ollama keeps the model in RAM after a request (default is 5m)

SYSTEM_PROMPT = (
    "You are an assistant for a tabletop role-playing game. "
    "Use your tools for dice rolls, random numbers, arithmetic, tracking counters and remembering facts "
    "instead of guessing. Keep answers concise."
)
