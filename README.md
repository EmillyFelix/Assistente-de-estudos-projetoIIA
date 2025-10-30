
# Assistente de Estudos —  (MVP: Regras + Heurísticas)

Aplicativo simples em **Python** com **linha de comando** e **interface Streamlit**.
Apresenta perguntas de múltipla escolha, registra acertos/erros/tempo por aluno e recomenda próximos temas com regras heurísticas.

## Estrutura
```
assistente_estudos_pt/
├─ src/
│  ├─ util_dados.py
│  ├─ recomendador.py
│  ├─ executar_sessao.py
│  └─ relatorio.py
├─ dados/
│  ├─ questoes.json
│  └─ historico/
├─ testes/
│  ├─ teste_util_dados.py
│  └─ teste_recomendador.py
├─ relatorios/
│  └─ (gráficos gerados)
├─ requirements.txt
└─ README.md
```

## Instalação
Requer Python 3.9+.
```bash
cd assistente_estudos
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
```

## Linha de comando (CLI)
```bash
python -m src.executar_sessao --aluno-id ana --num-perguntas 5
# Filtros opcionais:
#   --tema "Lógica"
#   --dificuldade facil|medio|dificil
#   --recomendar-tema
```

## Relatório no console + gráfico
```bash
python -m src.relatorio --aluno-id ana
# Gráfico salvo em relatorios/desempenho_ana.png
```

## Interface Web (Streamlit)
```bash
streamlit run src/app_streamlit.py
```

## Testes
```bash
pytest -q
```
