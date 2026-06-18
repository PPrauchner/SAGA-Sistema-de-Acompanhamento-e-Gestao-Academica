from __future__ import annotations

import io
from typing import Any

import pytest
from fastapi import HTTPException, UploadFile

from backend.app.core.auth import CurrentUser
from backend.app.repositories import storage_repository as storage_module
from backend.app.services import comprovante_service as comprovante_module
from backend.app.services.comprovante_service import (
    MAX_COMPROVANTE_SIZE_BYTES,
    ComprovanteService,
)


class _FakeBlob:
    def __init__(self) -> None:
        self.metadata: dict[str, str] | None = None
        self.uploaded: tuple[bytes, str | None] | None = None

    def upload_from_string(self, content: bytes, content_type: str | None = None) -> None:
        self.uploaded = (content, content_type)


class _FakeBucket:
    name = "test-bucket.appspot.com"

    def __init__(self) -> None:
        self.blobs: dict[str, _FakeBlob] = {}

    def blob(self, path: str) -> _FakeBlob:
        blob = _FakeBlob()
        self.blobs[path] = blob
        return blob


class _FakeStudentRepository:
    store: list[dict[str, Any]] = []

    async def list_all(self) -> list[dict[str, Any]]:
        return list(type(self).store)


class _FakeActivityRepository:
    # store[(student_id, activity_id)] = activity dict (None = não existe)
    store: dict[tuple[str, str], dict[str, Any]] = {}
    updates: list[tuple[str, str, dict[str, Any]]] = []

    async def get_activity(self, student_id: str, activity_id: str) -> dict[str, Any] | None:
        data = type(self).store.get((student_id, activity_id))
        return dict(data) if data else None

    async def update_activity(
        self, student_id: str, activity_id: str, data: dict[str, Any]
    ) -> None:
        type(self).updates.append((student_id, activity_id, dict(data)))


def _aluno() -> CurrentUser:
    return CurrentUser(uid="uid-aluno", role="aluno", programa_id="prog_default", email="a@x.com")


def _upload_file(
    content: bytes,
    filename: str,
    content_type: str,
    size: int | None = None,
) -> UploadFile:
    return UploadFile(
        file=io.BytesIO(content),
        size=size,
        filename=filename,
        headers={"content-type": content_type},
    )


@pytest.fixture(autouse=True)
def _setup(monkeypatch: pytest.MonkeyPatch) -> _FakeBucket:
    _FakeStudentRepository.store = [{"id": "student1", "uid": "uid-aluno"}]
    _FakeActivityRepository.store = {("student1", "act1"): {"id": "act1", "descricao": "x"}}
    _FakeActivityRepository.updates = []
    bucket = _FakeBucket()
    monkeypatch.setattr(comprovante_module, "StudentRepository", _FakeStudentRepository)
    monkeypatch.setattr(comprovante_module, "ActivityRepository", _FakeActivityRepository)
    monkeypatch.setattr(storage_module, "get_storage_bucket", lambda: bucket)
    return bucket


async def test_upload_persiste_no_bucket_e_devolve_url_tokenizada(
    _setup: _FakeBucket,
) -> None:
    service = ComprovanteService()

    result = await service.upload(
        "act1",
        _upload_file(b"%PDF-1.4 fake", "comprovante.pdf", "application/pdf"),
        _aluno(),
    )

    expected_path = "comprovantes/prog_default/student1/act1/comprovante.pdf"
    assert result["path_bucket"] == expected_path
    assert expected_path in _setup.blobs
    blob = _setup.blobs[expected_path]
    assert blob.uploaded == (b"%PDF-1.4 fake", "application/pdf")
    token = blob.metadata["firebaseStorageDownloadTokens"]
    assert result["comprovante_url"] == (
        f"https://firebasestorage.googleapis.com/v0/b/{_setup.name}/o/"
        f"comprovantes%2Fprog_default%2Fstudent1%2Fact1%2Fcomprovante.pdf"
        f"?alt=media&token={token}"
    )


async def test_upload_persiste_comprovante_url_no_doc_da_atividade(
    _setup: _FakeBucket,
) -> None:
    service = ComprovanteService()

    result = await service.upload(
        "act1",
        _upload_file(b"%PDF", "c.pdf", "application/pdf"),
        _aluno(),
    )

    assert _FakeActivityRepository.updates
    student_id, activity_id, data = _FakeActivityRepository.updates[0]
    assert (student_id, activity_id) == ("student1", "act1")
    assert data["comprovante_url"] == result["comprovante_url"]


async def test_upload_404_quando_atividade_inexistente() -> None:
    _FakeActivityRepository.store = {}
    service = ComprovanteService()

    with pytest.raises(HTTPException) as exc_info:
        await service.upload(
            "inexistente",
            _upload_file(b"%PDF", "c.pdf", "application/pdf"),
            _aluno(),
        )

    assert exc_info.value.status_code == 404
    assert _FakeActivityRepository.updates == []


async def test_upload_sanitiza_filename_com_path_traversal(
    _setup: _FakeBucket,
) -> None:
    service = ComprovanteService()

    result = await service.upload(
        "act1",
        _upload_file(b"%PDF", "../../etc/evil.pdf", "application/pdf"),
        _aluno(),
    )

    assert result["path_bucket"] == "comprovantes/prog_default/student1/act1/evil.pdf"


async def test_upload_gera_nome_quando_filename_vazio(
    _setup: _FakeBucket,
) -> None:
    service = ComprovanteService()

    result = await service.upload(
        "act1",
        _upload_file(b"%PDF", "", "application/pdf"),
        _aluno(),
    )

    assert result["path_bucket"].startswith(
        "comprovantes/prog_default/student1/act1/comprovante-"
    )


async def test_upload_rejeita_tipo_nao_suportado() -> None:
    service = ComprovanteService()

    with pytest.raises(HTTPException) as exc_info:
        await service.upload(
            "act1",
            _upload_file(b"<html>", "comprovante.html", "text/html"),
            _aluno(),
        )

    assert exc_info.value.status_code == 415


async def test_upload_rejeita_arquivo_acima_do_limite() -> None:
    service = ComprovanteService()
    big = b"x" * (MAX_COMPROVANTE_SIZE_BYTES + 1)

    with pytest.raises(HTTPException) as exc_info:
        await service.upload(
            "act1",
            _upload_file(big, "grande.pdf", "application/pdf"),
            _aluno(),
        )

    assert exc_info.value.status_code == 413


async def test_upload_rejeita_por_size_sem_ler_conteudo() -> None:
    service = ComprovanteService()
    # size declarado acima do limite, mas corpo vazio: a rejeição vem do pré-check
    # de arquivo.size, antes de qualquer read() do conteúdo.
    arquivo = _upload_file(
        b"",
        "grande.pdf",
        "application/pdf",
        size=MAX_COMPROVANTE_SIZE_BYTES + 1,
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.upload("act1", arquivo, _aluno())

    assert exc_info.value.status_code == 413


async def test_upload_404_quando_aluno_nao_encontrado() -> None:
    _FakeStudentRepository.store = [{"id": "student1", "uid": "outro-uid"}]
    service = ComprovanteService()

    with pytest.raises(HTTPException) as exc_info:
        await service.upload(
            "act1",
            _upload_file(b"%PDF", "c.pdf", "application/pdf"),
            _aluno(),
        )

    assert exc_info.value.status_code == 404
