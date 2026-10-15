"""TestingStudio Web — auditor de testes de software (Sprint 1: caixa-preta).

Este arquivo só monta a navegação entre as páginas; cada página fica em paginas/.
Executar:  python -m streamlit run app.py
"""

import streamlit as st

st.set_page_config(page_title="TestingStudio Web", page_icon="🧪", layout="wide")

pagina = st.navigation([
    st.Page("paginas/1_ler.py", title="Ler", icon="📄", default=True),
    st.Page("paginas/2_analisar.py", title="Analisar", icon="📐"),
    st.Page("paginas/3_revisar.py", title="Revisar", icon="🤖"),
])

with st.sidebar:
    st.title("🧪 TestingStudio Web")
    st.caption("Teste de Software I · Sprint 1 · Caixa-preta")
    st.markdown("1. **Ler** o `.txt` (código ou requisito)\n"
                "2. **Analisar**: ε, PCE, AVL e oráculo\n"
                "3. **Revisar** os casos com a IA")

pagina.run()
