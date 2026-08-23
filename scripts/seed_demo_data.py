import os
import sys

# Ensure parent directory is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from billing_db import (
    init_db,
    get_session,
    create_user,
    create_organization,
    create_analysis_record,
    update_analysis_status,
    User,
    Organization,
    Analysis
)
from pdf_generator import generate_analysis_pdf, REPORTS_DIR


def seed():
    init_db()
    session = get_session()

    # Clean existing demo users if they exist
    demo_emails = [
        'developer@example.com',
        'admin@acmefinancial.com',
        'sarah.lead@acmefinancial.com',
        'david.eng@acmefinancial.com'
    ]
    existing_users = session.query(User).filter(User.email.in_(demo_emails)).all()
    for u in existing_users:
        session.delete(u)
    session.commit()

    existing_org = session.query(Organization).filter_by(name='Acme Financial Corp').first()
    if existing_org:
        session.delete(existing_org)
    session.commit()
    session.close()

    print("Creating demo accounts...")

    # 1. Personal Developer User
    user_dev = create_user(email='developer@example.com', password='Password123!', organization_id=None, role='user')

    sample_metrics = {
        'filename': 'payment_processor.py',
        'language': 'Python',
        'total_lines': 324,
        'code_lines': 240,
        'comment_lines': 54,
        'blank_lines': 30,
        'cyclomatic_complexity': 8,
        'functions_count': 12,
        'classes_count': 2,
        'maintainability_index': 78,
        'security_issues': [{'severity': 'Medium', 'title': 'Hardcoded timeout fallback', 'description': 'Timeout configuration is fixed at 30s.'}],
        'ai_insights': {'quality_score': 88, 'grade': 'B+', 'executive_summary': 'Well-structured payment gateway integration module with strong input sanitization and unit test coverage.'}
    }

    # Seed personal analyses with real sample PDF reports
    for fn, price, fc in [('payment_processor.py', 5.0, 1), ('data_pipeline.sql', 10.0, 2), ('auth_service.ts', 15.0, 3)]:
        rec = create_analysis_record(user_id=user_dev.id, org_id=None, file_count=fc, filenames=[fn])
        metrics = dict(sample_metrics, filename=fn)
        pdf_file = generate_analysis_pdf(analysis_id=rec.id, analysis_metrics=metrics, price_charged=price, currency='USD')
        update_analysis_status(rec.id, 'completed', report_filename=pdf_file)

    # 2. Company Organization & Admin
    org = create_organization(name='Acme Financial Corp')
    admin_user = create_user(email='admin@acmefinancial.com', password='Password123!', organization_id=org.id, role='admin')
    dev1 = create_user(email='sarah.lead@acmefinancial.com', password='Password123!', organization_id=org.id, role='member')
    dev2 = create_user(email='david.eng@acmefinancial.com', password='Password123!', organization_id=org.id, role='member')

    # Seed company audits with sample reports
    for fn, price, fc in [('core_ledger.py', 25.0, 5), ('trading_engine.cpp', 15.0, 3), ('risk_model.py', 10.0, 2), ('api_gateway.go', 5.0, 1)]:
        rec = create_analysis_record(user_id=admin_user.id, org_id=org.id, file_count=fc, filenames=[fn])
        metrics = dict(sample_metrics, filename=fn)
        pdf_file = generate_analysis_pdf(analysis_id=rec.id, analysis_metrics=metrics, price_charged=price, currency='USD')
        update_analysis_status(rec.id, 'completed', report_filename=pdf_file)

    print("?? SUCCESS: Seeded demo accounts and sample reports!")
    print("-----------------------------------------------------")
    print("1. Personal User:   developer@example.com   | Password123!")
    print("2. Company Admin:   admin@acmefinancial.com | Password123!")
    print("-----------------------------------------------------")


if __name__ == '__main__':
    seed()
