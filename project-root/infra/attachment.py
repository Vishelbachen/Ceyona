"""
infra/attachment.py

Attachment abstraction — the single boundary between "a file the user sent
in Telegram" and "bytes/a URL a handler can hand to an external API".

Why this exists (ARCH-change 2026-07, attachment layer):
Before this module, each handler (speech_to_text.py, vision_handler.py) knew
about Supabase bucket/path directly, and made its own decision about
bytes-vs-URL inline. That produced exactly the divergence the project wanted
to avoid: photo handled one way, voice another, documents a third, and any
future attachment kind (video, etc.) needing its own bespoke wiring.

The contract this module holds:
  - Worker owns Telegram API and downloading. HF never talks to Telegram.
  - Supabase Storage is the only source of attachment bytes.
  - Every handler receives the *same* Attachment object, regardless of kind.
  - Attachment exposes exactly two data operations: bytes() and signed_url().
    Nothing else. It does NOT know Whisper's 25MB limit, or Vision's 4MB/20MB
    split, or any other per-model constraint — those stay inside the handler
    that owns that model (see speech_to_text.py, vision_handler.py).
  - Attachment does NOT decide whether a handler *should* use bytes or a URL.
    That decision belongs to the handler, informed by settings flags
    (app.settings: groq_whisper_accepts_signed_url, groq_vision_accepts_signed_url).
  - kind is a plain string, not a closed enum — new attachment kinds (video,
    sticker, etc.) need no change to this class, only a new Worker upload path
    and a new handler.

What this module explicitly is NOT:
  - Not a replacement for the legacy direct-to-Telegram-via-Worker fallback
    path that speech_to_text.py / vision_handler.py fall back to when the
    incoming update has no `_attachment` (Worker's own download/upload
    failed). That fallback is a migration safety net, lives at the call site
    in update_handler.py, and is intentionally NOT modeled as an Attachment —
    see update_handler.py's `build_attachment_or_none()` for where that
    branch lives. The target architecture does not depend on that fallback
    existing; it exists only so a Worker-side failure degrades gracefully
    instead of dropping the message.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Attachment:
    """
    A file the user sent, already stored in Supabase Storage by the Worker.

    Public surface for handlers (speech_to_text.py, vision_handler.py, and
    any future handler):
        attachment.mime_type
        attachment.size_bytes
        attachment.kind
        attachment.filename
        await attachment.bytes()
        await attachment.signed_url()

    `bucket` / `path` are intentionally not part of the public surface used
    by handlers — see storage_ref() below for the one sanctioned way to
    reach them, reserved for infra-level operations (cleanup, audit), not
    for model-calling code.
    """

    mime_type: str
    size_bytes: int
    kind: str          # "voice" | "photo" | "document" | any future kind — open string, not an enum
    filename: str       # original name/extension, e.g. "voice.ogg" — handlers use this for format decisions

    _bucket: str = field(repr=False)
    _path: str = field(repr=False)
    _supabase: Any = field(repr=False, compare=False)

    _cached_bytes: "list[bytes | None]" = field(default_factory=lambda: [None], repr=False, compare=False)

    # ── Public data operations ────────────────────────────────────────────

    async def bytes(self) -> bytes:
        """
        Download the raw file content from Storage.

        Use when a handler needs the actual bytes locally — e.g. VAD
        (silence detection), a format conversion fallback, or any model
        that only accepts a request body rather than fetching by URL.

        Cached on the instance: calling this more than once (e.g. VAD then
        a bytes-fallback send) does not re-download.
        """
        if self._cached_bytes[0] is not None:
            return self._cached_bytes[0]

        if self._supabase is None:
            raise RuntimeError(
                f"Attachment.bytes(): no supabase client available for "
                f"{self.kind}:{self._path}"
            )

        loop = asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(
                None, lambda: self._supabase.storage.from_(self._bucket).download(self._path)
            )
        except Exception as exc:
            logger.error(
                "Attachment.bytes(): Storage download failed",
                extra={"kind": self.kind, "bucket": self._bucket, "path": self._path, "error": str(exc)},
            )
            raise RuntimeError(f"Attachment.bytes(): Storage download failed: {exc}") from exc

        self._cached_bytes[0] = data
        logger.info(
            "Attachment.bytes(): downloaded from Storage",
            extra={"kind": self.kind, "bucket": self._bucket, "path": self._path, "size": len(data)},
        )
        return data

    async def signed_url(self, expires_in: int | None = None) -> str:
        """
        Create a short-lived signed URL an external API (Groq, etc.) can
        fetch directly, without HF downloading bytes itself.

        `expires_in` in seconds; defaults to settings.attachment_signed_url_ttl_seconds.
        Not cached — callers needing the URL more than once with different
        TTLs should call this again; a fresh signed URL is cheap to create
        and we'd rather not hand out a longer-lived URL than the caller asked for.
        """
        from app.settings import settings

        ttl = expires_in if expires_in is not None else settings.attachment_signed_url_ttl_seconds

        if self._supabase is None:
            raise RuntimeError(
                f"Attachment.signed_url(): no supabase client available for "
                f"{self.kind}:{self._path}"
            )

        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: self._supabase.storage.from_(self._bucket).create_signed_url(self._path, ttl),
            )
        except Exception as exc:
            logger.error(
                "Attachment.signed_url(): Storage signing failed",
                extra={"kind": self.kind, "bucket": self._bucket, "path": self._path, "error": str(exc)},
            )
            raise RuntimeError(f"Attachment.signed_url(): Storage signing failed: {exc}") from exc

        url = result.get("signedURL") or result.get("signedUrl") or result.get("signed_url")
        if not url:
            raise RuntimeError(
                f"Attachment.signed_url(): unexpected Storage response shape: {result!r}"
            )

        # Supabase returns a path-relative URL for some client versions; normalize to absolute.
        if url.startswith("/"):
            url = f"{settings.supabase_url.rstrip('/')}{url}"

        logger.info(
            "Attachment.signed_url(): created",
            extra={"kind": self.kind, "bucket": self._bucket, "path": self._path, "ttl": ttl},
        )
        return url

    # ── Infra-only escape hatch — NOT for handlers ────────────────────────

    def storage_ref(self) -> tuple[str, str]:
        """
        Returns (bucket, path) — the raw Storage coordinates.

        Reserved for infrastructure operations: housekeeping/cleanup jobs,
        audit logging, admin tooling. Handlers that call external AI models
        (speech_to_text.py, vision_handler.py, ...) must not call this —
        they should only ever use bytes()/signed_url(). If a handler needs
        this, that's a signal the abstraction is being bypassed rather than
        a signal this method should be more visible.
        """
        return self._bucket, self._path


def from_pending_update_ref(attachment_ref: dict, *, supabase: Any) -> Attachment | None:
    """
    Build an Attachment from the `_attachment` dict the Worker wrote onto
    pending_updates.payload (see ceyona-worker/worker.js::downloadAndStoreAttachment
    and supabase_storage_setup.md).

    Expected shape: {bucket, path, mime_type, size, file_id, kind}.

    Returns None if attachment_ref is missing/incomplete — callers (see
    update_handler.py) treat that as "no Attachment available, use the
    legacy fallback path", not as an error raised from here. Keeping this
    a plain None-return, rather than an exception, keeps the migration
    fallback decision entirely at the call site instead of leaking into
    this constructor.
    """
    if not attachment_ref:
        return None
    bucket = attachment_ref.get("bucket")
    path = attachment_ref.get("path")
    if not bucket or not path:
        return None

    filename = path.rsplit("/", 1)[-1] or f"{attachment_ref.get('file_id', 'file')}"

    return Attachment(
        mime_type=attachment_ref.get("mime_type", "application/octet-stream"),
        size_bytes=attachment_ref.get("size", 0),
        kind=attachment_ref.get("kind", "unknown"),
        filename=filename,
        _bucket=bucket,
        _path=path,
        _supabase=supabase,
    )