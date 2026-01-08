import logging
import sys


class _SafeExtraFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        record.doc_id = getattr(record, "doc_id", "-")
        record.client_id = getattr(record, "client_id", "-")
        record.server_seq = getattr(record, "server_seq", "-")
        return super().format(record)


def configure_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    formatter = _SafeExtraFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s doc_id=%(doc_id)s client_id=%(client_id)s server_seq=%(server_seq)s",
    )
    handler.setFormatter(formatter)

    root.setLevel(logging.INFO)
    root.addHandler(handler)
