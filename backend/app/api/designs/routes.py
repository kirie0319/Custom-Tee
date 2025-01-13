# app/api/designs/routes.py
from flask import jsonify, request
import requests
import os
from flask_jwt_extended import jwt_required, get_jwt_identity
import uuid
from app import db
from app.models.design import Design
from app.utils.dynamodb import DynamoDBClient
from app.utils.stable_diffusion import StableDiffusionClient
from app.utils.s3 import S3Client
from app.api.designs import bp
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def translate_text(api_key, text, target_language):
    """
    Deepl APIを使用してテキストを翻訳する関数
    
    :param api_key: Deepl APIの認証キー
    :param text: 翻訳するテキスト
    :param target_language: 翻訳先の言語コード（例: "EN"）
    :return: 翻訳結果のテキスト
    """
    url = 'https://api-free.deepl.com/v2/translate'

    # リクエストのパラメータ
    params = {
        'auth_key': api_key,  # APIキー
        'text': text,  # 翻訳するテキスト
        'target_lang': target_language  # 翻訳先の言語
    }

    # リクエストを送信
    response = requests.post(url, data=params)

    # レスポンスの確認と翻訳結果の返却
    if response.status_code == 200:
        translated_text = response.json()['translations'][0]['text']
        return translated_text
    else:
        return f"エラーが発生しました: {response.status_code}, {response.text}"

@bp.route('/generate', methods=['POST'])
@jwt_required()
def generate_design():
    try:
        # リクエストデータの取得と検証
        data = request.get_json()
        if not data or not data.get('prompt'):
            return jsonify({'error': 'Prompt is required'}), 400

        # 使用例
        api_key = os.getenv('DEEPL_API_KEY')  # 自分のAPIキーに置き換えてください
        text_to_translate = data['prompt']
        target_language = "EN"  # 翻訳先の言語（例: "EN"）

        translated_text = translate_text(api_key, text_to_translate, target_language)
        print(f"翻訳前: {data['prompt']}")
        print(f"翻訳結果: {translated_text}")
        print(type(data['prompt']))

        current_user_id = get_jwt_identity()
        request_id = str(uuid.uuid4())

        # DynamoDBに生成リクエストを保存
        dynamodb_client = DynamoDBClient()
        dynamodb_client.store_design_request(
            request_id=request_id,
            user_id=str(current_user_id),
            prompt=data['prompt']
        )

        # Stable Diffusionで画像生成
        sd_client = StableDiffusionClient()
        image_data = sd_client.generate_image(translated_text)
        
        # S3に画像をアップロード
        s3_client = S3Client()
        s3_key = f'designs/{current_user_id}/{request_id}.png'
        image_url = s3_client.upload_design(image_data, s3_key)

        # デザイン情報をRDSに保存
        design = Design(
            user_id=current_user_id,
            prompt=data['prompt'],
            image_url=image_url,
            s3_key=s3_key,
            position_x=data.get('position_x', 0),
            position_y=data.get('position_y', 0),
            scale=data.get('scale', 1.0)
        )
        
        db.session.add(design)
        db.session.commit()

        # 生成されたデザインをキャッシュ
        dynamodb_client.cache_design(str(design.id), image_url)

        return jsonify({
            'message': 'Design generated successfully',
            'design': {
                'id': design.id,
                'image_url': design.image_url,
                'prompt': design.prompt,
                'created_at': design.created_at.isoformat()
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/designs', methods=['GET'])
@jwt_required()
def get_user_designs():
    try:
        current_user_id = get_jwt_identity()
        designs = Design.query.filter_by(user_id=current_user_id).order_by(Design.created_at.desc()).all()
        
        return jsonify({
            'designs': [{
                'id': design.id,
                'image_url': design.image_url,
                'prompt': design.prompt,
                'created_at': design.created_at.isoformat()
            } for design in designs]
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/designs/<int:design_id>', methods=['GET'])
@jwt_required()
def get_design(design_id):
    try:
        current_user_id = get_jwt_identity()
        design = Design.query.get_or_404(design_id)
        
        # 所有者チェック
        if design.user_id != current_user_id:
            return jsonify({'error': 'Unauthorized access'}), 403

        return jsonify({
            'id': design.id,
            'image_url': design.image_url,
            'prompt': design.prompt,
            'position_x': design.position_x,
            'position_y': design.position_y,
            'scale': design.scale,
            'created_at': design.created_at.isoformat()
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500