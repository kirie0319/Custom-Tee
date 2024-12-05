# app/utils/email.py
import boto3
from botocore.exceptions import ClientError
from flask import current_app
from jinja2 import Template
import logging

class EmailService:
   @staticmethod
   def _get_ses_client():
       return boto3.client(
           'ses',
           aws_access_key_id=current_app.config['AWS_ACCESS_KEY_ID'],
           aws_secret_access_key=current_app.config['AWS_SECRET_ACCESS_KEY'],
           region_name=current_app.config['AWS_REGION']
       )

   @staticmethod
   def _get_order_template_html(order, lang='ja', is_admin_copy=False):
       if lang == 'ja':
           template = """
           <!DOCTYPE html>
           <html>
           <head>
               <meta charset="utf-8">
               <style>
                   body { font-family: "Helvetica Neue", Arial, "Hiragino Kaku Gothic ProN", "Hiragino Sans", Meiryo, sans-serif; }
                   .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                   .header { text-align: center; padding: 20px; background-color: #4F46E5; color: white; }
                   .content { padding: 20px; background-color: #ffffff; }
                   .order-details { margin: 20px 0; }
                   .total { font-size: 1.2em; font-weight: bold; }
                   .footer { text-align: center; padding: 20px; color: #666; }
                   .admin-notice { background-color: #fff3cd; padding: 15px; margin-bottom: 20px; border: 1px solid #ffeeba; }
               </style>
           </head>
           <body>
               <div class="container">
                   {% if is_admin_copy %}
                   <div class="admin-notice">
                       <h2>⚠️ 管理者用通知</h2>
                       <p>以下の注文情報を顧客（{{ order.customer_email }}）に転送してください。</p>
                       <p>注文番号: {{ order.id }}</p>
                   </div>
                   {% endif %}

                   <div class="header">
                       <h1>ご注文ありがとうございます</h1>
                   </div>
                   
                   <div class="content">
                       <h2>注文詳細</h2>
                       <p>注文番号: {{ order.id }}</p>
                       
                       <div class="order-details">
                           {% for item in order.order_items %}
                           <div style="margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 10px;">
                               <p>デザインID: {{ item.design_id }}</p>
                               <p>サイズ: {{ item.size }}</p>
                               <p>カラー: {{ item.color }}</p>
                               <p>数量: {{ item.quantity }}</p>
                               <p>価格: ¥{{ "{:,}".format(item.price) }}</p>
                           </div>
                           {% endfor %}
                           
                           <p class="total">
                               合計金額: ¥{{ "{:,}".format(order.total_amount) }}
                           </p>
                       </div>
                       
                       <div style="margin-top: 20px;">
                           <h3>配送先情報</h3>
                           <p>{{ order.shipping_address.name }}</p>
                           <p>{{ order.shipping_address.address }}</p>
                           <p>{{ order.shipping_address.city }}</p>
                           <p>{{ order.shipping_address.postal_code }}</p>
                           <p>{{ order.shipping_address.country }}</p>
                       </div>
                   </div>
                   
                   <div class="footer">
                       <p>ご不明な点がございましたら、お気軽にお問い合わせください。</p>
                       <p>© 2024 CustomAI Tee. All rights reserved.</p>
                   </div>
               </div>
           </body>
           </html>
           """
       else:
           template = """[English template here]"""
           
       return Template(template)

   @staticmethod
   def _get_status_update_template(context, lang='ja'):
       if lang == 'ja':
           template = """
           <!DOCTYPE html>
           <html>
           <head>
               <meta charset="utf-8">
               <style>
                   body { font-family: "Helvetica Neue", Arial, "Hiragino Kaku Gothic ProN", "Hiragino Sans", Meiryo, sans-serif; }
                   .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                   .admin-notice { background-color: #fff3cd; padding: 15px; margin-bottom: 20px; border: 1px solid #ffeeba; }
                   .status-update { background-color: #e8f4fd; padding: 15px; margin: 20px 0; border-radius: 5px; }
               </style>
           </head>
           <body>
               <div class="container">
                   <div class="admin-notice">
                       <h2>⚠️ 管理者用通知</h2>
                       <p>以下のステータス更新通知を顧客（{{ customer_email }}）に転送してください。</p>
                   </div>

                   <h1>ご注文のステータスが更新されました</h1>
                   <p>注文番号: {{ order.id }}</p>

                   <div class="status-update">
                       <p>ステータスが更新されました：</p>
                       <p>{{ old_status }} → {{ new_status }}</p>
                   </div>

                   <div style="margin-top: 20px;">
                       <p>ご注文内容の確認やステータスの詳細は、マイページからご確認いただけます。</p>
                   </div>

                   <div style="margin-top: 20px;">
                       <p>ご不明な点がございましたら、お気軽にお問い合わせください。</p>
                   </div>
               </div>
           </body>
           </html>
           """
       else:
           template = """[English template here]"""
           
       return Template(template)

   @staticmethod
   def send_order_confirmation(order, recipient_email, lang='ja'):
       try:
           ses_client = EmailService._get_ses_client()
           sender = current_app.config['ADMIN_EMAIL']
           admin_email = current_app.config['ADMIN_EMAIL']

           order_data = order.to_dict() if hasattr(order, 'to_dict') else order
           order_data = {**order_data, 'customer_email': recipient_email}

           template = EmailService._get_order_template_html(
               order_data, 
               lang=lang,
               is_admin_copy=True
           )
           html_content = template.render(order=order_data)

           try:
               response = ses_client.send_email(
                   Source=sender,
                   Destination={
                       'ToAddresses': [admin_email]
                   },
                   Message={
                       'Subject': {
                           'Data': f'[要転送] 新規注文 #{order_data["id"]} - CustomAI Tee',
                           'Charset': 'UTF-8'
                       },
                       'Body': {
                           'Html': {
                               'Data': html_content,
                               'Charset': 'UTF-8'
                           }
                       }
                   }
               )
               
               logging.info(f"Order confirmation email sent to admin. MessageId: {response['MessageId']}")
               return True

           except ClientError as e:
               logging.error(f"Failed to send email via SES: {str(e)}")
               return False

       except Exception as e:
           logging.error(f"Error in send_order_confirmation: {str(e)}")
           import traceback
           traceback.print_exc()
           return False

   @staticmethod
   def send_shipping_notification(order, recipient_email, tracking_number=None, lang='ja'):
       try:
           ses_client = EmailService._get_ses_client()
           sender = current_app.config['ADMIN_EMAIL']
           admin_email = current_app.config['ADMIN_EMAIL']

           subject = '[要転送] 商品発送のお知らせ - CustomAI Tee'
           template = """
           <!DOCTYPE html>
           <html>
           <head>
               <meta charset="utf-8">
               <style>
                   body { font-family: "Helvetica Neue", Arial, "Hiragino Kaku Gothic ProN", "Hiragino Sans", Meiryo, sans-serif; }
                   .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                   .admin-notice { background-color: #fff3cd; padding: 15px; margin-bottom: 20px; border: 1px solid #ffeeba; }
               </style>
           </head>
           <body>
               <div class="container">
                   <div class="admin-notice">
                       <h2>⚠️ 管理者用通知</h2>
                       <p>以下の発送通知を顧客（{{ customer_email }}）に転送してください。</p>
                   </div>

                   <h1>商品を発送いたしました</h1>
                   <p>注文番号: {{ order.id }}</p>
                   {% if tracking_number %}
                   <p>追跡番号: {{ tracking_number }}</p>
                   {% endif %}

                   <div style="margin-top: 20px;">
                       <h3>配送先情報</h3>
                       <p>{{ order.shipping_address.name }}</p>
                       <p>{{ order.shipping_address.address }}</p>
                       <p>{{ order.shipping_address.city }}</p>
                       <p>{{ order.shipping_address.postal_code }}</p>
                       <p>{{ order.shipping_address.country }}</p>
                   </div>
               </div>
           </body>
           </html>
           """
           
           html_content = Template(template).render(
               order=order,
               tracking_number=tracking_number,
               customer_email=recipient_email
           )

           try:
               response = ses_client.send_email(
                   Source=sender,
                   Destination={
                       'ToAddresses': [admin_email]
                   },
                   Message={
                       'Subject': {
                           'Data': subject,
                           'Charset': 'UTF-8'
                       },
                       'Body': {
                           'Html': {
                               'Data': html_content,
                               'Charset': 'UTF-8'
                           }
                       }
                   }
               )

               logging.info(f"Shipping notification email sent to admin. MessageId: {response['MessageId']}")
               return True

           except ClientError as e:
               logging.error(f"Failed to send email via SES: {str(e)}")
               return False

       except Exception as e:
           logging.error(f"Error in send_shipping_notification: {str(e)}")
           return False

   @staticmethod
   def send_status_update(order, recipient_email, old_status, new_status, lang='ja'):
       try:
           ses_client = EmailService._get_ses_client()
           sender = current_app.config['ADMIN_EMAIL']
           admin_email = current_app.config['ADMIN_EMAIL']

           status_messages = {
               'paid': '支払い完了',
               'processing': '処理中',
               'shipped': '発送済み',
               'delivered': '配達完了',
               'cancelled': 'キャンセル'
           }

           context = {
               'order': order,
               'old_status': status_messages.get(old_status, old_status),
               'new_status': status_messages.get(new_status, new_status),
               'customer_email': recipient_email
           }

           template = EmailService._get_status_update_template(context, lang)
           html_content = template.render(**context)

           response = ses_client.send_email(
               Source=sender,
               Destination={'ToAddresses': [admin_email]},
               Message={
                   'Subject': {
                       'Data': f'[要転送] 注文ステータス更新 - 注文番号: {order.id}',
                       'Charset': 'UTF-8'
                   },
                   'Body': {
                       'Html': {
                           'Data': html_content,
                           'Charset': 'UTF-8'
                       }
                   }
               }
           )
           
           logging.info(f"Status update email sent to admin. MessageId: {response['MessageId']}")
           return True

       except Exception as e:
           logging.error(f"Status update email error: {str(e)}")
           return False