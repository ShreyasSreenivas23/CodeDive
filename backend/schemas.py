from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    url: str = Field(..., min_length=1, examples=["https://github.com/user/project"])


class AnalyzeResponse(BaseModel):
    status: str
    repository_id: str
    repository: str
    owner: str
    files: int
    chunks: int
    message: str


class ChatRequest(BaseModel):
    repository_id: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)


class SourceReference(BaseModel):
    file: str
    start_line: int | None = None
    end_line: int | None = None


class ChatResponse(BaseModel):
    answer: str
    repository_id: str
    sources: list[SourceReference]


class RepositorySummary(BaseModel):
    repository_id: str
    owner: str
    repository: str
    url: str
    files: int
    chunks: int
    indexed_at: str
