# backend/app.py
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
import requests

load_dotenv()  # .envファイルから環境変数を読み込み

app = Flask(__name__)
# CORS(app)
# より詳細なCORS設定
cors_config = {
    "origins": [
        "http://localhost:5173",  # 開発環境のフロントエンド
        "http://your-frontend-domain.com",  # 本番環境のフロントエンド
        "http://43.207.168.95:5000"
    ],
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization"]
}
CORS(app, resources={r"/api/*": cors_config})

# 環境変数からポート設定を取得
port = int(os.environ.get("PORT", 5000))

@app.route('/')
def hello():
    return "Hello, CustomAI Tee!"

@app.route('/api/message')
def get_message():
    return jsonify({"message": "Hello from Flask!"})

@app.route('/api/generate_design', methods=['POST'])
def generate_design():
    data = request.get_json()
    theme = data.get("theme", "")
    
    # Stable Diffusion APIへのリクエスト
    api_url = "https://api.replicate.com/v1/predictions"
    headers = {
        "Authorization": f"Token {os.getenv('REPLICATE_API_TOKEN')}",
        "Content-Type": "application/json"
    }
    payload = {
        "version": "stable-diffusion-1.5",
        "input": {
            "prompt": theme
        }
    }

    response = requests.post(api_url, headers=headers, json=payload)
    result = response.json()
    print("API Response:", result)

    
    # 画像URLを取得
    image_url = result["output"][0] if "output" in result else "Error generating image"
    return jsonify({"message": f"Design generated for theme: {theme}", "image_url": image_url})

# if __name__ == '__main__':
#     app.run(debug=True)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port, debug=True)