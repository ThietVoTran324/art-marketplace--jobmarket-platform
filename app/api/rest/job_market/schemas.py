from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


EmploymentType = Literal[
    "full-time", "part-time", "hybrid", "outsourcing", "collaborator"
]
CredentialKind = Literal["education", "licensing", "award"]
WorkExpStatus = Literal["pending", "approved", "rejected"]


class WorkExperienceCreate(BaseModel):
    company_name: str | None = Field(default=None, min_length=1, max_length=200)
    company_id: int | None = None
    employment_type: EmploymentType
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    location: str | None = Field(default=None, max_length=200)
    start_date: date
    end_date: date | None = None

    @model_validator(mode="after")
    def validate_dates_and_company(self):
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date must be >= start_date")
        has_name = self.company_name is not None and bool(str(self.company_name).strip())
        if self.company_id is not None and has_name:
            raise ValueError("provide company_id XOR company_name")
        if self.company_id is None and not has_name:
            raise ValueError("company_name or company_id required")
        return self


class WorkExperienceUpdate(BaseModel):
    company_name: str | None = Field(default=None, min_length=1, max_length=200)
    company_id: int | None = None
    clear_company_id: bool = False
    employment_type: EmploymentType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    location: str | None = Field(default=None, max_length=200)
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError("end_date must be >= start_date")
        return self


class WorkExperienceOut(BaseModel):
    id: int
    user_id: int
    company_id: int | None = None
    company_name: str
    employment_type: str
    title: str
    description: str | None = None
    location: str | None
    start_date: date
    end_date: date | None
    status: WorkExpStatus

    model_config = {"from_attributes": True}


class CredentialCreate(BaseModel):
    kind: CredentialKind
    title: str = Field(min_length=1, max_length=200)
    organization: str | None = Field(default=None, max_length=200)
    occurred_on: date | None = None
    description: str | None = Field(default=None, max_length=400)


class CredentialUpdate(BaseModel):
    kind: CredentialKind | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    organization: str | None = Field(default=None, max_length=200)
    occurred_on: date | None = None
    description: str | None = Field(default=None, max_length=400)


class CredentialOut(BaseModel):
    id: int
    user_id: int
    kind: CredentialKind
    title: str
    organization: str | None
    occurred_on: date | None
    description: str | None

    model_config = {"from_attributes": True}


class UserCvOut(BaseModel):
    id: int
    user_id: int
    original_filename: str
    content_type: str
    size_bytes: int

    model_config = {"from_attributes": True}


# ---- Sprint2 KYC / company ----

KycDocType = Literal[
    "business_registration_document",
    "tax_registration_document",
    "authorization_evidence",
    "identity_document",
    "document_translation",
]

RequestStatus = Literal["pending", "need_more_info", "approved", "rejected"]
CompanyStatus = Literal[
    "pending_verification", "active", "rejected", "suspended", "soft_deleted"
]


class WarningItem(BaseModel):
    code: str


class HiringRightsRequestCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    industry: str | None = Field(default=None, max_length=100)
    size_min: int | None = Field(default=None, ge=0)
    size_max: int | None = Field(default=None, ge=0)
    website: str | None = Field(default=None, max_length=255)
    domain: str | None = Field(default=None, max_length=255)
    registration_country: str = Field(min_length=1, max_length=10)
    registration_authority: str | None = Field(default=None, max_length=100)
    registration_type: str = Field(min_length=1, max_length=50)
    registration_number_raw: str = Field(min_length=1, max_length=100)
    tax_id: str | None = Field(default=None, max_length=100)
    vat_number: str | None = Field(default=None, max_length=100)
    signer_full_name: str = Field(min_length=1, max_length=200)
    terms_version: str | None = Field(default=None, max_length=50)
    primary_document_language: str = Field(min_length=1, max_length=20)
    company_email: str = Field(min_length=1, max_length=200)
    address_line: str | None = Field(default=None, max_length=300)
    city: str | None = Field(default=None, max_length=100)
    branch_country: str | None = Field(default=None, max_length=10)

    @model_validator(mode="after")
    def validate_size(self):
        if (
            self.size_min is not None
            and self.size_max is not None
            and self.size_max < self.size_min
        ):
            raise ValueError("size_max must be >= size_min")
        return self


class KycDocumentOut(BaseModel):
    id: int
    request_id: int
    doc_type: KycDocType
    original_filename: str
    content_type: str
    size_bytes: int

    model_config = {"from_attributes": True}


class HiringRightsRequestOut(BaseModel):
    id: int
    company_id: int
    requester_user_id: int
    status: RequestStatus
    signer_full_name: str
    signed_at: datetime
    terms_version: str
    company_email: str
    company_email_confirmed_at: datetime | None
    admin_note: str | None
    rejection_reason: str | None
    primary_document_language: str
    created_at: datetime
    updated_at: datetime
    warnings: list[WarningItem] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class HiringRightsRequestCreateOut(HiringRightsRequestOut):
    pass


class AdminNoteBody(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


class AdminRejectBody(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class CompanyOut(BaseModel):
    id: int
    owner_user_id: int | None
    display_name: str
    description: str | None
    industry: str | None
    size_min: int | None
    size_max: int | None
    website: str | None
    domain: str | None
    registration_country: str
    registration_authority: str
    registration_type: str
    registration_number_raw: str
    registration_number_normalized: str
    tax_id: str | None
    vat_number: str | None
    status: CompanyStatus
    verified_at: datetime | None
    employees_public: bool = True
    warnings: list[WarningItem] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class CompanyPublicOut(BaseModel):
    """Public company card — no legal registration / tax identifiers."""

    id: int
    display_name: str
    description: str | None
    industry: str | None
    size_min: int | None
    size_max: int | None
    website: str | None
    domain: str | None
    registration_country: str
    status: CompanyStatus
    verified_at: datetime | None
    employees_public: bool = True

    model_config = {"from_attributes": True}


class CompanyUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    industry: str | None = Field(default=None, max_length=100)
    size_min: int | None = Field(default=None, ge=0)
    size_max: int | None = Field(default=None, ge=0)
    website: str | None = Field(default=None, max_length=255)
    domain: str | None = Field(default=None, max_length=255)
    employees_public: bool | None = None

    @model_validator(mode="after")
    def validate_size(self):
        if (
            self.size_min is not None
            and self.size_max is not None
            and self.size_max < self.size_min
        ):
            raise ValueError("size_max must be >= size_min")
        return self


class BranchCreate(BaseModel):
    label: str | None = Field(default=None, max_length=100)
    address_line: str = Field(min_length=1, max_length=300)
    city: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=10)
    is_primary: bool = False


class BranchUpdate(BaseModel):
    label: str | None = Field(default=None, max_length=100)
    address_line: str | None = Field(default=None, min_length=1, max_length=300)
    city: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=10)
    is_primary: bool | None = None


class BranchOut(BaseModel):
    id: int
    company_id: int
    label: str | None
    address_line: str
    city: str | None
    country: str | None
    is_primary: bool

    model_config = {"from_attributes": True}


# ---- Sprint3 job posts ----

SalaryMode = Literal["love_it", "range"]
JobCurrency = Literal["VND", "USD"]
JobStatus = Literal["active", "closed"]


class JobPostLocationOut(BaseModel):
    id: int
    job_post_id: int
    source_branch_id: int | None
    label: str | None
    address_line: str
    city: str | None
    country: str | None

    model_config = {"from_attributes": True}


class JobPostCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    years_experience: int = Field(ge=0)
    description: str | None = None
    requirements: str | None = None
    benefits: str | None = None
    salary_mode: SalaryMode
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    currency: JobCurrency = "VND"
    branch_ids: list[int] = Field(min_length=1)
    expires_at: datetime

    @model_validator(mode="after")
    def validate_salary(self):
        if self.salary_mode == "love_it":
            if self.salary_min is not None or self.salary_max is not None:
                raise ValueError("love_it requires salary_min and salary_max to be null")
        else:
            if self.salary_min is None and self.salary_max is None:
                raise ValueError("range requires at least one of salary_min or salary_max")
            if (
                self.salary_min is not None
                and self.salary_max is not None
                and self.salary_max < self.salary_min
            ):
                raise ValueError("salary_max must be >= salary_min")
        return self


class JobPostUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    years_experience: int | None = Field(default=None, ge=0)
    description: str | None = None
    requirements: str | None = None
    benefits: str | None = None
    salary_mode: SalaryMode | None = None
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    currency: JobCurrency | None = None
    branch_ids: list[int] | None = Field(default=None, min_length=1)
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def validate_salary_partial(self):
        if self.salary_mode == "love_it":
            if self.salary_min is not None or self.salary_max is not None:
                raise ValueError("love_it requires salary_min and salary_max to be null")
        if self.salary_mode == "range":
            if self.salary_min is None and self.salary_max is None:
                raise ValueError("range requires at least one of salary_min or salary_max")
            if (
                self.salary_min is not None
                and self.salary_max is not None
                and self.salary_max < self.salary_min
            ):
                raise ValueError("salary_max must be >= salary_min")
        elif (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_max < self.salary_min
        ):
            raise ValueError("salary_max must be >= salary_min")
        return self


class JobPostOut(BaseModel):
    id: int
    company_id: int
    title: str
    years_experience: int
    description: str | None
    requirements: str | None
    benefits: str | None
    salary_mode: SalaryMode
    salary_min: int | None
    salary_max: int | None
    currency: JobCurrency
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    locations: list[JobPostLocationOut] = Field(default_factory=list)
    company_display_name: str | None = None
    my_application: "MyApplicationBrief | None" = None
    application_count: int = 0

    model_config = {"from_attributes": True}


# ---- Sprint4 applications ----

ApplicationStatus = Literal["submitted", "viewed", "rejected", "passed"]
CvSource = Literal["tab", "oneshot"]


class MyApplicationBrief(BaseModel):
    id: int
    status: ApplicationStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class JobApplicationOut(BaseModel):
    id: int
    job_post_id: int
    applicant_user_id: int
    status: ApplicationStatus
    cover_note: str | None
    has_cover_file: bool = False
    cv_source: CvSource
    source_cv_id: int | None
    cv_original_filename: str
    viewed_at: datetime | None
    decided_at: datetime | None
    created_at: datetime
    updated_at: datetime
    applicant_username: str | None = None

    model_config = {"from_attributes": True}


class ApplicationCvViewOut(BaseModel):
    id: int
    job_post_id: int
    job_title: str | None = None
    applicant_user_id: int
    applicant_username: str | None = None
    status: ApplicationStatus
    cover_note: str | None
    has_cover_file: bool
    cv_original_filename: str
    cv_content_type: str
    viewed_at: datetime | None
    decided_at: datetime | None
    created_at: datetime


# ---- Sprint5 employees / suggest ----

class CompanySuggestOut(BaseModel):
    id: int
    display_name: str
    domain: str | None = None

    model_config = {"from_attributes": True}


class PendingWorkExperienceOut(WorkExperienceOut):
    artist_username: str | None = None
    artist_user_id: int | None = None


class EmployeeOut(BaseModel):
    user_id: int
    username: str | None = None
    title: str | None = None
    start_date: date | None = None
    work_experience_id: int | None = None


class EmployeeHeadCreate(BaseModel):
    user_id: int
    title: str = Field(min_length=1, max_length=100)
    note: str | None = None
    sort_order: int = 0


class EmployeeHeadUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    note: str | None = None
    sort_order: int | None = None


class EmployeeHeadOut(BaseModel):
    id: int
    company_id: int
    user_id: int
    username: str | None = None
    title: str
    note: str | None
    sort_order: int

    model_config = {"from_attributes": True}


class EmployeesListOut(BaseModel):
    employees_public: bool
    employees: list[EmployeeOut]
    heads: list[EmployeeHeadOut]


# ---- Sprint6 moderation ----

ReportReason = Literal["spam", "scam", "inappropriate", "other"]
ReportStatus = Literal["open", "dismissed", "actioned"]


class JobReportCreate(BaseModel):
    reason: ReportReason
    detail: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_other_detail(self):
        if self.reason == "other":
            if self.detail is None or not str(self.detail).strip():
                raise ValueError("detail required when reason is other")
        return self


class JobReportResolveBody(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


class CompanySuspendBody(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class JobReportOut(BaseModel):
    id: int
    job_post_id: int
    reporter_user_id: int
    reason: ReportReason
    detail: str | None
    status: ReportStatus
    admin_note: str | None
    resolved_by: int | None
    resolved_at: datetime | None
    created_at: datetime
    job_title: str | None = None
    company_id: int | None = None

    model_config = {"from_attributes": True}
