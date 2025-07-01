"""
Radar RH - Sistema de Análise de Rotatividade e Engajamento
Aplicação principal do Streamlit
"""

import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
from src.utils.config import Config
from src.components.header import render_header
from src.components.sidebar import render_sidebar
from src.pages import home, upload, dashboard, analysis, exports
from src.utils.helpers import init_session_state, apply_custom_css

# Configuração da página
st.set_page_config(
    page_title="Radar RH - Análise de Rotatividade",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'mailto:suporte@empresa.com',
        'Report a bug': 'mailto:suporte@empresa.com',
        'About': "Radar RH v1.0 - Sistema de Análise de Rotatividade e Engajamento"
    }
)

def main():
    """Função principal da aplicação"""
    
    # Inicializar estado da sessão
    init_session_state()
    
    # Aplicar CSS customizado
    apply_custom_css()
    
    # Renderizar header
    render_header()
    
    # Navegação principal
    with st.sidebar:
        selected_page = option_menu(
            menu_title="Navegação",
            options=["🏠 Início", "📤 Upload", "📊 Dashboard", "🔍 Análise", "📋 Exportar"],
            icons=["house", "upload", "graph-up", "search", "download"],
            menu_icon="cast",
            default_index=0,
            orientation="vertical",
            styles={
                "container": {"padding": "0!important", "background-color": "#fafafa"},
                "icon": {"color": "#1f77b4", "font-size": "18px"}, 
                "nav-link": {
                    "font-size": "14px", 
                    "text-align": "left", 
                    "margin": "0px",
                    "--hover-color": "#eee"
                },
                "nav-link-selected": {"background-color": "#1f77b4"},
            }
        )
        
        # Renderizar sidebar adicional
        render_sidebar()
    
    # Roteamento de páginas
    if selected_page == "🏠 Início":
        home.render()
    elif selected_page == "📤 Upload":
        upload.render()
    elif selected_page == "📊 Dashboard":
        dashboard.render()
    elif selected_page == "🔍 Análise":
        analysis.render()
    elif selected_page == "📋 Exportar":
        exports.render()
    
    # Footer
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            "<div style='text-align: center; color: #666; font-size: 12px;'>"
            "Radar RH v1.0 | Desenvolvido com ❤️ usando Streamlit"
            "</div>", 
            unsafe_allow_html=True
        )

if __name__ == "__main__":
    main()
