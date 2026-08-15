import os
import uuid
import hashlib
import secrets
from datetime import datetime
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Float,
    DateTime,
    Integer,
    ForeignKey,
    select,
    desc,
    func,
    inspect,
    text
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, scoped_session

Base = declarative_base()


class PricingConfig(Base):
    """Centralized authoritative pricing configuration."""
    __tablename__ = "pricing_config"

    id = Column(Integer, primary_key=True)
    analysis_price = Column(Float, nullable=False, default=5.00)
    currency = Column(String(10), nullable=False, default="USD")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Organization(Base):
    """Company / Organization account for shared billing."""
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    stripe_customer_id = Column(String(255), nullable=True)
    stripe_default_payment_method_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="organization")
    analyses = relationship("Analysis", back_populates="organization")


class User(Base):
    """User account (for organization members or administrators)."""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=True)
    role = Column(String(50), nullable=False, default="member")  # 'admin', 'member'
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="users")
    analyses = relationship("Analysis", back_populates="user")


class Analysis(Base):
    """Analysis Job / Batch record with price snapshotting."""
    __tablename__ = "analyses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=True)

    status = Column(String(50), nullable=False, default="pending_payment")
    # Valid statuses: 'pending_payment', 'paid', 'processing', 'completed', 'payment_failed', 'failed'

    file_count = Column(Integer, nullable=False, default=1)
    unit_price = Column(Float, nullable=False, default=5.00)  # Snapshot of unit price per file
    price = Column(Float, nullable=False)  # TOTAL price (file_count * unit_price)
    currency = Column(String(10), nullable=False, default="USD")

    stripe_checkout_session_id = Column(String(255), nullable=True)
    stripe_payment_intent_id = Column(String(255), nullable=True)
    report_filename = Column(String(255), nullable=True)
    zip_filename = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    organization = relationship("Organization", back_populates="analyses")
    user = relationship("User", back_populates="analyses")
    file_analyses = relationship("FileAnalysis", back_populates="analysis_job", cascade="all, delete-orphan")


class FileAnalysis(Base):
    """Individual file record within an Analysis Job."""
    __tablename__ = "file_analyses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_id = Column(String(36), ForeignKey("analyses.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    price = Column(Float, nullable=False, default=5.00)  # Unit price snapshot
    currency = Column(String(10), nullable=False, default="USD")
    status = Column(String(50), nullable=False, default="pending")  # 'pending', 'completed', 'failed'
    markdown_report = Column(String, nullable=True)
    pdf_filename = Column(String(255), nullable=True)
    quality_score = Column(Integer, nullable=True)
    grade = Column(String(10), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    analysis_job = relationship("Analysis", back_populates="file_analyses")


class ProcessedEvent(Base):
    """Idempotency log for Stripe webhooks and payment events."""
    __tablename__ = "processed_events"

    event_id = Column(String(255), primary_key=True)
    event_type = Column(String(100), nullable=False)
    processed_at = Column(DateTime, default=datetime.utcnow)


# --- Database Engine & Session Helper ---

_engine = None
_SessionFactory = None


def get_db_uri():
    default_uri = "sqlite:///billing.db"
    return os.getenv("BILLING_DATABASE_URL") or os.getenv("DATABASE_URL") or default_uri


def init_db(db_uri=None):
    global _engine, _SessionFactory
    if db_uri is None:
        db_uri = get_db_uri()

    # Handle PostgreSQL URL scheme if dialect is postgres://
    if db_uri.startswith("postgres://"):
        db_uri = db_uri.replace("postgres://", "postgresql://", 1)

    engine_kwargs = {"echo": False}
    if db_uri.startswith("postgresql"):
        engine_kwargs["pool_pre_ping"] = True
        engine_kwargs["pool_recycle"] = 300

    _engine = create_engine(db_uri, **engine_kwargs)
    Base.metadata.create_all(_engine)

    # Automatically migrate missing columns on existing databases (e.g. Neon PostgreSQL)
    try:
        inspector = inspect(_engine)
        if "analyses" in inspector.get_table_names():
            existing_cols = {c["name"] for c in inspector.get_columns("analyses")}
            with _engine.begin() as conn:
                if "file_count" not in existing_cols:
                    conn.execute(text("ALTER TABLE analyses ADD COLUMN file_count INTEGER DEFAULT 1 NOT NULL"))
                if "unit_price" not in existing_cols:
                    conn.execute(text("ALTER TABLE analyses ADD COLUMN unit_price FLOAT DEFAULT 5.0 NOT NULL"))
                if "zip_filename" not in existing_cols:
                    conn.execute(text("ALTER TABLE analyses ADD COLUMN zip_filename VARCHAR(255)"))
    except Exception as e:
        print(f"Schema migration note: {e}")

    _SessionFactory = scoped_session(sessionmaker(bind=_engine))

    # Ensure default pricing config exists ($5.00 USD)
    session = _SessionFactory()
    try:
        config = session.query(PricingConfig).first()
        if not config:
            config = PricingConfig(id=1, analysis_price=5.00, currency="USD")
            session.add(config)
            session.commit()
        elif config.analysis_price == 15.00:
            config.analysis_price = 5.00
            session.commit()
    finally:
        session.close()

def close_db():
    global _engine, _SessionFactory
    if _SessionFactory:
        _SessionFactory.remove()
    if _engine:
        _engine.dispose()


def get_session():
    global _SessionFactory
    if _SessionFactory is None:
        init_db()
    return _SessionFactory()


# --- Centralized Pricing Helpers ---

def get_pricing():
    """Returns the single authoritative (analysis_price, currency)."""
    session = get_session()
    try:
        config = session.query(PricingConfig).first()
        if not config:
            config = PricingConfig(id=1, analysis_price=5.00, currency="USD")
            session.add(config)
            session.commit()
        elif config.analysis_price == 15.00:
            config.analysis_price = 5.00
            session.commit()
        return float(config.analysis_price), str(config.currency)
    finally:
        session.close()


def set_pricing(price: float, currency: str = "USD"):
    """Updates the centralized authoritative price without changing historical transactions."""
    session = get_session()
    try:
        config = session.query(PricingConfig).first()
        if not config:
            config = PricingConfig(id=1, analysis_price=price, currency=currency)
            session.add(config)
        else:
            config.analysis_price = float(price)
            config.currency = str(currency)
            config.updated_at = datetime.utcnow()
        session.commit()
        return float(config.analysis_price), str(config.currency)
    finally:
        session.close()


# --- Organization & User Helpers ---

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"{salt}${key.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    try:
        salt, key_hex = hashed.split("$")
        test_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
        return secrets.compare_digest(key_hex, test_key.hex())
    except Exception:
        return False


def create_organization(name: str, stripe_customer_id: str = None) -> Organization:
    session = get_session()
    try:
        org = Organization(name=name, stripe_customer_id=stripe_customer_id)
        session.add(org)
        session.commit()
        session.refresh(org)
        return org
    finally:
        session.close()


def get_organization(org_id: str):
    session = get_session()
    try:
        return session.query(Organization).filter_by(id=org_id).first()
    finally:
        session.close()


def update_organization_stripe(org_id: str, stripe_customer_id: str, payment_method_id: str = None):
    session = get_session()
    try:
        org = session.query(Organization).filter_by(id=org_id).first()
        if org:
            org.stripe_customer_id = stripe_customer_id
            if payment_method_id:
                org.stripe_default_payment_method_id = payment_method_id
            session.commit()
            return True
        return False
    finally:
        session.close()


def create_user(email: str, password: str, organization_id: str = None, role: str = "member") -> User:
    session = get_session()
    try:
        existing = session.query(User).filter_by(email=email).first()
        if existing:
            raise ValueError(f"User with email '{email}' already exists.")
        user = User(
            email=email.strip().lower(),
            password_hash=hash_password(password),
            organization_id=organization_id,
            role=role
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
    finally:
        session.close()


def authenticate_user(email: str, password: str):
    session = get_session()
    try:
        user = session.query(User).filter_by(email=email.strip().lower()).first()
        if user and verify_password(password, user.password_hash):
            return {
                "id": user.id,
                "email": user.email,
                "organization_id": user.organization_id,
                "role": user.role
            }
        return None
    finally:
        session.close()


def get_org_users(org_id: str):
    session = get_session()
    try:
        users = session.query(User).filter_by(organization_id=org_id).all()
        return [{"id": u.id, "email": u.email, "role": u.role, "created_at": u.created_at} for u in users]
    finally:
        session.close()


# --- Analysis & Price Snapshotting Helpers ---

def create_analysis_record(
    user_id: str = None,
    org_id: str = None,
    file_count: int = 1,
    filenames: list = None
) -> Analysis:
    """Creates a new analysis job record with a SNAPSHOT of the current authoritative price per file."""
    current_unit_price, current_currency = get_pricing()
    count = max(1, int(file_count))
    total_price = round(count * current_unit_price, 2)

    session = get_session()
    try:
        analysis = Analysis(
            user_id=user_id,
            organization_id=org_id,
            status="pending_payment",
            file_count=count,
            unit_price=current_unit_price,  # Snapshot unit price
            price=total_price,              # Total charge
            currency=current_currency
        )
        session.add(analysis)
        session.flush()

        # Create individual FileAnalysis entries
        if filenames:
            for fname in filenames:
                fa = FileAnalysis(
                    analysis_id=analysis.id,
                    filename=fname,
                    price=current_unit_price,
                    currency=current_currency,
                    status="pending"
                )
                session.add(fa)

        session.commit()
        session.refresh(analysis)
        return analysis
    finally:
        session.close()


def get_analysis(analysis_id: str):
    session = get_session()
    try:
        return session.query(Analysis).filter_by(id=analysis_id).first()
    finally:
        session.close()


def get_analysis_files(analysis_id: str):
    session = get_session()
    try:
        files = session.query(FileAnalysis).filter_by(analysis_id=analysis_id).all()
        return [
            {
                "id": f.id,
                "analysis_id": f.analysis_id,
                "filename": f.filename,
                "price": f.price,
                "currency": f.currency,
                "status": f.status,
                "markdown_report": f.markdown_report,
                "pdf_filename": f.pdf_filename,
                "quality_score": f.quality_score,
                "grade": f.grade,
                "created_at": f.created_at
            }
            for f in files
        ]
    finally:
        session.close()


def update_file_analysis(
    file_analysis_id: str,
    status: str,
    markdown_report: str = None,
    pdf_filename: str = None,
    quality_score: int = None,
    grade: str = None
):
    session = get_session()
    try:
        fa = session.query(FileAnalysis).filter_by(id=file_analysis_id).first()
        if fa:
            fa.status = status
            if markdown_report is not None:
                fa.markdown_report = markdown_report
            if pdf_filename is not None:
                fa.pdf_filename = pdf_filename
            if quality_score is not None:
                fa.quality_score = quality_score
            if grade is not None:
                fa.grade = grade
            session.commit()
            return True
        return False
    finally:
        session.close()


def update_analysis_status(
    analysis_id: str,
    status: str,
    stripe_payment_intent_id: str = None,
    stripe_checkout_session_id: str = None,
    report_filename: str = None,
    zip_filename: str = None
):
    session = get_session()
    try:
        analysis = session.query(Analysis).filter_by(id=analysis_id).first()
        if not analysis:
            return None
        analysis.status = status
        if stripe_payment_intent_id:
            analysis.stripe_payment_intent_id = stripe_payment_intent_id
        if stripe_checkout_session_id:
            analysis.stripe_checkout_session_id = stripe_checkout_session_id
        if report_filename:
            analysis.report_filename = report_filename
        if zip_filename:
            analysis.zip_filename = zip_filename
        if status == "completed":
            analysis.completed_at = datetime.utcnow()
        session.commit()
        session.refresh(analysis)
        return analysis
    finally:
        session.close()


# --- Organization Usage Reporting ---

def get_org_usage(org_id: str):
    """Calculates aggregate usage reporting for an organization."""
    session = get_session()
    try:
        current_price, currency = get_pricing()

        # Count completed and paid analyses for this org
        analyses = session.query(Analysis).filter(
            Analysis.organization_id == org_id,
            Analysis.status.in_(["paid", "processing", "completed"])
        ).order_by(desc(Analysis.created_at)).all()

        analyses_count = len(analyses)
        # Sum of the snapshotted prices actually charged
        total_usage_amount = sum(a.price for a in analyses)

        recent_analyses = [
            {
                "id": a.id,
                "price": a.price,
                "currency": a.currency,
                "status": a.status,
                "created_at": a.created_at.strftime("%Y-%m-%d %H:%M:%S") if a.created_at else "",
                "report_filename": a.report_filename
            }
            for a in analyses[:20]
        ]

        return {
            "analyses_count": analyses_count,
            "current_price": current_price,
            "currency": currency,
            "total_usage_amount": round(total_usage_amount, 2),
            "recent_analyses": recent_analyses
        }
    finally:
        session.close()


# --- Idempotency Helpers ---

def is_event_processed(event_id: str) -> bool:
    session = get_session()
    try:
        return session.query(ProcessedEvent).filter_by(event_id=event_id).first() is not None
    finally:
        session.close()


def mark_event_processed(event_id: str, event_type: str):
    session = get_session()
    try:
        event = ProcessedEvent(event_id=event_id, event_type=event_type)
        session.merge(event)
        session.commit()
    finally:
        session.close()
