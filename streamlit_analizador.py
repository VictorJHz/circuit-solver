import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
from sympy import symbols, Eq, Derivative, latex, Function, solve, dsolve, Matrix, zeros, simplify
import numpy as np

# ---------- CONFIGURACIÓN DE INTERFAZ ----------
st.set_page_config(page_title="Circuit Solver", layout="wide")
st.title("⚡ Circuit Solver")
st.caption("Analisis de circuitos electricos con generacion de ecuaciones y sistema diferencial")

# ---------- SESSION STATE ----------
if 'componentes' not in st.session_state:
    st.session_state.componentes = []

# ---------- COMPONENTES DISPONIBLES ----------
componentes_disponibles = {
    "Resistencia": {"unidad": "Ω", "tipo": "R", "needs_current": True, "tipo_elec": "Pasivo"},
    "Capacitor": {"unidad": "F", "tipo": "C", "needs_current": True, "tipo_elec": "Pasivo"},
    "Inductor": {"unidad": "H", "tipo": "L", "needs_current": True, "tipo_elec": "Pasivo"},
    "Fuente de Voltaje": {"unidad": "V", "tipo": "V", "needs_current": True, "tipo_elec": "Activo"},
    "Fuente de Corriente": {"unidad": "A", "tipo": "I", "needs_current": False, "tipo_elec": "Activo"}
}

prefijos = {"": 1, "p": 1e-12, "n": 1e-9, "µ": 1e-6, "m": 1e-3, "k": 1e3, "M": 1e6}

# ---------- FORMULARIO PARA AGREGAR COMPONENTES ----------
st.sidebar.header("Agregar Componente")
with st.sidebar.form(key='form_componente', clear_on_submit=True):
    input_nombre = st.text_input("Nombre del componente (ej: R1, C1, V1, I1)")
    nodo_origen = st.text_input("Nodo origen (ej: N0, N1...)")
    nodo_destino = st.text_input("Nodo destino (ej: N0, N1...)")
    tipo_componente = st.selectbox("Tipo de componente", list(componentes_disponibles.keys()))
    col_val, col_pref = st.columns([3, 1])
    with col_val:
        valor_text = st.text_input("Valor (solo numero)")
    with col_pref:
        prefijo_valor = st.selectbox("Prefijo", list(prefijos.keys()), index=0)
    submit = st.form_submit_button("Agregar Componente")

if submit:
    if not input_nombre or not valor_text or not nodo_origen or not nodo_destino:
        st.warning("Por favor, llena todos los campos")
    else:
        try:
            float(valor_text)
            componente = {
                "nombre": input_nombre,
                "tipo": tipo_componente,
                "tipo_corto": componentes_disponibles[tipo_componente]["tipo"],
                "tipo_elec": componentes_disponibles[tipo_componente]["tipo_elec"],
                "unidad": componentes_disponibles[tipo_componente]["unidad"],
                "valor": float(valor_text),
                "prefijo": prefijo_valor,
                "multiplo": prefijos[prefijo_valor],
                "valor_total": float(valor_text) * prefijos[prefijo_valor],
                "nodo_origen": nodo_origen,
                "nodo_destino": nodo_destino,
                "needs_current": componentes_disponibles[tipo_componente]["needs_current"]
            }
            st.session_state.componentes.append(componente)
            st.success(f"Componente {input_nombre} agregado correctamente")
        except ValueError:
            st.error("El valor debe ser un numero")

# ---------- MOSTRAR COMPONENTES ----------
st.subheader("Componentes agregados")
if st.session_state.componentes:
    for i, c in enumerate(st.session_state.componentes):
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"**{c['nombre']}**: {c['tipo']} ({c['tipo_elec']}) | Valor: {c['valor']}{c['prefijo']}{c['unidad']} | Nodos: {c['nodo_origen']} -> {c['nodo_destino']}")
        with col2:
            if st.button(f"Eliminar", key=f"del_{i}"):
                st.session_state.componentes.pop(i)
                st.rerun()
else:
    st.info("No hay componentes agregados todavia. Agrega componentes en la barra lateral.")

# ---------- FUNCIONES ----------
def obtener_nodos_unicos(componentes):
    nodos = set()
    for c in componentes:
        nodos.add(c['nodo_origen'])
        nodos.add(c['nodo_destino'])
    return sorted(list(nodos))

def analizar_circuito_rc(componentes):
    """Analiza si es un circuito RC serie y extrae parametros"""
    R_val = None
    C_val = None
    Vin_val = None
    
    for c in componentes:
        if c['tipo'] == "Resistencia":
            R_val = c['valor_total']
        elif c['tipo'] == "Capacitor":
            C_val = c['valor_total']
        elif c['tipo'] == "Fuente de Voltaje":
            Vin_val = c['valor_total']
    
    if R_val is not None and C_val is not None and Vin_val is not None:
        return R_val, C_val, Vin_val
    else:
        return None, None, None

def generar_matriz_incidencia(componentes, nodos):
    """Genera la matriz de incidencia A (nodos x ramas)"""
    nodos_no_tierra = [n for n in nodos if n != "N0"]
    n_nodos = len(nodos_no_tierra)
    n_ramas = len(componentes)
    
    nodo_idx = {nodo: i for i, nodo in enumerate(nodos_no_tierra)}
    A = zeros(n_nodos, n_ramas)
    
    for j, c in enumerate(componentes):
        if c['nodo_origen'] != "N0":
            A[nodo_idx[c['nodo_origen']], j] = 1
        if c['nodo_destino'] != "N0":
            A[nodo_idx[c['nodo_destino']], j] = -1
    
    return A, nodos_no_tierra

def generar_sistema_tablueau(componentes, nodos):
    """Genera el sistema matricial completo M·x = b (Método de Tablueau)"""
    nodos_no_tierra = [n for n in nodos if n != "N0"]
    n_nodos = len(nodos_no_tierra)
    n_ramas = len(componentes)
    
    nodo_idx = {nodo: i for i, nodo in enumerate(nodos_no_tierra)}
    
    # Matriz de incidencia A (n_nodos x n_ramas)
    A = zeros(n_nodos, n_ramas)
    
    # Matrices Z e Y para componentes
    Z = zeros(n_ramas, n_ramas)
    Y = zeros(n_ramas, n_ramas)
    Vs = zeros(n_ramas, 1)
    Is = zeros(n_ramas, 1)
    
    for j, c in enumerate(componentes):
        # Matriz de incidencia
        if c['nodo_origen'] != "N0":
            A[nodo_idx[c['nodo_origen']], j] = 1
        if c['nodo_destino'] != "N0":
            A[nodo_idx[c['nodo_destino']], j] = -1
        
        # Relaciones de componentes
        if c['tipo'] == "Resistencia":
            Z[j, j] = c['valor_total']
        elif c['tipo'] == "Capacitor":
            Z[j, j] = 1/(c['valor_total'] * symbols('s'))
        elif c['tipo'] == "Inductor":
            Z[j, j] = c['valor_total'] * symbols('s')
        elif c['tipo'] == "Fuente de Voltaje":
            Vs[j, 0] = c['valor_total']
        elif c['tipo'] == "Fuente de Corriente":
            Is[j, 0] = c['valor_total']
    
    return A, Z, Vs, Is, n_nodos, n_ramas

def dibujar_grafo_con_polaridad(componentes):
    G = nx.MultiDiGraph()
    nodos = obtener_nodos_unicos(componentes)
    for nodo in nodos:
        G.add_node(nodo)
    for c in componentes:
        if c['tipo'] == "Resistencia":
            color = "red"
            linewidth = 2
            tipo_label = "R"
        elif c['tipo'] == "Capacitor":
            color = "blue"
            linewidth = 2
            tipo_label = "C"
        elif c['tipo'] == "Inductor":
            color = "green"
            linewidth = 2
            tipo_label = "L"
        elif c['tipo'] == "Fuente de Voltaje":
            color = "orange"
            linewidth = 2.5
            tipo_label = "V"
        elif c['tipo'] == "Fuente de Corriente":
            color = "purple"
            linewidth = 2.5
            tipo_label = "I"
        else:
            color = "gray"
            linewidth = 1.5
            tipo_label = ""
        valor_str = f"{c['valor']}{c['prefijo']}{c['unidad']}"
        if c['tipo_elec'] == "Activo":
            label = f"{c['nombre']}\n{tipo_label}={valor_str}\n(+) -> (-)"
        else:
            label = f"{c['nombre']}\n{tipo_label}={valor_str}\ni ->"
        G.add_edge(c['nodo_origen'], c['nodo_destino'], 
                   label=label, tipo=c['tipo'], color=color, linewidth=linewidth)
    return G, nodos

# ---------- BOTONES PRINCIPALES ----------
st.subheader("Acciones")
col1, col2, col3, col4 = st.columns(4)

# ----- Mostrar Grafo -----
with col1:
    if st.button("Mostrar Grafo"):
        if not st.session_state.componentes:
            st.warning("Agrega al menos un componente")
        else:
            G, nodos = dibujar_grafo_con_polaridad(st.session_state.componentes)
            fig, ax = plt.subplots(figsize=(14, 10))
            pos = nx.spring_layout(G, seed=42, k=2, iterations=50)
            nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=3000, ax=ax, edgecolors='black', linewidths=2)
            nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold', ax=ax)
            edge_colors = [d['color'] for u, v, d in G.edges(data=True)]
            edge_widths = [d['linewidth'] for u, v, d in G.edges(data=True)]
            nx.draw_networkx_edges(G, pos, edge_color=edge_colors, arrows=True, arrowsize=25, arrowstyle='->', ax=ax, connectionstyle="arc3,rad=0.1", width=edge_widths)
            edge_labels = {(u, v): d['label'] for u, v, d in G.edges(data=True)}
            nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=9, ax=ax, bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
            plt.title("Grafo del Circuito - Polaridad y Direccion de Corriente", fontsize=14, fontweight='bold')
            plt.axis('off')
            legend_elements = [
                plt.Line2D([0], [0], color='red', linewidth=2, label='Resistencia (Pasivo)'),
                plt.Line2D([0], [0], color='blue', linewidth=2, label='Capacitor (Pasivo)'),
                plt.Line2D([0], [0], color='green', linewidth=2, label='Inductor (Pasivo)'),
                plt.Line2D([0], [0], color='orange', linewidth=2.5, label='Fuente Voltaje (Activo: + -> -)'),
                plt.Line2D([0], [0], color='purple', linewidth=2.5, label='Fuente Corriente (Activo: + -> -)')
            ]
            ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
            plt.figtext(0.02, 0.02, "Activos: flecha del positivo (+) al negativo (-) | Pasivos: direccion convencional de corriente", fontsize=10, style='italic')
            st.pyplot(fig)

# ----- Generar Sistema de Ecuaciones (CON FORMA MATRICIAL) -----
with col2:
    if st.button("Generar Ecuaciones"):
        if not st.session_state.componentes:
            st.warning("Agrega componentes primero")
        else:
            R, C, Vin = analizar_circuito_rc(st.session_state.componentes)
            
            if R is not None and C is not None and Vin is not None:
                # Circuito RC - mostrar analisis completo con forma matricial
                st.subheader("Analisis Completo del Circuito RC")
                tau = R * C
                
                # 1. KCL
                st.write("**1. Ley de Corrientes de Kirchhoff (KCL)**")
                st.latex(r"i_R = i_C")
                
                # 2. LVK
                st.write("**2. Ley de Voltajes de Kirchhoff (LVK)**")
                st.latex(r"V_{in} - V_R - V_C = 0")
                
                # 3. BR
                st.write("**3. Relaciones de los Componentes (BR)**")
                st.latex(r"V_R = R \cdot i_R")
                st.latex(r"i_C = C \cdot \frac{dV_C}{dt}")
                st.latex(r"V_{in} = 9")
                
                # 4. FORMA MATRICIAL (Método de Tablueau)
                st.write("**4. Forma Matricial (Metodo de Tablueau)**")
                st.write("El sistema se puede escribir como M·x = b:")
                
                # Variables: [V_N1, V_N2, i_V1, i_R1, i_C1]
                st.latex(r"""
                M = \begin{bmatrix}
                1 & 0 & 0 & 0 & 0 \\
                0 & 1 & 0 & 0 & 0 \\
                0 & 0 & 1 & -1 & 0 \\
                0 & 0 & 0 & 1 & -1 \\
                0 & 0 & 0 & 0 & 1
                \end{bmatrix}
                """)
                
                st.latex(r"""
                x = \begin{bmatrix}
                V_{N1} \\ V_{N2} \\ i_{V1} \\ i_{R1} \\ i_{C1}
                \end{bmatrix},\quad
                b = \begin{bmatrix}
                9 \\ 0 \\ 0 \\ 0 \\ C \cdot \frac{dV_{N2}}{dt}
                \end{bmatrix}
                """)
                
                st.caption("Forma compacta: A·i = 0 (KCL), v = Aᵀ·e (KVL), v = Z·i + Vs (BR)")
                
                # 5. Ecuacion diferencial
                st.write("**5. Ecuacion Diferencial del Circuito**")
                st.latex(rf"{Vin:.1f} - V_C = {R:.0f} \cdot {C:.0e} \cdot \frac{{dV_C}}{{dt}}")
                st.latex(rf"\frac{{dV_C}}{{dt}} + \frac{{1}}{{{tau:.4f}}} V_C = \frac{{{Vin:.1f}}}{{{tau:.4f}}}")
                
                # 6. Variable de estado
                st.write("**6. Variable de Estado**")
                st.latex(r"x(t) = V_C(t)")
                
                # 7. Clasificacion
                st.write("**7. Clasificacion del Sistema**")
                st.write(f"- **Orden:** Sistema de primer orden")
                st.write(f"- **Linealidad:** Lineal")
                st.write(f"- **Invarianza:** Invariante en el tiempo")
                
                # 8. Interpretacion fisica
                st.write("**8. Interpretacion Fisica**")
                st.markdown(f"""
                - **Carga del capacitor:** El capacitor se carga desde 0 V hasta {Vin:.1f} V
                - **Regimen transitorio:** Dura aproximadamente {5*tau:.2f} segundos (5τ)
                - **Estado estable:** Despues de {5*tau:.2f} s, Vc ≈ {Vin:.1f} V
                - **Constante de tiempo:** τ = {tau:.4f} s (63.2% de la carga final)
                """)
                
                # 9. Solucion analitica
                st.write("**9. Solucion Analitica**")
                st.latex(f"V_C(t) = {Vin:.1f} \\cdot (1 - e^{{-t/{tau:.4f}}})")
                
            else:
                # Circuito general - mostrar forma matricial completa
                st.subheader("Sistema Matricial Completo (Metodo de Tablueau)")
                
                nodos = obtener_nodos_unicos(st.session_state.componentes)
                A, Z, Vs, Is, n_nodos, n_ramas = generar_sistema_tablueau(st.session_state.componentes, nodos)
                
                if n_nodos > 0:
                    st.write("**Matriz de Incidencia A (nodos x ramas):**")
                    st.latex(latex(A))
                    
                    st.write("**Matriz de Impedancias Z:**")
                    st.latex(latex(Z))
                    
                    st.write("**Vector de Fuentes de Voltaje Vs:**")
                    st.latex(latex(Vs))
                    
                    st.write("**Vector de Fuentes de Corriente Is:**")
                    st.latex(latex(Is))
                    
                    st.write("**Sistema de Ecuaciones:**")
                    st.latex(r"A \cdot i = 0 \quad \text{(KCL)}")
                    st.latex(r"v = A^T \cdot e \quad \text{(KVL)}")
                    st.latex(r"v = Z \cdot i + V_s \quad \text{(BR)}")
                else:
                    st.info("Circuito sin nodos (solo tierra)")

# ----- Generar Código MATLAB -----
with col3:
    if st.button("Codigo MATLAB"):
        if not st.session_state.componentes:
            st.warning("Agrega componentes primero")
        else:
            R, C, Vin = analizar_circuito_rc(st.session_state.componentes)
            
            if R is not None and C is not None and Vin is not None:
                tau = R * C
                matlab_code = f"""%% Circuito RC - Analisis Completo
%% Parametros: R = {R:.2f} Ohm, C = {C:.2e} F, Vin = {Vin:.2f} V
%% Constante de tiempo: tau = {tau:.4f} s

clear; clc; close all;

%% 1. Variable de estado
syms Vc(t)
R = {R:.10f};
C = {C:.10f};
Vin = {Vin:.10f};
tau = R * C;

%% 2. Ecuacion diferencial en forma estandar
%% dVc/dt + (1/tau)*Vc = Vin/tau
eq = diff(Vc, t) + (1/tau)*Vc == Vin/tau;

%% 3. Condicion inicial (capacitor descargado)
cond = Vc(0) == 0;

%% 4. Solucion
Vc_sol = dsolve(eq, cond);

%% 5. Resultados
disp('=== SOLUCION DEL CIRCUITO RC ===');
fprintf('Vc(t) = %.2f * (1 - exp(-t/%.4f))\\n', Vin, tau);
pretty(Vc_sol);

%% 6. Parametros
fprintf('\\n=== PARAMETROS ===\\n');
fprintf('tau = %.4f s\\n', tau);
fprintf('Estado estable = %.2f V\\n', Vin);
fprintf('Transitorio (5tau) = %.4f s\\n', 5*tau);

%% 7. Grafica
figure;
fplot(Vc_sol, [0 5*tau], 'LineWidth', 2);
xlabel('t (s)'); ylabel('Vc(t) (V)');
title('Respuesta del Circuito RC');
grid on;
hold on;
plot([0 5*tau], [Vin Vin], '--r');
legend('Vc(t)', 'Vin', 'Location', 'best');
"""
            else:
                nodos = obtener_nodos_unicos(st.session_state.componentes)
                A, Z, Vs, Is, n_nodos, n_ramas = generar_sistema_tablueau(st.session_state.componentes, nodos)
                
                matlab_code = "%% Circuito General - Sistema Tablueau\nclear; clc;\n\n"
                matlab_code += "%% Matriz de incidencia A\n"
                matlab_code += f"A = {latex(A)};\n\n"
                matlab_code += "%% Matriz de impedancias Z\n"
                matlab_code += f"Z = {latex(Z)};\n\n"
                matlab_code += "%% Resolver sistema\n% A*i = 0, v = A^T*e, v = Z*i + Vs\n"
            
            st.subheader("Codigo MATLAB Generado")
            st.code(matlab_code, language="matlab")
            st.download_button("Descargar", data=matlab_code, file_name="circuito.m")

# ----- Limpiar Circuito -----
with col4:
    if st.button("Limpiar Todo"):
        st.session_state.componentes = []
        st.rerun()

# ========== ANALISIS AVANZADO ==========
st.divider()
st.subheader("Analisis Avanzado")

col5, col6, col7 = st.columns(3)

# ----- Validacion -----
with col5:
    with st.expander("Validar Circuito", expanded=False):
        if st.button("Ejecutar Validacion", key="validar"):
            if not st.session_state.componentes:
                st.warning("Agrega componentes")
            else:
                errores = []
                warnings = []
                hay_tierra = any(c['nodo_origen'] == "N0" or c['nodo_destino'] == "N0" for c in st.session_state.componentes)
                if not hay_tierra:
                    errores.append("No hay nodo de referencia (N0)")
                nombres = [c['nombre'] for c in st.session_state.componentes]
                if len(nombres) != len(set(nombres)):
                    errores.append("Nombres duplicados")
                for c in st.session_state.componentes:
                    if c['valor'] <= 0:
                        warnings.append(f"{c['nombre']}: valor no positivo")
                if errores:
                    for err in errores:
                        st.error(err)
                else:
                    st.success("Sin errores criticos")
                for warn in warnings:
                    st.warning(warn)

# ----- Matriz de Incidencia -----
with col6:
    with st.expander("Matriz de Incidencia A", expanded=False):
        if st.button("Generar Matriz A", key="incidencia"):
            if not st.session_state.componentes:
                st.warning("Agrega componentes")
            else:
                nodos = obtener_nodos_unicos(st.session_state.componentes)
                A, nodos_nt = generar_matriz_incidencia(st.session_state.componentes, nodos)
                st.write(f"**Matriz de Incidencia A** ({len(nodos_nt)} nodos x {len(st.session_state.componentes)} ramas)")
                st.latex(latex(A))
                st.caption("Filas: nodos (excepto N0) | Columnas: ramas (componentes)")
                st.caption("+1: corriente sale del nodo | -1: corriente entra al nodo")

# ----- Sistema Tablueau -----
with col7:
    with st.expander("Sistema Tablueau (M·x = b)", expanded=False):
        if st.button("Generar Sistema Tablueau", key="tablueau"):
            if not st.session_state.componentes:
                st.warning("Agrega componentes")
            else:
                nodos = obtener_nodos_unicos(st.session_state.componentes)
                A, Z, Vs, Is, n_nodos, n_ramas = generar_sistema_tablueau(st.session_state.componentes, nodos)
                
                st.write("**Sistema M·x = b**")
                st.write("")
                st.write("**KCL:** A·i = 0")
                st.latex(latex(A) + r" \cdot i = 0")
                st.write("")
                st.write("**KVL:** v = Aᵀ·e")
                st.latex(r"v = " + latex(A.T) + r" \cdot e")
                st.write("")
                st.write("**BR:** v = Z·i + Vs")
                st.latex(r"v = " + latex(Z) + r" \cdot i + " + latex(Vs))

# ---------- INFORMACION ADICIONAL ----------
with st.sidebar.expander("Instrucciones"):
    st.markdown("""
    ### Como usar:
    1. **Nodo N0**: Usa N0 como tierra
    2. **Agrega componentes**: Completa todos los campos
    3. **Mostrar Grafo**: Visualiza polaridad y direcciones
    4. **Generar Ecuaciones**: Obtiene analisis completo con forma matricial
    5. **MATLAB**: Descarga codigo optimizado
    
    ### Ejemplo Circuito RC:
    | Nombre | Tipo | Origen | Destino | Valor |
    |--------|------|--------|---------|-------|
    | V1 | Fuente Voltaje | N0 | N1 | 9 |
    | R1 | Resistencia | N1 | N2 | 27k |
    | C1 | Capacitor | N2 | N0 | 100u |
    
    ### Forma Matricial (Tablueau):
    - **A**: Matriz de incidencia (nodos x ramas)
    - **Z**: Matriz de impedancias
    - **Vs/Is**: Vectores de fuentes
    - **Sistema**: A·i = 0, v = Aᵀ·e, v = Z·i + Vs
    """)
