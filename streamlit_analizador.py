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

# ---------- FUNCIONES PARA GENERAR ECUACIONES ----------
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
    nodo_capacitor = None
    nodo_resistencia = None
    
    for c in componentes:
        if c['tipo'] == "Resistencia":
            R_val = c['valor_total']
            nodo_resistencia = c['nodo_destino'] if c['nodo_origen'] != "N0" else c['nodo_origen']
        elif c['tipo'] == "Capacitor":
            C_val = c['valor_total']
            if c['nodo_destino'] == "N0":
                nodo_capacitor = c['nodo_origen']
            else:
                nodo_capacitor = c['nodo_destino']
        elif c['tipo'] == "Fuente de Voltaje":
            Vin_val = c['valor_total']
    
    return R_val, C_val, Vin_val, nodo_capacitor, nodo_resistencia

def generar_ecuacion_diferencial_rc(R, C, Vin):
    """Genera la ecuacion diferencial del circuito RC"""
    t = symbols('t')
    Vc = Function('Vc')(t)
    
    # Ecuacion diferencial: Vin - Vc = R * C * dVc/dt
    eq_diferencial = Eq(Vin - Vc, R * C * Derivative(Vc, t))
    
    # Forma estandar: dVc/dt + (1/(RC)) * Vc = Vin/(RC)
    tau = R * C
    forma_estandar = Eq(Derivative(Vc, t) + (1/tau) * Vc, Vin/tau)
    
    # Variable de estado
    x = Function('x')(t)
    x_def = Eq(x, Vc)
    
    return eq_diferencial, forma_estandar, tau

def obtener_tipo_sistema(R, C):
    """Determina el tipo de sistema"""
    tau = R * C
    if tau > 0:
        return "Sistema de primer orden", "Lineal", "Invariante en el tiempo"
    return None, None, None

def interpretacion_fisica(Vin, tau):
    """Interpretacion fisica del resultado"""
    return f"""
    **Interpretacion Fisica:**
    - **Carga del capacitor:** El capacitor se carga desde 0 V hasta {Vin} V
    - **Régimen transitorio:** Dura aproximadamente {5*tau:.2f} segundos (5τ)
    - **Estado estable:** Después de {5*tau:.2f} s, Vc ≈ {Vin} V
    - **Constante de tiempo:** τ = {tau:.4f} s (63.2% de la carga final)
    """

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

# ----- Generar Sistema de Ecuaciones (MEJORADO) -----
with col2:
    if st.button("Generar Ecuaciones"):
        if not st.session_state.componentes:
            st.warning("Agrega componentes primero")
        else:
            t = symbols('t')
            nodos = obtener_nodos_unicos(st.session_state.componentes)
            
            # Detectar si es circuito RC
            R, C, Vin, nodo_cap, _ = analizar_circuito_rc(st.session_state.componentes)
            
            if R and C and Vin:
                # Es un circuito RC - mostrar analisis completo
                st.subheader("📐 Analisis Completo del Circuito RC")
                
                # 1. KCL (forma nodal pura, sin corriente de fuente)
                st.write("**1. Ley de Corrientes de Kirchhoff (KCL)**")
                st.latex(r"i_R = i_C")
                st.caption("La corriente que pasa por la resistencia es igual a la corriente que pasa por el capacitor")
                
                # 2. LVK explícito
                st.write("**2. Ley de Voltajes de Kirchhoff (LVK)**")
                st.latex(r"V_{fuente} - V_R - V_C = 0")
                st.caption("Suma de voltajes en la malla cerrada es igual a cero")
                
                # 3. Relaciones de componentes
                st.write("**3. Relaciones de los Componentes (BR)**")
                st.latex(r"V_R = R \cdot i_R")
                st.latex(r"i_C = C \cdot \frac{dV_C}{dt}")
                st.latex(r"V_{fuente} = V_{in}")
                st.caption("Ley de Ohm y relacion del capacitor")
                
                # 4. Ecuacion diferencial
                st.write("**4. Ecuacion Diferencial del Circuito**")
                eq_diff, forma_std, tau = generar_ecuacion_diferencial_rc(R, C, Vin)
                st.latex(latex(eq_diff))
                st.caption(f"Ecuacion diferencial que describe la dinamica del circuito (τ = {tau:.4f} s)")
                
                # 5. Forma estandar
                st.write("**5. Forma Estandar del Sistema**")
                st.latex(latex(forma_std))
                st.caption(f"Forma canonica: dVc/dt + (1/τ)·Vc = Vin/τ")
                
                # 6. Variable de estado
                st.write("**6. Variable de Estado**")
                st.latex(r"x(t) = V_C(t)")
                st.caption("La variable de estado es el voltaje en el capacitor")
                
                # 7. Tipo de sistema
                st.write("**7. Clasificacion del Sistema**")
                tipo, lineal, invar = obtener_tipo_sistema(R, C)
                st.write(f"- **Orden:** {tipo}")
                st.write(f"- **Linealidad:** {lineal}")
                st.write(f"- **Variacion en el tiempo:** {invar}")
                
                # 8. Interpretacion fisica
                st.write("**8. Interpretacion Fisica**")
                st.markdown(interpretacion_fisica(Vin, tau))
                
                # 9. Solucion analitica
                st.write("**9. Solucion Analitica**")
                Vc_sol = Vin * (1 - np.exp(-t/tau))
                st.latex(f"V_C(t) = {Vin:.1f} \\cdot (1 - e^{{-t/{tau:.4f}}})")
                
            else:
                # No es RC simple - mostrar ecuaciones basicas
                st.warning("Circuito no es RC serie simple. Mostrando ecuaciones basicas.")
                v_nodos = {}
                for nodo in nodos:
                    if nodo != "N0":
                        v_nodos[nodo] = Function(f'V_{nodo}')(t)
                i_componentes = {}
                for c in st.session_state.componentes:
                    if c['needs_current'] or c['tipo'] == "Fuente de Corriente":
                        i_componentes[c['nombre']] = Function(f'i_{c["nombre"]}')(t)
                
                ecuaciones_kcl = []
                for nodo in nodos:
                    if nodo == "N0":
                        continue
                    suma = 0
                    for c in st.session_state.componentes:
                        if c['nodo_origen'] == nodo:
                            suma += i_componentes[c['nombre']]
                        elif c['nodo_destino'] == nodo:
                            suma -= i_componentes[c['nombre']]
                    if suma != 0:
                        ecuaciones_kcl.append(Eq(suma, 0))
                
                ecuaciones_br = []
                for c in st.session_state.componentes:
                    nombre = c['nombre']
                    tipo = c['tipo']
                    valor_total = c['valor_total']
                    nodo_o = c['nodo_origen']
                    nodo_d = c['nodo_destino']
                    
                    if nodo_o == "N0":
                        v_o = 0
                    else:
                        v_o = v_nodos[nodo_o]
                    if nodo_d == "N0":
                        v_d = 0
                    else:
                        v_d = v_nodos[nodo_d]
                    v_diff = v_o - v_d
                    
                    if tipo == "Resistencia":
                        ecuaciones_br.append(Eq(v_diff, valor_total * i_componentes[nombre]))
                    elif tipo == "Capacitor":
                        ecuaciones_br.append(Eq(i_componentes[nombre], valor_total * Derivative(v_diff, t)))
                    elif tipo == "Fuente de Voltaje":
                        if nodo_o == "N0":
                            ecuaciones_br.append(Eq(v_d - v_o, valor_total))
                        else:
                            ecuaciones_br.append(Eq(v_diff, valor_total))
                    elif tipo == "Fuente de Corriente":
                        ecuaciones_br.append(Eq(i_componentes[nombre], valor_total))
                
                st.write("**KCL - Ley de Corrientes de Kirchhoff**")
                for eq in ecuaciones_kcl:
                    st.latex(latex(eq))
                st.write("**BR - Relaciones de Componentes**")
                for eq in ecuaciones_br:
                    st.latex(latex(eq))

# ----- Generar Código MATLAB (MEJORADO) -----
with col3:
    if st.button("Codigo MATLAB"):
        if not st.session_state.componentes:
            st.warning("Agrega componentes primero")
        else:
            R, C, Vin, _, _ = analizar_circuito_rc(st.session_state.componentes)
            
            if R and C and Vin:
                tau = R * C
                matlab_code = f"""%% Circuito RC - Analisis Completo
%% Parametros: R = {R:.2f} Ohm, C = {C:.2e} F, Vin = {Vin:.2f} V
%% Constante de tiempo: tau = {tau:.4f} s

clear; clc; close all;

%% 1. Definicion de variable de estado
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

%% 4. Resolver la ecuacion diferencial
Vc_sol = dsolve(eq, cond);

%% 5. Mostrar resultado analitico
disp('=== SOLUCION DEL CIRCUITO RC ===');
disp('Variable de estado: Vc(t)');
pretty(Vc_sol);
fprintf('\\nForma simplificada: Vc(t) = %.2f * (1 - exp(-t/%.4f))\\n', Vin, tau);

%% 6. Parametros del sistema
fprintf('\\n=== PARAMETROS DEL SISTEMA ===\\n');
fprintf('Constante de tiempo tau = %.4f segundos\\n', tau);
fprintf('Voltaje final en estado estable = %.2f V\\n', Vin);
fprintf('Tiempo de establecimiento (5*tau) = %.4f segundos\\n', 5*tau);

%% 7. Graficar respuesta
figure('Position', [100, 100, 900, 500]);
fplot(Vc_sol, [0 5*tau], 'LineWidth', 2, 'Color', 'b');
xlabel('Tiempo (s)', 'FontSize', 12);
ylabel('Vc(t) (V)', 'FontSize', 12);
title('Respuesta del Circuito RC - Carga del Capacitor', 'FontSize', 14);
grid on;
hold on;
plot([0 5*tau], [Vin Vin], '--r', 'LineWidth', 1.5);
legend('Vc(t)', 'Vin', 'Location', 'best');

%% 8. Interpretacion
fprintf('\\n=== INTERPRETACION FISICA ===\\n');
fprintf('El capacitor se carga desde 0 V hasta %.2f V\\n', Vin);
fprintf('El regimen transitorio dura %.2f segundos (5τ)\\n', 5*tau);
"""
            else:
                matlab_code = "%% Circuito no RC simple\nclear; clc;\n% Agregar ecuaciones manualmente\n"
            
            st.subheader("Codigo MATLAB Generado")
            st.code(matlab_code, language="matlab")
            st.download_button("Descargar", data=matlab_code, file_name="circuito_rc.m")

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

# ----- Sistema Completo -----
with col6:
    with st.expander("Sistema Completo (KCL + LVK + BR)", expanded=False):
        if st.button("Generar Sistema Completo", key="sistema"):
            if not st.session_state.componentes:
                st.warning("Agrega componentes")
            else:
                R, C, Vin, _, _ = analizar_circuito_rc(st.session_state.componentes)
                if R and C and Vin:
                    st.write("### Sistema de Ecuaciones del Circuito RC")
                    st.write("")
                    st.write("**KCL:**")
                    st.latex(r"i_R = i_C")
                    st.write("")
                    st.write("**LVK:**")
                    st.latex(r"V_{in} - V_R - V_C = 0")
                    st.write("")
                    st.write("**BR:**")
                    st.latex(r"V_R = R \cdot i_R")
                    st.latex(r"i_C = C \cdot \frac{dV_C}{dt}")
                    st.write("")
                    st.write("**Sistema Reducido:**")
                    st.latex(r"\frac{V_{in} - V_C}{R} = C \cdot \frac{dV_C}{dt}")
                    st.latex(r"\frac{dV_C}{dt} + \frac{1}{RC} V_C = \frac{V_{in}}{RC}")
                else:
                    st.info("Circuito no reconocido como RC serie simple")

# ----- Analisis Nodal -----
with col7:
    with st.expander("Analisis Nodal (Matriz G)", expanded=False):
        if st.button("Ejecutar Analisis Nodal", key="nodal2"):
            if not st.session_state.componentes:
                st.warning("Agrega componentes")
            else:
                R, C, Vin, _, _ = analizar_circuito_rc(st.session_state.componentes)
                if R and C and Vin:
                    st.write("### Analisis Nodal (Metodo de Supernodo)")
                    st.write("")
                    st.write("**Matriz de Conductancias G:**")
                    st.latex(r"G = \begin{bmatrix} \frac{1}{R} & -\frac{1}{R} \\ -\frac{1}{R} & \frac{1}{R} \end{bmatrix}")
                    st.write("**Vector de Corrientes I:**")
                    st.latex(r"I = \begin{bmatrix} 0 \\ 0 \end{bmatrix}")
                    st.write("")
                    st.write("**Nota:** La fuente de voltaje requiere un supernodo. El sistema se resuelve con:")
                    st.latex(r"V_{N1} = V_{in}")
                    st.latex(r"\frac{V_{N1} - V_{N2}}{R} = C \cdot \frac{dV_{N2}}{dt}")
                else:
                    st.info("Analisis nodal optimizado para circuitos RC serie")

# ---------- INFORMACION ADICIONAL ----------
with st.sidebar.expander("Instrucciones"):
    st.markdown("""
    ### Como usar:
    1. **Nodo N0**: Usa N0 como tierra
    2. **Agrega componentes**: Completa todos los campos
    3. **Mostrar Grafo**: Visualiza polaridad y direcciones
    4. **Generar Ecuaciones**: Obtiene analisis completo (KCL, LVK, BR, ecuacion diferencial)
    5. **MATLAB**: Descarga codigo optimizado
    
    ### Ejemplo Circuito RC:
    | Nombre | Tipo | Origen | Destino | Valor |
    |--------|------|--------|---------|-------|
    | V1 | Fuente Voltaje | N0 | N1 | 9 |
    | R1 | Resistencia | N1 | N2 | 27k |
    | C1 | Capacitor | N2 | N0 | 100u |
    
    ### Mejoras incluidas:
    - ✅ LVK explicito
    - ✅ Variable de estado definida
    - ✅ Ecuacion diferencial en forma estandar
    - ✅ Interpretacion fisica
    - ✅ Analisis nodal con supernodo
    """)
