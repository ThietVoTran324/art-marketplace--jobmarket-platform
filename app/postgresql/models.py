from datetime import date, datetime, timezone

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UsersOrm(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    google_id: Mapped[str | None] = mapped_column(String(200), default=None)

    username: Mapped[str] = mapped_column(String(200), unique=True)
    hashed_password: Mapped[str | None] = mapped_column(String(200), default=None)
    image: Mapped[str | None] = mapped_column(String(200), default=None)
    banner_image: Mapped[str | None] = mapped_column(String(200), default=None)

    description: Mapped[str | None] = mapped_column(String(400), default=None)

    instagram: Mapped[str | None] = mapped_column(String(200), default=None)
    tiktok: Mapped[str | None] = mapped_column(String(200), default=None)
    telegram: Mapped[str | None] = mapped_column(String(200), default=None)
    pinterest: Mapped[str | None] = mapped_column(String(200), default=None)

    email: Mapped[str | None] = mapped_column(String(200), default=None)
    verified: Mapped[bool | None] = mapped_column(Boolean, default=False)

    chat_color: Mapped[str | None] = mapped_column(String(100), default="blue")
    chat_size: Mapped[int | None] = mapped_column(Integer, default=384)
    side_open: Mapped[bool | None] = mapped_column(Boolean, default=True)

    selected_board: Mapped[int | None] = mapped_column(
        ForeignKey("boards.id", ondelete="SET NULL", name="fk_users_selected_board"), default=None
    )

    recommendation_created_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), default=None
    )


class UserRolesOrm(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(50), primary_key=True)


class WorkExperiencesOrm(Base):
    __tablename__ = "work_experiences"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), default=None
    )
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    employment_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    location: Mapped[str | None] = mapped_column(String(200), default=None)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, default=None)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "employment_type IN ('full-time', 'part-time', 'hybrid', 'outsourcing', 'collaborator')",
            name="ck_work_experiences_employment_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_work_experiences_status",
        ),
        Index("ix_work_experiences_user_start", "user_id", "start_date"),
        Index("ix_work_experiences_company_status", "company_id", "status"),
        Index("ix_work_experiences_user_company", "user_id", "company_id"),
    )


class CompanyEmployeeHeadsOrm(Base):
    __tablename__ = "company_employee_heads"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, default=None)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (
        Index("ix_company_employee_heads_company_id", "company_id"),
        Index(
            "uq_company_employee_heads_company_user",
            "company_id",
            "user_id",
            unique=True,
        ),
    )


class ProfileCredentialsOrm(Base):
    __tablename__ = "profile_credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    organization: Mapped[str | None] = mapped_column(String(200), default=None)
    occurred_on: Mapped[date | None] = mapped_column(Date, default=None)
    description: Mapped[str | None] = mapped_column(String(400), default=None)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "kind IN ('education', 'licensing', 'award')",
            name="ck_profile_credentials_kind",
        ),
        Index("ix_profile_credentials_user_kind", "user_id", "kind"),
    )


class UserCvsOrm(Base):
    __tablename__ = "user_cvs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (Index("ix_user_cvs_user_id", "user_id"),)


class AuditLogOrm(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )

    action: Mapped[str] = mapped_column(String(50), nullable=False)

    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[int | None] = mapped_column(Integer, default=None)

    meta: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )

    __table_args__ = (
        CheckConstraint(
            "action IN ("
            "'admin_delete_pin', 'admin_delete_comment', 'role_assign', 'role_revoke', "
            "'kyc_submit', 'kyc_approve', 'kyc_reject', 'kyc_need_more_info', "
            "'work_exp_approve', 'work_exp_reject', "
            "'job_report_create', 'job_report_dismiss', 'job_report_actioned', "
            "'company_suspend', 'company_unsuspend', "
            "'copyright_report_resolve', 'copyright_report_dismiss', "
            "'payment_method_verify', 'seller_payout_mark'"
            ")",
            name="ck_audit_logs_action",
        ),
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_actor_user_id", "actor_user_id"),
        Index("ix_audit_logs_target", "target_type", "target_id"),
    )


class CompaniesOrm(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    industry: Mapped[str | None] = mapped_column(String(100), default=None)
    size_min: Mapped[int | None] = mapped_column(Integer, default=None)
    size_max: Mapped[int | None] = mapped_column(Integer, default=None)
    website: Mapped[str | None] = mapped_column(String(255), default=None)
    domain: Mapped[str | None] = mapped_column(String(255), default=None)
    registration_country: Mapped[str] = mapped_column(String(10), nullable=False)
    registration_authority: Mapped[str] = mapped_column(
        String(100), nullable=False, default="NATIONAL"
    )
    registration_type: Mapped[str] = mapped_column(String(50), nullable=False)
    registration_number_raw: Mapped[str] = mapped_column(String(100), nullable=False)
    registration_number_normalized: Mapped[str] = mapped_column(String(100), nullable=False)
    tax_id: Mapped[str | None] = mapped_column(String(100), default=None)
    vat_number: Mapped[str | None] = mapped_column(String(100), default=None)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending_verification")
    verified_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), default=None)
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), default=None)
    delete_reason: Mapped[str | None] = mapped_column(String(100), default=None)
    employees_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    suspend_reason: Mapped[str | None] = mapped_column(Text, default=None)
    suspended_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending_verification', 'active', 'rejected', 'suspended', 'soft_deleted')",
            name="ck_companies_status",
        ),
        Index(
            "uq_companies_legal_entity",
            "registration_country",
            "registration_authority",
            "registration_type",
            "registration_number_normalized",
            unique=True,
        ),
        Index(
            "uq_companies_owner_user_id",
            "owner_user_id",
            unique=True,
            postgresql_where=text("owner_user_id IS NOT NULL"),
        ),
        Index("ix_companies_status", "status"),
    )


class JobPostReportsOrm(Base):
    __tablename__ = "job_post_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_post_id: Mapped[int] = mapped_column(
        ForeignKey("job_posts.id", ondelete="CASCADE"), nullable=False
    )
    reporter_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(40), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    admin_note: Mapped[str | None] = mapped_column(Text, default=None)
    resolved_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "reason IN ('spam', 'scam', 'inappropriate', 'other')",
            name="ck_job_post_reports_reason",
        ),
        CheckConstraint(
            "status IN ('open', 'dismissed', 'actioned')",
            name="ck_job_post_reports_status",
        ),
        Index("ix_job_post_reports_job_post_id", "job_post_id"),
        Index("ix_job_post_reports_status_created", "status", "created_at"),
        Index(
            "uq_job_post_reports_open_reporter_job",
            "reporter_user_id",
            "job_post_id",
            unique=True,
            postgresql_where=text("status = 'open'"),
        ),
    )


class CompanyBranchesOrm(Base):
    __tablename__ = "company_branches"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str | None] = mapped_column(String(100), default=None)
    address_line: Mapped[str] = mapped_column(String(300), nullable=False)
    city: Mapped[str | None] = mapped_column(String(100), default=None)
    country: Mapped[str | None] = mapped_column(String(10), default=None)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (Index("ix_company_branches_company_id", "company_id"),)


class CompanyVerificationRequestsOrm(Base):
    __tablename__ = "company_verification_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    requester_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    signer_full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    signed_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    signer_ip: Mapped[str | None] = mapped_column(String(64), default=None)
    signer_user_agent: Mapped[str | None] = mapped_column(String(400), default=None)
    terms_version: Mapped[str] = mapped_column(String(50), nullable=False)
    company_email: Mapped[str] = mapped_column(String(200), nullable=False)
    company_email_confirmed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), default=None
    )
    admin_note: Mapped[str | None] = mapped_column(Text, default=None)
    rejection_reason: Mapped[str | None] = mapped_column(Text, default=None)
    primary_document_language: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'need_more_info', 'approved', 'rejected')",
            name="ck_company_verification_requests_status",
        ),
        Index("ix_cvr_company_status", "company_id", "status"),
        Index("ix_cvr_requester_user_id", "requester_user_id"),
    )


class CompanyVerificationDocumentsOrm(Base):
    __tablename__ = "company_verification_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("company_verification_requests.id", ondelete="CASCADE"), nullable=False
    )
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "doc_type IN ("
            "'business_registration_document', 'tax_registration_document', "
            "'authorization_evidence', 'identity_document', 'document_translation'"
            ")",
            name="ck_company_verification_documents_doc_type",
        ),
        Index("ix_cvd_request_doc_type", "request_id", "doc_type"),
    )


class JobPostsOrm(Base):
    __tablename__ = "job_posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    years_experience: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    requirements: Mapped[str | None] = mapped_column(Text, default=None)
    benefits: Mapped[str | None] = mapped_column(Text, default=None)
    salary_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    salary_min: Mapped[int | None] = mapped_column(Integer, default=None)
    salary_max: Mapped[int | None] = mapped_column(Integer, default=None)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="VND")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    hiring_cycle: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "salary_mode IN ('love_it', 'range')",
            name="ck_job_posts_salary_mode",
        ),
        CheckConstraint(
            "currency IN ('VND', 'USD')",
            name="ck_job_posts_currency",
        ),
        CheckConstraint(
            "status IN ('active', 'closed')",
            name="ck_job_posts_status",
        ),
        CheckConstraint(
            "years_experience >= 0",
            name="ck_job_posts_years_experience",
        ),
        Index("ix_job_posts_company_status", "company_id", "status"),
        Index("ix_job_posts_status_created", "status", "created_at"),
        Index("ix_job_posts_expires_at", "expires_at"),
        Index("ix_job_posts_status_expires", "status", "expires_at"),
    )


class JobPostLocationsOrm(Base):
    __tablename__ = "job_post_locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_post_id: Mapped[int] = mapped_column(
        ForeignKey("job_posts.id", ondelete="CASCADE"), nullable=False
    )
    source_branch_id: Mapped[int | None] = mapped_column(
        ForeignKey("company_branches.id", ondelete="SET NULL"), default=None
    )
    label: Mapped[str | None] = mapped_column(String(100), default=None)
    address_line: Mapped[str] = mapped_column(String(300), nullable=False)
    city: Mapped[str | None] = mapped_column(String(100), default=None)
    country: Mapped[str | None] = mapped_column(String(10), default=None)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (Index("ix_job_post_locations_job_post_id", "job_post_id"),)


class JobApplicationsOrm(Base):
    __tablename__ = "job_applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_post_id: Mapped[int] = mapped_column(
        ForeignKey("job_posts.id", ondelete="CASCADE"), nullable=False
    )
    applicant_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    hiring_cycle: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="submitted")
    cover_note: Mapped[str | None] = mapped_column(Text, default=None)
    cover_original_filename: Mapped[str | None] = mapped_column(String(255), default=None)
    cover_stored_name: Mapped[str | None] = mapped_column(String(255), default=None)
    cover_content_type: Mapped[str | None] = mapped_column(String(100), default=None)
    cover_size_bytes: Mapped[int | None] = mapped_column(Integer, default=None)
    cv_source: Mapped[str] = mapped_column(String(20), nullable=False)
    source_cv_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_cvs.id", ondelete="SET NULL"), default=None
    )
    cv_original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    cv_stored_name: Mapped[str] = mapped_column(String(255), nullable=False)
    cv_content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    cv_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    viewed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), default=None
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('submitted', 'viewed', 'rejected', 'passed')",
            name="ck_job_applications_status",
        ),
        CheckConstraint(
            "cv_source IN ('tab', 'oneshot')",
            name="ck_job_applications_cv_source",
        ),
        Index("ix_job_applications_job_created", "job_post_id", "created_at"),
        Index("ix_job_applications_applicant_job", "applicant_user_id", "job_post_id"),
        Index("ix_job_applications_job_status", "job_post_id", "status"),
        Index(
            "uq_job_applications_cycle",
            "applicant_user_id",
            "job_post_id",
            "hiring_cycle",
            unique=True,
        ),
    )


class PinsOrm(Base):
    __tablename__ = "pins"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    title: Mapped[str | None] = mapped_column(String(200), default=None)
    description: Mapped[str | None] = mapped_column(String(400), default=None)
    href: Mapped[str | None] = mapped_column(String(200), default=None)

    image: Mapped[str | None] = mapped_column(String(200), default=None)
    videoPreview: Mapped[str | None] = mapped_column(String(200), default=None)

    rgb: Mapped[str | None] = mapped_column(String(100), default=None)

    height: Mapped[str | None] = mapped_column(String(100), default=None)

    original_image: Mapped[str | None] = mapped_column(String(200), default=None)
    content_sha256: Mapped[str | None] = mapped_column(String(64), default=None)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )


class PinStatsOrm(Base):
    __tablename__ = "pin_stats"

    pin_id: Mapped[int] = mapped_column(
        ForeignKey("pins.id", ondelete="CASCADE"), primary_key=True
    )
    view_count: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default=text("0")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )


class PinLicenseAccessOrm(Base):
    __tablename__ = "pin_license_access"
    __table_args__ = (
        UniqueConstraint("user_id", "pin_id", name="uq_pin_license_access_user_pin"),
        Index("ix_pin_license_access_pin_id", "pin_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    pin_id: Mapped[int] = mapped_column(ForeignKey("pins.id", ondelete="CASCADE"), nullable=False)
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("pin_orders.id", ondelete="SET NULL"), default=None
    )
    granted_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )


class PinOriginalAccessLogsOrm(Base):
    __tablename__ = "pin_original_access_logs"
    __table_args__ = (
        CheckConstraint(
            "action IN ('mint', 'file')",
            name="ck_pin_original_access_logs_action",
        ),
        Index("ix_pin_original_access_logs_pin_id", "pin_id"),
        Index("ix_pin_original_access_logs_user_id", "user_id"),
        Index("ix_pin_original_access_logs_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pin_id: Mapped[int] = mapped_column(ForeignKey("pins.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    ip: Mapped[str | None] = mapped_column(String(64), default=None)
    user_agent: Mapped[str | None] = mapped_column(String(400), default=None)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )


class PinListingsOrm(Base):
    __tablename__ = "pin_listings"
    __table_args__ = (
        UniqueConstraint("pin_id", name="uq_pin_listings_pin_id"),
        CheckConstraint("license_type IN ('personal_use')", name="ck_pin_listings_license_type"),
        CheckConstraint("price_minor > 0", name="ck_pin_listings_price_minor"),
        CheckConstraint("currency IN ('USD', 'VND')", name="ck_pin_listings_currency"),
        CheckConstraint("status IN ('listed', 'unlisted')", name="ck_pin_listings_status"),
        Index("ix_pin_listings_seller_status", "seller_user_id", "status"),
        Index("ix_pin_listings_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pin_id: Mapped[int] = mapped_column(ForeignKey("pins.id", ondelete="CASCADE"), nullable=False)
    seller_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    license_type: Mapped[str] = mapped_column(String(50), nullable=False, default="personal_use")
    price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="listed")
    attestation_accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    attestation_version: Mapped[str | None] = mapped_column(String(50), default=None)
    attested_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class SellerPaymentMethodsOrm(Base):
    __tablename__ = "seller_payment_methods"
    __table_args__ = (
        CheckConstraint(
            "method_type IN ('bank', 'e_wallet')",
            name="ck_seller_payment_methods_type",
        ),
        CheckConstraint(
            "verification_status IN ('unverified', 'verified')",
            name="ck_seller_payment_methods_verification_status",
        ),
        Index("ix_seller_payment_methods_user_id", "user_id"),
        Index(
            "ix_seller_payment_methods_user_active_verified",
            "user_id",
            "is_active",
            "verification_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    method_type: Mapped[str] = mapped_column(String(50), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    account_identifier: Mapped[str] = mapped_column(String(200), nullable=False)
    bank_name: Mapped[str | None] = mapped_column(String(120), default=None)
    bank_code: Mapped[str | None] = mapped_column(String(20), default=None)
    account_holder: Mapped[str | None] = mapped_column(String(120), default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verification_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="unverified", server_default=text("'unverified'")
    )
    verified_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), default=None)
    verified_by: Mapped[str | None] = mapped_column(String(64), default=None)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )


class PinOrdersOrm(Base):
    __tablename__ = "pin_orders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'paid', 'failed', 'cancelled')",
            name="ck_pin_orders_status",
        ),
        CheckConstraint("currency IN ('USD', 'VND')", name="ck_pin_orders_currency"),
        CheckConstraint("price_minor > 0", name="ck_pin_orders_price_minor"),
        CheckConstraint("charge_amount_vnd > 0", name="ck_pin_orders_charge_vnd"),
        CheckConstraint(
            "payout_status IN ('pending', 'processing', 'paid', 'failed', 'skipped')",
            name="ck_pin_orders_payout_status",
        ),
        UniqueConstraint("payment_code", name="uq_pin_orders_payment_code"),
        Index("ix_pin_orders_buyer_status", "buyer_user_id", "status"),
        Index("ix_pin_orders_pin_status", "pin_id", "status"),
        Index("ix_pin_orders_expires_at", "expires_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    buyer_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    seller_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    pin_id: Mapped[int] = mapped_column(ForeignKey("pins.id", ondelete="CASCADE"), nullable=False)
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("pin_listings.id", ondelete="RESTRICT"), nullable=False
    )
    price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    charge_amount_vnd: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_code: Mapped[str] = mapped_column(String(40), nullable=False)
    provider: Mapped[str] = mapped_column(String(30), nullable=False, default="sepay")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    commission_percent: Mapped[float | None] = mapped_column(Float, default=None)
    commission_minor: Mapped[int | None] = mapped_column(Integer, default=None)
    seller_net_minor: Mapped[int | None] = mapped_column(Integer, default=None)
    payout_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    payout_method_type: Mapped[str | None] = mapped_column(String(50), default=None)
    payout_display_name: Mapped[str | None] = mapped_column(String(100), default=None)
    payout_account_identifier: Mapped[str | None] = mapped_column(String(200), default=None)
    payout_bank_name: Mapped[str | None] = mapped_column(String(120), default=None)
    payout_bank_code: Mapped[str | None] = mapped_column(String(20), default=None)
    payout_account_holder: Mapped[str | None] = mapped_column(String(120), default=None)
    payout_amount_vnd: Mapped[int | None] = mapped_column(Integer, default=None)
    payout_marked_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), default=None)
    payout_note: Mapped[str | None] = mapped_column(String(500), default=None)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class PayoutAttemptsOrm(Base):
    __tablename__ = "payout_attempts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('started', 'success', 'failed')",
            name="ck_payout_attempts_status",
        ),
        Index("ix_payout_attempts_order_id", "order_id"),
        Index("ix_payout_attempts_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("pin_orders.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error: Mapped[str | None] = mapped_column(String(500), default=None)
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )


class PaymentEventsOrm(Base):
    __tablename__ = "payment_events"
    __table_args__ = (
        UniqueConstraint(
            "provider", "provider_event_id", name="uq_payment_events_provider_event"
        ),
        Index("ix_payment_events_order_id", "order_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(80), nullable=False)
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("pin_orders.id", ondelete="SET NULL"), default=None
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    processed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )


class CopyrightReportsOrm(Base):
    __tablename__ = "copyright_reports"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'resolved', 'dismissed')",
            name="ck_copyright_reports_status",
        ),
        Index("ix_copyright_reports_pin_id", "pin_id"),
        Index("ix_copyright_reports_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    pin_id: Mapped[int] = mapped_column(ForeignKey("pins.id", ondelete="CASCADE"), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    admin_note: Mapped[str | None] = mapped_column(String(500), default=None)
    resolved_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class LicenseCertificatesOrm(Base):
    __tablename__ = "license_certificates"
    __table_args__ = (
        UniqueConstraint("order_id", name="uq_license_certificates_order_id"),
        UniqueConstraint("certificate_code", name="uq_license_certificates_code"),
        Index("ix_license_certificates_buyer", "buyer_user_id"),
        Index("ix_license_certificates_pin", "pin_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("pin_orders.id", ondelete="CASCADE"), nullable=False
    )
    pin_id: Mapped[int] = mapped_column(ForeignKey("pins.id", ondelete="CASCADE"), nullable=False)
    buyer_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    seller_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    license_type: Mapped[str] = mapped_column(String(50), nullable=False, default="personal_use")
    content_sha256: Mapped[str | None] = mapped_column(String(64), default=None)
    certificate_code: Mapped[str] = mapped_column(String(40), nullable=False)
    paid_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )


class BoardsOrm(Base):
    __tablename__ = "boards"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", name="fk_boards_user_id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class TagsOrm(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)


class CommentsOrm(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)

    pin_id: Mapped[int | None] = mapped_column(
        ForeignKey("pins.id", ondelete="CASCADE"), default=None
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    comment_id: Mapped[int | None] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE"), default=None
    )

    content: Mapped[str | None] = mapped_column(String(400), default=None)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    image: Mapped[str | None] = mapped_column(String(200), default=None)


class LikesOrm(Base):
    __tablename__ = "likes"
    __table_args__ = (
        Index(
            "uq_likes_user_pin",
            "user_id",
            "pin_id",
            unique=True,
            postgresql_where=text("pin_id IS NOT NULL"),
        ),
        Index(
            "uq_likes_user_comment",
            "user_id",
            "comment_id",
            unique=True,
            postgresql_where=text("comment_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    pin_id: Mapped[int | None] = mapped_column(
        ForeignKey("pins.id", ondelete="CASCADE"), default=None
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    comment_id: Mapped[int | None] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE"), default=None
    )


class SubsrciptionsOrm(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        UniqueConstraint(
            "follower_id",
            "following_id",
            name="uq_subscriptions_follower_following",
        ),
        CheckConstraint(
            "follower_id <> following_id",
            name="ck_subscriptions_no_self_follow",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    follower_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    following_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)


class ChatOrm(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), default="dm", server_default="dm")
    title: Mapped[str | None] = mapped_column(String(120), default=None)
    invite_code: Mapped[str | None] = mapped_column(String(10), default=None, unique=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    user_1_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    user_2_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class ChatMemberOrm(Base):
    __tablename__ = "chat_members"
    __table_args__ = (
        UniqueConstraint("chat_id", "user_id", name="uq_chat_members_chat_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), default="member", server_default="member")
    joined_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class MessageOrm(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"), nullable=False)
    user_id_: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    content: Mapped[str | None] = mapped_column(String(400), default=None)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    image: Mapped[str | None] = mapped_column(String(200), default=None)

    is_read: Mapped[bool | None] = mapped_column(Boolean, default=False)

    pin_id: Mapped[int | None] = mapped_column(
        ForeignKey("pins.id", ondelete="SET NULL"), default=None
    )
    message_kind: Mapped[str] = mapped_column(
        String(20), default="text", server_default="text"
    )


class SearchOrm(Base):
    __tablename__ = "search"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    query: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class UpdatesOrm(Base):
    __tablename__ = "updates"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_update_to_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    content: Mapped[str | None] = mapped_column(String(100), default=None)

    update_type: Mapped[str] = mapped_column(String(100), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    is_read: Mapped[bool | None] = mapped_column(Boolean, default=False)

    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), default=None)

    pin_id: Mapped[int | None] = mapped_column(
        ForeignKey("pins.id", ondelete="CASCADE"), default=None
    )

    comment_id: Mapped[int | None] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE"), default=None
    )

    reply_id: Mapped[int | None] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE"), default=None
    )

    meta: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, default=None
    )


class UsersRecommendationsPinsOrm(Base):
    __tablename__ = "users_recommendations_pins"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    pin_id: Mapped[int] = mapped_column(ForeignKey("pins.id", ondelete="CASCADE"), nullable=False)
    update_id: Mapped[int] = mapped_column(ForeignKey("updates.id"), nullable=False)


pins_tags = Table(
    "pins_tags",
    Base.metadata,
    Column("pin_id", ForeignKey("pins.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True),
)

users_pins = Table(
    "users_pins",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("pin_id", ForeignKey("pins.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "created_at",
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    ),
)

board_pins = Table(
    "board_pins",
    Base.metadata,
    Column("board_id", Integer, ForeignKey("boards.id", ondelete="CASCADE"), primary_key=True),
    Column("pin_id", Integer, ForeignKey("pins.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "created_at",
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    ),
)

users_view_pins = Table(
    "users_view_pins",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("pin_id", ForeignKey("pins.id", ondelete="CASCADE"), primary_key=True),
)
