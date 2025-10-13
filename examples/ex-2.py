import simpy
import random
import numpy as np
import scipy
import matplotlib
import matplotlib.pyplot as plt

from random import (expovariate, triangular, gauss, uniform, randint, seed)
from scipy import stats

seed(123)
NS, NA, NF, TS, TA, TF, USO_G, USO_C = [], [], [], [], [], [], [], []

NS_bar, NF_bar, NA_bar, TS_bar, TF_bar, TA_bar =  [], [], [], [], [], []
USO_G_bar, USO_C_bar = [], []
T = [] 

momento_chegada, momento_saida, tempo_sistema, momento_entrada_fila = {}, {}, {}, {}
momento_saida_fila, tempo_fila, inicia_atendimento, finaliza_atendimento = {}, {}, {}, {}
duracao_atendimento, utilizacao = {}, {}

CAP_GARCONS, CAP_COPOS = 1, 70

n_replicacao, duracao_da_simulacao, tempo_aquecimento, imprime_detalhes = 5, 365*12*60, 30*12*60, False

def distribuicoes(tipo):
    taxa_chegadas, med_servir, std_servir = 1/10, 6/60, 1/60
    cte_lavar, min_beber, max_beber = 30/60, 5, 8
    return {
        'chegada': expovariate(taxa_chegadas),
        'servir': gauss(med_servir, std_servir),
        'lavar': cte_lavar,
        'beber': uniform(min_beber, max_beber)
    }.get(tipo,0.0)

def chegada(env, entidade, garcons, copos):
    global conta_chegada
    global conta_saida
    while True:
        yield env.timeout(distribuicoes('chegada'))
        conta_chegada+=1
        nome = entidade + " " + str(conta_chegada)
        sede = randint(1,4)
        momento_chegada[nome] = env.now
        if imprime_detalhes:
            print("{0:.2f}: {1:s} chega no bar com sede {2:d}".format(env.now, nome, sede))
        prio = 0
        env.process(servir(env, nome, prio, garcons, copos, sede))

def chegada_garcons(env, entidade, copos):
    conta_chegada = 0
    yield env.timeout(0)
    for i in range(1,2):
        conta_chegada+=1
        nome = entidade + " " + str(conta_chegada)
        env.process(lavar(env, nome, garcons, copos))

def lavar(env, nome, garcons, copos):
    prio = 1
    request1 = garcons.request(priority=prio)
    request2 = copos.request(priority=prio)
    yield request1
    yield request2
    inicia_utilizacao_Recurso = env.now
    if imprime_detalhes:
        print("{0:.2f}: Garcom lava copos".format(env.now))
    yield env.timeout(distribuicoes('lavar'))
    yield garcons.release(request1)
    yield copos.release(request2)
    if imprime_detalhes:
        print("{0:.2f}: Garcom acabou de limpar um copo".format(env.now))
    global tempo_utilizacao_Recurso_Garcom
    tempo_utilizacao_Recurso_Garcom += env.now - inicia_utilizacao_Recurso
    utilizacao['Garcons'] = tempo_utilizacao_Recurso_Garcom / (CAP_GARCONS*env.now)
    global tempo_utilizacao_Recurso_Copos
    tempo_utilizacao_Recurso_Copos += env.now - inicia_utilizacao_Recurso
    utilizacao['Copos'] = tempo_utilizacao_Recurso_Copos / (CAP_COPOS*env.now)
    env.process(lavar(env, nome, garcons, copos))

def servir(env, nome, prio, garcons, copos, sede):
    momento_entrada_fila[nome] = env.now
    request1=garcons.request(priority=prio)
    request2=copos.request(priority=prio)
    yield request1
    yield request2
    momento_saida_fila[nome] = env.now
    tempo_fila[nome] = momento_saida_fila[nome] - momento_entrada_fila[nome]
    if imprime_detalhes:
        print("{0:.2f}: Garcom inicia o atendimento do {1:s}. Numero de entidades em atendimento: {2:d}"
              .format(env.now, nome, garcons.count))
    inicia_atendimento[nome] = env.now
    inicia_utilizacao_Recurso = env.now
    yield env.timeout(distribuicoes('servir'))
    if imprime_detalhes:
        print("{0:.2f}: Garcom termina o atendimento do {1:s}. Numero de entidades em fila: {2:d}"
              .format(env.now, nome, len(garcons.queue)))
    finaliza_atendimento[nome] = env.now
    duracao_atendimento[nome] = finaliza_atendimento[nome] - inicia_atendimento[nome]
    yield garcons.release(request1)
    yield copos.release(request2)
    global tempo_utilizacao_Recurso_Garcom
    tempo_utilizacao_Recurso_Garcom += env.now - inicia_utilizacao_Recurso
    utilizacao['Garcons'] = tempo_utilizacao_Recurso_Garcom / (CAP_GARCONS*env.now)
    global tempo_utilizacao_Recurso_Copos
    tempo_utilizacao_Recurso_Copos += env.now - inicia_utilizacao_Recurso
    utilizacao['Copos'] = tempo_utilizacao_Recurso_Copos / (CAP_COPOS*env.now)
    env.process(beber(env, nome, copos, sede))

def beber(env, nome, copos, sede):
    prio = 0
    request2=copos.request(priority=prio)
    yield request2
    if imprime_detalhes:
        print("{0:.2f}: {1:s} comeca a beber. Sede: {2:d}".format(env.now, nome, sede))
    inicia_utilizacao_Recurso = env.now
    yield env.timeout(distribuicoes('beber'))
    yield copos.release(request2)
    global tempo_utilizacao_Recurso_Copos
    tempo_utilizacao_Recurso_Copos += env.now - inicia_utilizacao_Recurso
    utilizacao['Copos'] = tempo_utilizacao_Recurso_Copos / (CAP_COPOS*env.now)
    sede = sede - 1
    if imprime_detalhes:
        print("{0:.2f}: {1:s} termina de beber. Copos em uso: {2:d}. Sede: {3:d}".format(env.now, nome, copos.count, sede))

    satisfeito(env, nome, garcons, copos, sede)

def satisfeito(env, nome, garcons, copos, sede):
    if sede == 0:
        if imprime_detalhes:
            print("{0:.2f}: {1:s} Acabou a sede. {1:s} Vai embora".format(env.now, nome))
        coleta_dados_indicadores(env, nome, garcons)
    else:
        prio=0
        if imprime_detalhes:
            print("{0:.2f}: {1:s} tem sede {2:d} e quer ser servido novamente".format(env.now, nome, sede))
        env.process(servir(env, nome, prio, garcons, copos, sede))

def coleta_dados_indicadores(env, nome, garcons):    
    global conta_saida
    conta_saida += 1
    numero_sistema = conta_chegada - conta_saida 
    if env.now > tempo_aquecimento:
        NS.append(numero_sistema), NA.append(garcons.count), NF.append(len(garcons.queue))

    momento_saida[nome] = env.now            
    tempo_sistema[nome] = momento_saida[nome] - momento_chegada[nome]
    
    if env.now > tempo_aquecimento:
        TS.append(tempo_sistema[nome]), TA.append(duracao_atendimento[nome]), TF.append(tempo_fila[nome])
        USO_G.append(utilizacao['Garcons']), USO_C.append(utilizacao['Copos']),T.append(env.now)

def computa_estatisticas(replicacao, entidade, tempo):  
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
    USO_G_i= np.mean(USO_G) if len(USO_G) > 0 else 0
    USO_C_i= np.mean(USO_C) if len(USO_C) > 0 else 0     
    print('Chegadas: {0:d} {1:s}'.format(conta_chegada, entidade))
    print('Saidas:   {0:d} {1:s}'.format(conta_saida, entidade))
    print('WIP:      {0:d} {1:s}'.format(conta_chegada-conta_saida, entidade))
    print('NS: {0:.2f} {1:s}'.format(NS_i, entidade))
    print('NF: {0:.2f} {1:s}'.format(NF_i, entidade))
    print('NA: {0:.2f} {1:s}'.format(NA_i, entidade))
    print('TS: {0:.2f} {1:s}'.format(TS_i, tempo))
    print('TF: {0:.2f} {1:s}'.format(TF_i, tempo))
    print('TA: {0:.2f} {1:s}'.format(TA_i, tempo))
    print('USO-G:{0:.2f}%'.format(USO_G_i*100))
    print('USO-C:{0:.2f}%'.format(USO_C_i*100))    
    print("="*comprimento_linha, end="\n")   
    NS_bar.append(NS_i), NF_bar.append(NF_i), NA_bar.append(NA_i), TS_bar.append(TS_i)
    TF_bar.append(TF_i), TA_bar.append(TA_i), USO_G_bar.append(USO_G_i), USO_C_bar.append(USO_C_i)

def calc_ic(lista):
    if len(lista) <= 1:
        return 0
    else:
        confidence = 0.95
        n = len(lista)
        mean_se = stats.sem(lista)
        h = mean_se * stats.t.ppf((1 + confidence) / 2., n-1)
        return h

def publica_estatisticas(entidade,tempo):  
    print()
    comprimento_linha = 100
    print("="*comprimento_linha)   
    print("Indicadores de Desempenho do Sistema", end="\n")
    print("="*comprimento_linha)   
    
    print('NS: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(NS_bar), calc_ic(NS), entidade))
    print('NF: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(NF_bar), calc_ic(NF), entidade))
    print('NA: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(NA_bar), calc_ic(NA), entidade))
    print('TS: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(TS_bar), calc_ic(TS), tempo))
    print('TF: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(TF_bar), calc_ic(TF), tempo))
    print('TA: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(TA_bar), calc_ic(TA), tempo))
    print('USO-G:{0:.2f}% \u00B1 {1:.2f}%  (IC 95%)'.format(np.mean(USO_G_bar)*100, calc_ic(USO_G)*100))
    print('USO-C:{0:.2f}% \u00B1 {1:.2f}%  (IC 95%)'.format(np.mean(USO_C_bar)*100, calc_ic(USO_C)*100))
    print("="*comprimento_linha, end="\n") 

    if n_replicacoes == 1:
        matplotlib.rcParams['figure.figsize'] = (8.0, 6.0)
        matplotlib.style.use('ggplot')
        
        xi = T     
        y1 = USO_G
        y2 = USO_C        
        
        plt.title('Indicador de Desempenho: \n\n' + "Utilizacao media de garcons e dos " + str(CAP_COPOS) + " copos")
        plt.plot(xi, y1, marker='o', linestyle='-', color='r', label='Garcom')
        plt.plot(xi, y2, marker='o', linestyle='-', color='b', label='Copos')
        plt.legend()
        plt.ylim(0.0,1.1)
        plt.xlim(0.0,duracao_da_simulacao)
        plt.xlabel('Tempo (minutos)')
        plt.ylabel('Valor') 
        plt.show()

for i in range (1,n_replicacoes+1):

    conta_chegada = 0    
    conta_saida = 0
    tempo_utilizacao_Recurso_Copos = 0
    tempo_utilizacao_Recurso_Garcom = 0

    env = simpy.Environment()
    garcons = simpy.PriorityResource(env, capacity=CAP_GARCONS)
    copos = simpy.PriorityResource(env, capacity=CAP_COPOS)
    env.process(chegada(env, "cliente", garcons, copos))
    env.process(chegada_garcons(env, "garcom", copos))
    env.run(duracao_da_simulacao)
    computa_estatisticas(i, "clientes", "minutos")    

publica_estatisticas("clientes", "minutos")
