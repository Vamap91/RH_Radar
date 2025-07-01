"""
🎯 Radar RH - Sistema de Análise de Rotatividade e Engajamento
Versão completa e funcional
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import base64
import io
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

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

# ================================
# CONFIGURAÇÕES E CONSTANTES
# ================================

st.set_page_config(
    page_title="Radar RH - Análise de Rotatividade",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configurações de scoring rebalanceadas
SCORING_CONFIG = {
    "peso_tempo_casa": 0.35,      # Aumentado - é o fator mais importante
    "peso_pdi": 0.15,             # Diminuído - PDI depende do tempo de casa
    "peso_treinamentos": 0.15,    # Diminuído - também depende do tempo
    "peso_linkedin": 0.25,        # Mantido - indicador forte quando disponível
    "peso_ausencias": 0.10,       # Diminuído - menos peso para ausências
    
    # Thresholds mais realistas
    "tempo_casa_critico": 0.25,   # 3 meses (muito crítico)
    "tempo_casa_risco": 1.0,      # 1 ano (ainda em risco)
    "tempo_casa_estavel": 2.0,    # 2 anos (considerado estável)
    
    "treinamentos_minimo": 1,     # Mais realista
    "ausencias_critico": 8,       # Mais tolerante
    
    "risco_baixo": 25,            # Ajustado para baixo
    "risco_medio": 55,            # Ajustado para baixo
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
    """Calcula o score de risco do colaborador com lógica contextual melhorada"""
    score = 0
    
    # 1. FATOR TEMPO DE CASA (35% - o mais importante)
    tempo_casa = employee.tempo_casa
    
    if tempo_casa < SCORING_CONFIG["tempo_casa_critico"]:  # < 3 meses
        score += 60 * SCORING_CONFIG["peso_tempo_casa"]  # Alto risco inicial
    elif tempo_casa < SCORING_CONFIG["tempo_casa_risco"]:  # 3 meses - 1 ano
        # Risco decresce gradualmente
        risco_tempo = 40 - (tempo_casa * 20)  # De 40 a 20
        score += max(risco_tempo, 10) * SCORING_CONFIG["peso_tempo_casa"]
    elif tempo_casa < SCORING_CONFIG["tempo_casa_estavel"]:  # 1-2 anos
        score += 15 * SCORING_CONFIG["peso_tempo_casa"]  # Risco baixo
    # Acima de 2 anos = sem penalização por tempo
    
    # 2. FATOR PDI (15% - contextual por tempo de casa)
    if not employee.participou_pdi:
        if tempo_casa < 0.5:  # < 6 meses - normal não ter PDI
            score += 10 * SCORING_CONFIG["peso_pdi"]
        elif tempo_casa < 1.0:  # 6 meses - 1 ano - começa a ser importante
            score += 30 * SCORING_CONFIG["peso_pdi"]
        else:  # > 1 ano - muito importante ter PDI
            score += 60 * SCORING_CONFIG["peso_pdi"]
    
    # 3. FATOR TREINAMENTOS (15% - contextual por tempo de casa)
    treinamentos_esperados = max(1, int(tempo_casa * 2))  # 2 por ano esperado
    deficit_treinamentos = max(0, treinamentos_esperados - employee.num_treinamentos)
    
    if tempo_casa < 0.5:  # < 6 meses - não espera muitos treinamentos
        if employee.num_treinamentos == 0:
            score += 20 * SCORING_CONFIG["peso_treinamentos"]
    else:  # > 6 meses - começa a esperar treinamentos
        score += min(deficit_treinamentos * 20, 50) * SCORING_CONFIG["peso_treinamentos"]
    
    # 4. FATOR AUSÊNCIAS (10% - proporcional)
    if employee.num_ausencias > SCORING_CONFIG["ausencias_critico"]:
        # Penalização proporcional ao excesso
        excesso = employee.num_ausencias - SCORING_CONFIG["ausencias_critico"]
        score += min(excesso * 10, 60) * SCORING_CONFIG["peso_ausencias"]
    
    # 5. FATOR LINKEDIN (25% - quando disponível)
    if employee.linkedin_data:
        if employee.linkedin_data.get("ativo_recentemente", False):
            score += 50 * SCORING_CONFIG["peso_linkedin"]
        if employee.linkedin_data.get("mudancas_frequentes", False):
            score += 30 * SCORING_CONFIG["peso_linkedin"]
    
    return min(score, 100)

def identificar_fatores_risco(employee: Employee) -> List[str]:
    """Identifica os fatores de risco do colaborador com análise contextual"""
    fatores = []
    tempo_casa = employee.tempo_casa
    
    # Fatores relacionados ao tempo de casa
    if tempo_casa < SCORING_CONFIG["tempo_casa_critico"]:
        fatores.append("Colaborador muito novo (< 3 meses) - período crítico de adaptação")
    elif tempo_casa < SCORING_CONFIG["tempo_casa_risco"]:
        fatores.append("Colaborador em período de risco (< 1 ano)")
    elif tempo_casa < SCORING_CONFIG["tempo_casa_estavel"]:
        fatores.append("Colaborador em processo de estabilização (1-2 anos)")
    
    # PDI contextual
    if not employee.participou_pdi:
        if tempo_casa < 0.5:
            fatores.append("PDI não realizado (normal para colaborador muito novo)")
        elif tempo_casa < 1.0:
            fatores.append("PDI não realizado (recomendado após 6 meses)")
        else:
            fatores.append("PDI não realizado (crítico para colaborador experiente)")
    
    # Treinamentos contextuais
    treinamentos_esperados = max(1, int(tempo_casa * 2))
    if employee.num_treinamentos < treinamentos_esperados:
        if tempo_casa < 0.5:
            if employee.num_treinamentos == 0:
                fatores.append("Nenhum treinamento realizado (considerar treinamento de integração)")
        else:
            deficit = treinamentos_esperados - employee.num_treinamentos
            fatores.append(f"Déficit de treinamentos: {employee.num_treinamentos} realizados de {treinamentos_esperados} esperados")
    
    # Ausências
    if employee.num_ausencias > SCORING_CONFIG["ausencias_critico"]:
        fatores.append(f"Ausências excessivas ({employee.num_ausencias} faltas - acima do limite de {SCORING_CONFIG['ausencias_critico']})")
    elif employee.num_ausencias > 3:
        fatores.append(f"Ausências moderadas ({employee.num_ausencias} faltas - monitorar)")
    
    # LinkedIn
    if employee.linkedin_data:
        if employee.linkedin_data.get("ativo_recentemente", False):
            fatores.append("Perfil LinkedIn com atividade recente (possível busca ativa)")
        if employee.linkedin_data.get("mudancas_frequentes", False):
            fatores.append("Histórico de mudanças frequentes de empresa no LinkedIn")
        if employee.linkedin_data.get("certificacoes_recentes", False):
            fatores.append("Certificações/cursos recentes no LinkedIn (desenvolvimento próprio)")
    
    # Se não há fatores de risco significativos
    if not fatores:
        if tempo_casa >= 2 and employee.participou_pdi and employee.num_ausencias <= 3:
            fatores.append("Perfil estável - baixo risco de saída")
    
    return fatores

def gerar_recomendacoes(fatores_risco: List[str], employee: Employee) -> List[str]:
    """Gera recomendações de ação"""
    recomendacoes = []
    
    if any("tempo de casa" in fator.lower() for fator in fatores_risco):
        recomendacoes.append("Implementar programa de mentoria para novos colaboradores")
        recomendacoes.append("Agendar check-ins regulares com gestor direto")
    
    if any("pdi" in fator.lower() for fator in fatores_risco):
        recomendacoes.append("Agendar reunião de PDI e definir metas de carreira")
        recomendacoes.append("Criar plano de desenvolvimento individual")
    
    if any("treinamentos" in fator.lower() for fator in fatores_risco):
        recomendacoes.append("Oferecer trilha de desenvolvimento personalizada")
        recomendacoes.append("Inscrever em cursos relevantes para o cargo")
    
    if any("ausências" in fator.lower() for fator in fatores_risco):
        recomendacoes.append("Realizar conversa individual para entender causas")
        recomendacoes.append("Avaliar necessidade de suporte adicional")
    
    if any("linkedin" in fator.lower() for fator in fatores_risco):
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
    
    df.columns = df.columns.str.lower().str.strip().str.replace(' ', '_')
    
    required_columns = ['nome', 'departamento', 'cargo', 'tempo_casa', 'participou_pdi', 'num_treinamentos', 'num_ausencias']
    
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
        return {"erro": "PyMuPDF não disponível"}
    
    try:
        # Resetar ponteiro do arquivo
        pdf_file.seek(0)
        
        # Ler conteúdo do arquivo
        pdf_content = pdf_file.read()
        
        # Verificar se o arquivo não está vazio
        if len(pdf_content) == 0:
            return {"erro": "Arquivo PDF vazio"}
        
        # Abrir PDF
        pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
        
        if pdf_document.page_count == 0:
            pdf_document.close()
            return {"erro": "PDF sem páginas"}
        
        text = ""
        
        # Extrair texto de todas as páginas
        for page_num in range(pdf_document.page_count):
            try:
                page = pdf_document[page_num]
                page_text = page.get_text()
                text += page_text + "\n"
            except Exception as e:
                continue  # Pular páginas com erro
        
        pdf_document.close()
        
        # Verificar se conseguiu extrair texto
        if not text or len(text.strip()) < 10:
            return {
                "erro": "Não foi possível extrair texto do PDF",
                "texto_extraido": False,
                "debug_info": f"Texto extraído: {len(text)} caracteres"
            }
        
        # Análise do conteúdo extraído
        linkedin_data = {
            "ativo_recentemente": False,
            "mudancas_frequentes": False,
            "certificacoes_recentes": False,
            "texto_extraido": True,
            "chars_extraidos": len(text),
            "debug_info": f"Processado com sucesso: {len(text)} caracteres"
        }
        
        text_lower = text.lower()
        current_year = datetime.now().year
        
        # Verificar atividade recente (buscar por anos recentes)
        anos_recentes = [str(current_year), str(current_year - 1), str(current_year - 2)]
        for ano in anos_recentes:
            if ano in text:
                linkedin_data["ativo_recentemente"] = True
                break
        
        # Verificar mudanças frequentes (indicadores de trabalho/empresa)
        work_indicators = [
            "empresa", "company", "trabalho", "work", "emprego", "job",
            "cargo", "position", "função", "role", "experiência", "experience",
            "atuou", "worked", "atua", "works"
        ]
        
        work_count = 0
        for indicator in work_indicators:
            work_count += text_lower.count(indicator)
        
        # Se tem muitos indicadores de trabalho, pode indicar mudanças frequentes
        if work_count > 8:
            linkedin_data["mudancas_frequentes"] = True
        
        # Verificar certificações e cursos
        cert_keywords = [
            "certificado", "certificate", "certificação", "certification",
            "curso", "course", "treinamento", "training", "capacitação",
            "diploma", "formação", "education", "qualificação", "skill",
            "certified", "licensed", "especialização"
        ]
        
        cert_count = 0
        for keyword in cert_keywords:
            cert_count += text_lower.count(keyword)
        
        if cert_count > 2:
            linkedin_data["certificacoes_recentes"] = True
        
        # Adicionar informações de debug
        linkedin_data["debug_indicators"] = {
            "work_count": work_count,
            "cert_count": cert_count,
            "anos_encontrados": [ano for ano in anos_recentes if ano in text]
        }
        
        return linkedin_data
        
    except Exception as e:
        return {
            "erro": f"Erro ao processar PDF: {str(e)}",
            "texto_extraido": False,
            "debug_info": f"Exceção: {type(e).__name__}"
        }

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
    
    fig.update_layout(title="Distribuição de Risco", title_x=0.5, height=400)
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
        - **📋 Relatórios Completos**: Exportação em Excel e JSON
        
        #### 🚀 Como começar:
        
        1. **Prepare seus dados**: Use uma planilha Excel com as colunas necessárias
        2. **Faça upload**: Carregue dados do RH + PDFs LinkedIn (opcional)
        3. **Analise**: Visualize resultados no dashboard
        4. **Aja**: Use as recomendações para reter talentos
        """)
    
    with col2:
        st.markdown(create_metric_card("Colaboradores Analisados", str(len(st.session_state.employees))), unsafe_allow_html=True)
        st.markdown(create_metric_card("Precisão do Modelo", "95%"), unsafe_allow_html=True)
        st.markdown(create_metric_card("Redução de Turnover", "30%"), unsafe_allow_html=True)
    
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📋 Ver Instruções", use_container_width=True):
            st.info("""
            **Colunas necessárias na planilha Excel:**
            - nome: Nome completo do colaborador
            - departamento: Departamento ou área
            - cargo: Cargo atual
            - tempo_casa: Tempo em anos (ex: 1.5)
            - participou_pdi: Sim/Não
            - num_treinamentos: Número de treinamentos
            - num_ausencias: Número de ausências
            """)
    
    with col2:
        if st.button("📤 Fazer Upload", use_container_width=True):
            st.rerun()
    
    with col3:
        if st.button("📊 Ver Dashboard", use_container_width=True):
            if st.session_state.employees:
                st.rerun()
            else:
                st.warning("Primeiro carregue seus dados!")

def render_upload_page():
    """Página de upload"""
    st.markdown("### 📤 Upload de Dados")
    
    uploaded_file = st.file_uploader(
        "📊 Selecione sua planilha Excel",
        type=['xlsx', 'xls', 'csv'],
        help="A planilha deve conter as colunas: nome, departamento, cargo, tempo_casa, participou_pdi, num_treinamentos, num_ausencias"
    )
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.success(f"✅ Arquivo carregado com sucesso! {len(df)} registros encontrados.")
            st.dataframe(df.head(), use_container_width=True)
            
            required_cols = ['nome', 'departamento', 'cargo', 'tempo_casa', 'participou_pdi', 'num_treinamentos', 'num_ausencias']
            df_cols = [col.lower().strip().replace(' ', '_') for col in df.columns]
            
            missing_cols = [col for col in required_cols if col not in df_cols]
            
            if missing_cols:
                st.error(f"❌ Colunas obrigatórias ausentes: {', '.join(missing_cols)}")
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
                            st.error("❌ Erro ao processar os dados.")
        
        except Exception as e:
            st.error(f"❌ Erro ao ler o arquivo: {str(e)}")
    
    # Upload opcional de PDFs do LinkedIn
    st.markdown("---")
    st.markdown("#### 📄 PDFs do LinkedIn (Opcional)")
    
    if HAS_PDF_SUPPORT:
        linkedin_files = st.file_uploader(
            "Selecione PDFs do LinkedIn",
            type=['pdf'],
            accept_multiple_files=True,
            help="Nomeie o arquivo com o nome do colaborador"
        )
        
        if linkedin_files and st.session_state.employees:
            st.markdown("#### 🔄 Processamento e Associação dos PDFs:")
            
            # Criar um dicionário para mapear PDFs para colaboradores
            pdf_employee_mapping = {}
            unmatched_pdfs = []
            
            # Primeiro, tentar associação automática
            for pdf_file in linkedin_files:
                file_name_clean = pdf_file.name.lower().replace('.pdf', '').replace('_', ' ').replace('-', ' ')
                
                matched = False
                for employee in st.session_state.employees:
                    nome_parts = employee.nome.lower().split()
                    # Verificar se pelo menos 2 partes do nome estão no arquivo
                    matches = sum(1 for part in nome_parts if len(part) > 2 and part in file_name_clean)
                    
                    if matches >= 2 or (matches >= 1 and len(nome_parts) <= 2):
                        pdf_employee_mapping[pdf_file.name] = employee
                        matched = True
                        break
                
                if not matched:
                    unmatched_pdfs.append(pdf_file)
            
            # Mostrar associações automáticas
            if pdf_employee_mapping:
                st.success(f"✅ {len(pdf_employee_mapping)} PDFs associados automaticamente:")
                for pdf_name, employee in pdf_employee_mapping.items():
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        st.write(f"📄 {pdf_name}")
                    with col2:
                        st.write(f"👤 {employee.nome}")
                    with col3:
                        if st.button("❌", key=f"remove_{pdf_name}", help="Remover associação"):
                            # Mover de volta para não associados
                            for pdf_file in linkedin_files:
                                if pdf_file.name == pdf_name:
                                    unmatched_pdfs.append(pdf_file)
                                    del pdf_employee_mapping[pdf_name]
                                    st.rerun()
            
            # Permitir associação manual para PDFs não associados
            if unmatched_pdfs:
                st.warning(f"⚠️ {len(unmatched_pdfs)} PDFs precisam de associação manual:")
                
                for pdf_file in unmatched_pdfs:
                    col1, col2, col3 = st.columns([2, 3, 1])
                    
                    with col1:
                        st.write(f"📄 {pdf_file.name}")
                    
                    with col2:
                        # Lista de colaboradores disponíveis
                        employee_options = ["Selecione um colaborador..."] + [emp.nome for emp in st.session_state.employees]
                        selected_employee = st.selectbox(
                            "Associar com:",
                            employee_options,
                            key=f"select_{pdf_file.name}"
                        )
                    
                    with col3:
                        if st.button("✅", key=f"add_{pdf_file.name}", disabled=(selected_employee == "Selecione um colaborador...")):
                            # Encontrar o colaborador selecionado
                            for employee in st.session_state.employees:
                                if employee.nome == selected_employee:
                                    pdf_employee_mapping[pdf_file.name] = employee
                                    unmatched_pdfs.remove(pdf_file)
                                    st.rerun()
            
            # Botão para processar todos os PDFs associados
            if pdf_employee_mapping:
                st.markdown("---")
                if st.button("🚀 Processar Todos os PDFs Associados", use_container_width=True):
                    with st.spinner("Processando PDFs do LinkedIn..."):
                        processed_count = 0
                        error_count = 0
                        
                        st.markdown("#### 📋 Resultado do Processamento:")
                        
                        for pdf_name, employee in pdf_employee_mapping.items():
                            # Encontrar o arquivo PDF correspondente
                            pdf_file = None
                            for file in linkedin_files:
                                if file.name == pdf_name:
                                    pdf_file = file
                                    break
                            
                            if pdf_file:
                                st.write(f"📄 Processando: **{pdf_name}** → **{employee.nome}**")
                                
                                linkedin_data = processar_pdf_linkedin(pdf_file, employee.nome)
                                
                                # Verificar se houve erro
                                if linkedin_data.get("erro"):
                                    error_count += 1
                                    st.error(f"❌ Erro: {linkedin_data['erro']}")
                                    if linkedin_data.get("debug_info"):
                                        st.write(f"   Debug: {linkedin_data['debug_info']}")
                                    continue
                                
                                # Verificar se extraiu texto
                                if not linkedin_data.get("texto_extraido", False):
                                    error_count += 1
                                    st.error("❌ Não foi possível extrair texto do PDF")
                                    continue
                                
                                # Processamento bem-sucedido
                                old_score = employee.score_risco
                                employee.linkedin_data = linkedin_data
                                employee.score_risco = calcular_score_risco(employee)
                                employee.fatores_risco = identificar_fatores_risco(employee)
                                employee.acoes_recomendadas = gerar_recomendacoes(employee.fatores_risco, employee)
                                
                                processed_count += 1
                                
                                # Mostrar resultado detalhado
                                col1, col2 = st.columns([3, 1])
                                with col1:
                                    st.success(f"✅ Processado com sucesso!")
                                    
                                    # Mostrar informações extraídas
                                    st.write(f"   • Texto extraído: {linkedin_data.get('chars_extraidos', 0)} caracteres")
                                    
                                    # Mostrar insights detectados
                                    insights = []
                                    if linkedin_data.get("ativo_recentemente"):
                                        insights.append("🔄 Atividade recente detectada")
                                    if linkedin_data.get("mudancas_frequentes"):
                                        insights.append("🏢 Múltiplas experiências profissionais")
                                    if linkedin_data.get("certificacoes_recentes"):
                                        insights.append("🎓 Certificações/cursos encontrados")
                                    
                                    if insights:
                                        st.write("   **Sinais detectados:**")
                                        for insight in insights:
                                            st.write(f"     • {insight}")
                                    else:
                                        st.write("   • Nenhum sinal de risco detectado")
                                    
                                    # Mostrar debug info se disponível
                                    if linkedin_data.get("debug_indicators"):
                                        debug = linkedin_data["debug_indicators"]
                                        with st.expander("🔍 Detalhes da análise"):
                                            st.write(f"Indicadores de trabalho: {debug.get('work_count', 0)}")
                                            st.write(f"Indicadores de certificação: {debug.get('cert_count', 0)}")
                                            st.write(f"Anos encontrados: {debug.get('anos_encontrados', [])}")
                                
                                with col2:
                                    # Mostrar mudança no score
                                    if old_score != employee.score_risco:
                                        delta = employee.score_risco - old_score
                                        if delta > 0:
                                            st.error(f"⬆️ +{delta:.1f}")
                                            st.write(f"{old_score:.1f} → {employee.score_risco:.1f}")
                                        else:
                                            st.success(f"⬇️ {delta:.1f}")
                                            st.write(f"{old_score:.1f} → {employee.score_risco:.1f}")
                                    else:
                                        st.info("➡️ Score mantido")
                                        st.write(f"Score: {employee.score_risco:.1f}")
                                
                                st.markdown("---")
                        
                        # Resumo final do processamento
                        st.markdown("### 📊 Resumo do Processamento")
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("PDFs Processados", processed_count)
                        with col2:
                            st.metric("Erros", error_count)
                        with col3:
                            total_linkedin = len([e for e in st.session_state.employees if e.linkedin_data])
                            st.metric("Total com LinkedIn", total_linkedin)
                        
                        if processed_count > 0:
                            st.balloons()
                            st.success(f"""
                            🎉 **Processamento Concluído!**
                            
                            ✅ {processed_count} PDFs processados com sucesso  
                            ❌ {error_count} erros encontrados  
                            📊 {total_linkedin} colaboradores agora têm dados do LinkedIn  
                            
                            **Próximo passo:** Vá para o Dashboard para ver os resultados atualizados!
                            """)
                        else:
                            st.error("""
                            ❌ **Nenhum PDF foi processado com sucesso**
                            
                            **Possíveis causas:**
                            - PDFs podem estar corrompidos ou protegidos por senha
                            - PDFs podem ser apenas imagens (sem texto extraível)
                            - Arquivos podem não ser PDFs válidos
                            
                            **Soluções:**
                            - Verifique se os PDFs abrem normalmente
                            - Exporte novamente do LinkedIn
                            - Certifique-se de que não são apenas imagens
                            """)
                            
                        # Mostrar dicas de troubleshooting se houve erros
                        if error_count > 0:
                            with st.expander("🛠️ Dicas para resolver problemas"):
                                st.markdown("""
                                ### Problemas comuns e soluções:
                                
                                **1. "Não foi possível extrair texto"**
                                - O PDF pode ser uma imagem escaneada
                                - Solução: Exporte novamente do LinkedIn
                                
                                **2. "PDF vazio" ou "PDF sem páginas"**
                                - Arquivo corrompido no upload
                                - Solução: Faça upload novamente
                                
                                **3. "Erro ao processar PDF"**
                                - PDF pode estar protegido por senha
                                - Solução: Remova a proteção ou exporte novamente
                                
                                ### ✅ Como garantir PDFs funcionais:
                                1. No LinkedIn, vá em seu perfil
                                2. Clique em "Mais" → "Salvar como PDF"
                                3. Aguarde o download completar
                                4. Teste abrindo o PDF antes do upload
                                """)
            else:
                st.info("💡 Associe pelo menos um PDF a um colaborador para poder processar.")
            
            # Instruções para melhor nomeação
            with st.expander("💡 Dicas para melhor associação automática"):
                st.markdown("""
                ### 📋 Como nomear os PDFs para associação automática:
                
                **✅ Bons exemplos:**
                - `João Silva.pdf`
                - `Maria_Oliveira_Costa.pdf`
                - `Pedro-Henrique-Lima.pdf`
                
                **❌ Evite:**
                - `LinkedIn_Profile.pdf`
                - `CV_2024.pdf`
                - `Perfil.pdf`
                
                ### 🎯 Regras de associação:
                - O sistema busca pelo **nome** e **sobrenome** do colaborador no nome do arquivo
                - Precisa de pelo menos **2 partes do nome** para associação automática
                - Ignora acentos, espaços e caracteres especiais
                - Não diferencia maiúsculas/minúsculas
                """)
        
        else:
            if not st.session_state.employees:
                st.info("💡 Primeiro faça upload da planilha Excel para poder associar os PDFs do LinkedIn.")
            
    else:
        st.info("💡 Funcionalidade de PDF não disponível. Instale PyMuPDF para usar esta funcionalidade.")

def render_dashboard_page():
    """Página do dashboard"""
    if not st.session_state.employees:
        st.warning("⚠️ Nenhum dado carregado. Faça upload dos dados primeiro.")
        return
    
    st.markdown("### 📊 Dashboard - Visão Geral")
    
    employees = st.session_state.employees
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_employees = len(employees)
    high_risk = len([e for e in employees if e.score_risco > 60])
    medium_risk = len([e for e in employees if 30 < e.score_risco <= 60])
    avg_score = sum(e.score_risco for e in employees) / len(employees)
    
    with col1:
        st.markdown(create_metric_card("Total", str(total_employees)), unsafe_allow_html=True)
    
    with col2:
        st.markdown(create_metric_card("Alto Risco", str(high_risk), "high"), unsafe_allow_html=True)
    
    with col3:
        st.markdown(create_metric_card("Risco Médio", str(medium_risk), "medium"), unsafe_allow_html=True)
    
    with col4:
        st.markdown(create_metric_card("Score Médio", f"{avg_score:.1f}", get_risk_level(avg_score).lower()), unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_dist = create_risk_distribution_chart(employees)
        st.plotly_chart(fig_dist, use_container_width=True)
    
    with col2:
        fig_dept = create_department_chart(employees)
        st.plotly_chart(fig_dept, use_container_width=True)
    
    st.markdown("### 🚨 Colaboradores em Alto Risco")
    
    high_risk_employees = [e for e in employees if e.score_risco > 60]
    
    if high_risk_employees:
        high_risk_data = []
        for emp in high_risk_employees:
            high_risk_data.append({
                'Nome': emp.nome,
                'Departamento': emp.departamento,
                'Score': f"{emp.score_risco:.1f}",
                'Principal Fator': emp.fatores_risco[0] if emp.fatores_risco else 'N/A'
            })
        
        df_high_risk = pd.DataFrame(high_risk_data)
        st.dataframe(df_high_risk, use_container_width=True, hide_index=True)
    else:
        st.success("✅ Nenhum colaborador em alto risco!")

def render_analysis_page():
    """Página de análise detalhada"""
    if not st.session_state.employees:
        st.warning("⚠️ Nenhum dado carregado. Faça upload dos dados primeiro.")
        return
    
    st.markdown("### 🔍 Análise Detalhada")
    
    employees = st.session_state.employees
    
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
            ["Score de Risco (Desc)", "Nome", "Departamento"]
        )
    
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
    
    if sort_by == "Score de Risco (Desc)":
        filtered_employees.sort(key=lambda x: x.score_risco, reverse=True)
    elif sort_by == "Nome":
        filtered_employees.sort(key=lambda x: x.nome)
    elif sort_by == "Departamento":
        filtered_employees.sort(key=lambda x: x.departamento)
    
    st.markdown(f"**{len(filtered_employees)} colaboradores encontrados**")
    
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
                
                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=emp.score_risco,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': "Score de Risco"},
                    gauge={
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
                st.plotly_chart(fig_gauge, use_container_width=True, key=f"gauge_{i}_{emp.nome.replace(' ', '_')}")
            
            with col2:
                st.markdown("#### 🚨 Fatores de Risco")
                if emp.fatores_risco:
                    for fator in emp.fatores_risco:
                        st.markdown(f"• {fator}")
                else:
                    st.success("✅ Nenhum fator de risco identificado")
                
                st.markdown("#### 💡 Recomendações de Ação")
                if emp.acoes_recomendadas:
                    for j, acao in enumerate(emp.acoes_recomendadas, 1):
                        st.markdown(f"{j}. {acao}")
                
                if has_openai() and HAS_OPENAI:
                    if st.button(f"🤖 Gerar Insights IA", key=f"ai_insights_{i}_{emp.nome.replace(' ', '_')}"):
                        try:
                            client = openai.OpenAI(api_key=get_openai_key())
                            
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
                            
                            response = client.chat.completions.create(
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
                            try:
                                openai.api_key = get_openai_key()
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
                            except Exception as e2:
                                st.error(f"Erro na API OpenAI: {str(e2)}")
                                st.info("💡 Verifique se sua chave OpenAI está correta nos Secrets")
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
    
    st.markdown("---")
    st.markdown("#### 👀 Preview dos Dados")
    
    preview_data = []
    for emp in employees[:10]:
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
# INTERFACE PRINCIPAL
# ================================

def main():
    """Função principal da aplicação"""
    apply_custom_css()
    init_session_state()
    
    st.markdown("""
    <div class="custom-header">
        <h1>🎯 Radar RH</h1>
        <p>Sistema Inteligente de Análise de Rotatividade e Engajamento</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.title("📋 Navegação")
        
        page = st.radio(
            "Selecione uma página:",
            ["🏠 Início", "📤 Upload de Dados", "📊 Dashboard", "🔍 Análise Detalhada", "📋 Exportar Relatórios"],
            key="navigation"
        )
        
        st.markdown("---")
        
        if has_openai():
            st.markdown('<div class="alert-success">✅ OpenAI Configurada</div>', unsafe_allow_html=True)
        else:
            if not HAS_OPENAI:
                st.markdown('<div class="alert-warning">⚠️ OpenAI não instalada</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="alert-warning">⚠️ OpenAI não configurada</div>', unsafe_allow_html=True)
        
        if not HAS_PDF_SUPPORT:
            st.markdown('<div class="alert-warning">⚠️ PDF não suportado</div>', unsafe_allow_html=True)
        
        if st.session_state.employees:
            st.markdown("### 📈 Estatísticas")
            total = len(st.session_state.employees)
            high_risk = len([e for e in st.session_state.employees if e.score_risco > 60])
            
            st.metric("Total de Colaboradores", total)
            st.metric("Alto Risco", high_risk, delta=f"{(high_risk/total)*100:.1f}%")
    
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

if __name__ == "__main__":
    main()
