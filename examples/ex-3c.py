# -*- coding: utf-8 -*-
#!/usr/bin/python3

# Disciplina: EPD899: Simulacao de Sistemas Logísticos
# Prof: Joao Flavio F. Almeida <joao.flavio@dep.ufmg>
# Problemas de Simulação - Resolução em Simpy (python)

# ##################################################################
# Implementação computacional dos 10 exemplos das aulas
# ##################################################################

# ##################################################################
# Considere o exemplo anterior (3b) da central telefônica.
# Refaça o problema anterior supondo que uma chamada, encontrando o 
# sistema congestionado (todos os troncos ocupados), é direcionada 
# para uma central auxiliar com outros 10 troncos de capacidade. 
# Caso a central auxiliar também esteja congestionada, a chamada 
# será perdida (não há retorno neste caso).
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

from random import expovariate, seed, random
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
USO=[]
USO_AD=[]
Perc_perdidas = []

NS_bar = []
NF_bar = [] 
NA_bar = [] 
TS_bar = [] 
TF_bar = [] 
TA_bar = []
USO_bar=[]
USO_AD_bar=[]
PER_bar= []

T = []  # Tempo dos Eventos Discretos

conta_chegada = 0
conta_saida = 0 
conta_perdida = 0
tempo_utilizacao_Recurso = 0
tempo_utilizacao_Recurso_Ad = 0

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

CAP_TRONCOS = 30
CAP_TRONCOS_AD = 10

###################################################################
# Configura a rodada de simulacao definindo o 
# numero de replicações e duração da simulação
###################################################################
# # Teste
# n_replicacoes = 1 
# duracao_da_simulacao = 1000
# tempo_aquecimento = 0
# imprime_detalhes = True 

###################################################################
# Simulação oficial
n_replicacoes = 1
duracao_da_simulacao =   3600*24*30 
tempo_aquecimento = 36000
imprime_detalhes = False 
###################################################################

# Unidade básica para todos os tempos: segundos
def distribuicoes(tipo):
    taxa_chegadas=1/4       # por segundo
    taxa_atendimento=1/120  # por segundo
    return {
        'chegada': expovariate(taxa_chegadas),
        'atendimento': expovariate(taxa_atendimento)        
    }.get(tipo,0.0)


def coleta_dados_indicadores(env, nome, troncos):
    # libera o recurso Tronco e sai do sistema    
    global conta_saida
    conta_saida += 1

    numero_sistema = conta_chegada - conta_saida 

    if env.now > tempo_aquecimento:
        NS.append(numero_sistema)
        NA.append(troncos.count)
        NF.append(len(troncos.queue))
    
    momento_saida[nome] = env.now            
    tempo_sistema[nome] = momento_saida[nome] - momento_chegada[nome]
    
    if env.now > tempo_aquecimento:
        TS.append(tempo_sistema[nome])
        TA.append(duracao_atendimento[nome])
        TF.append(tempo_fila[nome])


def tem_tronco(nome, troncos, troncos_ad):
    if troncos.count < CAP_TRONCOS:
        if imprime_detalhes:
            print("{0:.2f}: Atendimento da {1:s} iniciada".format(env.now, nome)) 
        env.process(atendimento(env, nome, troncos))
    elif troncos_ad.count < CAP_TRONCOS_AD:
        if imprime_detalhes:
            print("{0:.2f}: Atendimento da {1:s} iniciada em Troncos Adicionais".format(env.now, nome)) 
        env.process(atendimento_ad(env, nome, troncos_ad))
    else:
        global conta_perdida
        global conta_saida
        conta_perdida+=1
        conta_saida+=1
        if imprime_detalhes:
            print("{0:.2f}: {1:s} perdida! Quantidade perdida: {2:d}".format(env.now, nome, conta_perdida)) 
        if env.now > tempo_aquecimento:
            # Calcula perdidas
            Perc_perdidas.append(conta_perdida/conta_chegada)
            T.append(env.now)


def chegada (env, entidade, troncos, troncos_ad):
    # gera chamadas exponencialmente distribuídas
    global conta_chegada    

    while True:
        yield env.timeout(distribuicoes('chegada'))
        conta_chegada+=1
        nome = entidade + " " + str(conta_chegada)        
        momento_chegada[nome] = env.now        
        if imprime_detalhes:
            print("{0:.2f}: {1:s} chega na Central Telefonica".format(env.now, nome))
        # chama o proximo "bloco"        
        tem_tronco(nome, troncos, troncos_ad)


def atendimento (env, nome, troncos):

    momento_entrada_fila[nome] = env.now        
    # Requer uso de um slot do Recurso
    request=troncos.request()
    # Seize, Delay, Release
    yield request   
    momento_saida_fila[nome] = env.now
    tempo_fila[nome] = momento_saida_fila[nome] - momento_entrada_fila[nome] 
    if imprime_detalhes:
        print("{0:.2f}: Servidor inicia o atendimento da {1:s}. Número de entidades em atendimento: {2:d}"
        .format(env.now, nome, troncos.count))
   
    inicia_atendimento[nome] = env.now
    inicia_utilizacao_Recurso = env.now
    yield env.timeout(distribuicoes('atendimento'))    
    if imprime_detalhes:
        print("{0:.2f}: Servidor termina o atendimento da {1:s}. Número de entidades em fila: {2:d}"
        .format(env.now, nome, len(troncos.queue)))
    finaliza_atendimento[nome] = env.now        
    duracao_atendimento[nome] = finaliza_atendimento[nome] - inicia_atendimento[nome]        
    yield troncos.release(request)
   
    global tempo_utilizacao_Recurso
    tempo_utilizacao_Recurso += env.now - inicia_utilizacao_Recurso
    utilizacao['Troncos'] = tempo_utilizacao_Recurso / (CAP_TRONCOS*env.now)  
    USO.append(utilizacao['Troncos'])        

    coleta_dados_indicadores(env, nome, troncos)


def atendimento_ad (env, nome, troncos):

    momento_entrada_fila[nome] = env.now        
    # Requer uso de um slot do Recurso
    request=troncos.request()
    # Seize, Delay, Release
    yield request   
    momento_saida_fila[nome] = env.now
    tempo_fila[nome] = momento_saida_fila[nome] - momento_entrada_fila[nome] 
    if imprime_detalhes:
        print("{0:.2f}: Servidor inicia o atendimento da {1:s}. Número de entidades em atendimento: {2:d}"
        .format(env.now, nome, troncos.count))
   
    inicia_atendimento[nome] = env.now
    inicia_utilizacao_Recurso_Ad = env.now
    yield env.timeout(distribuicoes('atendimento'))    
    if imprime_detalhes:
        print("{0:.2f}: Servidor termina o atendimento da {1:s}. Número de entidades em fila: {2:d}"
        .format(env.now, nome, len(troncos.queue)))
    finaliza_atendimento[nome] = env.now        
    duracao_atendimento[nome] = finaliza_atendimento[nome] - inicia_atendimento[nome]        
    yield troncos.release(request)

    global tempo_utilizacao_Recurso_Ad
    tempo_utilizacao_Recurso_Ad += env.now - inicia_utilizacao_Recurso_Ad
    utilizacao['Troncos_Ad'] = tempo_utilizacao_Recurso_Ad / (CAP_TRONCOS_AD*env.now)
    USO_AD.append(utilizacao['Troncos_Ad'])  

    coleta_dados_indicadores(env, nome, troncos)


def computa_estatisticas(replicacao):  
    print()
    comprimento_linha = 100
    print("="*comprimento_linha)   
    print("Indicadores de Desempenho da Replicacao {0:d}".format(replicacao), end="\n")
    print("="*comprimento_linha)   
    NS_i = np.mean(NS)
    NF_i = np.mean(NF)
    NA_i = np.mean(NA)
    TS_i = np.mean(TS)
    TF_i = np.mean(TF)
    TA_i = np.mean(TA)
    USO_i= np.mean(USO)
    USO_AD_i= np.mean(USO_AD)
    PER_i = np.mean(Perc_perdidas) if conta_perdida > 0 else 0
    print('Chegadas: {0:d} chamadas'.format(conta_chegada))
    print('Saidas:   {0:d} chamadas'.format(conta_saida))
    print('WIP:      {0:d} chamadas'.format(conta_chegada-conta_saida))
    print('NS: {0:.2f} chamadas'.format(NS_i))
    print('NF: {0:.2f} chamadas'.format(NF_i))
    print('NA: {0:.2f} chamadas'.format(NA_i))
    print('TS: {0:.2f} segundos'.format(TS_i))
    print('TF: {0:.2f} segundos'.format(TF_i))
    print('TA: {0:.2f} segundos'.format(TA_i))
    print('USO:{0:.2f}%'.format(USO_i*100))
    print('USO_AD:{0:.2f}%'.format(USO_AD_i*100))
    print('Chamadas Perdidas:{0:.2f}%'.format(PER_i*100))
    print("="*comprimento_linha, end="\n")   
    NS_bar.append(NS_i)
    NF_bar.append(NF_i)
    NA_bar.append(NA_i)
    TS_bar.append(TS_i)
    TF_bar.append(TF_i)
    TA_bar.append(TA_i)
    USO_bar.append(USO_i)
    USO_AD_bar.append(USO_AD_i)
    PER_bar.append(PER_i)


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

def publica_estatisticas():  
    print()
    comprimento_linha = 100
    print("="*comprimento_linha)   
    print("Indicadores de Desempenho do Sistema", end="\n")
    print("="*comprimento_linha)     
    
    print('NS: {0:.2f} \u00B1 {1:.2f} chamadas (IC 95%)'.format(np.mean(NS_bar), calc_ic(NS)))
    print('NF: {0:.2f} \u00B1 {1:.2f} chamadas (IC 95%)'.format(np.mean(NF_bar), calc_ic(NF)))
    print('NA: {0:.2f} \u00B1 {1:.2f} chamadas (IC 95%)'.format(np.mean(NA_bar), calc_ic(NA)))
    print('TS: {0:.2f} \u00B1 {1:.2f} segundos (IC 95%)'.format(np.mean(TS_bar), calc_ic(TS)))
    print('TF: {0:.2f} \u00B1 {1:.2f} segundos (IC 95%)'.format(np.mean(TF_bar), calc_ic(TF)))
    print('TA: {0:.2f} \u00B1 {1:.2f} segundos (IC 95%)'.format(np.mean(TA_bar), calc_ic(TA)))
    print('USO:{0:.2f}% \u00B1 {1:.2f}%  (IC 95%)'.format(np.mean(USO_bar)*100, calc_ic(USO)*100))
    print('USO_AD:{0:.2f}% \u00B1 {1:.2f}%  (IC 95%)'.format(np.mean(USO_AD_bar)*100, calc_ic(USO_AD)*100))
    print('Chamadas Perdidas:{0:.2f}% \u00B1 {1:.2f}% (IC 95%)'.format(np.mean(PER_bar)*100, calc_ic(Perc_perdidas)*100))
    print("="*comprimento_linha, end="\n") 

    ###################################################################
    # Gera gráfico de Warm-up
    ###################################################################
    if n_replicacoes == 1:
        matplotlib.rcParams['figure.figsize'] = (8.0, 6.0)
        matplotlib.style.use('ggplot')
        # cria os dados
        xi = T     
        y = Perc_perdidas        
        # usa a função plot
        plt.title('Indicador de Desempenho: \n\n' \
        + "Percentual de chamadas perdidas ( " + str(CAP_TRONCOS) + \
        " + " + str(CAP_TRONCOS_AD) + " troncos )")
        plt.plot(xi, y, marker='o', linestyle='-', color='b', label='Troncos')
        plt.legend()
        plt.ylim(0.0,0.5)
        plt.xlim(0.0,duracao_da_simulacao)
        plt.xlabel('Tempo (segundos)')
        plt.ylabel('Valor') 
        plt.show()
    ###################################################################


###################################################################
for i in range (1,n_replicacoes+1):
    # Re-inicializacao das estatísticas entre replicações
    conta_chegada = 0
    conta_perdida = 0
    conta_saida = 0    
    tempo_utilizacao_Recurso = 0

    env = simpy.Environment()
    troncos = simpy.Resource(env, capacity=CAP_TRONCOS)
    troncos_ad = simpy.Resource(env, capacity=CAP_TRONCOS_AD)
    env.process(chegada(env, "chamada", troncos, troncos_ad))
    env.run(duracao_da_simulacao)
    computa_estatisticas(i)    

publica_estatisticas()
###################################################################
