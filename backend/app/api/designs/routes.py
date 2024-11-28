# app/api/designs/routes.py
from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
import uuid
from app import db
from app.models.design import Design
from app.utils.dynamodb import DynamoDBClient
from app.utils.stable_diffusion import StableDiffusionClient
from app.utils.s3 import S3Client
from app.api.designs import bp
from datetime import datetime

@bp.route('/generate', methods=['POST'])
@jwt_required()
def generate_design():
    try:
        # リクエストデータの取得と検証
        data = request.get_json()
        if not data or not data.get('prompt'):
            return jsonify({'error': 'Prompt is required'}), 400

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
        image_data = sd_client.generate_image(data['prompt'])
        
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