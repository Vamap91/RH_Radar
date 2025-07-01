"""
🎯 Radar RH - Sistema Simplificado (Apenas Excel)
Análise de risco baseada exclusivamente em dados de planilha
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io
import json
from typing import List
from dataclasses import dataclass

# ================================
# CONFIGURAÇÕES E CONSTANTES
# ================================

st.set_page_config(
    page_title="Radar RH - Análise Simplificada",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configurações de scoring SIMPLIFICADAS (apenas Excel)
SCORING_CONFIG = {
    "peso_tempo_casa": 0.25,     # 25%
    "peso_pdi": 0.30,           # 30% 
    "peso_treinamentos": 0.25,   # 25%
    "peso_ausencias": 0.20,      # 20%
    "tempo_casa_critico": 0.5,
    "treinamentos_minimo": 2,
    "ausencias_critico": 5,
    "risco_baixo": 20,
    "risco_medio": 45,
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
    score_risco: float = 0
    fatores_risco: List[str] = None
    acoes_recomendadas: List[str] = None

# ================================
# FUNÇÕES DE ANÁLISE SIMPLIFICADAS
# ================================

def calcular_score_risco(employee: Employee) -> float:
    """
    🎯 Cálculo de score baseado APENAS em dados Excel
    """
    score = 0
    
    # ================================
    # 1. FATOR TEMPO DE CASA (Peso: 25%)
    # ================================
    if employee.tempo_casa < 0.5:  # < 6 meses
        score += 15 * SCORING_CONFIG["peso_tempo_casa"]
    elif employee.tempo_casa < 1:  # 6-12 meses
        score += 35 * SCORING_CONFIG["peso_tempo_casa"]
    elif employee.tempo_casa < 2:  # 1-2 anos
        score += 20 * SCORING_CONFIG["peso_tempo_casa"]
    # Veteranos: sem penalização por tempo
    
    # ================================
    # 2. FATOR PDI (Peso: 30%)
    # ================================
    if not employee.participou_pdi:
        if employee.tempo_casa < 0.5:
            score += 15 * SCORING_CONFIG["peso_pdi"]
        elif employee.tempo_casa < 1:
            score += 50 * SCORING_CONFIG["peso_pdi"]
        elif employee.tempo_casa < 3:
            score += 75 * SCORING_CONFIG["peso_pdi"]
        else:  # Veteranos 3+ anos
            score += 100 * SCORING_CONFIG["peso_pdi"]  # 30 pontos!
    
    # ================================
    # 3. FATOR TREINAMENTOS (Peso: 25%)
    # ================================
    if employee.tempo_casa >= 1:  # Veteranos
        if employee.num_treinamentos == 0:
            score += 100 * SCORING_CONFIG["peso_treinamentos"]  # 25 pontos!
        elif employee.num_treinamentos == 1:
            score += 75 * SCORING_CONFIG["peso_treinamentos"]
        elif employee.num_treinamentos < 3:
            score += 50 * SCORING_CONFIG["peso_treinamentos"]
        elif employee.num_treinamentos < 5:
            score += 25 * SCORING_CONFIG["peso_treinamentos"]
    else:  # Novatos
        if employee.num_treinamentos == 0:
            score += 40 * SCORING_CONFIG["peso_treinamentos"]
        elif employee.num_treinamentos < 2:
            score += 20 * SCORING_CONFIG["peso_treinamentos"]
    
    # ================================
    # 4. FATOR AUSÊNCIAS (Peso: 20%)
    # ================================
    if employee.num_ausencias <= 2:
        score += 5 * SCORING_CONFIG["peso_ausencias"]
    elif employee.num_ausencias <= 5:
        score += 30 * SCORING_CONFIG["peso_ausencias"]
    elif employee.num_ausencias <= 10:
        score += 60 * SCORING_CONFIG["peso_ausencias"]
    elif employee.num_ausencias <= 20:
        score += 85 * SCORING_CONFIG["peso_ausencias"]
    else:  # 20+ ausências
        score += 100 * SCORING_CONFIG["peso_ausencias"]
        
        # Bônus para casos extremos
        if employee.num_ausencias >= 50:
            score += 15  # +15 pontos extras
    
    # ================================
    # 5. BÔNUS COMBINAÇÃO CRÍTICA
    # ================================
    if (employee.tempo_casa >= 2 and 
        not employee.participou_pdi and 
        employee.num_treinamentos <= 1 and 
        employee.num_ausencias >= 20):
        score += 20  # Bônus crítico
    
    return min(score, 100)

def identificar_fatores_risco(employee: Employee) -> List[str]:
    """Identifica fatores de risco baseado apenas nos dados Excel"""
    fatores = []
    
    # Tempo de casa
    if employee.tempo_casa < 0.5:
        fatores.append("⚠️ Muito novo na empresa (< 6 meses)")
    elif employee.tempo_casa < 1:
        fatores.append("⚠️ Pouco tempo de casa (< 1 ano)")
    elif employee.tempo_casa < 2:
        fatores.append("📝 Tempo de casa baixo (< 2 anos)")
    
    # PDI
    if not employee.participou_pdi:
        if employee.tempo_casa >= 3:
            fatores.append("🚨 CRÍTICO: Veterano sem PDI")
        elif employee.tempo_casa >= 1:
            fatores.append("⚠️ Sem PDI nos últimos 12 meses")
        else:
            fatores.append("📝 PDI pendente (novato)")
    
    # Treinamentos
    if employee.tempo_casa >= 1:
        if employee.num_treinamentos == 0:
            fatores.append("🚨 CRÍTICO: Zero treinamentos")
        elif employee.num_treinamentos == 1:
            fatores.append("⚠️ Apenas 1 treinamento")
        elif employee.num_treinamentos < 3:
            fatores.append(f"📚 Poucos treinamentos ({employee.num_treinamentos})")
    else:
        if employee.num_treinamentos == 0:
            fatores.append("📚 Sem treinamentos (novato)")
    
    # Ausências
    if employee.num_ausencias >= 50:
        fatores.append(f"🚨 CRÍTICO: Ausências extremas ({employee.num_ausencias})")
    elif employee.num_ausencias >= 20:
        fatores.append(f"🚨 Ausências muito frequentes ({employee.num_ausencias})")
    elif employee.num_ausencias > 10:
        fatores.append(f"⚠️ Ausências frequentes ({employee.num_ausencias})")
    elif employee.num_ausencias > 5:
        fatores.append(f"⚠️ Ausências preocupantes ({employee.num_ausencias})")
    
    # Combinação crítica
    if (employee.tempo_casa >= 2 and 
        not employee.participou_pdi and 
        employee.num_treinamentos <= 1 and 
        employee.num_ausencias >= 20):
        fatores.append("🚨 ALERTA MÁXIMO: Múltiplos fatores críticos")
    
    return fatores

def gerar_recomendacoes(fatores_risco: List[str], employee: Employee) -> List[str]:
    """Gera recomendações baseadas apenas nos dados Excel"""
    recomendacoes = []
    
    # Casos críticos
    if "CRÍTICO" in str(fatores_risco):
        recomendacoes.append("🚨 URGENTE: Reunião imediata com RH")
        recomendacoes.append("📋 Plano de ação em 48h")
    
    # Tempo de casa
    if any("novo" in f or "Pouco tempo" in f for f in fatores_risco):
        recomendacoes.append("👥 Programa de mentoria")
        recomendacoes.append("📅 Check-ins semanais")
    
    # PDI
    if "Veterano sem PDI" in str(fatores_risco):
        recomendacoes.append("📋 PDI emergencial (7 dias)")
    elif "Sem PDI" in str(fatores_risco):
        recomendacoes.append("📋 Agendar PDI (15 dias)")
    
    # Treinamentos
    if "Zero treinamentos" in str(fatores_risco):
        recomendacoes.append("🎓 Trilha de desenvolvimento urgente")
    elif "Poucos treinamentos" in str(fatores_risco):
        recomendacoes.append("📖 Ampliar capacitação")
    
    # Ausências
    if "extremas" in str(fatores_risco):
        recomendacoes.append("🏥 Avaliação médica/psicológica")
    elif "muito frequentes" in str(fatores_risco):
        recomendacoes.append("💬 Investigar causas das ausências")
    
    # Combinação crítica
    if "ALERTA MÁXIMO" in str(fatores_risco):
        recomendacoes.append("🚨 COMITÊ DE RETENÇÃO")
        recomendacoes.append("💰 Avaliar proposta de retenção")
    
    if not recomendacoes:
        recomendacoes.append("✅ Acompanhamento regular")
        recomendacoes.append("🏆 Reconhecimento")
    
    return recomendacoes

def get_risk_level(score: float) -> str:
    """Níveis de risco"""
    if score <= SCORING_CONFIG["risco_baixo"]:
        return "Baixo"
    elif score <= SCORING_CONFIG["risco_medio"]:
        return "Médio"
    else:
        return "Alto"

def get_risk_color(score: float) -> str:
    """Cores por nível de risco"""
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
    """Processa planilha Excel"""
    employees = []
    
    # Padronizar colunas
    df.columns = df.columns.str.lower().str.strip().str.replace(' ', '_')
    
    required_columns = ['nome', 'departamento', 'cargo', 'tempo_casa', 'participou_pdi', 'num_treinamentos', 'num_ausencias']
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        st.error(f"❌ Colunas ausentes: {', '.join(missing_columns)}")
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
            st.warning(f"⚠️ Erro ao processar {row.get('nome', 'N/A')}: {str(e)}")
    
    return employees

# ================================
# FUNÇÕES DE VISUALIZAÇÃO
# ================================

def apply_custom_css():
    """CSS customizado"""
    st.markdown(f"""
    <style>
        .main .block-container {{
            padding-top: 2rem;
            font-family: 'Arial', sans-serif;
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
        
        .alert-warning {{
            background: rgba(214, 39, 40, 0.1);
            border-left: 4px solid {COLORS['warning']};
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
    </style>
    """, unsafe_allow_html=True)

def create_metric_card(title: str, value: str, risk_level: str = "low"):
    """Card de métrica"""
    risk_class = f"risk-{risk_level}"
    return f"""
    <div class="metric-card {risk_class}">
        <h3 style="margin: 0; color: {COLORS['primary']}; font-size: 2rem;">{value}</h3>
        <p style="margin: 0.5rem 0 0 0; color: {COLORS['text']}; opacity: 0.7;">{title}</p>
    </div>
    """

def create_risk_chart(employees: List[Employee]):
    """Gráfico de distribuição de risco"""
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
        title="Distribuição de Risco - Análise Excel",
        title_x=0.5,
        height=400
    )
    
    return fig

def create_score_histogram(employees: List[Employee]):
    """Histograma de scores"""
    scores = [emp.score_risco for emp in employees]
    
    fig = go.Figure(data=[go.Histogram(
        x=scores,
        nbinsx=20,
        marker_color=COLORS["primary"],
        opacity=0.7
    )])
    
    # Adicionar linhas de threshold
    fig.add_vline(x=20, line_dash="dash", line_color=COLORS["success"], 
                  annotation_text="Baixo/Médio")
    fig.add_vline(x=45, line_dash="dash", line_color=COLORS["warning"], 
                  annotation_text="Médio/Alto")
    
    fig.update_layout(
        title="Distribuição dos Scores de Risco",
        xaxis_title="Score de Risco",
        yaxis_title="Número de Colaboradores",
        height=400
    )
    
    return fig

def export_to_excel(employees: List[Employee]) -> bytes:
    """Exporta para Excel"""
    data = []
    for emp in employees:
        data.append({
            'Nome': emp.nome,
            'Departamento': emp.departamento,
            'Cargo': emp.cargo,
            'Tempo_Casa_Anos': emp.tempo_casa,
            'Participou_PDI': 'Sim' if emp.participou_pdi else 'Não',
            'Num_Treinamentos': emp.num_treinamentos,
            'Num_Ausencias': emp.num_ausencias,
            'Score_Risco': round(emp.score_risco, 1),
            'Nivel_Risco': get_risk_level(emp.score_risco),
            'Fatores_Risco': '; '.join(emp.fatores_risco) if emp.fatores_risco else '',
            'Acoes_Recomendadas': '; '.join(emp.acoes_recomendadas) if emp.acoes_recomendadas else ''
        })
    
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Analise_Risco', index=False)
        
        # Planilha de resumo
        resumo = {
            'Métrica': ['Total Colaboradores', 'Alto Risco', 'Médio Risco', 'Baixo Risco', 'Score Médio'],
            'Valor': [
                len(employees),
                len([e for e in employees if e.score_risco > 45]),
                len([e for e in employees if 20 < e.score_risco <= 45]),
                len([e for e in employees if e.score_risco <= 20]),
                round(sum(e.score_risco for e in employees) / len(employees), 1)
            ]
        }
        pd.DataFrame(resumo).to_excel(writer, sheet_name='Resumo', index=False)
    
    return output.getvalue()

# ================================
# INTERFACE PRINCIPAL
# ================================

def init_session_state():
    if 'employees' not in st.session_state:
        st.session_state.employees = []

def main():
    apply_custom_css()
    init_session_state()
    
    # Header
    st.markdown("""
    <div class="custom-header">
        <h1>🎯 Radar RH - Versão Excel</h1>
        <p>Análise de Risco baseada exclusivamente em dados Excel</p>
        <p><small>📊 4 Indicadores: Tempo Casa | PDI | Treinamentos | Ausências</small></p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.title("📋 Menu")
        
        page = st.radio(
            "Navegação:",
            ["🏠 Início", "📤 Upload Excel", "📊 Dashboard", "📋 Exportar"]
        )
        
        # Status
        if st.session_state.employees:
            st.markdown("### 📈 Estatísticas")
            total = len(st.session_state.employees)
            high_risk = len([e for e in st.session_state.employees if e.score_risco > 45])
            st.metric("Total", total)
            st.metric("Alto Risco", high_risk)
            st.metric("% Alto Risco", f"{(high_risk/total)*100:.1f}%")
    
    # Páginas
    if page == "🏠 Início":
        render_home()
    elif page == "📤 Upload Excel":
        render_upload()
    elif page == "📊 Dashboard":
        render_dashboard()
    elif page == "📋 Exportar":
        render_export()

def render_home():
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### 🎯 Análise Baseada Apenas em Excel
        
        **Sistema focado em 4 indicadores essenciais do RH:**
        
        #### 📊 Indicadores Analisados:
        - **⏰ Tempo de Casa** (25%): Estabilidade na empresa
        - **📋 PDI** (30%): Participação em desenvolvimento
        - **🎓 Treinamentos** (25%): Investimento em capacitação  
        - **📅 Ausências** (20%): Frequência e pontualidade
        
        #### 🚀 Como Usar:
        1. **Prepare** planilha Excel com 7 colunas obrigatórias
        2. **Faça upload** na aba "Upload Excel"
        3. **Visualize** resultados no Dashboard
        4. **Exporte** relatório final
        
        #### 📈 Níveis de Risco:
        - **Baixo**: 0-20 pontos (✅ Seguro)
        - **Médio**: 21-45 pontos (⚠️ Atenção)
        - **Alto**: 46+ pontos (🚨 Ação urgente)
        
        #### ✅ Vantagens da Versão Excel:
        - **Simples**: Sem configurações complexas
        - **Prático**: Dados que RH já possui
        - **Direto**: Resultados imediatos
        - **Preciso**: Algoritmo rigoroso
        """)
    
    with col2:
        # Modelo de planilha
        if st.button("📥 Baixar Modelo Excel", use_container_width=True):
            modelo_data = {
                'nome': [
                    'João Silva', 'Maria Santos', 'Pedro Lima', 'Ana Costa',
                    'Carlos Oliveira', 'Fernanda Souza', 'Rafael Mendes'
                ],
                'departamento': [
                    'Vendas', 'Marketing', 'TI', 'RH', 'Financeiro', 'Operações', 'TI'
                ],
                'cargo': [
                    'Vendedor', 'Analista', 'Desenvolvedor', 'Analista RH', 
                    'Assistente', 'Coordenador', 'Estagiário'
                ],
                'tempo_casa': [0.3, 2.5, 1.2, 4.1, 0.8, 3.2, 0.1],
                'participou_pdi': ['Não', 'Sim', 'Sim', 'Sim', 'Não', 'Sim', 'Não'],
                'num_treinamentos': [0, 4, 2, 6, 1, 5, 0],
                'num_ausencias': [8, 2, 1, 0, 12, 1, 25]
            }
            
            df_modelo = pd.DataFrame(modelo_data)
            output = io.BytesIO()
            df_modelo.to_excel(output, index=False, engine='openpyxl')
            
            st.download_button(
                "💾 Download Modelo",
                data=output.getvalue(),
                file_name="modelo_radar_rh.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

def render_upload():
    st.markdown("### 📤 Upload da Planilha Excel")
    
    # Mostrar colunas obrigatórias
    st.markdown("""
    #### 📋 Colunas Obrigatórias:
    1. **nome** - Nome completo do colaborador
    2. **departamento** - Área/setor de trabalho
    3. **cargo** - Função atual
    4. **tempo_casa** - Anos na empresa (ex: 1.5)
    5. **participou_pdi** - Sim/Não nos últimos 12 meses
    6. **num_treinamentos** - Quantidade no último ano
    7. **num_ausencias** - Faltas nos últimos 6 meses
    """)
    
    uploaded_file = st.file_uploader(
        "📊 Selecione seu arquivo Excel",
        type=['xlsx', 'xls']
    )
    
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            st.success(f"✅ Arquivo carregado: {len(df)} registros")
            
            st.markdown("#### 👀 Preview")
            st.dataframe(df.head(), use_container_width=True)
            
            if st.button("🚀 Processar Análise", use_container_width=True):
                with st.spinner("Analisando dados..."):
                    employees = processar_planilha(df)
                    
                    if employees:
                        st.session_state.employees = employees
                        st.success(f"✅ {len(employees)} colaboradores analisados!")
                        
                        # Stats rápidas
                        high_risk = len([e for e in employees if e.score_risco > 45])
                        st.warning(f"🚨 {high_risk} colaboradores em ALTO RISCO")
                        st.balloons()
                    else:
                        st.error("❌ Erro no processamento")
        
        except Exception as e:
            st.error(f"❌ Erro: {str(e)}")

def render_dashboard():
    if not st.session_state.employees:
        st.warning("⚠️ Carregue dados primeiro")
        return
    
    st.markdown("### 📊 Dashboard de Risco")
    
    employees = st.session_state.employees
    
    # Métricas
    col1, col2, col3, col4 = st.columns(4)
    
    total = len(employees)
    high_risk = len([e for e in employees if e.score_risco > 45])
    medium_risk = len([e for e in employees if 20 < e.score_risco <= 45])
    low_risk = len([e for e in employees if e.score_risco <= 20])
    
    with col1:
        st.markdown(create_metric_card("Total", str(total)), unsafe_allow_html=True)
    with col2:
        st.markdown(create_metric_card("Alto Risco", f"{high_risk} ({(high_risk/total)*100:.1f}%)", "high"), unsafe_allow_html=True)
    with col3:
        st.markdown(create_metric_card("Médio Risco", f"{medium_risk} ({(medium_risk/total)*100:.1f}%)", "medium"), unsafe_allow_html=True)
    with col4:
        st.markdown(create_metric_card("Baixo Risco", f"{low_risk} ({(low_risk/total)*100:.1f}%)", "low"), unsafe_allow_html=True)
    
    # Gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        fig1 = create_risk_chart(employees)
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        fig2 = create_score_histogram(employees)
        st.plotly_chart(fig2, use_container_width=True)
    
    # Lista de alto risco
    st.markdown("### 🚨 Colaboradores em Alto Risco")
    high_risk_employees = [e for e in employees if e.score_risco > 45]
    
    if high_risk_employees:
        data = []
        for emp in high_risk_employees:
            data.append({
                'Nome': emp.nome,
                'Depto': emp.departamento,
                'Score': f"{emp.score_risco:.1f}",
                'Principal Problema': emp.fatores_risco[0] if emp.fatores_risco else 'N/A',
                'Ação Urgente': emp.acoes_recomendadas[0] if emp.acoes_recomendadas else 'N/A'
            })
        
        df_risk = pd.DataFrame(data)
        st.dataframe(df_risk, use_container_width=True, hide_index=True)
    else:
        st.success("✅ Nenhum colaborador em alto risco!")

def render_export():
    if not st.session_state.employees:
        st.warning("⚠️ Carregue dados primeiro")
        return
    
    st.markdown("### 📋 Exportar Relatórios")
    
    employees = st.session_state.employees
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 Relatório Excel Completo")
        st.markdown("Inclui análise detalhada + resumo executivo")
        
        if st.button("📥 Gerar Excel", use_container_width=True):
            excel_data = export_to_excel(employees)
            
            st.download_button(
                label="💾 Download Excel",
                data=excel_data,
                file_name=f"relatorio_radar_rh_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    with col2:
        st.markdown("#### 📄 Resumo Executivo")
        
        total = len(employees)
        high_risk = len([e for e in employees if e.score_risco > 45])
        medium_risk = len([e for e in employees if 20 < e.score_risco <= 45])
        low_risk = len([e for e in employees if e.score_risco <= 20])
        avg_score = sum(e.score_risco for e in employees) / len(employees)
        
        st.markdown(f"""
        **📊 Análise de {datetime.now().strftime('%d/%m/%Y')}**
        
        **Total:** {total} colaboradores
        - 🚨 Alto risco: {high_risk} ({(high_risk/total)*100:.1f}%)
        - ⚠️ Médio risco: {medium_risk} ({(medium_risk/total)*100:.1f}%)
        - ✅ Baixo risco: {low_risk} ({(low_risk/total)*100:.1f}%)
        
        **Score médio:** {avg_score:.1f} pontos
        
        **🎯 Recomendações:**
        - Focar nos {high_risk} casos de alto risco
        - Implementar PDI para veteranos sem desenvolvimento
        - Ampliar programa de treinamentos
        - Investigar causas de ausências excessivas
        """)

# Teste do algoritmo simplificado
def teste_algoritmo():
    st.markdown("### 🧪 Teste do Algoritmo Simplificado")
    
    with st.expander("Testar Caso Crítico"):
        st.markdown("""
        **Perfil de Teste:**
        - 7 anos na empresa (veterano)
        - SEM PDI  
        - 0 treinamentos
        - 50 ausências
        
        **Score esperado:** ~90 pontos (ALTO RISCO)
        """)
        
        if st.button("🧪 Executar Teste"):
            funcionario_teste = Employee(
                nome="Funcionário Crítico",
                departamento="TI",
                cargo="Desenvolvedor",
                tempo_casa=7.0,
                participou_pdi=False,
                num_treinamentos=0,
                num_ausencias=50
            )
            
            score = calcular_score_risco(funcionario_teste)
            nivel = get_risk_level(score)
            fatores = identificar_fatores_risco(funcionario_teste)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Score", f"{score:.1f}/100")
            with col2:
                st.metric("Nível", nivel)
            with col3:
                st.metric("Fatores", len(fatores))
            
            st.markdown("**🔍 Breakdown do Cálculo:**")
            st.markdown(f"""
            - **Tempo de casa (7 anos):** 0 pontos
            - **PDI ausente (veterano):** 30 pontos (100 × 0.30)
            - **Zero treinamentos:** 25 pontos (100 × 0.25)  
            - **50+ ausências:** 35 pontos (100 × 0.20 + 15 bônus)
            - **Bônus combinação crítica:** 20 pontos
            - **TOTAL:** {score:.1f} pontos = **{nivel.upper()} RISCO**
            """)
            
            st.markdown("**🚨 Fatores Detectados:**")
            for fator in fatores:
                st.markdown(f"• {fator}")

if __name__ == "__main__":
    main()
    
    # Mostrar teste na página inicial
    if st.session_state.get('current_page') != 'test':
        with st.expander("🧪 Testar Algoritmo"):
            teste_algoritmo()
