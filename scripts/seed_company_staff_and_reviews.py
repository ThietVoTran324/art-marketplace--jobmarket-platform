"""Seed staff + alumni for jmco_* companies, plus English company reviews.

Creates (idempotent by username / comment marker):
- Per seeded hiring company (`jmco_01`… owners): 3 current staff + 2 alumni
  users with approved work_experiences (current = open-ended; alumni = ended).
- Extra: take up to 15 other eligible artists and attach 1 approved *former*
  WE at a random jmco company (if they don't already have a seed former WE).
- Company comments (English) from current staff + alumni so UI badges can be tested
  (blue = current, amber = former).

Usage:
  docker compose -f docker-compose.prod.yml exec -T \\
    -w /fastapi -e PYTHONPATH=/fastapi fastapi-app \\
    python -m scripts.seed_company_staff_and_reviews

  ... python -m scripts.seed_company_staff_and_reviews --force
"""

from __future__ import annotations

import argparse
import asyncio
import random
import sys
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select

from app.api.rest.roles import assign_role, get_user_roles
from app.api.rest.utils import hash_password
from app.postgresql.database import async_session_maker
from app.postgresql.models import CommentsOrm, CompaniesOrm, UsersOrm, WorkExperiencesOrm

PASSWORD = "SeedStaffPass123!"
EMPLOYER_PREFIX = "jmco_"
STAFF_PREFIX = "jmstaff_"
WE_MARKER = "[seed-staff-we]"
COMMENT_MARKER = "[seed-co-review]"
CURRENT_PER_COMPANY = 3
ALUMNI_PER_COMPANY = 2
EXTRA_ALUMNI_USERS = 15

TITLES = [
    "UI Designer",
    "UX Designer",
    "Brand Designer",
    "Illustrator",
    "Motion Designer",
    "Art Director",
    "Graphic Designer",
    "Design Systems Designer",
]

CURRENT_COMMENTS = [
    f"{COMMENT_MARKER} Really solid mentorship here — weekly critiques actually help me grow, not just polish slides.",
    f"{COMMENT_MARKER} Pace is intense but fair. Design QA with engineering is the best I've had so far.",
    f"{COMMENT_MARKER} Love the squad model. Clear ownership on projects and honest feedback culture.",
    f"{COMMENT_MARKER} Benefits are practical (gear stipend, learning budget). Leadership listens when process breaks.",
    f"{COMMENT_MARKER} Hybrid schedule works well. Still enough in-person workshops to keep craft sharp.",
]

FORMER_COMMENTS = [
    f"{COMMENT_MARKER} Left on good terms after two years. Strong portfolio pieces and fair exit process.",
    f"{COMMENT_MARKER} Great place to level up early-career craft. Communication got rocky during big pitches.",
    f"{COMMENT_MARKER} Alumni network is real — still collaborate with ex-colleagues on freelance briefs.",
    f"{COMMENT_MARKER} Would recommend for branding/art direction growth. Less ideal if you want deep product UX.",
    f"{COMMENT_MARKER} Management cared about people. Workload spiked each quarter-end; plan buffer weeks.",
    f"{COMMENT_MARKER} Transparent about scope changes. I moved on for remote-first lifestyle, not toxicity.",
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> date:
    return _now().date()


async def load_jmco_companies(session) -> list[tuple[CompaniesOrm, UsersOrm]]:
    owners = list(
        (
            await session.scalars(
                select(UsersOrm)
                .where(UsersOrm.username.like(f"{EMPLOYER_PREFIX}%"))
                .order_by(UsersOrm.username)
            )
        ).all()
    )
    out: list[tuple[CompaniesOrm, UsersOrm]] = []
    for owner in owners:
        company = await session.scalar(
            select(CompaniesOrm).where(
                CompaniesOrm.owner_user_id == owner.id,
                CompaniesOrm.status == "active",
            )
        )
        if company is not None:
            out.append((company, owner))
    return out


async def ensure_user(session, username: str, *, description: str) -> UsersOrm:
    user = await session.scalar(select(UsersOrm).where(UsersOrm.username == username))
    if user is None:
        user = UsersOrm(
            username=username,
            hashed_password=hash_password(PASSWORD),
            email=f"{username}@example.local",
            verified=True,
            description=description,
        )
        session.add(user)
        await session.flush()
        print(f"  + user {username} / {PASSWORD}")
    else:
        user.verified = True
        print(f"  = user exists {username}")
    await assign_role(session, user.id, "artist")
    return user


async def ensure_we(
    session,
    *,
    user_id: int,
    company: CompaniesOrm,
    title: str,
    current: bool,
    rng: random.Random,
) -> WorkExperiencesOrm | None:
    """Idempotent approved WE for staff/alumni seed."""
    existing = await session.scalar(
        select(WorkExperiencesOrm).where(
            WorkExperiencesOrm.user_id == user_id,
            WorkExperiencesOrm.company_id == company.id,
            WorkExperiencesOrm.description.like(f"{WE_MARKER}%"),
        )
    )
    if existing is not None:
        # Keep status/dates aligned for badge testing
        existing.status = "approved"
        if current:
            existing.end_date = None
        elif existing.end_date is None or existing.end_date >= _today():
            existing.end_date = _today() - timedelta(days=rng.randint(60, 800))
        return existing

    start = _today() - timedelta(days=rng.randint(400, 1600))
    end = None if current else (_today() - timedelta(days=rng.randint(30, 700)))
    if end is not None and end < start:
        start = end - timedelta(days=365)

    row = WorkExperiencesOrm(
        user_id=user_id,
        company_id=company.id,
        company_name=company.display_name,
        employment_type=rng.choice(
            ["full-time", "part-time", "hybrid", "collaborator"]
        ),
        title=title,
        description=(
            f"{WE_MARKER} Seed {'current' if current else 'alumni'} role at "
            f"{company.display_name}."
        )[:2000],
        location=company.industry or "Hybrid",
        start_date=start,
        end_date=end,
        status="approved",
    )
    session.add(row)
    await session.flush()
    print(
        f"  + WE {title} @ {company.display_name} "
        f"[{'current' if current else 'alumni'}] user_id={user_id}"
    )
    return row


async def ensure_comment(
    session,
    *,
    company_id: int,
    user_id: int,
    content: str,
) -> bool:
    exists = await session.scalar(
        select(CommentsOrm.id).where(
            CommentsOrm.company_id == company_id,
            CommentsOrm.user_id == user_id,
            CommentsOrm.comment_id.is_(None),
            CommentsOrm.content.like(f"{COMMENT_MARKER}%"),
        )
    )
    if exists is not None:
        return False
    session.add(
        CommentsOrm(
            company_id=company_id,
            user_id=user_id,
            pin_id=None,
            content=content[:400],
        )
    )
    return True


async def seed_dedicated_staff(
    session, companies: list[tuple[CompaniesOrm, UsersOrm]], rng: random.Random
) -> dict[str, int]:
    stats = {"users": 0, "we": 0, "comments": 0}
    for idx, (company, _owner) in enumerate(companies, start=1):
        # Current staff
        for i in range(1, CURRENT_PER_COMPANY + 1):
            uname = f"{STAFF_PREFIX}{idx:02d}_cur_{i}"
            user = await ensure_user(
                session,
                uname,
                description=f"Seed current staff for {company.display_name}",
            )
            stats["users"] += 1
            before = await session.scalar(
                select(func.count())
                .select_from(WorkExperiencesOrm)
                .where(
                    WorkExperiencesOrm.user_id == user.id,
                    WorkExperiencesOrm.company_id == company.id,
                    WorkExperiencesOrm.description.like(f"{WE_MARKER}%"),
                )
            )
            await ensure_we(
                session,
                user_id=user.id,
                company=company,
                title=rng.choice(TITLES),
                current=True,
                rng=rng,
            )
            after = await session.scalar(
                select(func.count())
                .select_from(WorkExperiencesOrm)
                .where(
                    WorkExperiencesOrm.user_id == user.id,
                    WorkExperiencesOrm.company_id == company.id,
                    WorkExperiencesOrm.description.like(f"{WE_MARKER}%"),
                )
            )
            if int(after or 0) > int(before or 0):
                stats["we"] += 1
            if await ensure_comment(
                session,
                company_id=company.id,
                user_id=user.id,
                content=rng.choice(CURRENT_COMMENTS),
            ):
                stats["comments"] += 1
                print(f"  + comment (current) by {uname} on company {company.id}")

        # Alumni
        for i in range(1, ALUMNI_PER_COMPANY + 1):
            uname = f"{STAFF_PREFIX}{idx:02d}_ex_{i}"
            user = await ensure_user(
                session,
                uname,
                description=f"Seed alumni for {company.display_name}",
            )
            stats["users"] += 1
            before = await session.scalar(
                select(func.count())
                .select_from(WorkExperiencesOrm)
                .where(
                    WorkExperiencesOrm.user_id == user.id,
                    WorkExperiencesOrm.company_id == company.id,
                    WorkExperiencesOrm.description.like(f"{WE_MARKER}%"),
                )
            )
            await ensure_we(
                session,
                user_id=user.id,
                company=company,
                title=rng.choice(TITLES),
                current=False,
                rng=rng,
            )
            after = await session.scalar(
                select(func.count())
                .select_from(WorkExperiencesOrm)
                .where(
                    WorkExperiencesOrm.user_id == user.id,
                    WorkExperiencesOrm.company_id == company.id,
                    WorkExperiencesOrm.description.like(f"{WE_MARKER}%"),
                )
            )
            if int(after or 0) > int(before or 0):
                stats["we"] += 1
            if await ensure_comment(
                session,
                company_id=company.id,
                user_id=user.id,
                content=rng.choice(FORMER_COMMENTS),
            ):
                stats["comments"] += 1
                print(f"  + comment (alumni) by {uname} on company {company.id}")

        await session.commit()
    return stats


async def load_extra_candidates(
    session, reserved_ids: set[int]
) -> list[UsersOrm]:
    owner_ids = set(
        (
            await session.scalars(
                select(CompaniesOrm.owner_user_id).where(
                    CompaniesOrm.owner_user_id.is_not(None)
                )
            )
        ).all()
    )
    users = list((await session.scalars(select(UsersOrm).order_by(UsersOrm.id))).all())
    out: list[UsersOrm] = []
    for u in users:
        if u.id in reserved_ids or u.id in owner_ids:
            continue
        if u.username.startswith(EMPLOYER_PREFIX) or u.username.startswith(STAFF_PREFIX):
            continue
        roles = await get_user_roles(session, u.id)
        if "admin" in roles:
            continue
        out.append(u)
    return out


async def seed_extra_alumni_reviews(
    session,
    companies: list[CompaniesOrm],
    rng: random.Random,
) -> dict[str, int]:
    stats = {"users": 0, "we": 0, "comments": 0}
    if not companies:
        return stats

    reserved = set()
    candidates = await load_extra_candidates(session, reserved)
    rng.shuffle(candidates)
    picked = candidates[:EXTRA_ALUMNI_USERS]
    print(f"extra alumni candidates picked={len(picked)}")

    for user in picked:
        company = rng.choice(companies)
        # Skip if already has seed former WE at this company
        existing = await session.scalar(
            select(WorkExperiencesOrm.id).where(
                WorkExperiencesOrm.user_id == user.id,
                WorkExperiencesOrm.company_id == company.id,
                WorkExperiencesOrm.description.like(f"{WE_MARKER}%"),
            )
        )
        if existing is None:
            await ensure_we(
                session,
                user_id=user.id,
                company=company,
                title=rng.choice(TITLES),
                current=False,
                rng=rng,
            )
            stats["we"] += 1
        else:
            # Force alumni for badge test
            we = await session.scalar(
                select(WorkExperiencesOrm).where(WorkExperiencesOrm.id == existing)
            )
            if we is not None:
                we.status = "approved"
                if we.end_date is None or we.end_date >= _today():
                    we.end_date = _today() - timedelta(days=rng.randint(90, 600))

        if await ensure_comment(
            session,
            company_id=company.id,
            user_id=user.id,
            content=rng.choice(FORMER_COMMENTS),
        ):
            stats["comments"] += 1
            print(
                f"  + extra alumni review by {user.username} on {company.display_name}"
            )
        stats["users"] += 1
        await session.commit()
    return stats


async def run(*, seed: int) -> None:
    rng = random.Random(seed)
    async with async_session_maker() as session:
        pairs = await load_jmco_companies(session)
        print(f"jmco companies={len(pairs)} seed={seed}")
        if not pairs:
            print(
                "ERROR: no jmco_* companies found — run seed_jobmarket_companies_jds first",
                file=sys.stderr,
            )
            sys.exit(1)

        dedicated = await seed_dedicated_staff(session, pairs, rng)
        companies_only = [c for c, _ in pairs]
        extra = await seed_extra_alumni_reviews(session, companies_only, rng)

        print(
            "\nDONE dedicated "
            f"users~={dedicated['users']} we+={dedicated['we']} comments+={dedicated['comments']}"
        )
        print(
            "DONE extra alumni "
            f"users={extra['users']} we+={extra['we']} comments+={extra['comments']}"
        )
        print(f"Login staff with password: {PASSWORD} (usernames {STAFF_PREFIX}*)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed jmco staff/alumni + English company reviews"
    )
    parser.add_argument("--seed", type=int, default=7, help="RNG seed")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Accepted for CLI compatibility; seed is already idempotent",
    )
    args = parser.parse_args()
    asyncio.run(run(seed=args.seed))


if __name__ == "__main__":
    main()
