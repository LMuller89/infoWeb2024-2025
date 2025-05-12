from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client, Client
import os
from functools import lru_cache
import time

# Cache com expiração
# Cache simples sem LRU_CACHE

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

# Configuração do Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://vuvuiddlnpppzsyrhmff.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ1dnVpZGRsbnBwcHpzeXJobWZmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDU4Njg0ODYsImV4cCI6MjA2MTQ0NDQ4Nn0.RK9P2X3vdw9yjoEYT_xbHbr7VzbxKEv7bRSYYaqFsdU')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Redirecionamento da raiz para /home
@app.route('/')
def redirect_to_home():
    return redirect(url_for('index'))

# Rota principal
@app.route('/home')
def index():
    cor_principal = get_cached_theme_color()
    return render_template('index.html', cor_principal=cor_principal)

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

from flask import jsonify

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

# Admin protegida
@app.route('/admin')
def admin():
    logged_in = 'user_id' in session
    return render_template('admin.html', logged_in=logged_in)

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)
    
