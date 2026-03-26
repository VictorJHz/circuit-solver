import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
from sympy import symbols, Eq, Derivative, latex, Function, solve, dsolve, Matrix, zeros, simplify
import numpy as np
import re

# ---------- CONFIGURACIÓN ----------
st.set_page_config(page_title="Circuit Solver", layout="wide")
st.title("⚡ Circuit Solver")
st.caption("Analizador general de circuitos electricos - Metodo de Tablueau")

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
        return None, None
    valor_str = valor_str.strip().lower()
    match = re.match(r'^([\d\.]+)([pnumkM]?)$', valor_str)
    if match:
        num_str, pref = match.groups()
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
        
        if '#' in line:
            line = line.split('#')[0].strip()
        if ';' in line:
            line = line.split(';')[0].strip()
        
        if not line:
            continue
            
        parts = line.split()
        if len(parts) < 4:
            errores.append(f"Linea {line_num}: Formato incorrecto")
            continue
        
        nombre = parts[0]
        letra = nombre[0].upper()
        
        if letra not in tipo_por_letra:
            errores.append(f"Linea {line_num}: Tipo '{letra}' no reconocido")
            continue
        
        tipo = tipo_por_letra[letra]
        nodo_origen = parts[1]
        nodo_destino = parts[2]
        
        valor_str = None
        for i in range(3, len(parts)):
            if re.search(r'[\d\.]', parts[i]):
                valor_str = parts[i]
                break
        
        if not valor_str:
            errores.append(f"Linea {line_num}: No se encontro valor")
            continue
        
        valor_total, prefijo = parse_valor(valor_str)
        if valor_total is None:
            errores.append(f"Linea {line_num}: Valor '{valor_str}' no valido")
            continue
        
        mult = prefijos_regex.get(prefijo, 1)
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
    nombre = st.text_input("Nombre (R1, C1, V1, L1)")
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
        except ValueError:
            st.sidebar.error("Valor numerico invalido")

# ---------- NETLIST ----------
st.sidebar.divider()
st.sidebar.header("Netlist")
with st.sidebar.expander("Cargar desde Netlist", expanded=False):
    st.markdown("**Formato:** V1 N0 N1 9   o   R1 N1 N2 27k   o   L1 N1 N0 10m")
    netlist = st.text_area("Pega el netlist:", height=120)
    
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
                    st.rerun()
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

def clasificar_circuito(componentes):
    """Clasifica el circuito segun sus componentes"""
    tiene_resistencia = any(c['tipo'] == "Resistencia" for c in componentes)
    tiene_capacitor = any(c['tipo'] == "Capacitor" for c in componentes)
    tiene_inductor = any(c['tipo'] == "Inductor" for c in componentes)
    tiene_fuente_v = any(c['tipo'] == "Fuente de Voltaje" for c in componentes)
    tiene_fuente_i = any(c['tipo'] == "Fuente de Corriente" for c in componentes)
    
    if tiene_capacitor or tiene_inductor:
        tipo = "Dinamico"
        orden = sum(1 for c in componentes if c['tipo'] in ["Capacitor", "Inductor"])
        
        if tiene_capacitor and not tiene_inductor:
            subtipo = "RC"
        elif tiene_inductor and not tiene_capacitor:
            subtipo = "RL"
        elif tiene_capacitor and tiene_inductor:
            subtipo = "RLC"
        else:
            subtipo = "Dinamico"
        
        return tipo, subtipo, orden
    else:
        return "Estatico", "Resistivo", 0

def verificar_circuito_rc_valido(componentes):
    """Verifica si el circuito es un RC serie valido (1R, 1C, 1V en serie)"""
    num_res = sum(1 for c in componentes if c['tipo'] == "Resistencia")
    num_cap = sum(1 for c in componentes if c['tipo'] == "Capacitor")
    num_fuente_v = sum(1 for c in componentes if c['tipo'] == "Fuente de Voltaje")
    num_fuente_i = sum(1 for c in componentes if c['tipo'] == "Fuente de Corriente")
    
    if num_res != 1 or num_cap != 1 or num_fuente_v != 1 or num_fuente_i != 0:
        return False
    
    R = next(c for c in componentes if c['tipo'] == "Resistencia")
    C = next(c for c in componentes if c['tipo'] == "Capacitor")
    V = next(c for c in componentes if c['tipo'] == "Fuente de Voltaje")
    
    G = nx.Graph()
    for comp in [R, C, V]:
        G.add_edge(comp['nodo_origen'], comp['nodo_destino'])
    
    if nx.number_connected_components(G) != 1:
        return False
    
    nodos = set()
    for comp in [R, C, V]:
        nodos.add(comp['nodo_origen'])
        nodos.add(comp['nodo_destino'])
    
    if len(nodos) != 3:
        return False
    
    return True

def verificar_circuito_rl_valido(componentes):
    """Verifica si el circuito es un RL serie valido (1R, 1L, 1V en serie)"""
    num_res = sum(1 for c in componentes if c['tipo'] == "Resistencia")
    num_ind = sum(1 for c in componentes if c['tipo'] == "Inductor")
    num_fuente_v = sum(1 for c in componentes if c['tipo'] == "Fuente de Voltaje")
    num_fuente_i = sum(1 for c in componentes if c['tipo'] == "Fuente de Corriente")
    
    if num_res != 1 or num_ind != 1 or num_fuente_v != 1 or num_fuente_i != 0:
        return False
    
    R = next(c for c in componentes if c['tipo'] == "Resistencia")
    L = next(c for c in componentes if c['tipo'] == "Inductor")
    V = next(c for c in componentes if c['tipo'] == "Fuente de Voltaje")
    
    G = nx.Graph()
    for comp in [R, L, V]:
        G.add_edge(comp['nodo_origen'], comp['nodo_destino'])
    
    if nx.number_connected_components(G) != 1:
        return False
    
    nodos = set()
    for comp in [R, L, V]:
        nodos.add(comp['nodo_origen'])
        nodos.add(comp['nodo_destino'])
    
    if len(nodos) != 3:
        return False
    
    return True

def verificar_circuito_rlc_valido(componentes):
    """Verifica si el circuito es un RLC serie valido (1R, 1L, 1C, 1V en serie)"""
    num_res = sum(1 for c in componentes if c['tipo'] == "Resistencia")
    num_ind = sum(1 for c in componentes if c['tipo'] == "Inductor")
    num_cap = sum(1 for c in componentes if c['tipo'] == "Capacitor")
    num_fuente_v = sum(1 for c in componentes if c['tipo'] == "Fuente de Voltaje")
    num_fuente_i = sum(1 for c in componentes if c['tipo'] == "Fuente de Corriente")
    
    if num_res != 1 or num_ind != 1 or num_cap != 1 or num_fuente_v != 1 or num_fuente_i != 0:
        return False
    
    R = next(c for c in componentes if c['tipo'] == "Resistencia")
    L = next(c for c in componentes if c['tipo'] == "Inductor")
    C = next(c for c in componentes if c['tipo'] == "Capacitor")
    V = next(c for c in componentes if c['tipo'] == "Fuente de Voltaje")
    
    G = nx.Graph()
    for comp in [R, L, C, V]:
        G.add_edge(comp['nodo_origen'], comp['nodo_destino'])
    
    if nx.number_connected_components(G) != 1:
        return False
    
    nodos = set()
    for comp in [R, L, C, V]:
        nodos.add(comp['nodo_origen'])
        nodos.add(comp['nodo_destino'])
    
    if len(nodos) != 3:
        return False
    
    return True

def generar_reporte_rc(R, C, Vin, tau):
    """Genera reporte completo para circuito RC"""
    st.markdown("### 🔷 CONVENCION UNICA Y CONSISTENTE")
    st.markdown(r"""
    **Convencion de signos adoptada:**
    - **KCL:** +1 = corriente sale del nodo | -1 = corriente entra al nodo
    - **KVL:** $v_{\text{rama}} = e_{\text{origen}} - e_{\text{destino}}$
    """)
    
    st.markdown("### 1. Matriz de Incidencia A")
    st.latex(r"A = \begin{bmatrix} 1 & -1 & 0 \\ 0 & 1 & -1 \end{bmatrix}")
    
    st.markdown("### 2. KCL en forma matricial")
    st.latex(r"A \cdot i = 0")
    
    st.markdown("### 3. KVL en forma matricial")
    st.latex(r"v = A^T \cdot e")
    
    st.markdown("### 4. Relaciones de los Componentes (BR)")
    st.latex(r"\text{Fuente:} \quad v_{V1} = V_{in} = " + f"{Vin:.1f}" + r"\ V")
    st.latex(r"\text{Resistencia:} \quad v_{R1} = R \cdot i_{R1} = " + f"{R:.0f}" + r"\ \Omega \cdot i_{R1}")
    st.latex(r"\text{Capacitor:} \quad i_{C1} = C \cdot \frac{d v_{C1}}{dt} = " + f"{C:.0e}" + r"\ F \cdot \frac{d v_{C1}}{dt}")
    
    st.markdown("### 5. Ecuacion Diferencial")
    st.latex(rf"{Vin:.1f} - V_C = {R:.0f} \cdot {C:.0e} \cdot \frac{{dV_C}}{{dt}}")
    st.latex(rf"\frac{{dV_C}}{{dt}} + \frac{{1}}{{{tau:.4f}}} V_C = \frac{{{Vin:.1f}}}{{{tau:.4f}}}")
    
    st.markdown("### 6. Variable de Estado")
    st.latex(r"x(t) = V_C(t)")
    
    st.markdown("### 7. Ecuacion de Estado")
    st.latex(rf"\dot{{x}} = -\frac{{1}}{{{tau:.4f}}} x + \frac{{{Vin:.1f}}}{{{tau:.4f}}}")
    
    st.markdown("### 8. Solucion Analitica")
    st.latex(f"V_C(t) = {Vin:.1f} \\cdot (1 - e^{{-t/{tau:.4f}}}) \\quad [V]")

def generar_reporte_rl(R, L, Vin, tau):
    """Genera reporte para circuito RL"""
    st.markdown("### 🔷 Circuito RL Serie")
    
    st.markdown("### 1. Relaciones de los Componentes")
    st.latex(r"\text{Fuente:} \quad v_{V1} = V_{in} = " + f"{Vin:.1f}" + r"\ V")
    st.latex(r"\text{Resistencia:} \quad v_{R1} = R \cdot i_{R1} = " + f"{R:.0f}" + r"\ \Omega \cdot i_{R1}")
    st.latex(r"\text{Inductor:} \quad v_{L1} = L \cdot \frac{d i_{L1}}{dt} = " + f"{L:.0e}" + r"\ H \cdot \frac{d i_{L1}}{dt}")
    
    st.markdown("### 2. Ecuacion Diferencial")
    st.latex(rf"{Vin:.1f} = {R:.0f} \cdot i_L + {L:.0e} \cdot \frac{{di_L}}{{dt}}")
    st.latex(rf"\frac{{di_L}}{{dt}} + \frac{{1}}{{{tau:.4f}}} i_L = \frac{{{Vin:.1f}}}{{{L:.0e}}}")
    
    st.markdown("### 3. Variable de Estado")
    st.latex(r"x(t) = i_L(t) \quad [A]")
    
    st.markdown("### 4. Ecuacion de Estado")
    st.latex(rf"\dot{{x}} = -\frac{{1}}{{{tau:.4f}}} x + \frac{{{Vin:.1f}}}{{{L:.0e}}}")
    
    st.markdown("### 5. Solucion Analitica")
    st.latex(f"i_L(t) = {Vin/R:.4f} \\cdot (1 - e^{{-t/{tau:.4f}}}) \\quad [A]")

def generar_reporte_rlc(R, L, C, Vin):
    """Genera reporte para circuito RLC"""
    alpha = R / (2 * L)
    omega0 = 1 / np.sqrt(L * C)
    
    st.markdown("### 🔷 Circuito RLC Serie")
    
    st.markdown("### 1. Ecuacion Diferencial")
    st.latex(rf"L C \frac{{d^2 v_C}}{{dt^2}} + R C \frac{{d v_C}}{{dt}} + v_C = V_{{in}}")
    
    st.markdown("### 2. Parametros del Sistema")
    st.write(f"- **Frecuencia natural:** $\\omega_0 = {omega0:.4f}$ rad/s")
    st.write(f"- **Factor de amortiguamiento:** $\\alpha = {alpha:.4f}$")
    st.write(f"- **Coeficiente de amortiguamiento:** $\\zeta = {alpha/omega0:.4f}$")
    
    if omega0 > alpha:
        st.write("- **Tipo:** Subamortiguado")
    elif omega0 == alpha:
        st.write("- **Tipo:** Críticamente amortiguado")
    else:
        st.write("- **Tipo:** Sobreamortiguado")
    
    st.markdown("### 3. Variable de Estado")
    st.latex(r"x_1(t) = v_C(t), \quad x_2(t) = i_L(t)")

def generar_reporte_estatico(componentes):
    """Genera reporte para circuitos estaticos"""
    st.subheader("📐 Analisis de Circuito Estatico")
    
    st.write("**Componentes detectados:**")
    for c in componentes:
        st.write(f"- {c['nombre']}: {c['tipo']} = {c['valor']}{c['prefijo']}{c['unidad']}")
    
    nodos = obtener_nodos(componentes)
    nodos_no_tierra = [n for n in nodos if n != "N0"]
    n = len(nodos_no_tierra)
    
    if n == 0:
        st.warning("No hay nodos para analisis (solo tierra)")
        return
    
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
                I[nodo_idx[nodo_o], 0] += I_val
            if nodo_d != "N0":
                I[nodo_idx[nodo_d], 0] -= I_val
        
        elif c['tipo'] == "Fuente de Voltaje":
            st.warning(f"Fuente de voltaje {c['nombre']} requiere supernodo")
    
    st.write("### Matriz de Conductancias G")
    st.latex(latex(G))
    st.write("### Vector de Corrientes I")
    st.latex(latex(I))
    
    try:
        if G.det() != 0:
            V_sol = G.inv() * I
            st.write("**Voltajes de nodo:**")
            for i, nodo in enumerate(nodos_no_tierra):
                st.latex(f"V_{{{nodo}}} = {latex(V_sol[i, 0])} \\quad [V]")
    except:
        st.warning("No se pudo resolver el sistema")

def generar_reporte_dinamico(componentes, subtipo, orden):
    """Genera reporte para circuitos dinamicos"""
    st.subheader(f"📐 Analisis de Circuito Dinamico - Tipo: {subtipo}")
    st.write(f"**Orden del sistema:** {orden}")
    
    # Detectar valores
    R_val = C_val = L_val = Vin_val = None
    for c in componentes:
        if c['tipo'] == "Resistencia":
            R_val = c['valor_total']
        elif c['tipo'] == "Capacitor":
            C_val = c['valor_total']
        elif c['tipo'] == "Inductor":
            L_val = c['valor_total']
        elif c['tipo'] == "Fuente de Voltaje":
            Vin_val = c['valor_total']
    
    # Verificar casos especiales
    if subtipo == "RC" and verificar_circuito_rc_valido(componentes):
        tau = R_val * C_val
        generar_reporte_rc(R_val, C_val, Vin_val, tau)
    
    elif subtipo == "RL" and verificar_circuito_rl_valido(componentes):
        tau = L_val / R_val
        generar_reporte_rl(R_val, L_val, Vin_val, tau)
    
    elif subtipo == "RLC" and verificar_circuito_rlc_valido(componentes):
        generar_reporte_rlc(R_val, L_val, C_val, Vin_val)
    
    else:
        st.info("Circuito dinamico general - analisis basico")
        st.write("**Ecuaciones del circuito:**")
        
        t = symbols('t')
        nodos = obtener_nodos(componentes)
        
        v_nodos = {}
        for nodo in nodos:
            if nodo != "N0":
                v_nodos[nodo] = Function(f'V_{nodo}')(t)
        
        i_componentes = {}
        for c in componentes:
            if c['needs_current']:
                i_componentes[c['nombre']] = Function(f'i_{c["nombre"]}')(t)
        
        for nodo in nodos:
            if nodo == "N0":
                continue
            suma = 0
            for c in componentes:
                if c['nodo_origen'] == nodo:
                    suma += i_componentes[c['nombre']]
                elif c['nodo_destino'] == nodo:
                    suma -= i_componentes[c['nombre']]
            if suma != 0:
                st.latex(latex(Eq(suma, 0)))
        
        for c in componentes:
            nombre = c['nombre']
            tipo = c['tipo']
            valor = c['valor_total']
            nodo_o = c['nodo_origen']
            nodo_d = c['nodo_destino']
            
            v_o = 0 if nodo_o == "N0" else v_nodos[nodo_o]
            v_d = 0 if nodo_d == "N0" else v_nodos[nodo_d]
            v_diff = v_o - v_d
            
            if tipo == "Resistencia":
                st.latex(latex(Eq(v_diff, valor * i_componentes[nombre])))
            elif tipo == "Capacitor":
                st.latex(latex(Eq(i_componentes[nombre], valor * Derivative(v_diff, t))))
            elif tipo == "Inductor":
                st.latex(latex(Eq(v_diff, valor * Derivative(i_componentes[nombre], t))))
            elif tipo == "Fuente de Voltaje":
                if nodo_o == "N0":
                    st.latex(latex(Eq(v_d - v_o, valor)))
                else:
                    st.latex(latex(Eq(v_diff, valor)))
            elif tipo == "Fuente de Corriente":
                st.latex(latex(Eq(i_componentes[nombre], valor)))

def dibujar_grafo_formal(cs):
    """Genera un grafo formal del circuito"""
    G = nx.MultiDiGraph()
    
    nodos = obtener_nodos(cs)
    for nodo in nodos:
        G.add_node(nodo)
    
    ramas_info = []
    for idx, c in enumerate(cs, 1):
        nombre_rama = f"b{idx}"
        origen = c['nodo_origen']
        destino = c['nodo_destino']
        
        G.add_edge(origen, destino, 
                   label=nombre_rama,
                   tipo=c['tipo'],
                   tipo_elec=c['tipo_elec'],
                   nombre_comp=c['nombre'],
                   valor=f"{c['valor']}{c['prefijo']}{c['unidad']}")
        
        ramas_info.append({
            "rama": nombre_rama,
            "origen": origen,
            "destino": destino,
            "tipo": c['tipo'],
            "tipo_elec": c['tipo_elec'],
            "componente": c['nombre'],
            "valor": f"{c['valor']}{c['prefijo']}{c['unidad']}"
        })
    
    return G, nodos, ramas_info

# ---------- BOTONES PRINCIPALES ----------
st.subheader("Acciones")
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("Mostrar Grafo Formal", key="mostrar_grafo"):
        if not st.session_state.componentes:
            st.warning("Agrega componentes")
        else:
            G, nodos, ramas_info = dibujar_grafo_formal(st.session_state.componentes)
            
            st.subheader("📌 Nodos del Circuito")
            st.write(f"Nodos identificados: {', '.join(nodos)}")
            st.caption("N0 = Tierra (referencia)")
            
            st.subheader("🔗 Ramas del Circuito")
            ramas_df = []
            for r in ramas_info:
                ramas_df.append({
                    "Rama": r["rama"],
                    "Origen": r["origen"],
                    "Destino": r["destino"],
                    "Tipo": r["tipo"],
                    "Tipo Eléctrico": r["tipo_elec"],
                    "Componente": r["componente"],
                    "Valor": r["valor"]
                })
            st.dataframe(ramas_df, use_container_width=True)
            
            st.subheader("📊 Grafo Formal del Circuito")
            st.caption("Representación: Nodos = puntos | Ramas = flechas | + = origen | - = destino")
            
            fig, ax = plt.subplots(figsize=(14, 10))
            pos = nx.circular_layout(G)
            
            nx.draw_networkx_nodes(G, pos, node_color='lightblue', 
                                   node_size=3000, ax=ax, edgecolors='black', linewidths=2)
            nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold', ax=ax)
            
            edge_colors = []
            edge_widths = []
            for u, v, d in G.edges(data=True):
                if d['tipo_elec'] == "Activo":
                    edge_colors.append('orange')
                    edge_widths.append(3)
                else:
                    edge_colors.append('gray')
                    edge_widths.append(2)
            
            nx.draw_networkx_edges(G, pos, edge_color=edge_colors, arrows=True,
                                   arrowsize=25, arrowstyle='->', ax=ax, 
                                   connectionstyle="arc3,rad=0.15", width=edge_widths)
            
            edge_labels = {(u, v): d['label'] for u, v, d in G.edges(data=True)}
            nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, 
                                        font_size=10, ax=ax,
                                        bbox=dict(boxstyle="round,pad=0.3", 
                                                 facecolor="white", alpha=0.8))
            
            for u, v, d in G.edges(data=True):
                x1, y1 = pos[u]
                x2, y2 = pos[v]
                dx = (x2 - x1) * 0.15
                dy = (y2 - y1) * 0.15
                
                ax.text(x1 + dx*0.5, y1 + dy*0.5, '+', 
                       fontsize=14, fontweight='bold', color='green',
                       ha='center', va='center')
                ax.text(x2 - dx*0.5, y2 - dy*0.5, '-', 
                       fontsize=14, fontweight='bold', color='red',
                       ha='center', va='center')
            
            plt.title("Grafo Formal del Circuito", fontsize=16, fontweight='bold')
            plt.axis('off')
            
            legend_elements = [
                plt.Line2D([0], [0], color='orange', linewidth=3, label='Rama Activa (Fuente)'),
                plt.Line2D([0], [0], color='gray', linewidth=2, label='Rama Pasiva (R, L, C)'),
                plt.Line2D([0], [0], marker='+', color='green', markersize=12, linestyle='None', label='Polo Positivo (+)'),
                plt.Line2D([0], [0], marker='_', color='red', markersize=12, linestyle='None', label='Polo Negativo (-)')
            ]
            ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
            
            st.pyplot(fig)

with col2:
    if st.button("Generar Ecuaciones", key="generar_eq"):
        if not st.session_state.componentes:
            st
