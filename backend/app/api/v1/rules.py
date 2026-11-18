from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.entities import ClassificationRule
from app.schemas.api_schemas import (
    ClassificationRuleCreate,
    ClassificationRuleResponse,
    ClassificationRuleUpdate,
)

router = APIRouter(prefix="/rules", tags=["Tier 1 Classification Rules"])


@router.get("", response_model=List[ClassificationRuleResponse])
async def list_rules(db: AsyncSession = Depends(get_db)):
    stmt = select(ClassificationRule).order_by(
        ClassificationRule.priority.asc(), ClassificationRule.id.asc()
    )
    rows = (await db.execute(stmt)).scalars().all()
    return list(rows)


@router.post("", response_model=ClassificationRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    payload: ClassificationRuleCreate, db: AsyncSession = Depends(get_db)
):
    existing = (
        await db.execute(
            select(ClassificationRule).where(ClassificationRule.name == payload.name)
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Rule with name '{payload.name}' already exists",
        )
    rule = ClassificationRule(
        name=payload.name,
        description=payload.description,
        priority=payload.priority,
        is_active=payload.is_active,
        sender_domain=payload.sender_domain,
        sender_email=payload.sender_email,
        subject_regex=payload.subject_regex,
        snippet_regex=payload.snippet_regex,
        header_key=payload.header_key,
        header_regex=payload.header_regex,
        target_category=payload.target_category.value,
        target_severity=payload.target_severity.value,
        target_ttl=payload.target_ttl.value,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.patch("/{rule_id}", response_model=ClassificationRuleResponse)
async def update_rule(
    rule_id: int,
    payload: ClassificationRuleUpdate,
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(ClassificationRule).where(ClassificationRule.id == rule_id))
    rule = res.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")

    update_data = payload.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        if hasattr(v, "value"):
            setattr(rule, k, v.value)
        else:
            setattr(rule, k, v)

    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ClassificationRule).where(ClassificationRule.id == rule_id))
    rule = res.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    await db.delete(rule)
    await db.commit()
    return None
