import datetime as dt
from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, DateTime, Boolean, UniqueConstraint
)
from sqlalchemy.orm import relationship
from .database import Base


class Catalog(Base):
    """Ein importierter OSCAL-Katalog (z. B. NIS2, ISO 27001, BSI IT-Grundschutz)."""
    __tablename__ = "catalogs"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    source = Column(String, nullable=False, default="NIS2")
    version = Column(String, nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    controls = relationship("Control", back_populates="catalog", cascade="all, delete-orphan")
    assessments = relationship("Assessment", back_populates="catalog", cascade="all, delete-orphan")


class Control(Base):
    """Ein Knoten im Katalogbaum – kann Gruppe (is_group=True) oder Blatt-Kontrolle sein."""
    __tablename__ = "controls"

    id = Column(Integer, primary_key=True)
    catalog_id = Column(Integer, ForeignKey("catalogs.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("controls.id"), nullable=True)

    code = Column(String, nullable=False)       # z.B. "21.2d"
    title = Column(String, nullable=False)
    prose = Column(Text, nullable=True)          # Klartext-Anforderung
    is_group = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)

    catalog = relationship("Catalog", back_populates="controls")
    parent = relationship(
        "Control",
        back_populates="children",
        remote_side="Control.id",
        foreign_keys="[Control.parent_id]",
    )
    children = relationship(
        "Control",
        back_populates="parent",
        foreign_keys="[Control.parent_id]",
    )
    mappings = relationship("Mapping", back_populates="control", cascade="all, delete-orphan")


class Mapping(Base):
    """Cross-Framework-Mapping: welche ISO/BSI-Kontrolle erfüllt diese NIS2-Anforderung (OSCAL Profile)."""
    __tablename__ = "mappings"

    id = Column(Integer, primary_key=True)
    control_id = Column(Integer, ForeignKey("controls.id"), nullable=False)
    framework = Column(String, nullable=False)   # "ISO 27001" | "BSI IT-GS"
    code = Column(String, nullable=False)         # "A.8.8" | "CON.3"
    description = Column(String, nullable=False)

    control = relationship("Control", back_populates="mappings")


# --- NEU: Profile für das Tailoring (OSCAL Profile) ---
class Profile(Base):
    """Ein OSCAL Profile, das einen Basis-Katalog zuschneidet (Tailoring)."""
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    catalog_id = Column(Integer, ForeignKey("catalogs.id"), nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    catalog = relationship("Catalog")
    selections = relationship("ProfileSelection", back_populates="profile", cascade="all, delete-orphan")
    assessments = relationship("Assessment", back_populates="profile")

class ProfileSelection(Base):
    """Legt fest, ob eine Kontrolle im Profil enthalten ist oder abgewandelt wird."""
    __tablename__ = "profile_selections"

    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    control_id = Column(Integer, ForeignKey("controls.id"), nullable=False)
    is_included = Column(Boolean, default=True) # True = in Baseline, False = explizit ausgeschlossen

    profile = relationship("Profile", back_populates="selections")
    control = relationship("Control")


# --- ANPASSUNG: Assessment Modell ---
class Assessment(Base):
    """Ein konkreter Audit-Lauf (OSCAL assessment-plan / assessment-results)."""
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    catalog_id = Column(Integer, ForeignKey("catalogs.id"), nullable=False)
    
    # NEU: Verknüpfung zum Profil und OSCAL-Phasen-Steuerung
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=True)
    phase = Column(String, nullable=False, default="plan") # 'plan', 'execution', 'result'
    
    target_scope = Column(String, nullable=True)
    responsible = Column(String, nullable=True)
    due_date = Column(String, nullable=True)
    review_status = Column(String, nullable=False, default="draft")
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    catalog = relationship("Catalog", foreign_keys="[Assessment.catalog_id]")
    profile = relationship("Profile", back_populates="assessments")
    findings = relationship("Finding", back_populates="assessment", cascade="all, delete-orphan")


class Finding(Base):
    """Erfüllungsgrad + Kommentar pro Kontrolle innerhalb eines Audits (OSCAL finding)."""
    __tablename__ = "findings"
    __table_args__ = (UniqueConstraint("assessment_id", "control_id", name="uq_finding_per_control"),)

    id = Column(Integer, primary_key=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    control_id = Column(Integer, ForeignKey("controls.id"), nullable=False)

    status = Column(String, nullable=False, default="open")  # open|partial|fulfilled|na
    comment = Column(Text, nullable=True)
    deviation = Column(Text, nullable=True)
    corrective_action = Column(Text, nullable=True)
    evidence_reference = Column(Text, nullable=True)
    updated_by = Column(String, nullable=True)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    assessment = relationship("Assessment", back_populates="findings")
    control = relationship("Control")
    evidence = relationship("Evidence", back_populates="finding", cascade="all, delete-orphan")


class Evidence(Base):
    """Hochgeladener Nachweis oder externer Link (OSCAL observation -> relevant-evidence)."""
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True)
    finding_id = Column(Integer, ForeignKey("findings.id"), nullable=False)

    kind = Column(String, nullable=False, default="file")  # file|link
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=True)   # server-side path, for kind=file
    url = Column(String, nullable=True)        # for kind=link
    uploaded_by = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=dt.datetime.utcnow)

    finding = relationship("Finding", back_populates="evidence")


class AuditLog(Base):
    """Lückenlose Historisierung aller Bewertungsänderungen (N2: Fälschungssicherheit)."""
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    control_id = Column(Integer, ForeignKey("controls.id"), nullable=True)
    actor = Column(String, nullable=False, default="unknown")
    action = Column(String, nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
