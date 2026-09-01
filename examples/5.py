"""
DESK - SIMULAÇÃO COM VISUALIZAÇÃO EM TEMPO REAL
Consultório Médico com interface gráfica animada
Parâmetros REALISTAS para demonstração
<<<<<<< HEAD
Autor: 
=======
Autor: [Seu Nome]
>>>>>>> 650004406e9edbfa08a4e39f3bf05d12cb35892d
Disciplina: Simulação de Sistemas
"""

import simpy
import random
import math
import threading
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
from collections import deque
import time


# ####################################################################################
# Projeto: Consutório médico
# Autor: João Flávio F. ALmeida <joao.flavio@dep.ufmg.br>
# Implementação: Alunos da disciplina EPD733 - Simulação de sistema logísticos - PPGEP-UFMG
# Um consultório médico opera da seguinte forma (todos os valores de tempo estão em minutos): 
# os clientes chegam a intervalos que seguem uma distribuição triangular com moda de 30 , 
# mínimo de 23 e máximo de 35. Ao chegarem, são atendidos por uma secretária que preenche 
# um formulário eletrônico contendo informações sobre o paciente. O tempo deste atendimento 
# segue uma distribuição normal com média de 2 e desvio padrão de 0,5.
# Preenchido o formulário, o cliente aguarda pela consulta com o médico, cuja duração segue 
# uma distribuição normal com média de 20 e desvio padrão de 5. Após a consulta 10% dos 
# pacientes são submetidos a algum exame no próprio consultório, enquanto os demais vão embora. 
# O exame é realizado logo após a consulta e feito pelo próprio médico, tendo uma duração 
# exponencialmente distribuída com média igual a 5. Após isso, os clientes deixam o consultório.
# A secretária além de atender os clientes e preencher os formulários, também atende o telefone, 
# cujas chamadas chegam a intervalos que seguem uma distribuição exponencial com média de 5. 
# A duração da conversa telefônica é exponencialmente distribuída com média igual a 3. 
# O atendimento telefônico, quando a secretária está disponível, é prioritário. 
# Quando ela está atendendo algum paciente, ela termina o atendimento antes de atender 
# o telefone. 
# ####################################################################################

# =====================================================================
# PARÂMETROS REALISTAS
# =====================================================================
SIM_TIME = 5000             # 5000 minutos = 83.3 horas (simulação longa)
WARM_UP = 240               # 4 horas de aquecimento (descartar)
NUM_MEDICOS = 1             # 1 médico
NUM_SECRETARIAS = 1         # 1 secretária

# Configuração da visualização (tempo real vs tempo simulado)
VELOCIDADE_ANIMACAO = 100   # ms entre frames (quanto menor, mais rápido)
TEMPO_VISUALIZACAO = 500    # Mostrar apenas os primeiros 500 min na tela

def triangular(a, m, b):
    """Distribuição Triangular (min, moda, max)"""
    u = random.random()
    F = (m - a) / (b - a)
    if u < F:
        return a + math.sqrt(u * (b - a) * (m - a))
    else:
        return b - math.sqrt((1 - u) * (b - a) * (b - m))

# =====================================================================
# MODELO DO CONSULTÓRIO COM RASTREAMENTO
# =====================================================================
class ConsultorioVisual:
    def __init__(self, env):
        self.env = env
        self.secretaria = simpy.Resource(env, NUM_SECRETARIAS)
        self.medico = simpy.Resource(env, NUM_MEDICOS)
        
        # Dados para visualização
        self.historico_tempo = deque(maxlen=500)
        self.historico_fila_medico = deque(maxlen=500)
        self.historico_fila_secretaria = deque(maxlen=500)
        self.historico_ocupacao_medico = deque(maxlen=500)
        self.historico_ocupacao_secretaria = deque(maxlen=500)
        self.eventos_recentes = deque(maxlen=10)
        
        # Estatísticas
        self.tempos_espera_consulta = []
        self.tempos_espera_secretaria = []
        self.pacientes_atendidos = 0
        self.pacientes_com_exame = 0
        self.total_telefonemas = 0
        self.contador_pacientes = 0
        
    def atender_paciente(self, paciente_id):
        """Fluxo completo de um paciente"""
        chegada = self.env.now
        self.contador_pacientes += 1
        self.eventos_recentes.appendleft(f"[{self.env.now:.0f}min] Paciente {paciente_id} CHEGOU")
        
        # 1. SECRETÁRIA (Recepção)
        inicio_espera = self.env.now
        with self.secretaria.request() as req:
            yield req
            tempo_espera = self.env.now - inicio_espera
            self.tempos_espera_secretaria.append(tempo_espera)
            self.eventos_recentes.appendleft(f"[{self.env.now:.0f}min] Paciente {paciente_id} na RECEPÇÃO (espera: {tempo_espera:.1f}min)")
            yield self.env.timeout(max(0, random.gauss(2, 0.5)))
        
        # 2. MÉDICO (Consulta)
        inicio_espera = self.env.now
        with self.medico.request() as req:
            yield req
            tempo_espera = self.env.now - inicio_espera
            self.tempos_espera_consulta.append(tempo_espera)
            self.eventos_recentes.appendleft(f"[{self.env.now:.0f}min] Paciente {paciente_id} na CONSULTA (espera: {tempo_espera:.1f}min)")
            yield self.env.timeout(max(0, random.gauss(20, 5)))
        
        # 3. EXAME (10% dos pacientes)
        if random.random() < 0.10:
            self.pacientes_com_exame += 1
            self.eventos_recentes.appendleft(f"[{self.env.now:.0f}min] Paciente {paciente_id} em EXAME")
            with self.medico.request() as req:
                yield req
                yield self.env.timeout(random.expovariate(1/5))
        
        self.pacientes_atendidos += 1
        self.eventos_recentes.appendleft(f"[{self.env.now:.0f}min] Paciente {paciente_id} FINALIZOU")
        
        # Registrar para gráficos (apenas após warm-up)
        if self.env.now >= WARM_UP:
            self.historico_tempo.append(self.env.now)
            self.historico_fila_medico.append(len(self.medico.queue))
            self.historico_fila_secretaria.append(len(self.secretaria.queue))
            self.historico_ocupacao_medico.append(1 if self.medico.count > 0 else 0)
            self.historico_ocupacao_secretaria.append(1 if self.secretaria.count > 0 else 0)
    
    def telefonema(self):
        """Telefonemas com prioridade (atendidos pela secretária)"""
        self.total_telefonemas += 1
        self.eventos_recentes.appendleft(f"[{self.env.now:.0f}min] Telefonema RECEBIDO")
        with self.secretaria.request() as req:
            yield req
            yield self.env.timeout(random.expovariate(1/3))
            self.eventos_recentes.appendleft(f"[{self.env.now:.0f}min] Telefonema FINALIZADO")
    
    def gerador_pacientes(self):
        """Gera pacientes com intervalo Triangular(23,30,35)"""
        paciente_id = 0
        while True:
            yield self.env.timeout(triangular(23, 30, 35))
            paciente_id += 1
            self.env.process(self.atender_paciente(paciente_id))
    
    def gerador_telefonemas(self):
        """Gera telefonemas com intervalo Exponencial(5)"""
        while True:
            yield self.env.timeout(random.expovariate(1/5))
            self.env.process(self.telefonema())

# =====================================================================
# INTERFACE GRÁFICA PROFISSIONAL
# =====================================================================
def iniciar_visualizacao():
    """Inicia a simulação com interface gráfica em tempo real"""
    
    # Configurar estilo
    plt.style.use('dark_background')
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
    fig.patch.set_facecolor('#1a1a2e')
    fig.suptitle('CONSULTÓRIO MÉDICO - SIMULAÇÃO EM TEMPO REAL', 
                 fontsize=16, fontweight='bold', color='#e94560')
    
    # Inicializar ambiente e modelo
    env = simpy.Environment()
    consultorio = ConsultorioVisual(env)
    env.process(consultorio.gerador_pacientes())
    env.process(consultorio.gerador_telefonemas())
    
    # Dados para animação
    tempos = []
    filas_medico = []
    filas_secretaria = []
    ocupacoes_medico = []
    ocupacoes_secretaria = []
    
    print("=" * 70)
    print("🎬 DESK - SIMULAÇÃO CONSULTÓRIO MÉDICO")
    print("=" * 70)
    print(f"Tempo total: {SIM_TIME} min ({SIM_TIME/60:.1f} horas)")
    print(f"Warm-up: {WARM_UP} min ({WARM_UP/60:.0f} horas)")
    print(f"Médicos: {NUM_MEDICOS} | Secretárias: {NUM_SECRETARIAS}")
    print("=" * 70)
    print("📊 A janela gráfica será aberta...")
    print("🖱️ Feche a janela para encerrar a simulação.")
    print("⏳ A simulação continuará rodando em background...")
    print("=" * 70)
    
    def atualizar(frame):
        """Atualiza os gráficos a cada frame"""
        
        # Executar passo da simulação
        try:
            env.step()
        except:
            pass
        
        # Coletar novos dados
        if consultorio.historico_tempo:
            tempos.extend(consultorio.historico_tempo)
            filas_medico.extend(consultorio.historico_fila_medico)
            filas_secretaria.extend(consultorio.historico_fila_secretaria)
            ocupacoes_medico.extend(consultorio.historico_ocupacao_medico)
            ocupacoes_secretaria.extend(consultorio.historico_ocupacao_secretaria)
            consultorio.historico_tempo.clear()
            consultorio.historico_fila_medico.clear()
            consultorio.historico_fila_secretaria.clear()
            consultorio.historico_ocupacao_medico.clear()
            consultorio.historico_ocupacao_secretaria.clear()
        
        if tempos:
            # Manter apenas últimos pontos para performance
            max_pontos = 500
            if len(tempos) > max_pontos:
                tempos_display = tempos[-max_pontos:]
                filas_m_display = filas_medico[-max_pontos:]
                filas_s_display = filas_secretaria[-max_pontos:]
                ocup_m_display = ocupacoes_medico[-max_pontos:]
                ocup_s_display = ocupacoes_secretaria[-max_pontos:]
            else:
                tempos_display = tempos
                filas_m_display = filas_medico
                filas_s_display = filas_secretaria
                ocup_m_display = ocupacoes_medico
                ocup_s_display = ocupacoes_secretaria
            
            # Gráfico 1: Filas
            ax1.clear()
            ax1.plot(tempos_display, filas_m_display, 'r-', linewidth=1.5, label='Fila Médico')
            ax1.plot(tempos_display, filas_s_display, 'b-', linewidth=1.5, label='Fila Secretária')
            ax1.set_ylabel('Pacientes na Fila', color='white')
            ax1.set_xlabel('Tempo (minutos)', color='white')
            ax1.set_title('📊 EVOLUÇÃO DAS FILAS', color='#e94560', fontsize=12, fontweight='bold')
            ax1.tick_params(colors='white')
            ax1.grid(True, alpha=0.2, color='white')
            ax1.set_facecolor('#16213e')
            ax1.legend(loc='upper left', facecolor='#1a1a2e', edgecolor='#e94560')
            
            # Gráfico 2: Ocupação
            ax2.clear()
            ax2.fill_between(tempos_display, ocup_m_display, alpha=0.5, color='green', label='Médico')
            ax2.fill_between(tempos_display, ocup_s_display, alpha=0.5, color='orange', label='Secretária')
            ax2.set_ylabel('Ocupado (1=sim, 0=não)', color='white')
            ax2.set_xlabel('Tempo (minutos)', color='white')
            ax2.set_title('💼 OCUPAÇÃO DOS RECURSOS', color='#e94560', fontsize=12, fontweight='bold')
            ax2.tick_params(colors='white')
            ax2.set_ylim(-0.1, 1.1)
            ax2.grid(True, alpha=0.2, color='white')
            ax2.set_facecolor('#16213e')
            ax2.legend(loc='upper left', facecolor='#1a1a2e', edgecolor='#e94560')
        
        # Gráfico 3: Histórico de Eventos
        ax3.clear()
        ax3.axis('off')
        ax3.set_facecolor('#16213e')
        eventos_texto = "\n".join([f"• {e}" for e in list(consultorio.eventos_recentes)[:8]])
        ax3.text(0.05, 0.95, eventos_texto, transform=ax3.transAxes, fontsize=9,
                 color='white', verticalalignment='top', family='monospace')
        ax3.set_title('📋 HISTÓRICO DE EVENTOS', color='#e94560', fontsize=12, fontweight='bold')
        
        # Gráfico 4: Estatísticas
        ax4.clear()
        ax4.axis('off')
        ax4.set_facecolor('#16213e')
        
        # Calcular médias
        media_espera = np.mean(consultorio.tempos_espera_consulta[-50:]) if consultorio.tempos_espera_consulta else 0
        ocup_medico = np.mean(ocupacoes_medico[-100:]) if ocupacoes_medico else 0
        
        info_texto = f"""
╔════════════════════════════════════════╗
║           ESTATÍSTICAS                 ║
╠════════════════════════════════════════╣
║ Tempo atual: {env.now:.0f} min
║                                         ║
║ Pacientes atendidos: {consultorio.pacientes_atendidos}
║ Pacientes em exame: {consultorio.pacientes_com_exame}
║ Telefonemas: {consultorio.total_telefonemas}
║                                         ║
║ Fila Médico: {len(consultorio.medico.queue)}
║ Fila Secretária: {len(consultorio.secretaria.queue)}
║                                         ║
║ Tempo médio espera consulta: 
║   {media_espera:.1f} min
║                                         ║
║ Ocupação Médico: {ocup_medico*100:.1f}%
╚════════════════════════════════════════╝
        """
        ax4.text(0.5, 0.95, info_texto, transform=ax4.transAxes, fontsize=10,
                 color='#e94560', verticalalignment='top', horizontalalignment='center',
                 family='monospace', fontweight='bold')
        ax4.set_title('📈 INFORMAÇÕES', color='#e94560', fontsize=12, fontweight='bold')
        
        # Forçar atualização
        fig.canvas.draw_idle()
        
        # Verificar se simulação terminou
        if env.now >= SIM_TIME:
            print("\n" + "=" * 70)
            print("✅ SIMULAÇÃO CONCLUÍDA!")
            print(f"   Pacientes atendidos: {consultorio.pacientes_atendidos}")
            print(f"   Tempo médio de espera: {media_espera:.2f} min")
            print(f"   Ocupação do médico: {ocup_medico*100:.1f}%")
            print("=" * 70)
            plt.close()
        
        return ax1, ax2, ax3, ax4
    
    # Criar animação
    ani = animation.FuncAnimation(fig, atualizar, interval=VELOCIDADE_ANIMACAO, 
                                   cache_frame_data=False, blit=False)
    
    # Mostrar janela
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    iniciar_visualizacao()