
import streamlit as st
import matplotlib.pyplot as plt
import time
import io
from matplotlib.backends.backend_pdf import PdfPages

from util_dados import (
    carregar_questoes, filtrar_questoes, comparar_resposta,
    registrar_resposta, calcular_desempenho, calcular_metricas_agente,
    carregar_historico,
)
from recomendador import sugerir_proximo_tema

st.set_page_config(page_title="Assistente de Estudos", page_icon="📚", layout="centered")
st.title("📚 Assistente de Estudos — AIEP")

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
quantidade = st.sidebar.slider("Perguntas por sessão", min_value=1, max_value=20, value=5)

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

abas = st.tabs(["🎯 Quiz", "📈 Desempenho"])

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
        st.write(p["enunciado"])

        # Garante que o cronômetro seja iniciado ao exibir a pergunta
        if st.session_state.inicio_tempo is None:
            st.session_state.inicio_tempo = time.time()

        opcoes = list(p["alternativas"].keys())

        # key diferenciada por pergunta para evitar conflito entre radios
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

            # avança para a próxima pergunta
            st.session_state.indice += 1

            if st.session_state.indice >= len(st.session_state.perguntas):
                st.session_state.fim = True
                st.session_state.inicio_tempo = None
            else:
                st.session_state.inicio_tempo = time.time()


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
            st.dataframe(mostra, use_container_width=True)

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

st.markdown("---")
st.caption("Desenvolvido como assistente de estudos")
