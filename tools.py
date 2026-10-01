"""The tools the model can use. Each tool has two halves: a function and a schema."""
import random
from datetime import datetime


# --- The functions: ordinary Python that we run when the model asks ---
# Bad input returns an error string (it does not raise), so the model can read it and retry.

def get_current_time():
    return datetime.now().strftime("%A, %d %B %Y, %H:%M:%S")


def add(a, b):
    return a + b


def multiply(a, b):
    return a * b


def divide(a, b):
    if b == 0:
        return "Error: cannot divide by zero."
    return a / b


def roll_dice(sides=6, count=1):
    if sides < 2 or not 1 <= count <= 100:
        return "Error: sides must be at least 2 and count must be between 1 and 100."
    rolls = [random.randint(1, sides) for _ in range(count)]
    return f"Rolled {count}d{sides}: {rolls}, total {sum(rolls)}"


def random_number(minimum, maximum):
    if minimum > maximum:
        return "Error: minimum must not be greater than maximum."
    return random.randint(minimum, maximum)


# Counters and memories live in these dictionaries, so they last as long as the program runs.
COUNTERS = {}
MEMORY = {}


def change_counter(name, amount):
    COUNTERS[name] = COUNTERS.get(name, 0) + amount  # a new counter starts at 0
    return f"{name} is now {COUNTERS[name]}"


def get_counter(name):
    if name not in COUNTERS:
        return f"Error: no counter named '{name}'. Existing counters: {list(COUNTERS) or 'none'}"
    return f"{name} is {COUNTERS[name]}"


def remember(key, value):
    MEMORY[key.strip().lower()] = value  # lowercase so "Pixel" and "pixel" are the same key
    return f"Remembered {key}: {value}"


def recall(key):
    value = MEMORY.get(key.strip().lower())
    if value is None:
        return f"Error: nothing remembered under '{key}'. Known keys: {list(MEMORY) or 'none'}"
    return f"{key}: {value}"


# --- The schemas: the description of each tool that the model reads ---
# The model never sees the Python above, only this text. The description is
# how it decides whether and when to call the tool.

def _schema(func, description, properties=None, required=()):
    """Build one tool's schema. `properties` maps each argument name to its type and meaning."""
    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties or {},
                "required": list(required),  # arguments the model must always supply
            },
        },
    }


TOOLS = [
    _schema(get_current_time,
            "Get the current local date and time."),
    _schema(add, "Add two numbers.",
            {"a": {"type": "number", "description": "first number"},
             "b": {"type": "number", "description": "second number"}},
            required=["a", "b"]),
    _schema(multiply, "Multiply two numbers.",
            {"a": {"type": "number", "description": "first number"},
             "b": {"type": "number", "description": "second number"}},
            required=["a", "b"]),
    _schema(divide, "Divide a by b.",
            {"a": {"type": "number", "description": "the number to divide"},
             "b": {"type": "number", "description": "the number to divide by"}},
            required=["a", "b"]),
    _schema(roll_dice,
            "Roll dice and return each roll and the total. Always use this for dice; never invent rolls.",
            {"sides": {"type": "integer", "description": "number of sides on each die, default 6"},
             "count": {"type": "integer", "description": "how many dice to roll, default 1"}}),
    _schema(random_number,
            "Pick a random whole number between minimum and maximum, inclusive.",
            {"minimum": {"type": "integer", "description": "lowest possible value"},
             "maximum": {"type": "integer", "description": "highest possible value"}},
            required=["minimum", "maximum"]),
    _schema(change_counter,
            "Add to a named counter, such as a character's hit points or a score. "
            "Use a negative amount to subtract. A new counter starts at 0.",
            {"name": {"type": "string", "description": "counter name, e.g. 'goblin hp'"},
             "amount": {"type": "integer", "description": "amount to add (negative to subtract)"}},
            required=["name", "amount"]),
    _schema(get_counter,
            "Read the current value of a named counter.",
            {"name": {"type": "string", "description": "counter name"}},
            required=["name"]),
    _schema(remember,
            "Store a fact under a key so it can be recalled later, such as a character or NPC detail.",
            {"key": {"type": "string", "description": "what the fact is about, e.g. 'innkeeper name'"},
             "value": {"type": "string", "description": "the fact to store"}},
            required=["key", "value"]),
    _schema(recall,
            "Look up a previously remembered fact by its key.",
            {"key": {"type": "string", "description": "what the fact is about, e.g. 'innkeeper name'"}},
            required=["key"]),
]

# Lookup from the name the model writes to the function we run.
REGISTRY = {f.__name__: f for f in [
    get_current_time, add, multiply, divide, roll_dice, random_number,
    change_counter, get_counter, remember, recall,
]}


def run_tool(name, arguments):
    """Run the tool the model asked for and return its result as a string.

    Errors are returned as text, not raised, so the model can read them and try again.
    """
    func = REGISTRY.get(name)
    if func is None:
        return f"Error: unknown tool '{name}'. Available tools: {', '.join(REGISTRY)}"
    try:
        return str(func(**arguments))
    except TypeError as e:  # wrong or missing arguments
        return f"Error: bad arguments for {name}: {e}"
    except Exception as e:
        return f"Error while running {name}: {e}"
