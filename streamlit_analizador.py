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

# ---------- FUNCIONES NETLIST ----------
def parse_valor(valor_str):
    """Parsea valores como 9, 27k, 100u, 2.2M"""
    if not valor_str:
        return None, None
    valor_str = valor_str.strip().lower()
    # Eliminar palabras como dc, ac pero mantener prefijos
    # Primero extraer el numero con posible prefijo
    match = re.match(r'^([\d\.]+)([pnumkM]?)(.*)$', valor_str)
    if match:
        num_str, pref, resto = match.groups()
        try:
            num = float(num_str)
        except:
            return None, None
        if pref == 'p':
            return num * 1e-12, pref
        elif pref == 'n':
            return num * 1e-9, pref
        elif pref == 'u':
            return num * 1e-6, pref
        elif pref == 'm':
            return num * 1e-3, pref
        elif pref == 'k':
            return num * 1e3, pref
        elif pref == 'M':
            return num * 1e6, pref
        return num, ''
    return None, None

def parsear_netlist(texto):
    componentes = []
    errores = []
    
    tipo_por_letra = {
        'V': 'Fuente de Voltaje',
        'I': 'Fuente de Corriente',
        'R': 'Resistencia',
        'C': 'Capacitor',
        'L': 'Inductor'
    }
    
    for line_num, line in enumerate(texto.strip().split('\n'), 1):
        line = line.strip()
        if not line or line.startswith('#') or line.startswith(';'):
            continue
        
        # Eliminar comentarios
        if '#' in line:
            line = line.split('#')[0].strip()
        if ';' in line:
            line = line.split(';')[0].strip()
        
        if not line:
            continue
            
        parts = line.split()
        if len(parts) < 4:
            errores.append(f"Linea {line_num}: Formato incorrecto (minimo 4 campos)")
            continue
        
        # El primer campo es el nombre del componente (V1, R1, C1)
        nombre = parts[0]
        letra = nombre[0].upper()
        
        if letra not in tipo_por_letra:
            errores.append(f"Linea {line_num}: Tipo '{letra}' no reconocido (use V, R, C, L, I)")
            continue
        
        tipo = tipo_por_letra[letra]
        
        # Nodos
        nodo_origen = parts[1]
        nodo_destino = parts[2]
        
        # Buscar el valor (puede estar en pos 3 o 4 si hay DC/AC)
        valor_str = None
        for i in range(3, len(parts)):
            # Buscar algo que parezca un numero (con o sin prefijo)
            if re.search(r'[\d\.]', parts[i]):
                valor_str = parts[i]
                break
        
        if not valor_str:
            errores.append(f"Linea {line_num}: No se encontro valor")
            continue
        
        # Parsear valor
        valor_total, prefijo = parse_valor(valor_str)
        if valor_total is None:
            errores.append(f"Linea {line_num}: Valor '{valor_str}' no valido")
            continue
        
        # Obtener el valor base para mostrar
        mult = prefijos.get(prefijo, 1)
        valor_base = valor_total / mult if mult != 1 else valor_total
        
        componentes.append({
            "nombre": nombre,
            "tipo": tipo,
            "tipo_corto": componentes_disponibles[tipo]["tipo"],
            "tipo_elec": componentes_disponibles[tipo]["tipo_elec"],
            "unidad": componentes_disponibles[tipo]["unidad"],
            "valor": valor_base,
            "prefijo": prefijo,
            "multiplo": mult,
            "valor_total": valor_total,
            "nodo_origen": nodo_origen,
            "nodo_destino": nodo_destino,
            "needs_current": componentes_disponibles[tipo]["needs_current"]
        })
    
    return componentes, errores

# ---------- FORMULARIO INDIVIDUAL ----------
st.sidebar.header("Agregar Componente")
with st.sidebar.form(key='form_componente', clear_on_submit=True):
    nombre = st.text_input("Nombre (R1, C1, V1)")
    n_origen = st.text_input("Nodo origen (N0, N1...)")
    n_destino = st.text_input("Nodo destino (N0, N1...)")
    tipo = st.selectbox("Tipo", list(componentes_disponibles.keys()))
    col_val, col_pref = st.columns([3,1])
    with col_val:
        valor = st.text_input("Valor (numero)")
    with col_pref:
        pref = st.selectbox("Prefijo", list(prefijos.keys()), index=0)
    submit = st.form_submit_button("Agregar")

if submit:
    if not nombre or not valor or not n_origen or not n_destino:
        st.sidebar.warning("Llena todos los campos")
    else:
        try:
            v = float(valor)
            st.session_state.componentes.append({
                "nombre": nombre, "tipo": tipo, "tipo_corto": componentes_disponibles[tipo]["tipo"],
                "tipo_elec": componentes_disponibles[tipo]["tipo_elec"],
                "unidad": componentes_disponibles[tipo]["unidad"], "valor": v, "prefijo": pref,
                "multiplo": prefijos[pref], "valor_total": v * prefijos[pref],
                "nodo_origen": n_origen, "nodo_destino": n_destino,
                "needs_current": componentes_disponibles[tipo]["needs_current"]
            })
            st.sidebar.success(f"Agregado {nombre}")
            st.rerun()
        except ValueError:
            st.sidebar.error("El valor debe ser un numero")

# ---------- NETLIST ----------
st.sidebar.divider()
st.sidebar.header("Netlist")
with st.sidebar.expander("Cargar desde Netlist", expanded=False):
    st.markdown("**Formato:** V1 N0 N1 9   o   R1 N1 N2 27k")
    netlist = st.text_area("Pega el netlist:", height=120, 
                          placeholder="V1 N0 N1 9\nR1 N1 N2 27k\nC1 N2 N0 100u")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Cargar Netlist", key="cargar_netlist", use_container_width=True):
            if netlist.strip():
                nuevos, errores = parsear_netlist(netlist)
                if errores:
                    for err in errores:
                        st.sidebar.error(err)
                if nuevos:
                    for c in nuevos:
                        if c['nombre'] not in [x['nombre'] for x in st.session_state.componentes]:
                            st.session_state.componentes.append(c)
                            st.sidebar.success(f"Agregado {c['nombre']} ({c['tipo']})")
                    st.rerun()
                elif not errores:
                    st.sidebar.warning("No se encontraron componentes")
            else:
                st.sidebar.warning("Netlist vacio")
    
    with col2:
        if st.button("Ejemplo RC", key="ejemplo_rc", use_container_width=True):
            ejemplo = "V1 N0 N1 9\nR1 N1 N2 27k\nC1 N2 N0 100u"
            nuevos, errores = parsear_netlist(ejemplo)
            for c in nuevos:
                if c['nombre'] not in [x['nombre'] for x in st.session_state.componentes]:
                    st.session_state.componentes.append(c)
            st.rerun()

# ---------- MOSTRAR COMPONENTES ----------
st.subheader("Componentes")
if st.session_state.componentes:
    col_clear1, col_clear2 = st.columns([4, 1])
    with col_clear2:
        if st.button("Limpiar Todos", key="clear_all"):
            st.session_state.componentes = []
            st.rerun()
    
    for i, c in enumerate(st.session_state.componentes):
        col1, col2 = st.columns([4,1])
        with col1:
            st.write(f"**{c['nombre']}**: {c['tipo']} | {c['valor']}{c['prefijo']}{c['unidad']} | {c['nodo_origen']} -> {c['nodo_destino']}")
        with col2:
            if st.button("X", key=f"del_{i}"):
                st.session_state.componentes.pop(i)
                st.rerun()
else:
    st.info("Sin componentes. Agrega individualmente o con netlist.")

# ---------- FUNCIONES DE ANALISIS ----------
def obtener_nodos(cs):
    nodos = set()
    for c in cs:
        nodos.add(c['nodo_origen'])
        nodos.add(c['nodo_destino'])
    return sorted(list(nodos))

def analizar_rc(cs):
    R = C = Vin = None
    for c in cs:
        if c['tipo'] == "Resistencia":
            R = c['valor_total']
        elif c['tipo'] == "Capacitor":
            C = c['valor_total']
        elif c['tipo'] == "Fuente de Voltaje":
            Vin = c['valor_total']
    return (R, C, Vin) if None not in (R, C, Vin) else (None, None, None)

def dibujar_grafo(cs):
    G = nx.MultiDiGraph()
    for n in obtener_nodos(cs):
        G.add_node(n)
    for c in cs:
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
st.subheader("Acciones")
b1, b2, b3, b4 = st.columns(4)

with b1:
    if st.button("Mostrar Grafo", key="mostrar_grafo"):
        if not st.session_state.componentes:
            st.warning("Agrega componentes")
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

with b2:
    if st.button("Generar Ecuaciones", key="generar_eq"):
        if not st.session_state.componentes:
            st.warning("Agrega componentes")
        else:
            R, C, Vin = analizar_rc(st.session_state.componentes)
            if R is not None and C is not None and Vin is not None:
                tau = R * C
                st.subheader("Analisis Completo del Circuito RC")
                
                st.write("**1. Matriz de Incidencia A**")
                st.latex(r"A = \begin{bmatrix} 1 & -1 & 0 \\ 0 & 1 & -1 \end{bmatrix}")
                
                st.write("**2. Vector e (Potenciales nodales)**")
                st.latex(r"e = \begin{bmatrix} V_{N1} \\ V_{N2} \end{bmatrix}")
                
                st.write("**3. KCL en forma matricial**")
                st.latex(r"A \cdot i = 0")
                st.latex(r"\begin{bmatrix} 1 & -1 & 0 \\ 0 & 1 & -1 \end{bmatrix} \begin{bmatrix} i_{V1} \\ i_{R1} \\ i_{C1} \end{bmatrix} = \begin{bmatrix} 0 \\ 0 \end{bmatrix}")
                
                st.write("**4. KVL en forma matricial**")
                st.latex(r"v = A^T \cdot e")
                st.latex(r"\begin{bmatrix} v_{V1} \\ v_{R1} \\ v_{C1} \end{bmatrix} = \begin{bmatrix} 1 & 0 \\ -1 & 1 \\ 0 & -1 \end{bmatrix} \begin{bmatrix} V_{N1} \\ V_{N2} \end{bmatrix}")
                
                st.write("**5. Relaciones de los Componentes (BR)**")
                st.latex(r"v_{V1} = V_{in} = " + f"{Vin:.1f}" + r"\ V")
                st.latex(r"v_{R1} = R \cdot i_{R1} = " + f"{R:.0f}" + r"\ \Omega \cdot i_{R1}")
                st.latex(r"i_{C1} = C \cdot \frac{d v_{C1}}{dt} = " + f"{C:.0e}" + r"\ F \cdot \frac{d v_{C1}}{dt}")
                
                st.write("**6. Ecuacion Diferencial**")
                st.latex(rf"{Vin:.1f} - V_C = {R:.0f} \cdot {C:.0e} \cdot \frac{{dV_C}}{{dt}}")
                st.latex(rf"\frac{{dV_C}}{{dt}} + \frac{{1}}{{{tau:.4f}}} V_C = \frac{{{Vin:.1f}}}{{{tau:.4f}}}")
                
                st.write("**7. Variable de Estado**")
                st.latex(r"x(t) = V_C(t)")
                
                st.write("**8. Ecuacion de Estado**")
                st.latex(rf"\dot{{x}} = -\frac{{1}}{{{tau:.4f}}} x + \frac{{{Vin:.1f}}}{{{tau:.4f}}}")
                
                st.write("**9. Solucion Analitica**")
                st.latex(rf"V_C(t) = {Vin:.1f} \cdot (1 - e^{{-t/{tau:.4f}}})")
            else:
                st.info("Circuito no RC simple. Agrega una Resistencia, un Capacitor y una Fuente de Voltaje para ver el analisis completo.")

with b3:
    if st.button("Codigo MATLAB", key="matlab"):
        R, C, Vin = analizar_rc(st.session_state.componentes)
        if R is not None and C is not None and Vin is not None:
            tau = R * C
            code = f"""% Circuito RC - Analisis Completo
clear; clc; close all;

% Parametros
R = {R:.6f};  % Ohm
C = {C:.6f};  % Faradios
Vin = {Vin:.6f};  % Voltios
tau = R * C;  % Constante de tiempo

% Variable de estado
syms Vc(t)
eq = diff(Vc, t) == -1/tau * Vc + Vin/tau;
cond = Vc(0) == 0;
Vc_sol = dsolve(eq, cond);

% Resultados
disp('=== SOLUCION DEL CIRCUITO RC ===');
fprintf('Vc(t) = %.2f * (1 - exp(-t/%.4f))\\n', Vin, tau);
pretty(Vc_sol);

% Grafica
figure;
fplot(Vc_sol, [0 5*tau], 'LineWidth', 2);
xlabel('t (s)'); ylabel('Vc(t) (V)');
title('Respuesta del Circuito RC');
grid on;
hold on;
plot([0 5*tau], [Vin Vin], '--r');
legend('Vc(t)', 'Vin', 'Location', 'best');
"""
            st.code(code, language="matlab")
            st.download_button("Descargar", code, "circuito_rc.m", key="descargar_matlab")
        else:
            st.info("Agrega una Resistencia, un Capacitor y una Fuente de Voltaje para generar el codigo MATLAB.")

with b4:
    if st.button("Limpiar Todo", key="limpiar_todo"):
        st.session_state.componentes = []
        st.rerun()
