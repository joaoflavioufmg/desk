# -*- coding: utf-8 -*-
#!/usr/bin/python3

# Disciplina: EPD899: Simulacao de Sistemas Logísticos
# Prof: Joao Flavio F. Almeida <joao.flavio@dep.ufmg>
# Problemas de Simulação - Resolução em Simpy (python)

# ##################################################################
# Implementação computacional dos 10 exemplos das aulas
# ##################################################################

# ##################################################################
# Uma empresa opera 7 sondas de perfuração de petróleo num campo 
# petrolífero no mar. As sondas trabalham em operação contínua, 
# interrompendo seu funcionamento apenas para manutenção corretiva. 
# O tempo entre falhas é descrito por uma distribuição normal com média 
# 168 e desvio padrão de 24 horas. A manutenção é feita por uma única 
# equipe e sua duração é exponencialmente distribuída com média de 24 
# horas. No início da operação a equipe se encontra em uma base em 
# terra. A cada quebra de sonda, a equipe se desloca para o local da 
# sonda, ali permanecendo até o término da manutenção. Ao final da 
# manutenção, se não houver outras sondas quebradas, a equipe retorna 
# à base. Caso haja, a equipe se desloca diretamente para a sonda que 
# estiver há mais tempo aguardando manutenção. Os tempos de deslocamento 
# entre as sondas são descritos por uma distribuição normal com média 
# de 0.9h e desvio padrão de 0.2h. Os tempos de deslocamento entre
# as sondas e a base em terra também seguem uma distribuição normal 
# com média de 1,2h e desvio padrão de 0.2h. Posto isto, fazer o DCA 
# representativo do sistema.
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
USO_EM=[]

NS_bar = []
NF_bar = [] 
NA_bar = [] 
TS_bar = [] 
TF_bar = [] 
TA_bar = []
USO_EM_bar=[]

T = []  # Tempo dos Eventos Discretos

conta_chegada = 0
conta_saida = 0 
tempo_utilizacao_Recurso_Equipe_Mnt = 0

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

CAP_EQUIPE_MNT = 1

FILA_MNT = []

###################################################################
# Configura a rodada de simulacao definindo o 
# numero de replicações e duração da simulação
###################################################################
# # Teste
# n_replicacoes = 1 
# duracao_da_simulacao = 10000
# tempo_aquecimento = 0
# imprime_detalhes = True 
###################################################################
# Simulação oficial
n_replicacoes = 5
duracao_da_simulacao =   10*365*24
tempo_aquecimento = 12*30*24
imprime_detalhes = False 
###################################################################

# Unidade básica para todos os tempos: horas

def distribuicao(tipo):
    taxa_manutencao = 1/24 # por hora
    return {
        'operacao': max(0, gauss(168,24)),          # horas
        'deslocTerraMar': max(0, gauss(1.2,0.2)),   # horas
        'manutencao': expovariate(taxa_manutencao), # horas
        'deslocEntreSondas': max(0, gauss(0.9,0.2)),# horas          
        'deslocMarTerra': max(0, gauss(1.2,0.2))    # horas        
    }.get(tipo,0.0)


def gera_sondas(env, entidade, sondas, equipes_mnt):
    global conta_chegada
    yield env.timeout(0)
    for conta_chegada in range(1,8):        
        id = entidade + " " + str(conta_chegada)        
        momento_chegada[id] = env.now
        if imprime_detalhes:
            print("{0:.2f}: Gera {1:s}".format(env.now, id))
        # chama o proximo "bloco"
        env.process(operacao(env, id, sondas, equipes_mnt))


def operacao(env, id, sondas, equipes_mnt):
    if imprime_detalhes:
        print("{0:.2f}: {1:s} inicia operação.".format(env.now, id))
    # Delay
    yield env.timeout(distribuicao('operacao'))
    
    if imprime_detalhes:
        print("{0:.2f}: {1:s} quebrou e precisa de manutenção. Entidades em atendimento: {2:d}"
        .format(env.now, id, sondas.level))
    
    sondas.put(1) # -> há sonda esperando para ter manutenção
    FILA_MNT.append(id)   # Adiciona um elemento na fila (lista)
    
    nome = FILA_MNT[0]

    momento_entrada_fila[nome] = env.now            
    # chama o proximo "bloco" 
    env.process(desloc_terra_mar(env, id, nome, sondas, equipes_mnt))


def desloc_terra_mar(env, id, nome, sondas, equipes_mnt):
    yield equipes_mnt.get(1)    # Retira 1 equipe para resolver o problema
    yield sondas.get(1)         # Retira 1 sonda para ter o problema resolvido

    if imprime_detalhes:
        print("{0:.2f}: Equipe desloca para o mar".format(env.now))
    
    inicia_utilizacao_Recurso = env.now
    yield env.timeout(distribuicao('deslocTerraMar'))
    if imprime_detalhes:
        print("{0:.2f}: Equipe chega na {1:s} para realizar a manuteção"
        .format(env.now, nome))

    global tempo_utilizacao_Recurso_Equipe_Mnt
    tempo_utilizacao_Recurso_Equipe_Mnt += env.now - inicia_utilizacao_Recurso
    utilizacao['Equipe_Mnt'] = tempo_utilizacao_Recurso_Equipe_Mnt / (CAP_EQUIPE_MNT*env.now)  

    # chama o proximo "bloco" 
    env.process(manutencao(env, id, nome, sondas, equipes_mnt))


def manutencao(env, id, nome, sondas, equipes_mnt):

    global FILA_MNT

    momento_saida_fila[nome] = env.now
    tempo_fila[nome] = momento_saida_fila[nome] - momento_entrada_fila[nome] 
    if env.now > tempo_aquecimento:
        TF.append(tempo_fila[nome])
        NF.append(len(FILA_MNT))
    if imprime_detalhes:
        print("{0:.2f}: Equipe inicia manutenção da {1:s}. Entidades em atendimento: {2:d}"
        .format(env.now, nome, equipes_mnt.level))
    
    inicia_atendimento[nome] = env.now
    inicia_utilizacao_Recurso = env.now
    # Delay    
    yield env.timeout(distribuicao('manutencao'))
    if imprime_detalhes:
        print("{0:.2f}: Equipe termina a manutenção da {1:s}. Entidades em fila: {2:d}"
        .format(env.now, nome, len(FILA_MNT)))
    
    finaliza_atendimento[nome] = env.now        
    duracao_atendimento[nome] = finaliza_atendimento[nome] - inicia_atendimento[nome]
    if env.now > tempo_aquecimento:
        TA.append(duracao_atendimento[nome])

    global tempo_utilizacao_Recurso_Equipe_Mnt
    tempo_utilizacao_Recurso_Equipe_Mnt += env.now - inicia_utilizacao_Recurso
    utilizacao['Equipe_Mnt'] = tempo_utilizacao_Recurso_Equipe_Mnt / (CAP_EQUIPE_MNT*env.now)  

    FILA_MNT.pop(0)
    if env.now > tempo_aquecimento:        
        NF.append(len(FILA_MNT))

    env.process(operacao(env, id, sondas, equipes_mnt))

    if sondas.level > 0:
        env.process(desloc_entre_sondas(env, id, nome, sondas, equipes_mnt))        
    else:
        env.process(desloc_mar_terra(env, nome, equipes_mnt))
        

def desloc_entre_sondas(env, id, nome, sondas, equipes_mnt):

    yield sondas.get(1)
    if imprime_detalhes:
        print("{0:.2f}: Equipe vai para {1:s}. Entidades em atendimento: {2:d}"
        .format(env.now, nome, equipes_mnt.level))
    
    inicia_utilizacao_Recurso = env.now
    yield env.timeout(distribuicao('deslocEntreSondas'))
    if imprime_detalhes:
        print("{0:.2f}: Equipe chega na {1:s}. Entidades em fila: {2:d}"
        .format(env.now, nome, len(FILA_MNT)))

    global tempo_utilizacao_Recurso_Equipe_Mnt
    tempo_utilizacao_Recurso_Equipe_Mnt += env.now - inicia_utilizacao_Recurso
    utilizacao['Equipe_Mnt'] = tempo_utilizacao_Recurso_Equipe_Mnt / (CAP_EQUIPE_MNT*env.now)  

    # chama o proximo "bloco"
    env.process(manutencao(env, id, nome, sondas, equipes_mnt))


def desloc_mar_terra(env, nome, equipes_mnt):

    if imprime_detalhes:
        print("{0:.2f}: Equipe retorna ao continente. Entidades em atendimento: {1:d}"
        .format(env.now, equipes_mnt.level))
    
    inicia_utilizacao_Recurso = env.now
    yield env.timeout(distribuicao('deslocMarTerra'))
    if imprime_detalhes:
        print("{0:.2f}: Equipe chega ao continente. Entidades em fila: {1:d}"
        .format(env.now, len(FILA_MNT)))

    global tempo_utilizacao_Recurso_Equipe_Mnt
    tempo_utilizacao_Recurso_Equipe_Mnt += env.now - inicia_utilizacao_Recurso
    utilizacao['Equipe_Mnt'] = tempo_utilizacao_Recurso_Equipe_Mnt / (CAP_EQUIPE_MNT*env.now)  

    equipes_mnt.put(1)      # retorna 1 equipe para "escritório"
    
    # chama o proximo "bloco"
    coleta_dados_indicadores(env, nome)


def coleta_dados_indicadores(env, nome):    
    # Entidade não sai do sistema
    global conta_saida        
    
    global equipes_mnt

    # Coleta dados para estatísticas        
    numero_sistema = conta_chegada - conta_saida

    if env.now > tempo_aquecimento:
        NS.append(numero_sistema)        
        NA.append(equipes_mnt.level)
        # NF.append(len(FILA_MNT))
    
    momento_saida[nome] = env.now            
    tempo_sistema[nome] = momento_saida[nome] - momento_chegada[nome]
    
    if env.now > tempo_aquecimento:
        TS.append(tempo_sistema[nome])        
        USO_EM.append(utilizacao['Equipe_Mnt']) 
        T.append(env.now)


def computa_estatisticas(replicacao, tempo):  
    print()
    comprimento_linha = 100
    print("="*comprimento_linha)   
    print("Indicadores de Desempenho da Replicacao {0:d}"
    .format(replicacao), end="\n")
    print("="*comprimento_linha)   
    
    entidade = "sondas"

    NS_i = np.mean(NS)
    NF_i = np.mean(NF)
    NA_i = np.mean(NA)
    TS_i = np.mean(TS)
    TF_i = np.mean(TF)
    TA_i = np.mean(TA)
    USO_EM_i= np.mean(USO_EM) if len(USO_EM) > 0 else 0    
    
    print('Chegadas: {0:d} {1:s}'.format(conta_chegada, entidade))
    print('Saidas:   {0:d} {1:s}'.format(conta_saida, entidade))
    print('WIP:      {0:d} {1:s}'.format(conta_chegada-conta_saida, entidade))
    print('NS: {0:.2f} {1:s}'.format(NS_i, entidade))
    print('NF: {0:.2f} {1:s}'.format(NF_i, entidade))
    print('NA: {0:.2f} {1:s}'.format(NA_i, entidade))
    print('TS: {0:.2f} {1:s}'.format(TS_i, tempo))
    print('TF: {0:.2f} {1:s}'.format(TF_i, tempo))
    print('TA: {0:.2f} {1:s}'.format(TA_i, tempo))
    print('USO-EM:{0:.2f}%'.format(USO_EM_i*100))        
    
    print("="*comprimento_linha, end="\n")   
    NS_bar.append(NS_i)
    NF_bar.append(NF_i)
    NA_bar.append(NA_i)
    TS_bar.append(TS_i)
    TF_bar.append(TF_i)
    TA_bar.append(TA_i)
    USO_EM_bar.append(USO_EM_i)
    

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
    
    entidade = "sondas"

    print('NS: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(NS_bar), calc_ic(NS), entidade))
    print('NF: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(NF_bar), calc_ic(NF), entidade))
    print('NA: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(NA_bar), calc_ic(NA), entidade))
    print('TS: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(TS_bar), calc_ic(TS), tempo))
    print('TF: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(TF_bar), calc_ic(TF), tempo))
    print('TA: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(TA_bar), calc_ic(TA), tempo))
    print('USO-EM:{0:.2f}% \u00B1 {1:.2f}%  (IC 95%)'.format(np.mean(USO_EM_bar)*100, calc_ic(USO_EM)*100))
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
        y = USO_EM                
        # usa a função plot
        plt.title('Indicador de Desempenho: \n\n' + \
        "Utilização média dos Recursos")
        plt.plot(xi, y, marker='o', linestyle='-', color='red', label='Equipe de Manutenção')
        plt.legend()
        plt.ylim(0.0,1.05)
        plt.xlim(0.0,duracao_da_simulacao)
        plt.xlabel('Tempo (horas)')
        plt.ylabel('Valor') 
        plt.show()
###################################################################


###################################################################
for i in range (1,n_replicacoes+1):
    # Re-inicializacao das estatísticas entre replicações
    conta_chegada = 0     
    conta_saida = 0    
    tempo_utilizacao_Recurso_Sondas = 0
    tempo_utilizacao_Recurso_Equipe_Mnt = 0

    env = simpy.Environment()
    sondas = simpy.Container(env)
    equipes_mnt = simpy.Container(env, CAP_EQUIPE_MNT, init=CAP_EQUIPE_MNT)    
    env.process(gera_sondas(env, "sonda", sondas, equipes_mnt))
    env.run(duracao_da_simulacao)
    computa_estatisticas(i, "horas")        

publica_estatisticas("horas")
###################################################################
