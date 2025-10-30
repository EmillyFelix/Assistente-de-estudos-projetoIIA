
import streamlit as st
import matplotlib.pyplot as plt

from .util_dados import (
    carregar_questoes, filtrar_questoes, comparar_resposta,
    registrar_resposta, calcular_desempenho
)
from .recomendador import sugerir_proximo_tema

st.set_page_config(page_title="Assistente de Estudos", page_icon="📚", layout="centered")
st.title("📚 Assistente de Estudos — Português (MVP)")

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

def reiniciar_sessao():
    from random import shuffle
    st.session_state.indice = 0
    st.session_state.acertos = 0
    st.session_state.fim = False
    qs = filtrar_questoes(banco, tema=tema, dificuldade=None if dificuldade=="(todas)" else dificuldade)
    shuffle(qs)
    st.session_state.perguntas = qs[:quantidade]

st.sidebar.button("🔁 Reiniciar sessão", on_click=reiniciar_sessao)

if not st.session_state.perguntas:
    reiniciar_sessao()

abas = st.tabs(["🎯 Quiz", "📈 Desempenho"])

with abas[0]:
    if st.session_state.fim or st.session_state.indice >= len(st.session_state.perguntas):
        st.success(f"Sessão finalizada! Você acertou {st.session_state.acertos}/{len(st.session_state.perguntas)}.")
    else:
        p = st.session_state.perguntas[st.session_state.indice]
        st.subheader(f"Pergunta {st.session_state.indice+1} de {len(st.session_state.perguntas)}")
        st.caption(f"Tema: **{p['tema']}** · Dificuldade: **{p['dificuldade']}**")
        st.write(p["enunciado"])

        opcoes = list(p["alternativas"].keys())
        escolha = st.radio("Escolha uma alternativa:", opcoes, format_func=lambda k: f"{k}) {p['alternativas'][k]}")

        if st.button("Responder"):
            correto = comparar_resposta(escolha, p["resposta_correta"])
            if correto:
                st.success("✅ Correto!")
                st.session_state.acertos += 1
            else:
                st.error(f"❌ Errado — resposta correta: {p['resposta_correta']}")

            registrar_resposta(aluno_id.strip(), p["id"], bool(correto), p["tema"], p["dificuldade"], 0.0)
            st.session_state.indice += 1
            if st.session_state.indice >= len(st.session_state.perguntas):
                st.session_state.fim = True

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

            fig = plt.figure()
            plt.bar(df["tema"], df["taxa_acerto"])
            plt.title(f"Taxa de acerto por tema — {aluno_id}")
            plt.xlabel("Tema")
            plt.ylabel("Taxa de acerto")
            plt.ylim(0, 1)
            plt.xticks(rotation=30, ha="right")
            plt.tight_layout()
            st.pyplot(fig)

st.markdown("---")
st.caption("Desenvolvido como MVP para assistente de estudos em IA. 🚀")