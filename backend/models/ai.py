from pydantic import BaseModel, Field
from typing import Literal

# Mirrors the LANGUAGES list in frontend/src/constants.ts. The model is forced
# to pick one of these so the result is always a valid option in LanguageSelect.
LanguageName = Literal[
    "BASH", "C", "C++", "C#", "CSS", "DART", "DOCKER",
    "GO", "GRAPHQL", "HTML", "JAVA", "JAVASCRIPT", "JSON",
    "KOTLIN", "LUA", "MARKDOWN", "MATLAB", "PHP", "PYTHON",
    "R", "RUBY", "RUST", "SCALA", "SQL", "SWIFT",
    "TERRAFORM", "TYPESCRIPT", "YAML",
]


class SnippetAnalyzeRequest(BaseModel):
    """Input for the AI auto-fill endpoint: just the raw pasted code."""
    code: str = Field(min_length=1, max_length=20000)


class SnippetMetadata(BaseModel):
    """Structured metadata the model extracts from a code snippet.

    This doubles as the JSON schema sent to the LLM (via response_format) and
    the API response, so the shape the model must return and the shape we hand
    back to the frontend can never drift apart.
    """
    title: str = Field(description="A short, specific title for the snippet (3-8 words).")
    language: LanguageName = Field(description="The programming language of the code.")
    description: str = Field(description="One concise sentence describing what the code does.")
    tags: list[str] = Field(description="2-5 short, lowercase topic tags (e.g. 'async', 'sorting').")
