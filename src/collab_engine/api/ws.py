import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from collab_engine.core.protocol.messages import (
    ClientHello,
    ClientOp,
    ServerHelloAck,
    ServerOpEcho,
    ServerResync,
    parse_client_message,
)
from collab_engine.persistence.memory import InMemoryPersistence
from collab_engine.services.document_service import DocumentService
from collab_engine.session.session_manager import Connection, SessionManager

logger = logging.getLogger(__name__)

router = APIRouter()

_persistence = InMemoryPersistence()
_document_service = DocumentService(persistence=_persistence)
_sessions = SessionManager()


@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()

    conn: Connection | None = None
    writer_task: asyncio.Task[None] | None = None
    doc_id: str | None = None
    client_id: str | None = None

    try:
        raw = await websocket.receive_text()
        try:
            msg = parse_client_message(raw)
        except Exception:
            await websocket.close(code=1002, reason="protocol: invalid hello")
            return
        if not isinstance(msg, ClientHello):
            await websocket.close(code=1002, reason="protocol: first message must be hello")
            return

        doc_id = msg.doc_id
        client_id = msg.client_id
        logger.info("ws hello", extra={"doc_id": doc_id, "client_id": client_id})

        conn = Connection(websocket=websocket, client_id=msg.client_id)
        writer_task = asyncio.create_task(conn.writer_loop())

        await _sessions.join(doc_id=msg.doc_id, connection=conn)

        current_seq = _document_service.get_server_seq(doc_id=msg.doc_id)
        hello_ack = ServerHelloAck(doc_id=msg.doc_id, server_seq=current_seq)
        await conn.send_json(hello_ack.model_dump())

        if msg.last_seen_server_seq and msg.last_seen_server_seq > 0 and msg.last_seen_server_seq < current_seq:
            logger.info(
                "ws replay start",
                extra={"doc_id": doc_id, "client_id": client_id, "server_seq": current_seq},
            )
            replay = _persistence.get_ops_since(doc_id=msg.doc_id, since_server_seq=msg.last_seen_server_seq)
            if replay is not None and len(replay) <= 500:
                for rec in replay:
                    await conn.send_json(
                        ServerOpEcho(
                            doc_id=msg.doc_id,
                            server_seq=rec.server_seq,
                            origin_client_id=rec.origin_client_id,
                            client_msg_id=rec.client_msg_id,
                            op=rec.op,
                        ).model_dump()
                    )
                logger.info(
                    "ws replay done",
                    extra={"doc_id": doc_id, "client_id": client_id, "server_seq": current_seq},
                )
            else:
                full_text, server_seq = _document_service.get_snapshot(doc_id=msg.doc_id)
                logger.info(
                    "ws resync (replay unavailable)",
                    extra={"doc_id": doc_id, "client_id": client_id, "server_seq": server_seq},
                )
                await conn.send_json(ServerResync(doc_id=msg.doc_id, server_seq=server_seq, full_text=full_text).model_dump())
        else:
            full_text, server_seq = _document_service.get_snapshot(doc_id=msg.doc_id)
            logger.info(
                "ws resync",
                extra={"doc_id": doc_id, "client_id": client_id, "server_seq": server_seq},
            )
            await conn.send_json(ServerResync(doc_id=msg.doc_id, server_seq=server_seq, full_text=full_text).model_dump())

        while True:
            raw = await websocket.receive_text()
            try:
                client_msg = parse_client_message(raw)
            except Exception:
                logger.warning(
                    "ws protocol violation: invalid message",
                    extra={"doc_id": doc_id or "-", "client_id": client_id or "-"},
                )
                await websocket.close(code=1002, reason="protocol: invalid message")
                return

            if isinstance(client_msg, ClientOp):
                if doc_id is None or client_msg.doc_id != doc_id:
                    logger.warning(
                        "ws protocol violation: doc_id mismatch",
                        extra={"doc_id": doc_id or "-", "client_id": client_id or "-"},
                    )
                    await websocket.close(code=1008, reason="protocol: doc_id mismatch")
                    return

                if client_id is None or client_msg.client_id != client_id:
                    logger.warning(
                        "ws protocol violation: client_id mismatch",
                        extra={"doc_id": doc_id or "-", "client_id": client_id or "-"},
                    )
                    await websocket.close(code=1008, reason="protocol: client_id mismatch")
                    return

                server_seq = await _document_service.apply_op(
                    doc_id=client_msg.doc_id,
                    origin_client_id=client_msg.client_id,
                    client_msg_id=client_msg.client_msg_id,
                    op=client_msg.op,
                )

                logger.info(
                    "op integrated",
                    extra={"doc_id": doc_id, "client_id": client_id, "server_seq": server_seq},
                )

                echo = ServerOpEcho(
                    doc_id=client_msg.doc_id,
                    server_seq=server_seq,
                    origin_client_id=client_msg.client_id,
                    client_msg_id=client_msg.client_msg_id,
                    op=client_msg.op,
                )
                await _sessions.broadcast(doc_id=client_msg.doc_id, message=echo.model_dump())
            else:
                logger.warning(
                    "ws protocol violation: unexpected message type",
                    extra={"doc_id": doc_id or "-", "client_id": client_id or "-"},
                )
                await websocket.close(code=1003, reason="protocol: unexpected message type")
                return

    except WebSocketDisconnect:
        logger.info("ws disconnect", extra={"doc_id": doc_id or "-", "client_id": client_id or "-"})
    except Exception:
        logger.exception("ws error", extra={"doc_id": doc_id or "-", "client_id": client_id or "-"})
        try:
            await websocket.close(code=1011, reason="internal error")
        except Exception:
            pass
    finally:
        if conn is not None:
            await _sessions.leave_any(connection=conn)
            conn.close()
        if writer_task is not None:
            writer_task.cancel()
