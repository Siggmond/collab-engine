import json
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field


ElementId = tuple[int, str]


class InsertOp(BaseModel):
    type: Literal["ins"]
    parent_id: ElementId
    id: ElementId
    value: str = Field(min_length=1, max_length=1)


class DeleteOp(BaseModel):
    type: Literal["del"]
    id: ElementId


Op = Annotated[Union[InsertOp, DeleteOp], Field(discriminator="type")]


class ClientHello(BaseModel):
    type: Literal["hello"]
    doc_id: str = Field(min_length=1)
    client_id: str = Field(min_length=1)
    last_seen_server_seq: int = Field(default=0, ge=0)


class ClientOp(BaseModel):
    type: Literal["op"]
    doc_id: str = Field(min_length=1)
    client_id: str = Field(min_length=1)
    client_msg_id: str = Field(min_length=1)
    op: Op


ClientMessage = Union[ClientHello, ClientOp]


class ServerHelloAck(BaseModel):
    type: Literal["hello_ack"] = "hello_ack"
    doc_id: str
    server_seq: int


class ServerResync(BaseModel):
    type: Literal["resync"] = "resync"
    doc_id: str
    server_seq: int
    full_text: str


class ServerOpEcho(BaseModel):
    type: Literal["op_echo"] = "op_echo"
    doc_id: str
    server_seq: int
    origin_client_id: str
    client_msg_id: str
    op: Op


ServerMessage = Union[ServerHelloAck, ServerResync, ServerOpEcho]


def parse_client_message(raw_text: str) -> ClientMessage:
    data: Any = json.loads(raw_text)
    t = data.get("type")
    if t == "hello":
        return ClientHello.model_validate(data)
    if t == "op":
        return ClientOp.model_validate(data)
    raise ValueError(f"unknown message type: {t!r}")
