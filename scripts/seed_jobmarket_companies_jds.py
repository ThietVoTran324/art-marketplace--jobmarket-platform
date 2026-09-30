"""Seed 10 hiring companies + 5 professional design/art JDs each (Job Market soft-live).

Creates for each company:
- employer user (verified email) + role `employer`
- `companies` row status=active (demo bypass KYC queue) with full legal/profile fields
- primary branch (HQ address)
- 5 `job_posts` (status=active) with full description / requirements / benefits
- `job_post_locations` linked to the HQ branch

Idempotent: usernames `jmco_01` … `jmco_10`. Re-run skips existing users/companies
unless `--force` (force still skips duplicate JD titles under same company).

Usage:
  docker compose -f docker-compose.prod.yml -f docker-compose.override.yml exec -T \\
    -w /fastapi -e PYTHONPATH=/fastapi fastapi-app \\
    python -m scripts.seed_jobmarket_companies_jds

  ... python -m scripts.seed_jobmarket_companies_jds --force
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from app.api.rest.job_market.helpers import normalize_registration_number
from app.api.rest.roles import assign_role
from app.api.rest.utils import hash_password
from app.postgresql.database import async_session_maker
from app.postgresql.models import (
    CompaniesOrm,
    CompanyBranchesOrm,
    JobPostLocationsOrm,
    JobPostsOrm,
    UsersOrm,
)

PASSWORD = "SeedCoPass123!"
USER_PREFIX = "jmco_"
COMPANY_COUNT = 10
JDS_PER_COMPANY = 5


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Company catalog (mix VN + international creative studios)
# ---------------------------------------------------------------------------

COMPANIES: list[dict[str, Any]] = [
    {
        "username": "jmco_01",
        "display_name": "Atelier Sài Gòn Visual",
        "industry": "Design Studio",
        "description": (
            "Atelier Sài Gòn Visual là studio thiết kế độc lập tại Quận 1, chuyên "
            "brand identity, packaging và campaign visual cho FMCG cùng startup công nghệ. "
            "Chúng tôi làm việc theo mô hình squad nhỏ, kết hợp research thị trường Việt Nam "
            "với aesthetic đương đại, và thường xuyên collab với illustrator/photographer local."
        ),
        "size_min": 11,
        "size_max": 50,
        "website": "https://ateliersaigon.example",
        "domain": "ateliersaigon.example",
        "registration_country": "VN",
        "registration_type": "ENTERPRISE",
        "registration_number_raw": "0318123401",
        "tax_id": "0318123401",
        "branch": {
            "label": "HQ District 1",
            "address_line": "48 Nguyễn Huệ, Bến Nghé, Quận 1",
            "city": "Ho Chi Minh City",
            "country": "VN",
        },
        "currency": "VND",
        "jd_keys": ["uiux", "brand", "illustrator", "art_director", "graphic"],
    },
    {
        "username": "jmco_02",
        "display_name": "Hanoi Pixel Collective",
        "industry": "Digital Product Design",
        "description": (
            "Hanoi Pixel Collective xây dựng sản phẩm số cho fintech và edtech: "
            "từ discovery workshop, design system đến handoff với engineering. "
            "Văn hóa studio chú trọng critique định kỳ, accessibility, và đo lường "
            "impact bằng usability metric thay vì chỉ 'làm đẹp UI'."
        ),
        "size_min": 21,
        "size_max": 100,
        "website": "https://hanoipixel.example",
        "domain": "hanoipixel.example",
        "registration_country": "VN",
        "registration_type": "ENTERPRISE",
        "registration_number_raw": "0109876543",
        "tax_id": "0109876543",
        "branch": {
            "label": "HQ Cầu Giấy",
            "address_line": "Tầng 8, 18 Phạm Hùng, Mỹ Đình",
            "city": "Hanoi",
            "country": "VN",
        },
        "currency": "VND",
        "jd_keys": ["product", "uiux", "motion", "content", "design_system"],
    },
    {
        "username": "jmco_03",
        "display_name": "Đông Nam Creative Agency",
        "industry": "Advertising / Branding",
        "description": (
            "Agency full-service phục vụ ngành F&B, bất động sản và lifestyle. "
            "Team sáng tạo đảm nhận big idea, art direction, social content và "
            "production supervision. Chúng tôi ưu tiên storytelling rõ insight Việt "
            "và delivery có thể scale multi-channel."
        ),
        "size_min": 51,
        "size_max": 200,
        "website": "https://dongnamcreative.example",
        "domain": "dongnamcreative.example",
        "registration_country": "VN",
        "registration_type": "ENTERPRISE",
        "registration_number_raw": "0305566778",
        "tax_id": "0305566778",
        "branch": {
            "label": "Studio Thảo Điền",
            "address_line": "21 Quốc Hương, Thảo Điền, TP. Thủ Đức",
            "city": "Ho Chi Minh City",
            "country": "VN",
        },
        "currency": "VND",
        "jd_keys": ["art_director", "brand", "motion", "graphic", "illustrator"],
    },
    {
        "username": "jmco_04",
        "display_name": "Lạc Hồng Type Foundry",
        "industry": "Typography / Editorial",
        "description": (
            "Studio chuyên type design, editorial layout và custom lettering cho "
            "nhà xuất bản, bảo tàng và thương hiệu văn hóa. Dự án điển hình gồm "
            "bộ chữ tiếng Việt tối ưu đọc báo chí và hệ thống identity cho festival nghệ thuật."
        ),
        "size_min": 5,
        "size_max": 20,
        "website": "https://lachongtype.example",
        "domain": "lachongtype.example",
        "registration_country": "VN",
        "registration_type": "ENTERPRISE",
        "registration_number_raw": "0401122334",
        "tax_id": "0401122334",
        "branch": {
            "label": "Workshop Hải Châu",
            "address_line": "112 Bạch Đằng, Hải Châu",
            "city": "Da Nang",
            "country": "VN",
        },
        "currency": "VND",
        "jd_keys": ["typography", "graphic", "illustrator", "brand", "editorial"],
    },
    {
        "username": "jmco_05",
        "display_name": "Mekong Motion Lab",
        "industry": "Motion / Animation",
        "description": (
            "Lab sản xuất motion graphics, 2D/3D short-form và title design cho "
            "OTT, game trailer và brand film. Pipeline dùng After Effects, Cinema 4D "
            "và Blender; có technical art coach và review theo shot."
        ),
        "size_min": 11,
        "size_max": 50,
        "website": "https://mekongmotion.example",
        "domain": "mekongmotion.example",
        "registration_country": "VN",
        "registration_type": "ENTERPRISE",
        "registration_number_raw": "3609988776",
        "tax_id": "3609988776",
        "branch": {
            "label": "Prod House Bình Thạnh",
            "address_line": "88 Xô Viết Nghệ Tĩnh, Phường 21",
            "city": "Ho Chi Minh City",
            "country": "VN",
        },
        "currency": "VND",
        "jd_keys": ["motion", "character", "art_director", "illustrator", "uiux"],
    },
    {
        "username": "jmco_06",
        "display_name": "Sông Hồng Brandworks",
        "industry": "Brand Strategy & Design",
        "description": (
            "Tư vấn định vị thương hiệu và hệ nhận diện cho SME mở rộng khu vực. "
            "Quy trình gồm audit, brand platform, visual system và brand guideline "
            "bàn giao kèm asset kit cho in-house marketing."
        ),
        "size_min": 11,
        "size_max": 50,
        "website": "https://songhongbrand.example",
        "domain": "songhongbrand.example",
        "registration_country": "VN",
        "registration_type": "ENTERPRISE",
        "registration_number_raw": "0104455667",
        "tax_id": "0104455667",
        "branch": {
            "label": "HQ Hoàn Kiếm",
            "address_line": "27 Hàng Bài, Hoàn Kiếm",
            "city": "Hanoi",
            "country": "VN",
        },
        "currency": "VND",
        "jd_keys": ["brand", "graphic", "uiux", "content", "art_director"],
    },
    {
        "username": "jmco_07",
        "display_name": "Northwind Studio Berlin",
        "industry": "Product Design",
        "description": (
            "Berlin-based product design studio partnering with European SaaS scale-ups. "
            "We ship end-to-end product UX, design systems, and growth experimentation "
            "with bilingual (EN/DE) documentation and remote-first rituals."
        ),
        "size_min": 21,
        "size_max": 80,
        "website": "https://northwind.studio",
        "domain": "northwind.studio",
        "registration_country": "DE",
        "registration_type": "GMBH",
        "registration_number_raw": "HRB 214567",
        "tax_id": "DE312345678",
        "vat_number": "DE312345678",
        "branch": {
            "label": "HQ Kreuzberg",
            "address_line": "Oranienstraße 42",
            "city": "Berlin",
            "country": "DE",
        },
        "currency": "USD",
        "jd_keys": ["product", "uiux", "design_system", "motion", "content"],
    },
    {
        "username": "jmco_08",
        "display_name": "Harbor & Grain Design Co.",
        "industry": "Brand / Packaging",
        "description": (
            "Independent branding house in Singapore focusing on F&B packaging, "
            "retail environments, and campaign art direction across APAC markets. "
            "Known for tactile print craft mixed with digital-first asset systems."
        ),
        "size_min": 11,
        "size_max": 40,
        "website": "https://harborgrain.design",
        "domain": "harborgrain.design",
        "registration_country": "SG",
        "registration_type": "PTE_LTD",
        "registration_number_raw": "201912345A",
        "tax_id": "201912345A",
        "branch": {
            "label": "Studio Chinatown",
            "address_line": "18 Mosque Street #03-01",
            "city": "Singapore",
            "country": "SG",
        },
        "currency": "USD",
        "jd_keys": ["brand", "packaging", "illustrator", "art_director", "graphic"],
    },
    {
        "username": "jmco_09",
        "display_name": "Lumen Frame Interactive",
        "industry": "Game / Interactive Art",
        "description": (
            "Interactive art and game UI studio delivering HUD systems, character "
            "concepts, and cinematic key art for mid-core mobile and PC titles. "
            "Hybrid team across Lisbon and remote EU contractors."
        ),
        "size_min": 21,
        "size_max": 70,
        "website": "https://lumenframe.interactive",
        "domain": "lumenframe.interactive",
        "registration_country": "PT",
        "registration_type": "LDA",
        "registration_number_raw": "514987321",
        "tax_id": "PT514987321",
        "vat_number": "PT514987321",
        "branch": {
            "label": "Studio Alcântara",
            "address_line": "Rua da Junqueira 39",
            "city": "Lisbon",
            "country": "PT",
        },
        "currency": "USD",
        "jd_keys": ["character", "uiux", "illustrator", "motion", "art_director"],
    },
    {
        "username": "jmco_10",
        "display_name": "Cascade Type & Interface",
        "industry": "Design Systems / Typography",
        "description": (
            "US West Coast practice specializing in interface typography, "
            "multi-brand design systems, and documentation for design-engineering parity. "
            "Clients include B2B platforms that need scalable token architecture."
        ),
        "size_min": 11,
        "size_max": 60,
        "website": "https://cascadetype.io",
        "domain": "cascadetype.io",
        "registration_country": "US",
        "registration_type": "LLC",
        "registration_number_raw": "88-4455667",
        "tax_id": "88-4455667",
        "branch": {
            "label": "HQ Portland",
            "address_line": "920 SW 6th Avenue, Suite 400",
            "city": "Portland",
            "country": "US",
        },
        "currency": "USD",
        "jd_keys": ["design_system", "typography", "uiux", "product", "content"],
    },
]


def _jd_bank(company: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Professional JD templates keyed by role; text tailored to company."""
    name = company["display_name"]
    city = company["branch"]["city"]
    cur = company["currency"]

    def sal_vnd(lo: int, hi: int) -> dict[str, Any]:
        return {
            "salary_mode": "range",
            "salary_min": lo,
            "salary_max": hi,
            "currency": "VND",
        }

    def sal_usd(lo: int, hi: int) -> dict[str, Any]:
        return {
            "salary_mode": "range",
            "salary_min": lo,
            "salary_max": hi,
            "currency": "USD",
        }

    def sal_love() -> dict[str, Any]:
        return {
            "salary_mode": "love_it",
            "salary_min": None,
            "salary_max": None,
            "currency": cur,
        }

    pay = sal_vnd if cur == "VND" else sal_usd

    return {
        "uiux": {
            "title": "Senior UI/UX Designer",
            "years_experience": 4,
            **(pay(25000000, 45000000) if cur == "VND" else pay(4500, 7500)),
            "description": (
                f"{name} đang tìm Senior UI/UX Designer làm việc tại {city}, "
                "chịu trách nhiệm end-to-end cho 1–2 product surface chính.\n\n"
                "Bạn sẽ dẫn dắt discovery (interview, usability test), xây user flow/"
                "wireframe/hi-fi, duy trì component trong Figma, và partner sát với PM "
                "cùng engineering để ship theo sprint. Vai trò này không chỉ 'vẽ màn hình' — "
                "bạn cần bảo vệ chất lượng trải nghiệm, đề xuất trade-off rõ ràng, và "
                "document quyết định thiết kế để team scale.\n\n"
                "Môi trường: critique 2 tuần/lần, design QA trước release, và thời gian "
                "dành cho craft/research không bị cắt bởi pure production."
            ),
            "requirements": (
                "- 4+ năm kinh nghiệm product/UI-UX (web hoặc mobile), có case study shipped.\n"
                "- Thành thạo Figma (auto-layout, variants, design tokens, prototyping).\n"
                "- Biết lập kế hoạch research nhẹ (guerrilla test, survey, heuristic review).\n"
                "- Hiểu accessibility cơ bản (contrast, focus order, touch target).\n"
                "- Giao tiếp rõ bằng tiếng Việt và/hoặc English tùy stakeholder.\n"
                "- Portfolio bắt buộc: 2–3 case thể hiện problem → insight → solution → impact."
            ),
            "benefits": (
                "- Lương theo band role + 13th month / performance bonus theo chính sách công ty.\n"
                "- Hybrid hoặc remote linh hoạt theo sprint (thỏa thuận khi offer).\n"
                "- Ngân sách tool (Figma seat, plugin) và học online 1 khóa/năm.\n"
                "- Thiết bị làm việc + hỗ trợ coworking khi cần workshop onsite.\n"
                "- Môi trường critique xây dựng, không blame culture."
            ),
        },
        "brand": {
            "title": "Brand Designer",
            "years_experience": 3,
            **(pay(18000000, 35000000) if cur == "VND" else pay(3800, 6200)),
            "description": (
                f"Vị trí Brand Designer tại {name} phụ trách mở rộng và bảo vệ hệ nhận diện "
                f"thương hiệu cho client/portfolio tại {city}.\n\n"
                "Công việc gồm xây visual platform (logo system, color, type, imagery), "
                "ứng dụng lên collaterals, social templates, pitch deck và guideline. "
                "Bạn làm việc sát Brand Strategist/AD để đảm bảo mỗi deliverable nhất quán "
                "với positioning, đồng thời đủ linh hoạt cho team marketing vận hành hàng ngày.\n\n"
                "Chúng tôi kỳ vọng tư duy hệ thống: không chỉ 'một logo đẹp' mà là bộ quy tắc "
                "giúp brand sống được trên nhiều touchpoint."
            ),
            "requirements": (
                "- 3+ năm brand/visual identity (agency hoặc in-house).\n"
                "- Portfolio có ít nhất một full identity system (không chỉ logo mark).\n"
                "- Thành thạo Illustrator, InDesign/Figma; hiểu print production cơ bản.\n"
                "- Nhạy insight văn hóa địa phương (ưu tiên nếu đã làm thị trường VN/APAC).\n"
                "- Có thể trình bày rational thiết kế trước client một cách súc tích."
            ),
            "benefits": (
                "- Project bonus theo milestone campaign lớn.\n"
                "- Cơ hội dẫn art direction cho pitch/new business.\n"
                "- Studio visit / print house tour định kỳ.\n"
                "- BHXH đầy đủ (VN) hoặc tương đương theo quốc gia đăng ký.\n"
                "- Lịch nghỉ phép cạnh tranh + ngày creative off sau deadline lớn."
            ),
        },
        "illustrator": {
            "title": "Illustrator / Concept Artist",
            "years_experience": 3,
            **(pay(16000000, 32000000) if cur == "VND" else pay(3500, 6000)),
            "description": (
                f"{name} tuyển Illustrator/Concept Artist để sản xuất visual kể chuyện "
                f"cho campaign, sản phẩm và editorial tại {city}.\n\n"
                "Bạn phát triển styleframe, character/environment concept, và final illustration "
                "theo brief art direction. Làm việc với AD/Motion để đảm bảo asset sẵn sàng "
                "cho animation hoặc print. Chúng tôi đề cao khả năng iterate nhanh theo feedback "
                "mà vẫn giữ được chất lượng nghệ thuật và narrative rõ."
            ),
            "requirements": (
                "- Portfolio illustration/concept mạnh (digital; traditional là điểm cộng).\n"
                "- Thành thạo Photoshop/Procreate/Clip Studio; biết vector là lợi thế.\n"
                "- Hiểu light, anatomy, composition và visual storytelling.\n"
                "- Làm việc được dưới deadline campaign; quản lý version file chuyên nghiệp.\n"
                "- Open với direction thay đổi mà không defensive."
            ),
            "benefits": (
                "- Credit nghệ thuật trên case study công khai (khi NDA cho phép).\n"
                "- Thời gian dành cho personal style exploration mỗi quý.\n"
                "- Tablet/pen display hỗ trợ theo nhu cầu role.\n"
                "- Community critique nội bộ với guest artist thỉnh thoảng."
            ),
        },
        "art_director": {
            "title": "Art Director",
            "years_experience": 6,
            **(pay(35000000, 60000000) if cur == "VND" else pay(6500, 10000)),
            "description": (
                f"Art Director tại {name} định hướng thẩm mỹ tổng thể cho pitching và "
                f"delivery tại {city}.\n\n"
                "Bạn dẫn dắt đội designer/illustrator/motion, set look & feel, review "
                "từng key visual, và bảo vệ big idea trước client. Vai trò kết nối strategy "
                "với craft: translate brief thành moodboard, art bible, và tiêu chuẩn QA "
                "trước khi asset ra production. Kỳ vọng leadership bằng ví dụ — vẫn làm tay "
                "được khi cần set bar."
            ),
            "requirements": (
                "- 6+ năm trong creative (trong đó 2+ năm AD hoặc lead).\n"
                "- Portfolio campaign/brand có storytelling và craft xuất sắc.\n"
                "- Kinh nghiệm manage 3–8 creative; biết phân việc và feedback cụ thể.\n"
                "- Hiểu production (print, social, motion) đủ để estimate và tránh rework.\n"
                "- Đàm phán scope/change request với account một cách chuyên nghiệp."
            ),
            "benefits": (
                "- Quyền quyết định creative trong squad được phân công.\n"
                "- Thưởng theo win pitch / campaign performance.\n"
                "- Ngân sách research trip / exhibition khi liên quan dự án.\n"
                "- Lộ trình lên Head of Art / Creative Director rõ ràng."
            ),
        },
        "graphic": {
            "title": "Graphic Designer",
            "years_experience": 2,
            **(pay(12000000, 25000000) if cur == "VND" else pay(2800, 4500)),
            "description": (
                f"Graphic Designer hỗ trợ đội sáng tạo {name} sản xuất collateral "
                f"và digital asset hằng ngày tại {city}.\n\n"
                "Phạm vi: social key visual, presentation, OOH layout, email header, "
                "và adapt template theo brand guideline. Bạn làm việc dưới sự dẫn dắt của "
                "Brand Designer/AD, học cách giữ consistency và tốc độ trên nhiều format."
            ),
            "requirements": (
                "- 2+ năm graphic design; portfolio đa dạng print + digital.\n"
                "- Thành thạo Illustrator, Photoshop, Figma hoặc InDesign.\n"
                "- Hiểu hierarchy, grid, typography cơ bản.\n"
                "- Cẩn thận file prep (export spec, naming, folder hygiene).\n"
                "- Thái độ học hỏi và chịu được feedback iterate."
            ),
            "benefits": (
                "- Mentorship 1:1 với senior designer.\n"
                "- Cơ hội tham gia pitch khi tiến bộ.\n"
                "- Phụ cấp ăn trưa / remote allowance tùy site.\n"
                "- Đánh giá tăng band sau 12 tháng nếu đạt expectation."
            ),
        },
        "motion": {
            "title": "Motion Graphic Designer",
            "years_experience": 3,
            **(pay(18000000, 38000000) if cur == "VND" else pay(4000, 7000)),
            "description": (
                f"{name} cần Motion Designer xây dựng ngôn ngữ chuyển động cho brand "
                f"và product storytelling tại {city}.\n\n"
                "Bạn nhận styleframe từ AD/Illustrator, animate theo timing rõ ràng, "
                "xuất bản cho social, landing, và presentation. Ưu tiên motion có mục đích "
                "(hướng sự chú ý, giải thích sản phẩm) hơn effect thừa."
            ),
            "requirements": (
                "- 3+ năm motion (After Effects bắt buộc; Cinema 4D/Blender là cộng).\n"
                "- Demo reel 45–90s thể hiện typography motion và UI animation.\n"
                "- Hiểu frame rate, easing, export codec cho web/social.\n"
                "- Làm việc được với design tokens/color từ Figma.\n"
                "- Chủ động estimate giờ và flag risk sớm."
            ),
            "benefits": (
                "- Workstation cấu hình phù hợp render.\n"
                "- Plugin/license cần thiết do công ty chi trả.\n"
                "- Thời gian R&D kỹ thuật mỗi sprint.\n"
                "- Cơ hội lead motion cho campaign flagship."
            ),
        },
        "product": {
            "title": "Product Designer",
            "years_experience": 4,
            **(pay(28000000, 50000000) if cur == "VND" else pay(5000, 8500)),
            "description": (
                f"Product Designer tại {name} sở hữu trải nghiệm end-to-end cho một "
                f"product area tại {city}, từ problem framing đến release.\n\n"
                "Bạn phối hợp PM để ưu tiên roadmap, prototype giả thuyết, chạy test, "
                "và đo kết quả sau ship. Design system được dùng như nền — bạn đóng góp "
                "pattern mới khi product yêu cầu, kèm documentation cho engineering."
            ),
            "requirements": (
                "- 4+ năm product design trong môi trường agile/scrum.\n"
                "- Portfolio có metric/impact (conversion, retention, task success…).\n"
                "- Thành thạo Figma + prototyping; biết đủ HTML/CSS để nói chuyện với FE.\n"
                "- Kinh nghiệm design system hoặc contribution vào shared library.\n"
                "- Tư duy ưu tiên: biết nói không với scope làm loãng giá trị."
            ),
            "benefits": (
                "- Ảnh hưởng trực tiếp lên roadmap sản phẩm.\n"
                "- Pair với researcher khi có dự án lớn.\n"
                "- Conference/ticket budget hàng năm.\n"
                "- Flexible hours quanh core collaboration window."
            ),
        },
        "design_system": {
            "title": "Design System Designer",
            "years_experience": 4,
            **(pay(30000000, 52000000) if cur == "VND" else pay(5500, 9000)),
            "description": (
                f"Vai trò Design System Designer giúp {name} scale UI nhất quán "
                f"giữa nhiều squad tại {city}.\n\n"
                "Bạn quản lý token (color, type, space), component API, documentation, "
                "và governance (contribution model, versioning). Làm việc với FE để "
                "đồng bộ Figma ↔ code, giảm drift, và hỗ trợ adoption cho product designer."
            ),
            "requirements": (
                "- 4+ năm UI/product, trong đó 1–2 năm focus design system.\n"
                "- Thành thạo Figma libraries, tokens, theming.\n"
                "- Hiểu accessibility và responsive behavior của component.\n"
                "- Viết documentation rõ (do/don't, usage guidelines).\n"
                "- Kinh nghiệm làm việc với engineers (Storybook/token pipeline là cộng)."
            ),
            "benefits": (
                "- Ownership rõ ràng lên system roadmap.\n"
                "- Ảnh hưởng cross-team cao.\n"
                "- Hỗ trợ tool/automation liên quan system.\n"
                "- Peer review với design community bên ngoài khi phù hợp."
            ),
        },
        "content": {
            "title": "Content Designer / UX Writer",
            "years_experience": 3,
            **(pay(15000000, 30000000) if cur == "VND" else pay(3200, 5500)),
            "description": (
                f"{name} tuyển Content Designer để nâng chất lượng microcopy và "
                f"nội dung sản phẩm tại {city}.\n\n"
                "Bạn viết UI copy, empty/error states, onboarding, và content guideline. "
                "Phối hợp designer/PM để language hỗ trợ task completion, giọng điệu "
                "thương hiệu nhất quán, và giảm ambiguity trong flow phức tạp."
            ),
            "requirements": (
                "- 3+ năm UX writing / content design / editorial cho sản phẩm số.\n"
                "- Portfolio mẫu copy trong context UI (không chỉ bài blog).\n"
                "- Hiểu information architecture và plain language.\n"
                "- Làm việc được song ngữ (VN+EN hoặc EN) tùy market của studio.\n"
                "- Có kinh nghiệm content style guide là lợi thế."
            ),
            "benefits": (
                "- Ngồi chung squad product, không bị cô lập.\n"
                "- Ảnh hưởng tới voice & tone của brand/product.\n"
                "- Ngân sách sách/course writing.\n"
                "- Hybrid làm việc."
            ),
        },
        "typography": {
            "title": "Type Designer / Editorial Designer",
            "years_experience": 4,
            **(pay(20000000, 40000000) if cur == "VND" else pay(4200, 7200)),
            "description": (
                f"Type/Editorial Designer tại {name} phát triển chữ và layout "
                f"cho xuất bản phẩm, identity và interface typography tại {city}.\n\n"
                "Bạn làm việc trên glyph set, kerning, và ứng dụng type vào "
                "editorial/grid system. Dự án yêu cầu độ chính xác cao và hiểu "
                "đọc tiếng Việt/Latin tùy brief."
            ),
            "requirements": (
                "- 4+ năm type design hoặc editorial design chuyên sâu.\n"
                "- Thành thạo Glyphs/FontLab hoặc InDesign editorial workflow.\n"
                "- Portfolio thể hiện độ tinh trên letterforms và hierarchy.\n"
                "- Kiên nhĩ với iterate chi tiết và QA in ấn.\n"
                "- Hiểu licensing font cơ bản."
            ),
            "benefits": (
                "- Thời gian deep-work bảo vệ cho craft.\n"
                "- Cơ hội phát hành typeface dưới thương hiệu studio (thỏa thuận).\n"
                "- Công cụ phần mềm chuyên dụng được cấp.\n"
                "- Môi trường peer review chất lượng cao."
            ),
        },
        "character": {
            "title": "Character Designer",
            "years_experience": 3,
            **(pay(17000000, 34000000) if cur == "VND" else pay(3600, 6500)),
            "description": (
                f"Character Designer phát triển nhân vật cho dự án interactive/"
                f"campaign của {name} tại {city}.\n\n"
                "Từ silhouette, expression sheet đến turnaround và costume variation, "
                "bạn đảm bảo nhân vật đọc rõ trên nhiều kích thước và sẵn sàng "
                "cho animation/rig. Làm việc với AD và narrative lead."
            ),
            "requirements": (
                "- Portfolio character design đa dạng (stylized và semi-real).\n"
                "- Hiểu anatomy, appeal, silhouette reading.\n"
                "- Thành thạo digital painting; biết prepare asset cho motion/3D là cộng.\n"
                "- Làm việc theo style bible và iteration nhanh.\n"
                "- Có kinh nghiệm game/animation là lợi thế."
            ),
            "benefits": (
                "- Credit trên title/art book khi áp dụng.\n"
                "- Mentorship từ art director giàu kinh nghiệm IP.\n"
                "- Thiết bị và phần mềm phù hợp.\n"
                "- Môi trường sáng tạo tôn trọng originality."
            ),
        },
        "packaging": {
            "title": "Packaging Designer",
            "years_experience": 3,
            **(pay(16000000, 33000000) if cur == "VND" else pay(3500, 6000)),
            "description": (
                f"Packaging Designer tại {name} thiết kế bao bì và structural graphic "
                f"cho thương hiệu F&B/retail tại {city}.\n\n"
                "Bạn cân bằng storytelling trên shelf với ràng buộc sản xuất "
                "(dieline, finish, cost). Phối hợp supplier và brand team để prototype "
                "và duyệt trước mass print."
            ),
            "requirements": (
                "- 3+ năm packaging hoặc brand ứng dụng vật lý.\n"
                "- Thành thạo Illustrator; hiểu dieline và print finishes.\n"
                "- Portfolio có ít nhất 2 line packaging đã sản xuất (hoặc mockup rất mạnh).\n"
                "- Làm việc được với constraint giá thành.\n"
                "- Attention to detail cao trên typography nhỏ."
            ),
            "benefits": (
                "- Tham gia press check / factory visit.\n"
                "- Sample library vật liệu phong phú.\n"
                "- Project bonus theo launch.\n"
                "- Hybrid theo giai đoạn production."
            ),
        },
        "editorial": {
            "title": "Editorial Designer",
            "years_experience": 3,
            **(pay(14000000, 28000000) if cur == "VND" else pay(3000, 5200)),
            "description": (
                f"Editorial Designer dựng layout sách/catalog/magazine cho "
                f"dự án văn hóa của {name} tại {city}.\n\n"
                "Bạn sở hữu grid, type hierarchy, image pacing và prepress. "
                "Làm việc với biên tập và illustrator để nhịp đọc mạch lạc."
            ),
            "requirements": (
                "- 3+ năm editorial/print design.\n"
                "- Thành thạo InDesign; hiểu prepress và binding basics.\n"
                "- Portfolio spreads thể hiện rhythm và typography.\n"
                "- Đọc proof tiếng Việt/EN chính xác.\n"
                "- Quản lý deadline xuất bản nghiêm ngặt."
            ),
            "benefits": (
                "- Tặng bản in các ấn phẩm bạn tham gia.\n"
                "- Môi trường craft-oriented.\n"
                "- Linh hoạt onsite khi vào giai đoạn print.\n"
                "- Học hỏi từ senior type/editorial."
            ),
        },
    }


async def ensure_user(session, username: str, email: str) -> UsersOrm:
    user = await session.scalar(select(UsersOrm).where(UsersOrm.username == username))
    if user is None:
        user = UsersOrm(
            username=username,
            hashed_password=hash_password(PASSWORD),
            email=email,
            verified=True,
            description="Seed employer account for Job Market demo.",
        )
        session.add(user)
        await session.flush()
        print(f"  + user {username} / {PASSWORD}")
    else:
        user.verified = True
        if not user.email:
            user.email = email
        print(f"  = user exists {username}")
    await assign_role(session, user.id, "employer")
    await assign_role(session, user.id, "artist")  # soft-live: can still browse as creator
    return user


async def ensure_company(
    session, user: UsersOrm, spec: dict[str, Any], *, force: bool
) -> tuple[CompaniesOrm, CompanyBranchesOrm]:
    company = await session.scalar(
        select(CompaniesOrm).where(CompaniesOrm.owner_user_id == user.id)
    )
    raw = spec["registration_number_raw"]
    # Keep registration unique across re-seeds if collision: append short suffix once
    normalized = normalize_registration_number(raw)
    if company is None:
        # Avoid unique legal-entity clash with leftover rows
        clash = await session.scalar(
            select(CompaniesOrm).where(
                CompaniesOrm.registration_country == spec["registration_country"],
                CompaniesOrm.registration_authority == "NATIONAL",
                CompaniesOrm.registration_type == spec["registration_type"],
                CompaniesOrm.registration_number_normalized == normalized,
            )
        )
        if clash is not None and clash.owner_user_id != user.id:
            normalized = normalize_registration_number(f"{raw}{uuid.uuid4().hex[:4]}")
            raw = normalized

        now = _now()
        company = CompaniesOrm(
            owner_user_id=user.id,
            display_name=spec["display_name"],
            description=spec["description"],
            industry=spec["industry"],
            size_min=spec["size_min"],
            size_max=spec["size_max"],
            website=spec["website"],
            domain=spec["domain"],
            registration_country=spec["registration_country"],
            registration_authority="NATIONAL",
            registration_type=spec["registration_type"],
            registration_number_raw=raw,
            registration_number_normalized=normalized,
            tax_id=spec.get("tax_id"),
            vat_number=spec.get("vat_number"),
            status="active",
            verified_at=now,
            employees_public=True,
        )
        session.add(company)
        await session.flush()
        print(f"  + company {company.display_name} (id={company.id})")
    else:
        if force:
            company.display_name = spec["display_name"]
            company.description = spec["description"]
            company.industry = spec["industry"]
            company.size_min = spec["size_min"]
            company.size_max = spec["size_max"]
            company.website = spec["website"]
            company.domain = spec["domain"]
            company.status = "active"
            company.verified_at = company.verified_at or _now()
            company.updated_at = _now()
        print(f"  = company exists {company.display_name} (id={company.id})")

    branch = await session.scalar(
        select(CompanyBranchesOrm).where(
            CompanyBranchesOrm.company_id == company.id,
            CompanyBranchesOrm.is_primary.is_(True),
        )
    )
    b = spec["branch"]
    if branch is None:
        branch = CompanyBranchesOrm(
            company_id=company.id,
            label=b.get("label"),
            address_line=b["address_line"],
            city=b.get("city"),
            country=b.get("country"),
            is_primary=True,
        )
        session.add(branch)
        await session.flush()
        print(f"  + branch {branch.city}")
    else:
        if force:
            branch.label = b.get("label")
            branch.address_line = b["address_line"]
            branch.city = b.get("city")
            branch.country = b.get("country")
        print(f"  = branch exists {branch.city}")

    return company, branch


async def ensure_jobs(
    session,
    company: CompaniesOrm,
    branch: CompanyBranchesOrm,
    spec: dict[str, Any],
) -> int:
    bank = _jd_bank(spec)
    created = 0
    expires = _now() + timedelta(days=60)

    for key in spec["jd_keys"][:JDS_PER_COMPANY]:
        jd = bank[key]
        existing = await session.scalar(
            select(JobPostsOrm).where(
                JobPostsOrm.company_id == company.id,
                JobPostsOrm.title == jd["title"],
            )
        )
        if existing is not None:
            print(f"  = JD exists: {jd['title']}")
            continue

        row = JobPostsOrm(
            company_id=company.id,
            title=jd["title"],
            years_experience=jd["years_experience"],
            description=jd["description"],
            requirements=jd["requirements"],
            benefits=jd["benefits"],
            salary_mode=jd["salary_mode"],
            salary_min=jd["salary_min"],
            salary_max=jd["salary_max"],
            currency=jd["currency"],
            status="active",
            hiring_cycle=0,
            expires_at=expires,
        )
        session.add(row)
        await session.flush()
        session.add(
            JobPostLocationsOrm(
                job_post_id=row.id,
                source_branch_id=branch.id,
                label=branch.label,
                address_line=branch.address_line,
                city=branch.city,
                country=branch.country,
            )
        )
        created += 1
        print(f"  + JD: {jd['title']}")
    return created


async def run(*, force: bool) -> None:
    assert len(COMPANIES) == COMPANY_COUNT

    async with async_session_maker() as session:
        total_jd = 0
        for spec in COMPANIES:
            print(f"\n== {spec['display_name']} ==")
            email = f"{spec['username']}@seed.jobmarket.local"
            user = await ensure_user(session, spec["username"], email)
            company, branch = await ensure_company(session, user, spec, force=force)
            await session.commit()
            n = await ensure_jobs(session, company, branch, spec)
            await session.commit()
            total_jd += n

        print(
            f"\nDONE companies={COMPANY_COUNT} new_jds={total_jd} "
            f"login password={PASSWORD} users={USER_PREFIX}01..10"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed JM companies + design/art JDs")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Refresh company profile fields and create any missing JDs",
    )
    args = parser.parse_args()
    try:
        asyncio.run(run(force=args.force))
    except Exception as e:
        print(f"FATAL: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
