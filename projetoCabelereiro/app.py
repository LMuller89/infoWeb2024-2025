from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client, Client
import os
import time
from flask import jsonify
from flask import send_from_directory
from io import BytesIO
from werkzeug.utils import secure_filename
from supabase import create_client
import tempfile

SUPABASE_URL = "https://vuvuiddlnpppzsyrhmff.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ1dnVpZGRsbnBwcHpzeXJobWZmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NTg2ODQ4NiwiZXhwIjoyMDYxNDQ0NDg2fQ.NLxj4Vbi-EdvQaxlqc6qhRQZ7YpSWXQkGB7m-rRrSJ8"  # use a chave correta aqui

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configure o bucket do Supabase
BUCKET_NAME = "gallery"

# Cache com expiração
theme_cache = {
    "color": None,
    "timestamp": 0,
    "ttl": 5  # 30 segundos para teste
}

def get_cached_theme_color(force_refresh=False):
    """Obter a cor do tema, possivelmente do cache"""
    current_time = time.time()
    
    # Verificar se precisa atualizar o cache
    if (force_refresh or 
        theme_cache["color"] is None or 
        (current_time - theme_cache["timestamp"] > theme_cache["ttl"])):
        
        try:
            # Buscar do banco de dados
            response = supabase.table('theme_config').select('*').limit(1).execute()
            data = response.data
            if data:
                theme_cache["color"] = data[0]['background_color']
            else:
                theme_cache["color"] = "#ffffff"
            
            # Atualizar timestamp
            theme_cache["timestamp"] = current_time
            
        except Exception as e:
            print(f"Erro ao buscar cor do tema: {e}")
            if theme_cache["color"] is None:
                theme_cache["color"] = "#ffffff"
    
    return theme_cache["color"]

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'mysecretkey')  # Recomendação: usar variável de ambiente

# Redirecionamento da raiz para /home
@app.route('/')
def redirect_to_home():
    return redirect(url_for('index'))

# Rota principal
@app.route('/home')
def index():
    cor_principal = get_cached_theme_color()

    try:
        # Corrigido: Buscar diretamente da TABELA, não do bucket
        response = supabase.table('gallery_images').select('*').execute()
        data = response.data if response.data else []

        # Montar o dicionário com os IDs corretos
        gallery_images = {img['image_id']: img['image_url'] for img in data}

        # DEBUG opcional: ver no terminal o que está vindo
        print("DEBUG: gallery_images =", gallery_images)

    except Exception as e:
        print(f"Erro ao buscar imagens: {str(e)}")
        gallery_images = {}

    return render_template('index.html',
                         cor_principal=cor_principal,
                         gallery_images=gallery_images)

# Página de registro
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        hashed_password = generate_password_hash(password)

        # Salvar no Supabase
        try:
            supabase.table('users').insert({
                'email': email,
                'password': hashed_password
            }).execute()
            flash('Usuário registrado com sucesso! Faça login.', 'success')
            return redirect(url_for('admin'))
        except Exception as e:
            flash(f'Erro ao registrar: {str(e)}', 'danger')
            return redirect(url_for('register'))
    
    # Se for GET, exibe a página de registro
    return render_template('register.html')

# Admin protegida
@app.route('/admin')
def admin():
    print("Session data:", session)
    logged_in = 'user_id' in session

    try:
        # Buscar dados da tabela gallery_images com image_id e image_url
        response = supabase.table('gallery_images').select('*').execute()
        data = response.data if response.data else []

        # Mapear corretamente pelo ID (ex: 'image-1', 'image-2', etc.)
        gallery_images = {img['image_id']: img['image_url'] for img in data}

    except Exception as e:
        print(f"Erro ao buscar imagens: {str(e)}")
        gallery_images = {}

    return render_template('admin.html',
                           logged_in=logged_in,
                           gallery_images=gallery_images)


# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('admin'))

# Login
@app.route('/admin/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    # Buscar usuário no Supabase
    response = supabase.table('users').select('*').eq('email', email).execute()
    users = response.data

    if users and len(users) > 0:
        user = users[0]
        if check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['email'] = user['email']
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('admin'))

    flash('Email ou senha inválidos.', 'danger')
    return redirect(url_for('admin'))

# Rota para obter a cor do tema
@app.route('/api/theme', methods=['GET'])
def get_theme_color():
    try:
        color = get_cached_theme_color()
        return jsonify({'color': color})
    except Exception as e:
        return jsonify({'color': '#ffffff'}), 200  # Retornar status 200 mesmo com erro

# Rota para atualizar a cor do tema
@app.route('/api/theme', methods=['POST'])
def update_theme_color():
    try:
        new_color = request.json.get('color')
        supabase.table('theme_config').delete().neq('id', 0).execute()
        supabase.table('theme_config').insert({'background_color': new_color}).execute()
        theme_cache["valor"] = new_color  # atualiza o cache aqui
        return jsonify({'message': 'Cor atualizada com sucesso'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

# Rota para obter imagens
@app.route('/api/gallery', methods=['GET'])
def get_gallery_images():
    try:
        response = supabase.table('gallery_images').select('*').execute()
        db_images = {img['image_id']: img['image_url'] for img in response.data}

        # Garante que a estrutura sempre tenha image-1 até image-6
        images = {}
        for i in range(1, 7):
            key = f'image-{i}'
            images[key] = db_images.get(key, '')

        return jsonify(images)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/gallery', methods=['POST'])
def update_gallery_image():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        image_id = request.form.get('image_id')
        file = request.files.get('image')

        if not image_id:
            return jsonify({'error': 'ID da imagem não fornecido'}), 400
        if not file or file.filename == '':
            return jsonify({'error': 'Nenhum arquivo selecionado'}), 400

        file_ext = secure_filename(file.filename).split('.')[-1].lower()
        if file_ext not in {'png', 'jpg', 'jpeg'}:
            return jsonify({'error': 'Formato inválido (use PNG/JPG)'}), 400

        new_filename = f"{image_id}.{file_ext}"

        # Criar arquivo temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as temp:
            file.save(temp.name)
            temp_path = temp.name

        # Upload para Supabase Storage
        supabase.storage.from_(BUCKET_NAME).upload(
            path=new_filename,
            file=temp_path,
            file_options={"contentType": file.mimetype}
        )

        # Remover arquivo temporário
        os.remove(temp_path)

        # Obter URL pública
        image_url = supabase.storage.from_(BUCKET_NAME).get_public_url(new_filename)

        # ✅ Usar o ID correto enviado pelo HTML
        supabase.table('gallery_images').upsert({
            'image_id': image_id,
            'image_url': image_url
        }).execute()

        return jsonify({'message': 'Success', 'new_url': image_url})

    except Exception as e:
        print(f"ERRO GERAL: {str(e)}")
        return jsonify({'error': f"Erro no upload: {str(e)}"}), 500
    
if __name__ == '__main__':
    app.run(debug=True)
    
