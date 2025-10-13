# -*- coding: utf-8 -*-
#!/usr/bin/python3

# Disciplina: EPD899: Simulacao de Sistemas Logísticos
# Prof: Joao Flavio F. Almeida <joao.flavio@dep.ufmg>
# Problemas de Simulação - Resolução em Simpy (python)

# ##################################################################
# Implementação computacional dos 10 exemplos das aulas
# ##################################################################

# ##################################################################
# Em uma empresa de comércio eletrônico, os pedidos chegam ao setor de 
# vendas via correio eletrônico onde são analisados por um funcionário 
# que verifica se todos os itens constantes do pedido existem no estoque 
# da empresa. Caso falte algum item, o pedido é encaminhado ao
# departamento de produção, saindo do setor de vendas. Caso todos os 
# itens estejam disponíveis, o pedido é enviado para um outro funcionário, 
# que entra em contato com a administradora de cartões de crédito para 
# verificar se a compra pode ser debitada no cartão de crédito fornecido 
# pelo cliente. Caso exista algum problema com o cartão, o pedido é 
# recusado e o funcionário, antes de verificar o próximo pedido, redige e 
# envia uma mensagem para o cliente informando a recusa da administradora 
# do cartão. Se a administradora do cartão aceitar o débito, o pedido é 
# encaminhado ao almoxarifado, saindo do setor de vendas. Os pedidos chegam 
# a intervalos de 10 minutos, seguindo uma distribuição exponencial. 
# O tempo de verificação do estoque segue uma distribuição normal com 
# média de 8 minutos e desvio padrão de 0.75 minutos. O processo de 
# verificação do crédito segue uma distribuição triangular com mínimo 
# de 4, moda de 6 e máximo de 9 minutos. O tempo de redigir e enviar a 
# mensagem para o cliente, quando o pedido é recusado pela administradora 
# de cartões, segue uma distribuição normal com média de 3 minutos e 
# desvio padrão de 0,5 minutos. Sabe-se que historicamente, 20% dos 
# pedidos contém itens em falta e que 7% das transações com cartão são 
# recusadas pela administradora. Posto isto, construir o DCA
# representativo do sistema, informando todos os detalhes do processo.
# ##################################################################

# simulacao: https://simpy.readthedocs.io/en/latest/index.html
import simpy              
# numero aleatorio: https://docs.python.org/3/library/random.html
import random             
# biblioteca numérica do python: https://numpy.org/doc/stable/
import numpy as np        
# biblioteca numérica do python: https://scipy.org/
import scipy
# Impressao de graficos para periodo de Warm-up
import matplotlib
import matplotlib.pyplot as plt

from random import (expovariate, triangular, gauss, 
uniform, randint, random, seed)

from scipy import stats

# Fixando a semente do gerador de numero aleatorio 
# (p/controle de cenários)
seed(1) 

NS = []
NA = []
NF = []
TS = []
TA = []
TF = []
USO_F1=[]
USO_F2=[]

NS_bar = []
NF_bar = [] 
NA_bar = [] 
TS_bar = [] 
TF_bar = [] 
TA_bar = []
USO_F1_bar=[]
USO_F2_bar=[]

T = []  # Tempo dos Eventos Discretos

conta_chegada = 0
conta_saida = 0 
tempo_utilizacao_Recurso_Funcionario_1 = 0
tempo_utilizacao_Recurso_Funcionario_2 = 0

momento_chegada = {}
momento_saida = {}
tempo_sistema = {}
momento_entrada_fila = {}  
momento_saida_fila = {}
tempo_fila = {}
inicia_atendimento = {}
finaliza_atendimento = {}
duracao_atendimento = {}
utilizacao = {}

CAP_FUNCIONARIO_1 = 1
CAP_FUNCIONARIO_2 = 1

###################################################################
# Configura a rodada de simulacao definindo o 
# numero de replicações e duração da simulação
###################################################################
# # Teste
# n_replicacoes = 1 
# duracao_da_simulacao = 100
# tempo_aquecimento = 0
# imprime_detalhes = True 
###################################################################
# Simulação oficial
n_replicacoes = 5
duracao_da_simulacao =   365*24*60 
tempo_aquecimento = 30*24*60
imprime_detalhes = False 
###################################################################

# Unidade básica para todos os tempos: minutos

def distribuicao(tipo):
    taxa_chegada = 1/10 # por minuto
    return {
        'chegada': expovariate(taxa_chegada),       # minutos
        'verificar_estoque': max(0, gauss(8,0.75)), # minutos
        'verificar_credito': triangular(4,9,6),     # minutos                
        'enviar_mensagem': max(0, gauss(3,0.5))     # minutos        
    }.get(tipo,0.0)


def chegada_pedidos(env, entidade, funcionario_1, funcionario_2):
    global conta_chegada

    while True:        
        yield env.timeout(distribuicao('chegada'))
        conta_chegada+=1
        nome = entidade + " " + str(conta_chegada)        
        momento_chegada[nome] = env.now        
        if imprime_detalhes:
            print("{0:.2f}: {1:s} chega na empresa".format(env.now, nome))
        # chama o proximo "bloco"                
        env.process(verifica_estoque(env, nome, funcionario_1, funcionario_2))

def verifica_estoque(env, nome, funcionario_1, funcionario_2):
    momento_entrada_fila[nome] = env.now            
    # Seize, Delay, Release 
    request =funcionario_1.request()    
    # Seize
    yield request
    momento_saida_fila[nome] = env.now
    tempo_fila[nome] = momento_saida_fila[nome] - momento_entrada_fila[nome] 
    if env.now > tempo_aquecimento:
        TF.append(tempo_fila[nome])
    if imprime_detalhes:
        print("{0:.2f}: Funcionário 1 verifica se tem estoque para {1:s}. Entidades em atendimento: {2:d}"
        .format(env.now, nome, funcionario_1.count))
    
    inicia_atendimento[nome] = env.now
    inicia_utilizacao_Recurso = env.now
    # Delay           
    yield env.timeout(distribuicao('verificar_estoque'))
    if imprime_detalhes:
        print("{0:.2f}: Funcionário 1 termina verificação do {1:s}.  Entidades em fila: {2:d}"
        .format(env.now, nome, len(funcionario_1.queue)))
    
    finaliza_atendimento[nome] = env.now        
    duracao_atendimento[nome] = finaliza_atendimento[nome] - inicia_atendimento[nome]
    if env.now > tempo_aquecimento:
        TA.append(duracao_atendimento[nome])
    # Release
    yield funcionario_1.release(request)

    global tempo_utilizacao_Recurso_Funcionario_1
    tempo_utilizacao_Recurso_Funcionario_1 += env.now - inicia_utilizacao_Recurso
    utilizacao['Funcionario_1'] = tempo_utilizacao_Recurso_Funcionario_1 / (CAP_FUNCIONARIO_1*env.now)  

    tem_no_estoque=random()

    if tem_no_estoque <= 0.8:
        if imprime_detalhes:
            print("{0:.2f}: Todos os itens do {1:s} estão no estoque".format(env.now, nome))
        # chama o proximo "bloco"
        prio=1
        env.process(verifica_credito(env, nome, prio, funcionario_2))
    else:
        # chama o proximo "bloco"
        coleta_dados_indicadores(env, nome)

def verifica_credito(env, nome, prio, funcionario_2):
    momento_entrada_fila[nome] = env.now            
    # Seize, Delay (apenas!)
    request = funcionario_2.request(priority=prio)    
    # Seize
    yield request
    momento_saida_fila[nome] = env.now
    tempo_fila[nome] = momento_saida_fila[nome] - momento_entrada_fila[nome] 
    if env.now > tempo_aquecimento:
        TF.append(tempo_fila[nome])
    if imprime_detalhes:
        print("{0:.2f}: Funcionário 2 verifica se cliente tem crédito para {1:s}. Entidades em atendimento: {2:d}"
        .format(env.now, nome, funcionario_2.count))
    
    inicia_atendimento[nome] = env.now
    inicia_utilizacao_Recurso = env.now
    # Delay
    yield env.timeout(distribuicao('verificar_credito'))
    if imprime_detalhes:
        print("{0:.2f}: Funcionário 2 termina verificação de crédito para {1:s}.  Entidades em fila: {2:d}"
        .format(env.now, nome, len(funcionario_2.queue)))
    
    finaliza_atendimento[nome] = env.now        
    duracao_atendimento[nome] = finaliza_atendimento[nome] - inicia_atendimento[nome]
    if env.now > tempo_aquecimento:
        TA.append(duracao_atendimento[nome])

    credito_ok = random()    

    if credito_ok <= 0.93:
        # Release
        yield funcionario_2.release(request)

        global tempo_utilizacao_Recurso_Funcionario_2
        tempo_utilizacao_Recurso_Funcionario_2 += env.now - inicia_utilizacao_Recurso
        utilizacao['Funcionario_2'] = tempo_utilizacao_Recurso_Funcionario_2 / (CAP_FUNCIONARIO_2*env.now)
        
        # chama o proximo "bloco" 
        coleta_dados_indicadores(env, nome)
    else:        
        if imprime_detalhes:
            print("{0:.2f}: Cliente do {1:s} teve crétido negado.".format(env.now, nome))
        # chama o proximo "bloco"
        prio=0
        env.process(envia_mensagem(env, nome, request, prio, funcionario_2))       

def envia_mensagem(env, nome, request, prio, funcionario_2):   
    # Libera e troca e prioridade imediatamente
    yield funcionario_2.release(request)
    req = funcionario_2.request(priority=prio)
    yield req
    if imprime_detalhes:
        print("{0:.2f}: Funcionário 2 redige mensagem sobre o {1:s}. Entidades em atendimento: {2:d}"
        .format(env.now, nome, funcionario_2.count))
    
    inicia_atendimento[nome] = env.now
    inicia_utilizacao_Recurso = env.now
    # Delay
    yield env.timeout(distribuicao('enviar_mensagem'))
    if imprime_detalhes:
        print("{0:.2f}: Funcionário 2 finaliza o envio da mensagem sobre o {1:s}. Entidades em fila: {2:d}"
        .format(env.now, nome, len(funcionario_2.queue)))
    
    finaliza_atendimento[nome] = env.now        
    duracao_atendimento[nome] = finaliza_atendimento[nome] - inicia_atendimento[nome]
    if env.now > tempo_aquecimento:
        TA.append(duracao_atendimento[nome])
        
    # Release
    yield funcionario_2.release(req)

    global tempo_utilizacao_Recurso_Funcionario_2
    tempo_utilizacao_Recurso_Funcionario_2 += env.now - inicia_utilizacao_Recurso
    utilizacao['Funcionario_2'] = tempo_utilizacao_Recurso_Funcionario_2 / (CAP_FUNCIONARIO_2*env.now)  

    # chama o proximo "bloco"
    coleta_dados_indicadores(env, nome)


def coleta_dados_indicadores(env, nome):    
    # Entidade sai do sistema    
    global conta_saida
    conta_saida+=1    
    
    global funcionario_1
    global funcionario_2

    # Coleta dados para estatísticas        
    numero_sistema = conta_chegada - conta_saida

    if env.now > tempo_aquecimento:
        NS.append(numero_sistema)        
        NA.append(funcionario_1.count + funcionario_2.count)
        NF.append(len(funcionario_1.queue) + len(funcionario_2.queue))
    
    momento_saida[nome] = env.now            
    tempo_sistema[nome] = momento_saida[nome] - momento_chegada[nome]
    
    if env.now > tempo_aquecimento:
        TS.append(tempo_sistema[nome])        
        USO_F1.append(utilizacao['Funcionario_1']) 
        USO_F2.append(utilizacao['Funcionario_2'])
        T.append(env.now)


def computa_estatisticas(replicacao, tempo):  
    print()
    comprimento_linha = 100
    print("="*comprimento_linha)   
    print("Indicadores de Desempenho da Replicacao {0:d}".format(replicacao), end="\n")
    print("="*comprimento_linha)   
    
    entidade = "pedidos"

    NS_i = np.mean(NS)
    NF_i = np.mean(NF)
    NA_i = np.mean(NA)
    TS_i = np.mean(TS)
    TF_i = np.mean(TF)
    TA_i = np.mean(TA)
    USO_F1_i= np.mean(USO_F1) if len(USO_F1) > 0 else 0    
    USO_F2_i= np.mean(USO_F2) if len(USO_F2) > 0 else 0    
    
    print('Chegadas: {0:d} {1:s}'.format(conta_chegada, entidade))
    print('Saidas:   {0:d} {1:s}'.format(conta_saida, entidade))
    print('WIP:      {0:d} {1:s}'.format(conta_chegada-conta_saida, entidade))
    print('NS: {0:.2f} {1:s}'.format(NS_i, entidade))
    print('NF: {0:.2f} {1:s}'.format(NF_i, entidade))
    print('NA: {0:.2f} {1:s}'.format(NA_i, entidade))
    print('TS: {0:.2f} {1:s}'.format(TS_i, tempo))
    print('TF: {0:.2f} {1:s}'.format(TF_i, tempo))
    print('TA: {0:.2f} {1:s}'.format(TA_i, tempo))
    print('USO-F1:{0:.2f}%'.format(USO_F1_i*100))    
    print('USO-F2:{0:.2f}%'.format(USO_F2_i*100))    
    
    
    print("="*comprimento_linha, end="\n")   
    NS_bar.append(NS_i)
    NF_bar.append(NF_i)
    NA_bar.append(NA_i)
    TS_bar.append(TS_i)
    TF_bar.append(TF_i)
    TA_bar.append(TA_i)
    USO_F1_bar.append(USO_F1_i)
    USO_F2_bar.append(USO_F2_i)
    

def calc_ic(lista):
    if len(lista) <= 1:
        return 0
    else:
        confidence = 0.95
        n = len(lista)
        # mean_se: Erro Padrão da Média
        mean_se = stats.sem(lista)
        h = mean_se * stats.t.ppf((1 + confidence) / 2., n-1)
        # Intervalo de confiança: mean, +_h
        return h


def publica_estatisticas(tempo):  
    print()
    comprimento_linha = 100
    print("="*comprimento_linha)   
    print("Indicadores de Desempenho do Sistema", end="\n")
    print("="*comprimento_linha)   
    
    entidade = "pedidos"

    print('NS: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(NS_bar), calc_ic(NS), entidade))
    print('NF: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(NF_bar), calc_ic(NF), entidade))
    print('NA: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(NA_bar), calc_ic(NA), entidade))
    print('TS: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(TS_bar), calc_ic(TS), tempo))
    print('TF: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(TF_bar), calc_ic(TF), tempo))
    print('TA: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(TA_bar), calc_ic(TA), tempo))
    print('USO-F1:{0:.2f}% \u00B1 {1:.2f}%  (IC 95%)'.format(np.mean(USO_F1_bar)*100, calc_ic(USO_F1)*100))
    print('USO-F2:{0:.2f}% \u00B1 {1:.2f}%  (IC 95%)'.format(np.mean(USO_F2_bar)*100, calc_ic(USO_F2)*100))
    print("="*comprimento_linha, end="\n")
    gera_grafico()     


###################################################################
# Gera gráfico de Warm-up
###################################################################
def gera_grafico():
    if n_replicacoes == 1:
        matplotlib.rcParams['figure.figsize'] = (8.0, 6.0)
        matplotlib.style.use('ggplot')
        # Dados
        xi = T     
        y1 = USO_F1        
        y2 = USO_F2
        
        # usa a função plot
        plt.title('Indicador de Desempenho: \n\n' + \
        "Utilização média dos Recursos")
        plt.plot(xi, y1, marker='o', linestyle='-', color='red', label='Funcionário 1')        
        plt.plot(xi, y2, marker='o', linestyle='-', color='green', label='Funcionário 2')        
        plt.legend()
        plt.ylim(0.0,1.05)
        plt.xlim(0.0,duracao_da_simulacao)
        plt.xlabel('Tempo (minutos)')
        plt.ylabel('Valor') 
        plt.show()
###################################################################

###################################################################
for i in range (1,n_replicacoes+1):
    # Re-inicializacao das estatísticas entre replicações
    conta_chegada = 0     
    conta_saida = 0    
    tempo_utilizacao_Recurso_Funcionario_1 = 0
    tempo_utilizacao_Recurso_Funcionario_2 = 0

    env = simpy.Environment()
    funcionario_1 = simpy.Resource(env,capacity=CAP_FUNCIONARIO_1)
    funcionario_2 = simpy.PriorityResource(env,capacity=CAP_FUNCIONARIO_2)
    env.process(chegada_pedidos(env, "pedido", funcionario_1, funcionario_2))
    env.run(duracao_da_simulacao)
    computa_estatisticas(i, "minutos")        

publica_estatisticas("minutos")
###################################################################
