from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_migrate import Migrate
from datetime import datetime, timedelta
import os
from models import db, Stock, PriceHistory
from stock_tracker import StockTracker

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///stocks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)
migrate = Migrate(app, db)

# Initialize stock tracker
stock_tracker = StockTracker()

@app.route('/')
def index():
    """Render the main dashboard"""
    stocks = Stock.query.all()
    return render_template('index.html', stocks=stocks)

@app.route('/api/stocks', methods=['GET'])
def get_stocks():
    """Get all stocks"""
    stocks = Stock.query.all()
    return jsonify([stock.to_dict() for stock in stocks])

@app.route('/api/stocks', methods=['POST'])
def add_stock():
    """Add a new stock"""
    data = request.json
    try:
        stock = Stock(
            ticker=data['ticker'].upper(),
            purchase_date=datetime.strptime(data['purchase_date'], '%Y-%m-%d').date(),
            shares=float(data['shares']),
            purchase_price=float(data['purchase_price'])
        )
        db.session.add(stock)
        db.session.commit()
        return jsonify(stock.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/stocks/<int:stock_id>', methods=['DELETE'])
def delete_stock(stock_id):
    """Delete a stock"""
    stock = Stock.query.get_or_404(stock_id)
    db.session.delete(stock)
    db.session.commit()
    return '', 204

@app.route('/api/stocks/<int:stock_id>/prices', methods=['GET'])
def get_stock_prices(stock_id):
    """Get price history for a stock"""
    stock = Stock.query.get_or_404(stock_id)
    prices = PriceHistory.query.filter_by(stock_id=stock_id).order_by(PriceHistory.date.desc()).all()
    return jsonify([price.to_dict() for price in prices])

@app.route('/api/reports/performance', methods=['GET'])
def get_performance_report():
    """Generate performance report"""
    stocks = Stock.query.all()
    performance = []
    
    for stock in stocks:
        latest_price = PriceHistory.query.filter_by(stock_id=stock.id).order_by(PriceHistory.date.desc()).first()
        if latest_price:
            purchase_value = stock.shares * stock.purchase_price
            current_value = stock.shares * latest_price.price
            gain_loss = current_value - purchase_value
            gain_loss_percent = (gain_loss / purchase_value) * 100 if purchase_value > 0 else 0
            
            performance.append({
                'ticker': stock.ticker,
                'shares': stock.shares,
                'purchase_date': stock.purchase_date.isoformat(),
                'purchase_price': stock.purchase_price,
                'current_price': latest_price.price,
                'purchase_value': purchase_value,
                'current_value': current_value,
                'gain_loss': gain_loss,
                'gain_loss_percent': gain_loss_percent
            })
    
    return jsonify(performance)

@app.route('/api/update-prices', methods=['POST'])
def update_prices():
    """Update prices for all stocks"""
    stocks = Stock.query.all()
    updated = 0
    
    for stock in stocks:
        try:
            price_data = stock_tracker.get_current_price(stock.ticker)
            if price_data['price'] > 0:
                price_history = PriceHistory(
                    stock_id=stock.id,
                    date=datetime.now().date(),
                    price=price_data['price'],
                    change=price_data['change'],
                    change_percent=price_data['change_percent']
                )
                db.session.add(price_history)
                updated += 1
        except Exception as e:
            app.logger.error(f"Error updating price for {stock.ticker}: {str(e)}")
    
    db.session.commit()
    return jsonify({'updated': updated})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 