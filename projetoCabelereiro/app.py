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
from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime
from uuid import uuid4

SUPABASE_URL = "https://vuvuiddlnpppzsyrhmff.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ1dnVpZGRsbnBwcHpzeXJobWZmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NTg2ODQ4NiwiZXhwIjoyMDYxNDQ0NDg2fQ.NLxj4Vbi-EdvQaxlqc6qhRQZ7YpSWXQkGB7m-rRrSJ8"  # use a chave correta aqui

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configure o bucket do Supabase
BUCKET_NAME = "gallery"

# Cache para duas cores de tema
theme_cache = {
    "section_color": None,  # cor de features/footer/.testimonial
    "body_color": None,     # cor do body
    "timestamp": 0,
    "ttl": 5                # em segundos
}

def get_cached_theme(force_refresh=False):
    """Retorna um dict {'section':..., 'body':...} possivelmente em cache."""
    now = time.time()
    # se cache expirou ou não existe
    if force_refresh or theme_cache["section_color"] is None or now - theme_cache["timestamp"] > theme_cache["ttl"]:
        try:
            resp = supabase.table('theme_config').select('*').limit(1).execute()
            data = resp.data
            if data:
                row = data[0]
                theme_cache["section_color"] = row.get('background_color', '#ffffff')
                theme_cache["body_color"]    = row.get('body_color', '#ffffff')
            else:
                theme_cache["section_color"] = theme_cache["body_color"] = '#ffffff'
            theme_cache["timestamp"] = now
        except Exception as e:
            print(f"Erro ao buscar cores: {e}")
            if theme_cache["section_color"] is None:
                theme_cache["section_color"] = theme_cache["body_color"] = '#ffffff'
    return {
        'section': theme_cache["section_color"],
        'body':    theme_cache["body_color"]
    }

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'mysecretkey')  # Recomendação: usar variável de ambiente

# Redirecionamento da raiz para /home

# Redirecionamento da raiz para /home
@app.route('/')
def redirect_to_home():
    return redirect(url_for('index'))


# Rota principal
@app.route('/home')
def index():
    # 1) Buscar cores do tema (sem alterações)
    tema = get_cached_theme()            # <-- sua função existente
    cor_principal = tema['section']
    cor_body      = tema['body']

    # 2) Buscar imagens da galeria
    try:
        response = supabase.table('gallery_images').select('*').execute()
        data = response.data or []
        gallery_images = {img['image_id']: img['image_url'] for img in data}
    except Exception as e:
        print(f"Erro ao buscar imagens: {e}")
        gallery_images = {}

    # 3) Buscar links sociais
    try:
        response = supabase.table('social_links').select('*').limit(1).execute()
        social_links = response.data[0] if response.data else {
            'instagram': '#',
            'facebook': '#',
            'x': '#',
            'youtube': '#'
        }
    except Exception as e:
        print(f"Erro ao buscar links sociais: {e}")
        social_links = {
            'instagram': '#',
            'facebook': '#',
            'x': '#',
            'youtube': '#'
        }

    # 4) Buscar visibilidade de seções (clients e gallery)
    try:
        response = supabase.table('hidden_sections').select('*').execute()
        rows = response.data or []

        section_visibility = {
            'clients': False,
            'gallery': 'full'
        }

        for row in rows:
            sid = row.get('id')
            if sid == 'clients':
                section_visibility['clients'] = bool(row.get('hidden', False))
            elif sid == 'gallery':
                section_visibility['gallery'] = row.get('gallery_visibility') or 'full'

        print("DEBUG section_visibility:", section_visibility)
    except Exception as e:
        print(f"Erro ao buscar visibilidade: {e}")
        section_visibility = {
            'clients': False,
            'gallery': 'full'
        }

    # 5) Buscar o map_url na tabela settingsmap
    try:
        resp_map = supabase.table('settingsmap').select('map_url').eq('id', 1).execute()
        data_map = resp_map.data
        if data_map and len(data_map) > 0:
            map_url = data_map[0]['map_url']
        else:
            map_url = ""
    except Exception as e:
        print(f"Erro ao buscar map_url: {e}")
        map_url = ""

    # 6) Renderiza o template passando tudo
    return render_template(
        'index.html',
        cor_principal=cor_principal,
        cor_body=cor_body,
        gallery_images=gallery_images,
        social_links=social_links,
        section_visibility=section_visibility,
        map_url=map_url
    )

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

# Rota GET unificada
@app.route('/api/theme', methods=['GET'])
def get_theme():
    try:
        t = get_cached_theme()
        return jsonify({
            'section_color': t['section'],
            'body_color':    t['body']
        })
    except Exception:
        # mesmo em erro, retorna 200 com cores padrão
        return jsonify({
            'section_color': '#ffffff',
            'body_color':    '#ffffff'
        }), 200

# Rota POST para atualizar section_color
@app.route('/api/theme/section', methods=['POST'])
def update_section_color():
    try:
        new_color = request.json.get('color')
        current   = get_cached_theme()
        # grava no DB mantendo body_color atual
        supabase.table('theme_config').delete().neq('id', 0).execute()
        supabase.table('theme_config').insert({
            'background_color': new_color,
            'body_color':       current['body']
        }).execute()
        theme_cache["section_color"] = new_color
        return jsonify({'message': 'Seção atualizada com sucesso'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Nova rota POST para atualizar body_color
@app.route('/api/theme/body', methods=['POST'])
def update_body_color():
    try:
        new_color = request.json.get('color')
        current   = get_cached_theme()
        # grava no DB mantendo section_color atual
        supabase.table('theme_config').delete().neq('id', 0).execute()
        supabase.table('theme_config').insert({
            'background_color': current['section'],
            'body_color':       new_color
        }).execute()
        theme_cache["body_color"] = new_color
        return jsonify({'message': 'Body atualizado com sucesso'})
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

        # 🧹 Deletar todas versões anteriores com diferentes extensões
        possible_extensions = ['jpg', 'jpeg', 'png']
        filenames_to_delete = [f"{image_id}.{ext}" for ext in possible_extensions]

        try:
            supabase.storage.from_(BUCKET_NAME).remove(filenames_to_delete)
        except Exception as del_err:
            print(f"Aviso: falha ao deletar imagens antigas: {del_err}")

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

        # Atualizar/inserir no banco
        supabase.table('gallery_images').upsert({
            'image_id': image_id,
            'image_url': image_url
        }).execute()

        return jsonify({'message': 'Success', 'new_url': image_url})

    except Exception as e:
        print(f"ERRO GERAL: {str(e)}")
        return jsonify({'error': f"Erro no upload: {str(e)}"}), 500
    
@app.route('/api/social-links', methods=['GET', 'POST'])
def social_links():
    if request.method == 'GET':
        result = supabase.table('social_links').select('*').limit(1).execute()
        if result.data:
            return jsonify(result.data[0])
        else:
            return jsonify({
                'instagram': '',
                'facebook': '',
                'x': '',
                'youtube': ''
            })

    elif request.method == 'POST':
        try:
            data = request.get_json()

            # Buscar o ID da única linha existente
            result = supabase.table('social_links').select('id').limit(1).execute()
            if result.data:
                row_id = result.data[0]['id']
                supabase.table('social_links').update({
                    'instagram': data.get('instagram', ''),
                    'facebook': data.get('facebook', ''),
                    'x': data.get('x', ''),
                    'youtube': data.get('youtube', ''),
                    'updated_at': datetime.now().isoformat()  # ✅ Correto
                }).eq('id', row_id).execute()
                return jsonify({'message': 'Links atualizados com sucesso!'})
            else:
                # Caso não exista ainda, inserir novo
                supabase.table('social_links').insert([{
                    'id': str(uuid4()),
                    'instagram': data.get('instagram', ''),
                    'facebook': data.get('facebook', ''),
                    'x': data.get('x', ''),
                    'youtube': data.get('youtube', ''),
                    'updated_at': datetime.now().isoformat()  # ✅ Correto
                }]).execute()
                return jsonify({'message': 'Links criados com sucesso!'})

        except Exception as e:
            print(f"Erro no POST /api/social-links: {e}")
            return jsonify({'error': str(e)}), 500

@app.route('/api/section-visibility', methods=['GET', 'POST'])
def section_visibility():
    # retorna estado atual de *clients* e *gallery*

    if request.method == 'GET':
        try:
            result = supabase.table('hidden_sections').select('*').execute()
            vis = {}
            if result.data:
                for row in result.data:
                    section_id = row.get('id')
                    # Se for clients, devolve o booleano de 'hidden'
                    if section_id == 'clients':
                        vis['clients'] = bool(row.get('hidden', False))
                    # Se for gallery, devolve a string de 'gallery_visibility'
                    elif section_id == 'gallery':
                        # Se estiver nulo, retornar valor padrão 'full'
                        vis['gallery'] = row.get('gallery_visibility') or 'full'
                # Se não existir linha para 'clients' ou 'gallery', adiciona valores padrão:
                if 'clients' not in vis:
                    vis['clients'] = False
                if 'gallery' not in vis:
                    vis['gallery'] = 'full'
            else:
                # Se a tabela estiver vazia, assume clientes visível e galeria em 'full'
                vis = {
                    'clients': False,
                    'gallery': 'full'
                }
            return jsonify(vis)
        except Exception as e:
            print(f"Erro ao buscar visibilidade: {e}")
            return jsonify({}), 500

    # atualiza *clients* e/ou *gallery* JSON de entrada pode ter: { "clients": <true|false> } e/ou { "gallery": "<none|partial|full>" }
    
    elif request.method == 'POST':
        try:
            data = request.get_json() or {}
            # No mínimo deve haver a chave 'clients' ou 'gallery' no JSON
            if not any(key in data for key in ('clients', 'gallery')):
                return jsonify({'error': "Envie 'clients' ou 'gallery' no corpo."}), 400

            # 2.1) Se vier valor para clients, faz upsert em hidden
            if 'clients' in data:
                valor_clients = data['clients']
                try:
                    ocultar = bool(valor_clients)
                except:
                    return jsonify({'error': "Valor inválido para 'clients' (deve ser true/false)."}), 400

                supabase.table('hidden_sections').upsert({
                    'id': 'clients',
                    'hidden': ocultar,
                    'updated_at': datetime.now().isoformat()
                }, on_conflict='id').execute()

            # 2.2) Se vier valor para gallery, faz upsert em gallery_visibility
            if 'gallery' in data:
                modo = data['gallery']
                if modo not in ('none', 'partial', 'full'):
                    return jsonify({'error': "Valor inválido para 'gallery' (use 'none', 'partial' ou 'full')."}), 400

                supabase.table('hidden_sections').upsert({
                    'id': 'gallery',
                    'gallery_visibility': modo,
                    'updated_at': datetime.now().isoformat()
                }, on_conflict='id').execute()

            return jsonify({'message': 'Visibilidade atualizada!'})
        except Exception as e:
            print(f"Erro ao atualizar visibilidade: {e}")
            return jsonify({'error': str(e)}), 500
        
# --- INÍCIO: rota separada /admin/map para editar o Google Maps --- #
@app.route('/admin/map', methods=['GET', 'POST'])
def admin_map():
    # (1) Mesmo critério de autenticação que /admin
    logged_in = 'user_id' in session

    # (2) Se veio via POST, atualiza o map_url
    if request.method == 'POST':
        nova_url = request.form.get("map_url", "").strip()
        if nova_url:
            try:
                supabase.table("settingsmap") \
                    .update({"map_url": nova_url}) \
                    .eq("id", 1) \
                    .execute()
                print("DEBUG: map_url atualizado para:", nova_url)
            except Exception as e:
                print(f"Erro ao atualizar map_url: {e}")
        # Redireciona de volta para a mesma tela em GET
        return redirect(url_for('admin_map'))

    # (3) Se for GET, buscamos primeiro os gallery_images (igual /admin)
    try:
        response = supabase.table('gallery_images').select('*').execute()
        data = response.data or []
        gallery_images = {img['image_id']: img['image_url'] for img in data}
    except Exception as e:
        print(f"Erro ao buscar imagens no admin_map: {e}")
        gallery_images = {}

    # (4) Agora buscamos o map_url atual na tabela settingsmap
    try:
        resp_map = supabase.table("settingsmap") \
            .select("map_url") \
            .eq("id", 1) \
            .execute()
        data_map = resp_map.data
        print("DEBUG: data_map retornado pelo Supabase:", data_map)
        if data_map and len(data_map) > 0:
            map_url_atual = data_map[0]["map_url"] or ""
        else:
            map_url_atual = ""
    except Exception as e:
        print(f"Erro ao buscar map_url no admin_map (GET): {e}")
        map_url_atual = ""

    # (5) Passa EXATAMENTE as mesmas variáveis de /admin, mais map_url_atual
    return render_template(
        'admin.html',
        logged_in=logged_in,
        gallery_images=gallery_images,
        map_url_atual=map_url_atual
    )




    
if __name__ == '__main__':
    app.run(debug=True)
    
