# remodelando fluxo
import simpy
import random
import tkinter as tk
import threading
import time

random.seed()

# -------------------------------
# Configuração do fluxo (caixas + setas)
# -------------------------------
atividades = [
    ("Conferência", 100, 100),
    ("Registro", 300, 100),
    ("Armazenamento na CAF", 500, 100),
    ("Avaliação para Fracionamento", 100, 200),
    ("Unitalização Manual", 300, 200),
    ("Unitalização Automática", 500, 200),
    ("Armazenamento no Estoque Interno", 100, 300),
    ("Ressuprimento da satelite", 300, 300),
    ("Armazenamento no Estoque da Farmácia Satelite", 500, 300),
    ("Atender solicitação", 700, 300),
    ("Produção de Fita", 300, 400),
    ("Dispensação", 500, 400),
]

# -------------------------------
# Estruturas para indicadores
# -------------------------------
t_fila = {}
t_fila = {nome: [] for nome, _, _ in atividades}# Inicializar as chaves no dicionário t_fila
t_sistema = []
uso = {}
uso = {nome: 0 for nome, _, _ in atividades}# Inicializar as chaves no dicionário uso

ligacoes = [
    ("Conferência", "Registro"),
    ("Registro", "Armazenamento na CAF"),
    ("Armazenamento na CAF", "Avaliação para Fracionamento"),
    ("Armazenamento na CAF", "Armazenamento no Estoque Interno"),
    ("Avaliação para Fracionamento", "Unitalização Manual"),
    ("Avaliação para Fracionamento", "Unitalização Automática"),
    ("Unitalização Manual", "Armazenamento no Estoque Interno"),
    ("Unitalização Automática", "Armazenamento no Estoque Interno"),
    ("Armazenamento no Estoque Interno", "Ressuprimento da satelite"),
    ("Ressuprimento da satelite", "Armazenamento no Estoque da Farmácia Satelite"),
    ("Armazenamento no Estoque da Farmácia Satelite", "Atender solicitação"),
    ("Atender solicitação", "Produção de Fita"),
    ("Atender solicitação", "Dispensação"),
    ("Produção de Fita", "Dispensação"),
]

# -------------------------------
# Interface gráfica
# -------------------------------
class SimGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulação Farmácia")
        self.canvas = tk.Canvas(root, width=800, height=500, bg="white")
        self.canvas.pack()

        # contador de tempo no topo
        self.time_label = self.canvas.create_text(400, 30, text="Tempo: 0",
                                                  font=("Arial", 14, "bold"),
                                                  fill="black")

        # desenhar caixas
        self.nodes = {}
        for nome, x, y in atividades:
            self.nodes[nome] = (x, y)
            self.canvas.create_rectangle(x-60, y-30, x+60, y+30, fill="lightblue")
            self.canvas.create_text(x, y, text=nome, font=("Arial", 9))

        # setas
        for origem, destino in ligacoes:
            x1, y1 = self.nodes[origem]
            x2, y2 = self.nodes[destino]
            self.canvas.create_line(x1+60, y1, x2-60, y2, arrow=tk.LAST)

        self.items = {}

    def criar_item(self, nome, numero):
        # Posição inicial das bolinhas (ajustando para evitar sobreposição)
        x, y = atividades[0][1]-100, atividades[0][2]
        bola = self.canvas.create_oval(x-10, y-10, x+10, y+10, fill="red")
        texto = self.canvas.create_text(x, y, text=str(numero), font=("Arial", 10, "bold"), fill="white")
        self.items[nome] = (bola, texto)
        self.root.update()

    def mover_item(self, nome, destino, tempo_atual):
        """Move o item até o destino e atualiza contador"""
        if nome not in self.items or destino not in self.nodes:
            return

        # atualizar contador de tempo
        self.canvas.itemconfig(self.time_label, text=f"Tempo: {tempo_atual}")

        bola, texto = self.items[nome]
        x1, y1, x2, y2 = self.canvas.coords(bola)
        cx, cy = (x1+x2)/2, (y1+y2)/2
        dx, dy = self.nodes[destino]

        passos = 20
        for _ in range(passos):
            self.canvas.move(bola, (dx-cx)/passos, (dy-cy)/passos)
            self.canvas.move(texto, (dx-cx)/passos, (dy-cy)/passos)
            x1, y1, x2, y2 = self.canvas.coords(bola)
            cx, cy = (x1+x2)/2, (y1+y2)/2
            self.root.update()
            time.sleep(0.05)

def distribuicoes(tipo):
    return {
        # Cada segundo real, representa 60 min 
        "Etapa_Chegada": random.triangular(0.8,1.2,6),
        "Etapa_conferencia": random.triangular(0.16,0.33,1.5),
        "Etapa_registro": random.triangular(0.16,0.33,0.5),
        "Etapa_armazena_caf": random.triangular(0.33,0.5,0.66),
        "Etapa_avaliar_fracio": random.triangular(0.0002,0.002,0.0033),
        "Etapa_unita_manual": random.triangular(2,2.5,8),
        "Etapa_unita_auto": random.triangular(2,2.5,8),
        "Etapa_armazena_interno": random.triangular(0.33,0.66,1),
        "Etapa_ressupri_satelite": random.triangular(1.06,2,2.8), #Considerei o ressuprimento como a soma de atender a solicitação da satélite e o transporte até lá
        # "Etapa_atender_satel": random.triangular(0.66,1,1.5)
        # "Etapa_transporte_satel": random.triangular(0.4,1,1.3),
        "Etapa_armazena_satelite": random.triangular(0.5,0.66,1.5),
        "Etapa_atend_solic": random.triangular(0.002,0.005,0.016),
        "Etapa_producao_fita": random.triangular(0.08,0.16,0.5),
        "Etapa_dispensacao": random.triangular(0.03,0.08,0.33),
        }.get(tipo,0.0)

# -------------------------------
# Função de chegada
# -------------------------------
def Etapa_Chegada(env, gui, taxa_chegada, Aux_adm_of, Aux_adm_reg,
                  Aux_far_frac, Aux_far_unita_manual, Aux_far_unita_auto,
                  Aux_almox_armz, Aux_far_ressupri, Aux_far_satel):
    countarrivals = 0
    while True:
        #yield env.timeout(taxa_chegada) # taxa_chegada fixa
        yield env.timeout(distribuicoes ("Etapa_Chegada"))  
        countarrivals += 1
        item = f"item {countarrivals}"
        gui.criar_item(item, countarrivals)
        print(f"{env.now}: {item} chegou na farmácia.")
        env.process(Etapa_conferencia(env, gui, item, 10, Aux_adm_of, Aux_adm_reg, #remover tempo de duração
                                      Aux_far_frac, Aux_far_unita_manual,
                                      Aux_far_unita_auto, Aux_almox_armz,
                                      Aux_far_ressupri, Aux_far_satel))

# -------------------------------
# Etapas do fluxo (adicionada atualização do contador)
# -------------------------------

# #++++++++++++++ funcao basica +++++++++++++++++
# def Etapa_conferencia(env, gui, item, tempo, Aux_adm_of, Aux_adm_reg, *args): #remover tempo de duração
#     chegada = env.now
#     gui.mover_item(item, "Conferência", env.now)
#     with Aux_adm_of.request() as req:
#         print(f"{env.now}: {item} foi para conferência — itens na fila: {len(Aux_adm_of.queue)}") # Medir tamanho da fila ANTES de tentar pegar o recurso
#         yield req
#         t_fila["Conferência"].append(env.now-chegada)
#         ini_confe = env.now 
#         print(f"{env.now}: {item} iniciou conferência")
#         #yield env.timeout(tempo)
#         yield env.timeout(distribuicoes("Etapa_conferencia")) 
#         #  uso["Conferência"] += env.now - ini_confe # uso total do sistema
#         uso["Conferência"] = env.now - ini_confe 
#         print(f"{env.now}: {item} finalizou conferência | tempo em fila={t_fila["Conferência"][-1]:.2f} | uso={uso["Conferência"]:.2f}")
#         env.process(Etapa_registro(env, gui, item, 2, Aux_adm_reg, *args))
# #++++++++++++++++++++++++++++++++++++++++++++

def Etapa_conferencia(env, gui, item, tempo, Aux_adm_of, Aux_adm_reg, *args): #remover tempo de duração
    chegada = env.now
    gui.mover_item(item, "Conferência", env.now)
    with Aux_adm_of.request() as req:
        print(f"{env.now}: {item} foi para conferência — itens na fila: {len(Aux_adm_of.queue)}") # Medir tamanho da fila ANTES de tentar pegar o recurso
        yield req
        t_fila["Conferência"].append(env.now-chegada)
        ini_confe = env.now
        print(f"{env.now}: {item} iniciou conferência")
        #yield env.timeout(tempo)
        yield env.timeout(distribuicoes ("Etapa_conferencia"))
        #  uso["Conferência"] += env.now - ini_confe # uso total do sistema
        uso["Conferência"] = env.now - ini_confe
        print(f"{env.now}: {item} finalizou conferência | tempo em fila={t_fila["Conferência"][-1]:.2f} | uso={uso["Conferência"]:.2f}")
        env.process(Etapa_registro(env, gui, item, 2, Aux_adm_reg, *args))

def Etapa_registro(env, gui, item, tempo, Aux_adm_reg, Aux_almox_armz, *args):
    chegada = env.now
    gui.mover_item(item, "Registro", env.now)
    with Aux_adm_reg.request() as req:
        print(f"{env.now}: {item} foi para registro — itens na fila: {len(Aux_adm_reg.queue)}") # Medir tamanho da fila ANTES de tentar pegar o recurso       
        yield req
        t_fila["Registro"].append(env.now-chegada)
        ini_reg = env.now
        print(f"{env.now}: {item} iniciou registro")
        #yield env.timeout(tempo)
        yield env.timeout(distribuicoes("Etapa_registro"))
        uso["Registro"] = env.now - ini_reg
        print(f"{env.now}: {item} finalizou registro | tempo em fila={t_fila["Registro"][-1]:.2f} | uso={uso["Registro"]:.2f}")
        env.process(Etapa_armazena_caf(env, gui, item, 3, Aux_almox_armz, *args))

def Etapa_armazena_caf(env, gui, item, tempo, Aux_almox_armz, *args):
    chegada = env.now
    gui.mover_item(item, "Armazenamento na CAF", env.now)
    with Aux_almox_armz.request(priority=0) as req:
        print(f"{env.now}: {item} foi para armazenamento na CAF — itens na fila: {len(Aux_almox_armz.queue)}") # Medir tamanho da fila ANTES de tentar pegar o recurso
        yield req
        t_fila["Armazenamento na CAF"].append(env.now-chegada)
        ini_arm_caf = env.now 
        print(f"{env.now}: {item} iniciou armazenamento na CAF")
        #yield env.timeout(tempo)
        yield env.timeout(distribuicoes("Armazenamento na CAF"))
        #  uso["Armazenamento na CAF"] += env.now - ini_arm_caf # uso total do sistema
        uso["Armazenamento na CAF"] = env.now - ini_arm_caf
        print(f"{env.now}: {item} finalizou armazenamento na CAF | tempo em fila={t_fila["Armazenamento na CAF"][-1]:.2f} | uso={uso["Armazenamento na CAF"]:.2f}")

        result = random.random()
        if result <= 0.02:
            print(f"{env.now}: {item} seguiu para armazenamento interno")
            env.process(Etapa_armazena_interno(env, gui, item, 2, *args))
        else:
            print(f"{env.now}: {item} seguiu para unitarização manual")
            env.process(Etapa_avaliar_fracio(env, gui, item, 4, *args))

def Etapa_avaliar_fracio(env, gui, item, tempo, Aux_far_frac, *args):
    chegada = env.now
    gui.mover_item(item, "Avaliação para Fracionamento", env.now)
    with Aux_far_frac.request() as req:
        print(f"{env.now}: {item} foi para avaliação de fracionamento — itens na fila: {len(Aux_far_frac.queue)}") # Medir tamanho da fila ANTES de tentar pegar o recurso
        yield req
        t_fila["Avaliação para Fracionamento"].append(env.now-chegada)
        ini_ava_frac = env.now
        print(f"{env.now}: {item} iniciou avaliação de fracionamento")
        #yield env.timeout(tempo)
        yield env.timeout(distribuicoes("Etapa_avaliar_fracio"))
        #  uso["Avaliação para Fracionamento"] += env.now - ini_ava_frac # uso total do sistema
        uso["Avaliação para Fracionamento"] = env.now - ini_ava_frac
        print(f"{env.now}: {item} finalizou avaliação de fracionamento | tempo em fila={t_fila["Avaliação para Fracionamento"][-1]:.2f} | uso={uso["Avaliação para Fracionamento"]:.2f}")

        result = random.random()
        if result <= 0.15:
            print(f"{env.now}: {item} seguiu para unitarização manual")
            env.process(Etapa_unita_manual(env, gui, item, 3, *args))
        else: 
            print(f"{env.now}: {item} seguiu para unitarização automática") 
            env.process(Etapa_unita_auto(env, gui, item, 2, *args))

def Etapa_unita_manual(env, gui, item, tempo, Aux_far_unita_manual, *args):
    chegada = env.now
    gui.mover_item(item, "Unitalização Manual", env.now)
    with Aux_far_unita_manual.request() as req:
        print(f"{env.now}: {item} foi para unitalização manual — itens na fila: {len(Aux_far_unita_manual.queue)}") # Medir tamanho da fila ANTES de tentar pegar o recurso
        yield req
        t_fila["Unitalização Manual"].append(env.now-chegada)
        ini_uni_man = env.now
        print(f"{env.now}: {item} iniciou unitalização manual")
        #yield env.timeout(tempo)
        yield env.timeout(distribuicoes("Etapa_unita_manual"))
        #  uso["Unitalização Manual"] += env.now - ini_uni_man # uso total do sistema
        uso["Unitalização Manual"] = env.now - ini_uni_man
        print(f"{env.now}: {item} finalizou unitalização manual | tempo em fila={t_fila["Unitalização Manual"][-1]:.2f} | uso={uso["Unitalização Manual"]:.2f}")
        env.process(Etapa_armazena_interno(env, gui, item, 2, *args))

def Etapa_unita_auto(env, gui, item, tempo, Aux_far_unita_auto, *args):
    chegada = env.now
    gui.mover_item(item, "Unitalização Automática", env.now)
    with Aux_far_unita_auto.request() as req:
        print(f"{env.now}: {item} foi para unitalização automática — itens na fila: {len(Aux_far_unita_auto.queue)}") # Medir tamanho da fila ANTES de tentar pegar o recurso
        yield req
        t_fila["Unitalização Automática"].append(env.now-chegada)
        ini_uni_auto = env.now
        print(f"{env.now}: {item} iniciou unitalização automática")
        #yield env.timeout(tempo)
        yield env.timeout(distribuicoes("Etapa_unita_auto")) 
        #  uso["Unitalização Automática"] += env.now - ini_uni_auto # uso total do sistema
        uso["Unitalização Automática"] = env.now - ini_uni_auto
        print(f"{env.now}: {item} finalizou unitalização automática | tempo em fila={t_fila["Unitalização Automática"][-1]:.2f} | uso={uso["Unitalização Automática"]:.2f}")
        env.process(Etapa_armazena_interno(env, gui, item, 2, *args))

def Etapa_armazena_interno(env, gui, item, tempo, Aux_almox_armz, *args):
    chegada = env.now
    gui.mover_item(item, "Armazenamento no Estoque Interno", env.now)
    with Aux_almox_armz.request(priority=1) as req:
        print(f"{env.now}: {item} foi para armazenamento no estoque interno — itens na fila: {len(Aux_almox_armz.queue)}")
        yield req
        t_fila["Armazenamento no Estoque Interno"].append(env.now-chegada)
        ini_arm_int = env.now
        print(f"{env.now}: {item} iniciou armazenamento no estoque interno")
        #yield env.timeout(tempo)
        yield env.timeout(distribuicoes("Etapa_armazena_interno"))
        #  uso["Armazenamento no Estoque Interno"] += env.now - ini_arm_int # uso total do sistema
        uso["Armazenamento no Estoque Interno"] = env.now - ini_arm_int
        print(f"{env.now}: {item} finalizou armazenamento no estoque interno | tempo em fila={t_fila["Armazenamento no Estoque Interno"][-1]:.2f} | uso={uso["Armazenamento no Estoque Interno"]:.2f}")
        env.process(Etapa_ressupri_satelite(env, gui, item, 3, *args))

def Etapa_ressupri_satelite(env, gui, item, tempo, Aux_far_ressupri, *args):
    chegada = env.now
    gui.mover_item(item, "Ressuprimento da satelite", env.now)
    with Aux_far_ressupri.request() as req:
        print(f"{env.now}: {item} foi para Ressuprimento da satelite — itens na fila: {len(Aux_far_ressupri.queue)}")
        yield req
        t_fila["Ressuprimento da satelite"].append(env.now-chegada)
        ini_ressupri = env.now
        print(f"{env.now}: {item} iniciou Ressuprimento da satelite")
        #yield env.timeout(tempo)
        yield env.timeout(distribuicoes("Etapa_ressupri_satelite")) 
        #  uso["Ressuprimento da satelite"] += env.now - ini_ressupri # uso total do sistema
        uso["Ressuprimento da satelite"] = env.now - ini_ressupri
        print(f"{env.now}: {item} finalizou Ressuprimento da satelite | tempo em fila={t_fila["Ressuprimento da satelite"][-1]:.2f} | uso={uso["Ressuprimento da satelite"]:.2f}")
        env.process(Etapa_armazena_satelite(env, gui, item, 3, *args))



def Etapa_armazena_satelite(env, gui, item, tempo, Aux_far_satel, *args):
    chegada = env.now
    gui.mover_item(item, "Armazenamento no Estoque da Farmácia Satelite", env.now)
    with Aux_far_satel.request(priority=2) as req:
        print(f"{env.now}: {item} foi para Armazenamento no Estoque da Farmácia Satelite — itens na fila: {len(Aux_far_satel.queue)}")
        yield req
        t_fila["Armazenamento no Estoque da Farmácia Satelite"].append(env.now-chegada)
        ini_arm_satel = env.now
        print(f"{env.now}: {item} iniciou armazenamento no estoque da farmacia satelite")
        #yield env.timeout(tempo)
        yield env.timeout(distribuicoes("Etapa_armazena_satelite")) 
        #  uso["Armazenamento no Estoque da Farmácia Satelite"] += env.now - ini_arm_satel # uso total do sistema
        uso["Armazenamento no Estoque da Farmácia Satelite"] = env.now - ini_arm_satel
        print(f"{env.now}: {item} finalizou armazenamento no estoque da farmacia satelite | tempo em fila={t_fila["Armazenamento no Estoque da Farmácia Satelite"][-1]:.2f} | uso={uso["Armazenamento no Estoque da Farmácia Satelite"]:.2f}")
        env.process(Etapa_atend_solic(env, gui, item, 2, Aux_far_satel))


def Etapa_atend_solic(env, gui, item, tempo, Aux_far_satel, *args):
    chegada = env.now
    gui.mover_item(item, "Atender solicitação", env.now)
    with Aux_far_satel.request(priority=1) as req:
        print(f"{env.now}: {item} foi para separação em atender solicitação — itens na fila: {len(Aux_far_satel.queue)}")
        yield req
        t_fila["Atender solicitação"].append(env.now-chegada)
        ini_aten_sol = env.now
        print(f"{env.now}: {item} iniciou armazenamento no estoque da farmacia satelite")
        #yield env.timeout(tempo)
        yield env.timeout(distribuicoes("Etapa_atend_solic")) 
        #  uso["Atender solicitação"] += env.now - ini_aten_sol # uso total do sistema
        uso["Atender solicitação"] = env.now - ini_aten_sol
        print(f"{env.now}: {item} finalizou separação em atender solicitação | tempo em fila={t_fila["Atender solicitação"][-1]:.2f} | uso={uso["Atender solicitação"]:.2f}")
        result = random.random()
        if result <= 0.20:
            print(f"{env.now}: {item} seguiu para dispensação para a equipe assistencial")
            env.process(Etapa_dispensacao(env, gui, item, 2, Aux_far_satel))
        else:
            print(f"{env.now}: {item} seguiu para produção de fita")
            env.process(Etapa_producao_fita(env, gui, item, 2, Aux_far_satel, *args))

def Etapa_producao_fita(env, gui, item, tempo, Aux_far_satel, *args):
    chegada = env.now
    gui.mover_item(item, "Produção de Fita", env.now)
    print(f"{env.now}: {item} foi para produção da fita")
    with Aux_far_satel.request(priority=3) as req:
        print(f"{env.now}: {item} foi para produção da fita — itens na fila: {len(Aux_far_satel.queue)}") # Medir tamanho da fila ANTES de tentar pegar o recurso
        yield req
        t_fila["Produção de Fita"].append(env.now-chegada)
        ini_prod_fita = env.now
        print(f"{env.now}: {item} iniciou produção da fita")
         #yield env.timeout(tempo)
        yield env.timeout(distribuicoes("Etapa_producao_fita")) 
        #  uso["Produção de Fita"] += env.now - ini_prod_fita # uso total do sistema
        uso["Produção de Fita"] = env.now - ini_prod_fita
        print(f"{env.now}: {item} finalizou produção da fita | tempo em fila={t_fila["Produção de Fita"][-1]:.2f} | uso={uso["Produção de Fita"]:.2f}")
        env.process(Etapa_dispensacao(env, gui, item, 2, Aux_far_satel))

def Etapa_dispensacao(env, gui, item, tempo, Aux_far_satel):
    chegada = env.now
    gui.mover_item(item, "Dispensação", env.now)
    with Aux_far_satel.request(priority=0) as req:
        print(f"{env.now}: {item} foi para dispensação final — itens na fila: {len(Aux_far_satel.queue)}") # Medir tamanho da fila ANTES de tentar pegar o recurso
        yield req
        t_fila["Dispensação"].append(env.now-chegada)
        ini_disp = env.now
        print(f"{env.now}: {item} iniciou dispensação final")
        #yield env.timeout(tempo)
        yield env.timeout(distribuicoes("Etapa_dispensacao")) 
        #  uso["Dispensação"] += env.now - ini_disp # uso total do sistema
        uso["Dispensação"] = env.now - ini_disp
        print(f"{env.now}: {item} finalizou dispensação final ✅ | tempo em fila={t_fila["Dispensação"][-1]:.2f} | uso={uso["Dispensação"]:.2f}")

# -------------------------------
# Rodar tudo em paralelo
# -------------------------------
def rodar_simulacao(gui):
    env = simpy.Environment()

    Aux_adm_of = simpy.PriorityResource(env, capacity=1)
    Aux_adm_reg = simpy.PriorityResource(env, capacity=1)
    Aux_almox = simpy.PriorityResource(env, capacity=1)
    Aux_far_frac = simpy.PriorityResource(env, capacity=2)
    Aux_far_unita_manual = simpy.PriorityResource(env, capacity=2)
    Aux_far_unita_auto = simpy.PriorityResource(env, capacity=2)
    Aux_almox_armz = simpy.PreemptiveResource(env, capacity=1)
    Aux_far_ressupri = simpy.PriorityResource(env, capacity=1)
    Aux_far_satel = simpy.PreemptiveResource(env, capacity=2)

    env.process(Etapa_Chegada(env, gui, taxa_chegada=0, #remover taxa_chegada, por ser fixa
                            Aux_adm_of=Aux_adm_of,
                            Aux_adm_reg=Aux_adm_reg,
                            Aux_almox_armz=Aux_almox_armz,
                            Aux_far_frac=Aux_far_frac,
                            Aux_far_unita_manual=Aux_far_unita_manual,
                            Aux_far_unita_auto=Aux_far_unita_auto,
                            Aux_far_ressupri=Aux_far_ressupri,
                            Aux_far_satel=Aux_far_satel))

    env.run(until=50)

# -------------------------------
# Iniciar GUI + Simulação
# -------------------------------
root = tk.Tk()
gui = SimGUI(root)

threading.Thread(target=rodar_simulacao, args=(gui,), daemon=True).start()

root.mainloop()
