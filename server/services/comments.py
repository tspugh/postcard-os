from sqlalchemy import select
from sqlalchemy.orm import Session

from server.errors import NotFound, ValidationRejected
from server.models import Business, COMMENT_ENTITIES, Comment, Email, Interaction, PostcardDraft
from server.services.serialize import comment_to_dict

_ENTITY_MODEL = {"email": Email, "postcard_slot": PostcardDraft, "business": Business}


def add_comment(
    session: Session,
    entity_type: str,
    entity_id,
    author: str,
    body: str,
    slot_number: int | None = None,
) -> dict:
    if entity_type not in COMMENT_ENTITIES:
        raise ValidationRejected(f"entity_type must be one of {', '.join(COMMENT_ENTITIES)}.")
    if not (body or "").strip():
        raise ValidationRejected("A comment needs a body.")
    if not (author or "").strip():
        raise ValidationRejected("A comment needs an author.")
    if entity_type == "postcard_slot" and slot_number is None:
        raise ValidationRejected("postcard_slot comments anchor to a slot: slot_number is required.")
    if entity_type != "postcard_slot" and slot_number is not None:
        raise ValidationRejected("slot_number only applies to postcard_slot comments.")
    target = session.get(_ENTITY_MODEL[entity_type], entity_id)
    if target is None:
        raise NotFound(f"No {entity_type} entity with id {entity_id} to comment on.")
    c = Comment(
        entity_type=entity_type,
        entity_id=entity_id,
        slot_number=slot_number,
        author=author.strip(),
        body=body,
    )
    session.add(c)
    # Comments are state-relevant events: land them in the card's timeline too
    # (postcard_slot comments are campaign-level — no business to anchor to).
    if entity_type == "email":
        session.add(
            Interaction(
                business_id=target.participation.business_id,
                participation_id=target.participation_id,
                type="comment_added",
                payload={"entity_type": "email", "author": c.author, "email_version": target.version, "body": body},
            )
        )
    elif entity_type == "business":
        session.add(
            Interaction(
                business_id=entity_id,
                type="comment_added",
                payload={"entity_type": "business", "author": c.author, "body": body},
            )
        )
    session.flush()
    return comment_to_dict(c)


def list_comments(session: Session, entity_type: str, entity_id, unresolved_only: bool = False) -> list[dict]:
    if entity_type not in COMMENT_ENTITIES:
        raise ValidationRejected(f"entity_type must be one of {', '.join(COMMENT_ENTITIES)}.")
    q = (
        select(Comment)
        .where(Comment.entity_type == entity_type, Comment.entity_id == entity_id)
        .order_by(Comment.created_at)
    )
    if unresolved_only:
        q = q.where(Comment.resolved.is_(False))
    return [comment_to_dict(c) for c in session.scalars(q)]


def resolve_comment(session: Session, comment_id, resolved: bool = True) -> dict:
    c = session.get(Comment, comment_id)
    if c is None:
        raise NotFound(f"No comment with id {comment_id}.")
    c.resolved = resolved
    session.flush()
    return comment_to_dict(c)
