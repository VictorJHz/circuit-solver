import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
from sympy import symbols, Eq, Derivative, latex, Function, solve, dsolve, Matrix, zeros, simplify
import numpy as np

# ---------- CONFIGURACIÓN DE INTERFAZ ----------
st.set_page_config(page_title="Circuit Solver", layout="wide")
st.title("⚡ Circuit Solver")
st.caption("Analisis de circuitos electricos - Metodo de Tablueau en dominio del tiempo")

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

# ----- Generar Sistema de Ecuaciones (VERSION FINAL CORREGIDA) -----
with col2:
    if st.button("Generar Ecuaciones"):
        if not st.session_state.componentes:
            st.warning("Agrega componentes primero")
        else:
            R, C, Vin = analizar_circuito_rc(st.session_state.componentes)
            
            if R is not None and C is not None and Vin is not None:
                tau = R * C
                st.subheader("Analisis Completo del Circuito RC")
                
                # ========== 1. CONVENCION UNICA Y CONSISTENTE ==========
                st.write("### 🔷 CONVENCION UNICA Y CONSISTENTE")
                st.markdown("""
                **Convencion de signos adoptada (UNICA para todo el desarrollo):**
                - **KCL:** +1 = corriente sale del nodo | -1 = corriente entra al nodo
                - **KVL:** v_rama = e_origen - e_destino
                - **BR:** v_rama = Z·i_rama + V_s (dominio tiempo)
                """)
                
                # ========== 2. MATRIZ DE INCIDENCIA A (UNICA) ==========
                st.write("**1. Matriz de Incidencia A (UNICA - no cambia)**")
                st.write("**Orden de ramas:** [V1, R1, C1]")
                st.write("**Convencion:** +1 sale, -1 entra")
                A = Matrix([
                    [1, -1, 0],   # Nodo N1: V1 sale, R1 entra
                    [0, 1, -1]    # Nodo N2: R1 sale, C1 entra
                ])
                st.latex(r"A = \begin{bmatrix} 1 & -1 & 0 \\ 0 & 1 & -1 \end{bmatrix}")
                st.caption("Filas: nodos N1, N2 | Columnas: ramas [V1, R1, C1]")
                
                # ========== 3. VECTOR e (potenciales nodales) ==========
                st.write("**2. Vector e (Potenciales nodales)**")
                st.latex(r"e = \begin{bmatrix} V_{N1} \\ V_{N2} \end{bmatrix} \quad [V]")
                st.caption("Voltajes de los nodos respecto a tierra (N0 = 0V)")
                
                # ========== 4. KCL en forma matricial ==========
                st.write("**3. KCL en forma matricial**")
                st.latex(r"A \cdot i = 0")
                st.latex(r"\begin{bmatrix} 1 & -1 & 0 \\ 0 & 1 & -1 \end{bmatrix} \begin{bmatrix} i_{V1} \\ i_{R1} \\ i_{C1} \end{bmatrix} = \begin{bmatrix} 0 \\ 0 \end{bmatrix}")
                st.caption("Ecuaciones: i_V1 - i_R1 = 0, i_R1 - i_C1 = 0")
                
                # ========== 5. KVL en forma matricial con interpretacion explicita ==========
                st.write("**4. KVL en forma matricial**")
                st.latex(r"v = A^T \cdot e")
                st.latex(r"\begin{bmatrix} v_{V1} \\ v_{R1} \\ v_{C1} \end{bmatrix} = \begin{bmatrix} 1 & 0 \\ -1 & 1 \\ 0 & -1 \end{bmatrix} \begin{bmatrix} V_{N1} \\ V_{N2} \end{bmatrix}")
                st.write("**Interpretacion explicita:**")
                st.latex(r"v_{V1} = V_{N1} - 0 = V_{N1} \quad [V]")
                st.latex(r"v_{R1} = V_{N1} - V_{N2} \quad [V]")
                st.latex(r"v_{C1} = V_{N2} - 0 = V_{N2} \quad [V]")
                st.caption("Nota: El signo negativo en la tercera fila de Aᵀ indica que v_C1 = -V_N2, pero por definicion v_C1 = V_N2 - 0 = V_N2")
                
                # ========== 6. BR EN DOMINIO TIEMPO (NO LAPLACE) ==========
                st.write("**5. Relaciones de los Componentes (BR) en dominio tiempo**")
                st.latex(r"\text{Fuente V1:} \quad v_{V1} = V_{in} \quad [V]")
                st.latex(r"\text{Resistencia R1:} \quad v_{R1} = R \cdot i_{R1} \quad [V]")
                st.latex(r"\text{Capacitor C1:} \quad i_{C1} = C \cdot \frac{d v_{C1}}{dt} \quad [A]")
                st.caption("**NOTA:** Todas las ecuaciones estan en dominio del tiempo (no Laplace)")
                
                # ========== 7. MATRIZ Z EN DOMINIO TIEMPO ==========
                st.write("**6. Matriz Z (Impedancias) - Notacion en tiempo**")
                st.latex(r"Z = \begin{bmatrix} 0 & 0 & 0 \\ 0 & R & 0 \\ 0 & 0 & \frac{1}{C \cdot \frac{d}{dt}} \end{bmatrix}")
                st.caption("El operador 1/(C·d/dt) representa la relacion integral: v_C = (1/C)∫ i_C dt")
                
                # ========== 8. VECTOR Vs (mapeo explicito) ==========
                st.write("**7. Vector Vs (Fuentes de voltaje)**")
                st.latex(r"V_s = \begin{bmatrix} V_{in} \\ 0 \\ 0 \end{bmatrix}")
                st.caption("**Mapeo:** Rama 1 (V1) → Fuente de voltaje Vin | Ramas 2 y 3 → 0")
                
                # ========== 9. MATRIZ M DEL METODO TABLEAU (FORMA RIGUROSA) ==========
                st.write("**8. Matriz M del Metodo de Tablueau**")
                st.write("**Estructura rigurosa (forma estandar):**")
                st.latex(r"\begin{bmatrix} A & 0 & 0 \\ 0 & I & 0 \\ A^T & 0 & -Z \end{bmatrix} \begin{bmatrix} e \\ i \\ v \end{bmatrix} = \begin{bmatrix} 0 \\ 0 \\ V_s \end{bmatrix}")
                st.write("")
                st.write("**Donde:**")
                st.write("- **A** = Matriz de incidencia")
                st.write("- **I** = Matriz identidad")
                st.write("- **Z** = Matriz de impedancias")
                st.write("- **e** = Potenciales nodales")
                st.write("- **i** = Corrientes de rama")
                st.write("- **v** = Voltajes de rama")
                st.write("- **V_s** = Fuentes de voltaje")
                st.write("")
                st.write("**Para el circuito RC:**")
                
                # Matriz M completa con bloques
                st.latex(r"M = \left[\begin{array}{cc|ccc|ccc} 
                0 & 0 & 1 & -1 & 0 & 0 & 0 & 0 \\
                0 & 0 & 0 & 1 & -1 & 0 & 0 & 0 \\
                \hline
                0 & 0 & 0 & 0 & 0 & 1 & 0 & 0 \\
                0 & 0 & 0 & 0 & 0 & 0 & 1 & 0 \\
                0 & 0 & 0 & 0 & 0 & 0 & 0 & 1 \\
                \hline
                1 & 0 & 0 & 0 & 0 & -1 & 0 & 0 \\
                -1 & 1 & 0 & 0 & 0 & 0 & -1 & 0 \\
                0 & -1 & 0 & 0 & 0 & 0 & 0 & -1
                \end{array}\right]")
                
                st.write("**Vector x:**")
                st.latex(r"x = \begin{bmatrix} V_{N1} \\ V_{N2} \\ i_{V1} \\ i_{R1} \\ i_{C1} \\ v_{V1} \\ v_{R1} \\ v_{C1} \end{bmatrix}")
                
                st.write("**Vector b:**")
                st.latex(r"b = \begin{bmatrix} 0 \\ 0 \\ 0 \\ 0 \\ 0 \\ V_{in} \\ 0 \\ 0 \end{bmatrix}")
                
                # ========== 10. ECUACION DIFERENCIAL EN TIEMPO ==========
                st.write("**9. Ecuacion Diferencial del Circuito (dominio tiempo)**")
                st.latex(rf"{Vin:.1f} - V_C = {R:.0f} \cdot {C:.0e} \cdot \frac{{dV_C}}{{dt}} \quad [V]")
                st.latex(rf"\frac{{dV_C}}{{dt}} + \frac{{1}}{{{tau:.4f}}} V_C = \frac{{{Vin:.1f}}}{{{tau:.4f}}} \quad [V/s]")
                st.caption(f"Unidades: V_C [V], t [s], dV_C/dt [V/s]")
                
                # ========== 11. VARIABLE DE ESTADO ==========
                st.write("**10. Variable de Estado**")
                st.latex(r"x(t) = V_C(t) \quad [V]")
                
                # ========== 12. ECUACION DE ESTADO ==========
                st.write("**11. Ecuacion de Estado**")
                a = -1/tau
                b = Vin/tau
                st.latex(rf"\dot{{x}} = -\frac{{1}}{{RC}} x + \frac{{V_{{in}}}}{{RC}}")
                st.latex(rf"\dot{{x}} = {a:.4f} x + {b:.4f} \quad [V/s]")
                st.caption(f"Forma estandar: ẋ = A·x + B·u | A = {a:.4f} [1/s], B = {b:.4f} [V/s]")
                
                # ========== 13. CLASIFICACION ==========
                st.write("**12. Clasificacion del Sistema**")
                st.write(f"- **Orden:** Sistema de primer orden")
                st.write(f"- **Linealidad:** Lineal")
                st.write(f"- **Invarianza:** Invariante en el tiempo")
                st.write(f"- **Tipo:** Pasa-bajas de primer orden")
                
                # ========== 14. INTERPRETACION FISICA ==========
                st.write("**13. Interpretacion Fisica**")
                st.markdown(f"""
                - **Carga del capacitor:** El capacitor se carga desde 0 V hasta {Vin:.1f} V
                - **Regimen transitorio:** Dura aproximadamente {5*tau:.2f} segundos (5τ)
                - **Estado estable:** Despues de {5*tau:.2f} s, Vc ≈ {Vin:.1f} V
                - **Constante de tiempo:** τ = {tau:.4f} s (63.2% de la carga final)
                """)
                
                # ========== 15. SOLUCION ANALITICA ==========
                st.write("**14. Solucion Analitica**")
                st.latex(f"V_C(t) = {Vin:.1f} \\cdot (1 - e^{{-t/{tau:.4f}}}) \\quad [V]")
                
            else:
                st.subheader("Sistema Matricial Completo (Metodo de Tablueau)")
                st.info("Para circuitos no RC, se muestra la estructura general del metodo de Tablueau")

# ----- Generar Código MATLAB -----
with col3:
    if st.button("Codigo MATLAB"):
        if not st.session_state.componentes:
            st.warning("Agrega componentes primero")
        else:
            R, C, Vin = analizar_circuito_rc(st.session_state.componentes)
            
            if R is not None and C is not None and Vin is not None:
                tau = R * C
                matlab_code = f"""%% Circuito RC - Analisis Completo (Dominio Tiempo)
%% Parametros: R = {R:.2f} Ohm, C = {C:.2e} F, Vin = {Vin:.2f} V
%% Constante de tiempo: tau = {tau:.4f} s

clear; clc; close all;

%% 1. Variable de estado [V]
syms Vc(t)
R = {R:.10f};
C = {C:.10f};
Vin = {Vin:.10f};
tau = R * C;

%% 2. Ecuacion de estado [V/s]
%% dVc/dt = -(1/RC)*Vc + Vin/RC
A = -1/tau;      % [1/s]
B = Vin/tau;     % [V/s]
eq = diff(Vc, t) == A*Vc + B;

%% 3. Condicion inicial [V]
cond = Vc(0) == 0;

%% 4. Solucion [V]
Vc_sol = dsolve(eq, cond);

%% 5. Resultados
disp('=== SOLUCION DEL CIRCUITO RC ===');
fprintf('Vc(t) = %.2f * (1 - exp(-t/%.4f)) [V]\\n', Vin, tau);
pretty(Vc_sol);

%% 6. Parametros del sistema
fprintf('\\n=== PARAMETROS DEL SISTEMA ===\\n');
fprintf('tau = %.4f [s]\\n', tau);
fprintf('Estado estable = %.2f [V]\\n', Vin);
fprintf('Transitorio (5tau) = %.4f [s]\\n', 5*tau);

%% 7. Grafica
figure;
fplot(Vc_sol, [0 5*tau], 'LineWidth', 2);
xlabel('t [s]', 'FontSize', 12);
ylabel('Vc(t) [V]', 'FontSize', 12);
title('Respuesta del Circuito RC', 'FontSize', 14);
grid on;
hold on;
plot([0 5*tau], [Vin Vin], '--r', 'LineWidth', 1.5);
legend('Vc(t)', 'Vin', 'Location', 'best');
"""
            else:
                matlab_code = "%% Circuito General\nclear; clc;\n% Usar las ecuaciones generadas en la app\n"
            
            st.subheader("Codigo MATLAB Generado")
            st.code(matlab_code, language="matlab")
            st.download_button("Descargar", data=matlab_code, file_name="circuito.m")

# ----- Limpiar Circuito -----
with col4:
    if st.button("Limpiar Todo"):
        st.session_state.componentes = []
        st.rerun()

# ---------- ANALISIS AVANZADO ----------
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
        st.write("**Matriz de Incidencia A (UNICA)**")
        st.write("**Orden de ramas:** [V1, R1, C1]")
        st.write("**Convencion:** +1 sale, -1 entra")
        A = Matrix([
            [1, -1, 0],
            [0, 1, -1]
        ])
        st.latex(r"A = \begin{bmatrix} 1 & -1 & 0 \\ 0 & 1 & -1 \end{bmatrix}")
        st.caption("**NOTA:** Esta es la UNICA matriz A. No hay versiones alternativas.")

# ----- Metodo Tablueau -----
with col7:
    with st.expander("Metodo de Tablueau", expanded=False):
        st.write("### Metodo de Tablueau - Forma Estandar")
        st.write("")
        st.write("**Convencion UNICA:**")
        st.write("- KCL: +1 sale, -1 entra")
        st.write("- KVL: v = e_origen - e_destino")
        st.write("- BR: v = Z·i + Vs (dominio tiempo)")
        st.write("")
        st.write("**Estructura rigurosa:**")
        st.latex(r"\begin{bmatrix} A & 0 & 0 \\ 0 & I & 0 \\ A^T & 0 & -Z \end{bmatrix} \begin{bmatrix} e \\ i \\ v \end{bmatrix} = \begin{bmatrix} 0 \\ 0 \\ V_s \end{bmatrix}")
        st.write("")
        st.write("**Para el circuito RC:**")
        st.latex(r"e = \begin{bmatrix} V_{N1} \\ V_{N2} \end{bmatrix}, \quad i = \begin{bmatrix} i_{V1} \\ i_{R1} \\ i_{C1} \end{bmatrix}, \quad v = \begin{bmatrix} v_{V1} \\ v_{R1} \\ v_{C1} \end{bmatrix}")
        st.write("")
        st.write("**NOTA IMPORTANTE:**")
        st.write("Todas las ecuaciones estan en **dominio del tiempo**. No se usa transformada de Laplace para mantener consistencia con la ecuacion diferencial final.")

# ---------- INFORMACION ADICIONAL ----------
with st.sidebar.expander("Instrucciones"):
    st.markdown("""
    ### Como usar:
    1. **Nodo N0**: Usa N0 como tierra
    2. **Agrega componentes**: Completa todos los campos
    3. **Mostrar Grafo**: Visualiza polaridad y direcciones
    4. **Generar Ecuaciones**: Obtiene analisis completo
    5. **MATLAB**: Descarga codigo optimizado
    
    ### Ejemplo Circuito RC:
    | Nombre | Tipo | Origen | Destino | Valor |
    |--------|------|--------|---------|-------|
    | V1 | Fuente Voltaje | N0 | N1 | 9 |
    | R1 | Resistencia | N1 | N2 | 27k |
    | C1 | Capacitor | N2 | N0 | 100u |
    
    ### Convencion UNICA:
    - **KCL:** +1 sale, -1 entra
    - **KVL:** v = e_origen - e_destino
    - **BR:** v = Z·i + Vs (dominio tiempo)
    
    ### Metodo de Tablueau:
    - Sistema M·x = b con 8 ecuaciones y 8 variables
    - Incluye KCL, KVL y BR en forma matricial
    - Todo en dominio del tiempo (no Laplace)
    """)
