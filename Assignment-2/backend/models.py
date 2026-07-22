from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Lead(db.Model):
    """Lead table – one row per scraped business contact."""
    __tablename__ = 'leads'

    id            = db.Column(db.Integer, primary_key=True)
    business_name = db.Column(db.String(255), nullable=False, default='Unknown')
    owner         = db.Column(db.String(255), default='')
    email         = db.Column(db.String(255), default='')
    phone         = db.Column(db.String(100), default='')
    country       = db.Column(db.String(100), default='')
    source        = db.Column(db.String(500), default='')   # URL / domain
    score         = db.Column(db.Integer, default=0)         # confidence 0-100
    contacted     = db.Column(db.Boolean, default=False)
    website       = db.Column(db.String(500), default='')
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':            self.id,
            'business_name': self.business_name,
            'owner':         self.owner,
            'email':         self.email,
            'phone':         self.phone,
            'country':       self.country,
            'source':        self.source,
            'score':         self.score,
            'contacted':     self.contacted,
            'website':       self.website,
        }


class AppStats(db.Model):
    """Single-row stats table (id always = 1)."""
    __tablename__ = 'app_stats'

    id           = db.Column(db.Integer, primary_key=True, default=1)
    total_leads  = db.Column(db.Integer, default=0)
    contacted    = db.Column(db.Integer, default=0)
    emails_sent  = db.Column(db.Integer, default=0)
    failed       = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            'total_leads': self.total_leads,
            'contacted':   self.contacted,
            'emails_sent': self.emails_sent,
            'failed':      self.failed,
        }
