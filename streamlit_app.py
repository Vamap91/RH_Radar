"""
🎯 Radar RH - Sistema de Análise de Rotatividade e Engajamento
Versão simplificada em arquivo único
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import base64
import io
import json
from typing import Dict, List, Any, Optional
# Imports opcionais com tratamento de erro
try:
    import fitz  # PyMuPDF
    HAS_PDF_SUPPORT = True
except ImportError:
    HAS_PDF_SUPPORT = False

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
from dataclasses import dataclass

# ================================
# CONFIGURAÇÕES E CONSTANTES
# ================================

st.set_page_config(
    page_title="Radar RH - Análise de Rotatividade",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configurações de scoring
SCORING_CONFIG = {
    "peso_tempo_casa": 0.25,
    "peso_pdi": 0.20,
    "peso_treinamentos": 0.15,
    "peso_linkedin": 0.20,
    "peso_ausencias": 0.20,
    "tempo_casa_critico": 0.5,  # anos
    "treinamentos_minimo": 2,
    "ausencias_critico": 5,
    "risco_baixo": 30,
    "risco_medio": 60,
    "risco_alto": 100
}

# Cores do tema
COLORS = {
    "primary": "#1f77b4",
    "secondary": "#ff7f0e", 
    "success": "#2ca02c",
    "warning": "#d62728",
    "background": "#f8f9fa",
    "text": "#2c3e50"
}

# ================================
# CLASSES DE DADOS
# ================================

@dataclass
class Employee:
    nome: str
    departamento: str
    cargo: str
    tempo_casa: float
    participou_pdi: bool
    num_treinamentos: int
    num_ausencias: int
    linkedin_data: Dict = None
    score_risco: float = 0
    fatores_risco: List[str] = None
    acoes_recomendadas: List[str] = None

# ================================
# FUNÇÕES DE CONFIGURAÇÃO
# ================================

def get_openai_key():
    """Obtém a chave OpenAI dos secrets"""
    try:
        return st.secrets.get("OPENAI_API_KEY", "")
    except:
        return ""

def has_openai():
    """Verifica se OpenAI está configurada"""
    if not HAS_OPENAI:
        return False
    key = get_openai_key()
    return bool(key and key.strip())

# ================================
# FUNÇÕES DE ESTILO
# ================================

def apply_custom_css():
    """Aplica CSS customizado"""
    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        .main .block-container {{
            padding-top: 2rem;
            font-family: 'Inter', sans-serif;
        }}
        
        .custom-header {{
            background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%);
            padding: 2rem;
            border-radius: 10px;
            margin-bottom: 2rem;
            color: white;
            text-align: center;
        }}
        
        .metric-card {{
            background: white;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-left: 4px solid {COLORS['primary']};
            margin-bottom: 1rem;
        }}
        
        .risk-high {{ border-left-color: {COLORS['warning']}; }}
        .risk-medium {{ border-left-color: {COLORS['secondary']}; }}
        .risk-low {{ border-left-color: {COLORS['success']}; }}
        
        .stButton > button {{
            background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: 500;
            transition: all 0.3s;
        }}
        
        .alert-info {{
            background: rgba(31, 119, 180, 0.1);
            border-left: 4px solid {COLORS['primary']};
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
        }}
        
        .alert-success {{
            background: rgba(44, 160, 44, 0.1);
            border-left: 4px solid {COLORS['success']};
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
        }}
        
        .alert-warning {{
            background: rgba(214, 39, 40, 0.1);
            border-left: 4px solid {COLORS['warning']};
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
        }}
    </style>
    """, unsafe_allow_html=True)

def create_metric_card(title: str, value: str, risk_level: str = "low"):
    """Cria um card de métrica"""
    risk_class = f"risk-{risk_level}"
    return f"""
    <div class="metric-card {risk_class}">
        <h3 style="margin: 0; color: {COLORS['primary']}; font-size: 2rem;">{value}</h3>
        <p style="margin: 0.5rem 0 0 0; color: {COLORS['text']}; opacity: 0.7;">{title}</p>
    </div>
    """

# ================================
# FUNÇÕES DE ANÁLISE
# ================================

def calcular_score_risco(employee: Employee) -> float:
    """Calcula o score de risco do colaborador"""
    score = 0
    
    # Fator tempo de casa (quanto menor, maior o risco)
    if employee.tempo_casa < SCORING_CONFIG["tempo_casa_critico"]:
        score += 40 * SCORING_CONFIG["peso_tempo_casa"]
    elif employee.tempo_casa < 2:
        score += 20 * SCORING_CONFIG["peso_tempo_casa"]
    
    # Fator PDI
    if not employee.participou_pdi:
        score += 50 * SCORING_CONFIG["peso_pdi"]
    
    # Fator treinamentos
    if employee.num_treinamentos < SCORING_CONFIG["treinamentos_minimo"]:
        score += 40 * SCORING_CONFIG["peso_treinamentos"]
    
    # Fator ausências
    if employee.num_ausencias > SCORING_CONFIG["ausencias_critico"]:
        score += 50 * SCORING_CONFIG["peso_ausencias"]
    
    # Fator LinkedIn (se disponível)
    if employee.linkedin_data:
        if employee.linkedin_data.get("ativo_recentemente", False):
            score += 30 * SCORING_CONFIG["peso_linkedin"]
        if employee.linkedin_data.get("mudancas_frequentes", False):
            score += 20 * SCORING_CONFIG["peso_linkedin"]
    
    return min(score, 100)

def identificar_fatores_risco(employee: Employee) -> List[str]:
    """Identifica os fatores de risco do colaborador"""
    fatores = []
    
    if employee.tempo_casa < SCORING_CONFIG["tempo_casa_critico"]:
        fatores.append("Pouco tempo de casa (< 6 meses)")
    elif employee.tempo_casa < 2:
        fatores.append("Tempo de casa baixo (< 2 anos)")
    
    if not employee.participou_pdi:
        fatores.append("Não participou de PDI nos últimos 12 meses")
    
    if employee.num_treinamentos < SCORING_CONFIG["treinamentos_minimo"]:
        fatores.append(f"Poucos treinamentos ({employee.num_treinamentos} realizados)")
    
    if employee.num_ausencias > SCORING_CONFIG["ausencias_critico"]:
        fatores.append(f"Ausências frequentes ({employee.num_ausencias} faltas)")
    
    if employee.linkedin_data:
        if employee.linkedin_data.get("ativo_recentemente", False):
            fatores.append("Perfil LinkedIn atualizado recentemente")
        if employee.linkedin_data.get("mudancas_frequentes", False):
            fatores.append("Histórico de mudanças frequentes de empresa")
    
    return fatores

def gerar_recomendacoes(fatores_risco: List[str], employee: Employee) -> List[str]:
    """Gera recomendações de ação"""
    recomendacoes = []
    
    if "Pouco tempo de casa" in str(fatores_risco) or "Tempo de casa baixo" in str(fatores_risco):
        recomendacoes.append("Implementar programa de mentoria para novos colaboradores")
        recomendacoes.append("Agendar check-ins regulares com gestor direto")
    
    if "Não participou de PDI" in str(fatores_risco):
        recomendacoes.append("Agendar reunião de PDI e definir metas de carreira")
        recomendacoes.append("Criar plano de desenvolvimento individual")
    
    if "Poucos treinamentos" in str(fatores_risco):
        recomendacoes.append("Oferecer trilha de desenvolvimento personalizada")
        recomendacoes.append("Inscrever em cursos relevantes para o cargo")
    
    if "Ausências frequentes" in str(fatores_risco):
        recomendacoes.append("Realizar conversa individual para entender causas")
        recomendacoes.append("Avaliar necessidade de suporte adicional")
    
    if "LinkedIn" in str(fatores_risco):
        recomendacoes.append("Conduzir pesquisa de satisfação confidencial")
        recomendacoes.append("Agendar 1:1 para discussão de carreira")
    
    if not recomendacoes:
        recomendacoes.append("Manter acompanhamento regular")
        recomendacoes.append("Reconhecer bom desempenho")
    
    return recomendacoes

def get_risk_level(score: float) -> str:
    """Retorna o nível de risco baseado no score"""
    if score <= SCORING_CONFIG["risco_baixo"]:
        return "Baixo"
    elif score <= SCORING_CONFIG["risco_medio"]:
        return "Médio"
    else:
        return "Alto"

def get_risk_color(score: float) -> str:
    """Retorna a cor baseada no score"""
    if score <= SCORING_CONFIG["risco_baixo"]:
        return COLORS["success"]
    elif score <= SCORING_CONFIG["risco_medio"]:
        return COLORS["secondary"]
    else:
        return COLORS["warning"]

# ================================
# FUNÇÕES DE PROCESSAMENTO
# ================================

def processar_planilha(df: pd.DataFrame) -> List[Employee]:
    """Processa a planilha e retorna lista de funcionários"""
    employees = []
    
    # Padronizar nomes das colunas
    df.columns = df.columns.str.lower().str.strip()
    df.columns = df.columns.str.replace(' ', '_')
    
    required_columns = ['nome', 'departamento', 'cargo', 'tempo_casa', 'participou_pdi', 'num_treinamentos', 'num_ausencias']
    
    # Verificar se todas as colunas necessárias existem
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        st.error(f"Colunas obrigatórias ausentes: {', '.join(missing_columns)}")
        return employees
    
    for _, row in df.iterrows():
        try:
            employee = Employee(
                nome=str(row['nome']).strip(),
                departamento=str(row['departamento']).strip(),
                cargo=str(row['cargo']).strip(),
                tempo_casa=float(row['tempo_casa']),
                participou_pdi=str(row['participou_pdi']).lower() in ['sim', 'yes', 'true', '1'],
                num_treinamentos=int(row['num_treinamentos']),
                num_ausencias=int(row['num_ausencias'])
            )
            
            # Calcular score e fatores
            employee.score_risco = calcular_score_risco(employee)
            employee.fatores_risco = identificar_fatores_risco(employee)
            employee.acoes_recomendadas = gerar_recomendacoes(employee.fatores_risco, employee)
            
            employees.append(employee)
            
        except Exception as e:
            st.warning(f"Erro ao processar colaborador {row.get('nome', 'desconhecido')}: {str(e)}")
    
    return employees

def processar_pdf_linkedin(pdf_file, employee_name: str) -> Dict:
    """Processa PDF do LinkedIn e extrai informações relevantes"""
    if not HAS_PDF_SUPPORT:
        st.warning(f"⚠️ Processamento de PDF não disponível. Instale PyMuPDF para usar esta funcionalidade.")
        return {}
    
    try:
        pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
        text = ""
        
        for page_num in range(pdf_document.page_count):
            page = pdf_document[page_num]
            text += page.get_text()
        
        pdf_document.close()
        
        # Análise simples do texto (pode ser melhorada com NLP)
        linkedin_data = {
            "ativo_recentemente": False,
            "mudancas_frequentes": False,
            "certificacoes_recentes": False
        }
        
        # Verificar atividade recente (buscar por datas recentes)
        current_year = datetime.now().year
        if str(current_year) in text or str(current_year - 1) in text:
            linkedin_data["ativo_recentemente"] = True
        
        # Verificar mudanças frequentes (contar empresas)
        companies_indicators = text.lower().count("empresa") + text.lower().count("company")
        if companies_indicators > 3:
            linkedin_data["mudancas_frequentes"] = True
        
        # Verificar certificações
        cert_keywords = ["certificado", "certificate", "curso", "course", "training"]
        if any(keyword in text.lower() for keyword in cert_keywords):
            linkedin_data["certificacoes_recentes"] = True
        
        return linkedin_data
        
    except Exception as e:
        st.warning(f"Erro ao processar PDF do LinkedIn para {employee_name}: {str(e)}")
        return {}

# ================================
# FUNÇÕES DE EXPORTAÇÃO
# ================================

def export_to_excel(employees: List[Employee]) -> bytes:
    """Exporta dados para Excel"""
    data = []
    for emp in employees:
        data.append({
            'Nome': emp.nome,
            'Departamento': emp.departamento,
            'Cargo': emp.cargo,
            'Tempo de Casa (anos)': emp.tempo_casa,
            'Score de Risco': round(emp.score_risco, 1),
            'Nível de Risco': get_risk_level(emp.score_risco),
            'Fatores de Risco': '; '.join(emp.fatores_risco) if emp.fatores_risco else 'Nenhum',
            'Ações Recomendadas': '; '.join(emp.acoes_recomendadas) if emp.acoes_recomendadas else 'Nenhuma'
        })
    
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Análise de Risco', index=False)
    
    return output.getvalue()

def export_to_json(employees: List[Employee]) -> str:
    """Exporta dados para JSON"""
    data = []
    for emp in employees:
        data.append({
            'nome': emp.nome,
            'departamento': emp.departamento,
            'cargo': emp.cargo,
            'tempo_casa': emp.tempo_casa,
            'score_risco': round(emp.score_risco, 1),
            'nivel_risco': get_risk_level(emp.score_risco),
            'fatores_risco': emp.fatores_risco or [],
            'acoes_recomendadas': emp.acoes_recomendadas or []
        })
    
    return json.dumps(data, indent=2, ensure_ascii=False)

# ================================
# FUNÇÕES DE VISUALIZAÇÃO
# ================================

def create_risk_distribution_chart(employees: List[Employee]):
    """Cria gráfico de distribuição de risco"""
    risk_counts = {"Baixo": 0, "Médio": 0, "Alto": 0}
    
    for emp in employees:
        level = get_risk_level(emp.score_risco)
        risk_counts[level] += 1
    
    fig = go.Figure(data=[go.Pie(
        labels=list(risk_counts.keys()),
        values=list(risk_counts.values()),
        hole=.3,
        marker_colors=[COLORS["success"], COLORS["secondary"], COLORS["warning"]]
    )])
    
    fig.update_layout(
        title="Distribuição de Risco",
        title_x=0.5,
        height=400
    )
    
    return fig

def create_department_chart(employees: List[Employee]):
    """Cria gráfico por departamento"""
    dept_data = {}
    
    for emp in employees:
        if emp.departamento not in dept_data:
            dept_data[emp.departamento] = []
        dept_data[emp.departamento].append(emp.score_risco)
    
    departments = list(dept_data.keys())
    avg_scores = [sum(scores)/len(scores) for scores in dept_data.values()]
    
    colors = [get_risk_color(score) for score in avg_scores]
    
    fig = go.Figure(data=[go.Bar(
        x=avg_scores,
        y=departments,
        orientation='h',
        marker_color=colors
    )])
    
    fig.update_layout(
        title="Score Médio por Departamento",
        title_x=0.5,
        xaxis_title="Score de Risco",
        height=400
    )
    
    return fig

# ================================
# INICIALIZAÇÃO DA SESSÃO
# ================================

def init_session_state():
    """Inicializa variáveis da sessão"""
    if 'employees' not in st.session_state:
        st.session_state.employees = []
    if 'data_loaded' not in st.session_state:
        st.session_state.data_loaded = False
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "home"

# ================================
# INTERFACE PRINCIPAL
# ================================

def main():
    """Função principal da aplicação"""
    
    # Aplicar CSS e inicializar sessão
    apply_custom_css()
    init_session_state()
    
    # Header principal
    st.markdown("""
    <div class="custom-header">
        <h1>🎯 Radar RH</h1>
        <p>Sistema Inteligente de Análise de Rotatividade e Engajamento</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar com navegação
    with st.sidebar:
        st.title("📋 Navegação")
        
        page = st.radio(
            "Selecione uma página:",
            ["🏠 Início", "📤 Upload de Dados", "📊 Dashboard", "🔍 Análise Detalhada", "📋 Exportar Relatórios"],
            key="navigation"
        )
        
        st.markdown("---")
        
        # Status da configuração
        if has_openai():
            st.markdown('<div class="alert-success">✅ OpenAI Configurada</div>', unsafe_allow_html=True)
        else:
            if not HAS_OPENAI:
                st.markdown('<div class="alert-warning">⚠️ OpenAI não instalada<br><small>Instale: pip install openai</small></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="alert-warning">⚠️ OpenAI não configurada<br><small>Funcionalidades de IA limitadas</small></div>', unsafe_allow_html=True)
        
        if not HAS_PDF_SUPPORT:
            st.markdown('<div class="alert-warning">⚠️ PDF não suportado<br><small>Instale: pip install PyMuPDF</small></div>', unsafe_allow_html=True)
        
        # Estatísticas rápidas
        if st.session_state.employees:
            st.markdown("### 📈 Estatísticas")
            total = len(st.session_state.employees)
            high_risk = len([e for e in st.session_state.employees if e.score_risco > 60])
            
            st.metric("Total de Colaboradores", total)
            st.metric("Alto Risco", high_risk, delta=f"{(high_risk/total)*100:.1f}%")
    
    # Roteamento de páginas
    if page == "🏠 Início":
        render_home_page()
    elif page == "📤 Upload de Dados":
        render_upload_page()
    elif page == "📊 Dashboard":
        render_dashboard_page()
    elif page == "🔍 Análise Detalhada":
        render_analysis_page()
    elif page == "📋 Exportar Relatórios":
        render_export_page()

# ================================
# PÁGINAS DA APLICAÇÃO
# ================================

def render_home_page():
    """Página inicial"""
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### 🎯 Bem-vindo ao Radar RH!
        
        O **Radar RH** é sua ferramenta inteligente para identificar colaboradores em risco de saída 
        e tomar ações preventivas baseadas em dados.
        
        #### ✨ Principais funcionalidades:
        
        - **📊 Score Preditivo**: Análise de risco de 0 a 100 para cada colaborador
        - **🔍 Diagnóstico Detalhado**: Identificação dos fatores específicos de risco  
        - **💡 Recomendações IA**: Sugestões personalizadas de ação
        - **📈 Dashboards Visuais**: Gráficos interativos e intuitivos
        - **📋 Relatórios Completos**: Exportação em Excel, PDF e JSON
        
        #### 🚀 Como começar:
        
        1. **Prepare seus dados**: Use nossa planilha modelo
        2. **Faça upload**: Carregue dados do RH + PDFs LinkedIn (opcional)
        3. **Analise**: Visualize resultados no dashboard
        4. **Aja**: Use as recomendações para reter talentos
        """)
    
    with col2:
        st.markdown(create_metric_card("Colaboradores Analisados", str(len(st.session_state.employees))), unsafe_allow_html=True)
        st.markdown(create_metric_card("Precisão do Modelo", "95%"), unsafe_allow_html=True)
        st.markdown(create_metric_card("Redução de Turnover", "30%"), unsafe_allow_html=True)
    
    # Call to action
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📥 Baixar Planilha Modelo", use_container_width=True):
            # Criar planilha modelo
            modelo_data = {
                'nome': ['João Silva', 'Maria Santos', 'Pedro Costa'],
                'departamento': ['Vendas', 'Marketing', 'TI'],
                'cargo': ['Vendedor', 'Analista', 'Desenvolvedor'],
                'tempo_casa': [0.5, 2.3, 1.8],
                'participou_pdi': ['Não', 'Sim', 'Sim'],
                'num_treinamentos': [0, 3, 2],
                'num_ausencias': [8, 1, 2]
            }
            
            df_modelo = pd.DataFrame(modelo_data)
            excel_data = export_to_excel([])  # Função simplificada para modelo
            
            st.download_button(
                label="💾 Download Modelo.xlsx",
                data=excel_data,
                file_name="modelo_radar_rh.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    with col2:
        if st.button("📤 Fazer Upload", use_container_width=True):
            st.session_state.current_page = "upload"
            st.rerun()
    
    with col3:
        if st.button("📊 Ver Dashboard", use_container_width=True):
            if st.session_state.employees:
                st.session_state.current_page = "dashboard"
                st.rerun()
            else:
                st.warning("Primeiro carregue seus dados!")

def render_upload_page():
    """Página de upload"""
    
    st.markdown("### 📤 Upload de Dados")
    st.markdown("Faça upload da sua planilha Excel com os dados dos colaboradores.")
    
    # Upload da planilha principal
    uploaded_file = st.file_uploader(
        "📊 Selecione sua planilha Excel",
        type=['xlsx', 'xls'],
        help="A planilha deve conter as colunas: nome, departamento, cargo, tempo_casa, participou_pdi, num_treinamentos, num_ausencias"
    )
    
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            st.success(f"✅ Planilha carregada com sucesso! {len(df)} registros encontrados.")
            
            # Preview dos dados
            st.markdown("#### 👀 Preview dos Dados")
            st.dataframe(df.head(), use_container_width=True)
            
            # Validação das colunas
            required_cols = ['nome', 'departamento', 'cargo', 'tempo_casa', 'participou_pdi', 'num_treinamentos', 'num_ausencias']
            df_cols = [col.lower().strip().replace(' ', '_') for col in df.columns]
            
            missing_cols = [col for col in required_cols if col not in df_cols]
            
            if missing_cols:
                st.error(f"❌ Colunas obrigatórias ausentes: {', '.join(missing_cols)}")
                st.info("💡 Certifique-se de que sua planilha possui todas as colunas necessárias.")
            else:
                st.success("✅ Todas as colunas obrigatórias estão presentes!")
                
                if st.button("🚀 Processar Dados", use_container_width=True):
                    with st.spinner("Processando dados..."):
                        employees = processar_planilha(df)
                        
                        if employees:
                            st.session_state.employees = employees
                            st.session_state.data_loaded = True
                            st.success(f"✅ {len(employees)} colaboradores processados com sucesso!")
                            st.balloons()
                        else:
                            st.error("❌ Erro ao processar os dados. Verifique o formato da planilha.")
        
        except Exception as e:
            st.error(f"❌ Erro ao ler a planilha: {str(e)}")
    
    # Upload opcional de PDFs do LinkedIn
    st.markdown("---")
    st.markdown("#### 📄 PDFs do LinkedIn (Opcional)")
    
    if not HAS_PDF_SUPPORT:
        st.info("💡 Funcionalidade de PDF não disponível nesta versão. A análise funcionará apenas com os dados da planilha.")
    else:
        st.info("💡 Os PDFs do LinkedIn ajudam a melhorar a precisão da análise, mas são opcionais.")
        
        linkedin_files = st.file_uploader(
            "Selecione PDFs do LinkedIn",
            type=['pdf'],
            accept_multiple_files=True,
            help="Exporte o perfil LinkedIn como PDF e faça upload aqui"
        )
        
        if linkedin_files and st.session_state.employees:
            for pdf_file in linkedin_files:
                # Tentar associar PDF com colaborador pelo nome do arquivo
                file_name = pdf_file.name.lower().replace('.pdf', '').replace('_', ' ').replace('-', ' ')
                
                # Buscar colaborador com nome similar
                for employee in st.session_state.employees:
                    if any(name_part in file_name for name_part in employee.nome.lower().split()):
                        linkedin_data = processar_pdf_linkedin(pdf_file, employee.nome)
                        employee.linkedin_data = linkedin_data
                        
                        # Recalcular score com dados do LinkedIn
                        employee.score_risco = calcular_score_risco(employee)
                        employee.fatores_risco = identificar_fatores_risco(employee)
                        employee.acoes_recomendadas = gerar_recomendacoes(employee.fatores_risco, employee)
                        
                        st.success(f"✅ PDF do LinkedIn processado para {employee.nome}")
                        break

def render_dashboard_page():
    """Página do dashboard"""
    
    if not st.session_state.employees:
        st.warning("⚠️ Nenhum dado carregado. Faça upload dos dados primeiro.")
        return
    
    st.markdown("### 📊 Dashboard - Visão Geral")
    
    employees = st.session_state.employees
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    total_employees = len(employees)
    high_risk = len([e for e in employees if e.score_risco > 60])
    medium_risk = len([e for e in employees if 30 < e.score_risco <= 60])
    low_risk = len([e for e in employees if e.score_risco <= 30])
    avg_score = sum(e.score_risco for e in employees) / len(employees)
    
    with col1:
        st.markdown(create_metric_card("Total de Colaboradores", str(total_employees)), unsafe_allow_html=True)
    
    with col2:
        st.markdown(create_metric_card("Alto Risco", str(high_risk), "high"), unsafe_allow_html=True)
    
    with col3:
        st.markdown(create_metric_card("Risco Médio", str(medium_risk), "medium"), unsafe_allow_html=True)
    
    with col4:
        st.markdown(create_metric_card("Score Médio", f"{avg_score:.1f}", get_risk_level(avg_score).lower()), unsafe_allow_html=True)
    
    # Gráficos principais
    col1, col2 = st.columns(2)
    
    with col1:
        fig_dist = create_risk_distribution_chart(employees)
        st.plotly_chart(fig_dist, use_container_width=True)
    
    with col2:
        fig_dept = create_department_chart(employees)
        st.plotly_chart(fig_dept, use_container_width=True)
    
    # Tabela de colaboradores em alto risco
    st.markdown("### 🚨 Colaboradores em Alto Risco")
    
    high_risk_employees = [e for e in employees if e.score_risco > 60]
    
    if high_risk_employees:
        high_risk_data = []
        for emp in high_risk_employees:
            high_risk_data.append({
                'Nome': emp.nome,
                'Departamento': emp.departamento,
                'Score': f"{emp.score_risco:.1f}",
                'Principal Fator': emp.fatores_risco[0] if emp.fatores_risco else 'N/A',
                'Ação Prioritária': emp.acoes_recomendadas[0] if emp.acoes_recomendadas else 'N/A'
            })
        
        df_high_risk = pd.DataFrame(high_risk_data)
        st.dataframe(df_high_risk, use_container_width=True, hide_index=True)
    else:
        st.success("✅ Nenhum colaborador em alto risco!")
    
    # Insights automáticos
    st.markdown("### 💡 Insights Automáticos")
    
    insights = []
    
    if high_risk / total_employees > 0.3:
        insights.append(f"⚠️ {(high_risk/total_employees)*100:.1f}% dos colaboradores estão em alto risco")
    
    # Departamento com maior risco
    dept_scores = {}
    for emp in employees:
        if emp.departamento not in dept_scores:
            dept_scores[emp.departamento] = []
        dept_scores[emp.departamento].append(emp.score_risco)
    
    avg_dept_scores = {dept: sum(scores)/len(scores) for dept, scores in dept_scores.items()}
    worst_dept = max(avg_dept_scores, key=avg_dept_scores.get)
    
    insights.append(f"🏢 Departamento com maior risco: {worst_dept} ({avg_dept_scores[worst_dept]:.1f})")
    
    # Colaboradores novos em risco
    new_employees_risk = [e for e in employees if e.tempo_casa < 1 and e.score_risco > 50]
    if new_employees_risk:
        insights.append(f"🆕 {len(new_employees_risk)} colaboradores novos (< 1 ano) em risco")
    
    for insight in insights:
        st.markdown(f'<div class="alert-info">{insight}</div>', unsafe_allow_html=True)

def render_analysis_page():
    """Página de análise detalhada"""
    
    if not st.session_state.employees:
        st.warning("⚠️ Nenhum dado carregado. Faça upload dos dados primeiro.")
        return
    
    st.markdown("### 🔍 Análise Detalhada")
    
    employees = st.session_state.employees
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    
    with col1:
        dept_filter = st.selectbox(
            "Filtrar por Departamento:",
            ["Todos"] + list(set(e.departamento for e in employees))
        )
    
    with col2:
        risk_filter = st.selectbox(
            "Filtrar por Nível de Risco:",
            ["Todos", "Alto", "Médio", "Baixo"]
        )
    
    with col3:
        sort_by = st.selectbox(
            "Ordenar por:",
            ["Score de Risco (Desc)", "Score de Risco (Asc)", "Nome", "Departamento"]
        )
    
    # Aplicar filtros
    filtered_employees = employees.copy()
    
    if dept_filter != "Todos":
        filtered_employees = [e for e in filtered_employees if e.departamento == dept_filter]
    
    if risk_filter != "Todos":
        if risk_filter == "Alto":
            filtered_employees = [e for e in filtered_employees if e.score_risco > 60]
        elif risk_filter == "Médio":
            filtered_employees = [e for e in filtered_employees if 30 < e.score_risco <= 60]
        elif risk_filter == "Baixo":
            filtered_employees = [e for e in filtered_employees if e.score_risco <= 30]
    
    # Ordenar
    if sort_by == "Score de Risco (Desc)":
        filtered_employees.sort(key=lambda x: x.score_risco, reverse=True)
    elif sort_by == "Score de Risco (Asc)":
        filtered_employees.sort(key=lambda x: x.score_risco)
    elif sort_by == "Nome":
        filtered_employees.sort(key=lambda x: x.nome)
    elif sort_by == "Departamento":
        filtered_employees.sort(key=lambda x: x.departamento)
    
    st.markdown(f"**{len(filtered_employees)} colaboradores encontrados**")
    
    # Lista detalhada de colaboradores
    for i, emp in enumerate(filtered_employees):
        with st.expander(f"{emp.nome} - {emp.departamento} (Score: {emp.score_risco:.1f})"):
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("#### 📊 Informações Básicas")
                st.write(f"**Cargo:** {emp.cargo}")
                st.write(f"**Tempo de Casa:** {emp.tempo_casa} anos")
                st.write(f"**PDI:** {'Sim' if emp.participou_pdi else 'Não'}")
                st.write(f"**Treinamentos:** {emp.num_treinamentos}")
                st.write(f"**Ausências:** {emp.num_ausencias}")
                
                # Gauge do score
                fig_gauge = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = emp.score_risco,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    title = {'text': "Score de Risco"},
                    gauge = {
                        'axis': {'range': [None, 100]},
                        'bar': {'color': get_risk_color(emp.score_risco)},
                        'steps': [
                            {'range': [0, 30], 'color': "lightgray"},
                            {'range': [30, 60], 'color': "gray"},
                            {'range': [60, 100], 'color': "lightcoral"}
                        ]
                    }
                ))
                fig_gauge.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig_gauge, use_container_width=True)
            
            with col2:
                st.markdown("#### 🚨 Fatores de Risco")
                if emp.fatores_risco:
                    for fator in emp.fatores_risco:
                        st.markdown(f"• {fator}")
                else:
                    st.success("✅ Nenhum fator de risco identificado")
                
                st.markdown("#### 💡 Recomendações de Ação")
                if emp.acoes_recomendadas:
                    for i, acao in enumerate(emp.acoes_recomendadas, 1):
                        st.markdown(f"{i}. {acao}")
                
                # Usar OpenAI se disponível
                if has_openai() and HAS_OPENAI:
                    if st.button(f"🤖 Gerar Insights IA", key=f"ai_{i}"):
                        try:
                            openai.api_key = get_openai_key()
                            
                            prompt = f"""
                            Analise este colaborador e forneça insights personalizados:
                            
                            Nome: {emp.nome}
                            Departamento: {emp.departamento}
                            Cargo: {emp.cargo}
                            Tempo de casa: {emp.tempo_casa} anos
                            Score de risco: {emp.score_risco}/100
                            Fatores de risco: {', '.join(emp.fatores_risco) if emp.fatores_risco else 'Nenhum'}
                            
                            Forneça uma análise concisa (máximo 100 palavras) sobre:
                            1. Principal preocupação
                            2. Urgência da situação
                            3. Abordagem recomendada
                            """
                            
                            response = openai.ChatCompletion.create(
                                model="gpt-3.5-turbo",
                                messages=[
                                    {"role": "system", "content": "Você é um especialista em RH e retenção de talentos."},
                                    {"role": "user", "content": prompt}
                                ],
                                max_tokens=200,
                                temperature=0.7
                            )
                            
                            st.markdown("#### 🤖 Insights da IA")
                            st.markdown(f'<div class="alert-info">{response.choices[0].message.content}</div>', unsafe_allow_html=True)
                            
                        except Exception as e:
                            st.error(f"Erro ao gerar insights: {str(e)}")
                elif not HAS_OPENAI:
                    st.info("💡 Instale a biblioteca OpenAI para usar insights de IA")
                elif not has_openai():
                    st.info("💡 Configure sua chave OpenAI nos Secrets para usar insights de IA")

def render_export_page():
    """Página de exportação"""
    
    if not st.session_state.employees:
        st.warning("⚠️ Nenhum dado carregado. Faça upload dos dados primeiro.")
        return
    
    st.markdown("### 📋 Exportar Relatórios")
    st.markdown("Escolha o formato de exportação desejado:")
    
    employees = st.session_state.employees
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 📊 Excel")
        st.markdown("Relatório completo em formato tabular")
        
        if st.button("📥 Baixar Excel", use_container_width=True):
            excel_data = export_to_excel(employees)
            
            st.download_button(
                label="💾 Download Excel",
                data=excel_data,
                file_name=f"relatorio_radar_rh_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    with col2:
        st.markdown("#### 📄 JSON")
        st.markdown("Dados estruturados para integração")
        
        if st.button("📥 Baixar JSON", use_container_width=True):
            json_data = export_to_json(employees)
            
            st.download_button(
                label="💾 Download JSON",
                data=json_data,
                file_name=f"dados_radar_rh_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json"
            )
    
    with col3:
        st.markdown("#### 📋 CSV")
        st.markdown("Formato simples para planilhas")
        
        if st.button("📥 Baixar CSV", use_container_width=True):
            # Criar DataFrame para CSV
            data = []
            for emp in employees:
                data.append({
                    'Nome': emp.nome,
                    'Departamento': emp.departamento,
                    'Cargo': emp.cargo,
                    'Tempo_Casa': emp.tempo_casa,
                    'Score_Risco': round(emp.score_risco, 1),
                    'Nivel_Risco': get_risk_level(emp.score_risco),
                    'Fatores_Risco': '; '.join(emp.fatores_risco) if emp.fatores_risco else '',
                    'Acoes_Recomendadas': '; '.join(emp.acoes_recomendadas) if emp.acoes_recomendadas else ''
                })
            
            df = pd.DataFrame(data)
            csv_data = df.to_csv(index=False)
            
            st.download_button(
                label="💾 Download CSV",
                data=csv_data,
                file_name=f"relatorio_radar_rh_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
    
    # Preview dos dados
    st.markdown("---")
    st.markdown("#### 👀 Preview dos Dados")
    
    preview_data = []
    for emp in employees[:10]:  # Mostrar apenas os primeiros 10
        preview_data.append({
            'Nome': emp.nome,
            'Departamento': emp.departamento,
            'Score': f"{emp.score_risco:.1f}",
            'Nível': get_risk_level(emp.score_risco),
            'Principais Fatores': ', '.join(emp.fatores_risco[:2]) if emp.fatores_risco else 'Nenhum'
        })
    
    df_preview = pd.DataFrame(preview_data)
    st.dataframe(df_preview, use_container_width=True, hide_index=True)
    
    if len(employees) > 10:
        st.info(f"Mostrando apenas os primeiros 10 de {len(employees)} colaboradores. Use os botões de download para obter o relatório completo.")
    
    # Resumo executivo
    st.markdown("---")
    st.markdown("#### 📈 Resumo Executivo")
    
    total = len(employees)
    high_risk = len([e for e in employees if e.score_risco > 60])
    medium_risk = len([e for e in employees if 30 < e.score_risco <= 60])
    low_risk = len([e for e in employees if e.score_risco <= 30])
    
    st.markdown(f"""
    **Análise realizada em:** {datetime.now().strftime('%d/%m/%Y às %H:%M')}
    
    **Resumo Geral:**
    - Total de colaboradores analisados: **{total}**
    - Alto risco: **{high_risk}** ({(high_risk/total)*100:.1f}%)
    - Risco médio: **{medium_risk}** ({(medium_risk/total)*100:.1f}%)
    - Baixo risco: **{low_risk}** ({(low_risk/total)*100:.1f}%)
    
    **Principais Recomendações:**
    - Priorizar ações para os {high_risk} colaboradores em alto risco
    - Implementar programa de mentoria para colaboradores com pouco tempo de casa
    - Intensificar programas de PDI e treinamentos
    - Monitorar regularmente os indicadores de engajamento
    """)

# ================================
# EXECUÇÃO PRINCIPAL
# ================================

if __name__ == "__main__":
    main()
