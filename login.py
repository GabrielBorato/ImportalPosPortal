from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import requests
from datetime import datetime, timedelta, time 
from bot import start_robo
import queue
import threading

# Configs e certificados
app = Flask(__name__)
app.secret_key = 'flavinhodopneu'
base_url = 'https://rpafinpos.superkoch.com.br'


operacao_em_andamento = False
ultima_operacao = None


fila_datas = queue.Queue()

horario_inicio = time(8, 20)  
horario_fim = time(9, 10)

horario_inicio2 = time(12, 00) 
horario_fim2 = time(13, 10)

##############################################################################
# Função para autenticar o usuário
def authenticate_user(username, password):
    auth_url = "https://autenticacao.superkoch.com.br/login"
    data = {
        "username": username,
        "password": password
    }
    response = requests.post(auth_url, json=data)

    if response.status_code == 200:
        user_data = response.json()
        user_group = user_data.get('GRUPO')
        if user_group == 'agpaineladm' or user_group == 'financeiro':
            return True
        else:
            flash('Você não tem permissão para acessar este recurso.', 'error')
            return False
    elif response.status_code == 401:
        flash('Usuário ou senha incorretos. Tente novamente.', 'error')
        return False
    else:
        flash('Erro de autenticação. Tente novamente mais tarde.', 'error')
        return False

# Rota para renderizar a página inicial de login
@app.route('/')
def index():
    return render_template('login.html')

# Rota para processar o formulário de login
@app.route('/login', methods=['POST'])
def login_post():
    username = request.form['username']
    password = request.form['password']
    
    if authenticate_user(username, password):
        return redirect(url_for('start_index'))  # Redirecionar para a página inicial do robô após autenticação
    else:
        return redirect(url_for('index'))  # Redirecionar de volta para a página de login em caso de falha na autenticação

# Rota para a página inicial do robô
@app.route('/start')
def start_index():
    return render_template('portal.html')
#####################################################################################################
def start_robo_async(data_recebida):
    global operacao_em_andamento, ultima_operacao
    
    # Marcar operação como em andamento
    operacao_em_andamento = True
    
    # Chamar a função de operação do robô
    start_robo(data_recebida)
    
    # Atualizar a última operação concluída
    ultima_operacao = datetime.now()
    
    # Marcar operação como concluída
    operacao_em_andamento = False

def gerenciar_operacoes():
    global operacao_em_andamento, ultima_operacao
    
    while True:
        # Verificar se há operações em andamento ou se a fila está vazia
        if not operacao_em_andamento and not fila_datas.empty():
            
            # Obter a data recebida da fila
            data_recebida = fila_datas.get()
            
            # Verificar se a última operação foi concluída há pelo menos 30 minutos
            if ultima_operacao:
                tempo_passado = datetime.now() - ultima_operacao
                if tempo_passado < timedelta(minutes=30):
                    # Se ainda não passou 30 minutos, devolve a data para a fila e espera
                    fila_datas.put(data_recebida)
                    continue
            
            # Iniciar uma nova thread para processar a operação
            threading.Thread(target=start_robo_async, args=(data_recebida,)).start()

@app.route('/operar-robo', methods=['POST'])
def operar_robo():
    # Verificação se o robô pode operar com base nos horários de restrição
    horario_atual = datetime.now().time()
    if (horario_inicio <= horario_atual <= horario_fim) or (horario_inicio2 <= horario_atual <= horario_fim2):
        return render_template('portal.html', error="O robô não pode operar no momento. Por favor, tente mais tarde.")
    data_recebida = request.form.get('data_recebida')  
    
    if not data_recebida:
        return render_template('portal.html', error="Por favor, insira uma data de operação.")
    
    try:
        data_recebida = datetime.strptime(data_recebida, "%Y-%m-%d")
    except ValueError:
        return render_template('portal.html', error="Formato de data inválido.")
    
    if data_recebida > datetime.now():
        return render_template('portal.html', error="Por favor, insira uma data válida no passado. Não é possível operar com datas futuras.")
    
    # Adicionar a data recebida à fila
    fila_datas.put(data_recebida)
    
    # Iniciar a função de gerenciamento de operações
    threading.Thread(target=gerenciar_operacoes).start()
    
    return render_template('portal.html', success="Processamento iniciado com sucesso. Fila de operações em andamento.")

if __name__ == '__main__':
    app.run(debug=True, host='172.19.20.35', port=5050)