from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Stock(db.Model):
    """Stock model for storing stock purchase information"""
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), nullable=False, index=True)
    purchase_date = db.Column(db.Date, nullable=False)
    shares = db.Column(db.Float, nullable=False)
    purchase_price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with price history
    price_history = db.relationship('PriceHistory', backref='stock', lazy=True)
    
    def __repr__(self):
        return f'<Stock {self.ticker}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'ticker': self.ticker,
            'purchase_date': self.purchase_date.isoformat(),
            'shares': self.shares,
            'purchase_price': self.purchase_price,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class PriceHistory(db.Model):
    """Price history model for storing daily stock prices"""
    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    price = db.Column(db.Float, nullable=False)
    change = db.Column(db.Float, nullable=False)
    change_percent = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Composite index for efficient querying
    __table_args__ = (
        db.Index('idx_stock_date', 'stock_id', 'date'),
    )
    
    def __repr__(self):
        return f'<PriceHistory {self.stock_id} {self.date}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'stock_id': self.stock_id,
            'date': self.date.isoformat(),
            'price': self.price,
            'change': self.change,
            'change_percent': self.change_percent,
            'created_at': self.created_at.isoformat()
        } 