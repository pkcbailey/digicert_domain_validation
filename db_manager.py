#!/usr/bin/env python3
"""
Database Manager for Stock Tracker

This module handles all database operations for the stock tracker application.
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
import os

class DatabaseManager:
    def __init__(self, db_path: str = "stocks.db"):
        """Initialize the database manager"""
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.initialize_db()
    
    def connect(self):
        """Establish connection to the database"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # This enables column access by name
            self.cursor = self.conn.cursor()
        except sqlite3.Error as e:
            print(f"Error connecting to database: {e}")
            raise
    
    def disconnect(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None
    
    def initialize_db(self):
        """Initialize the database with required tables"""
        try:
            self.connect()
            
            # Create tables (we'll add the actual schema based on your requirements)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS stocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    purchase_date TEXT NOT NULL,
                    shares REAL NOT NULL,
                    purchase_price REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            self.conn.commit()
            
        except sqlite3.Error as e:
            print(f"Error initializing database: {e}")
            raise
        finally:
            self.disconnect()
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()

# Example usage:
if __name__ == "__main__":
    # Test database connection
    with DatabaseManager() as db:
        print("Database initialized successfully!") 