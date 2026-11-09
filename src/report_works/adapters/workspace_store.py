"""Áreas de trabalho em disco: template, fotos por seção e relatórios gerados.

Cada área é uma pasta `workdir/<id>/` com `template.xlsx`, `photos/<seção>/` e `outputs/`.
Tudo que vem do usuário (nomes de arquivo, ZIP, ids) é validado aqui, antes de tocar o disco.
"""

from __future__ import annotations

import contextlib
import re
import shutil
import tempfile
import time
import uuid
import zipfile
from collections.abc import Callable, Iterable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import IO, Any, cast

import rarfile  # pyright: ignore[reportMissingTypeStubs]

from report_works.domain.errors import (
    UnsafePathError,
    UnsupportedFileError,
    UploadTooLargeError,
    WorkspaceNotFoundError,
)
from report_works.domain.models import SECTION_ID_PATTERN
from report_works.i18n import pt_br
from report_works.services.photo_discovery import DEFAULT_EXTENSIONS

WORKSPACE_ID = re.compile(r"^[0-9a-f]{32}$")
SECTION_ID = re.compile(SECTION_ID_PATTERN)
TEMPLATE_NAME = "template.xlsx"
CHUNK_BYTES = 1024 * 1024
MAX_ARCHIVE_MEMBERS = 20_000
BYTES_PER_MB = 1024 * 1024
ZIP_SIGNATURE = b"PK"
RAR_SIGNATURE = b"Rar!"
WINRAR_UNRAR = Path(r"C:\Program Files\WinRAR\UnRAR.exe")

# Um membro de arquivo compactado ou de pasta: caminho relativo + como abrir o conteúdo.
_Opener = Callable[[], AbstractContextManager[IO[bytes]]]
_Member = tuple[str, _Opener]


@dataclass(frozen=True)
class UploadSummary:
    """Quantos arquivos foram guardados e quantos foram ignorados (tipo não aceito)."""

    saved: int
    skipped: int


class _Budget:
    """Orçamento de bytes de um envio (um arquivo, um lote ou um ZIP inteiro)."""

    def __init__(self, limit_bytes: int) -> None:
        self._limit = limit_bytes
        self._remaining = limit_bytes

    def copy(self, source: IO[bytes], target: Path) -> None:
        """Copia em pedaços e falha assim que o limite é ultrapassado (apaga o parcial)."""
        try:
            with target.open("wb") as output:
                while chunk := source.read(CHUNK_BYTES):
                    self._remaining -= len(chunk)
                    if self._remaining < 0:
                        limit_mb = self._limit // BYTES_PER_MB
                        raise UploadTooLargeError(
                            pt_br.ERR_UPLOAD_TOO_LARGE.format(limit_mb=limit_mb)
                        )
                    output.write(chunk)
        except UploadTooLargeError:
            target.unlink(missing_ok=True)
            raise


def _configure_rar_tool(configured: Path | None) -> None:
    """Escolhe a ferramenta externa que abre RAR (UnRAR, 7-Zip ou bsdtar) para a `rarfile`.

    Ordem: caminho informado em `REPORT_RAR_TOOL`; ferramentas já no PATH; WinRAR instalado no
    Windows; `tar` do Windows (bsdtar). Sem nenhuma, levanta `UnsupportedFileError`.
    """
    if configured is not None:
        name = configured.name.lower()
        if "7z" in name:
            rarfile.SEVENZIP_TOOL = str(configured)
        elif "tar" in name:
            rarfile.BSDTAR_TOOL = str(configured)
        else:
            rarfile.UNRAR_TOOL = str(configured)
    else:
        on_path = any(shutil.which(tool) for tool in ("unrar", "unar", "7z", "bsdtar"))
        if not on_path and WINRAR_UNRAR.is_file():
            rarfile.UNRAR_TOOL = str(WINRAR_UNRAR)
        elif not on_path and (tar := shutil.which("tar")):
            rarfile.BSDTAR_TOOL = tar  # no Windows 10+, `tar` é o bsdtar
    try:
        rarfile.tool_setup(force=True)
    except rarfile.RarCannotExec as error:
        raise UnsupportedFileError(pt_br.ERR_RAR_TOOL_MISSING) from error


def _rar_members(archive: rarfile.RarFile) -> list[_Member]:
    """Membros de um RAR aberto (a `rarfile` não tem tipos; as conversões ficam só aqui)."""
    reader = cast("Any", archive)
    members: list[_Member] = []
    for info in cast("list[Any]", reader.infolist()):
        if not info.is_dir():
            members.append((str(info.filename), _opener(reader, info)))
    return members


def _opener(reader: object, info: object) -> _Opener:
    return lambda: cast("IO[bytes]", cast("Any", reader).open(info))


def _safe_filename(name: str) -> str:
    """Só o nome do arquivo, sem pastas nem separadores de qualquer sistema."""
    return PurePosixPath(name.replace("\\", "/")).name


class WorkspaceStore:
    """Gerencia as áreas de trabalho dentro de `root`."""

    def __init__(self, root: Path, max_upload_bytes: int, rar_tool: Path | None = None) -> None:
        self._root = root
        self._max_upload_bytes = max_upload_bytes
        self._rar_tool = rar_tool
        root.mkdir(parents=True, exist_ok=True)

    # --- áreas e caminhos -----------------------------------------------------------------

    def create(self) -> str:
        """Cria uma área de trabalho nova e devolve o id."""
        workspace_id = uuid.uuid4().hex
        (self._root / workspace_id / "photos").mkdir(parents=True)
        (self._root / workspace_id / "outputs").mkdir()
        return workspace_id

    def workspace(self, workspace_id: str) -> Path:
        """Pasta da área; id inválido ou inexistente vira `WorkspaceNotFoundError`."""
        path = self._root / workspace_id
        if not WORKSPACE_ID.fullmatch(workspace_id) or not path.is_dir():
            raise WorkspaceNotFoundError(pt_br.ERR_WORKSPACE_NOT_FOUND)
        return path

    def template_path(self, workspace_id: str) -> Path:
        """Caminho do template (pode ainda não existir)."""
        return self.workspace(workspace_id) / TEMPLATE_NAME

    def photos_dir(self, workspace_id: str) -> Path:
        """Pasta raiz das fotos (uma subpasta por seção)."""
        return self.workspace(workspace_id) / "photos"

    def output_path(self, workspace_id: str, job_id: str) -> Path:
        """Caminho do relatório de uma tarefa."""
        return self.workspace(workspace_id) / "outputs" / f"{job_id}.xlsx"

    def purge_older_than(self, hours: int) -> int:
        """Remove as áreas não modificadas há mais de `hours`; retorna quantas foram."""
        limit = time.time() - hours * 3600
        removed = 0
        for path in self._root.iterdir():
            if WORKSPACE_ID.fullmatch(path.name) and path.is_dir() and path.stat().st_mtime < limit:
                shutil.rmtree(path, ignore_errors=True)
                removed += 1
        return removed

    # --- envios ---------------------------------------------------------------------------

    def save_template(self, workspace_id: str, source: IO[bytes], filename: str) -> Path:
        """Guarda o template (somente `.xlsx`), substituindo o anterior."""
        if not _safe_filename(filename).lower().endswith(".xlsx"):
            raise UnsupportedFileError(pt_br.ERR_UPLOAD_EXTENSION.format(name=filename))
        target = self.template_path(workspace_id)
        _Budget(self._max_upload_bytes).copy(source, target)
        return target

    def save_photos(
        self, workspace_id: str, section_id: str, files: Iterable[tuple[str, IO[bytes]]]
    ) -> UploadSummary:
        """Guarda fotos soltas na pasta de uma seção; arquivos de outro tipo são ignorados."""
        folder = self._section_folder(workspace_id, section_id)
        budget = _Budget(self._max_upload_bytes)
        saved = skipped = 0
        for name, source in files:
            safe = _safe_filename(name)
            if not safe or Path(safe).suffix.lower() not in DEFAULT_EXTENSIONS:
                skipped += 1
                continue
            folder.mkdir(parents=True, exist_ok=True)
            budget.copy(source, folder / safe)
            saved += 1
        return UploadSummary(saved, skipped)

    def save_archive(self, workspace_id: str, source: IO[bytes]) -> tuple[dict[str, int], int]:
        """Extrai um ZIP ou RAR com pastas por seção; devolve fotos por seção e ignorados.

        O formato vem da assinatura do arquivo. A pasta que contém a foto (em qualquer nível) é
        o id da seção, em minúsculas. Caminhos absolutos, `..` e unidades de disco são recusados.
        """
        photos_root = self.photos_dir(workspace_id)
        signature = source.read(len(RAR_SIGNATURE))
        source.seek(0)
        if signature.startswith(RAR_SIGNATURE):
            return self._save_rar(photos_root, source)
        if signature.startswith(ZIP_SIGNATURE):
            return self._save_zip(photos_root, source)
        raise UnsupportedFileError(pt_br.ERR_ARCHIVE_INVALID)

    def save_folder(
        self, workspace_id: str, files: Iterable[tuple[str, IO[bytes]]]
    ) -> tuple[dict[str, int], int]:
        """Guarda arquivos de uma pasta enviada (caminho relativo + conteúdo), por seção.

        Mesma regra do ZIP: a pasta imediata que contém a foto é o id da seção.
        """
        members: list[_Member] = [
            (path, lambda source=source: contextlib.nullcontext(source)) for path, source in files
        ]
        return self._store_members(self.photos_dir(workspace_id), members)

    def _save_zip(self, photos_root: Path, source: IO[bytes]) -> tuple[dict[str, int], int]:
        try:
            archive = zipfile.ZipFile(source)
        except zipfile.BadZipFile as error:
            raise UnsupportedFileError(pt_br.ERR_ARCHIVE_INVALID) from error
        with archive:
            members: list[_Member] = [
                (info.filename, lambda info=info: archive.open(info))
                for info in archive.infolist()
                if not info.is_dir()
            ]
            return self._store_members(photos_root, members)

    def _save_rar(self, photos_root: Path, source: IO[bytes]) -> tuple[dict[str, int], int]:
        _configure_rar_tool(self._rar_tool)
        # As ferramentas de RAR precisam de um arquivo em disco, não de um fluxo em memória.
        with tempfile.TemporaryDirectory(dir=photos_root.parent) as scratch:
            rar_path = Path(scratch) / "upload.rar"
            _Budget(self._max_upload_bytes).copy(source, rar_path)
            try:
                with rarfile.RarFile(rar_path) as archive:
                    return self._store_members(photos_root, _rar_members(archive))
            except rarfile.RarCannotExec as error:
                raise UnsupportedFileError(pt_br.ERR_RAR_TOOL_MISSING) from error
            except rarfile.Error as error:
                raise UnsupportedFileError(pt_br.ERR_ARCHIVE_INVALID) from error

    def _store_members(
        self, photos_root: Path, members: list[_Member]
    ) -> tuple[dict[str, int], int]:
        if len(members) > MAX_ARCHIVE_MEMBERS:
            raise UnsupportedFileError(pt_br.ERR_ARCHIVE_INVALID)
        budget = _Budget(self._max_upload_bytes)
        per_section: dict[str, int] = {}
        skipped = 0
        for name_in_archive, open_member in members:
            parts = self._relative_parts(name_in_archive)
            section_id = parts[-2].lower() if len(parts) >= 2 else ""
            name = parts[-1]
            if not SECTION_ID.fullmatch(section_id) or Path(name).suffix.lower() not in (
                DEFAULT_EXTENSIONS
            ):
                skipped += 1
                continue
            folder = photos_root / section_id
            folder.mkdir(parents=True, exist_ok=True)
            with open_member() as member:
                budget.copy(member, folder / name)
            per_section[section_id] = per_section.get(section_id, 0) + 1
        return per_section, skipped

    def count_by_section(self, workspace_id: str) -> dict[str, int]:
        """Quantidade de fotos guardadas em cada pasta de seção."""
        counts: dict[str, int] = {}
        for folder in sorted(self.photos_dir(workspace_id).iterdir()):
            if folder.is_dir():
                counts[folder.name] = sum(
                    1 for f in folder.iterdir() if f.suffix.lower() in DEFAULT_EXTENSIONS
                )
        return counts

    # --- auxiliares -----------------------------------------------------------------------

    def _section_folder(self, workspace_id: str, section_id: str) -> Path:
        if not SECTION_ID.fullmatch(section_id):
            raise UnsafePathError(pt_br.ERR_SECTION_ID_INVALID.format(value=section_id))
        return self.photos_dir(workspace_id) / section_id

    @staticmethod
    def _relative_parts(member_name: str) -> list[str]:
        normalized = PurePosixPath(member_name.replace("\\", "/"))
        unsafe = (
            normalized.is_absolute()
            or ".." in normalized.parts
            or any(":" in part for part in normalized.parts)  # unidade de disco ou fluxo NTFS
        )
        if unsafe or not normalized.name:
            raise UnsupportedFileError(pt_br.ERR_ARCHIVE_UNSAFE.format(name=member_name))
        return list(normalized.parts)
