"""Pairing storage - YAML-based storage for authorized users and pending requests."""

import secrets
import string
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class AuthorizedUser:
    """An authorized user."""

    channel: str
    user_id: str
    name: str
    approved_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class PendingRequest:
    """A pending pairing request."""

    channel: str
    user_id: str
    name: str
    code: str
    requested_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


def generate_code(length: int = 8) -> str:
    """Generate a random pairing code."""
    alphabet = string.ascii_uppercase + string.digits
    # Remove ambiguous characters
    alphabet = (
        alphabet.replace("O", "").replace("0", "").replace("I", "").replace("1", "")
    )
    return "".join(secrets.choice(alphabet) for _ in range(length))


class PairingStorage:
    """YAML-based storage for pairing data."""

    def __init__(self, path: Path):
        self._path = path
        self._authorized: list[AuthorizedUser] = []
        self._pending: list[PendingRequest] = []
        self._last_mtime: float = 0
        self._load()

    def _load(self) -> None:
        """Load data from YAML file."""
        if not self._path.exists():
            return

        try:
            self._last_mtime = self._path.stat().st_mtime

            with open(self._path) as f:
                data = yaml.safe_load(f) or {}

            self._authorized = []
            self._pending = []

            for item in data.get("authorized", []):
                self._authorized.append(AuthorizedUser(**item))

            for item in data.get("pending", []):
                self._pending.append(PendingRequest(**item))

        except Exception:
            # Start fresh on error
            self._authorized = []
            self._pending = []

    def _reload_if_changed(self) -> None:
        """Reload from disk if file was modified (e.g., by CLI approve)."""
        if not self._path.exists():
            return
        try:
            mtime = self._path.stat().st_mtime
            if mtime > self._last_mtime:
                self._load()
        except Exception:
            pass

    def _save(self) -> None:
        """Save data to YAML file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "authorized": [asdict(u) for u in self._authorized],
            "pending": [asdict(r) for r in self._pending],
        }

        with open(self._path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def is_authorized(self, channel: str, user_id: str) -> bool:
        """Check if a user is authorized.

        Checks file mtime to pick up CLI approvals without restart.
        """
        self._reload_if_changed()
        user_id = str(user_id)
        return any(
            u.channel == channel and u.user_id == user_id for u in self._authorized
        )

    def get_authorized(self) -> list[AuthorizedUser]:
        """Get all authorized users."""
        return list(self._authorized)

    def get_pending(self) -> list[PendingRequest]:
        """Get all pending requests."""
        return list(self._pending)

    def get_pending_by_code(self, code: str) -> Optional[PendingRequest]:
        """Get a pending request by code."""
        code = code.upper()
        for req in self._pending:
            if req.code == code:
                return req
        return None

    def get_pending_for_user(
        self, channel: str, user_id: str
    ) -> Optional[PendingRequest]:
        """Get pending request for a user."""
        user_id = str(user_id)
        for req in self._pending:
            if req.channel == channel and req.user_id == user_id:
                return req
        return None

    def add_pending(self, channel: str, user_id: str, name: str) -> PendingRequest:
        """Add a pending pairing request.

        If a request already exists for this user, return it.
        Otherwise create a new one.
        """
        user_id = str(user_id)

        # Check if already pending
        existing = self.get_pending_for_user(channel, user_id)
        if existing:
            return existing

        # Create new request
        req = PendingRequest(
            channel=channel,
            user_id=user_id,
            name=name,
            code=generate_code(),
        )
        self._pending.append(req)
        self._save()
        return req

    def approve(self, code: str) -> Optional[AuthorizedUser]:
        """Approve a pending request by code.

        Returns the authorized user if successful, None if code not found.
        """
        req = self.get_pending_by_code(code)
        if not req:
            return None

        # Remove from pending
        self._pending = [r for r in self._pending if r.code != req.code]

        # Add to authorized
        user = AuthorizedUser(
            channel=req.channel,
            user_id=req.user_id,
            name=req.name,
        )
        self._authorized.append(user)
        self._save()
        return user

    def reject(self, code: str) -> bool:
        """Reject a pending request by code.

        Returns True if found and removed, False otherwise.
        """
        req = self.get_pending_by_code(code)
        if not req:
            return False

        self._pending = [r for r in self._pending if r.code != req.code]
        self._save()
        return True

    def revoke(self, channel: str, user_id: str) -> bool:
        """Revoke authorization for a user.

        Returns True if found and removed, False otherwise.
        """
        user_id = str(user_id)
        original_len = len(self._authorized)
        self._authorized = [
            u
            for u in self._authorized
            if not (u.channel == channel and u.user_id == user_id)
        ]

        if len(self._authorized) < original_len:
            self._save()
            return True
        return False

    def add_authorized(
        self, channel: str, user_id: str, name: str = ""
    ) -> AuthorizedUser:
        """Directly add an authorized user (for owner_ids bootstrap)."""
        user_id = str(user_id)

        # Check if already authorized
        if self.is_authorized(channel, user_id):
            for u in self._authorized:
                if u.channel == channel and u.user_id == user_id:
                    return u

        user = AuthorizedUser(
            channel=channel,
            user_id=user_id,
            name=name or f"owner:{user_id}",
        )
        self._authorized.append(user)
        self._save()
        return user
