#!/usr/bin/env python3
"""
BitSheet24 - Ana Uygulama
"""
from flask import Flask, jsonify
from config import get_config, FLASK_ENV
from models import create_tables, drop_tables

def create_app(config_name=None):
    """Flask uygulamasını oluştur"""
    app = Flask(__name__)
    
    # Konfigürasyonu yükle
    config = get_config(config_name or FLASK_ENV)
    app.config.from_object(config)
    
    # Routeları kaydet
    @app.route('/')
    def index():
        return jsonify({
            'message': 'BitSheet24 API\'ye Hoşgeldiniz!',
            'version': '1.0.0',
            'environment': FLASK_ENV
        })
    
    @app.route('/health')
    def health():
        return jsonify({
            'status': 'healthy',
            'message': 'Sistem çalışıyor'
        })
    
    @app.route('/api/v1/info')
    def info():
        return jsonify({
            'app': 'BitSheet24',
            'version': '1.0.0',
            'database': app.config.get('SQLALCHEMY_DATABASE_URI', '').split('@')[-1],
            'debug': app.config.get('DEBUG', False)
        })
    
    return app

if __name__ == '__main__':
    # Tabloları oluştur
    try:
        create_tables()
    except Exception as e:
        print(f"Tablolar zaten mevcut: {e}")
    
    # Uygulamayı çalıştır
    app = create_app()
    app.run(debug=True, host='127.0.0.1', port=5000)
