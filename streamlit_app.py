"""
🎯 Radar RH - Sistema Simplificado (Apenas Excel)
Análise de risco baseada exclusivamente em dados de planilha
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import io
from typing import List
from dataclasses import dataclass

# ================================
# CONFIGURAÇÕES
# ================================

st.set_page_config(
    page_title="Radar RH - Análise Excel",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configurações de scoring
SCORING_CONFIG = {
    "peso_tempo_casa": 0.25,
    "peso_pdi": 0.30,
    "peso_treinamentos": 0.25,
    "peso_ausencias": 0.20,
    "risco_baixo": 20,
    "risco_medio": 45,
    "risco_alto": 100
}

# Cores
COLORS = {
    "primary": "#1f77b4",
    "secondary": "#ff7f0e", 
    "success": "#2ca02c",
    "warning": "#d62728",
    "text": "#2c3e50"
}

# ================================
# CLASSE DE DADOS
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
# FUNÇÕES DE ANÁLISE
# ================================

def calcular_score_risco(employee: Employee) -> float:
    """Cálculo de score ULTRA RIGOROSO baseado apenas em dados Excel"""
    score = 0
    
    # 1. Tempo de Casa (25%) - MAIS RIGOROSO
    if employee.tempo_casa < 0.5:  # < 6 meses
        score += 30 * SCORING_CONFIG["peso_tempo_casa"]  # Era 15, agora 30
    elif employee.tempo_casa < 1:  # 6-12 meses
        score += 50 * SCORING_CONFIG["peso_tempo_casa"]  # Era 35, agora 50
    elif employee.tempo_casa < 2:  # 1-2 anos
        score += 20 * SCORING_CONFIG["peso_tempo_casa"]
    
    # 2. PDI (30%) - ULTRA RIGOROSO
    if not employee.participou_pdi:
        if employee.tempo_casa < 0.5:  # Novatos
            score += 60 * SCORING_CONFIG["peso_pdi"]  # Era 15, agora 60
        elif employee.tempo_casa < 1:
            score += 80 * SCORING_CONFIG["peso_pdi"]  # Era 50, agora 80
        elif employee.tempo_casa < 3:
            score += 90 * SCORING_CONFIG["peso_pdi"]  # Era 75, agora 90
        else:  # Veteranos
            score += 100 * SCORING_CONFIG["peso_pdi"]
    
    # 3. Treinamentos (25%) - ULTRA RIGOROSO
    if employee.tempo_casa >= 0.5:  # Mudou de 1 ano para 6 meses
        if employee.num_treinamentos == 0:
            score += 100 * SCORING_CONFIG["peso_treinamentos"]  # Máximo sempre
        elif employee.num_treinamentos == 1:
            score += 80 * SCORING_CONFIG["peso_treinamentos"]  # Era 75, agora 80
        elif employee.num_treinamentos < 3:
            score += 60 * SCORING_CONFIG["peso_treinamentos"]  # Era 50, agora 60
        elif employee.num_treinamentos < 5:
            score += 30 * SCORING_CONFIG["peso_treinamentos"]  # Era 25, agora 30
    else:  # Muito novatos (< 6 meses)
        if employee.num_treinamentos == 0:
            score += 70 * SCORING_CONFIG["peso_treinamentos"]  # Era 40, agora 70
        elif employee.num_treinamentos < 2:
            score += 40 * SCORING_CONFIG["peso_treinamentos"]  # Era 20, agora 40
    
    # 4. Ausências (20%) - EXPONENCIAL
    if employee.num_ausencias <= 2:
        score += 10 * SCORING_CONFIG["peso_ausencias"]  # Era 5, agora 10
    elif employee.num_ausencias <= 5:
        score += 40 * SCORING_CONFIG["peso_ausencias"]  # Era 30, agora 40
    elif employee.num_ausencias <= 10:
        score += 70 * SCORING_CONFIG["peso_ausencias"]  # Era 60, agora 70
    elif employee.num_ausencias <= 20:
        score += 90 * SCORING_CONFIG["peso_ausencias"]  # Era 85, agora 90
    else:  # 20+ ausências
        score += 100 * SCORING_CONFIG["peso_ausencias"]
        
        # Bônus MASSIVO para casos extremos
        if employee.num_ausencias >= 50:
            score += 25  # Era 15, agora 25 pontos extras!
        elif employee.num_ausencias >= 30:
            score += 15  # Novo: bônus para 30+
    
    # 5. Bônus combinação crítica - MAIS AGRESSIVO
    if (employee.tempo_casa >= 1 and 
        not employee.participou_pdi and 
        employee.num_treinamentos <= 1 and 
        employee.num_ausencias >= 20):
        score += 25  # Era 20, agora 25
    
    # 6. NOVO: Bônus para novatos problemáticos
    if (employee.tempo_casa < 1 and 
        not employee.participou_pdi and 
        employee.num_treinamentos == 0 and 
        employee.num_ausencias >= 30):
        score += 20  # Bônus especial para novatos críticos
    
    return min(score, 100)

def identificar_fatores_risco(employee: Employee) -> List[str]:
    """Identifica fatores de risco"""
    fatores = []
    
    if employee.tempo_casa < 0.5:
        fatores.append("⚠️ Muito novo na empresa")
    elif employee.tempo_casa < 1:
        fatores.append("⚠️ Pouco tempo de casa")
    elif employee.tempo_casa < 2:
        fatores.append("📝 Tempo de casa baixo")
    
    if not employee.participou_pdi:
        if employee.tempo_casa >= 3:
            fatores.append("🚨 CRÍTICO: Veterano sem PDI")
        elif employee.tempo_casa >= 1:
            fatores.append("⚠️ Sem PDI nos últimos 12 meses")
        else:
            fatores.append("📝 PDI pendente")
    
    if employee.tempo_casa >= 1:
        if employee.num_treinamentos == 0:
            fatores.append("🚨 CRÍTICO: Zero treinamentos")
        elif employee.num_treinamentos < 3:
            fatores.append(f"📚 Poucos treinamentos ({employee.num_treinamentos})")
    else:
        if employee.num_treinamentos == 0:
            fatores.append("📚 Sem treinamentos")
    
    if employee.num_ausencias >= 50:
        fatores.append(f"🚨 CRÍTICO: Ausências extremas ({employee.num_ausencias})")
    elif employee.num_ausencias >= 20:
        fatores.append(f"🚨 Ausências muito frequentes ({employee.num_ausencias})")
    elif employee.num_ausencias > 10:
        fatores.append(f"⚠️ Ausências frequentes ({employee.num_ausencias})")
    elif employee.num_ausencias > 5:
        fatores.append(f"⚠️ Ausências preocupantes ({employee.num_ausencias})")
    
    if (employee.tempo_casa >= 2 and 
        not employee.participou_pdi and 
        employee.num_treinamentos <= 1 and 
        employee.num_ausencias >= 20):
        fatores.append("🚨 ALERTA MÁXIMO: Múltiplos fatores críticos")
    
    return fatores

def gerar_recomendacoes(fatores_risco: List[str], employee: Employee) -> List[str]:
    """Gera recomendações"""
    recomendacoes = []
    
    if "CRÍTICO" in str(fatores_risco):
        recomendacoes.append("🚨 URGENTE: Reunião imediata com RH")
        recomendacoes.append("📋 Plano de ação em 48h")
    
    if any("novo" in f or "Pouco tempo" in f for f in fatores_risco):
        recomendacoes.append("👥 Programa de mentoria")
    
    if "Veterano sem PDI" in str(fatores_risco):
        recomendacoes.append("📋 PDI emergencial (7 dias)")
    elif "Sem PDI" in str(fatores_risco):
        recomendacoes.append("📋 Agendar PDI (15 dias)")
    
    if "Zero treinamentos" in str(fatores_risco):
        recomendacoes.append("🎓 Trilha de desenvolvimento urgente")
    elif "Poucos treinamentos" in str(fatores_risco):
        recomendacoes.append("📖 Ampliar capacitação")
    
    if "extremas" in str(fatores_risco):
        recomendacoes.append("🏥 Avaliação médica")
    elif "muito frequentes" in str(fatores_risco):
        recomendacoes.append("💬 Investigar causas das ausências")
    
    if "ALERTA MÁXIMO" in str(fatores_risco):
        recomendacoes.append("🚨 COMITÊ DE RETENÇÃO")
    
    if not recomendacoes:
        recomendacoes.append("✅ Acompanhamento regular")
    
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
    """Cores por nível"""
    if score <= SCORING_CONFIG["risco_baixo"]:
        return COLORS["success"]
    elif score <= SCORING_CONFIG["risco_medio"]:
        return COLORS["secondary"]
    else:
        return COLORS["warning"]

# ================================
# PROCESSAMENTO DE DADOS
# ================================

def processar_planilha(df: pd.DataFrame) -> List[Employee]:
    """Processa planilha Excel"""
    employees = []
    
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
# VISUALIZAÇÕES
# ================================

def apply_custom_css():
    """CSS customizado"""
    st.markdown(f"""
    <style>
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
    """Gráfico de distribuição"""
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
    
    return output.getvalue()

# ================================
# INTERFACE
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
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.title("📋 Menu")
        
        page = st.radio(
            "Navegação:",
            ["🏠 Início", "📤 Upload Excel", "📊 Dashboard", "📋 Exportar"]
        )
        
        if st.session_state.employees:
            st.markdown("### 📈 Stats")
            total = len(st.session_state.employees)
            high_risk = len([e for e in st.session_state.employees if e.score_risco > 45])
            st.metric("Total", total)
            st.metric("Alto Risco", high_risk)
    
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
        
        **4 indicadores essenciais do RH:**
        
        - **⏰ Tempo de Casa** (25%): Estabilidade
        - **📋 PDI** (30%): Desenvolvimento
        - **🎓 Treinamentos** (25%): Capacitação  
        - **📅 Ausências** (20%): Frequência
        
        #### 📈 Níveis de Risco:
        - **Baixo**: 0-20 pontos (✅ Seguro)
        - **Médio**: 21-45 pontos (⚠️ Atenção)
        - **Alto**: 46+ pontos (🚨 Urgente)
        """)
    
    with col2:
        if st.button("📥 Baixar Modelo Excel", use_container_width=True):
            modelo_data = {
                'nome': ['João Silva', 'Maria Santos', 'Pedro Lima'],
                'departamento': ['Vendas', 'Marketing', 'TI'],
                'cargo': ['Vendedor', 'Analista', 'Desenvolvedor'],
                'tempo_casa': [0.3, 2.5, 7.0],
                'participou_pdi': ['Não', 'Sim', 'Não'],
                'num_treinamentos': [0, 4, 0],
                'num_ausencias': [8, 2, 50]
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
    
    st.markdown("""
    #### 📋 Colunas Obrigatórias:
    1. **nome** - Nome completo
    2. **departamento** - Área/setor
    3. **cargo** - Função atual
    4. **tempo_casa** - Anos na empresa (ex: 1.5)
    5. **participou_pdi** - Sim/Não
    6. **num_treinamentos** - Quantidade no ano
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
            
            st.dataframe(df.head(), use_container_width=True)
            
            if st.button("🚀 Processar Análise", use_container_width=True):
                with st.spinner("Analisando dados..."):
                    employees = processar_planilha(df)
                    
                    if employees:
                        st.session_state.employees = employees
                        st.success(f"✅ {len(employees)} colaboradores analisados!")
                        
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
    
    # Gráfico
    fig = create_risk_chart(employees)
    st.plotly_chart(fig, use_container_width=True)
    
    # Lista COMPLETA de colaboradores com análise individual
    st.markdown("### 👥 Análise Individual dos Colaboradores")
    
    for i, emp in enumerate(employees):
        risk_level = get_risk_level(emp.score_risco)
        risk_color = get_risk_color(emp.score_risco)
        
        # Expandir para cada colaborador
        with st.expander(f"{emp.nome} - {emp.departamento} | Score: {emp.score_risco:.1f} ({risk_level})", expanded=False):
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("#### 📊 Dados Básicos")
                st.write(f"**Cargo:** {emp.cargo}")
                st.write(f"**Tempo de Casa:** {emp.tempo_casa} anos")
                st.write(f"**PDI:** {'✅ Sim' if emp.participou_pdi else '❌ Não'}")
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
                        'bar': {'color': risk_color},
                        'steps': [
                            {'range': [0, 20], 'color': "lightgreen"},
                            {'range': [20, 45], 'color': "lightyellow"},
                            {'range': [45, 100], 'color': "lightcoral"}
                        ]
                    }
                ))
                fig_gauge.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig_gauge, use_container_width=True)
            
            with col2:
                st.markdown("#### 🚨 Fatores de Risco Identificados")
                if emp.fatores_risco:
                    for j, fator in enumerate(emp.fatores_risco, 1):
                        st.markdown(f"**{j}.** {fator}")
                else:
                    st.success("✅ Nenhum fator de risco crítico identificado")
                
                st.markdown("#### 💡 Recomendações de Ação")
                if emp.acoes_recomendadas:
                    for j, acao in enumerate(emp.acoes_recomendadas, 1):
                        st.markdown(f"**{j}.** {acao}")
                
                # BOTÃO DE ANÁLISE DETALHADA
                if st.button(f"🔍 Análise Detalhada", key=f"analise_{i}", use_container_width=True):
                    st.markdown("#### 🔬 Breakdown Detalhado do Score")
                    
                    # Calcular cada componente
                    breakdown = calcular_breakdown_score(emp)
                    
                    st.markdown(f"""
                    **📊 Decomposição do Score ({emp.score_risco:.1f} pontos):**
                    
                    **1. ⏰ Tempo de Casa ({breakdown['tempo_casa']:.1f} pts):**
                    - {emp.tempo_casa} anos na empresa
                    - {breakdown['tempo_casa_desc']}
                    
                    **2. 📋 PDI ({breakdown['pdi']:.1f} pts):**
                    - {'Participou' if emp.participou_pdi else 'NÃO participou'} nos últimos 12 meses
                    - {breakdown['pdi_desc']}
                    
                    **3. 🎓 Treinamentos ({breakdown['treinamentos']:.1f} pts):**
                    - {emp.num_treinamentos} treinamentos realizados
                    - {breakdown['treinamentos_desc']}
                    
                    **4. 📅 Ausências ({breakdown['ausencias']:.1f} pts):**
                    - {emp.num_ausencias} faltas nos últimos 6 meses
                    - {breakdown['ausencias_desc']}
                    
                    **5. ⚡ Bônus/Penalizações ({breakdown['bonus']:.1f} pts):**
                    - {breakdown['bonus_desc']}
                    
                    ---
                    **🎯 TOTAL: {emp.score_risco:.1f} pontos = {risk_level.upper()} RISCO**
                    """)
                    
                    # Recomendação urgente
                    if emp.score_risco > 70:
                        st.error("🚨 **AÇÃO URGENTE NECESSÁRIA!** Este colaborador apresenta risco crítico de saída.")
                    elif emp.score_risco > 45:
                        st.warning("⚠️ **ATENÇÃO NECESSÁRIA!** Monitorar de perto e implementar ações preventivas.")
                    else:
                        st.success("✅ **Situação controlada.** Manter acompanhamento regular.")

def calcular_breakdown_score(employee: Employee) -> dict:
    """Calcula breakdown detalhado do score para exibição"""
    breakdown = {
        'tempo_casa': 0,
        'pdi': 0,
        'treinamentos': 0,
        'ausencias': 0,
        'bonus': 0,
        'tempo_casa_desc': '',
        'pdi_desc': '',
        'treinamentos_desc': '',
        'ausencias_desc': '',
        'bonus_desc': ''
    }
    
    # Tempo de Casa
    if employee.tempo_casa < 0.5:
        breakdown['tempo_casa'] = 30 * SCORING_CONFIG["peso_tempo_casa"]
        breakdown['tempo_casa_desc'] = "Muito novo (< 6 meses) - Risco alto de não adaptação"
    elif employee.tempo_casa < 1:
        breakdown['tempo_casa'] = 50 * SCORING_CONFIG["peso_tempo_casa"]
        breakdown['tempo_casa_desc'] = "Pouco tempo (< 1 ano) - Risco de saída precoce"
    elif employee.tempo_casa < 2:
        breakdown['tempo_casa'] = 20 * SCORING_CONFIG["peso_tempo_casa"]
        breakdown['tempo_casa_desc'] = "Tempo baixo (< 2 anos) - Ainda em consolidação"
    else:
        breakdown['tempo_casa_desc'] = "Veterano - Estabilidade esperada"
    
    # PDI
    if not employee.participou_pdi:
        if employee.tempo_casa < 0.5:
            breakdown['pdi'] = 60 * SCORING_CONFIG["peso_pdi"]
            breakdown['pdi_desc'] = "Novato sem PDI - Falta de direcionamento"
        elif employee.tempo_casa < 1:
            breakdown['pdi'] = 80 * SCORING_CONFIG["peso_pdi"]
            breakdown['pdi_desc'] = "Sem PDI há mais de 6 meses - Sinal de desengajamento"
        elif employee.tempo_casa < 3:
            breakdown['pdi'] = 90 * SCORING_CONFIG["peso_pdi"]
            breakdown['pdi_desc'] = "Sem PDI há mais de 1 ano - Falta de desenvolvimento"
        else:
            breakdown['pdi'] = 100 * SCORING_CONFIG["peso_pdi"]
            breakdown['pdi_desc'] = "Veterano sem PDI - CRÍTICO! Falta total de desenvolvimento"
    else:
        breakdown['pdi_desc'] = "Participou do PDI - Desenvolvimento ativo"
    
    # Treinamentos
    if employee.tempo_casa >= 0.5:
        if employee.num_treinamentos == 0:
            breakdown['treinamentos'] = 100 * SCORING_CONFIG["peso_treinamentos"]
            breakdown['treinamentos_desc'] = "ZERO treinamentos - Falta total de capacitação"
        elif employee.num_treinamentos == 1:
            breakdown['treinamentos'] = 80 * SCORING_CONFIG["peso_treinamentos"]
            breakdown['treinamentos_desc'] = "Apenas 1 treinamento - Capacitação insuficiente"
        elif employee.num_treinamentos < 3:
            breakdown['treinamentos'] = 60 * SCORING_CONFIG["peso_treinamentos"]
            breakdown['treinamentos_desc'] = f"Poucos treinamentos ({employee.num_treinamentos}) - Abaixo do esperado"
        elif employee.num_treinamentos < 5:
            breakdown['treinamentos'] = 30 * SCORING_CONFIG["peso_treinamentos"]
            breakdown['treinamentos_desc'] = f"Treinamentos adequados ({employee.num_treinamentos})"
        else:
            breakdown['treinamentos_desc'] = f"Bem treinado ({employee.num_treinamentos} treinamentos)"
    else:
        if employee.num_treinamentos == 0:
            breakdown['treinamentos'] = 70 * SCORING_CONFIG["peso_treinamentos"]
            breakdown['treinamentos_desc'] = "Novato sem treinamentos - Necessita capacitação urgente"
    
    # Ausências
    if employee.num_ausencias <= 2:
        breakdown['ausencias'] = 10 * SCORING_CONFIG["peso_ausencias"]
        breakdown['ausencias_desc'] = "Pontualidade excelente"
    elif employee.num_ausencias <= 5:
        breakdown['ausencias'] = 40 * SCORING_CONFIG["peso_ausencias"]
        breakdown['ausencias_desc'] = "Ausências dentro do aceitável"
    elif employee.num_ausencias <= 10:
        breakdown['ausencias'] = 70 * SCORING_CONFIG["peso_ausencias"]
        breakdown['ausencias_desc'] = "Ausências preocupantes - Investigar causas"
    elif employee.num_ausencias <= 20:
        breakdown['ausencias'] = 90 * SCORING_CONFIG["peso_ausencias"]
        breakdown['ausencias_desc'] = "Ausências frequentes - Problema sério"
    else:
        breakdown['ausencias'] = 100 * SCORING_CONFIG["peso_ausencias"]
        breakdown['ausencias_desc'] = "Ausências excessivas - CRÍTICO!"
        
        if employee.num_ausencias >= 50:
            breakdown['bonus'] += 25
        elif employee.num_ausencias >= 30:
            breakdown['bonus'] += 15
    
    # Bônus combinações
    bonus_desc = []
    
    if (employee.tempo_casa >= 1 and 
        not employee.participou_pdi and 
        employee.num_treinamentos <= 1 and 
        employee.num_ausencias >= 20):
        breakdown['bonus'] += 25
        bonus_desc.append("Combinação crítica: Veterano problemático (+25 pts)")
    
    if (employee.tempo_casa < 1 and 
        not employee.participou_pdi and 
        employee.num_treinamentos == 0 and 
        employee.num_ausencias >= 30):
        breakdown['bonus'] += 20
        bonus_desc.append("Novato problemático (+20 pts)")
    
    if employee.num_ausencias >= 50:
        bonus_desc.append("Ausências extremas (+25 pts)")
    elif employee.num_ausencias >= 30:
        bonus_desc.append("Ausências muito altas (+15 pts)")
    
    breakdown['bonus_desc'] = '; '.join(bonus_desc) if bonus_desc else "Nenhum bônus aplicado"
    
    return breakdown

def render_export():
    if not st.session_state.employees:
        st.warning("⚠️ Carregue dados primeiro")
        return
    
    st.markdown("### 📋 Exportar Relatório")
    
    if st.button("📥 Gerar Excel", use_container_width=True):
        excel_data = export_to_excel(st.session_state.employees)
        
        st.download_button(
            label="💾 Download Excel",
            data=excel_data,
            file_name=f"relatorio_radar_rh_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# Teste do algoritmo
def teste_algoritmo():
    st.markdown("### 🧪 Teste do Algoritmo ULTRA Rigoroso")
    
    if st.button("🧪 Testar Caso do Vinicius"):
        # Caso real do Vinicius
        funcionario_vinicius = Employee(
            nome="Vinicius Paschoa",
            departamento="TI",
            cargo="Especialista de IA",
            tempo_casa=0.3,  # 3.6 meses
            participou_pdi=False,
            num_treinamentos=0,
            num_ausencias=50
        )
        
        score = calcular_score_risco(funcionario_vinicius)
        nivel = get_risk_level(score)
        fatores = identificar_fatores_risco(funcionario_vinicius)
        breakdown = calcular_breakdown_score(funcionario_vinicius)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Score", f"{score:.1f}/100")
        with col2:
            st.metric("Nível", nivel)
        with col3:
            st.metric("Fatores", len(fatores))
        
        st.markdown(f"""
        **🔥 BREAKDOWN DETALHADO PARA VINICIUS:**
        
        **1. ⏰ Tempo de Casa:** {breakdown['tempo_casa']:.1f} pts
        - 0.3 anos (3.6 meses) - Muito novo na empresa
        
        **2. 📋 PDI:** {breakdown['pdi']:.1f} pts  
        - NÃO participou - Novato sem direcionamento
        
        **3. 🎓 Treinamentos:** {breakdown['treinamentos']:.1f} pts
        - ZERO treinamentos - Falta total de capacitação
        
        **4. 📅 Ausências:** {breakdown['ausencias']:.1f} pts
        - 50 ausências - EXTREMAMENTE CRÍTICO!
        
        **5. ⚡ Bônus:** {breakdown['bonus']:.1f} pts
        - Novato problemático + Ausências extremas
        
        **🎯 TOTAL: {score:.1f} pontos = {nivel.upper()} RISCO**
        """)
        
        if score < 80:
            st.error(f"🚨 AINDA MUITO BAIXO! Esperado: 80+ pontos, Atual: {score:.1f}")
        else:
            st.success(f"✅ SCORE ADEQUADO! {score:.1f} pontos reflete o risco real")
        
        st.markdown("**🚨 Fatores detectados:**")
        for fator in fatores:
            st.markdown(f"• {fator}")
    
    # Teste adicional
    if st.button("🧪 Testar Caso Veterano Crítico"):
        funcionario_veterano = Employee(
            nome="Veterano Problemático", 
            departamento="TI",
            cargo="Desenvolvedor",
            tempo_casa=7.0,
            participou_pdi=False,
            num_treinamentos=0,
            num_ausencias=50
        )
        
        score = calcular_score_risco(funcionario_veterano)
        nivel = get_risk_level(score)
        
        st.metric("Veterano - Score", f"{score:.1f}/100")
        st.metric("Nível", nivel)
        
        if score < 85:
            st.error(f"🚨 Veterano crítico deveria ter 85+ pontos! Atual: {score:.1f}")
        else:
            st.success(f"✅ Score adequado para veterano crítico: {score:.1f}")

if __name__ == "__main__":
    main()
    
    # Mostrar teste
    with st.expander("🧪 Testar Algoritmo"):
        teste_algoritmo()
