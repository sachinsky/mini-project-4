from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, func, select

from .database import SessionLocal
from .models import ConversationLog


def normalize_query(query: str) -> str:
    return " ".join(query.lower().strip().split())[:500]


def log_conversation(
    *,
    query: str,
    response: str,
    category: str | None = None,
    input_guardrail: str | None = None,
    output_guardrail: str | None = None,
    session_id: str | None = None,
) -> None:
    """Persist a support interaction for analytics. Failures are swallowed."""
    db = SessionLocal()
    try:
        entry = ConversationLog(
            query=query.strip(),
            normalized_query=normalize_query(query),
            response=response.strip(),
            category=category,
            input_guardrail=input_guardrail,
            output_guardrail=output_guardrail,
            session_id=session_id,
        )
        db.add(entry)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _since(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


def get_analytics_summary(days: int = 30) -> dict:
    db = SessionLocal()
    try:
        since = _since(days)
        total = db.scalar(
            select(func.count()).select_from(ConversationLog).where(ConversationLog.created_at >= since)
        ) or 0

        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today = db.scalar(
            select(func.count())
            .select_from(ConversationLog)
            .where(ConversationLog.created_at >= today_start)
        ) or 0

        category_rows = db.execute(
            select(ConversationLog.category, func.count())
            .where(ConversationLog.created_at >= since)
            .group_by(ConversationLog.category)
            .order_by(desc(func.count()))
        ).all()

        return {
            "total_queries": total,
            "queries_today": today,
            "period_days": days,
            "category_breakdown": [
                {"category": row[0] or "Unknown", "count": row[1]} for row in category_rows
            ],
        }
    finally:
        db.close()


def get_top_queries(limit: int = 10, days: int = 30) -> list[dict]:
    db = SessionLocal()
    try:
        since = _since(days)
        rows = db.execute(
            select(
                ConversationLog.normalized_query,
                func.count().label("count"),
                func.max(ConversationLog.query).label("sample_query"),
                func.max(ConversationLog.category).label("latest_category"),
                func.max(ConversationLog.created_at).label("last_seen"),
            )
            .where(ConversationLog.created_at >= since)
            .group_by(ConversationLog.normalized_query)
            .order_by(desc("count"))
            .limit(limit)
        ).all()

        return [
            {
                "rank": index,
                "query": row.sample_query,
                "normalized_query": row.normalized_query,
                "count": row.count,
                "latest_category": row.latest_category,
                "last_seen": row.last_seen.isoformat() if row.last_seen else None,
            }
            for index, row in enumerate(rows, start=1)
        ]
    finally:
        db.close()


def get_recent_conversations(limit: int = 50, days: int = 30) -> list[dict]:
    db = SessionLocal()
    try:
        since = _since(days)
        rows = db.execute(
            select(ConversationLog)
            .where(ConversationLog.created_at >= since)
            .order_by(desc(ConversationLog.created_at))
            .limit(limit)
        ).scalars().all()

        return [
            {
                "id": row.id,
                "query": row.query,
                "response": row.response,
                "category": row.category,
                "session_id": row.session_id,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    finally:
        db.close()


def get_daily_volume(days: int = 30) -> list[dict]:
    db = SessionLocal()
    try:
        since = _since(days)
        rows = db.execute(
            select(
                func.date(ConversationLog.created_at).label("day"),
                func.count().label("count"),
            )
            .where(ConversationLog.created_at >= since)
            .group_by(func.date(ConversationLog.created_at))
            .order_by("day")
        ).all()

        return [{"date": str(row.day), "count": row.count} for row in rows]
    finally:
        db.close()


def get_daily_volume(days: int = 30) -> list[dict]:
    db = SessionLocal()
    try:
        since = _since(days)
        rows = db.execute(
            select(
                func.date(ConversationLog.created_at).label("day"),
                func.count().label("count"),
            )
            .where(ConversationLog.created_at >= since)
            .group_by(func.date(ConversationLog.created_at))
            .order_by("day")
        ).all()

        return [{"date": str(row.day), "count": row.count} for row in rows]
    finally:
        db.close()
