import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import ChatMessage, ChatSession, Chunk, Document, ProcessingJob, Tenant, User


def seed(session: Session) -> tuple[Tenant, Tenant, User, Document]:
    first, second = Tenant(name="First"), Tenant(name="Second")
    session.add_all([first, second])
    session.flush()
    user = User(tenant_id=first.id, email="first@example.com", password_hash="test-hash")
    session.add(user)
    session.flush()
    document = Document(
        tenant_id=first.id,
        uploader_id=user.id,
        filename="test.txt",
        mime_type="text/plain",
        sha256="a" * 64,
        size_bytes=12,
        storage_key=f"{first.id}/{uuid.uuid4()}",
    )
    session.add(document)
    session.commit()
    return first, second, user, document


def test_document_cannot_reference_another_tenant_uploader(session: Session) -> None:
    _, second, user, _ = seed(session)
    session.add(
        Document(
            tenant_id=second.id,
            uploader_id=user.id,
            filename="leak.txt",
            mime_type="text/plain",
            sha256="b" * 64,
            size_bytes=1,
            storage_key="unique",
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()


@pytest.mark.parametrize("kind", ["chunk", "job"])
def test_child_cannot_reference_another_tenant_document(session: Session, kind: str) -> None:
    _, second, _, document = seed(session)
    if kind == "chunk":
        session.add(Chunk(tenant_id=second.id, document_id=document.id, chunk_index=0, text="x"))
    else:
        session.add(ProcessingJob(tenant_id=second.id, document_id=document.id))
    with pytest.raises(IntegrityError):
        session.commit()


def test_message_cannot_reference_another_tenant_session(session: Session) -> None:
    first, second, user, _ = seed(session)
    chat = ChatSession(tenant_id=first.id, user_id=user.id, title="Question")
    session.add(chat)
    session.commit()
    session.add(ChatMessage(tenant_id=second.id, session_id=chat.id, role="user", content="x"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_duplicate_document_hash_is_tenant_scoped(session: Session) -> None:
    first, second, user, document = seed(session)
    second_user = User(tenant_id=second.id, email="second@example.com", password_hash="test")
    session.add(second_user)
    session.flush()
    session.add(
        Document(
            tenant_id=second.id,
            uploader_id=second_user.id,
            filename="same.txt",
            mime_type="text/plain",
            sha256=document.sha256,
            size_bytes=12,
            storage_key="second",
        )
    )
    session.commit()
    session.add(
        Document(
            tenant_id=first.id,
            uploader_id=user.id,
            filename="duplicate.txt",
            mime_type="text/plain",
            sha256=document.sha256,
            size_bytes=12,
            storage_key="third",
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()


def test_invalid_document_state_rejected(session: Session) -> None:
    _, _, _, document = seed(session)
    document.status = "pretend_success"
    with pytest.raises(IntegrityError):
        session.commit()


def test_document_delete_cascades_chunks_and_job(session: Session) -> None:
    first, _, _, document = seed(session)
    chunk = Chunk(tenant_id=first.id, document_id=document.id, chunk_index=0, text="evidence")
    job = ProcessingJob(tenant_id=first.id, document_id=document.id)
    session.add_all([chunk, job])
    session.commit()
    chunk_id, job_id = chunk.id, job.id
    session.delete(document)
    session.commit()
    session.expunge_all()
    assert session.get(Chunk, chunk_id) is None
    assert session.get(ProcessingJob, job_id) is None
