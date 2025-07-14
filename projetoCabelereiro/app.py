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
import uuid
import re
import json
import os
from urllib.parse import urlparse
from PIL import Image
import io
from flask import request, redirect, render_template_string
import uuid
import asyncio
from flask import Flask, request, render_template_string, redirect

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
    """Retorna um dict com todas as cores de tema, inclusive fontes."""
    now = time.time()
    
    # TTL padrão em segundos (você pode ajustar)
    TTL = theme_cache.get("ttl", 60)

    # Verifica se o cache deve ser renovado (não existe, expirou ou forçado)
    if (
        force_refresh
        or theme_cache.get("section_color") is None
        or now - theme_cache.get("timestamp", 0) > TTL
    ):
        try:
            resp = supabase.table('theme_config').select('*').limit(1).execute()
            data = resp.data
            if data and len(data) > 0:
                row = data[0]
                # Atualiza o cache com TODAS as cores/fonte JUNTAS
                theme_cache["section_color"] = row.get('background_color', '#ffffff')
                theme_cache["body_color"] = row.get('body_color', '#ffffff')
                theme_cache["body_font_color"] = row.get('body_font_color', '#000000')
                theme_cache["section_font_color"] = row.get('section_font_color', '#000000')
                theme_cache["background_font_color"] = row.get('background_font_color', '#000000')
            else:
                # Valores padrão caso tabela esteja vazia
                theme_cache["section_color"] = '#ffffff'
                theme_cache["body_color"] = '#ffffff'
                theme_cache["body_font_color"] = '#000000'
                theme_cache["section_font_color"] = '#000000'
                theme_cache["background_font_color"] = '#000000'
            
            # Atualiza o timestamp após atualizar o cache
            theme_cache["timestamp"] = now

        except Exception as e:
            print(f"Erro ao buscar cores: {e}")
            # Se cache vazio, inicializa com padrão para não quebrar
            if theme_cache.get("section_color") is None:
                theme_cache["section_color"] = '#ffffff'
                theme_cache["body_color"] = '#ffffff'
                theme_cache["body_font_color"] = '#000000'
                theme_cache["section_font_color"] = '#000000'
                theme_cache["background_font_color"] = '#000000'

    # Retorna as cores e fontes do cache (sem consultar DB novamente)
    return {
        'section': theme_cache.get("section_color", '#ffffff'),
        'body': theme_cache.get("body_color", '#ffffff'),
        'body_font': theme_cache.get("body_font_color", '#000000'),
        'section_font': theme_cache.get("section_font_color", '#000000'),
        'background_font': theme_cache.get("background_font_color", '#000000')
    }

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'mysecretkey')  # Recomendação: usar variável de ambiente

# Redirecionamento da raiz para /home
@app.route('/')
def redirect_to_home():
    return redirect(url_for('index'))

# Rota principal
@app.route('/home')
def index():
    # 1) Buscar cores do tema (com cache)
    tema = get_cached_theme()
    cor_principal = tema['section']                # cor da seção (features, footer, etc)
    cor_body = tema['body']                        # cor de fundo do body
    cor_body_font = tema['body_font']              # cor da fonte do body
    cor_section_font = tema['section_font']        # cor da fonte da seção
    cor_background_font = tema['background_font']  # cor da fonte do background
    
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

    # 4) Buscar visibilidade de seções (clients, gallery, localizacao, testimonials)
    try:
        response = supabase.table('hidden_sections').select('*').execute()
        rows = response.data or []

        section_visibility = {
            'clients': False,
            'gallery': 'full',
            'localizacao': False,
            'testimonials': False
        }

        for row in rows:
            sid = row.get('id')
            if sid == 'clients':
                section_visibility['clients'] = bool(row.get('hidden', False))
            elif sid == 'gallery':
                section_visibility['gallery'] = row.get('gallery_visibility') or 'full'
            elif sid == 'localizacao':
                section_visibility['localizacao'] = bool(row.get('hidden', False))
            elif sid == 'testimonials':
                section_visibility['testimonials'] = bool(row.get('hidden', False))

        print("DEBUG section_visibility:", section_visibility)
    except Exception as e:
        print(f"Erro ao buscar visibilidade: {e}")
        section_visibility = {
            'clients': False,
            'gallery': 'full',
            'localizacao': False,
            'testimonials': False
        }

    # 5) Buscar o map_url na tabela settingsmap
    try:
        resp_map = supabase.table('settingsmap').select('map_url').eq('id', 1).execute()
        data_map = resp_map.data
        map_url = data_map[0]['map_url'] if data_map and len(data_map) > 0 else ""
    except Exception as e:
        print(f"Erro ao buscar map_url: {e}")
        map_url = ""

    # 6) Buscar funcionários e serviços (funcionarios_servicos)
    try:
        response = supabase.table('funcionarios_servicos').select('*').limit(6).execute()
        funcionarios = response.data or []
    except Exception as e:
        print(f"Erro ao buscar funcionários: {e}")
        funcionarios = []

    # 7) Buscar lista de serviços para montar lookup
    try:
        resp_servicos = supabase.table('servicos').select('id, nome').execute()
        servicos = resp_servicos.data or []
        servicos_lookup = {s['id']: s['nome'] for s in servicos}
    except Exception as e:
        print(f"Erro ao buscar serviços: {e}")
        servicos_lookup = {}
        
    # 8) Buscar logo ativa
    try:
        resp_logo = supabase.table('logos').select('*').eq('is_active', True).limit(1).execute()
        logo_data = resp_logo.data[0] if resp_logo.data else {
            "logo_url": "/static/img/logo.png",
            "height_px": 120
        }
    except Exception as e:
        print(f"Erro ao buscar logo: {e}")
        logo_data = {
            "logo_url": "/static/img/logo.png",
            "height_px": 120
        }

    # 9) Buscar logo ativa
    try:
        resp_video = supabase.table('videos').select('video_url').eq('id', 1).limit(1).execute()
        video_data = resp_video.data[0] if resp_video.data else None
        video_url = video_data['video_url'] if video_data else url_for('static', filename='img/video.mp4')
    except Exception as e:
        print(f"Erro ao buscar vídeo: {e}")
        video_url = url_for('static', filename='img/video.mp4')
        
    # 10) Buscar dados do footer (telefone e endereço formatado)
    try:
        resp_footer = supabase.table('contato_footer').select('telefone, endereco').eq('id', 1).limit(1).execute()
        footer_data = resp_footer.data[0] if resp_footer.data else {
            "telefone": "(45) 3254-4200",
            "endereco": "Rua Santa Catarina, N° 577 - Centro, Cidade: Marechal Cândido Rondon PR"
        }
    except Exception as e:
        print(f"Erro ao buscar contato_footer: {e}")
        footer_data = {
            "telefone": "(45) 3254-4200",
            "endereco": "Rua Santa Catarina, N° 577 - Centro, Cidade: Marechal Cândido Rondon PR"
        }
        
    # 11) Buscar no banco a URL da imagem do showcase
    data = supabase.table("site_config").select("showcase_image_url").limit(1).execute()
    img_url = None
    if data.data and len(data.data) > 0:
        img_url = data.data[0].get("showcase_image_url")

    # 12) Renderizar template passando todas as variáveis, incluindo cores das fontes
    return render_template(
        'index.html',
        cor_principal=cor_principal,
        cor_body=cor_body,
        cor_body_font=cor_body_font,
        cor_section_font=cor_section_font,
        cor_background_font=cor_background_font,
        gallery_images=gallery_images,
        social_links=social_links,
        section_visibility=section_visibility,
        map_url=map_url,
        localizacao_hidden=section_visibility.get('localizacao', False),
        funcionarios=funcionarios,
        servicos_lookup=servicos_lookup,
        logo=logo_data,
        video_url=video_url,
        footer_data=footer_data,
        showcase_url=img_url
    )

@app.route('/admin')
def admin():
    print("Session data:", session)
    logged_in = 'user_id' in session
    
    1# Buscar imagens da galeria
    try:
        response = supabase.table('gallery_images').select('*').execute()
        data = response.data if response.data else []
        gallery_images = {img['image_id']: img['image_url'] for img in data}
    except Exception as e:
        print(f"Erro ao buscar imagens: {str(e)}")
        gallery_images = {}
        
    2# Buscar vídeo atual
    try:
        video_data = supabase.table("videos").select("*").eq("id", 1).execute()
        video_url = video_data.data[0]["video_url"] if video_data.data else None
    except Exception as e:
        print(f"Erro ao buscar vídeo: {str(e)}")
        video_url = None

    3# Buscar background image
    result = supabase.table("site_config").select("showcase_image_url").limit(1).execute()
    showcase_url = None
    if result.data and len(result.data) > 0:
        showcase_url = result.data[0]["showcase_image_url"]
        
    return render_template(
        'admin.html',
        logged_in=logged_in,
        gallery_images=gallery_images,
        video_url=video_url,
        showcase_url=showcase_url
    )

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

@app.route("/upload-logo", methods=["POST"])
def upload_logo():
    file = request.files.get("logo")
    height = request.form.get("height")

    if not file or not height:
        return jsonify({"success": False, "error": "Arquivo ou altura ausente"})

    try:
        # 🚫 VERIFICA SE JÁ EXISTEM 4 LOGOS
        existing_logos = supabase.table("logos").select("id").execute()
        if len(existing_logos.data) >= 4:
            return jsonify({"success": False, "error": "Limite de 4 logos atingido. Exclua uma antes de adicionar outra."})

        # CONTINUA O PROCESSO NORMAL
        filename = secure_filename(file.filename)
        extension = os.path.splitext(filename)[1]
        unique_name = f"logo-{uuid.uuid4()}{extension}"
        file_data = file.read()

        # 🧠 Detectar se a imagem é clara
        is_clara = cor_dominante_e_clara(file_data)
        bg_contraste = "black" if is_clara else "white"

        # Upload no Supabase
        try:
            supabase.storage.from_('logos').upload(unique_name, file_data, {
                "content-type": file.mimetype
            })
        except Exception as e:
            return jsonify({"success": False, "error": f"Erro no upload: {str(e)}"})

        public_url = supabase.storage.from_('logos').get_public_url(unique_name)

        insert = supabase.table("logos").insert({
            "nome": filename,
            "logo_url": public_url,
            "height_px": int(height),
            "is_active": False,
            "bg_contraste": bg_contraste
        }).execute()

        if not insert.data:
            return jsonify({"success": False, "error": "Erro ao salvar no banco: retorno vazio"})

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
    
@app.route('/api/listar-logos', methods=['GET'])
def listar_logos():
    try:
        logos_resp = supabase.table('logos').select("*").order("id", desc=False).execute()
        logos = logos_resp.data if logos_resp.data else []
        return jsonify({"success": True, "logos": logos})
    except Exception as e:
        print("Erro ao listar logos:", e)
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/ativar-logo', methods=['POST'])
def ativar_logo():
    data = request.get_json()
    logo_id = data.get("id")
    if not logo_id:
        return jsonify({"error": "ID da logo não fornecido"}), 400

    try:
        resp1 = supabase.table('logos').update({"is_active": False}).eq("is_active", True).execute()
        if not resp1.data:
            print("Nenhuma logo estava ativa antes, tudo bem")

        resp2 = supabase.table('logos').update({"is_active": True}).eq("id", logo_id).execute()
        if not resp2.data:
            return jsonify({"error": "Logo não encontrada para ativar"}), 400

        return jsonify({"success": True})
    except Exception as e:
        print("Erro ao ativar logo:", e)
        return jsonify({"error": "Erro interno"}), 500

@app.route("/api/deletar-logo", methods=["POST"])
def deletar_logo():
    data = request.get_json()
    logo_id = data.get("id")
    logo_url = data.get("logo_url")

    if not logo_id or not logo_url:
        return jsonify({"success": False, "error": "ID ou URL da logo ausente"})

    try:
        # Extrai caminho da URL completa
        path = urlparse(logo_url).path  # exemplo: /storage/v1/object/public/logos//logo-xxxx.png
        file_path = path.split("/storage/v1/object/public/logos/")[-1]  # retorna logo-xxxx.png

        print("Tentando remover arquivo do bucket:", file_path)

        # Remove da storage
        response = supabase.storage.from_('logos').remove([file_path])
        print("Resposta da remoção:", response)

        if isinstance(response, list):
            print("Logo removida da storage com sucesso.")
        elif isinstance(response, dict) and response.get('error'):
            return jsonify({"success": False, "error": f"Erro na remoção: {response['error']}"})
        else:
            print("Resposta inesperada:", response)

        # Remove do banco
        supabase.table("logos").delete().eq("id", logo_id).execute()

        return jsonify({"success": True})

    except Exception as e:
        print("Erro ao deletar logo:", e)
        return jsonify({"success": False, "error": str(e)})

# Função para definir fundo da logo/imagem na admin de acordo com a cor dela
def cor_dominante_e_clara(image_bytes):
    with Image.open(io.BytesIO(image_bytes)) as img:
        img = img.convert('RGBA')  # mantém canal alfa
        img = img.resize((100, 100))
        pixels = list(img.getdata())

        r_total = g_total = b_total = count = 0

        for r, g, b, a in pixels:
            if a > 10:  # ignora pixels quase totalmente transparentes
                r_total += r
                g_total += g
                b_total += b
                count += 1

        if count == 0:
            return False  # Se todos os pixels forem transparentes, assume imagem escura (ou mude para True)

        avg_r = r_total / count
        avg_g = g_total / count
        avg_b = b_total / count

        luminancia = 0.2126 * avg_r + 0.7152 * avg_g + 0.0722 * avg_b

        return luminancia > 160  # Limiar ajustável

# Rota GET unificada
@app.route('/api/theme', methods=['GET'])
def get_theme():
    try:
        t = get_cached_theme()
        return jsonify({
            'section_color':          t['section'],
            'body_color':             t['body'],
            'body_font_color':        t.get('body_font', '#000000'),
            'section_font_color':     t.get('section_font', '#000000'),
            'background_font_color':  t.get('background_font', '#000000')
        })
    except Exception:
        return jsonify({
            'section_color': '#ffffff',
            'body_color':    '#ffffff',
            'body_font_color': '#000000',
            'section_font_color': '#000000',
            'background_font_color': '#000000'
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
        return jsonify({'message': 'Seção atualizada com sucesso!'})
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
        return jsonify({'message': 'Body atualizado com sucesso!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/theme/body-font', methods=['POST'])
def update_body_font_color():
    try:
        new_color = request.json.get('color')
        current = get_cached_theme()
        supabase.table('theme_config').delete().neq('id', 0).execute()
        supabase.table('theme_config').insert({
            'background_color': current['section'],
            'body_color':       current['body'],
            'body_font_color':  new_color,
            'section_font_color': current.get('section_font', '#000000')
        }).execute()
        theme_cache["body_font_color"] = new_color
        return jsonify({'message': 'Fonte do body atualizada com sucesso!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/theme/section-font', methods=['POST'])
def update_section_font_color():
    try:
        new_color = request.json.get('color')
        current = get_cached_theme()
        supabase.table('theme_config').delete().neq('id', 0).execute()
        supabase.table('theme_config').insert({
            'background_color':      current['section'],
            'body_color':            current['body'],
            'body_font_color':       current.get('body_font', '#000000'),
            'section_font_color':    new_color,
            'background_font_color': current.get('background_font', '#000000'),
        }).execute()
        theme_cache["section_font_color"] = new_color
        return jsonify({'message': 'Fonte da seção atualizada com sucesso!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/theme/background-font', methods=['POST'])
def update_background_font_color():
    try:
        new_color = request.json.get('color')
        current = get_cached_theme()
        supabase.table('theme_config').delete().neq('id', 0).execute()
        supabase.table('theme_config').insert({
            'background_color':      current['section'],
            'body_color':            current['body'],
            'body_font_color':       current.get('body_font', '#000000'),
            'section_font_color':    current.get('section_font', '#000000'),
            'background_font_color': new_color,
        }).execute()
        theme_cache["background_font_color"] = new_color
        return jsonify({'message': 'Fonte do background atualizada com sucesso!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/upload-showcase-image", methods=["POST"])
def upload_showcase_image():
    BUCKET_NAME = "backgroundimage"  # aqui o nome correto da bucket

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    file = request.files.get("background-file")
    if not file:
        return jsonify({"success": False, "error": "Nenhum arquivo enviado"}), 400

    existing = supabase.table("site_config").select("showcase_image_url", "id").limit(1).execute()

    if existing.data and len(existing.data) > 0:
        old_url = existing.data[0].get("showcase_image_url", "")
        record_id = existing.data[0].get("id")

        if old_url:
            try:
                old_filename = old_url.split(f"/{BUCKET_NAME}/")[1]
                supabase.storage.from_(BUCKET_NAME).remove([old_filename])
            except Exception as e:
                print("Erro ao deletar arquivo antigo:", e)
    else:
        record_id = None

    filename = f"showcase-{uuid.uuid4()}.png"

    try:
        file_bytes = file.read()
        supabase.storage.from_(BUCKET_NAME).upload(filename, file_bytes, {"content-type": file.content_type})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    public_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{filename}"

    if record_id:
        supabase.table("site_config").update({"showcase_image_url": public_url}).eq("id", record_id).execute()
    else:
        supabase.table("site_config").insert({"showcase_image_url": public_url}).execute()

    return jsonify({"success": True, "url": public_url})

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
                    if section_id == 'clients':
                        vis['clients'] = bool(row.get('hidden', False))
                    elif section_id == 'gallery':
                        vis['gallery'] = row.get('gallery_visibility') or 'full'
                    elif section_id == 'localizacao':
                        vis['localizacao'] = bool(row.get('hidden', False))
                    elif section_id == 'testimonials':
                        vis['testimonials'] = bool(row.get('hidden', False))

                if 'clients' not in vis:
                    vis['clients'] = False
                if 'gallery' not in vis:
                    vis['gallery'] = 'full'
                if 'localizacao' not in vis:
                    vis['localizacao'] = False
                if 'testimonials' not in vis:
                    vis['testimonials'] = False

            else:
                # Se a tabela estiver vazia, assume clientes visível e galeria em 'full'
                vis = {
                    'clients': False,
                    'gallery': 'full',
                    'localizacao': False,
                    'testimonials': False
                }
                
            return jsonify(vis)
        except Exception as e:
            print(f"Erro ao buscar visibilidade: {e}")
            return jsonify({}), 500

    # atualiza *clients* e/ou *gallery* JSON de entrada pode ter: { "clients": <true|false> } e/ou { "gallery": "<none|partial|full>" }
    
    elif request.method == 'POST':
        try:
            data = request.get_json() or {}
            # No mínimo deve haver a chave 'clients', 'gallery' ou 'localizacao' no JSON
            if not any(key in data for key in ('clients', 'gallery', 'localizacao', 'testimonials')):
                return jsonify({'error': "Envie 'clients', 'gallery', 'localizacao' ou 'testimonials' no corpo."}), 400

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

            # 2.3) Se vier valor para localizacao, faz upsert em hidden
            if 'localizacao' in data:
                valor_loc = data['localizacao']
                try:
                    ocultar = bool(valor_loc)
                except:
                    return jsonify({'error': "Valor inválido para 'localizacao' (deve ser true/false)."}), 400

                supabase.table('hidden_sections').upsert({
                    'id': 'localizacao',
                    'hidden': ocultar,
                    'updated_at': datetime.now().isoformat()
                }, on_conflict='id').execute()
            
            if 'testimonials' in data:
                valor_test = data['testimonials']
                try:
                    ocultar = bool(valor_test)
                except:
                    return jsonify({'error': "Valor inválido para 'testimonials' (deve ser true/false)."}), 400

                supabase.table('hidden_sections').upsert({
                    'id': 'testimonials',
                    'hidden': ocultar,
                    'updated_at': datetime.now().isoformat()
                }, on_conflict='id').execute()

            return jsonify({'message': 'Visibilidade atualizada!'})
        except Exception as e:
            print(f"Erro ao atualizar visibilidade: {e}")
            return jsonify({'error': str(e)}), 500
        
# --- ROTA PRINCIPAL: /admin/map para exibir e salvar o Google Maps --- #
@app.route('/admin/map', methods=['GET', 'POST'])
def admin_map():
    # (1) Verifica se está logado
    logged_in = 'user_id' in session

    # (2) Se for POST, atualiza o map_url
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
        return redirect(url_for('admin_map'))

    # (3) Busca imagens da galeria
    try:
        response = supabase.table('gallery_images').select('*').execute()
        data = response.data or []
        gallery_images = {img['image_id']: img['image_url'] for img in data}
    except Exception as e:
        print(f"Erro ao buscar imagens no admin_map: {e}")
        gallery_images = {}

    # (4) Busca o map_url atual
    try:
        resp_map = supabase.table("settingsmap") \
            .select("map_url") \
            .eq("id", 1) \
            .execute()
        data_map = resp_map.data
        print("DEBUG: data_map retornado pelo Supabase:", data_map)
        map_url_atual = data_map[0]["map_url"] if data_map and len(data_map) > 0 else ""
    except Exception as e:
        print(f"Erro ao buscar map_url no admin_map (GET): {e}")
        map_url_atual = ""

    # (5) Renderiza o admin.html com as variáveis necessárias
    return render_template(
        'admin.html',
        logged_in=logged_in,
        gallery_images=gallery_images,
        map_url_atual=map_url_atual  # opcional agora, pois o JS faz a busca
    )

# --- NOVA ROTA AUXILIAR: /api/map-url para JS buscar o valor atual --- #
@app.route("/api/map-url", methods=["GET"])
def api_map_url():
    try:
        result = supabase.table("settingsmap") \
            .select("map_url") \
            .eq("id", 1) \
            .execute()

        data = result.data
        if data and len(data) > 0:
            return jsonify({"map_url": data[0]["map_url"]})
        else:
            return jsonify({"map_url": ""})
    except Exception as e:
        print("Erro ao buscar map_url:", e)
        return jsonify({"map_url": ""}), 500



# GERENCIAMENTO NOSSOS SERVIÇOS
# ROTA DE ADD (ajustada)
@app.route('/admin/add-funcionario', methods=['POST'])
def add_funcionario():
    try:
        # 1. Verifica quantidade atual de funcionários
        response = supabase \
            .table('funcionarios_servicos') \
            .select('id') \
            .execute()

        if response.data and len(response.data) >= 6:
            return jsonify({
                'success': False,
                'error': 'Limite de 6 funcionários atingido. Remova um antes de adicionar outro.'
            }), 400

        # 2. Continua com a lógica atual
        nome = request.form.get('nome', '').strip()

        servicos_json = request.form.get('servicos', '[]')
        servicos = json.loads(servicos_json)

        if len(servicos) > 8:
            return jsonify({
                'success': False,
                'error': 'Limite de 8 serviços por funcionário excedido.'
            }), 400

        foto = request.files.get('foto')
        foto_url = None
        if foto and foto.filename:
            bucket = 'funcionarios'
            ext = foto.filename.rsplit('.', 1)[-1]
            key = f"{uuid.uuid4()}.{ext}"

            file_bytes = foto.read()
            supabase.storage.from_(bucket).upload(key, file_bytes, {
                "content-type": foto.content_type
            })

            foto_url = supabase.storage.from_(bucket).get_public_url(key)

        payload = {
            'nome': nome or None,
            'servicos': servicos,
            'foto_url': foto_url
        }

        supabase.table('funcionarios_servicos').insert(payload).execute()
        return jsonify({'success': True}), 200

    except Exception as e:
        print("Erro ao adicionar funcionário:", e)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/listar-funcionarios', methods=['GET'])
def listar_funcionarios():
    try:
        response = supabase \
            .table('funcionarios_servicos') \
            .select('*') \
            .order('created_at', desc=True) \
            .limit(6) \
            .execute()

        # response.data já é uma lista de dicts
        return jsonify(response.data), 200
    except Exception as e:
        print("Erro ao listar funcionários:", e)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/remover-funcionario/<int:funcionario_id>', methods=['DELETE'])
def remover_funcionario(funcionario_id):
    try:
        bucket = 'funcionarios'

        # 1) Buscar foto_url
        resp = supabase \
            .table('funcionarios_servicos') \
            .select('foto_url') \
            .eq('id', funcionario_id) \
            .single() \
            .execute()

        data = resp.data
        if not data:
            return jsonify({'success': False, 'error': 'Funcionário não encontrado'}), 404

        foto_url = data.get('foto_url')

        # 2) Se houver foto, remove do Storage
        if foto_url:
            prefix = f"https://{SUPABASE_URL.split('//')[1]}/storage/v1/object/public/{bucket}/"
            if foto_url.startswith(prefix):
                key = foto_url[len(prefix):].split('?')[0]  # ← aqui corrigido
                print(f"[INFO] Removendo do Storage: {key}")
                remove_response = supabase.storage.from_(bucket).remove([key])
                if hasattr(remove_response, 'error') and remove_response.error:
                    print("[ERRO] Falha ao remover imagem do Storage:", remove_response.error)
                else:
                    print("[OK] Imagem removida do Storage com sucesso.")
            else:
                print("[ERRO] Não foi possível extrair a chave da imagem:", foto_url)


        # 3) Remove do banco
        supabase \
            .table('funcionarios_servicos') \
            .delete() \
            .eq('id', funcionario_id) \
            .execute()

        return jsonify({'success': True}), 200

    except Exception as e:
        print("Erro ao remover funcionário:", e)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/listar-servicos', methods=['GET'])
def listar_servicos():
    try:
        response = supabase.table('servicos').select('*').order('nome').execute()
        return jsonify(response.data), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/upload_video', methods=['POST'])
def upload_video():
    file = request.files.get("video")
    if not file:
        return jsonify({"success": False, "error": "Nenhum arquivo recebido."})

    try:
        # Novo nome de arquivo
        filename = f"video-{uuid.uuid4()}.mp4"
        file_data = file.read()

        # Verifica vídeo antigo
        existing = supabase.table("videos").select("*").eq("id", 1).execute()
        if existing.data:
            old_url = existing.data[0].get("video_url")
            if old_url:
                # Extrai o nome do arquivo da URL pública
                old_filename = old_url.split("/")[-1].split("?")[0]

                # Remove vídeo anterior do bucket
                try:
                    supabase.storage.from_("videos").remove([old_filename])
                except Exception as e:
                    print("Erro ao remover vídeo antigo:", e)

        # Upload novo vídeo
        supabase.storage.from_("videos").upload(filename, file_data, {
            "content-type": file.mimetype
        })

        # Nova URL pública
        public_url = supabase.storage.from_("videos").get_public_url(filename)

        # Atualiza/inserir no banco
        if existing.data:
            supabase.table("videos").update({
                "video_url": public_url,
                "is_active": True
            }).eq("id", 1).execute()
        else:
            supabase.table("videos").insert({
                "id": 1,
                "video_url": public_url,
                "is_active": True
            }).execute()

        return jsonify({"success": True, "video_url": public_url})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
    
@app.route('/salvar-contato', methods=['POST'])
def salvar_contato():
    data = request.get_json()
    telefone = data.get('telefone')
    endereco = data.get('endereco')

    if not telefone or not endereco:
        return jsonify({'error': 'Dados incompletos'}), 400

    try:
        supabase.table('contato_footer').upsert({
            "id": 1,
            "telefone": telefone,
            "endereco": endereco
        }).execute()

        return jsonify({'message': 'Contato atualizado com sucesso'}), 200
    except Exception as e:
        print(f"Erro ao salvar contato_footer: {e}")
        return jsonify({'error': str(e)}), 500
    
import re

@app.route('/get-contato', methods=['GET'])
def get_contato():
    try:
        resp = supabase.table('contato_footer').select('telefone, endereco').eq('id', 1).limit(1).execute()
        data = resp.data[0] if resp.data else None

        if not data:
            return jsonify({}), 200

        telefone = data['telefone'].strip()
        endereco = data['endereco'].strip()

        # Tenta extrair usando expressão regular
        match = re.match(r'^(.*?),\s*N[°º]?\s*(.*?)\s*-\s*(.*?),\s*Cidade:\s*(.*)$', endereco)
        if match:
            rua = match.group(1)
            numero = match.group(2)
            bairro = match.group(3)
            cidade = match.group(4)
        else:
            print("⚠️ Endereço mal formatado:", endereco)
            rua = numero = bairro = ''
            cidade = endereco  # joga tudo na cidade se não reconhecer

        return jsonify({
            "rua": rua.strip(),
            "numero": numero.strip(),
            "bairro": bairro.strip(),
            "cidade": cidade.strip(),
            "telefone": telefone
        }), 200

    except Exception as e:
        print("❌ Erro em /get-contato:", e)
        return jsonify({}), 500
    



if __name__ == '__main__':
    app.run(debug=True)
    
