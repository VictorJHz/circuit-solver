import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
from sympy import symbols, Eq, Derivative, latex, Function, solve, dsolve, Matrix, zeros
import numpy as np
import re

# ---------- CONFIGURACIÓN ----------
st.set_page_config(page_title="Circuit Solver", layout="wide")
st.title("⚡ Circuit Solver")
st.caption("Analisis de circuitos electricos - Metodo de Tablueau")

# ---------- SESSION STATE ----------
if 'componentes' not in st.session_state:
    st.session_state.componentes = []

# ---------- COMPONENTES ----------
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
    nombre = st.text_input("Nombre del componente (ej: R1, C1, V1, I1)")
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
    if not nombre or not valor_text or not nodo_origen or not nodo_destino:
        st.warning("Por favor, llena todos los campos")
    else:
        try:
            float(valor_text)
            componente = {
                "nombre": nombre,
                "tipo": tipo_componente,
                "tipo_corto": componentes_disponibles[tipo_componente]["tipo"],
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
            st.success(f"✅ Componente {nombre} agregado correctamente")
        except ValueError:
            st.error("El valor debe ser un número")

# ---------- MOSTRAR COMPONENTES ----------
st.subheader("📋 Componentes agregados")
if st.session_state.componentes:
    for i, c in enumerate(st.session_state.componentes):
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"**{c['nombre']}**: {c['tipo']} | Valor: {c['valor']}{c['prefijo']}{c['unidad']} | Nodos: {c['nodo_origen']} → {c['nodo_destino']}")
        with col2:
            if st.button(f"🗑️", key=f"del_{i}"):
                st.session_state.componentes.pop(i)
                st.rerun()
else:
    st.info("No hay componentes agregados todavía. Agrega componentes en la barra lateral.")

# ---------- FUNCIONES ----------
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

def analizar_rc(componentes):
    R = C = Vin = None
    for c in componentes:
        if c['tipo'] == "Resistencia":
            R = c['valor_total']
        elif c['tipo'] == "Capacitor":
            C = c['valor_total']
        elif c['tipo'] == "Fuente de Voltaje":
            Vin = c['valor_total']
    return (R, C, Vin) if None not in (R, C, Vin) else (None, None, None)

def dibujar_grafo(componentes):
    G = nx.MultiDiGraph()
    nodos = obtener_nodos_unicos(componentes)
    for nodo in nodos:
        G.add_node(nodo)
    for c in componentes:
        color = {"Resistencia":"red", "Capacitor":"blue", "Inductor":"green", "Fuente de Voltaje":"orange", "Fuente de Corriente":"purple"}.get(c['tipo'], "gray")
        tipo_label = {"Resistencia":"R", "Capacitor":"C", "Inductor":"L", "Fuente de Voltaje":"V", "Fuente de Corriente":"I"}.get(c['tipo'], "")
        val = f"{c['valor']}{c['prefijo']}{c['unidad']}"
        if c['tipo_elec'] == "Activo":
            label = f"{c['nombre']}\n{tipo_label}={val}\n(+) -> (-)"
        else:
            label = f"{c['nombre']}\n{tipo_label}={val}\ni ->"
        G.add_edge(c['nodo_origen'], c['nodo_destino'], label=label, color=color)
    return G

# ---------- BOTONES PRINCIPALES ----------
st.subheader("🎯 Acciones")
col1, col2, col3, col4 = st.columns(4)

# ----- Mostrar Grafo -----
with col1:
    if st.button("📊 Mostrar Grafo"):
        if not st.session_state.componentes:
            st.warning("Agrega al menos un componente")
        else:
            G = dibujar_grafo(st.session_state.componentes)
            fig, ax = plt.subplots(figsize=(12,8))
            pos = nx.spring_layout(G, seed=42, k=2)
            nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=2500, ax=ax)
            nx.draw_networkx_labels(G, pos, font_size=12, ax=ax)
            colors = [d['color'] for u,v,d in G.edges(data=True)]
            nx.draw_networkx_edges(G, pos, edge_color=colors, arrows=True, arrowsize=20, ax=ax)
            labels = {(u,v): d['label'] for u,v,d in G.edges(data=True)}
            nx.draw_networkx_edge_labels(G, pos, edge_labels=labels, font_size=9, ax=ax)
            plt.axis('off')
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
            
            st.subheader("📊 Resumen del Sistema")
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Total Ecuaciones", total_ecuaciones)
                st.write(f"- KCL: {len(ecuaciones_kcl)}")
                st.write(f"- BR: {len(ecuaciones_br)}")
            with col_b:
                st.metric("Total Variables", total_variables)
                st.write(f"- Voltajes de nodo: {len(v_nodos)}")
                st.write(f"- Corrientes: {len(i_componentes)}")
            
            if total_ecuaciones == total_variables:
                st.success("✅ Sistema bien definido (ecuaciones = variables)")
            else:
                st.warning(f"⚠️ Desbalance: {total_ecuaciones} eq vs {total_variables} var")

# ----- Generar Código MATLAB -----
with col3:
    if st.button("📄 Código MATLAB"):
        if not st.session_state.componentes:
            st.warning("Agrega componentes primero")
        else:
            R, C, Vin = analizar_rc(st.session_state.componentes)
            
            if R is not None and C is not None and Vin is not None:
                tau = R * C
                code = f"""%% Circuito RC - Solución Automática
clear; clc; close all;

R = {R:.10f};
C = {C:.10f};
Vin = {Vin:.10f};
tau = R * C;

syms Vc(t)
eq = diff(Vc, t) == -1/tau * Vc + Vin/tau;
cond = Vc(0) == 0;
Vc_sol = dsolve(eq, cond);

disp('=== SOLUCIÓN DEL CIRCUITO RC ===');
pretty(Vc_sol);
fprintf('Vc(t) = %.2f * (1 - exp(-t/%.4f))\\n', Vin, tau);

figure;
fplot(Vc_sol, [0 5*tau], 'LineWidth', 2);
xlabel('t (s)'); ylabel('Vc(t) (V)');
title('Respuesta del Circuito RC');
grid on;
hold on;
plot([0 5*tau], [Vin Vin], '--r');
legend('Vc(t)', 'Vin');
"""
                st.code(code, language="matlab")
                st.download_button("Descargar", code, "circuito_rc.m", key="descargar_matlab")
            else:
                st.info("Circuito no RC simple")

# ----- Limpiar Circuito -----
with col4:
    if st.button("🗑️ Limpiar Todo"):
        st.session_state.componentes = []
        st.rerun()

# ---------- INFORMACIÓN ADICIONAL ----------
with st.sidebar.expander("ℹ️ Instrucciones"):
    st.markdown("""
    ### Cómo usar:
    1. **Nodo N0**: Usa N0 como tierra
    2. **Agrega componentes**: Completa todos los campos
    3. **Genera ecuaciones**: Obtiene KCL y BR
    4. **MATLAB**: Descarga código para resolver
    
    ### Ejemplo Circuito RC:
    | Nombre | Tipo | Origen | Destino | Valor |
    |--------|------|--------|---------|-------|
    | V1 | Fuente Voltaje | N0 | N1 | 9 |
    | R1 | Resistencia | N1 | N2 | 27k |
    | C1 | Capacitor | N2 | N0 | 100μ |
    """)
