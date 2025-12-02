
import streamlit as st
import matplotlib.pyplot as plt
import time
import io
from matplotlib.backends.backend_pdf import PdfPages

from util_dados import (
    carregar_questoes, filtrar_questoes, comparar_resposta,
    registrar_resposta, calcular_desempenho, calcular_metricas_agente,
    carregar_historico, carregar_historico_completo,
)
from recomendador import sugerir_proximo_tema
from modelo_preditivo import inicializar_modelo_performance, predizer_desempenho_aluno
from navegador_prerequisitos import analisar_caminho_aprendizagem, obter_navegador

st.set_page_config(page_title="Assistente de Estudos", page_icon="📚", layout="centered")
st.title("📚 Assistente de Estudos — AIEP")

# === INICIALIZAÇÃO DOS MODELOS DE IA ===
@st.cache_resource
def inicializar_modelos_ia():
    """Inicializa os modelos de Machine Learning (cache para performance)."""
    with st.spinner("🤖 Inicializando modelos de IA..."):
        # Carrega histórico completo de todos os alunos
        historico_completo = carregar_historico_completo()
        
        # Inicializa modelo preditivo
        modelo_pred = inicializar_modelo_performance(historico_completo)
        
        return modelo_pred

# Inicializa os modelos (só roda uma vez devido ao cache)
modelo_performance = inicializar_modelos_ia()

st.sidebar.header("Configurações")
aluno_id = st.sidebar.text_input("ID do aluno", value="ana")
usar_recomendacao = st.sidebar.checkbox("Usar recomendação de tema", value=False)

banco = carregar_questoes()
temas = sorted({q["tema"] for q in banco})

if usar_recomendacao and aluno_id.strip():
    recomendado = sugerir_proximo_tema(aluno_id.strip())
    if recomendado:
        st.sidebar.success(f"Tema recomendado: **{recomendado}**")
        tema = recomendado
    else:
        st.sidebar.info("Sem histórico para recomendar; selecione um tema.")
        tema = st.sidebar.selectbox("Tema", temas)
else:
    tema = st.sidebar.selectbox("Tema", temas)

dificuldade = st.sidebar.selectbox("Dificuldade", ["(todas)","facil","medio","dificil"], index=0)

# Calcula o máximo de questões disponíveis para o tema selecionado
qs_tema = filtrar_questoes(
    banco,
    tema=tema,
    dificuldade=None if dificuldade == "(todas)" else dificuldade,
)
max_questoes = len(qs_tema)

# Verifica se há questões disponíveis
if max_questoes == 0:
    st.sidebar.warning(f"⚠️ Nenhuma questão encontrada para o tema '{tema}' e dificuldade '{dificuldade}'")
    st.sidebar.text("Selecione outro tema ou dificuldade")
    st.stop()  # Para a execução aqui para evitar erro

# Garante que há pelo menos 2 questões para o slider funcionar
if max_questoes == 1:
    quantidade = 1
    st.sidebar.info(f"Apenas 1 questão disponível para '{tema}'")
else:
    quantidade = st.sidebar.slider(
        f"Perguntas por sessão (máx: {max_questoes})", 
        min_value=1, 
        max_value=max_questoes,
        value=min(5, max_questoes)
    )

if "perguntas" not in st.session_state:
    st.session_state.perguntas = []
if "indice" not in st.session_state:
    st.session_state.indice = 0
if "acertos" not in st.session_state:
    st.session_state.acertos = 0
if "fim" not in st.session_state:
    st.session_state.fim = False
if "inicio_tempo" not in st.session_state:
    st.session_state.inicio_tempo = None
if "nota_clareza" not in st.session_state:
    st.session_state.nota_clareza = 1.0
if "nota_adaptacao" not in st.session_state:
    st.session_state.nota_adaptacao = 1.0
if "modelo_ia_inicializado" not in st.session_state:
    st.session_state.modelo_ia_inicializado = False

def reiniciar_sessao():
    from random import shuffle
    st.session_state.indice = 0
    st.session_state.acertos = 0
    st.session_state.fim = False
    qs = filtrar_questoes(
        banco,
        tema=tema,
        dificuldade=None if dificuldade == "(todas)" else dificuldade,
    )

    # Evita repetir questões fáceis que já foram acertadas por este aluno
    if aluno_id.strip():
        df_hist = carregar_historico(aluno_id.strip())
        if not df_hist.empty:
            # IDs das questões fáceis já acertadas
            ids_faceis_acertadas = set(
                df_hist[
                    (df_hist["acertou"] == 1)
                    & (df_hist["dificuldade"].str.lower() == "facil")
                ]["pergunta_id"]
            )
            if dificuldade.lower() == "facil":
                qs = [q for q in qs if q.get("id") not in ids_faceis_acertadas]
            elif dificuldade == "(todas)":
                qs = [
                    q
                    for q in qs
                    if not (
                        q.get("dificuldade", "").lower() == "facil"
                        and q.get("id") in ids_faceis_acertadas
                    )
                ]

    shuffle(qs)
    st.session_state.perguntas = qs[:quantidade]
    if st.session_state.perguntas:
        st.session_state.inicio_tempo = time.time()
    else:
        st.session_state.inicio_tempo = None


st.sidebar.button("🔁 Reiniciar sessão", on_click=reiniciar_sessao)

if not st.session_state.perguntas:
    reiniciar_sessao()

# Inicializa modelo de IA (uma vez por sessão)
if not st.session_state.modelo_ia_inicializado:
    with st.spinner("🤖 Inicializando IA..."):
        historico_completo = carregar_historico_completo()
        inicializar_modelo_performance(historico_completo)
        st.session_state.modelo_ia_inicializado = True

abas = st.tabs(["🎯 Quiz", "📈 Desempenho", "🤖 O que estudar?"])

with abas[0]:
    # Sem perguntas configuradas ainda
    if not st.session_state.perguntas:
        st.info("Configure o tema na barra lateral e clique em 'Reiniciar sessão' para começar.")
    # Sessão já finalizada
    elif st.session_state.fim or st.session_state.indice >= len(st.session_state.perguntas):
        st.success(
            f"Sessão finalizada! Você acertou "
            f"{st.session_state.acertos}/{len(st.session_state.perguntas)}."
        )
    # Mostrar pergunta atual
    else:
        p = st.session_state.perguntas[st.session_state.indice]

        st.subheader(
            f"Pergunta {st.session_state.indice + 1} de {len(st.session_state.perguntas)}"
        )
        st.caption(f"Tema: **{p['tema']}** · Dificuldade: **{p['dificuldade']}**")
        
        # === PREDIÇÃO DE IA ===
        if aluno_id.strip() and st.session_state.modelo_ia_inicializado:
            historico_aluno = carregar_historico(aluno_id.strip())
            predicao = predizer_desempenho_aluno(
                aluno_id.strip(), 
                p, 
                historico_aluno, 
                st.session_state.indice
            )
            
            # Mostra predição de forma discreta
            col1, col2 = st.columns([3, 1])
            with col2:
                with st.expander("🤖 Predição IA", expanded=False):
                    prob = predicao['prob_acerto']
                    tempo = predicao['tempo_estimado']
                    
                    if prob > 0.7:
                        st.success(f"🎯 {prob:.1%} chance de acerto")
                    elif prob < 0.4:
                        st.warning(f"⚠️ {prob:.1%} chance de acerto")
                    else:
                        st.info(f"🤔 {prob:.1%} chance de acerto")
                    
                    st.caption(f"⏱️ Tempo estimado: {tempo:.0f}s")
                    st.caption(f"🎓 {predicao['explicacao']}")
        
        st.write(p["enunciado"])

        # Garante que o cronômetro seja iniciado ao exibir a pergunta
        if st.session_state.inicio_tempo is None:
            st.session_state.inicio_tempo = time.time()

        opcoes = list(p["alternativas"].keys())

        # key diferenciada por pergunta para evitar conflito entre radios
        # Verifica se já respondeu esta pergunta
        pergunta_respondida_key = f"respondida_{st.session_state.indice}"
        
        if not st.session_state.get(pergunta_respondida_key, False):
            # Ainda não respondeu - mostra opções e botão "Responder"
            escolha = st.radio(
                "Escolha uma alternativa:",
                opcoes,
                format_func=lambda k: f"{k}) {p['alternativas'][k]}",
                key=f"radio_pergunta_{st.session_state.indice}",
            )

            if st.button("Responder", key=f"btn_responder_{st.session_state.indice}"):
                # calcula o tempo gasto na questão atual
                tempo_gasto = 0.0
                if st.session_state.get("inicio_tempo") is not None:
                    tempo_gasto = time.time() - st.session_state.inicio_tempo

                correto = comparar_resposta(escolha, p["resposta_correta"])
                if correto:
                    st.success("✅ Correto!")
                    st.session_state.acertos += 1
                else:
                    st.error(f"❌ Errado — resposta correta: {p['resposta_correta']}")

                # registra resposta com o tempo real gasto
                registrar_resposta(
                    aluno_id.strip(),
                    p["id"],
                    bool(correto),
                    p["tema"],
                    p["dificuldade"],
                    tempo_gasto,
                )

                # Marca como respondida
                st.session_state[pergunta_respondida_key] = True
                st.session_state[f"resultado_{st.session_state.indice}"] = correto
                st.session_state[f"escolha_{st.session_state.indice}"] = escolha

        else:
            # Já respondeu - mostra resultado e botão "Próxima"
            escolha_feita = st.session_state.get(f"escolha_{st.session_state.indice}")
            resultado = st.session_state.get(f"resultado_{st.session_state.indice}")
            
            # Mostra as alternativas desabilitadas
            st.write("**Sua resposta:**")
            for opcao in opcoes:
                if opcao == escolha_feita:
                    if resultado:
                        st.success(f"✅ {opcao}) {p['alternativas'][opcao]} (Sua escolha)")
                    else:
                        st.error(f"❌ {opcao}) {p['alternativas'][opcao]} (Sua escolha)")
                elif opcao == p["resposta_correta"] and not resultado:
                    st.success(f"✅ {opcao}) {p['alternativas'][opcao]} (Correto)")
                else:
                    st.write(f"   {opcao}) {p['alternativas'][opcao]}")
            
            # Botão para próxima pergunta
            if st.session_state.indice + 1 < len(st.session_state.perguntas):
                if st.button("Próxima pergunta ➡️", key=f"btn_proxima_{st.session_state.indice}"):
                    st.session_state.indice += 1
                    st.session_state.inicio_tempo = time.time()
                    st.rerun()
            else:
                if st.button("Finalizar Quiz 🏁", key=f"btn_finalizar_{st.session_state.indice}"):
                    st.session_state.fim = True
                    st.session_state.inicio_tempo = None
                    st.rerun()


with abas[1]:
    st.subheader("Desempenho por tema")
    if not aluno_id.strip():
        st.info("Informe um ID de aluno para ver o desempenho.")
    else:
        df = calcular_desempenho(aluno_id.strip())
        if df.empty:
            st.info("Sem histórico ainda. Faça algumas questões no Quiz!")
        else:
            mostra = df.copy()
            mostra["taxa_acerto"] = mostra["taxa_acerto"].apply(lambda x: f"{x:.2f}")
            mostra["tempo_medio_segundos"] = mostra["tempo_medio_segundos"].apply(lambda x: f"{x:.2f}")
            st.dataframe(mostra, width="stretch")

            # Gráfico de barras — taxa de acerto por tema (desempenho do aluno)
            fig_bar = plt.figure()
            plt.bar(df["tema"], df["taxa_acerto"])
            plt.title(f"Taxa de acerto por tema — {aluno_id}")
            plt.xlabel("Tema")
            plt.ylabel("Taxa de acerto")
            plt.ylim(0, 1)
            plt.xticks(rotation=30, ha="right")
            plt.tight_layout()
            st.pyplot(fig_bar)

            # Gráfico de linhas — tempo médio de resposta por tema
            fig_line = plt.figure()
            plt.plot(df["tema"], df["tempo_medio_segundos"], marker="o")
            plt.title(f"Tempo médio de resposta por tema — {aluno_id}")
            plt.xlabel("Tema")
            plt.ylabel("Tempo médio (s)")
            plt.xticks(rotation=30, ha="right")
            plt.tight_layout()
            st.pyplot(fig_line)

            # Gráficos por dificuldade (usando histórico bruto)
            df_hist = carregar_historico(aluno_id.strip())
            if not df_hist.empty:
                # Distribuição de respostas por dificuldade (pizza)
                dist = df_hist.groupby("dificuldade")["acertou"].count().reset_index(name="total_respostas")
                fig_pizza = plt.figure()
                plt.pie(
                    dist["total_respostas"],
                    labels=dist["dificuldade"],
                    autopct="%1.1f%%",
                    startangle=90,
                )
                plt.title("Distribuição de respostas por dificuldade")
                plt.tight_layout()
                st.pyplot(fig_pizza)

            # Métricas de desempenho do agente (PEAS)
            st.markdown("### Métricas do agente (PEAS)")
            st.write(
                "As métricas abaixo seguem o modelo descrito no relatório: "
                "P₁ (precisão), P₂ (eficiência no tempo), "
                "P₃ (clareza) e P₄ (adaptação), com a pontuação geral D."
            )

            st.session_state.nota_clareza = st.slider(
                "P₃ — Clareza dos resultados (0 a 1)",
                0.0,
                1.0,
                float(st.session_state.nota_clareza),
                step=0.05,
            )
            st.session_state.nota_adaptacao = st.slider(
                "P₄ — Adaptação de dificuldade (0 a 1)",
                0.0,
                1.0,
                float(st.session_state.nota_adaptacao),
                step=0.05,
            )

            metricas = calcular_metricas_agente(
                aluno_id.strip(),
                tempo_limite_segundos=60.0,
                clareza=st.session_state.nota_clareza,
                adaptacao=st.session_state.nota_adaptacao,
            )

            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("P₁ — Precisão", f"{metricas['P1']:.2f}")
            col2.metric("P₂ — Eficiência", f"{metricas['P2']:.2f}")
            col3.metric("P₃ — Clareza", f"{metricas['P3']:.2f}")
            col4.metric("P₄ — Adaptação", f"{metricas['P4']:.2f}")
            col5.metric("D — Desempenho geral", f"{metricas['D']:.2f}")

            # Geração de relatório em PDF p/ download 
            buffer = io.BytesIO()
            with PdfPages(buffer) as pdf:
                pdf.savefig(fig_bar)
                pdf.savefig(fig_line)
                if 'fig_pizza' in locals():
                    pdf.savefig(fig_pizza)

            buffer.seek(0)
            st.download_button(
                "📄 Baixar relatório em PDF",
                data=buffer,
                file_name=f"relatorio_{aluno_id.strip()}.pdf",
                mime="application/pdf",
            )

with abas[2]:  # 🤖 O que estudar?
    st.subheader("Sugestões de Estudo")    
    if not aluno_id.strip():
        st.info("Informe um ID de aluno para ver o navegador de pré-requisitos.")
    else:
        historico_aluno = carregar_historico(aluno_id.strip())
        
        if historico_aluno.empty:
            st.info("Faça algumas questões no Quiz para gerar o mapa de conhecimento!")
        else:
            # === SUGESTÕES DE ESTUDO ===
            st.markdown("### 📚 O que estudar?")
            st.write("Baseado no que você já sabe, aqui estão algumas dicas:")
            
            # Análise do navegador de pré-requisitos
            navegacao = analisar_caminho_aprendizagem(aluno_id.strip(), historico_aluno)
            
            # Seletor de objetivo de aprendizagem
            navegador = obter_navegador()
            temas_objetivos = list(navegador.grafo_conhecimento.keys())
            tema_objetivo = st.selectbox(
                "💭 Que matéria você quer dominar?",
                ["(Escolha uma)"] + temas_objetivos,
                key="tema_objetivo_select"
            )
            
            if tema_objetivo != "(Escolha uma)":
                # Recalcula com objetivo específico
                navegacao = analisar_caminho_aprendizagem(
                    aluno_id.strip(), historico_aluno, tema_objetivo
                )
            
            # Próximo tema sugerido
            if navegacao['proximo_tema_sugerido']:
                st.info(f"💡 **Sugestão:** Que tal estudar **{navegacao['proximo_tema_sugerido']}**?")
            else:
                st.success("🎉 Parabéns! Você já domina o básico!")
            
            # Caminho para objetivo específico
            if navegacao.get('caminho_otimo') and tema_objetivo != "(Escolha uma)":
                caminho = navegacao['caminho_otimo']
                if caminho:
                    st.markdown(f"📋 **Para dominar {tema_objetivo}, estude nesta ordem:**")
                    for i, tema in enumerate(caminho, 1):
                        st.write(f"{i}. {tema}")
                else:
                    st.success(f"✅ Você já sabe {tema_objetivo}!")
            
            # Exibe análise em colunas
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 📊 Como você está")
                
                # Mostra só os temas que já estudou
                estudados = {tema: nivel for tema, nivel in navegacao['estado_conhecimento'].items() 
                            if nivel != 'INEXISTENTE'}
                
                if estudados:
                    for tema, nivel in estudados.items():
                        if nivel == "DOMINADO":
                            st.success(f"🏆 {tema} - Dominado")
                        elif nivel == "AVANCADO":
                            st.info(f"💪 {tema} - Quase lá")
                        elif nivel == "INTERMEDIARIO":
                            st.warning(f"📈 {tema} - Progredindo")
                        elif nivel == "BASICO":
                            st.error(f"🌱 {tema} - Começando")
                        else:
                            st.text(f"👶 {tema} - Iniciante")
                else:
                    st.info("Faça mais questões para ver seu progresso!")
            
            with col2:
                st.markdown("#### 🎯 Pode estudar agora")
                
                # Temas disponíveis
                if navegacao['temas_disponiveis']:
                    for tema in navegacao['temas_disponiveis']:
                        st.write(f"📚 {tema}")
                else:
                    st.info("Continue praticando os temas atuais!")
                
                # Tempo de estudo
                if navegacao['tempo_gasto_horas'] > 0:
                    st.metric("⏰ Tempo estudado", f"{navegacao['tempo_gasto_horas']:.1f}h")
            
            # === PREDIÇÕES DE PERFORMANCE ===
            st.markdown("### 🎯 Modelo Preditivo de Performance")
            st.write("O modelo Random Forest prediz seu desempenho futuro baseado em padrões de aprendizagem.")
            
            if st.session_state.perguntas and st.session_state.indice < len(st.session_state.perguntas):
                # Predição para próxima questão
                proxima_questao = st.session_state.perguntas[st.session_state.indice]
                predicao = predizer_desempenho_aluno(
                    aluno_id.strip(), 
                    proxima_questao, 
                    historico_aluno, 
                    st.session_state.indice
                )
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(
                        "Probabilidade de Acerto",
                        f"{predicao['prob_acerto']:.1%}",
                        delta=None
                    )
                with col2:
                    st.metric(
                        "Tempo Estimado",
                        f"{predicao['tempo_estimado']:.0f}s",
                        delta=None
                    )
                with col3:
                    st.metric(
                        "Confiança da IA",
                        f"{predicao['confianca']:.1%}",
                        delta=None
                    )
                
                st.info(f"🎓 **Explicação da IA:** {predicao['explicacao']}")
            
            # === DADOS TÉCNICOS (PARA CURIOSOS) ===
            with st.expander("🔧 Dados Técnicos da IA", expanded=False):
                if st.session_state.perguntas and st.session_state.indice < len(st.session_state.perguntas):
                    if 'features_utilizadas' in predicao:
                        st.markdown("#### Features do Modelo Preditivo")
                        features = predicao['features_utilizadas']
                        st.json(features)
                    else:
                        st.info("💡 Features do modelo serão exibidas após o modelo ser treinado com mais dados.")

st.markdown("---")
st.caption("Desenvolvido como assistente de estudos.")
