from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import datetime
import uuid
import os
import json
from openai import OpenAI

app = Flask(__name__)
CORS(app)

app.config["JWT_SECRET_KEY"] = "f8s3j6k1a9d0g4h5l2p7w3e9r5t8y2u"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = datetime.timedelta(days=30)
jwt = JWTManager(app)

DEEPSEEK_API_KEY = "sk-5d33c45b52ec4b5b9eb689c43156da8b"

DATABASE = 'deepseek_server.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        member_expire TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS activation_codes (
        code TEXT PRIMARY KEY,
        days INTEGER NOT NULL,
        used INTEGER DEFAULT 0
    )''')
    conn.commit()
    conn.close()

init_db()

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'msg': '用户名和密码不能为空'}), 400
    if len(password) < 6:
        return jsonify({'msg': '密码至少6位'}), 400
    conn = get_db()
    user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    if user:
        conn.close()
        return jsonify({'msg': '用户名已存在'}), 409
    password_hash = generate_password_hash(password)
    conn.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, password_hash))
    conn.commit()
    conn.close()
    return jsonify({'msg': '注册成功'}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'msg': '缺少用户名或密码'}), 400
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    if user and check_password_hash(user['password_hash'], password):
        access_token = create_access_token(identity=username)
        return jsonify({'msg': '登录成功', 'token': access_token, 'member_expire': user['member_expire']}), 200
    return jsonify({'msg': '用户名或密码错误'}), 401

@app.route('/api/user/info', methods=['GET'])
@jwt_required()
def user_info():
    username = get_jwt_identity()
    conn = get_db()
    user = conn.execute('SELECT username, member_expire FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    if not user:
        return jsonify({'msg': '用户不存在'}), 404
    is_member = False
    expire_str = user['member_expire']
    if expire_str:
        try:
            expire_date = datetime.datetime.strptime(expire_str, '%Y-%m-%d')
            if expire_date >= datetime.datetime.now():
                is_member = True
        except:
            pass
    return jsonify({'username': user['username'], 'member_expire': expire_str, 'is_member': is_member})

@app.route('/api/member/check', methods=['GET'])
@jwt_required()
def check_membership():
    username = get_jwt_identity()
    conn = get_db()
    user = conn.execute('SELECT member_expire FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    if not user:
        return jsonify({'is_member': False, 'msg': '用户不存在'}), 404
    expire_str = user['member_expire']
    is_member = False
    if expire_str:
        try:
            expire_date = datetime.datetime.strptime(expire_str, '%Y-%m-%d')
            if expire_date >= datetime.datetime.now():
                is_member = True
        except:
            pass
    return jsonify({'is_member': is_member, 'member_expire': expire_str})

@app.route('/api/member/activate', methods=['POST'])
@jwt_required()
def activate_member():
    username = get_jwt_identity()
    data = request.get_json()
    code = data.get('code')
    if not code:
        return jsonify({'msg': '请输入激活码'}), 400
    conn = get_db()
    code_row = conn.execute('SELECT * FROM activation_codes WHERE code = ? AND used = 0', (code,)).fetchone()
    if not code_row:
        conn.close()
        return jsonify({'msg': '激活码无效或已使用'}), 400
    days = code_row['days']
    user = conn.execute('SELECT member_expire FROM users WHERE username = ?', (username,)).fetchone()
    current_expire = user['member_expire'] if user and user['member_expire'] else datetime.datetime.now().strftime('%Y-%m-%d')
    try:
        current_date = datetime.datetime.strptime(current_expire, '%Y-%m-%d')
        if current_date < datetime.datetime.now():
            current_date = datetime.datetime.now()
    except:
        current_date = datetime.datetime.now()
    new_expire = current_date + datetime.timedelta(days=days)
    new_expire_str = new_expire.strftime('%Y-%m-%d')
    conn.execute('UPDATE users SET member_expire = ? WHERE username = ?', (new_expire_str, username))
    conn.execute('UPDATE activation_codes SET used = 1 WHERE code = ?', (code,))
    conn.commit()
    conn.close()
    return jsonify({'msg': f'激活成功！会员到期 {new_expire_str}', 'member_expire': new_expire_str})

@app.route('/api/admin/gen_code', methods=['POST'])
def gen_code():
    data = request.get_json()
    if data.get('admin_key') != '490145692hailin':
        return jsonify({'msg': '无权限'}), 403
    days = data.get('days', 365)
    code = str(uuid.uuid4()).replace('-', '')[:16].upper()
    conn = get_db()
    conn.execute('INSERT INTO activation_codes (code, days) VALUES (?, ?)', (code, days))
    conn.commit()
    conn.close()
    return jsonify({'code': code, 'days': days})

# ---------- 流式聊天接口 ----------
@app.route('/api/chat', methods=['POST'])
@jwt_required()
def chat_stream():
    username = get_jwt_identity()
    conn = get_db()
    user = conn.execute('SELECT member_expire FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    if not user or not user['member_expire']:
        return jsonify({'msg': '未开通会员，请先激活'}), 403
    try:
        expire_date = datetime.datetime.strptime(user['member_expire'], '%Y-%m-%d')
        if expire_date < datetime.datetime.now():
            return jsonify({'msg': '会员已过期，请续费'}), 403
    except:
        return jsonify({'msg': '会员状态异常'}), 403

    data = request.get_json()
    messages = data.get('messages', [])
    if not messages:
        return jsonify({'msg': '缺少消息'}), 400

    def generate():
        try:
            client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1")
            stream = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
