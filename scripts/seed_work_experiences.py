"""Seed work experiences for existing users (Job Market profile soft-live).

Eligible users: everyone except
- role `admin`
- company owners (`companies.owner_user_id`)
- seed employer logins `jmco_%`

Rules (CHỐT):
- ~2 work experiences per eligible user (idempotent via description marker)
- 50% linked to an active in-system company (`company_id` set)
- 50% external (`company_id` null + free-text company_name)
- 80% `status=approved` (company-confirmed / shown verified)
- 20% `status=pending`
- employment_type / titles / descriptions realistic for design–art careers

Usage:
  docker compose -f docker-compose.prod.yml -f docker-compose.override.yml exec -T \\
    -w /fastapi -e PYTHONPATH=/fastapi fastapi-app \\
    python -m scripts.seed_work_experiences

  ... python -m scripts.seed_work_experiences --force   # refresh missing only; never dup titles
"""
from __future__ import annotations

import argparse
import asyncio
import random
import sys
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import func, select

from app.api.rest.roles import get_user_roles
from app.postgresql.database import async_session_maker
from app.postgresql.models import CompaniesOrm, UsersOrm, WorkExperiencesOrm

MARKER = "[seed-we]"
WE_PER_USER = 2
LINKED_RATIO = 0.50
APPROVED_RATIO = 0.80
EMPLOYER_USER_PREFIX = "jmco_"

EMPLOYMENT_TYPES = (
    "full-time",
    "part-time",
    "hybrid",
    "outsourcing",
    "collaborator",
)

EXTERNAL_COMPANIES = [
    "Studio Mai Vàng",
    "Red Bean Interactive",
    "Lotus Frame Media",
    "Night Owl Motion",
    "Cà Phê Design Lab",
    "Indigo Craft House",
    "Saigon Sketch Co.",
    "Asia Pacific Brand Lab",
    "Freelance Collective Asia",
    "Northern Lights Creative",
    "Paper Crane Publishing",
    "Orbit Product Studio",
]

ROLE_BANK = [
    {
        "title": "UI Designer",
        "description": (
            f"{MARKER} Thiết kế giao diện web/mobile, xây component Figma, "
            "hỗ trợ handoff và design QA trước release. Tham gia usability test nhẹ "
            "và iterate theo feedback sản phẩm."
        ),
    },
    {
        "title": "UX Designer",
        "description": (
            f"{MARKER} Nghiên cứu người dùng, dựng user flow/wireframe, "
            "đồng hành discovery với PM và validate giả thuyết bằng prototype."
        ),
    },
    {
        "title": "Brand Designer",
        "description": (
            f"{MARKER} Xây hệ nhận diện, guideline và ứng dụng brand lên "
            "collateral, packaging và social template cho nhiều touchpoint."
        ),
    },
    {
        "title": "Graphic Designer",
        "description": (
            f"{MARKER} Sản xuất key visual, deck, OOH và adapt asset đa format "
            "theo art direction; quản lý file export chuyên nghiệp."
        ),
    },
    {
        "title": "Illustrator",
        "description": (
            f"{MARKER} Minh họa character/editorial cho campaign và sản phẩm; "
            "phối hợp AD/motion để asset sẵn sàng animate hoặc in ấn."
        ),
    },
    {
        "title": "Motion Designer",
        "description": (
            f"{MARKER} Làm motion graphics/UI animation cho social và product "
            "storytelling; xuất bản đúng spec codec và brand motion language."
        ),
    },
    {
        "title": "Art Director",
        "description": (
            f"{MARKER} Định hướng thẩm mỹ campaign, review deliverable đội sáng tạo, "
            "bảo vệ big idea và tiêu chuẩn craft trước client."
        ),
    },
    {
        "title": "Product Designer",
        "description": (
            f"{MARKER} Sở hữu trải nghiệm một product area end-to-end; "
            "prototype, đo impact sau ship và đóng góp design system."
        ),
    },
    {
        "title": "Packaging Designer",
        "description": (
            f"{MARKER} Thiết kế bao bì và structural graphic; làm việc với "
            "supplier về dieline, finish và duyệt trước mass production."
        ),
    },
    {
        "title": "Content Designer",
        "description": (
            f"{MARKER} Viết microcopy/UX writing, empty states và content guideline; "
            "đảm bảo giọng điệu thương hiệu nhất quán trên sản phẩm."
        ),
    },
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _rand_dates(rng: random.Random) -> tuple[date, date | None]:
    """Return (start, end) with end None ~30% (current role)."""
    start_year = rng.randint(2016, 2023)
    start_month = rng.randint(1, 12)
    start = date(start_year, start_month, 1)
    if rng.random() < 0.30:
        return start, None
    end_year = rng.randint(start_year, 2025)
    end_month = rng.randint(1, 12)
    if end_year == start_year and end_month < start_month:
        end_month = start_month
    end = date(end_year, end_month, 28 if end_month == 2 else 1)
    if end < start:
        end = start
    return start, end


async def load_eligible_users(session) -> list[UsersOrm]:
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
        if u.username.startswith(EMPLOYER_USER_PREFIX):
            continue
        if u.id in owner_ids:
            continue
        roles = await get_user_roles(session, u.id)
        if "admin" in roles:
            continue
        out.append(u)
    return out


async def load_active_companies(session) -> list[CompaniesOrm]:
    return list(
        (
            await session.scalars(
                select(CompaniesOrm)
                .where(CompaniesOrm.status == "active")
                .order_by(CompaniesOrm.id)
            )
        ).all()
    )


async def existing_seed_count(session, user_id: int) -> int:
    return int(
        await session.scalar(
            select(func.count())
            .select_from(WorkExperiencesOrm)
            .where(
                WorkExperiencesOrm.user_id == user_id,
                WorkExperiencesOrm.description.like(f"{MARKER}%"),
            )
        )
        or 0
    )


def build_we_row(
    *,
    user_id: int,
    linked: bool,
    approved: bool,
    companies: list[CompaniesOrm],
    rng: random.Random,
) -> dict[str, Any]:
    role = rng.choice(ROLE_BANK)
    emp = rng.choice(EMPLOYMENT_TYPES)
    start, end = _rand_dates(rng)
    status = "approved" if approved else "pending"

    if linked and companies:
        company = rng.choice(companies)
        return {
            "user_id": user_id,
            "company_id": company.id,
            "company_name": company.display_name,
            "employment_type": emp,
            "title": role["title"],
            "description": role["description"][:2000],
            "location": company.industry or "Remote / Hybrid",
            "start_date": start,
            "end_date": end,
            "status": status,
        }

    ext = rng.choice(EXTERNAL_COMPANIES)
    return {
        "user_id": user_id,
        "company_id": None,
        "company_name": ext,
        "employment_type": emp,
        "title": role["title"],
        "description": role["description"][:2000],
        "location": rng.choice(
            ["Ho Chi Minh City", "Hanoi", "Da Nang", "Remote", "Singapore", "Berlin"]
        ),
        "start_date": start,
        "end_date": end,
        "status": status,
    }


async def seed_for_user(
    session,
    user: UsersOrm,
    *,
    companies: list[CompaniesOrm],
    rng: random.Random,
    force: bool,
) -> tuple[int, int, int]:
    """Returns (created, linked_n, approved_n)."""
    have = await existing_seed_count(session, user.id)
    need = WE_PER_USER - have
    if need <= 0 and not force:
        print(f"  = {user.username}: already {have} seed WE")
        return 0, 0, 0
    if need <= 0:
        print(f"  = {user.username}: skip (have {have})")
        return 0, 0, 0

    created = linked_n = approved_n = 0
    for i in range(need):
        # Decide linked/approved with global intent approximated per-row.
        linked = rng.random() < LINKED_RATIO
        approved = rng.random() < APPROVED_RATIO
        row = build_we_row(
            user_id=user.id,
            linked=linked,
            approved=approved,
            companies=companies,
            rng=rng,
        )
        # Avoid exact dup title+company for same user
        clash = await session.scalar(
            select(WorkExperiencesOrm.id).where(
                WorkExperiencesOrm.user_id == user.id,
                WorkExperiencesOrm.title == row["title"],
                WorkExperiencesOrm.company_name == row["company_name"],
                WorkExperiencesOrm.description.like(f"{MARKER}%"),
            )
        )
        if clash is not None:
            # tweak title slightly
            row["title"] = f"{row['title']} ({row['start_date'].year})"

        session.add(WorkExperiencesOrm(**row))
        created += 1
        if row["company_id"] is not None:
            linked_n += 1
        if row["status"] == "approved":
            approved_n += 1
        print(
            f"  + {user.username}: {row['title']} @ {row['company_name']} "
            f"[{row['status']}]{' linked' if row['company_id'] else ' external'}"
        )
    return created, linked_n, approved_n


async def run(*, force: bool, seed: int) -> None:
    rng = random.Random(seed)
    async with async_session_maker() as session:
        users = await load_eligible_users(session)
        companies = await load_active_companies(session)
        print(f"eligible_users={len(users)} active_companies={len(companies)} seed={seed}")
        if not users:
            print("ERROR: no eligible users", file=sys.stderr)
            sys.exit(1)
        if not companies:
            print(
                "WARN: no active companies — all WE will be external",
                file=sys.stderr,
            )

        total_c = total_l = total_a = 0
        for u in users:
            created, linked_n, approved_n = await seed_for_user(
                session,
                u,
                companies=companies,
                rng=rng,
                force=force,
            )
            await session.commit()
            total_c += created
            total_l += linked_n
            total_a += approved_n

        print(
            f"\nDONE created={total_c} linked={total_l} approved={total_a} "
            f"(targets ~{int(LINKED_RATIO*100)}% linked, ~{int(APPROVED_RATIO*100)}% approved)"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed work experiences for artists")
    parser.add_argument("--force", action="store_true", help="Reserved; fill up to WE_PER_USER")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed for reproducibility")
    args = parser.parse_args()
    asyncio.run(run(force=args.force, seed=args.seed))


if __name__ == "__main__":
    main()
