# -*- coding: utf-8 -*-
#!/usr/bin/python3

# Disciplina: EPD899: Simulacao de Sistemas Logísticos
# Prof: Joao Flavio F. Almeida <joao.flavio@dep.ufmg>
# Problemas de Simulação - Resolução em Simpy (python)

# ##################################################################
# Implementação computacional dos 10 exemplos das aulas
# ##################################################################

# ##################################################################
# Uma oficina de automóveis realiza serviços de manutenção mecânica, 
# manutenção elétrica e lanternagem. Para tanto, esta oficina conta 
# com 4 equipes, duas para manutenção mecânica, uma para manutenção 
# elétrica e uma para lanternagem. Os carros, ao chegarem na oficina, 
# passam por uma triagem inicial, realizada por um único funcionário, 
# e são encaminhados para realização dos serviços, sendo que 45% deles 
# necessitam de manutenção mecânica, 25% de manutenção elétrica, 18% 
# de lanternagem e 12% de manutenção mecânica e lanternagem. Os carros 
# que necessitam de lanternagem e manutenção mecânica (12%) são atendidos
# primeiramente no serviço que apresentar a menor fila de espera e após
# sua realização são, então, encaminhados ao outro serviço, tendo 
# prioridade de atendimento sobre os veículos que porventura estiverem 
# na fila de espera para realização daquele serviço. O intervalo entre 
# chegadas de carros segue uma distribuição exponencial negativa com 
# média de 2h. O tempo de triagem segue uma distribuição normal com 
# média de 0,17 h e desvio padrão de 0,02 h. O tempo de manutenção 
# mecânica segue uma distribuição exponencial negativa com média de 
# 3,8h. O tempo de manutenção elétrica segue uma distribuição 
# exponencial negativa com média de 2.5 h. O tempo de lanternagem 
# segue uma distribuição exponencial negativa com média de 5 h.
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
USO_T=[]
USO_E=[]
USO_M=[]
USO_L=[]

NS_bar = []
NF_bar = [] 
NA_bar = [] 
TS_bar = [] 
TF_bar = [] 
TA_bar = []
USO_T_bar=[]
USO_E_bar=[]
USO_M_bar=[]
USO_L_bar=[]

T = []  # Tempo dos Eventos Discretos

conta_chegada = 0
conta_saida = 0 

tempo_utilizacao_Recurso_Triagem = 0
tempo_utilizacao_Recurso_Mecanica = 0
tempo_utilizacao_Recurso_Eletrica = 0
tempo_utilizacao_Recurso_Lanternagem = 0

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

utilizacao['Triagem'] = 0
utilizacao['Eletrica'] = 0
utilizacao['Mecanica'] = 0
utilizacao['Lanternagem'] = 0

CAP_TRIAGEM = 1
CAP_MECANICA = 2
CAP_ELETRICA = 1
CAP_LANTERNAGEM = 1

###################################################################
# Configura a rodada de simulacao definindo o 
# numero de replicações e duração da simulação
###################################################################
# # Teste
# n_replicacoes = 1 
# duracao_da_simulacao = 1000
# tempo_aquecimento = 200
# imprime_detalhes = True 
###################################################################
# Simulação oficial
n_replicacoes = 5
duracao_da_simulacao =  365*8
tempo_aquecimento = 30*8
imprime_detalhes = False 
###################################################################

# Unidade básica para todos os tempos: horas

def distribuicao(tipo):
    taxa_chegadas = 1/2 # por hora
    med_triagem = 0.17  # horas
    std_triagem = 0.02  # horas
    taxa_mnt_mecanica = 1/3.8 # por hora
    taxa_mnt_eletrica = 1/2.5 # por hora
    taxa_lanternagem = 1/5    # por hora
    return {
        'chegada': expovariate(taxa_chegadas),      # horas
        'triagem': max(0, gauss(med_triagem,std_triagem)),   # horas
        'mnt_mecanica': expovariate(taxa_mnt_mecanica), # horas
        'mnt_eletrica': expovariate(taxa_mnt_eletrica), # horas
        'lanternagem':  expovariate(taxa_lanternagem),  # horas 
    }.get(tipo,0.0)


def sorteia_servico():
    servico = random()
    if servico <   0.45:   # mecanica
        return 1
    elif servico < 0.70: # eletrica
        return 2
    elif servico < 0.88: # lanternagem
        return 3
    else:                # mecanica e lanternagem
        return 4

def chegada_carro(env, entidade):
    global conta_chegada

    while True:
        yield env.timeout(distribuicao('chegada'))
        conta_chegada+=1
        nome = entidade + " " + str(conta_chegada)        
        momento_chegada[nome] = env.now        
        if imprime_detalhes:
            print("{0:.2f}: {1:s} chega na oficina de carros".format(env.now, nome))
        
        # chama o proximo "bloco"  
        env.process(triagem(env, nome))


def triagem(env, nome):
    global equipe_triagem, equipe_lanternagem, equipe_mnt_mec
    momento_entrada_fila[nome] = env.now            
    # Seize, Delay, Release 
    with equipe_triagem.request() as req:
        # Seize
        yield req
        momento_saida_fila[nome] = env.now
        tempo_fila[nome] = momento_saida_fila[nome] - momento_entrada_fila[nome] 
        if env.now > tempo_aquecimento:
            TF.append(tempo_fila[nome])
        if imprime_detalhes:
            print("{0:.2f}: Funcionário da triagem recebe o {1:s}. Entidades em atendimento: {2:d}"
            .format(env.now, nome, equipe_triagem.count))
        
        inicia_atendimento[nome] = env.now
        inicia_utilizacao_Recurso = env.now        
        yield env.timeout(distribuicao('triagem'))
        if imprime_detalhes:
            print("{0:.2f}: Funcionário da triagem termina avaliação do {1:s}. Entidades em fila: {2:d}"
            .format(env.now, nome, len(equipe_triagem.queue)))
        
        finaliza_atendimento[nome] = env.now        
        duracao_atendimento[nome] = finaliza_atendimento[nome] - inicia_atendimento[nome]
        if env.now > tempo_aquecimento:
            TA.append(duracao_atendimento[nome])
    # Release
    prio  =1
    n_serv=1

    global tempo_utilizacao_Recurso_Triagem
    tempo_utilizacao_Recurso_Triagem += env.now - inicia_utilizacao_Recurso
    utilizacao['Triagem'] = tempo_utilizacao_Recurso_Triagem / (CAP_TRIAGEM*env.now) 
    
    servico = sorteia_servico()

    if servico == 1:
        # chama o proximo "bloco"
        env.process(Mnt_mecanica(env, nome, prio, n_serv))
    elif servico == 2:
        # chama o proximo "bloco"
        env.process(Mnt_eletrica(env, nome, prio, n_serv))
    elif servico == 3:
        # chama o proximo "bloco"
        env.process(Lanternagem(env, nome, prio, n_serv))
    else:
        n_serv = 2
        if len(equipe_mnt_mec.queue) <= len(equipe_lanternagem.queue):
            # chama o proximo "bloco"            
            env.process(Mnt_mecanica(env, nome, prio, n_serv))            
        else:
            # chama o proximo "bloco"
            env.process(Lanternagem(env, nome, prio, n_serv))
            

def Mnt_mecanica(env, nome, prio, n_serv):
    global equipe_mnt_mec
    momento_entrada_fila[nome] = env.now            
    # Seize, Delay, Release 
    with equipe_mnt_mec.request(priority=prio) as req:
        # Seize
        yield req
        momento_saida_fila[nome] = env.now
        tempo_fila[nome] = momento_saida_fila[nome] - momento_entrada_fila[nome] 
        if env.now > tempo_aquecimento:
            TF.append(tempo_fila[nome])
        if imprime_detalhes:
            if prio == 0:
                print("{0:.2f}: >>> {1:s} tem prioridade!".format(env.now, nome))
            print("{0:.2f}: Equipe Mnt Mecânica inicia o conserto do {1:s}. Entidades em atendimento: {2:d}"
            .format(env.now, nome, equipe_mnt_mec.count))
        
        inicia_atendimento[nome] = env.now
        inicia_utilizacao_Recurso = env.now
        # Delay                   
        yield env.timeout(distribuicao('mnt_mecanica'))
        if imprime_detalhes:
            print("{0:.2f}: Equipe Mnt Mecânica termina o conserto do {1:s}.  Entidades em fila: {2:d}"
            .format(env.now, nome, len(equipe_mnt_mec.queue)))
        
        finaliza_atendimento[nome] = env.now        
        duracao_atendimento[nome] = finaliza_atendimento[nome] - inicia_atendimento[nome]
        if env.now > tempo_aquecimento:
            TA.append(duracao_atendimento[nome])
    # Release
        
    global tempo_utilizacao_Recurso_Mecanica
    tempo_utilizacao_Recurso_Mecanica += env.now - inicia_utilizacao_Recurso
    utilizacao['Mecanica'] = tempo_utilizacao_Recurso_Mecanica / (CAP_MECANICA*env.now)  

    if n_serv == 2:
        n_serv -=1
        prio=0
        # chama o proximo "bloco"
        env.process(Lanternagem(env, nome, prio, n_serv))
    else:
        # chama o proximo "bloco"
        coleta_dados_indicadores(env, nome)


def Mnt_eletrica(env, nome, prio, n_serv):
    global equipe_mnt_ele
    momento_entrada_fila[nome] = env.now            
    # Seize, Delay, Release 
    with equipe_mnt_ele.request() as req:
        # Seize
        yield req
        momento_saida_fila[nome] = env.now
        tempo_fila[nome] = momento_saida_fila[nome] - momento_entrada_fila[nome] 
        if env.now > tempo_aquecimento:
            TF.append(tempo_fila[nome])
        if imprime_detalhes:
            print("{0:.2f}: Equipe Mnt Elétrica inicia o conserto do {1:s}. Entidades em atendimento: {2:d}"
            .format(env.now, nome, equipe_mnt_ele.count))
        
        inicia_atendimento[nome] = env.now
        inicia_utilizacao_Recurso = env.now
        # Delay
        yield env.timeout(distribuicao('mnt_eletrica'))
        if imprime_detalhes:
            print("{0:.2f}: Equipe Mnt Elétrica termina o conserto do {1:s}.  Entidades em fila: {2:d}"
            .format(env.now, nome, len(equipe_mnt_ele.queue)))
        
        finaliza_atendimento[nome] = env.now        
        duracao_atendimento[nome] = finaliza_atendimento[nome] - inicia_atendimento[nome]
        if env.now > tempo_aquecimento:
            TA.append(duracao_atendimento[nome])
    # Release
        
    global tempo_utilizacao_Recurso_Eletrica
    tempo_utilizacao_Recurso_Eletrica += env.now - inicia_utilizacao_Recurso
    utilizacao['Eletrica'] = tempo_utilizacao_Recurso_Eletrica / (CAP_ELETRICA*env.now)  

    # chama o proximo "bloco"
    coleta_dados_indicadores(env, nome)


def Lanternagem(env, nome, prio, n_serv): #Mesmo que Mnt_mecanica
    global equipe_lanternagem
    momento_entrada_fila[nome] = env.now            
    # Seize, Delay, Release 
    with equipe_lanternagem.request(priority=prio) as req:
        # Seize
        yield req
        momento_saida_fila[nome] = env.now
        tempo_fila[nome] = momento_saida_fila[nome] - momento_entrada_fila[nome] 
        if env.now > tempo_aquecimento:
            TF.append(tempo_fila[nome])
        if imprime_detalhes:
            if prio == 0:
                print("{0:.2f}: >>> {1:s} tem prioridade!".format(env.now, nome))
            print("{0:.2f}: Equipe Lanternagem inicia o conserto do {1:s}. Entidades em atendimento: {2:d}"
            .format(env.now, nome, equipe_lanternagem.count))
        
        inicia_atendimento[nome] = env.now
        inicia_utilizacao_Recurso = env.now
        # Delay
        yield env.timeout(distribuicao('lanternagem'))
        if imprime_detalhes:
            print("{0:.2f}: Equipe Lanternagem termina o conserto do {1:s}.  Entidades em fila: {2:d}"
            .format(env.now, nome, len(equipe_lanternagem.queue)))
        
        finaliza_atendimento[nome] = env.now        
        duracao_atendimento[nome] = finaliza_atendimento[nome] - inicia_atendimento[nome]
        if env.now > tempo_aquecimento:
            TA.append(duracao_atendimento[nome])
    # Release
        
    global tempo_utilizacao_Recurso_Lanternagem
    tempo_utilizacao_Recurso_Lanternagem += env.now - inicia_utilizacao_Recurso
    utilizacao['Lanternagem'] = tempo_utilizacao_Recurso_Lanternagem / (CAP_LANTERNAGEM*env.now)  

    if n_serv == 2:
        n_serv -=1
        prio=0
        # chama o proximo "bloco"
        env.process(Mnt_mecanica(env, nome, prio, n_serv))
    else:
        # chama o proximo "bloco"
        coleta_dados_indicadores(env, nome)


def coleta_dados_indicadores(env, nome):    
    # Entidade sai do sistema    
    global conta_saida
    conta_saida+=1    
    
    global equipe_triagem
    global equipe_mnt_mec
    global equipe_mnt_ele
    global equipe_lanternagem    

    # Coleta dados para estatísticas        
    numero_sistema = conta_chegada - conta_saida

    if env.now > tempo_aquecimento:
        NS.append(numero_sistema)        
        NA.append(equipe_triagem.count + equipe_mnt_mec.count +
        equipe_mnt_ele.count + equipe_lanternagem.count)
        NF.append(len(equipe_triagem.queue) + len(equipe_mnt_mec.queue) +
        len(equipe_mnt_ele.queue) + len(equipe_lanternagem.queue))
    
    momento_saida[nome] = env.now            
    tempo_sistema[nome] = momento_saida[nome] - momento_chegada[nome]
    
    if env.now > tempo_aquecimento:
        TS.append(tempo_sistema[nome])        
        USO_T.append(utilizacao['Triagem']) 
        USO_E.append(utilizacao['Eletrica'])        
        USO_M.append(utilizacao['Mecanica'])        
        USO_L.append(utilizacao['Lanternagem'])
        T.append(env.now)


def computa_estatisticas(replicacao, tempo):  
    print()
    comprimento_linha = 100
    print("="*comprimento_linha)   
    print("Indicadores de Desempenho da Replicacao {0:d}".format(replicacao), end="\n")
    print("="*comprimento_linha)   
    
    entidade = "carros"

    NS_i = np.mean(NS)
    NF_i = np.mean(NF)
    NA_i = np.mean(NA)
    TS_i = np.mean(TS)
    TF_i = np.mean(TF)
    TA_i = np.mean(TA)
    USO_T_i= np.mean(USO_T) if len(USO_T) > 0 else 0    
    USO_E_i= np.mean(USO_E) if len(USO_E) > 0 else 0    
    USO_M_i= np.mean(USO_M) if len(USO_M) > 0 else 0    
    USO_L_i= np.mean(USO_L) if len(USO_L) > 0 else 0    
    
    print('Chegadas: {0:d} {1:s}'.format(conta_chegada, entidade))
    print('Saidas:   {0:d} {1:s}'.format(conta_saida, entidade))
    print('WIP:      {0:d} {1:s}'.format(conta_chegada-conta_saida, entidade))
    print('NS: {0:.2f} {1:s}'.format(NS_i, entidade))
    print('NF: {0:.2f} {1:s}'.format(NF_i, entidade))
    print('NA: {0:.2f} {1:s}'.format(NA_i, entidade))
    print('TS: {0:.2f} {1:s}'.format(TS_i, tempo))
    print('TF: {0:.2f} {1:s}'.format(TF_i, tempo))
    print('TA: {0:.2f} {1:s}'.format(TA_i, tempo))
    print('USO-T:{0:.2f}%'.format(USO_T_i*100))    
    print('USO-E:{0:.2f}%'.format(USO_E_i*100))    
    print('USO-M:{0:.2f}%'.format(USO_M_i*100))    
    print('USO-L:{0:.2f}%'.format(USO_L_i*100))    
    
    
    print("="*comprimento_linha, end="\n")   
    NS_bar.append(NS_i)
    NF_bar.append(NF_i)
    NA_bar.append(NA_i)
    TS_bar.append(TS_i)
    TF_bar.append(TF_i)
    TA_bar.append(TA_i)
    USO_T_bar.append(USO_T_i)
    USO_E_bar.append(USO_E_i)
    USO_M_bar.append(USO_M_i)
    USO_L_bar.append(USO_L_i)

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
    
    entidade = "carros"

    print('NS: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(NS_bar), calc_ic(NS), entidade))
    print('NF: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(NF_bar), calc_ic(NF), entidade))
    print('NA: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(NA_bar), calc_ic(NA), entidade))
    print('TS: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(TS_bar), calc_ic(TS), tempo))
    print('TF: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(TF_bar), calc_ic(TF), tempo))
    print('TA: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(TA_bar), calc_ic(TA), tempo))
    print('USO-T:{0:.2f}% \u00B1 {1:.2f}%  (IC 95%)'.format(np.mean(USO_T_bar)*100, calc_ic(USO_T)*100))
    print('USO-E:{0:.2f}% \u00B1 {1:.2f}%  (IC 95%)'.format(np.mean(USO_E_bar)*100, calc_ic(USO_E)*100))
    print('USO-M:{0:.2f}% \u00B1 {1:.2f}%  (IC 95%)'.format(np.mean(USO_M_bar)*100, calc_ic(USO_M)*100))
    print('USO-L:{0:.2f}% \u00B1 {1:.2f}%  (IC 95%)'.format(np.mean(USO_L_bar)*100, calc_ic(USO_L)*100))
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
        y1 = USO_T
        y2 = USO_E
        y3 = USO_M
        y4 = USO_L
        
        # usa a função plot
        plt.title('Indicador de Desempenho: \n\n' + \
        "Utilização média dos Recursos")
        plt.plot(xi, y1, marker='o', linestyle='-', color='red', label='Equipe de Triagem')        
        plt.plot(xi, y2, marker='o', linestyle='-', color='green', label='Equipe de Mnt Elétrica')                
        plt.plot(xi, y3, marker='o', linestyle='-', color='blue', label='Equipe de Mnt Mecânica')        
        plt.plot(xi, y4, marker='o', linestyle='-', color='yellow', label='Equipe de Lanternagem')        
        
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
    tempo_utilizacao_Recurso_Triagem = 0
    tempo_utilizacao_Recurso_Mecanica = 0
    tempo_utilizacao_Recurso_Eletrica = 0
    tempo_utilizacao_Recurso_Lanternagem = 0

    env = simpy.Environment()
    equipe_triagem = simpy.Resource(env, CAP_TRIAGEM)
    equipe_mnt_mec = simpy.PriorityResource(env, CAP_MECANICA)
    equipe_mnt_ele = simpy.PriorityResource(env, CAP_ELETRICA)
    equipe_lanternagem = simpy.PriorityResource(env, CAP_LANTERNAGEM)
    env.process(chegada_carro(env, "carro"))
    env.run(duracao_da_simulacao)
    computa_estatisticas(i, "horas")        

publica_estatisticas("horas")
###################################################################


