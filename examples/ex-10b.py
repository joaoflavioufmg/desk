# -*- coding: utf-8 -*-
#!/usr/bin/python3

# Disciplina: EPD899: Simulacao de Sistemas Logísticos
# Prof: Joao Flavio F. Almeida <joao.flavio@dep.ufmg>
# Problemas de Simulação - Resolução em Simpy (python)

# ##################################################################
# Implementação computacional dos 10 exemplos das aulas
# ##################################################################

# ##################################################################
# (somente máquinas internas) Uma empresa possui uma oficina de 
# manutenção de 5 máquinas que são utilizadas para operação dentro de 
# sua área industrial. Dentro da oficina existem duas estações de reparo, 
# estação A e B. Em cada uma destas estações, existe apenas 1 operador 
# disponível para execução dos trabalhos. A probabilidade de uma 
# máquina necessitar de reparos na estação A é de 75% e na estação B de 
# 25%. Uma máquina, após reparada vai para uma inspeção final, onde 
# existe um único operador que realiza o trabalho. Após a inspeção, 
# 90% das máquinas são liberadas para operação e 10% retornam para 
# nova manutenção. Esta nova manutenção sempre ocorre na mesma estação 
# onde a máquina foi reparada inicialmente.

# (parte com máquinas externas) Além da manutenção das máquinas da 
# empresa, esta oficina também está estudando a possibilidade de realizar 
# serviços para terceiros, isto é, manutenção em máquinas de outras empresas. 
# As máquinas externas sempre seriam reparadas na estação B e, após o 
# reparo, também seriam inspecionadas pelo mesmo operador que inspeciona 
# as máquinas internas e seriam liberadas (neste caso a taxa é de 82% 
# dos casos) ou retidas para nova manutenção (18% dos casos). A nova
# manutenção, neste caso, sempre aconteceria na estação B. 
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
uniform, gammavariate, weibullvariate, randint, random, seed)

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
USO_A=[]
USO_B=[]
USO_I=[]

NS_bar = []
NF_bar = [] 
NA_bar = [] 
TS_bar = [] 
TF_bar = [] 
TA_bar = []
USO_A_bar=[]
USO_B_bar=[]
USO_I_bar=[]

T = []  # Tempo dos Eventos Discretos

conta_chegada = 0
conta_chegada_maq_externa = 0
conta_saida = 0 
conta_saida_maq_externa = 0    

tempo_utilizacao_Recurso_Operador_A = 0
tempo_utilizacao_Recurso_Operador_B = 0
tempo_utilizacao_Recurso_Operador_C = 0

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

utilizacao['Estacao_A'] = 0
utilizacao['Estacao_B'] = 0
utilizacao['Inspecao'] = 0

CAP_OPERADOR_A = 1
CAP_OPERADOR_B = 1
CAP_OPERADOR_C = 1

###################################################################
# Configura a rodada de simulacao definindo o 
# numero de replicações e duração da simulação
###################################################################
# # Teste
# n_replicacoes = 1 
# duracao_da_simulacao = 100000
# tempo_aquecimento = 0
# imprime_detalhes = True 
###################################################################
# Simulação oficial
n_replicacoes = 5
duracao_da_simulacao =  365*24*60
tempo_aquecimento = 30*24*60
imprime_detalhes = False 
###################################################################

# Unidade básica para todos os tempos: minutos

def distribuicao(tipo):    
    taxa_mnt_a = 1/88.98 # por minuto
    return {
        'chegada': gammavariate(0.96, 7.97)*60,         # minutos        
        'operacao': gammavariate(0.97, 10.36)*60,       # minutos        
        'mnt_a': expovariate(taxa_mnt_a),               # minutos
        'mnt_b': gammavariate(1.03,60.48),              # minutos
        'inspecao':  weibullvariate(31.05, 1.03)        # minutos 
    }.get(tipo,0.0)


def chegada_maq_externas(env, entidade, operador_A, operador_B, operador_C):
    global conta_chegada_maq_externa
    while True:        
        yield env.timeout(distribuicao('chegada'))
        conta_chegada_maq_externa += 1
        nome = entidade + " " + str(conta_chegada_maq_externa)        
        momento_chegada[nome] = env.now        
        if imprime_detalhes:
            print("{0:.2f}: {1:s} chega na oficina de manutenção".format(env.now, nome))
        
        # chama o proximo "bloco"          
        estacao='B' 
        tipo='externa'       
        env.process(manutencao_B(env, nome, tipo, estacao, operador_A, operador_B, operador_C))


def chegada_maq_internas(env, entidade, operador_A, operador_B, operador_C):
    global conta_chegada
    # Gera as 5 máquinas internas    
    for conta_chegada in range(1,6):
        yield env.timeout(0)
        nome = entidade + " " + str(conta_chegada)        
        momento_chegada[nome] = env.now        
        if imprime_detalhes:
            print("{0:.2f}: {1:s} gerada".format(env.now, nome))
        
        # chama o proximo "bloco"         
        env.process(operacao(env, nome, operador_A, operador_B, operador_C))


def operacao(env, nome, operador_A, operador_B, operador_C):
    # Processo não precisa de recursos, apenas da máquina        
    yield env.timeout(distribuicao('operacao'))

    tipo='interna'      
    
    # Decide: 2-way by chance
    sorteio = random()    
    if sorteio <= 0.75: # A máquina vai para a manutenção em A
        estacao='A'        
        env.process(manutencao_A(env, nome, tipo, estacao, operador_A, operador_B, operador_C))
    else:
        estacao='B'          
        env.process(manutencao_B(env, nome, tipo, estacao, operador_A, operador_B, operador_C))


def manutencao_A(env, nome, tipo, estacao, operador_A, operador_B, operador_C):
    momento_entrada_fila[nome] = env.now            
    # Seize, Delay, Release
    request=operador_A.request()
    # Seize
    yield request
    momento_saida_fila[nome] = env.now
    tempo_fila[nome] = momento_saida_fila[nome] - momento_entrada_fila[nome] 
    if env.now > tempo_aquecimento:
        TF.append(tempo_fila[nome])
    if imprime_detalhes:
        print("{0:.2f}: Operador A inicia a manutencao da {1:s}. Entidades em atendimento: {2:d}"
        .format(env.now, nome, operador_A.count))
    
    inicia_atendimento[nome] = env.now
    inicia_utilizacao_Recurso = env.now            
    # Delay
    yield env.timeout(distribuicao('mnt_a'))
    if imprime_detalhes:
        print("{0:.2f}: Operador A termina a manutencao da {1:s}. Entidades em fila: {2:d}"
        .format(env.now, nome, len(operador_A.queue)))
    
    finaliza_atendimento[nome] = env.now        
    duracao_atendimento[nome] = finaliza_atendimento[nome] - inicia_atendimento[nome]
    if env.now > tempo_aquecimento:
        TA.append(duracao_atendimento[nome])
    # Release
    yield operador_A.release(request)

    global tempo_utilizacao_Recurso_Operador_A
    tempo_utilizacao_Recurso_Operador_A += env.now - inicia_utilizacao_Recurso
    utilizacao['Estacao_A'] = tempo_utilizacao_Recurso_Operador_A / (CAP_OPERADOR_A*env.now) 

    # chama o proximo "bloco"
    env.process(inspecao(env, nome, tipo, estacao, operador_A, operador_B, operador_C))


def manutencao_B(env, nome, tipo, estacao, operador_A, operador_B, operador_C):
    momento_entrada_fila[nome] = env.now            
    # Seize, Delay, Release
    request=operador_B.request()
    # Seize
    yield request
    momento_saida_fila[nome] = env.now
    tempo_fila[nome] = momento_saida_fila[nome] - momento_entrada_fila[nome] 
    if env.now > tempo_aquecimento:
        TF.append(tempo_fila[nome])
    if imprime_detalhes:
        print("{0:.2f}: Operador B inicia a manutencao da {1:s}. Entidades em atendimento: {2:d}"
        .format(env.now, nome, operador_B.count))
    
    inicia_atendimento[nome] = env.now
    inicia_utilizacao_Recurso = env.now            
    # Delay
    yield env.timeout(distribuicao('mnt_b'))
    if imprime_detalhes:
        print("{0:.2f}: Operador B termina a manutencao da {1:s}. Entidades em fila: {2:d}"
        .format(env.now, nome, len(operador_B.queue)))
    
    finaliza_atendimento[nome] = env.now        
    duracao_atendimento[nome] = finaliza_atendimento[nome] - inicia_atendimento[nome]
    if env.now > tempo_aquecimento:
        TA.append(duracao_atendimento[nome])
    # Release
    yield operador_B.release(request)
    
    global tempo_utilizacao_Recurso_Operador_B
    tempo_utilizacao_Recurso_Operador_B += env.now - inicia_utilizacao_Recurso
    utilizacao['Estacao_B'] = tempo_utilizacao_Recurso_Operador_B / (CAP_OPERADOR_B*env.now) 

    # chama o proximo "bloco"
    env.process(inspecao(env, nome, tipo, estacao, operador_A, operador_B, operador_C))


def inspecao(env, nome, tipo, estacao, operador_A, operador_B, operador_C):
    global conta_saida_maq_externa        
    momento_entrada_fila[nome] = env.now            
    # Seize, Delay, Release
    request=operador_C.request()
    # Seize
    yield request
    momento_saida_fila[nome] = env.now
    tempo_fila[nome] = momento_saida_fila[nome] - momento_entrada_fila[nome] 
    if env.now > tempo_aquecimento:
        TF.append(tempo_fila[nome])
    if imprime_detalhes:
        print("{0:.2f}: Operador C inicia a inspeção da {1:s}. Entidades em atendimento: {2:d}"
        .format(env.now, nome, operador_C.count))
    
    inicia_atendimento[nome] = env.now
    inicia_utilizacao_Recurso = env.now            
    # Delay       
    yield env.timeout(distribuicao('inspecao'))
    if imprime_detalhes:
        print("{0:.2f}: Operador C termina a inspeção da {1:s}. Entidades em fila: {2:d}"
        .format(env.now, nome, len(operador_C.queue)))
    
    finaliza_atendimento[nome] = env.now        
    duracao_atendimento[nome] = finaliza_atendimento[nome] - inicia_atendimento[nome]
    if env.now > tempo_aquecimento:
        TA.append(duracao_atendimento[nome])
    # Release    
    yield operador_C.release(request)

    global tempo_utilizacao_Recurso_Operador_C
    tempo_utilizacao_Recurso_Operador_C += env.now - inicia_utilizacao_Recurso
    utilizacao['Inspecao'] = tempo_utilizacao_Recurso_Operador_C / (CAP_OPERADOR_C*env.now) 

    # Decide: 2-way by chance
    sorteio = random()
    if tipo=='interna':
        if sorteio <= 0.9:
            # chama o proximo "bloco"
            coleta_dados_indicadores(env, nome)
            if imprime_detalhes:
                print("{0:.2f}: Inspecao aprovada! {1:s} retorna à operação".format(env.now, nome))
            env.process(operacao(env, nome, operador_A, operador_B, operador_C))        
        else:
            if estacao == 'A':                        
                if imprime_detalhes:
                    print("{0:.2f}: Inspecao reprovada! {1:s} retorna à manutenção (Estação A)"
                    .format(env.now, nome))
                # chama o proximo "bloco"
                env.process(manutencao_A(env, nome, tipo, estacao, operador_A, operador_B, operador_C))            
            else:            
                if imprime_detalhes:
                    print("{0:.2f}: Inspecao reprovada! {1:s} retorna à manutenção (Estação B)"
                    .format(env.now, nome))
                # chama o proximo "bloco"
                env.process(manutencao_B(env, nome, tipo, estacao, operador_A, operador_B, operador_C))
    else:
        if sorteio <= 0.18:
            # chama o proximo "bloco"            
            if imprime_detalhes:
                print("{0:.2f}: Inspecao reprovada! {1:s} retorna à manutenção (Estação B)"
                .format(env.now, nome))
            # chama o proximo "bloco"
            env.process(manutencao_B(env, nome, tipo, estacao, operador_A, operador_B, operador_C))
        else:
            # chama o proximo "bloco"
            conta_saida_maq_externa += 1
            coleta_dados_indicadores(env, nome)            


def coleta_dados_indicadores(env, nome):    
    # Entidade não sai do sistema    
    global conta_saida
    global conta_saida_maq_externa        

    global operador_A
    global operador_B
    global operador_C

    # Coleta dados para estatísticas        
    numero_sistema = conta_chegada + conta_chegada_maq_externa \
    - conta_saida - conta_saida_maq_externa

    if env.now > tempo_aquecimento:
        NS.append(numero_sistema)        
        NA.append(operador_A.count + operador_B.count + operador_C.count)
        NF.append(len(operador_A.queue) + len(operador_B.queue) +
        len(operador_C.queue))
    
    momento_saida[nome] = env.now            
    tempo_sistema[nome] = momento_saida[nome] - momento_chegada[nome]
    
    if env.now > tempo_aquecimento:
        TS.append(tempo_sistema[nome])        
        USO_A.append(utilizacao['Estacao_A']) 
        USO_B.append(utilizacao['Estacao_B'])        
        USO_I.append(utilizacao['Inspecao'])                
        T.append(env.now)


def computa_estatisticas(replicacao, tempo):  
    print()
    comprimento_linha = 100
    print("="*comprimento_linha)   
    print("Indicadores de Desempenho da Replicacao {0:d}".format(replicacao), end="\n")
    print("="*comprimento_linha)   
    
    entidade = "máquinas"

    NS_i = np.mean(NS)
    NF_i = np.mean(NF)
    NA_i = np.mean(NA)
    TS_i = np.mean(TS)
    TF_i = np.mean(TF)
    TA_i = np.mean(TA)
    USO_A_i= np.mean(USO_A) if len(USO_A) > 0 else 0    
    USO_B_i= np.mean(USO_B) if len(USO_B) > 0 else 0    
    USO_I_i= np.mean(USO_I) if len(USO_I) > 0 else 0        
    conta_chegada + conta_chegada_maq_externa \
    - conta_saida - conta_saida_maq_externa
    print('Chegadas: {0:d} {1:s}'.format(conta_chegada + conta_chegada_maq_externa, entidade))
    print('Saidas:   {0:d} {1:s}'.format(conta_saida + conta_saida_maq_externa, entidade))
    print('WIP:      {0:d} {1:s}'.format(conta_chegada + conta_chegada_maq_externa - conta_saida - conta_saida_maq_externa, entidade))
    print('NS: {0:.2f} {1:s}'.format(NS_i, entidade))
    print('NF: {0:.2f} {1:s}'.format(NF_i, entidade))
    print('NA: {0:.2f} {1:s}'.format(NA_i, entidade))
    print('TS: {0:.2f} {1:s}'.format(TS_i, tempo))
    print('TF: {0:.2f} {1:s}'.format(TF_i, tempo))
    print('TA: {0:.2f} {1:s}'.format(TA_i, tempo))
    print('USO-A:{0:.2f}%'.format(USO_A_i*100))    
    print('USO-B:{0:.2f}%'.format(USO_B_i*100))    
    print('USO-I:{0:.2f}%'.format(USO_I_i*100))    
    
    print("="*comprimento_linha, end="\n")   
    NS_bar.append(NS_i)
    NF_bar.append(NF_i)
    NA_bar.append(NA_i)
    TS_bar.append(TS_i)
    TF_bar.append(TF_i)
    TA_bar.append(TA_i)
    USO_A_bar.append(USO_A_i)
    USO_B_bar.append(USO_B_i)
    USO_I_bar.append(USO_I_i)


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
    
    entidade = "máquinas"

    print('NS: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(NS_bar), calc_ic(NS), entidade))
    print('NF: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(NF_bar), calc_ic(NF), entidade))
    print('NA: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(NA_bar), calc_ic(NA), entidade))
    print('TS: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(TS_bar), calc_ic(TS), tempo))
    print('TF: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(TF_bar), calc_ic(TF), tempo))
    print('TA: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(TA_bar), calc_ic(TA), tempo))
    print('USO-A:{0:.2f}% \u00B1 {1:.2f}%  (IC 95%)'.format(np.mean(USO_A_bar)*100, calc_ic(USO_A)*100))
    print('USO-B:{0:.2f}% \u00B1 {1:.2f}%  (IC 95%)'.format(np.mean(USO_B_bar)*100, calc_ic(USO_B)*100))
    print('USO-I:{0:.2f}% \u00B1 {1:.2f}%  (IC 95%)'.format(np.mean(USO_I_bar)*100, calc_ic(USO_I)*100))    
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
        y1 = USO_A
        y2 = USO_B
        y3 = USO_I        
        # usa a função plot
        plt.title('Indicador de Desempenho: \n\n' + \
        "Utilização média dos Recursos")
        plt.plot(xi, y1, marker='o', linestyle='-', color='red', label='Operador (Estação Mnt A)')        
        plt.plot(xi, y2, marker='o', linestyle='-', color='green', label='Operador (Estação Mnt B)')                
        plt.plot(xi, y3, marker='o', linestyle='-', color='blue', label='Operador (Inspeção)')        
        
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
    conta_chegada_maq_externa = 0    
    conta_saida = 0    
    conta_saida_maq_externa = 0    
    tempo_utilizacao_Recurso_Operador_A = 0
    tempo_utilizacao_Recurso_Operador_B = 0
    tempo_utilizacao_Recurso_Operador_C = 0

    env = simpy.Environment()
    operador_A = simpy.Resource(env,capacity=CAP_OPERADOR_A)
    operador_B = simpy.Resource(env,capacity=CAP_OPERADOR_B)
    operador_C = simpy.Resource(env,capacity=CAP_OPERADOR_C)
    env.process(chegada_maq_internas(env, "maquina_interna", operador_A,
    operador_B, operador_C))
    env.process(chegada_maq_externas(env, "maquina_externa", operador_A,
    operador_B, operador_C))
    env.run(duracao_da_simulacao)
    computa_estatisticas(i, "minutos")        

publica_estatisticas("minutos")
###################################################################

