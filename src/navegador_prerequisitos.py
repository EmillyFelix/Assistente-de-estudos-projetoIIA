"""
Navegador de Pré-requisitos

Sistema que encontra o melhor caminho de estudos baseado nas dependências entre temas.
"""

import heapq
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass, field
from enum import Enum

class NivelDominio(Enum):
    INEXISTENTE = 0
    INICIANTE = 1
    BASICO = 2
    INTERMEDIARIO = 3
    AVANCADO = 4
    DOMINADO = 5

@dataclass
class NoConhecimento:
    tema: str
    nivel_atual: NivelDominio
    prerequisitos: List[str] = field(default_factory=list)
    dificuldade_aprendizado: float = 1.0
    tempo_estimado_horas: float = 10.0
    
    def __hash__(self):
        return hash(self.tema)
    
    def __eq__(self, other):
        return isinstance(other, NoConhecimento) and self.tema == other.tema

@dataclass
class EstadoAprendizagem:
    dominios: Dict[str, NivelDominio]
    tempo_gasto_total: float = 0.0
    
    def __hash__(self):
        items = tuple(sorted(self.dominios.items()))
        return hash((items, self.tempo_gasto_total))
    
    def __eq__(self, other):
        return (isinstance(other, EstadoAprendizagem) and 
                self.dominios == other.dominios and
                self.tempo_gasto_total == other.tempo_gasto_total)

class NavegadorPrerequisitos:
    
    def __init__(self):
        self.grafo_conhecimento: Dict[str, NoConhecimento] = {}
        self.mapa_dependencias: Dict[str, List[str]] = {}
        self._construir_grafo_conhecimento()
    
    def _construir_grafo_conhecimento(self):
        # Temas e suas dependências
        conhecimentos = [
            NoConhecimento("Lógica", NivelDominio.INEXISTENTE, [], 1.0, 8.0),
            NoConhecimento("Conjuntos", NivelDominio.INEXISTENTE, [], 1.2, 10.0),
            NoConhecimento("Funções", NivelDominio.INEXISTENTE, ["Conjuntos"], 1.5, 12.0),
            NoConhecimento("Álgebra", NivelDominio.INEXISTENTE, ["Lógica"], 1.3, 15.0),
            NoConhecimento("Geometria", NivelDominio.INEXISTENTE, ["Álgebra"], 1.4, 12.0),
            NoConhecimento("Trigonometria", NivelDominio.INEXISTENTE, ["Geometria", "Funções"], 1.8, 14.0),
            NoConhecimento("Limites", NivelDominio.INEXISTENTE, ["Funções", "Álgebra"], 2.0, 16.0),
            NoConhecimento("Derivadas", NivelDominio.INEXISTENTE, ["Limites"], 2.2, 18.0),
            NoConhecimento("Integrais", NivelDominio.INEXISTENTE, ["Derivadas"], 2.5, 20.0),
            NoConhecimento("Algoritmos", NivelDominio.INEXISTENTE, ["Lógica"], 1.6, 20.0),
            NoConhecimento("Estruturas de Dados", NivelDominio.INEXISTENTE, ["Algoritmos"], 2.0, 25.0),
            NoConhecimento("Programação", NivelDominio.INEXISTENTE, ["Algoritmos"], 1.8, 30.0),
        ]
        
        # Adiciona ao grafo
        for conhecimento in conhecimentos:
            self.grafo_conhecimento[conhecimento.tema] = conhecimento
            self.mapa_dependencias[conhecimento.tema] = conhecimento.prerequisitos.copy()
    
    def atualizar_estado_conhecimento(self, aluno_id: str, historico_df: pd.DataFrame) -> EstadoAprendizagem:
        dominios = {}
        
        # Inicializa todos os temas como inexistentes
        for tema in self.grafo_conhecimento.keys():
            dominios[tema] = NivelDominio.INEXISTENTE
        
        if historico_df.empty:
            return EstadoAprendizagem(dominios)
        
        desempenho_por_tema = historico_df.groupby('tema').agg({
            'acertou': ['mean', 'count']
        }).round(3)
        
        for tema in desempenho_por_tema.index:
            if tema in dominios:
                taxa_acerto = desempenho_por_tema.loc[tema, ('acertou', 'mean')]
                num_questoes = desempenho_por_tema.loc[tema, ('acertou', 'count')]
                
                if num_questoes >= 3:
                    if taxa_acerto >= 0.96:
                        dominios[tema] = NivelDominio.DOMINADO
                    elif taxa_acerto >= 0.81:
                        dominios[tema] = NivelDominio.AVANCADO
                    elif taxa_acerto >= 0.61:
                        dominios[tema] = NivelDominio.INTERMEDIARIO
                    elif taxa_acerto >= 0.41:
                        dominios[tema] = NivelDominio.BASICO
                    else:
                        dominios[tema] = NivelDominio.INICIANTE
        
        # Calcula tempo total gasto
        tempo_total = historico_df['tempo_segundos'].sum() / 3600.0  # Converte para horas
        
        return EstadoAprendizagem(dominios, tempo_total)
    
    def verificar_prerequisitos_atendidos(self, tema: str, estado: EstadoAprendizagem) -> bool:
        """
        Verifica se todos os pré-requisitos de um tema foram atendidos.
        
        Um pré-requisito é atendido se o aluno tem pelo menos nível BASICO.
        """
        if tema not in self.grafo_conhecimento:
            return False
        
        prerequisitos = self.mapa_dependencias[tema]
        
        for prereq in prerequisitos:
            if (prereq not in estado.dominios or 
                estado.dominios[prereq].value < NivelDominio.BASICO.value):
                return False
        
        return True
    
    def calcular_heuristica(self, estado_atual: EstadoAprendizagem, tema_objetivo: str) -> float:
        if tema_objetivo not in self.grafo_conhecimento:
            return float('inf')
        
        # Se já domina o tema, custo = 0
        if (tema_objetivo in estado_atual.dominios and 
            estado_atual.dominios[tema_objetivo] == NivelDominio.DOMINADO):
            return 0.0
        
        custo_estimado = 0.0
        temas_a_estudar = set()
        
        def _adicionar_prerequisitos_recursivo(tema: str):
            """Adiciona tema e todos os pré-requisitos necessários."""
            if tema in temas_a_estudar:
                return
            
            if tema in self.grafo_conhecimento:
                nivel_atual = estado_atual.dominios.get(tema, NivelDominio.INEXISTENTE)
                
                # Se não domina ainda, precisa estudar
                if nivel_atual.value < NivelDominio.DOMINADO.value:
                    temas_a_estudar.add(tema)
                    
                    # Adiciona pré-requisitos
                    for prereq in self.mapa_dependencias.get(tema, []):
                        _adicionar_prerequisitos_recursivo(prereq)
        
        # Calcula temas necessários
        _adicionar_prerequisitos_recursivo(tema_objetivo)
        
        # Soma tempo estimado para cada tema
        for tema in temas_a_estudar:
            if tema in self.grafo_conhecimento:
                no = self.grafo_conhecimento[tema]
                nivel_atual = estado_atual.dominios.get(tema, NivelDominio.INEXISTENTE)
                
                # Tempo reduzido baseado no progresso atual
                fator_progresso = 1.0 - (nivel_atual.value / NivelDominio.DOMINADO.value) * 0.7
                tempo_necessario = no.tempo_estimado_horas * fator_progresso * no.dificuldade_aprendizado
                
                custo_estimado += tempo_necessario
        
        return custo_estimado
    
    def gerar_acoes_possiveis(self, estado_atual: EstadoAprendizagem) -> List[str]:
        """
        Gera lista de temas que o aluno pode estudar agora (pré-requisitos atendidos).
        
        Retorna apenas temas que:
        1. Ainda não foram dominados
        2. Têm todos os pré-requisitos atendidos
        """
        acoes_validas = []
        
        for tema, no in self.grafo_conhecimento.items():
            # Pula temas já dominados
            if (tema in estado_atual.dominios and 
                estado_atual.dominios[tema] == NivelDominio.DOMINADO):
                continue
            
            # Verifica pré-requisitos
            if self.verificar_prerequisitos_atendidos(tema, estado_atual):
                acoes_validas.append(tema)
        
        return acoes_validas
    
    def aplicar_acao(self, estado: EstadoAprendizagem, tema: str) -> EstadoAprendizagem:
        """
        Aplica uma ação (estudar um tema) e retorna o novo estado.
        
        Simula o progresso: avança um nível no tema estudado.
        """
        if tema not in self.grafo_conhecimento:
            return estado
        
        novo_dominios = estado.dominios.copy()
        no = self.grafo_conhecimento[tema]
        
        # Avança um nível no domínio
        nivel_atual = novo_dominios.get(tema, NivelDominio.INEXISTENTE)
        if nivel_atual.value < NivelDominio.DOMINADO.value:
            novo_nivel = NivelDominio(nivel_atual.value + 1)
            novo_dominios[tema] = novo_nivel
        
        # Calcula tempo gasto (reduzido se já tem progresso)
        fator_progresso = 0.2 + (nivel_atual.value / NivelDominio.DOMINADO.value) * 0.8
        tempo_gasto = no.tempo_estimado_horas * fator_progresso * no.dificuldade_aprendizado / 5.0
        
        novo_tempo_total = estado.tempo_gasto_total + tempo_gasto
        
        return EstadoAprendizagem(novo_dominios, novo_tempo_total)
    
    def buscar_caminho_otimo_astar(self, estado_inicial: EstadoAprendizagem, 
                                   tema_objetivo: str) -> Optional[List[str]]:
        """
        Implementação do algoritmo A* para encontrar o caminho ótimo de aprendizagem.
        
        Retorna:
            Lista de temas na ordem ótima de estudo, ou None se não há caminho.
        """
        if tema_objetivo not in self.grafo_conhecimento:
            return None
        
        # Verifica se já domina o objetivo
        if (tema_objetivo in estado_inicial.dominios and 
            estado_inicial.dominios[tema_objetivo] == NivelDominio.DOMINADO):
            return []  # Já atingiu o objetivo
        
        heap = []
        heapq.heappush(heap, (
            self.calcular_heuristica(estado_inicial, tema_objetivo),
            0.0,
            estado_inicial,
            []
        ))
        
        visitados: Set[EstadoAprendizagem] = set()
        melhores_custos: Dict[EstadoAprendizagem, float] = {estado_inicial: 0.0}
        
        iteracoes = 0
        MAX_ITERACOES = 1000
        
        while heap and iteracoes < MAX_ITERACOES:
            iteracoes += 1
            
            f_score, g_score, estado_atual, caminho = heapq.heappop(heap)
            
            if estado_atual in visitados:
                continue
            
            visitados.add(estado_atual)
            
            if (tema_objetivo in estado_atual.dominios and 
                estado_atual.dominios[tema_objetivo] == NivelDominio.DOMINADO):
                return caminho
            
            acoes_possiveis = self.gerar_acoes_possiveis(estado_atual)
            
            for acao in acoes_possiveis:
                novo_estado = self.aplicar_acao(estado_atual, acao)
                novo_caminho = caminho + [acao]
                novo_g_score = novo_estado.tempo_gasto_total
                
                if (novo_estado in visitados or 
                    (novo_estado in melhores_custos and novo_g_score >= melhores_custos[novo_estado])):
                    continue
                
                melhores_custos[novo_estado] = novo_g_score
                
                heuristica = self.calcular_heuristica(novo_estado, tema_objetivo)
                novo_f_score = novo_g_score + heuristica
                
                heapq.heappush(heap, (novo_f_score, novo_g_score, novo_estado, novo_caminho))
        
        return None
    
    def buscar_caminho_otimo_simples(self, estado_inicial: EstadoAprendizagem, 
                                     tema_objetivo: str) -> Optional[List[str]]:
        if tema_objetivo not in self.grafo_conhecimento:
            return None
        
        # Se já domina o objetivo
        if (tema_objetivo in estado_inicial.dominios and 
            estado_inicial.dominios[tema_objetivo] == NivelDominio.DOMINADO):
            return []
        
        temas_necessarios = set()
        
        def coletar_prerequisitos(tema):
            if tema in self.grafo_conhecimento:
                nivel_atual = estado_inicial.dominios.get(tema, NivelDominio.INEXISTENTE)
                
                if nivel_atual.value < NivelDominio.DOMINADO.value:
                    temas_necessarios.add(tema)
                
                for prereq in self.mapa_dependencias.get(tema, []):
                    coletar_prerequisitos(prereq)
        
        coletar_prerequisitos(tema_objetivo)
        
        def contar_prerequisitos_nao_dominados(tema):
            count = 0
            for prereq in self.mapa_dependencias.get(tema, []):
                if prereq in temas_necessarios:
                    count += 1
            return count
        
        temas_ordenados = sorted(temas_necessarios, 
                                key=lambda t: contar_prerequisitos_nao_dominados(t))
        
        return temas_ordenados
    
    def analisar_gaps_conhecimento(self, estado: EstadoAprendizagem) -> Dict[str, List[str]]:
        """
        Analisa gaps de conhecimento: temas bloqueados por falta de pré-requisitos.
        
        Retorna dicionário: {tema_bloqueado: [prerequisitos_em_falta]}
        """
        gaps = {}
        
        for tema, no in self.grafo_conhecimento.items():
            if tema in estado.dominios and estado.dominios[tema] == NivelDominio.DOMINADO:
                continue  # Já domina
            
            prerequisitos_em_falta = []
            for prereq in no.prerequisitos:
                if (prereq not in estado.dominios or 
                    estado.dominios[prereq].value < NivelDominio.BASICO.value):
                    prerequisitos_em_falta.append(prereq)
            
            if prerequisitos_em_falta:
                gaps[tema] = prerequisitos_em_falta
        
        return gaps
    
    def sugerir_proximo_tema_otimo(self, estado: EstadoAprendizagem, 
                                   tema_objetivo: str = None) -> Optional[str]:
        """
        Sugere o próximo tema ótimo para estudar.
        
        Se tema_objetivo for dado, usa A* para encontrar o próximo passo.
        Senão, sugere baseado em temas disponíveis e lacunas de conhecimento.
        """
        if tema_objetivo:
            # Usa A* para encontrar caminho até objetivo
            caminho = self.buscar_caminho_otimo_simples(estado, tema_objetivo)
            if caminho and len(caminho) > 0:
                return caminho[0]  # Primeiro passo do caminho ótimo
        
        # Estratégia alternativa: tema com pré-requisitos atendidos e maior impacto
        acoes_possiveis = self.gerar_acoes_possiveis(estado)
        
        if not acoes_possiveis:
            return None
        
        # Ordena por "impacto": quantos temas avançados este tema desbloqueia
        def calcular_impacto(tema: str) -> int:
            impacto = 0
            for outro_tema, prerequisitos in self.mapa_dependencias.items():
                if tema in prerequisitos:
                    impacto += 1
            return impacto
        
        # Ordena por impacto decrescente, depois por dificuldade crescente
        acoes_possiveis.sort(key=lambda t: (
            -calcular_impacto(t),  # Maior impacto primeiro
            self.grafo_conhecimento[t].dificuldade_aprendizado  # Menor dificuldade primeiro
        ))
        
        return acoes_possiveis[0]

# === INSTÂNCIA GLOBAL ===
navegador_global = NavegadorPrerequisitos()

def obter_navegador() -> NavegadorPrerequisitos:
    """Retorna a instância global do navegador."""
    return navegador_global

def analisar_caminho_aprendizagem(aluno_id: str, historico_df: pd.DataFrame, 
                                  tema_objetivo: str = None) -> Dict:
    navegador = obter_navegador()
    
    # Atualiza estado de conhecimento
    estado_atual = navegador.atualizar_estado_conhecimento(aluno_id, historico_df)
    
    # Analisa gaps
    gaps = navegador.analisar_gaps_conhecimento(estado_atual)
    
    # Temas que pode estudar agora
    temas_disponiveis = navegador.gerar_acoes_possiveis(estado_atual)
    
    # Sugestão de próximo tema
    proximo_tema = navegador.sugerir_proximo_tema_otimo(estado_atual, tema_objetivo)
    
    resultado = {
        'estado_conhecimento': {tema: nivel.name for tema, nivel in estado_atual.dominios.items()},
        'tempo_gasto_horas': round(estado_atual.tempo_gasto_total, 2),
        'gaps_conhecimento': gaps,
        'temas_disponiveis': temas_disponiveis,
        'proximo_tema_sugerido': proximo_tema,
        'caminho_otimo': None
    }
    
    # Se há objetivo específico, calcula caminho ótimo
    if tema_objetivo:
        caminho = navegador.buscar_caminho_otimo_simples(estado_atual, tema_objetivo)
        resultado['caminho_otimo'] = caminho
        resultado['tema_objetivo'] = tema_objetivo
    
    return resultado