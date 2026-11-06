"""Dark web monitoring: match every user's monitored assets against the collected feeds.

Each new match becomes a ``DarkWebMention`` (deduplicated by a fingerprint) and an alert
(which also reaches the user's webhook). Runs from the scheduler and on demand.
"""

from __future__ import annotations

import hashlib
import threading
from collections import Counter
from datetime import datetime, timezone
from typing import Optional

from loguru import logger
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import time

from app.core.encryption import decrypt_value
from app.models.darkweb import DarkWebMention, DarkWebSource, MonitoredAsset, TelegramAccount, TelegramChannel
from app.models.user import User
from app.services.darkweb import feeds, sources, telegram
from app.services.darkweb.matcher import Asset, Matcher

MAX_ALERTS_PER_SCAN = 15
MAX_INFOSTEALER_DOMAINS = 10
_scan_locks: dict[str, threading.Lock] = {}
_scan_locks_guard = threading.Lock()


def _lock_for(user_id: str) -> threading.Lock:
    with _scan_locks_guard:
        return _scan_locks.setdefault(user_id, threading.Lock())


def _fp(*parts: object) -> str:
    return hashlib.sha256("|".join(str(p).lower() for p in parts).encode()).hexdigest()[:64]


class DarkWebMonitor:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------ helpers

    def _assets(self, user_id: str) -> list[Asset]:
        rows = (
            self.db.query(MonitoredAsset)
            .filter(MonitoredAsset.user_id == user_id, MonitoredAsset.is_active.is_(True))
            .all()
        )
        return [Asset(id=r.id, user_id=r.user_id, kind=r.kind, value=r.value) for r in rows]

    def _add(self, user_id: str, asset: Asset, source: str, severity: str, title: str, *, snippet: str = "",
             url: str = "", actor: str = "", published_at: Optional[datetime] = None, details: Optional[dict] = None,
             fingerprint: str) -> Optional[DarkWebMention]:
        if self.db.query(DarkWebMention.id).filter_by(user_id=user_id, fingerprint=fingerprint).first():
            return None
        mention = DarkWebMention(
            user_id=user_id,
            asset_id=asset.id,
            source=source,
            severity=severity,
            matched_term=asset.value,
            title=title[:500],
            snippet=(snippet or "")[:2000],
            url=(url or "")[:1000] or None,
            actor=(actor or "")[:255] or None,
            published_at=published_at,
            details=details,
            fingerprint=fingerprint,
        )
        try:
            with self.db.begin_nested():
                self.db.add(mention)
        except IntegrityError:
            return None
        return mention

    # ------------------------------------------------------------------ collectors

    def _ransomware(self, user_id: str, matcher: Matcher, posts: list[feeds.LeakPost]) -> list[DarkWebMention]:
        found = []
        for post in posts:
            for asset in matcher.find(post.victim, post.domain, post.description):
                direct = asset.kind == "domain" and (
                    post.domain == asset.value or post.domain.endswith("." + asset.value) or post.victim.lower() == asset.value
                )
                m = self._add(
                    user_id, asset, "ransomware", "critical" if direct else "high",
                    f"{post.group or 'Unknown group'} leak site lists \"{post.victim}\"",
                    snippet=matcher.snippet(" - ".join(filter(None, [post.victim, post.domain, post.description])), asset),
                    url=post.url, actor=post.group, published_at=post.published_at,
                    details={"aggregator": post.source, "victim": post.victim, "domain": post.domain, **post.extra},
                    fingerprint=_fp("ransomware", post.key, asset.id),
                )
                if m:
                    found.append(m)
        return found

    def _breaches(self, user_id: str, assets: list[Asset], breaches: list[dict]) -> list[DarkWebMention]:
        found = []
        domains = [a for a in assets if a.kind in ("domain", "email_domain")]
        for breach in breaches:
            bdomain = str(breach.get("Domain") or "").lower()
            if not bdomain:
                continue
            for asset in domains:
                if bdomain == asset.value or bdomain.endswith("." + asset.value):
                    classes = ", ".join(breach.get("DataClasses") or [])
                    m = self._add(
                        user_id, asset, "breach", "high",
                        f"Breach: {breach.get('Title') or breach.get('Name')} ({int(breach.get('PwnCount') or 0):,} accounts)",
                        snippet=f"Breach date {breach.get('BreachDate')} - data: {classes}",
                        url=f"https://haveibeenpwned.com/PwnedWebsites#{breach.get('Name')}",
                        actor="Have I Been Pwned",
                        published_at=feeds._dt(breach.get("AddedDate")),
                        details={k: breach.get(k) for k in ("Name", "BreachDate", "PwnCount", "IsVerified", "IsStealerLog")},
                        fingerprint=_fp("breach", breach.get("Name"), asset.id),
                    )
                    if m:
                        found.append(m)
        return found

    def _infostealers(self, user_id: str, assets: list[Asset]) -> list[DarkWebMention]:
        found = []
        domains = [a for a in assets if a.kind == "domain"][:MAX_INFOSTEALER_DOMAINS]
        started, errors = time.monotonic(), []
        for asset in domains:
            try:
                exposure = feeds.infostealer_exposure(asset.value, raise_errors=True)
            except Exception as exc:
                errors.append(f"{asset.value}: {type(exc).__name__}")
                continue
            if not exposure or not (exposure["employees"] or exposure["users"]):
                continue
            severity = "high" if exposure["employees"] else "medium"
            families = ", ".join(sorted(exposure["stealer_families"], key=exposure["stealer_families"].get, reverse=True)[:4])
            m = self._add(
                user_id, asset, "infostealer", severity,
                f"Infostealer logs: {exposure['employees']} employees, {exposure['users']} users of {asset.value}",
                snippet=(
                    f"Last employee infection {(exposure['last_employee_compromised'] or '-')[:10]}, last user infection "
                    f"{(exposure['last_user_compromised'] or '-')[:10]}. Families: {families or '-'}"
                ),
                url=f"https://www.hudsonrock.com/search?domain={asset.value}",
                actor="Hudson Rock",
                published_at=feeds._dt(exposure["last_employee_compromised"] or exposure["last_user_compromised"]),
                details=exposure,
                # a new mention whenever the numbers change
                fingerprint=_fp("infostealer", asset.id, exposure["employees"], exposure["users"]),
            )
            if m:
                found.append(m)
        if domains:
            sources.record(self.db, "hudsonrock", ok=not errors, items=len(domains) - len(errors), started=started,
                           error="; ".join(errors))
        return found

    def _telegram(self, user_id: str, matcher: Matcher) -> list[DarkWebMention]:
        found = []
        channels = (
            self.db.query(TelegramChannel)
            .filter(TelegramChannel.user_id == user_id, TelegramChannel.is_active.is_(True))
            .all()
        )
        account = self.db.query(TelegramAccount).filter_by(user_id=user_id, status="connected").first()
        started, fetched, failed = time.monotonic(), 0, []
        for channel in channels:
            try:
                if channel.mode == "account":
                    if not account:
                        raise ValueError("No Telegram account connected")
                    title, messages = telegram.account_fetch(
                        account.api_id, decrypt_value(account.api_hash_enc), decrypt_value(account.session_enc),
                        channel.username, channel.last_message_id,
                    )
                else:
                    title, messages = telegram.fetch_public(channel.username)
                channel.title = title or channel.title
                channel.last_error = None
            except Exception as exc:
                channel.last_error = str(exc)[:500]
                channel.last_checked_at = datetime.now(timezone.utc)
                failed.append(channel.username)
                logger.warning("Telegram channel {} failed: {}", channel.username, exc)
                continue
            fetched += len(messages)
            newest = channel.last_message_id
            for msg in messages:
                if msg.message_id <= channel.last_message_id:
                    continue
                newest = max(newest, msg.message_id)
                for asset in matcher.find(msg.text):
                    # domain / e-mail matches are concrete; brand keywords are noisier
                    severity = "medium" if asset.kind == "keyword" else "high"
                    m = self._add(
                        user_id, asset, "telegram", severity,
                        f"Mentioned in Telegram: {channel.title or channel.username}",
                        snippet=matcher.snippet(msg.text, asset), url=msg.url,
                        actor=f"@{channel.username}" if channel.mode == "public" else (channel.title or channel.username),
                        published_at=msg.published_at,
                        details={"channel": channel.username, "message_id": msg.message_id, "mode": channel.mode},
                        fingerprint=_fp("telegram", channel.username, msg.message_id, asset.id),
                    )
                    if m:
                        found.append(m)
            channel.last_message_id = newest
            channel.last_checked_at = datetime.now(timezone.utc)
        if channels:
            # a few dead channels are a per-channel problem; the source is only "failing" if nothing worked
            sources.record(self.db, "telegram", ok=len(failed) < len(channels), items=fetched, started=started,
                           error=f"{len(failed)} channel(s) failed: {', '.join(failed[:5])}" if failed else None)
        return found

    def _custom_feeds(self, user_id: str, matcher: Matcher, custom: dict) -> list[DarkWebMention]:
        found = []
        for key, entry in custom.items():
            name, severity, items = entry[:3]
            category = entry[3] if len(entry) > 3 else "feed"
            # forum / breach / ransomware feeds show up under their own heading, news & custom under "feed"
            mention_source = category if category in ("forum", "breach", "ransomware") else "feed"
            for item in items:
                for asset in matcher.find(item.title, item.text, item.url):
                    m = self._add(
                        user_id, asset, mention_source, severity, f"{name}: {item.title}",
                        snippet=matcher.snippet(f"{item.title} - {item.text}", asset), url=item.url, actor=name,
                        published_at=item.published_at, details={"source_key": key},
                        fingerprint=_fp("feed", key, item.url or item.title, asset.id),
                    )
                    if m:
                        found.append(m)
        return found

    # ------------------------------------------------------------------ shared feeds

    def collect_shared(self) -> dict:
        """Fetch the feeds that are the same for every user once, recording each source's health."""
        sources.ensure_seeded(self.db)
        enabled = {s.key: s for s in self.db.query(DarkWebSource).filter(DarkWebSource.is_enabled.is_(True)).all()}
        shared: dict = {"custom": {}}

        def run(key, fetch):
            if key not in enabled:
                return None
            started = time.monotonic()
            try:
                data = fetch()
                sources.record(self.db, key, ok=True, items=len(data), started=started)
                return data
            except Exception as exc:
                sources.record(self.db, key, ok=False, started=started, error=f"{type(exc).__name__}: {exc}"[:500])
                logger.warning("Dark web source {} failed: {}", key, exc)
                return None

        shared["ransomware_live"] = run("ransomware_live", feeds.ransomware_live_posts)
        shared["ransomlook"] = run("ransomlook", feeds.ransomlook_posts)
        shared["hibp"] = run("hibp", feeds.hibp_catalog)
        for key, row in enabled.items():
            if row.config:  # built-in RSS feeds and admin-defined custom feeds
                items = run(key, lambda cfg=row.config: sources.fetch_custom(cfg))
                if items is not None:
                    shared["custom"][key] = (row.name, (row.config or {}).get("severity", "high"), items, row.category)
        self.db.commit()
        return shared

    # ------------------------------------------------------------------ public

    def scan_user(self, user_id: str, shared: Optional[dict] = None, posts=None, breaches=None) -> dict:
        """Scan one user. ``posts`` / ``breaches`` override the fetched feeds (tests)."""
        lock = _lock_for(user_id)
        if not lock.acquire(blocking=False):
            return {"status": "busy"}
        try:
            assets = self._assets(user_id)
            if not assets:
                return {"status": "no_assets", "new_mentions": 0}
            if shared is None:
                shared = self.collect_shared() if posts is None or breaches is None else {"custom": {}}
            user = self.db.query(User).filter(User.id == user_id).first()
            active = sources.active_keys(self.db, user.profile_json if user else None)
            if not self.db.query(DarkWebSource.id).first():  # registry not seeded yet (tests)
                active = {s["key"] for s in sources.BUILTIN_SOURCES}

            if posts is None:
                posts = feeds.merge_posts(
                    shared.get("ransomware_live") or [] if "ransomware_live" in active else [],
                    shared.get("ransomlook") or [] if "ransomlook" in active else [],
                )
            elif not active & {"ransomware_live", "ransomlook"}:
                posts = []
            if breaches is None:
                breaches = shared.get("hibp") or [] if "hibp" in active else []
            elif "hibp" not in active:
                breaches = []

            matcher = Matcher(assets)
            new: list[DarkWebMention] = []
            new += self._ransomware(user_id, matcher, posts)
            new += self._breaches(user_id, assets, breaches)
            if "hudsonrock" in active:
                new += self._infostealers(user_id, assets)
            if "telegram" in active:
                new += self._telegram(user_id, matcher)
            custom = {k: v for k, v in (shared.get("custom") or {}).items() if k in active}
            new += self._custom_feeds(user_id, matcher, custom)
            self.db.commit()
            self._alert(user_id, new)
            return {
                "status": "ok",
                "new_mentions": len(new),
                "by_source": dict(Counter(m.source for m in new)),
                "leak_posts_checked": len(posts),
                "sources_used": sorted(active),
            }
        finally:
            lock.release()

    def scan_all(self) -> dict:
        user_ids = [uid for (uid,) in self.db.query(MonitoredAsset.user_id).filter(MonitoredAsset.is_active.is_(True)).distinct()]
        if not user_ids:
            return {"users": 0, "new_mentions": 0, "by_source": {}}
        shared = self.collect_shared()
        totals: Counter[str] = Counter()
        for user_id in user_ids:
            try:
                result = self.scan_user(user_id, shared=shared)
                totals.update(result.get("by_source", {}))
            except Exception:
                self.db.rollback()
                logger.exception("Dark web scan failed for user {}", user_id)
        return {"users": len(user_ids), "new_mentions": sum(totals.values()), "by_source": dict(totals)}

    def _alert(self, user_id: str, mentions: list[DarkWebMention]) -> None:
        if not mentions:
            return
        from app.models.alert import AlertSeverity, AlertType
        from app.schemas.alert import AlertCreate
        from app.services.alert_service import AlertService

        service = AlertService(self.db)
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        ranked = sorted(mentions, key=lambda m: order.get(m.severity, 9))
        for m in ranked[:MAX_ALERTS_PER_SCAN]:
            service.create_alert(
                user_id,
                AlertCreate(
                    alert_type=AlertType.DARKWEB,
                    severity=AlertSeverity(m.severity),
                    title=f"Dark web: {m.title}"[:255],
                    message=f"Matched \"{m.matched_term}\" ({m.source}). {m.snippet or ''}"[:2000],
                    metadata={"mention_id": m.id, "source": m.source, "url": m.url},
                ),
            )
        rest = len(ranked) - MAX_ALERTS_PER_SCAN
        if rest > 0:
            service.create_alert(
                user_id,
                AlertCreate(
                    alert_type=AlertType.DARKWEB,
                    severity=AlertSeverity.MEDIUM,
                    title=f"Dark web: {rest} more new mentions",
                    message="See the Dark Web page for the full list.",
                ),
            )


def run_scheduled_scan() -> None:
    from app.db.base import SessionLocal

    db = SessionLocal()
    try:
        summary = DarkWebMonitor(db).scan_all()
        logger.info("Dark web scan finished: {}", summary)
    except Exception:
        logger.exception("Scheduled dark web scan failed")
    finally:
        db.close()
