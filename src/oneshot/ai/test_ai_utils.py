from src.oneshot.ai.ai_utils import clean_llm_response
import pytest

def test_clean_llm_response_removes_starting_code_block():
    response = "```python\nsome code here\n```"
    result = clean_llm_response(response)
    assert result == "some code here"


def test_clean_llm_response_plain_text_unchanged():
    response = "just plain text without code blocks"
    result = clean_llm_response(response)
    assert result == "just plain text without code blocks"


def test_clean_llm_response_no_language_marker():
    response = "```\nsome code here\n```"
    result = clean_llm_response(response)
    assert result == "some code here"
    assert not result.startswith("```")
    assert not result.endswith("```")


def test_clean_llm_response_multiline_code_block():
    response = "```json\n{\n  \"key\": \"value\"\n}\n```"
    result = clean_llm_response(response)
    assert result == "{\n  \"key\": \"value\"\n}"


def test_clean_llm_response_empty_string():
    response = ""
    result = clean_llm_response(response)
    assert result == ""


def test_clean_llm_response_leading_whitespace_before_code_block():
    # Leading whitespace prevents detection of code block
    response = "  ```python\ncode\n```"
    result = clean_llm_response(response)
    assert result == "code"

def test_clean_llm_response_only_opening_marker_no_trailing():
    # Only opening marker present, no trailing ``` - opening should be removed but nothing else
    response = "```python\nsome code here"
    result = clean_llm_response(response)
    assert result == "some code here"


def test_clean_llm_response_only_trailing_marker_no_opening():
    # Only trailing marker present, no opening ``` - trailing should be removed but nothing else
    response = "some code here\n```"
    result = clean_llm_response(response)
    assert result == "some code here"


def test_clean_llm_response_sql_language_marker():
    # Ensure other language markers are also stripped correctly
    response = "```sql\nSELECT * FROM table;\n```"
    result = clean_llm_response(response)
    assert result == "SELECT * FROM table;"
