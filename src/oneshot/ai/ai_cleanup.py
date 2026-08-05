import re

_TICKS_WITH_LANGUAGE_IDENTIFIER = re.compile(r"^```[a-zA-Z]*\n")
_TICKS_WITHOUT_LANGUAGE_IDENTIFIER = re.compile(r"^```")
_TRAILING_TICKS = re.compile(r"\n?```$")

def clean_llm_response(response: str | None) -> str:
    """Clean raw LLM output and return a trimmed, balanced result."""
    if response is None:
        return ""

    text = response.strip()
    if not text:
        return ""

    # squirrel away filename
    text, filename = _remove_filename_lines(text)
    # starting backticks
    if _TICKS_WITH_LANGUAGE_IDENTIFIER.match(text):
        text = _TICKS_WITH_LANGUAGE_IDENTIFIER.sub("", text, count=1)
    if _TICKS_WITHOUT_LANGUAGE_IDENTIFIER.match(text):
        text = _TICKS_WITHOUT_LANGUAGE_IDENTIFIER.sub("", text, count=1)
    # trailing backticks
    if _TRAILING_TICKS.search(text):
        text = _TRAILING_TICKS.sub("", text, count=1)
    # normalize brackets
    if text.startswith("[") or text.endswith("]"):
        if not text.startswith("["):
            text = f"[{text}"
        if not text.endswith("]"):
            text = f"{text}]"

    return f"{filename}{text.strip()}"


def _remove_filename_lines(text: str) -> tuple[str, str]:
    """Remove metadata lines starting with FILENAME:."""
    lines = text.split("\n")
    res = []
    filename = ""
    for line in lines:
        if line.startswith("FILENAME:"):
            filename = f"{line}\n"
            continue
        res.append(line)
    return "\n".join(res).strip(), filename
