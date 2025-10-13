# -*- coding: utf-8 -*-
#!/usr/bin/python3

# Disciplina: EPD899: Simulacao de Sistemas Logísticos
# Prof: Joao Flavio F. Almeida <joao.flavio@dep.ufmg>
# Problemas de Simulação - Resolução em Simpy (python)

# ##################################################################
# Implementação computacional dos 10 exemplos das aulas
# ##################################################################

# ##################################################################
# Um consultório médico opera da seguinte forma (todos os valores de 
# tempo estão em minutos): os pacientes chegam a intervalos que seguem 
# uma distribuição triangular com moda de 30 , mínimo de 23 e máximo 
# de 35. Ao chegarem, são atendidos por uma secretária que preenche 
# um formulário eletrônico contendo informações sobre o paciente. 
# O tempo deste atendimento segue uma distribuição normal com média 
# de 2 e desvio padrão de 0,5. Preenchido o formulário, o Paciente
# aguarda pela consulta com o médico, cuja duração segue uma distribuição 
# normal com média de 20 e desvio padrão de 5. Após a consulta 10% dos 
# pacientes são submetidos a algum exame no próprio consultório, 
# enquanto os demais vão embora. O exame é realizado logo após a consulta 
# e feito pelo próprio médico, tendo uma duração exponencialmente 
# distribuída com média igual a 5. Após isso, os Pacientes deixam o 
# consultório. A secretária além de preencher os formulários, também 
# atende o telefone, cujas chamadas chegam a intervalos que seguem 
# uma distribuição exponencial com média de 5. A duração da conversa 
# telefônica é exponencialmente distribuída com média igual a 3. O
# atendimento telefônico, quando a secretária está disponível, é 
# prioritário. Quando ela está atendendo algum paciente, ela termina 
# o atendimento antes de atender o telefone. Posto isto, construir o
# diagrama de ciclo de atividades representativo deste sistema
# explicitando todos os seus elementos e condições.
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

# Pacientes (_P)
NS_P = []
NA_P = []
NF_P = []
TS_P = []
TA_P = []
TF_P = []
# Chamadas (_C)
NS_C = []
NA_C = []
NF_C = []
TS_C = []
TA_C = []
TF_C = []

USO_S=[] # Secretaria
USO_M=[] # Medico

NS_P_bar = []
NF_P_bar = [] 
NA_P_bar = [] 
TS_P_bar = [] 
TF_P_bar = [] 
TA_P_bar = []

NS_C_bar = []
NF_C_bar = [] 
NA_C_bar = [] 
TS_C_bar = [] 
TF_C_bar = [] 
TA_C_bar = []

USO_S_bar=[]
USO_M_bar=[]

TM = []  # Tempo dos Eventos Discretos: Medico
TS = []  # Tempo dos Eventos Discretos: Secretaria

conta_chegada_paciente = 0
conta_chegada_chamada = 0
conta_saida_paciente = 0 
conta_saida_chamada = 0 
tempo_utilizacao_Recurso_Secretaria = 0
tempo_utilizacao_Recurso_Medico = 0

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

CAP_SECRETARIAS = 1
CAP_MEDICOS = 1

###################################################################
# Configura a rodada de simulacao definindo o 
# numero de replicações e duração da simulação
###################################################################
# # Teste
# n_replicacoes = 1 
# duracao_da_simulacao = 10000
# tempo_aquecimento = 2000
# imprime_detalhes = True 

###################################################################
# Simulação oficial
n_replicacoes = 5
duracao_da_simulacao =   30*12*60
tempo_aquecimento = 3*12*60
imprime_detalhes = False 
###################################################################

# Unidade básica para todos os tempos: minutos

def distribuicoes(tipo):
    return {
        'chegada_paciente': triangular(23,35,30),   # minutos
        'recepcao':     gauss(2,0.5),               # minutos
        'consulta':     gauss(20,5),                # minutos
        'exame':        expovariate(1/5),           # minutos
        'chegada_chamada': expovariate(1/5),        # minutos
        'atende_chamada':  expovariate(1/3)         # minutos
    }.get(tipo,0.0)


def chegada_paciente(env, entidade, secretaria, medico):
    global conta_chegada_paciente    
    
    while True:        
        yield env.timeout(distribuicoes('chegada_paciente'))
        conta_chegada_paciente+=1
        nome = entidade + " " + str(conta_chegada_paciente)        
        momento_chegada[nome] = env.now        
        if imprime_detalhes:
            print("{0:.2f}: {1:s} chega no Consultório Médico".format(env.now, nome))
        
        # chama o proximo "bloco"                
        prio=1
        env.process(recepcao(env, nome, prio, secretaria, medico))


def recepcao (env, nome, prio, secretaria, medico):
    momento_entrada_fila[nome] = env.now        
    # Requer uso de um slot do Recurso
    # Seize, Delay, Release
    with secretaria.request(priority=prio) as req:
        # Seize
        yield req
        momento_saida_fila[nome] = env.now
        tempo_fila[nome] = momento_saida_fila[nome] - momento_entrada_fila[nome] 
        if env.now > tempo_aquecimento:
            TF_P.append(tempo_fila[nome])

        if imprime_detalhes:
            print("{0:.2f}: Secretária inicia a recepção do {1:s}. Número de entidades em atendimento: {2:d}"
            .format(env.now, nome, secretaria.count))

        if env.now > tempo_aquecimento:
            NA_P.append(secretaria.count)
    
        inicia_atendimento[nome] = env.now
        inicia_utilizacao_Recurso = env.now
        # Delay        
        yield env.timeout(distribuicoes('recepcao'))
        if imprime_detalhes:
            print("{0:.2f}: Secretária termina a recepção do {1:s}.  Número de entidades em fila: {2:d}"
            .format(env.now, nome, len(secretaria.queue)))
        
        if env.now > tempo_aquecimento:
            NF_P.append(len(secretaria.queue))        

        finaliza_atendimento[nome] = env.now        
        duracao_atendimento[nome] = finaliza_atendimento[nome] - inicia_atendimento[nome]                
        
        if env.now > tempo_aquecimento:
            TA_P.append(duracao_atendimento[nome])
        
    # Release

    global tempo_utilizacao_Recurso_Secretaria
    tempo_utilizacao_Recurso_Secretaria += env.now - inicia_utilizacao_Recurso
    utilizacao['Secretarias'] = tempo_utilizacao_Recurso_Secretaria / (CAP_SECRETARIAS*env.now)  
    if env.now > tempo_aquecimento:
        USO_S.append(utilizacao['Secretarias'])        
        TS.append(env.now)

    # chama o proximo "bloco"
    env.process(realiza_consulta(env, nome, medico, prio))


def realiza_consulta(env, nome, medico, prio):

    momento_entrada_fila[nome] = env.now
    # Seize, Delay (apenas!)
    request=medico.request(priority=prio)    
    yield request
    momento_saida_fila[nome] = env.now
    tempo_fila[nome] = momento_saida_fila[nome] - momento_entrada_fila[nome] 
    if env.now > tempo_aquecimento:
        TF_P.append(tempo_fila[nome])

    if imprime_detalhes:
        print("{0:.2f}: Médico inicia o atendimento do {1:s}. Número de entidades em atendimento: {2:d}"
        .format(env.now, nome, medico.count))
    
    if env.now > tempo_aquecimento:
        NA_P.append(medico.count)
    
    inicia_atendimento[nome] = env.now
    inicia_utilizacao_Recurso = env.now
    yield env.timeout(distribuicoes('consulta'))
    if imprime_detalhes:
        print("{0:.2f}: Médico termina o atendimento do {1:s}. Número de entidades em fila: {2:d}"
        .format(env.now, nome, len(medico.queue)))

    if env.now > tempo_aquecimento:
        NF_P.append(len(medico.queue))
    
    # chama o proximo "bloco"
    env.process(vai_embora_ou_realiza_exame(env, nome, medico, request, prio, inicia_utilizacao_Recurso))


def vai_embora_ou_realiza_exame(env, nome, medico, request, prio, inicia_utilizacao_Recurso):    
    sorteio=random()
    if sorteio <= 0.1:
        # Aumenta a prioridade e fará exame
        prio -= prio
        if imprime_detalhes:
            print("{0:.2f}: {1:s} deverá realizar exame.".format(env.now, nome))
        # chama o proximo "bloco"
        env.process(realiza_exame(env, nome, request, prio, medico, inicia_utilizacao_Recurso))
    else:
        # Libera o médido e vai embora
        yield medico.release(request)

        finaliza_atendimento[nome] = env.now        
        duracao_atendimento[nome] = finaliza_atendimento[nome] - inicia_atendimento[nome]        
        
        if env.now > tempo_aquecimento:
            TA_P.append(duracao_atendimento[nome])

        global tempo_utilizacao_Recurso_Medico
        tempo_utilizacao_Recurso_Medico += env.now - inicia_utilizacao_Recurso
        utilizacao['Medicos'] = tempo_utilizacao_Recurso_Medico / (CAP_MEDICOS*env.now)  
        if env.now > tempo_aquecimento:
            USO_M.append(utilizacao['Medicos'])
            TM.append(env.now)

        # chama o proximo "bloco"
        coleta_dados_indicadores_paciente(env, nome)


def realiza_exame(env, nome, request, prio, medico, inicia_utilizacao_Recurso):
    # with medico.request(priority=prio)as req:
    # yield req
    # Libera o médido e o prende-o novamente aumentando a prioridade
    yield medico.release(request)
    # Seize, Delay, Release
    request=medico.request(priority=prio)    
    yield request
    if imprime_detalhes:
        print("{0:.2f}: {1:s} inicia o exame.".format(env.now, nome))
    
    inicia_atendimento[nome] = env.now
    inicia_utilizacao_Recurso = env.now
    yield env.timeout(distribuicoes('exame'))
    if imprime_detalhes:
        print("{0:.2f}: {1:s} finaliza o exame. Número de entidades em fila: {2:d}"
        .format(env.now, nome, len(medico.queue)))
    
    if env.now > tempo_aquecimento:
        NF_P.append(len(medico.queue))

    finaliza_atendimento[nome] = env.now        
    duracao_atendimento[nome] = finaliza_atendimento[nome] - inicia_atendimento[nome]        
    
    if env.now > tempo_aquecimento:
        TA_P.append(duracao_atendimento[nome])

    # Libera o médido e vai embora
    yield medico.release(request)

    global tempo_utilizacao_Recurso_Medico
    tempo_utilizacao_Recurso_Medico += env.now - inicia_utilizacao_Recurso
    utilizacao['Medicos'] = tempo_utilizacao_Recurso_Medico / (CAP_MEDICOS*env.now)  
    if env.now > tempo_aquecimento:
        USO_M.append(utilizacao['Medicos'])
        TM.append(env.now)

    # chama o proximo "bloco"
    coleta_dados_indicadores_paciente(env, nome)


def chegada_chamada(env, entidade, secretaria):
    global conta_chegada_chamada
    while True:
        yield env.timeout(distribuicoes('chegada_chamada'))
        conta_chegada_chamada +=1
        nome = entidade + " " + str(conta_chegada_chamada)        
        momento_chegada[nome] = env.now        
        if imprime_detalhes:
            print("{0:.2f}: {1:s} chega para a secretária".format(env.now, nome))
        
        # chama o proximo "bloco"                
        prio=0
        env.process(atende_chamada(env, nome, secretaria, prio))


def atende_chamada(env, nome, secretaria, prio):
    momento_entrada_fila[nome] = env.now        
    # Requer uso de um slot do Recurso
    # Seize, Delay, Release
    with secretaria.request(priority=prio) as req:
        yield req
        momento_saida_fila[nome] = env.now
        tempo_fila[nome] = momento_saida_fila[nome] - momento_entrada_fila[nome] 
        if env.now > tempo_aquecimento:
            TF_C.append(tempo_fila[nome])

        if imprime_detalhes:
            print("{0:.2f}: {1:s} é atendida. Número de entidades em atendimento: {2:d}"
            .format(env.now, nome, secretaria.count))
        
        if env.now > tempo_aquecimento:
            NA_C.append(secretaria.count)
    
        inicia_atendimento[nome] = env.now
        inicia_utilizacao_Recurso = env.now
        # Delay        
        yield env.timeout(distribuicoes('atende_chamada'))
        if imprime_detalhes:
            print("{0:.2f}: {1:s} é finalizada. Número de entidades em fila: {2:d}"
            .format(env.now, nome, len(secretaria.queue)))

        if env.now > tempo_aquecimento:
            NF_C.append(len(secretaria.queue))

        finaliza_atendimento[nome] = env.now        
        duracao_atendimento[nome] = finaliza_atendimento[nome] - inicia_atendimento[nome]                

        if env.now > tempo_aquecimento:
            TA_C.append(duracao_atendimento[nome])

    # Release

    global tempo_utilizacao_Recurso_Secretaria
    tempo_utilizacao_Recurso_Secretaria += env.now - inicia_utilizacao_Recurso
    utilizacao['Secretarias'] = tempo_utilizacao_Recurso_Secretaria / (CAP_SECRETARIAS*env.now)  
    if env.now > tempo_aquecimento:
        USO_S.append(utilizacao['Secretarias']) 
        TS.append(env.now)       

    # chama o proximo "bloco"
    coleta_dados_indicadores_chamada(env, nome)


def coleta_dados_indicadores_paciente(env, nome):
    # Entidade sai do sistema    
    global conta_saida_paciente
    conta_saida_paciente += 1

    numero_sistema = conta_chegada_paciente - conta_saida_paciente

    if env.now > tempo_aquecimento:
        NS_P.append(numero_sistema)        
    
    momento_saida[nome] = env.now            
    tempo_sistema[nome] = momento_saida[nome] - momento_chegada[nome]
    
    if env.now > tempo_aquecimento:
        TS_P.append(tempo_sistema[nome])        


def coleta_dados_indicadores_chamada(env, nome):
    # Entidade sai do sistema    
    global conta_saida_chamada    
    conta_saida_chamada += 1

    numero_sistema = conta_chegada_chamada - conta_saida_chamada

    if env.now > tempo_aquecimento:
        NS_C.append(numero_sistema)
    
    momento_saida[nome] = env.now            
    tempo_sistema[nome] = momento_saida[nome] - momento_chegada[nome]
    
    if env.now > tempo_aquecimento:
        TS_C.append(tempo_sistema[nome])


def computa_estatisticas_paciente(replicacao, tempo):  
    print()
    comprimento_linha = 100
    print("="*comprimento_linha)   
    print("Indicadores de Desempenho de Pacientes da Replicacao {0:d}".format(replicacao), end="\n")
    print("="*comprimento_linha) 

    entidade = "pacientes"

    NS_i = np.mean(NS_P)
    NF_i = np.mean(NF_P)
    NA_i = np.mean(NA_P)
    TS_i = np.mean(TS_P)
    TF_i = np.mean(TF_P)
    TA_i = np.mean(TA_P)
    USO_M_i= np.mean(USO_M)
    USO_S_i= np.mean(USO_S)    
    print('Chegadas: {0:d} {1:s}'.format(conta_chegada_paciente, entidade))
    print('Saidas:   {0:d} {1:s}'.format(conta_saida_paciente, entidade))
    print('WIP:      {0:d} {1:s}'.format(conta_chegada_paciente-conta_saida_paciente, entidade))
    print('NS: {0:.2f} {1:s}'.format(NS_i, entidade))
    print('NF: {0:.2f} {1:s}'.format(NF_i, entidade))
    print('NA: {0:.2f} {1:s}'.format(NA_i, entidade))
    print('TS: {0:.2f} {1:s}'.format(TS_i, tempo))
    print('TF: {0:.2f} {1:s}'.format(TF_i, tempo))
    print('TA: {0:.2f} {1:s}'.format(TA_i, tempo))
    print('USO-M:{0:.2f}%'.format(USO_M_i*100))
    print('USO-S:{0:.2f}%'.format(USO_S_i*100))    
    print("="*comprimento_linha, end="\n")   
    NS_P_bar.append(NS_i)
    NF_P_bar.append(NF_i)
    NA_P_bar.append(NA_i)
    TS_P_bar.append(TS_i)
    TF_P_bar.append(TF_i)
    TA_P_bar.append(TA_i)
    USO_M_bar.append(USO_M_i)
    USO_S_bar.append(USO_S_i)
    
def computa_estatisticas_chamadas(replicacao, tempo):  
    print()
    comprimento_linha = 100
    print("="*comprimento_linha)   
    print("Indicadores de Desempenho de Chamadas da Replicacao {0:d}".format(replicacao), end="\n")
    print("="*comprimento_linha) 

    entidade = "chamadas"

    NS_i = np.mean(NS_C)
    NF_i = np.mean(NF_C)
    NA_i = np.mean(NA_C)
    TS_i = np.mean(TS_C)
    TF_i = np.mean(TF_C)
    TA_i = np.mean(TA_C)
    
    print('Chegadas: {0:d} {1:s}'.format(conta_chegada_chamada, entidade))
    print('Saidas:   {0:d} {1:s}'.format(conta_saida_chamada, entidade))
    print('WIP:      {0:d} {1:s}'.format(conta_chegada_chamada-conta_saida_chamada, entidade))
    print('NS: {0:.2f} {1:s}'.format(NS_i, entidade))
    print('NF: {0:.2f} {1:s}'.format(NF_i, entidade))
    print('NA: {0:.2f} {1:s}'.format(NA_i, entidade))
    print('TS: {0:.2f} {1:s}'.format(TS_i, tempo))
    print('TF: {0:.2f} {1:s}'.format(TF_i, tempo))
    print('TA: {0:.2f} {1:s}'.format(TA_i, tempo))    
    print("="*comprimento_linha, end="\n")   
    NS_C_bar.append(NS_i)
    NF_C_bar.append(NF_i)
    NA_C_bar.append(NA_i)
    TS_C_bar.append(TS_i)
    TF_C_bar.append(TF_i)
    TA_C_bar.append(TA_i)

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
    print("Indicadores de Desempenho do Sistema de Pacientes", end="\n")
    print("="*comprimento_linha)     
    
    entidade = "pacientes"
    print('NS: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(NS_P_bar), calc_ic(NS_P), entidade))
    print('NF: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(NF_P_bar), calc_ic(NF_P), entidade))
    print('NA: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(NA_P_bar), calc_ic(NA_P), entidade))
    print('TS: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(TS_P_bar), calc_ic(TS_P), tempo))
    print('TF: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(TF_P_bar), calc_ic(TF_P), tempo))
    print('TA: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(TA_P_bar), calc_ic(TA_P), tempo))
    print('USO-M:{0:.2f}% \u00B1 {1:.2f}%  (IC 95%)'.format(np.mean(USO_M_bar)*100, calc_ic(USO_M)*100))
    print('USO-S:{0:.2f}% \u00B1 {1:.2f}%  (IC 95%)'.format(np.mean(USO_S_bar)*100, calc_ic(USO_S)*100))
    print("="*comprimento_linha, end="\n") 
    print("")
    print("="*comprimento_linha)   
    print("Indicadores de Desempenho do Sistema de Chamadas", end="\n")
    print("="*comprimento_linha)     
    
    entidade = "chamadas"
    print('NS: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(NS_C_bar), calc_ic(NS_C), entidade))
    print('NF: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(NF_C_bar), calc_ic(NF_C), entidade))
    print('NA: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(NA_C_bar), calc_ic(NA_C), entidade))
    print('TS: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(TS_C_bar), calc_ic(TS_C), tempo))
    print('TF: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(TF_C_bar), calc_ic(TF_C), tempo))
    print('TA: {0:.2f} \u00B1 {1:.2f} {2:s} (IC 95%)'.format(np.mean(TA_C_bar), calc_ic(TA_C), tempo))
    print("="*comprimento_linha, end="\n") 

    ###################################################################
    # Gera gráfico de Warm-up
    ###################################################################
    if n_replicacoes == 1:
        matplotlib.rcParams['figure.figsize'] = (8.0, 6.0)
        matplotlib.style.use('ggplot')
        # cria os dados
        xi = TM     
        y = USO_M        
        # usa a função plot
        plt.title('Indicador de Desempenho: \n\n' \
        + "Utilização média do Médico")
        plt.plot(xi, y, marker='o', linestyle='-', color='b', label='Médicos')
        plt.legend()
        plt.ylim(0.0,1.0)
        plt.xlim(0.0,duracao_da_simulacao)
        plt.xlabel('Tempo (minutos)')
        plt.ylabel('Valor') 
        plt.show()

        # cria os dados
        xi = TS     
        y = USO_S        
        # usa a função plot
        plt.title('Indicador de Desempenho: \n\n' \
        + "Utilização média da Secretária")
        plt.plot(xi, y, marker='o', linestyle='-', color='r', label='Scretárias')
        plt.legend()
        plt.ylim(0.0,1.0)
        plt.xlim(0.0,duracao_da_simulacao)
        plt.xlabel('Tempo (minutos)')
        plt.ylabel('Valor') 
        plt.show()
    ###################################################################


###################################################################
for i in range (1,n_replicacoes+1):
    # Re-inicializacao das estatísticas entre replicações
    conta_chegada_paciente = 0 
    conta_chegada_chamada = 0   
    conta_saida_paciente = 0    
    conta_saida_chamada = 0    
    tempo_utilizacao_Recurso_Medico = 0
    tempo_utilizacao_Recurso_Secretaria = 0

    env = simpy.Environment()
    secretaria = simpy.PriorityResource(env,capacity=CAP_SECRETARIAS)
    medico= simpy.PriorityResource(env,capacity=CAP_MEDICOS)    
    env.process(chegada_paciente(env, "paciente", secretaria, medico))
    env.process(chegada_chamada(env, "chamada", secretaria))
    env.run(duracao_da_simulacao)
    computa_estatisticas_paciente(i, "minutos")    
    computa_estatisticas_chamadas(i, "minutos")    

publica_estatisticas("minutos")
###################################################################
