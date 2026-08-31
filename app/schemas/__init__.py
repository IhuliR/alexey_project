from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OrmSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    username: str
    password: str
    email: str = ''


class RegisteredUser(OrmSchema):
    email: str
    username: str
    id: int


class CurrentUserRead(OrmSchema):
    id: int
    username: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str
    re_new_password: str


class TokenObtain(BaseModel):
    username: str
    password: str


class TokenPair(BaseModel):
    refresh: str
    access: str


class TokenRefresh(BaseModel):
    refresh: str


class TokenVerify(BaseModel):
    token: str


class AccessToken(BaseModel):
    access: str


class DocumentRead(OrmSchema):
    id: int
    user: int = Field(validation_alias='user_id')
    title: str
    slug: str
    original_filename: str
    content: str
    created_at: datetime


class PaginatedDocuments(BaseModel):
    count: int
    next: str | None
    previous: str | None
    results: list[DocumentRead]


class ChunkPage(BaseModel):
    document_id: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool
    total_chunks: int
    chunk: list[str]
    chunk_index: int | None
    chunk_start: int | None
    chunk_end: int | None


class LabelWrite(BaseModel):
    name: str
    color: str = '#ffff00'


class LabelPatch(BaseModel):
    name: str = ''
    color: str = '#ffff00'


class LabelRead(OrmSchema):
    id: int
    name: str
    color: str


class AnnotationWrite(BaseModel):
    document: int
    label: int
    start: int
    end: int


class AnnotationPatch(BaseModel):
    document: int = 0
    label: int = 0
    start: int = 0
    end: int = 0


class AnnotationRead(OrmSchema):
    id: int
    document: int = Field(validation_alias='document_id')
    label: int = Field(validation_alias='label_id')
    start: int
    end: int
    text: str
    created_at: datetime
