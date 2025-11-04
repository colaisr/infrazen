#!/usr/bin/env python3
"""
Generate AI text for existing recommendations
Run this once to populate AI fields for already-created recommendations
"""
from app import create_app
from app.core.models import db
from app.core.models.recommendations import OptimizationRecommendation
from app.core.services.ai_text_generator import generate_recommendation_text
from datetime import datetime

app = create_app()

with app.app_context():
    # Get all pending recommendations without AI text
    recs = OptimizationRecommendation.query.filter_by(
        ai_short_description=None,
        status='pending'
    ).limit(50).all()
    
    print(f"Found {len(recs)} recommendations without AI text")
    
    success = 0
    failed = 0
    
    for rec in recs:
        try:
            print(f"Generating AI text for recommendation {rec.id} ({rec.resource_name})...", end=" ")
            ai_text = generate_recommendation_text(rec.id)
            
            if ai_text:
                rec.ai_short_description = ai_text['short_description_html']
                rec.ai_detailed_description = ai_text['detailed_description_html']
                rec.ai_generated_at = datetime.utcnow()
                success += 1
                print("✓")
            else:
                failed += 1
                print("✗ (no text returned)")
        except Exception as e:
            failed += 1
            print(f"✗ ({e})")
    
    db.session.commit()
    print(f"\nDone! Success: {success}, Failed: {failed}")

