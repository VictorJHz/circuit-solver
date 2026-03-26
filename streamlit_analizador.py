import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
from sympy import symbols, Eq, Derivative, latex, Function, solve, dsolve, Matrix, zeros
import numpy as np

# ---------- CONFIGURACIÓN DE INTERFAZ ----------
st.set_page_config(page_title="Circuit Solver", layout="wide")
st.title("⚡ Circuit Solver")
st.caption("Análisis de circuitos eléctricos con generación correcta de ecuaciones")

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
        valor_text = st.text_input("Valor (solo número)")
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
            st.success(f"✅ Componente {input_nombre} agregado correctamente")
        except ValueError:
            st.error("El valor debe ser un número")

# ---------- MOSTRAR COMPONENTES ----------
st.subheader("📋 Componentes agregados")
if st.session_state.componentes:
    for i, c in enumerate(st.session_state.componentes):
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"**{c['nombre']}**: {c['tipo']} ({c['tipo_elec']}) | Valor: {c['valor']}{c['prefijo']}{c['unidad']} | Nodos: {c['nodo_origen']} → {c['nodo_destino']}")
        with col2:
            if st.button(f"🗑️", key=f"del_{i}"):
                st.session_state.componentes.pop(i)
                st.rerun()
else:
    st.info("No hay componentes agregados todavía. Agrega componentes en la barra lateral.")

# ---------- FUNCIONES PARA GENERAR ECUACIONES ----------
def obtener_nodos_unicos(componentes):
    nodos = set()
    for c in componentes:
        nodos.add(c['nodo_origen'])
        nodos.add(c['nodo_destino'])
    return sorted(list(nodos))

def generar_ecuaciones_kcl(componentes, nodos, i_componentes):
    ecuaciones_kcl = []
    for nodo in nodos:
        if nodo == "N0":
            continue
        suma_corrientes = 0
        for c in componentes:
            if c['nodo_origen'] == nodo:
                suma_corrientes += i_componentes[c['nombre']]
            elif c['nodo_destino'] == nodo:
                suma_corrientes -= i_componentes[c['nombre']]
        if suma_corrientes != 0:
            ecuacion = Eq(suma_corrientes, 0)
            ecuaciones_kcl.append((nodo, ecuacion))
    return ecuaciones_kcl

def generar_ecuaciones_componentes(componentes, v_nodos, i_componentes, t):
    ecuaciones_br = []
    for c in componentes:
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
            ecuacion = Eq(v_diff, valor_total * i_componentes[nombre])
            ecuaciones_br.append((nombre, ecuacion, "Ley de Ohm"))
        elif tipo == "Capacitor":
            ecuacion = Eq(i_componentes[nombre], valor_total * Derivative(v_diff, t))
            ecuaciones_br.append((nombre, ecuacion, "Relación Capacitor: i = C·dv/dt"))
        elif tipo == "Inductor":
            ecuacion = Eq(v_diff, valor_total * Derivative(i_componentes[nombre], t))
            ecuaciones_br.append((nombre, ecuacion, "Relación Inductor: v = L·di/dt"))
        elif tipo == "Fuente de Voltaje":
            if nodo_o == "N0":
                ecuacion = Eq(v_d - v_o, valor_total)
            elif nodo_d == "N0":
                ecuacion = Eq(v_o - v_d, valor_total)
            else:
                ecuacion = Eq(v_diff, valor_total)
            ecuaciones_br.append((nombre, ecuacion, "Fuente de Voltaje"))
        elif tipo == "Fuente de Corriente":
            ecuacion = Eq(i_componentes[nombre], valor_total)
            ecuaciones_br.append((nombre, ecuacion, "Fuente de Corriente"))
    return ecuaciones_br

def validar_circuito(componentes):
    errores = []
    warnings = []
    hay_tierra = False
    for c in componentes:
        if c['nodo_origen'] == "N0" or c['nodo_destino'] == "N0":
            hay_tierra = True
            break
    if not hay_tierra:
        errores.append("❌ No hay nodo de referencia (N0). Agrega un componente conectado a tierra.")
    nombres = [c['nombre'] for c in componentes]
    if len(nombres) != len(set(nombres)):
        errores.append("❌ Hay nombres de componentes duplicados.")
    for c in componentes:
        if c['valor'] <= 0:
            warnings.append(f"⚠️ {c['nombre']} tiene valor {c['valor']}{c['prefijo']}{c['unidad']} (no positivo)")
    return errores, warnings

def analisis_nodal_basico(componentes, nodos):
    try:
        nodos_no_tierra = [n for n in nodos if n != "N0"]
        n = len(nodos_no_tierra)
        if n == 0:
            return None, None, None, "No hay nodos para análisis nodal"
        nodo_idx = {nodo: i for i, nodo in enumerate(nodos_no_tierra)}
        G = zeros(n, n)
        I = zeros(n, 1)
        for c in componentes:
            if c['tipo'] == "Resistencia":
                G_val = 1 / c['valor_total']
                nodo_o = c['nodo_origen']
                nodo_d = c['nodo_destino']
                if nodo_o != "N0" and nodo_d != "N0":
                    i = nodo_idx[nodo_o]
                    j = nodo_idx[nodo_d]
                    G[i, i] += G_val
                    G[j, j] += G_val
                    G[i, j] -= G_val
                    G[j, i] -= G_val
                elif nodo_o != "N0":
                    i = nodo_idx[nodo_o]
                    G[i, i] += G_val
                elif nodo_d != "N0":
                    i = nodo_idx[nodo_d]
                    G[i, i] += G_val
            elif c['tipo'] == "Fuente de Corriente":
                I_val = c['valor_total']
                nodo_o = c['nodo_origen']
                nodo_d = c['nodo_destino']
                if nodo_o != "N0":
                    i = nodo_idx[nodo_o]
                    I[i, 0] += I_val
                if nodo_d != "N0":
                    i = nodo_idx[nodo_d]
                    I[i, 0] -= I_val
        fuentes_v = [c for c in componentes if c['tipo'] == "Fuente de Voltaje"]
        mensaje = None
        if fuentes_v:
            mensaje = "⚠️ El circuito contiene fuentes de voltaje. El análisis nodal básico requiere supernodo."
        return G, I, nodos_no_tierra, mensaje
    except Exception as e:
        return None, None, None, str(e)

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
            label = f"{c['nombre']}\n{tipo_label}={valor_str}\n(+) → (-)"
        else:
            label = f"{c['nombre']}\n{tipo_label}={valor_str}\n↓ i"
        G.add_edge(c['nodo_origen'], c['nodo_destino'], 
                   label=label, tipo=c['tipo'], color=color, linewidth=linewidth)
    return G, nodos

# ---------- BOTONES PRINCIPALES ----------
st.subheader("🎯 Acciones")
col1, col2, col3, col4 = st.columns(4)

# ----- Mostrar Grafo -----
with col1:
    if st.button("📊 Mostrar Grafo"):
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
            plt.title("Grafo del Circuito - Polaridad y Dirección de Corriente", fontsize=14, fontweight='bold')
            plt.axis('off')
            legend_elements = [
                plt.Line2D([0], [0], color='red', linewidth=2, label='Resistencia (Pasivo)'),
                plt.Line2D([0], [0], color='blue', linewidth=2, label='Capacitor (Pasivo)'),
                plt.Line2D([0], [0], color='green', linewidth=2, label='Inductor (Pasivo)'),
                plt.Line2D([0], [0], color='orange', linewidth=2.5, label='Fuente Voltaje (Activo: + → -)'),
                plt.Line2D([0], [0], color='purple', linewidth=2.5, label='Fuente Corriente (Activo: + → -)')
            ]
            ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
            plt.figtext(0.02, 0.02, "Activos: flecha del positivo (+) al negativo (-) | Pasivos: dirección convencional de corriente", fontsize=10, style='italic')
            st.pyplot(fig)

# ----- Generar Sistema de Ecuaciones -----
with col2:
    if st.button("🔧 Generar Ecuaciones"):
        if not st.session_state.componentes:
            st.warning("Agrega componentes primero")
        else:
            t = symbols('t')
            nodos = obtener_nodos_unicos(st.session_state.componentes)
            v_nodos = {}
            for nodo in nodos:
                if nodo != "N0":
                    v_nodos[nodo] = Function(f'V_{nodo}')(t)
            i_componentes = {}
            for c in st.session_state.componentes:
                if c['needs_current'] or c['tipo'] == "Fuente de Corriente":
                    i_componentes[c['nombre']] = Function(f'i_{c["nombre"]}')(t)
            ecuaciones_kcl = generar_ecuaciones_kcl(st.session_state.componentes, nodos, i_componentes)
            ecuaciones_br = generar_ecuaciones_componentes(st.session_state.componentes, v_nodos, i_componentes, t)
            st.subheader("📐 Ecuaciones del Circuito")
            if ecuaciones_kcl:
                st.write("**1. Ley de Corrientes de Kirchhoff (KCL)**")
                for nodo, eq in ecuaciones_kcl:
                    st.latex(latex(eq))
                    st.caption(f"KCL en nodo {nodo}")
            if ecuaciones_br:
                st.write("**2. Relaciones de los Componentes (BR)**")
                for nombre, eq, desc in ecuaciones_br:
                    st.latex(latex(eq))
                    st.caption(f"{desc} - {nombre}")
            total_ecuaciones = len(ecuaciones_kcl) + len(ecuaciones_br)
            total_variables = len(v_nodos) + len(i_componentes)
            st.subheader("📊 Resumen")
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Total Ecuaciones", total_ecuaciones)
            with col_b:
                st.metric("Total Variables", total_variables)
            if total_ecuaciones == total_variables:
                st.success("✅ Sistema bien definido")
            else:
                st.warning(f"⚠️ Desbalance: {total_ecuaciones} eq vs {total_variables} var")

# ----- Generar Código MATLAB -----
with col3:
    if st.button("📄 Código MATLAB"):
        if not st.session_state.componentes:
            st.warning("Agrega componentes primero")
        else:
            R_val = None
            C_val = None
            Vin_val = None
            for c in st.session_state.componentes:
                if c['tipo'] == "Resistencia":
                    R_val = c['valor_total']
                elif c['tipo'] == "Capacitor":
                    C_val = c['valor_total']
                elif c['tipo'] == "Fuente de Voltaje":
                    Vin_val = c['valor_total']
            if R_val is not None and C_val is not None and Vin_val is not None:
                matlab_code = f"""%% Circuito RC
clear; clc; close all;
syms V(t)
R = {R_val:.10f};
C = {C_val:.10f};
Vin = {Vin_val:.10f};
eq = Vin - V == R * C * diff(V, t);
cond = V(0) == 0;
V_sol = dsolve(eq, cond);
disp('Solucion:');
pretty(V_sol)
tau = R * C;
fprintf('tau = %.4f s\\n', tau);
figure;
fplot(V_sol, [0 5*tau], 'LineWidth', 2);
xlabel('t (s)'); ylabel('V(t) (V)');
title('Respuesta Circuito RC');
grid on;
"""
            else:
                matlab_code = "%% Circuito\nclear; clc;\n% Agregar ecuaciones manualmente\n"
            st.subheader("📄 Código MATLAB")
            st.code(matlab_code, language="matlab")
            st.download_button("💾 Descargar", data=matlab_code, file_name="circuito.m")

# ----- Limpiar Circuito -----
with col4:
    if st.button("🗑️ Limpiar Todo"):
        st.session_state.componentes = []
        st.rerun()

# ========== ANALISIS AVANZADO ==========
st.divider()
st.subheader("📚 Análisis Avanzado")

col5, col6, col7 = st.columns(3)

# ----- Validación -----
with col5:
    with st.expander("🔍 Validar Circuito", expanded=False):
        if st.button("Ejecutar Validación", key="validar"):
            if not st.session_state.componentes:
                st.warning("Agrega componentes")
            else:
                errores, warnings = validar_circuito(st.session_state.componentes)
                if errores:
                    for err in errores:
                        st.error(err)
                else:
                    st.success("✅ Sin errores críticos")
                for warn in warnings:
                    st.warning(warn)

# ----- Sistema Completo (KCL + BR) -----
with col6:
    with st.expander("📊 Sistema Completo (KCL + BR)", expanded=False):
        if st.button("Generar Sistema Completo", key="sistema"):
            if not st.session_state.componentes:
                st.warning("Agrega componentes")
            else:
                t = symbols('t')
                nodos = obtener_nodos_unicos(st.session_state.componentes)
                v_nodos = {}
                for nodo in nodos:
                    if nodo != "N0":
                        v_nodos[nodo] = Function(f'V_{nodo}')(t)
                i_componentes = {}
                for c in st.session_state.componentes:
                    if c['needs_current'] or c['tipo'] == "Fuente de Corriente":
                        i_componentes[c['nombre']] = Function(f'i_{c["nombre"]}')(t)
                
                ecuaciones_kcl = generar_ecuaciones_kcl(st.session_state.componentes, nodos, i_componentes)
                ecuaciones_br = generar_ecuaciones_componentes(st.session_state.componentes, v_nodos, i_componentes, t)
                
                st.write("### 📌 Sistema de Ecuaciones")
                st.write("")
                st.write("**KCL - Ley de Corrientes de Kirchhoff**")
                for nodo, eq in ecuaciones_kcl:
                    st.latex(latex(eq))
                st.write("")
                st.write("**BR - Relaciones de Componentes**")
                for nombre, eq, desc in ecuaciones_br:
                    st.latex(latex(eq))
                st.write("")
                total_eq = len(ecuaciones_kcl) + len(ecuaciones_br)
                total_var = len(v_nodos) + len(i_componentes)
                st.info(f"Total ecuaciones: {total_eq} | Total variables: {total_var}")
                if total_eq == total_var:
                    st.success("✅ Sistema cuadrado y bien definido")

# ----- Análisis Nodal -----
with col7:
    with st.expander("🔢 Análisis Nodal (Matriz G)", expanded=False):
        if st.button("Ejecutar Análisis Nodal", key="nodal2"):
            if not st.session_state.componentes:
                st.warning("Agrega componentes")
            else:
                nodos = obtener_nodos_unicos(st.session_state.componentes)
                G, I, nodos_nt, msg = analisis_nodal_basico(st.session_state.componentes, nodos)
                if msg:
                    st.warning(msg)
                if G is not None:
                    st.write("**Matriz de Conductancias G:**")
                    st.latex(latex(G))
                    st.write("**Vector de Corrientes I:**")
                    st.latex(latex(I))
                    st.write("**Sistema G·V = I:**")
                    st.write("")
                    for i, nodo in enumerate(nodos_nt):
                        ecuacion = ""
                        for j in range(len(nodos_nt)):
                            val = float(G[i, j])
                            if val != 0:
                                if val > 0 and ecuacion:
                                    ecuacion += f" + {val:.3e}·V_{nodos_nt[j]}"
                                elif val < 0:
                                    ecuacion += f" - {abs(val):.3e}·V_{nodos_nt[j]}"
                                elif not ecuacion:
                                    ecuacion += f"{val:.3e}·V_{nodos_nt[j]}"
                        if float(I[i, 0]) >= 0:
                            ecuacion += f" = {float(I[i, 0]):.3e}"
                        else:
                            ecuacion += f" = {float(I[i, 0]):.3e}"
                        st.latex(ecuacion)
                    try:
                        if G.det() != 0:
                            V_sol = G.inv() * I
                            st.write("**Solución (voltajes de nodo):**")
                            for i, nodo in enumerate(nodos_nt):
                                st.latex(f"V_{{{nodo}}} = {latex(V_sol[i, 0])}")
                        else:
                            st.warning("Matriz singular - se requiere supernodo para fuentes de voltaje")
                    except:
                        st.warning("No se pudo resolver el sistema")

# ---------- INFORMACION ADICIONAL ----------
with st.sidebar.expander("ℹ️ Instrucciones"):
    st.markdown("""
    ### Cómo usar:
    1. **Nodo N0**: Usa N0 como tierra
    2. **Agrega componentes**: Completa todos los campos
    3. **Mostrar Grafo**: Visualiza polaridad y direcciones
    4. **Generar Ecuaciones**: Obtiene KCL y BR
    5. **MATLAB**: Descarga código para resolver
    
    ### Ejemplo Circuito RC:
    | Nombre | Tipo | Origen | Destino | Valor |
    |--------|------|--------|---------|-------|
    | V1 | Fuente Voltaje | N0 | N1 | 9 |
    | R1 | Resistencia | N1 | N2 | 27k |
    | C1 | Capacitor | N2 | N0 | 100μ |
    
    ### Polaridad en el Grafo:
    - **Activos** (Fuentes): (+) → (-)
    - **Pasivos**: Dirección convencional de corriente
    """)