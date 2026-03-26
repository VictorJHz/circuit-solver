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
prefijos_regex = {"p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6, "m": 1e-3, "k": 1e3, "M": 1e6}

# ---------- FUNCIONES NETLIST ----------
def parse_valor(valor_str):
    if not valor_str:
        return None
    valor_str = valor_str.strip().lower()
    # Eliminar palabras como DC, AC, etc
    valor_str = re.sub(r'[a-z]+', '', valor_str)
    match = re.match(r'^([\d\.]+)([pnumkM]?)$', valor_str)
    if match:
        num, pref = match.groups()
        try:
            num = float(num)
        except:
            return None
        if pref == 'p':
            return num * 1e-12
        elif pref == 'n':
            return num * 1e-9
        elif pref == 'u':
            return num * 1e-6
        elif pref == 'm':
            return num * 1e-3
        elif pref == 'k':
            return num * 1e3
        elif pref == 'M':
            return num * 1e6
        return num
    return None

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
        
        # Eliminar comentarios en linea
        if '#' in line:
            line = line.split('#')[0].strip()
        if ';' in line:
            line = line.split(';')[0].strip()
        
        if not line:
            continue
            
        parts = line.split()
        if len(parts) < 4:
            errores.append(f"Linea {line_num}: Formato incorrecto (se necesitan al menos 4 campos)")
            continue
        
        # El primer campo puede ser "V1" o "V"
        primero = parts[0]
        
        # Detectar el tipo y nombre
        if primero[0] in tipo_por_letra:
            letra = primero[0]
            nombre = primero[1:] if len(primero) > 1 else primero
            tipo = tipo_por_letra[letra]
            # Si el nombre esta vacio, usar el primer campo como nombre
            if not nombre:
                nombre = primero
            
            # Los siguientes campos son nodos y valor
            nodo_origen = parts[1] if len(parts) > 1 else None
            nodo_destino = parts[2] if len(parts) > 2 else None
            
            # El valor puede estar en la posicion 3, pero puede haber palabras como DC
            valor_str = None
            for i in range(3, len(parts)):
                # Buscar un valor numerico o con prefijo
                if re.search(r'[\d\.]+[pnumkM]?', parts[i]):
                    valor_str = parts[i]
                    break
            
            # Si no se encontro valor, usar la posicion 3
            if valor_str is None and len(parts) > 3:
                valor_str = parts[3]
        else:
            # Formato con tipo separado: "V V1 N0 N1 9"
            letra = parts[0]
            if letra not in tipo_por_letra:
                errores.append(f"Linea {line_num}: Tipo '{letra}' no reconocido")
                continue
            tipo = tipo_por_letra[letra]
            nombre = parts[1] if len(parts) > 1 else None
            nodo_origen = parts[2] if len(parts) > 2 else None
            nodo_destino = parts[3] if len(parts) > 3 else None
            valor_str = parts[4] if len(parts) > 4 else None
        
        # Validar campos
        if not nombre:
            errores.append(f"Linea {line_num}: Falta nombre del componente")
            continue
        if not nodo_origen or not nodo_destino:
            errores.append(f"Linea {line_num}: Faltan nodos de conexion")
            continue
        if not valor_str:
            errores.append(f"Linea {line_num}: Falta valor del componente")
            continue
        
        # Parsear valor
        valor = parse_valor(valor_str)
        if valor is None:
            errores.append(f"Linea {line_num}: Valor '{valor_str}' no valido")
            continue
        
        # Detectar prefijo para mostrar
        prefijo = ""
        for p in prefijos_regex:
            if p and valor_str.endswith(p):
                prefijo = p
                break
        
        componentes.append({
            "nombre": nombre,
            "tipo": tipo,
            "tipo_corto": componentes_disponibles[tipo]["tipo"],
            "tipo_elec": componentes_disponibles[tipo]["tipo_elec"],
            "unidad": componentes_disponibles[tipo]["unidad"],
            "valor": valor / prefijos_regex.get(prefijo, 1) if prefijo else valor,
            "prefijo": prefijo,
            "multiplo": prefijos_regex.get(prefijo, 1),
            "valor_total": valor,
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
        valor = st.text_input("Valor")
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
        except:
            st.sidebar.error("Valor numerico invalido")

# ---------- NETLIST ----------
st.sidebar.divider()
st.sidebar.header("Netlist")
with st.sidebar.expander("Cargar desde Netlist", expanded=True):
    st.markdown("Formato: V1 N0 N1 9  o  V1 N0 N1 DC 9")
    netlist = st.text_area("Pega el netlist:", height=150, placeholder="V1 N0 N1 9\nR1 N1 N2 27k\nC1 N2 N0 100u")
    
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
                            st.sidebar.success(f"Agregado {c['nombre']}")
                    st.rerun()
                elif not errores:
                    st.sidebar.warning("No se encontraron componentes validos")
            else:
                st.sidebar.warning("Netlist vacio")
    
    with col2:
        if st.button("Ejemplo RC", key="ejemplo_rc", use_container_width=True):
            ejemplo = "V1 N0 N1 9\nR1 N1 N2 27k\nC1 N2 N0 100u"
            netlist = ejemplo
            nuevos, errores = parsear_netlist(ejemplo)
            for c in nuevos:
                if c['nombre'] not in [x['nombre'] for x in st.session_state.componentes]:
                    st.session_state.componentes.append(c)
                    st.sidebar.success(f"Agregado {c['nombre']}")
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

# ---------- FUNCIONES ----------
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
            if R and C and Vin:
                tau = R*C
                st.subheader("Circuito RC")
                st.latex(r"A = \begin{bmatrix} 1 & -1 & 0 \\ 0 & 1 & -1 \end{bmatrix}")
                st.latex(r"e = \begin{bmatrix} V_{N1} \\ V_{N2} \end{bmatrix}")
                st.latex(r"i = \begin{bmatrix} i_{V1} \\ i_{R1} \\ i_{C1} \end{bmatrix}")
                st.latex(r"v = \begin{bmatrix} v_{V1} \\ v_{R1} \\ v_{C1} \end{bmatrix}")
                st.latex(r"v_{V1}=V_{in},\quad v_{R1}=R i_{R1},\quad i_{C1}=C\frac{dv_{C1}}{dt}")
                st.latex(rf"\frac{{dV_C}}{{dt}} + \frac{{1}}{{{tau:.4f}}} V_C = \frac{{{Vin:.1f}}}{{{tau:.4f}}}")
                st.latex(rf"V_C(t) = {Vin:.1f}(1 - e^{{-t/{tau:.4f}}})")
            else:
                st.info("Circuito no RC simple")

with b3:
    if st.button("Codigo MATLAB", key="matlab"):
        R, C, Vin = analizar_rc(st.session_state.componentes)
        if R and C and Vin:
            tau = R*C
            code = f"""% Circuito RC
clear; clc;
syms Vc(t)
R={R:.6f}; C={C:.6f}; Vin={Vin:.6f}; tau=R*C;
eq = diff(Vc,t) == -1/tau*Vc + Vin/tau;
cond = Vc(0)==0;
Vc_sol = dsolve(eq,cond);
fplot(Vc_sol, [0 5*tau])
xlabel('t(s)'); ylabel('Vc(V)')
grid on
"""
            st.code(code, language="matlab")
            st.download_button("Descargar", code, "circuito.m", key="descargar_matlab")

with b4:
    if st.button("Limpiar Todo", key="limpiar_todo"):
        st.session_state.componentes = []
        st.rerun()
