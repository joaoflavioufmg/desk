# -*- coding: utf-8 -*-
#!/usr/bin/python3

# Disciplina: EPD899: Simulacao de Sistemas Logísticos
# Prof: Joao Flavio F. Almeida <joao.flavio@dep.ufmg>
# Problemas de Simulação - Resolução em Simpy (python)

# ##################################################################
# Implementação computacional dos 10 exemplos das aulas
# ##################################################################

# ##################################################################
# Um porto de embarque de minério opera da seguinte forma: 
# Os navios chegam ao porto em intervalos de tempo que seguem uma 
# distribuição exponencial com média de 4.39 dias. A capacidade dos 
# navios varia da seguinte forma: 75% são de 100.000 t, 15% são de 
# 200.000 t e 10% de 150.000 t. Chegando ao porto, os navios encontrando 
# o pier vago ( o porto só possui 1 pier) e desde que haja minério 
# no estoque, começam a ser carregados a uma taxa de 1200 t/h. 
# Caso o estoque de minério termine antes do navio ser completamente 
# carregado, o navio aguardará no pier a chegada de minério, ou seja, 
# ele só deixa o pier quando estiver completamente carregado. 
# O minério chega ao porto via ferrovia, sendo que cada trem é composto 
# de 80 vagões com capacidade de 100 t cada um. Os trens chegam ao porto, 
# em média, a cada 7 horas, seguindo uma distribuição normal, com desvio 
# padrão de 1.07 hora. Os trens, chegando ao porto, têm seus vagões 
# descarregados um a um, por um único virador de vagões. O tempo de 
# descarga de cada vagão segue uma distribuição normal com média de 
# 2,5 minutos e desvio padrão de 0,3 minutos. Ao fim da descarga de 
# cada vagão, obviamente, o estoque de minério do porto aumenta em 
# 100 t. Posto isto, pede-se construir o diagrama de ciclo de 
# atividades para o sistema.  
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

# Navios (_N)
NS_N = []
NA_N = []
NF_N = []
TS_N = []
TA_N = []
TF_N = []
# Trens (_T)
NS_T = []
NA_T = []
NF_T = []
TS_T = []
TA_T = []
TF_T = []

USO_P= [] # Pier
USO_V= [] # Virador de Vagões

NS_N_bar = []
NF_N_bar = [] 
NA_N_bar = [] 
TS_N_bar = [] 
TF_N_bar = [] 
TA_N_bar = []

NS_T_bar = []
NF_T_bar = [] 
NA_T_bar = [] 
TS_T_bar = [] 
TF_T_bar = [] 
TA_T_bar = []

USO_P_bar= [] # Pier
USO_V_bar= [] # Virador de Vagões

TP = []  # Tempo dos Eventos Discretos: Pier
TV = []  # Tempo dos Eventos Discretos: Virador
TS = []  # Tempo dos Eventos Discretos: Variaveis do Sistema

conta_chegada_navio = 0
conta_chegada_trem = 0
conta_saida_navio = 0 
conta_saida_trem = 0 

tempo_utilizacao_Recurso_Pier = 0
tempo_utilizacao_Recurso_VV = 0

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


# Capacidade dos Recursos
CAP_PIER = 1
CAP_VIRADOR = 1

# Variáveis do sistema
volume_exportacao = 0
navio_cheio = 0

EM = [] # estoque de minério (estoqueMinerio.level)
EX = [] # exportações (cap_aux)
VEX = [] # volume de exportação (volume_exportacao)

EM_bar = [] # Media de estoque de minerio
EX_bar = [] # Media do volume exportado

###################################################################
# Configura a rodada de simulacao definindo o 
# numero de replicações e duração da simulação
###################################################################
# Teste
n_replicacoes = 1 
duracao_da_simulacao = 20
tempo_aquecimento = 0
imprime_detalhes = True
###################################################################
# # Simulação oficial
# n_replicacoes = 5
# duracao_da_simulacao =   24*365
# tempo_aquecimento = 24*30
# imprime_detalhes = False 
###################################################################

# Unidade básica para todos os tempos: hora

taxa_carga_navios = 1200 # toneladas por hora
carga_vagao       = 100  # toneladas por hora    

def distribuicoes(tipo):
    taxa_chegadas_navios = 1/(4.39*24)  # por hora    
    med_chegada_trem = 7            # horas
    std_chegada_trem = 1.07         # horas
    med_descarga_vagao = 2.5/60     # horas
    std_descarga_vagao = 0.3/60     # horas    
    
    return {
        'chegada_navio': expovariate(taxa_chegadas_navios),         # horas
        'chegada_trem': max(0, gauss(med_chegada_trem, std_chegada_trem)),  # horas
        'descarga_vagao': max(0, gauss(med_descarga_vagao, std_descarga_vagao)),  # horas
        'carrega_navio': carga_vagao/taxa_carga_navios              # horas        
    }.get(tipo,0.0)


def sorteia_capacidade_navio():
    sorteio = random()
    if sorteio <=.75:
        return 100000
    elif sorteio <= .90:
        return 200000
    else:
        return 150000


def chegada_navio(env, entidade, pier):
    global conta_chegada_navio
    
    while True:     # São infinitos navios
        # Delay
        yield env.timeout(distribuicoes('chegada_navio'))
        conta_chegada_navio +=1
        nome = entidade + " " + str(conta_chegada_navio)  
        momento_chegada[nome] = env.now        
        if imprime_detalhes:
            print("{0:.2f}: {1:s} chega no cáis. Navios atracados no Pier: {2:d}"
            .format(env.now, nome, pier.count))
        # chama o proximo "bloco"        
        env.process(atracar_e_carregar_navio(env, nome, pier))


def atracar_e_carregar_navio(env, nome, pier):
    global estoqueMinerio
    global carga_vagao  
    global navio_cheio

    capacidade_navio = sorteia_capacidade_navio()        
    cap_aux = capacidade_navio
    navio_cheio = capacidade_navio    

    momento_entrada_fila[nome] = env.now    

    # Seize, Delay, Release
    with pier.request() as req:
        # Seize
        yield req

        momento_saida_fila[nome] = env.now
        tempo_fila[nome] = momento_saida_fila[nome] - momento_entrada_fila[nome]

        inicia_atendimento[nome] = env.now
        inicia_utilizacao_Recurso = env.now    

        if imprime_detalhes:
            print("{0:.2f}: {1:s} atracado no pier!Hora de carregar! Estoque de minerio: {2:d}"
            .format(env.now, nome, estoqueMinerio.level)) 
        
        # Delay
        while capacidade_navio > 0:
            # carga_vagao = min(taxa_carga_navios,capacidade_navio)
            # Reduz ("get") o estoque de minério
            yield estoqueMinerio.get(carga_vagao)
            # Tempo de carregamento do navio ((100/1200)*60 = 5 min)
            yield env.timeout(distribuicoes('carrega_navio'))
            capacidade_navio -= carga_vagao

            if imprime_detalhes:
                print("{0:.2f}: {1:s} carregado com {2:d} toneladas de minério! Faltam {3:d} toneladas! Estoque de minerio: {4:d}"
                .format(env.now, nome, cap_aux - capacidade_navio, capacidade_navio, estoqueMinerio.level)) 
        
        # Release
        finaliza_atendimento[nome] = env.now        
        duracao_atendimento[nome] = finaliza_atendimento[nome] - inicia_atendimento[nome]
        
        if imprime_detalhes:    
            print("{0:.2f}: {1:s} foi carregado! Pier liberado!".format(env.now, nome)) 
        

        global tempo_utilizacao_Recurso_Pier
        tempo_utilizacao_Recurso_Pier += env.now - inicia_utilizacao_Recurso
        utilizacao['Pier'] = tempo_utilizacao_Recurso_Pier / (CAP_PIER*env.now)

        # chama o proximo "bloco" 
        coleta_indicadores_navio(env, nome, pier)
        coleta_indicadores_variaveis()     
   

def chegada_trem(env, entidade, virador):
    global conta_chegada_trem 

    while True:     # São infinitos trens
        # Delay
        yield env.timeout(distribuicoes('chegada_trem'))
        conta_chegada_trem +=1
        nome = entidade + " " + str(conta_chegada_trem)  
        momento_chegada[nome] = env.now        
        if imprime_detalhes:
            print("{0:.2f}: {1:s} chega no porto para descarregar! Vagões no Virador: {2:d}"
            .format(env.now, nome, virador.count))
        # chama o proximo "bloco"                
        env.process(descarregar_trem(env, nome, virador))


def descarregar_trem(env, nome, virador):
    global estoqueMinerio
    global carga_vagao
    vagoes_no_trem = 80

    momento_entrada_fila[nome] = env.now

    # Seize, Delay, Release
    with virador.request() as req:
        # Seize
        yield req

        momento_saida_fila[nome] = env.now
        tempo_fila[nome] = momento_saida_fila[nome] - momento_entrada_fila[nome]

        inicia_atendimento[nome] = env.now
        inicia_utilizacao_Recurso = env.now    

        if imprime_detalhes:
            print("{0:.2f}: {1:s} posicionado no Virador!Hora de descarregar! Estoque de minerio: {2:d}"
            .format(env.now, nome, estoqueMinerio.level))
        
        # Delay
        while vagoes_no_trem > 0:
            # Aumenta ("put") o minério no estoque
            yield estoqueMinerio.put(carga_vagao)
            # Tempo de descarga do vagão
            yield env.timeout(distribuicoes('descarga_vagao'))
            
            vagoes_no_trem -= 1
            if imprime_detalhes:
                print("{0:.2f}: {1:s} tem o vagão {2:d} descarregado. Vagões no Virador: {3:d}. Estoque de minerio: {4:d}"
                .format(env.now, nome, 80-vagoes_no_trem, virador.count, estoqueMinerio.level))
            
    # Release
    finaliza_atendimento[nome] = env.now        
    duracao_atendimento[nome] = finaliza_atendimento[nome] - inicia_atendimento[nome]

    if imprime_detalhes:
        print("{0:.2f}: {1:s} finalizou! Virador liberado! Vagões no Virador: {2:d}. Estoque de minerio: {3:d}"
        .format(env.now, nome, virador.count, estoqueMinerio.level))
    
    global tempo_utilizacao_Recurso_Virador
    tempo_utilizacao_Recurso_Virador += env.now - inicia_utilizacao_Recurso
    utilizacao['Virador'] = tempo_utilizacao_Recurso_Virador / (CAP_VIRADOR*env.now)

    # chama o proximo "bloco" 
    coleta_indicadores_virador(env, nome, virador)   
    coleta_indicadores_variaveis()


def coleta_indicadores_navio(env, nome, pier):    
    # libera o recurso Pier e sai do sistema    
    global conta_saida_navio
    conta_saida_navio += 1

    # Coleta dados para estatísticas        
    numero_sistema = conta_chegada_navio - conta_saida_navio 

    if env.now > tempo_aquecimento:
        NS_N.append(numero_sistema)
        NA_N.append(pier.count)
        NF_N.append(len(pier.queue))
    
    momento_saida[nome] = env.now            
    tempo_sistema[nome] = momento_saida[nome] - momento_chegada[nome]
    
    if env.now > tempo_aquecimento:
        TS_N.append(tempo_sistema[nome])
        TA_N.append(duracao_atendimento[nome])
        TF_N.append(tempo_fila[nome])
        USO_P.append(utilizacao['Pier'])        
        TP.append(env.now)


def coleta_indicadores_virador(env, nome, virador):    
    # libera o recurso Virador e sai do sistema    
    global conta_saida_trem
    conta_saida_trem += 1

    # Coleta dados para estatísticas        
    numero_sistema = conta_chegada_trem - conta_saida_trem 

    if env.now > tempo_aquecimento:
        NS_T.append(numero_sistema)
        NA_T.append(virador.count)
        NF_T.append(len(virador.queue))
    
    momento_saida[nome] = env.now            
    tempo_sistema[nome] = momento_saida[nome] - momento_chegada[nome]
    
    if env.now > tempo_aquecimento:
        TS_T.append(tempo_sistema[nome])
        TA_T.append(duracao_atendimento[nome])
        TF_T.append(tempo_fila[nome])        
        USO_V.append(utilizacao['Virador'])        
        TV.append(env.now)


def coleta_indicadores_variaveis():
    global estoqueMinerio
    global volume_exportacao    
    global navio_cheio 

    volume_exportacao += navio_cheio

    if env.now > tempo_aquecimento:        
        EM.append(estoqueMinerio.level)
        EX.append(navio_cheio)        
        navio_cheio = 0
        VEX.append(volume_exportacao)
        TS.append(env.now)  


def computa_estatisticas_navio(replicacao, tempo):  
    print()
    comprimento_linha = 100
    print("="*comprimento_linha)   
    print("Indicadores de Desempenho de Navios da Replicacao {0:d}".format(replicacao), end="\n")
    print("="*comprimento_linha)   
    
    entidade = "navios"
    
    NS_i = np.mean(NS_N)
    NF_i = np.mean(NF_N)
    NA_i = np.mean(NA_N)
    TS_i = np.mean(TS_N)
    TF_i = np.mean(TF_N)
    TA_i = np.mean(TA_N)
    USO_P_i= np.mean(USO_P) if len(USO_P) > 0 else 0    
    EX_i= np.mean(VEX) if len(VEX) > 0 else 0    
    print('Chegadas: {0:d} {1:s}'.format(conta_chegada_navio, entidade))
    print('Saidas:   {0:d} {1:s}'.format(conta_saida_navio, entidade))
    print('WIP:      {0:d} {1:s}'.format(conta_chegada_navio-conta_saida_navio, entidade))
    print('NS: {0:.2f} {1:s}'.format(NS_i, entidade))
    print('NF: {0:.2f} {1:s}'.format(NF_i, entidade))
    print('NA: {0:.2f} {1:s}'.format(NA_i, entidade))
    print('TS: {0:.2f} {1:s}'.format(TS_i, tempo))
    print('TF: {0:.2f} {1:s}'.format(TF_i, tempo))
    print('TA: {0:.2f} {1:s}'.format(TA_i, tempo))
    print('USO-P:{0:.2f}%'.format(USO_P_i*100))    
    print('Exportação de minério: {0:.2f} Mt'.format(volume_exportacao/1000000))
    
    print("="*comprimento_linha, end="\n")   
    NS_N_bar.append(NS_i)
    NF_N_bar.append(NF_i)
    NA_N_bar.append(NA_i)
    TS_N_bar.append(TS_i)
    TF_N_bar.append(TF_i)
    TA_N_bar.append(TA_i)
    USO_P_bar.append(USO_P_i)
    EX_bar.append(EX_i) 
    

def computa_estatisticas_trem(replicacao, tempo):  
    print()
    comprimento_linha = 100
    print("="*comprimento_linha)   
    print("Indicadores de Desempenho de Trens da Replicacao {0:d}".format(replicacao), end="\n")
    print("="*comprimento_linha)   
    
    entidade = "trens"
    
    NS_i = np.mean(NS_T)
    NF_i = np.mean(NF_T)
    NA_i = np.mean(NA_T)
    TS_i = np.mean(TS_T)
    TF_i = np.mean(TF_T)
    TA_i = np.mean(TA_T)
    USO_V_i= np.mean(USO_V) if len(USO_V) > 0 else 0    
    EM_i= np.mean(EM) if len(EM) > 0 else 0    
    print('Chegadas: {0:d} {1:s}'.format(conta_chegada_trem, entidade))
    print('Saidas:   {0:d} {1:s}'.format(conta_saida_trem, entidade))
    print('WIP:      {0:d} {1:s}'.format(conta_chegada_trem-conta_saida_trem, entidade))
    print('NS: {0:.2f} {1:s}'.format(NS_i, entidade))
    print('NF: {0:.2f} {1:s}'.format(NF_i, entidade))
    print('NA: {0:.2f} {1:s}'.format(NA_i, entidade))
    print('TS: {0:.2f} {1:s}'.format(TS_i, tempo))
    print('TF: {0:.2f} {1:s}'.format(TF_i, tempo))
    print('TA: {0:.2f} {1:s}'.format(TA_i, tempo))
    print('USO-V:{0:.2f}%'.format(USO_V_i*100))
    print('Estoque de minério: Min: {0:.2f} t\tMed: {1:.2f} t\tMax: {2:.2f} t'
    .format(np.min(EM), np.mean(EM), np.max(EM)))
    
    print("="*comprimento_linha, end="\n")   
    NS_T_bar.append(NS_i)
    NF_T_bar.append(NF_i)
    NA_T_bar.append(NA_i)
    TS_T_bar.append(TS_i)
    TF_T_bar.append(TF_i)
    TA_T_bar.append(TA_i)
    USO_V_bar.append(USO_V_i)
    EM_bar.append(EM_i)


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
    print("Indicadores de Desempenho do Sistema de Navios", end="\n")
    print("="*comprimento_linha)   
    
    entidade = "navios"
    print('NS: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(NS_N_bar), calc_ic(NS_N), entidade))
    print('NF: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(NF_N_bar), calc_ic(NF_N), entidade))
    print('NA: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(NA_N_bar), calc_ic(NA_N), entidade))
    print('TS: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(TS_N_bar), calc_ic(TS_N), tempo))
    print('TF: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(TF_N_bar), calc_ic(TF_N), tempo))
    print('TA: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(TA_N_bar), calc_ic(TA_N), tempo))
    print('USO-P:{0:.2f}% \u00B1 {1:.2f}%  (IC 95%)'.format(np.mean(USO_P_bar)*100, calc_ic(USO_P)*100))
    print("="*comprimento_linha, end="\n") 

    print("="*comprimento_linha)   
    print("Indicadores de Desempenho do Sistema de Trens", end="\n")
    print("="*comprimento_linha) 

    entidade = "trens"      
    print('NS: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(NS_T_bar), calc_ic(NS_T), entidade))
    print('NF: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(NF_T_bar), calc_ic(NF_T), entidade))
    print('NA: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(NA_T_bar), calc_ic(NA_T), entidade))
    print('TS: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(TS_T_bar), calc_ic(TS_T), tempo))
    print('TF: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(TF_T_bar), calc_ic(TF_T), tempo))
    print('TA: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(TA_T_bar), calc_ic(TA_T), tempo))
    print('USO-V:{0:.2f}% \u00B1 {1:.2f}%  (IC 95%)'.format(np.mean(USO_V_bar)*100, calc_ic(USO_V)*100))
    print("="*comprimento_linha, end="\n") 
    print('Estoque de minério: {0:.2f} \u00B1 {1:.2f} t (IC 95%)'.format(np.mean(EM_bar), calc_ic(EM)))
    print('Exportação de minério: {0:.2f} \u00B1 {1:.2f} Mt (IC 95%)'
    .format(np.mean(EX_bar)/1000000, calc_ic(EX)/1000000))
    print("="*comprimento_linha, end="\n") 
    

    ###################################################################
    # Gera gráfico de Warm-up
    ###################################################################
    if n_replicacoes == 1:
        matplotlib.rcParams['figure.figsize'] = (8.0, 6.0)
        matplotlib.style.use('ggplot')
        # Dados
        xi = TP     
        y = USO_P        
        # y2 = USO_V
        # usa a função plot
        plt.title('Indicador de Desempenho: \n\n' + \
        "Utilização média do Pier")
        plt.plot(xi, y, marker='o', linestyle='-', color='r', label='Pier')        
        plt.legend()
        plt.ylim(0.0,1.05)
        plt.xlim(0.0,duracao_da_simulacao)
        plt.xlabel('Tempo (horas)')
        plt.ylabel('Valor') 
        plt.show()

        # Dados
        xi = TV     
        y = USO_V
        plt.title('Indicador de Desempenho: \n\n' + \
        "Utilização média do Virador")
        plt.plot(xi, y, marker='o', linestyle='-', color='b', label='Virador')        
        plt.legend()
        plt.ylim(0.0,1.05)
        plt.xlim(0.0,duracao_da_simulacao)
        plt.xlabel('Tempo (horas)')
        plt.ylabel('Valor') 
        plt.show()

        # Dados
        xi = TS     
        y1 = EM
        y2 = EX
        plt.title('Indicadores de Desempenho: \n\n' + \
        "Estoque de minerio e Exportação")
        plt.plot(xi, y1, marker='o', linestyle='-', color='b', label='Estoque de minerio')        
        plt.plot(xi, y2, marker='o', linestyle='-', color='r', label='Exportação')        
        plt.legend()
        # plt.ylim(0.0,1.05)
        plt.xlim(0.0,duracao_da_simulacao)
        plt.xlabel('Tempo (horas)')
        plt.ylabel('Valor') 
        plt.show()
    ###################################################################


###################################################################
for i in range (1,n_replicacoes+1):
    # Re-inicializacao das estatísticas entre replicações
    conta_chegada_navio = 0    
    conta_chegada_trem = 0    
    conta_saida_navio = 0
    conta_saida_trem = 0
    tempo_utilizacao_Recurso_Pier = 0
    tempo_utilizacao_Recurso_Virador = 0
    volume_exportacao = 0
    navio_cheio = 0    

    env = simpy.Environment()
    pier = simpy.Resource(env, capacity=CAP_PIER)
    virador = simpy.Resource(env, capacity=CAP_VIRADOR)
    estoqueMinerio = simpy.Container(env)
    env.process(chegada_navio(env, "navio", pier))
    env.process(chegada_trem(env, "trem", virador))
    env.run(duracao_da_simulacao)
    computa_estatisticas_navio(i, "horas")        
    computa_estatisticas_trem(i, "horas")        

publica_estatisticas("horas")
###################################################################