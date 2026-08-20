import datetime as dt
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class MappingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    framework: str
    code: str
    description: str


class ControlTreeNode(BaseModel):
    id: int
    code: str
    title: str
    is_group: bool
    status: Optional[str] = None
    children: List["ControlTreeNode"] = []


ControlTreeNode.model_rebuild()


class CatalogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    source: str
    version: Optional[str] = None


class ProfileCreate(BaseModel):
    title: str
    description: Optional[str] = None
    catalog_id: int
    included_control_ids: List[int] = []

class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: Optional[str] = None
    catalog_id: int

class AssessmentCreate(BaseModel):
    title: str
    catalog_id: int
    profile_id: Optional[int] = None   
    phase: Optional[str] = "plan"     
    target_scope: Optional[str] = None
    responsible: Optional[str] = None
    due_date: Optional[str] = None
    review_status: Optional[str] = "draft"


class AssessmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    catalog_id: int
    profile_id: Optional[int] = None 
    phase: str
    target_scope: Optional[str] = None
    responsible: Optional[str] = None
    due_date: Optional[str] = None
    review_status: str = "draft"


class AssessmentProgress(BaseModel):
    total: int
    fulfilled: int
    partial: int
    open: int
    na: int
    progress_pct: float


class ControlDetail(BaseModel):
    id: int
    code: str
    title: str
    prose: Optional[str] = None
    status: str
    comment: Optional[str] = None
    deviation: Optional[str] = None
    corrective_action: Optional[str] = None
    evidence_reference: Optional[str] = None
    finding_id: int
    mappings: List[MappingOut] = []


class StatusUpdate(BaseModel):
    status: str
    actor: str = "unknown"


class FindingUpdate(BaseModel):
    comment: Optional[str] = None
    deviation: Optional[str] = None
    corrective_action: Optional[str] = None
    evidence_reference: Optional[str] = None
    actor: str = "unknown"


class CommentUpdate(BaseModel):
    comment: str
    actor: str = "unknown"


class AssessmentUpdate(BaseModel):
    title: Optional[str] = None
    target_scope: Optional[str] = None
    responsible: Optional[str] = None
    due_date: Optional[str] = None
    review_status: Optional[str] = None
    actor: str = "unknown"


class DashboardMetric(BaseModel):
    total: int
    fulfilled: int
    partial: int
    open: int
    na: int
    review_required: int
    approved: int
    draft: int


class DashboardOut(BaseModel):
    audits: int
    scope_count: int
    metrics: DashboardMetric
    target_scopes: List[str] = []


class EvidenceLinkCreate(BaseModel):
    url: str
    filename: str
    actor: str = "unknown"


class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    kind: str
    filename: str
    url: Optional[str] = None
    uploaded_by: Optional[str] = None
    uploaded_at: dt.datetime


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    control_id: Optional[int] = None
    actor: str
    action: str
    created_at: dt.datetime
