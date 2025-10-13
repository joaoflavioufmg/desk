# -*- coding: utf-8 -*-
#!/usr/bin/python3

# Disciplina: EPD899: Simulacao de Sistemas Logísticos
# Prof: Joao Flavio F. Almeida <joao.flavio@dep.ufmg>
# Problemas de Simulação - Resolução em Simpy (python)

# ##################################################################
# Implementação computacional dos 10 exemplos das aulas
# ##################################################################

# ##################################################################
# Uma empresa usa matérias primas do tipo A e B. Ambas são 
# transportadas por caminhões, de mesma capacidade, que chegam à empresa 
# segundo uma distribuição exponencial negativa de média de 25 minutos. 
# Sabe-se que 30% desses caminhões trazem matéria prima do tipo A e o
# restante do tipo B. Ao chegarem à empresa os caminhões têm sua carga 
# checada por um funcionário da portaria, que preenche um formulário e 
# encaminha o caminhão para uma das docas de descarga, atividade que 
# possui duração exponencialmente distribuída com média de 5 minutos. 
# Existe uma doca (Doca A) para descarga de caminhões que transportam 
# mercadorias do tipo A e duas docas para aqueles que transportam 
# mercadorias do tipo B (Doca B1 e Doca B2). O tempo de descarga
# dos caminhões que transportam mercadoria do tipo A segue uma 
# distribuição normal com média de 30 minutos e desvio padrão de 
# 6 minutos. O tempo de descarga dos caminhões que transportam 
# mercadoria do tipo B segue uma distribuição triangular com moda 
# de 38, mínimo de 30 e máximo de 50 minutos. Os caminhões com 
# mercadorias do tipo B são encaminhados para a doca que tiver
# menor fila (B1 ou B2). Após a descarga, os caminhões seguem para 
# outro setor da empresa onde entregam as notas fiscais e os recibos 
# de descarga. Neste setor, os caminhões são atendidos por um
# funcionário, que preenche um formulário de liberação do veículo. 
# O tempo gasto pelo funcionário para realização deste serviço segue 
# uma distribuição normal com média de 7 minutos e desvio padrão de 2 
# minutos. Após receberem o formulário de liberação, os caminhões se 
# dirigem à portaria da empresa, onde o mesmo funcionário que os recebeu 
# faz uma vistoria de segurança nos caminhões, para certificar se eles 
# não estão saindo com nada da empresa, e os libera em seguida. O tempo 
# gasto nesta atividade é exponencialmente distribuído com média de 4 
# minutos. O funcionário da portaria prioriza o atendimento de chegada 
# de caminhões em relação à vistoria de saída. Posto isto, construir 
# o diagrama de ciclo de atividades representativo deste sistema.
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
USO_P=[]
USO_F=[]
USO_A=[]
USO_B1=[]
USO_B2=[]

NS_bar = []
NF_bar = [] 
NA_bar = [] 
TS_bar = [] 
TF_bar = [] 
TA_bar = []
USO_P_bar=[]
USO_F_bar=[]
USO_A_bar=[]
USO_B1_bar=[]
USO_B2_bar=[]

T = []  # Tempo dos Eventos Discretos

conta_chegada = 0
conta_saida = 0 
tempo_utilizacao_Recurso_Porteiro = 0
tempo_utilizacao_Recurso_Funcionario = 0
tempo_utilizacao_Recurso_Doca_A = 0
tempo_utilizacao_Recurso_Doca_B1 = 0
tempo_utilizacao_Recurso_Doca_B2 = 0

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
utilizacao['Doca_A'] = 0
utilizacao['Doca_B1'] = 0
utilizacao['Doca_B2'] = 0

CAP_PORTEIROS = 1
CAP_FUNCIONARIOS = 1
CAP_DOCA_A = 1
CAP_DOCA_B1 = 1
CAP_DOCA_B2 = 1

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
    taxa_chegada = 1/25 # por minuto
    taxa_checagem = 1/5 # por minuto
    taxa_vistoria = 1/4 # por minuto
    return {
        'chegada': expovariate(taxa_chegada),       # minutos
        'recepcao': expovariate(taxa_checagem),     # minutos
        'descarga_A': max(0, gauss(30,6)),          # minutos
        'descarga_B': triangular(30,50,38),         # minutos
        'liberacao': max(0, gauss(7,2)),            # minutos
        'vistoria':  expovariate(taxa_vistoria)     # minutos
    }.get(tipo,0.0)


def sorteia_carga():
    r = random()    
    return "A" if r <= 0.30 else "B"
    # if r <= 0.30:
    #     return "A"
    # else:
    #     return "B"


def chegada_caminhao(env, entidade, porteiro):
    global conta_chegada

    while True:
        yield env.timeout(distribuicao('chegada'))
        conta_chegada+=1
        nome = entidade + " " + str(conta_chegada)        
        momento_chegada[nome] = env.now        
        if imprime_detalhes:
            print("{0:.2f}: {1:s} chega na empresa".format(env.now, nome))
        # chama o proximo "bloco"                
        prio=0
        env.process(recepcao(env, nome, porteiro, prio))
        
        
def recepcao(env, nome, porteiro, prio):
    momento_entrada_fila[nome] = env.now            
    # Seize, Delay, Release    
    with porteiro.request(priority=prio) as req:
        # Seize
        yield req
        momento_saida_fila[nome] = env.now
        tempo_fila[nome] = momento_saida_fila[nome] - momento_entrada_fila[nome] 
        if env.now > tempo_aquecimento:
            TF.append(tempo_fila[nome])
        if imprime_detalhes:
            print("{0:.2f}: Porteiro inicia a recepção do {1:s}. Número de entidades em atendimento: {2:d}"
            .format(env.now, nome, porteiro.count))
        
        inicia_atendimento[nome] = env.now
        inicia_utilizacao_Recurso = env.now
        # Delay        
        yield env.timeout(distribuicao('recepcao'))
        if imprime_detalhes:
            print("{0:.2f}: Porteiro termina a recepção do {1:s}.  Número de entidades em fila: {2:d}"
            .format(env.now, nome, len(porteiro.queue)))
        
        finaliza_atendimento[nome] = env.now        
        duracao_atendimento[nome] = finaliza_atendimento[nome] - inicia_atendimento[nome]
        if env.now > tempo_aquecimento:
            TA.append(duracao_atendimento[nome])

    # Release
    global tempo_utilizacao_Recurso_Porteiro
    tempo_utilizacao_Recurso_Porteiro += env.now - inicia_utilizacao_Recurso
    utilizacao['Porteiros'] = tempo_utilizacao_Recurso_Porteiro / (CAP_PORTEIROS*env.now)  
        
    # chama o proximo "bloco" # Carga tipo A?
    tipo_carga = sorteia_carga()    
    
    if tipo_carga == "A":
        env.process(descarga_A(env, nome, doca_A))
    else:
        env.process(descarga_B(env, nome, doca_B1, doca_B2))


def descarga_A(env, nome, doca_A):    
    momento_entrada_fila[nome] = env.now        
    # Seize, Delay, Release
    with doca_A.request() as req:
        # Seize
        yield req
        momento_saida_fila[nome] = env.now
        tempo_fila[nome] = momento_saida_fila[nome] - momento_entrada_fila[nome] 
        if env.now > tempo_aquecimento:
            TF.append(tempo_fila[nome])
        if imprime_detalhes:
            print("{0:.2f}: {1:s} inicia a descarga na Doca A. Entidades em atendimento: {2:d}"
            .format(env.now, nome, doca_A.count))
        # Delay
        inicia_atendimento[nome] = env.now
        inicia_utilizacao_Recurso = env.now
        yield env.timeout(distribuicao('descarga_A'))
        if imprime_detalhes:
            print("{0:.2f}: {1:s} finaliza a descarga na Doca A. Entidades em fila: {2:d}"
            .format(env.now, nome, len(doca_A.queue)))
        
        finaliza_atendimento[nome] = env.now        
        duracao_atendimento[nome] = finaliza_atendimento[nome] - inicia_atendimento[nome]
        if env.now > tempo_aquecimento:
            TA.append(duracao_atendimento[nome])

    # Release
    global tempo_utilizacao_Recurso_Doca_A
    tempo_utilizacao_Recurso_Doca_A += env.now - inicia_utilizacao_Recurso
    utilizacao['Doca_A'] = tempo_utilizacao_Recurso_Doca_A / (CAP_DOCA_A*env.now)  
        
    # chama o proximo "bloco"         
    env.process(liberacao(env, nome, funcionario))

def descarga_B(env, nome, doca_B1, doca_B2):   
    if len(doca_B1.queue) <= len(doca_B2.queue):
        momento_entrada_fila[nome] = env.now
        # Seize, Delay, Release
        with doca_B1.request() as req:
            # Seize
            yield req
            momento_saida_fila[nome] = env.now
            tempo_fila[nome] = momento_saida_fila[nome] - momento_entrada_fila[nome] 
            if env.now > tempo_aquecimento:
                TF.append(tempo_fila[nome])
            if imprime_detalhes:
                print("{0:.2f}: {1:s} inicia a descarga na Doca B1. Entidades em atendimento: {2:d}"
                .format(env.now, nome, doca_B1.count))
            # Delay
            inicia_atendimento[nome] = env.now
            inicia_utilizacao_Recurso = env.now            
            yield env.timeout(distribuicao('descarga_B'))
            if imprime_detalhes:
                print("{0:.2f}: {1:s} finaliza a descarga na Doca B1. Entidades em fila: {2:d}"
                .format(env.now, nome, len(doca_B1.queue)))
            
            finaliza_atendimento[nome] = env.now        
            duracao_atendimento[nome] = finaliza_atendimento[nome] - inicia_atendimento[nome]
            if env.now > tempo_aquecimento:
                TA.append(duracao_atendimento[nome])
        
         # Release
        global tempo_utilizacao_Recurso_Doca_B1
        tempo_utilizacao_Recurso_Doca_B1 += env.now - inicia_utilizacao_Recurso
        utilizacao['Doca_B1'] = tempo_utilizacao_Recurso_Doca_B1 / (CAP_DOCA_B1*env.now)  
            
        # chama o proximo "bloco"
        env.process(liberacao(env, nome, funcionario))
    else:
        momento_entrada_fila[nome] = env.now
        # Seize, Delay, Release
        with doca_B2.request() as req:
            # Seize
            yield req
            momento_saida_fila[nome] = env.now
            tempo_fila[nome] = momento_saida_fila[nome] - momento_entrada_fila[nome] 
            if env.now > tempo_aquecimento:
                TF.append(tempo_fila[nome])
            if imprime_detalhes:
                print("{0:.2f}: {1:s} inicia a descarga na Doca B2. Entidades em atendimento: {2:d}"
                .format(env.now, nome, doca_B2.count))
            # Delay
            inicia_atendimento[nome] = env.now
            inicia_utilizacao_Recurso = env.now            
            yield env.timeout(distribuicao('descarga_B'))
            if imprime_detalhes:
                print("{0:.2f}: {1:s} finaliza a descarga na Doca B2. Entidades em fila: {2:d}"
                .format(env.now, nome, len(doca_B2.queue)))
            
            finaliza_atendimento[nome] = env.now        
            duracao_atendimento[nome] = finaliza_atendimento[nome] - inicia_atendimento[nome]
            if env.now > tempo_aquecimento:
                TA.append(duracao_atendimento[nome])
        
        # Release
        global tempo_utilizacao_Recurso_Doca_B2
        tempo_utilizacao_Recurso_Doca_B2 += env.now - inicia_utilizacao_Recurso
        utilizacao['Doca_B2'] = tempo_utilizacao_Recurso_Doca_B2 / (CAP_DOCA_B2*env.now)  
            
        # chama o proximo "bloco"
        env.process(liberacao(env, nome, funcionario))

def liberacao(env, nome, funcionario):
    momento_entrada_fila[nome] = env.now
    # Seize, Delay, Release
    with funcionario.request() as req:
        # Seize
        yield req
        momento_saida_fila[nome] = env.now
        tempo_fila[nome] = momento_saida_fila[nome] - momento_entrada_fila[nome] 
        if env.now > tempo_aquecimento:
            TF.append(tempo_fila[nome])
        if imprime_detalhes:
            print("{0:.2f}: Funcionário inicia a liberação do {1:s}. Entidades em atendimento: {2:d}"
            .format(env.now, nome, funcionario.count))
        # Delay
        inicia_atendimento[nome] = env.now
        inicia_utilizacao_Recurso = env.now 
        yield env.timeout(distribuicao('liberacao'))
        if imprime_detalhes:
            print("{0:.2f}: Funcionário finaliza a liberação do {1:s}. Entidades em fila: {2:d}"
            .format(env.now, nome, len(funcionario.queue)))
        
        finaliza_atendimento[nome] = env.now        
        duracao_atendimento[nome] = finaliza_atendimento[nome] - inicia_atendimento[nome]
        if env.now > tempo_aquecimento:
            TA.append(duracao_atendimento[nome])
    
    # Release
    global tempo_utilizacao_Recurso_Funcionario
    tempo_utilizacao_Recurso_Funcionario += env.now - inicia_utilizacao_Recurso
    utilizacao['Funcionarios'] = tempo_utilizacao_Recurso_Funcionario / (CAP_FUNCIONARIOS*env.now)  
    
        
    # chama o proximo "bloco"   
    prio=1
    env.process(vistoria(env, nome, porteiro, prio))

def vistoria(env, nome, porteiro, prio):
    momento_entrada_fila[nome] = env.now
    # Seize, Delay, Release
    with porteiro.request(priority=prio) as req:
        # Seize
        yield req
        momento_saida_fila[nome] = env.now
        tempo_fila[nome] = momento_saida_fila[nome] - momento_entrada_fila[nome] 
        if env.now > tempo_aquecimento:
            TF.append(tempo_fila[nome])
        if imprime_detalhes:
            print("{0:.2f}: Porteiro inicia a vistoria do {1:s}. Entidades em atendimento: {2:d}"
            .format(env.now, nome, porteiro.count))
        # Delay
        inicia_atendimento[nome] = env.now
        inicia_utilizacao_Recurso = env.now 
        
        yield env.timeout(distribuicao('vistoria'))
        if imprime_detalhes:
            print("{0:.2f}: Porteiro finaliza a vistoria do {1:s}. Entidades em fila: {2:d}"
            .format(env.now, nome, len(porteiro.queue)))
        
        finaliza_atendimento[nome] = env.now        
        duracao_atendimento[nome] = finaliza_atendimento[nome] - inicia_atendimento[nome]
        if env.now > tempo_aquecimento:
            TA.append(duracao_atendimento[nome])
    
    # Release
    global tempo_utilizacao_Recurso_Porteiro
    tempo_utilizacao_Recurso_Porteiro += env.now - inicia_utilizacao_Recurso
    utilizacao['Porteiros'] = tempo_utilizacao_Recurso_Porteiro / (CAP_PORTEIROS*env.now)  
    
        
    # chama o proximo "bloco"
    coleta_dados_indicadores(env, nome)
        

def coleta_dados_indicadores(env, nome):    
    # Entidade sai do sistema    
    global conta_saida
    conta_saida += 1

    global porteiro
    global funcionario
    global doca_A
    global doca_B1
    global doca_B2

    # Coleta dados para estatísticas        
    numero_sistema = conta_chegada - conta_saida

    if env.now > tempo_aquecimento:
        NS.append(numero_sistema)
        NA.append(porteiro.count + funcionario.count + doca_A.count +
        doca_B1.count + doca_B2.count)
        NF.append(len(porteiro.queue) + len(funcionario.queue) + 
        len(doca_A.queue) + len(doca_B1.queue) + len(doca_B2.queue))
        
    
    momento_saida[nome] = env.now            
    tempo_sistema[nome] = momento_saida[nome] - momento_chegada[nome]
    
    if env.now > tempo_aquecimento:
        TS.append(tempo_sistema[nome])
        
        USO_P.append(utilizacao['Porteiros']) 
        USO_F.append(utilizacao['Funcionarios'])
        USO_A.append(utilizacao['Doca_A'])
        USO_B1.append(utilizacao['Doca_B1'])
        USO_B2.append(utilizacao['Doca_B2'])       
        T.append(env.now)
 

def computa_estatisticas(replicacao, tempo):  
    print()
    comprimento_linha = 100
    print("="*comprimento_linha)   
    print("Indicadores de Desempenho da Replicacao {0:d}".format(replicacao), end="\n")
    print("="*comprimento_linha)   
    
    entidade = "caminhões"

    NS_i = np.mean(NS)
    NF_i = np.mean(NF)
    NA_i = np.mean(NA)
    TS_i = np.mean(TS)
    TF_i = np.mean(TF)
    TA_i = np.mean(TA)
    USO_P_i= np.mean(USO_P) if len(USO_P) > 0 else 0    
    USO_F_i= np.mean(USO_F) if len(USO_F) > 0 else 0    
    USO_A_i= np.mean(USO_A) if len(USO_A) > 0 else 0    
    USO_B1_i= np.mean(USO_B1) if len(USO_B1) > 0 else 0    
    USO_B2_i= np.mean(USO_B2) if len(USO_B2) > 0 else 0    
    
    print('Chegadas: {0:d} {1:s}'.format(conta_chegada, entidade))
    print('Saidas:   {0:d} {1:s}'.format(conta_saida, entidade))
    print('WIP:      {0:d} {1:s}'.format(conta_chegada-conta_saida, entidade))
    print('NS: {0:.2f} {1:s}'.format(NS_i, entidade))
    print('NF: {0:.2f} {1:s}'.format(NF_i, entidade))
    print('NA: {0:.2f} {1:s}'.format(NA_i, entidade))
    print('TS: {0:.2f} {1:s}'.format(TS_i, tempo))
    print('TF: {0:.2f} {1:s}'.format(TF_i, tempo))
    print('TA: {0:.2f} {1:s}'.format(TA_i, tempo))
    print('USO-P:{0:.2f}%'.format(USO_P_i*100))    
    print('USO-F:{0:.2f}%'.format(USO_F_i*100))    
    print('USO-A:{0:.2f}%'.format(USO_A_i*100))    
    print('USO-B1:{0:.2f}%'.format(USO_B1_i*100))    
    print('USO-B2:{0:.2f}%'.format(USO_B2_i*100))    
    
    
    print("="*comprimento_linha, end="\n")   
    NS_bar.append(NS_i)
    NF_bar.append(NF_i)
    NA_bar.append(NA_i)
    TS_bar.append(TS_i)
    TF_bar.append(TF_i)
    TA_bar.append(TA_i)
    USO_P_bar.append(USO_P_i)
    USO_F_bar.append(USO_F_i)
    USO_A_bar.append(USO_A_i)
    USO_B1_bar.append(USO_B1_i)
    USO_B2_bar.append(USO_B2_i)

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
    
    entidade = "caminhões"

    print('NS: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(NS_bar), calc_ic(NS), entidade))
    print('NF: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(NF_bar), calc_ic(NF), entidade))
    print('NA: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(NA_bar), calc_ic(NA), entidade))
    print('TS: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(TS_bar), calc_ic(TS), tempo))
    print('TF: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(TF_bar), calc_ic(TF), tempo))
    print('TA: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(TA_bar), calc_ic(TA), tempo))
    print('USO-P:{0:.2f}% \u00B1 {1:.2f}%  (IC 95%)'.format(np.mean(USO_P_bar)*100, calc_ic(USO_P)*100))
    print('USO-F:{0:.2f}% \u00B1 {1:.2f}%  (IC 95%)'.format(np.mean(USO_F_bar)*100, calc_ic(USO_F)*100))
    print('USO-A:{0:.2f}% \u00B1 {1:.2f}%  (IC 95%)'.format(np.mean(USO_A_bar)*100, calc_ic(USO_A)*100))
    print('USO-B1:{0:.2f}% \u00B1 {1:.2f}%  (IC 95%)'.format(np.mean(USO_B1_bar)*100, calc_ic(USO_B1)*100))
    print('USO-B2:{0:.2f}% \u00B1 {1:.2f}%  (IC 95%)'.format(np.mean(USO_B2_bar)*100, calc_ic(USO_B2)*100))
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
        y1 = USO_P        
        y2 = USO_F
        y3 = USO_A
        y4 = USO_B1
        y5 = USO_B2
        
        # usa a função plot
        plt.title('Indicador de Desempenho: \n\n' + \
        "Utilização média dos Recursos")
        plt.plot(xi, y1, marker='o', linestyle='-', color='red', label='Porteiros')        
        plt.plot(xi, y2, marker='o', linestyle='-', color='green', label='Funcionários')        
        plt.plot(xi, y3, marker='o', linestyle='-', color='blue', label='Doca A')        
        plt.plot(xi, y4, marker='o', linestyle='-', color='yellow', label='Doca B1')        
        plt.plot(xi, y5, marker='o', linestyle='-', color='black', label='Doca B2')        
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
    tempo_utilizacao_Recurso_Porteiro = 0
    tempo_utilizacao_Recurso_Funcionario = 0
    tempo_utilizacao_Recurso_Doca_A = 0
    tempo_utilizacao_Recurso_Doca_B1 = 0
    tempo_utilizacao_Recurso_Doca_B2 = 0

    env = simpy.Environment()
    porteiro = simpy.PriorityResource(env,CAP_PORTEIROS)
    funcionario = simpy.Resource(env,CAP_FUNCIONARIOS)
    doca_A = simpy.Resource(env,CAP_DOCA_A)
    doca_B1 = simpy.Resource(env,CAP_DOCA_B1)
    doca_B2 = simpy.Resource(env,CAP_DOCA_B2)
    env.process(chegada_caminhao(env, "caminhao", porteiro))
    env.run(duracao_da_simulacao)
    computa_estatisticas(i, "minutos")        

publica_estatisticas("minutos")
###################################################################
