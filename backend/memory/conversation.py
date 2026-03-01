"""Conversation history management utilities."""
import uuid
from datetime import datetime
from memory.db import Session, Conversation
import logging

logger = logging.getLogger("vini.conversation")


def save_conversation(role: str, content: str, session_id: str) -> None:
    """Save conversation turn to database."""
    try:
        session = Session()
        conv = Conversation(
            id=str(uuid.uuid4()),
            role=role,
            content=content,
            session_id=session_id,
            created=datetime.utcnow(),
        )
        session.add(conv)
        session.commit()
        session.close()
    except Exception as e:
        logger.error(f"Failed to save conversation: {e}")


def load_conversation_history(limit: int = 50) -> list[dict]:
    """Load recent conversation history from database."""
    try:
        session = Session()
        convos = session.query(Conversation)\
            .order_by(Conversation.created.desc())\
            .limit(limit)\
            .all()
        session.close()
        return [
            {"role": c.role, "content": c.content}
            for c in reversed(convos)
        ]
    except Exception as e:
        logger.error(f"Failed to load conversation history: {e}")
        return []


def clear_conversation_history() -> None:
    """Clear all conversation history from database."""
    try:
        session = Session()
        session.query(Conversation).delete()
        session.commit()
        session.close()
    except Exception as e:
        logger.error(f"Failed to clear history: {e}")
