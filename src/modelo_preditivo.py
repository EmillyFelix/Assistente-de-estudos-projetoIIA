"""
Modelo Preditivo de Performance

Sistema de ML que prediz desempenho usando Random Forest.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, mean_squared_error
import pickle
import os
from datetime import datetime, time
from pathlib import Path

# Caminho para salvar os modelos treinados
PASTA_MODELOS = Path(__file__).resolve().parents[1] / "dados" / "modelos"
PASTA_MODELOS.mkdir(parents=True, exist_ok=True)

class ModeloPreditivoPerformance:
    """
    Sistema de IA que prediz o desempenho do aluno usando Random Forest.
    
    Como funciona:
    1. Coleta features (características) do aluno e questão
    2. Usa Random Forest para prever probabilidade de acerto e tempo
    3. Aprende continuamente com novos dados
    """
    
    def __init__(self):
        # Dois modelos separados: um para acerto (classificação) e outro para tempo (regressão)
        self.modelo_acerto = RandomForestClassifier(
            n_estimators=100,      # 100 árvores na "floresta"
            max_depth=10,          # Profundidade máxima de cada árvore
            random_state=42        # Para resultados reproduzíveis
        )
        
        self.modelo_tempo = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        
        self.encoder_tema = LabelEncoder()
        self.encoder_dificuldade = LabelEncoder()
        self.scaler = StandardScaler()
        
        self.modelo_treinado = False
        self.features_names = []
    
    def extrair_features(self, aluno_id, questao, historico_df, posicao_sessao=0):
        features = {}
        
        if not historico_df.empty:
            features['taxa_acerto_geral'] = historico_df['acertou'].mean()
            features['tempo_medio_geral'] = historico_df['tempo_segundos'].mean()
            features['total_questoes_feitas'] = len(historico_df)
            
            # Desempenho por tema
            hist_tema = historico_df[historico_df['tema'] == questao['tema']]
            if not hist_tema.empty:
                features['taxa_acerto_tema'] = hist_tema['acertou'].mean()
                features['tempo_medio_tema'] = hist_tema['tempo_segundos'].mean()
                features['experiencia_tema'] = len(hist_tema)
            else:
                features['taxa_acerto_tema'] = 0.5  # Neutro para temas novos
                features['tempo_medio_tema'] = 30.0
                features['experiencia_tema'] = 0
            
            # Desempenho por dificuldade
            hist_dif = historico_df[historico_df['dificuldade'] == questao['dificuldade']]
            if not hist_dif.empty:
                features['taxa_acerto_dificuldade'] = hist_dif['acertou'].mean()
                features['tempo_medio_dificuldade'] = hist_dif['tempo_segundos'].mean()
            else:
                features['taxa_acerto_dificuldade'] = 0.5
                features['tempo_medio_dificuldade'] = 30.0
            
            # Padrão de melhoria (está melhorando ao longo do tempo?)
            if len(historico_df) >= 5:
                ultimas_5 = historico_df.tail(5)['acertou'].mean()
                primeiras_5 = historico_df.head(5)['acertou'].mean()
                features['tendencia_melhoria'] = ultimas_5 - primeiras_5
            else:
                features['tendencia_melhoria'] = 0.0
        else:
            # Aluno novo - valores neutros
            features.update({
                'taxa_acerto_geral': 0.5,
                'tempo_medio_geral': 30.0,
                'total_questoes_feitas': 0,
                'taxa_acerto_tema': 0.5,
                'tempo_medio_tema': 30.0,
                'experiencia_tema': 0,
                'taxa_acerto_dificuldade': 0.5,
                'tempo_medio_dificuldade': 30.0,
                'tendencia_melhoria': 0.0
            })
        

        features['tema'] = questao['tema']
        features['dificuldade'] = questao['dificuldade']
        features['id_questao'] = questao['id']
        
        # Complexidade estimada do enunciado (número de palavras)
        features['complexidade_enunciado'] = len(questao['enunciado'].split())
        

        agora = datetime.now()
        features['hora_do_dia'] = agora.hour + agora.minute/60.0  # 14.5 = 14:30
        features['dia_da_semana'] = agora.weekday()  # 0=segunda, 6=domingo
        features['posicao_na_sessao'] = posicao_sessao  # 1ª, 2ª, 3ª questão...
        
        return features
    
    def preparar_dados_para_treino(self, historico_completo_df):
        """
        Prepara os dados históricos para treinar o modelo.
        
        Pega o histórico de TODOS os alunos e transforma em formato que o Random Forest entende.
        """
        if historico_completo_df.empty:
            return None, None, None, None
        
        print(f"📊 Preparando dados de {len(historico_completo_df)} respostas para treino...")
        
        X = []  # Features (características)
        y_acerto = []  # Target: acertou ou não
        y_tempo = []   # Target: tempo de resposta
        
        # Para cada aluno e cada resposta, extrair features
        for aluno_id in historico_completo_df['aluno_id'].unique():
            hist_aluno = historico_completo_df[historico_completo_df['aluno_id'] == aluno_id].copy()
            hist_aluno = hist_aluno.sort_values('momento')  # Ordem cronológica
            
            for i, (idx, row) in enumerate(hist_aluno.iterrows()):
                # Histórico ANTERIOR a esta resposta (simula situação real)
                hist_anterior = hist_aluno.iloc[:i] if i > 0 else pd.DataFrame()
                
                # Simula a questão atual
                questao_sim = {
                    'id': row['pergunta_id'],
                    'tema': row['tema'],
                    'dificuldade': row['dificuldade'],
                    'enunciado': f"Questão {row['pergunta_id']}"  # Simplificado
                }
                
                # Extrai features
                features = self.extrair_features(aluno_id, questao_sim, hist_anterior, i)
                
                X.append(features)
                y_acerto.append(row['acertou'])
                y_tempo.append(row['tempo_segundos'])
        
        if not X:
            return None, None, None, None
        
        # Converte para DataFrame
        X_df = pd.DataFrame(X)
        
        # Salva os nomes das colunas para usar depois
        self.features_names = X_df.columns.tolist()
        
        return X_df, np.array(y_acerto), np.array(y_tempo), X_df.columns.tolist()
    
    def treinar_modelo(self, historico_completo_df, salvar=True):
        """
        Treina o modelo Random Forest com dados históricos.
        
        É como "ensinar" a IA mostrando milhares de exemplos:
        "Nesta situação, o aluno acertou/errou e levou X segundos"
        """
        X_df, y_acerto, y_tempo, feature_names = self.preparar_dados_para_treino(historico_completo_df)
        
        if X_df is None:
            print("⚠️ Dados insuficientes para treinar o modelo")
            return False
        
        print(f"🚀 Treinando Random Forest com {len(X_df)} exemplos...")
        
        # Codifica variáveis categóricas (transforma texto em números)
        X_encoded = X_df.copy()
        
        # Temas únicos no dataset
        temas_unicos = X_encoded['tema'].unique()
        dificuldades_unicas = X_encoded['dificuldade'].unique()
        
        # Treina os encoders
        self.encoder_tema.fit(temas_unicos)
        self.encoder_dificuldade.fit(dificuldades_unicas)
        
        # Aplica a codificação
        X_encoded['tema'] = self.encoder_tema.transform(X_encoded['tema'])
        X_encoded['dificuldade'] = self.encoder_dificuldade.transform(X_encoded['dificuldade'])
        
        # Normaliza os dados (StandardScaler)
        X_scaled = self.scaler.fit_transform(X_encoded)
        
        # Divide dados: 80% treino, 20% teste
        X_train, X_test, y_acerto_train, y_acerto_test, y_tempo_train, y_tempo_test = train_test_split(
            X_scaled, y_acerto, y_tempo, test_size=0.2, random_state=42
        )
        
        # === TREINA MODELO DE ACERTO (CLASSIFICAÇÃO) ===
        print("🎯 Treinando modelo de predição de acerto...")
        self.modelo_acerto.fit(X_train, y_acerto_train)
        
        # Avalia performance no conjunto de teste
        pred_acerto = self.modelo_acerto.predict(X_test)
        acc_acerto = accuracy_score(y_acerto_test, pred_acerto)
        print(f"   ✅ Acurácia do modelo de acerto: {acc_acerto:.3f} ({acc_acerto*100:.1f}%)")
        
        # === TREINA MODELO DE TEMPO (REGRESSÃO) ===
        print("⏱️ Treinando modelo de predição de tempo...")
        self.modelo_tempo.fit(X_train, y_tempo_train)
        
        # Avalia performance
        pred_tempo = self.modelo_tempo.predict(X_test)
        mse_tempo = mean_squared_error(y_tempo_test, pred_tempo)
        print(f"   ✅ Erro médio quadrático do tempo: {mse_tempo:.2f}")
        
        self.modelo_treinado = True
        
        # Salva os modelos treinados
        if salvar:
            self.salvar_modelos()
        
        # Mostra as features mais importantes
        self.mostrar_importancia_features()
        
        return True
    
    def mostrar_importancia_features(self):
        """
        Mostra quais características são mais importantes para as predições.
        
        Isso é MUITO útil para entender como a IA está "pensando"!
        """
        if not self.modelo_treinado:
            return
        
        print("\n🔍 FEATURES MAIS IMPORTANTES:")
        
        # Importância para predição de acerto
        importancias_acerto = self.modelo_acerto.feature_importances_
        
        print("\n   📊 Para predizer ACERTO:")
        for i, importancia in enumerate(sorted(zip(self.features_names, importancias_acerto), 
                                               key=lambda x: x[1], reverse=True)[:5]):
            feature, valor = importancia
            print(f"      {i+1}. {feature}: {valor:.3f}")
        
        # Importância para predição de tempo
        importancias_tempo = self.modelo_tempo.feature_importances_
        
        print("\n   ⏱️ Para predizer TEMPO:")
        for i, importancia in enumerate(sorted(zip(self.features_names, importancias_tempo), 
                                               key=lambda x: x[1], reverse=True)[:5]):
            feature, valor = importancia
            print(f"      {i+1}. {feature}: {valor:.3f}")
    
    def predizer_performance(self, aluno_id, questao, historico_df, posicao_sessao=0):
        if not self.modelo_treinado:
            # Modelo não treinado - retorna estimativas neutras
            return {
                'prob_acerto': 0.5,
                'tempo_estimado': 30.0,
                'confianca': 0.0,
                'explicacao': 'Modelo ainda não foi treinado com dados suficientes.'
            }
        
        features = self.extrair_features(aluno_id, questao, historico_df, posicao_sessao)
        
        X_df = pd.DataFrame([features])
        
        try:
            X_df['tema'] = self.encoder_tema.transform([features['tema']])[0]
            X_df['dificuldade'] = self.encoder_dificuldade.transform([features['dificuldade']])[0]
        except ValueError:
            X_df['tema'] = 0
            X_df['dificuldade'] = 0
        
        X_scaled = self.scaler.transform(X_df[self.features_names])
        
        prob_acerto = self.modelo_acerto.predict_proba(X_scaled)[0][1]
        
        tempo_estimado = max(5.0, self.modelo_tempo.predict(X_scaled)[0])
        
        confianca = min(1.0, features['experiencia_tema'] / 10.0)
        
        explicacao = self._gerar_explicacao(features, prob_acerto, tempo_estimado)
        
        return {
            'prob_acerto': prob_acerto,
            'tempo_estimado': tempo_estimado,
            'confianca': confianca,
            'explicacao': explicacao,
            'features_utilizadas': features
        }
    
    def _gerar_explicacao(self, features, prob_acerto, tempo_estimado):
        explicacoes = []
        
        # Baseado na taxa de acerto geral
        if features['taxa_acerto_geral'] > 0.7:
            explicacoes.append("Seu histórico geral é excelente")
        elif features['taxa_acerto_geral'] < 0.4:
            explicacoes.append("Seu histórico geral indica dificuldades")
        
        # Baseado na experiência no tema
        if features['experiencia_tema'] > 5:
            explicacoes.append(f"Você tem boa experiência em {features['tema']}")
        elif features['experiencia_tema'] == 0:
            explicacoes.append(f"Este é seu primeiro contato com {features['tema']}")
        
        # Baseado na dificuldade
        if features['dificuldade'] == 'dificil':
            explicacoes.append("A questão é de nível difícil")
        elif features['dificuldade'] == 'facil':
            explicacoes.append("A questão é de nível fácil")
        
        # Baseado no horário
        hora = features['hora_do_dia']
        if hora < 12:
            explicacoes.append("Está estudando de manhã (boa concentração)")
        elif hora > 18:
            explicacoes.append("Está estudando à noite (possível cansaço)")
        
        if not explicacoes:
            return "Predição baseada no seu padrão geral de respostas."
        
        return "Fatores considerados: " + ", ".join(explicacoes) + "."
    
    def salvar_modelos(self):
        """Salva os modelos treinados para reutilização."""
        if not self.modelo_treinado:
            return
        
        try:
            # Salva modelo de acerto
            with open(PASTA_MODELOS / "modelo_acerto.pkl", "wb") as f:
                pickle.dump(self.modelo_acerto, f)
            
            # Salva modelo de tempo
            with open(PASTA_MODELOS / "modelo_tempo.pkl", "wb") as f:
                pickle.dump(self.modelo_tempo, f)
            
            # Salva encoders e scaler
            with open(PASTA_MODELOS / "encoders.pkl", "wb") as f:
                pickle.dump({
                    'encoder_tema': self.encoder_tema,
                    'encoder_dificuldade': self.encoder_dificuldade,
                    'scaler': self.scaler,
                    'features_names': self.features_names
                }, f)
            
            print(f"💾 Modelos salvos em {PASTA_MODELOS}")
        
        except Exception as e:
            print(f"⚠️ Erro ao salvar modelos: {e}")
    
    def carregar_modelos(self):
        """Carrega modelos previamente treinados."""
        try:
            # Carrega modelo de acerto
            with open(PASTA_MODELOS / "modelo_acerto.pkl", "rb") as f:
                self.modelo_acerto = pickle.load(f)
            
            # Carrega modelo de tempo
            with open(PASTA_MODELOS / "modelo_tempo.pkl", "rb") as f:
                self.modelo_tempo = pickle.load(f)
            
            # Carrega encoders
            with open(PASTA_MODELOS / "encoders.pkl", "rb") as f:
                data = pickle.load(f)
                self.encoder_tema = data['encoder_tema']
                self.encoder_dificuldade = data['encoder_dificuldade']
                self.scaler = data['scaler']
                self.features_names = data['features_names']
            
            self.modelo_treinado = True
            print(f"✅ Modelos carregados de {PASTA_MODELOS}")
            return True
        
        except FileNotFoundError:
            print("ℹ️ Nenhum modelo salvo encontrado. Será necessário treinar.")
            return False
        except Exception as e:
            print(f"⚠️ Erro ao carregar modelos: {e}")
            return False


# Instância global do modelo
modelo_performance = ModeloPreditivoPerformance()

def inicializar_modelo_performance(historico_completo_df=None):
    """
    Função principal para inicializar o modelo preditivo.
    
    Tenta carregar modelo salvo, se não existir, treina um novo.
    """
    global modelo_performance
    
    # Tenta carregar modelo existente
    if modelo_performance.carregar_modelos():
        return modelo_performance
    
    # Se não existe, treina um novo (se tiver dados)
    if historico_completo_df is not None and not historico_completo_df.empty:
        print("🚀 Treinando novo modelo preditivo...")
        modelo_performance.treinar_modelo(historico_completo_df)
    
    return modelo_performance

def predizer_desempenho_aluno(aluno_id, questao, historico_df, posicao_sessao=0):
    global modelo_performance
    return modelo_performance.predizer_performance(aluno_id, questao, historico_df, posicao_sessao)