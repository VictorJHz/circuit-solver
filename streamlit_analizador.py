import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
from sympy import symbols, Eq, Derivative, latex, Function, solve, dsolve, Matrix, zeros, simplify
import numpy as np
import re
import pandas as pd

# ---------- CONFIGURACIÓN ----------
st.set_page_config(page_title="Circuit Solver", layout="wide")
st.title("⚡ Circuit Solver")
st.caption("Analizador universal de circuitos eléctricos - Modified Nodal Analysis (MNA)")

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
            errores.append(f"Línea {line_num}: Formato incorrecto")
            continue
        
        primero = parts[0]
        
        if primero and primero[0] in tipo_por_letra:
            letra = primero[0]
            nombre = primero[1:] if len(primero) > 1 else primero
            tipo = tipo_por_letra[letra]
            if not nombre:
                nombre = primero
            
            nodo_origen = parts[1] if len(parts) > 1 else None
            nodo_destino = parts[2] if len(parts) > 2 else None
            
            valor_str = None
            for i in range(3, len(parts)):
                if re.search(r'[\d\.]', parts[i]):
                    valor_str = parts[i]
                    break
            if not valor_str and len(parts) > 3:
                valor_str = parts[3]
        else:
            letra = parts[0]
            if letra not in tipo_por_letra:
                errores.append(f"Línea {line_num}: Tipo '{letra}' no reconocido")
                continue
            tipo = tipo_por_letra[letra]
            nombre = parts[1] if len(parts) > 1 else None
            nodo_origen = parts[2] if len(parts) > 2 else None
            nodo_destino = parts[3] if len(parts) > 3 else None
            valor_str = parts[4] if len(parts) > 4 else None
        
        if not nombre:
            errores.append(f"Línea {line_num}: Falta nombre")
            continue
        if not nodo_origen or not nodo_destino:
            errores.append(f"Línea {line_num}: Faltan nodos")
            continue
        if not valor_str:
            errores.append(f"Línea {line_num}: Falta valor")
            continue
        
        valor_total, prefijo = parse_valor(valor_str)
        if valor_total is None:
            errores.append(f"Línea {line_num}: Valor '{valor_str}' no válido")
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
            st.sidebar.error("Valor numérico inválido")

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
                st.sidebar.warning("Netlist vacío")
    
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

# ---------- FUNCIONES DE ANÁLISIS ----------
def obtener_nodos(cs):
    nodos = set()
    for c in cs:
        nodos.add(c['nodo_origen'])
        nodos.add(c['nodo_destino'])
    return sorted(list(nodos))

def clasificar_circuito(componentes):
    """Clasifica el circuito según sus componentes"""
    tiene_capacitor = any(c['tipo'] == "Capacitor" for c in componentes)
    tiene_inductor = any(c['tipo'] == "Inductor" for c in componentes)
    
    if tiene_capacitor or tiene_inductor:
        tipo = "Dinámico"
        orden = sum(1 for c in componentes if c['tipo'] in ["Capacitor", "Inductor"])
        
        if tiene_capacitor and not tiene_inductor:
            subtipo = "RC"
        elif tiene_inductor and not tiene_capacitor:
            subtipo = "RL"
        elif tiene_capacitor and tiene_inductor:
            subtipo = "RLC"
        else:
            subtipo = "Dinámico"
        
        return tipo, subtipo, orden
    else:
        return "Estático", "Resistivo", 0

def construir_sistema_mna(componentes, nodos):
    """
    Construye el sistema MNA completo:
    [G   B] [V]   [I]
    [B^T 0] [Iv] = [E]
    """
    nodos_no_tierra = [n for n in nodos if n != "N0"]
    n_nodos = len(nodos_no_tierra)
    
    fuentes_v = [c for c in componentes if c['tipo'] == "Fuente de Voltaje"]
    m = len(fuentes_v)
    
    nodo_idx = {nodo: i for i, nodo in enumerate(nodos_no_tierra)}
    
    G = zeros(n_nodos, n_nodos)
    B = zeros(n_nodos, m)
    I = zeros(n_nodos, 1)
    E = zeros(m, 1)
    
    # Resistencias
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
    
    # Fuentes de corriente
    for c in componentes:
        if c['tipo'] == "Fuente de Corriente":
            I_val = c['valor_total']
            nodo_o = c['nodo_origen']
            nodo_d = c['nodo_destino']
            
            if nodo_o != "N0":
                I[nodo_idx[nodo_o], 0] -= I_val
            if nodo_d != "N0":
                I[nodo_idx[nodo_d], 0] += I_val
    
    # Fuentes de voltaje
    for idx_v, c in enumerate(fuentes_v):
        nodo_o = c['nodo_origen']
        nodo_d = c['nodo_destino']
        V_val = c['valor_total']
        
        E[idx_v, 0] = V_val
        
        if nodo_o != "N0":
            B[nodo_idx[nodo_o], idx_v] = 1
        if nodo_d != "N0":
            B[nodo_idx[nodo_d], idx_v] = -1
    
    # Construir sistema
    top_left = G.row_join(B)
    bottom_left = B.T.row_join(zeros(m, m))
    M = top_left.col_join(bottom_left)
    b = I.col_join(E)
    
    return M, b, n_nodos, m, fuentes_v, G, B, I, E

def resolver_mna(M, b):
    try:
        if M.det() != 0:
            sol = M.inv() * b
            return sol, None
        else:
            return None, "La matriz MNA es singular (circuito mal definido)"
    except Exception as e:
        return None, str(e)

def generar_reporte_completo(componentes):
    """Genera reporte completo del circuito con KCL, KVL, BR y sistema MNA"""
    st.subheader("📐 Análisis de Circuito - Modified Nodal Analysis (MNA)")
    
    nodos = obtener_nodos(componentes)
    nodos_no_tierra = [n for n in nodos if n != "N0"]
    
    st.write("**Componentes detectados:**")
    for c in componentes:
        st.write(f"- {c['nombre']}: {c['tipo']} = {c['valor']}{c['prefijo']}{c['unidad']}")
    
    st.write(f"**Nodos:** {nodos_no_tierra} (N0 = tierra)")
    
    # ========== 1. CONVENCIÓN ==========
    st.markdown("### 🔷 CONVENCIÓN ÚNICA Y CONSISTENTE")
    st.markdown(r"""
    **Convención de signos adoptada:**
    - **KCL:** +1 = corriente que **entra** al nodo | -1 = corriente que **sale** del nodo
    - **KVL:** $v_{\text{rama}} = e_{\text{origen}} - e_{\text{destino}}$
    - **Fuente de corriente:** La corriente fluye de $nodo_{origen} \rightarrow nodo_{destino}$
    - **Fuente de voltaje:** Matriz B: +1 en $nodo_{origen}$, -1 en $nodo_{destino}$
    """)
    
    # ========== 2. MATRIZ DE INCIDENCIA A ==========
    st.markdown("### 1. Matriz de Incidencia A")
    st.write("**Orden de ramas:** " + ", ".join([c['nombre'] for c in componentes]))
    st.write("**Convención:** +1 = corriente sale, -1 = corriente entra")
    
    n_ramas = len(componentes)
    A = zeros(len(nodos_no_tierra), n_ramas)
    nodo_idx = {nodo: i for i, nodo in enumerate(nodos_no_tierra)}
    
    for j, c in enumerate(componentes):
        if c['nodo_origen'] != "N0":
            A[nodo_idx[c['nodo_origen']], j] = 1
        if c['nodo_destino'] != "N0":
            A[nodo_idx[c['nodo_destino']], j] = -1
    
    st.latex(latex(A))
    st.caption(f"Filas: nodos {nodos_no_tierra} | Columnas: ramas")
    
    # ========== 3. KCL EN FORMA MATRICIAL ==========
    st.markdown("### 2. KCL en forma matricial")
    st.latex(r"A \cdot i = 0")
    st.caption("La suma algebraica de corrientes en cada nodo es cero")
    
    # ========== 4. KVL EN FORMA MATRICIAL ==========
    st.markdown("### 3. KVL en forma matricial")
    st.latex(r"v = A^T \cdot e")
    st.latex(r"\begin{bmatrix} v_1 \\ v_2 \\ \vdots \\ v_{n} \end{bmatrix} = A^T \begin{bmatrix} V_{N1} \\ V_{N2} \\ \vdots \\ V_{Nn} \end{bmatrix}")
    st.caption("Los voltajes de rama se expresan en función de los potenciales nodales")
    
    # ========== 5. RELACIONES DE COMPONENTES (BR) ==========
    st.markdown("### 4. Relaciones de los Componentes (BR)")
    for c in componentes:
        if c['tipo'] == "Resistencia":
            st.latex(rf"\text{{{c['nombre']}}}: \quad v_{{{c['nombre']}}} = {c['valor_total']:.0f} \cdot i_{{{c['nombre']}}} \quad [\Omega]")
        elif c['tipo'] == "Fuente de Corriente":
            st.latex(rf"\text{{{c['nombre']}}}: \quad i_{{{c['nombre']}}} = {c['valor_total']:.4f} \quad [A]")
        elif c['tipo'] == "Fuente de Voltaje":
            st.latex(rf"\text{{{c['nombre']}}}: \quad v_{{{c['nombre']}}} = {c['valor_total']:.4f} \quad [V]")
        elif c['tipo'] == "Capacitor":
            st.latex(rf"\text{{{c['nombre']}}}: \quad i_{{{c['nombre']}}} = {c['valor_total']:.0e} \cdot \frac{{dv_{{{c['nombre']}}}}}{{dt}} \quad [F]")
        elif c['tipo'] == "Inductor":
            st.latex(rf"\text{{{c['nombre']}}}: \quad v_{{{c['nombre']}}} = {c['valor_total']:.0e} \cdot \frac{{di_{{{c['nombre']}}}}}{{dt}} \quad [H]")
    
    # ========== 6. SISTEMA MNA ==========
    st.markdown("### 5. Sistema MNA")
    st.latex(r"\begin{bmatrix} G & B \\ B^T & 0 \end{bmatrix} \begin{bmatrix} V \\ I_v \end{bmatrix} = \begin{bmatrix} I \\ E \end{bmatrix}")
    
    # Construir sistema
    M, b, n_nodos, m, fuentes_v, G_mat, B_mat, I_vec, E_vec = construir_sistema_mna(componentes, nodos)
    
    st.write(f"**Tamaño del sistema:** {M.shape[0]} × {M.shape[1]}")
    
    with st.expander("📊 Ver matrices del sistema MNA"):
        st.write("**Matriz G (conductancias):**")
        st.latex(latex(G_mat))
        st.write("**Matriz B (incidencia de fuentes de voltaje):**")
        st.latex(latex(B_mat))
        st.write("**Vector I (fuentes de corriente):**")
        st.latex(latex(I_vec))
        st.write("**Vector E (fuentes de voltaje):**")
        st.latex(latex(E_vec))
        st.write("**Matriz M completa:**")
        st.latex(latex(M))
        st.write("**Vector b:**")
        st.latex(latex(b))
    
    # Resolver
    sol, error = resolver_mna(M, b)
    
    if error:
        st.error(f"Error al resolver: {error}")
        return
    
    # Extraer resultados
    voltajes = {}
    for i, nodo in enumerate(nodos_no_tierra):
        voltajes[nodo] = float(sol[i, 0])
    
    corrientes_fuentes_v = {}
    for i, fv in enumerate(fuentes_v):
        corrientes_fuentes_v[fv['nombre']] = float(sol[n_nodos + i, 0])
    
    # ========== 7. RESULTADOS ==========
    st.markdown("### 📊 Resultados")
    
    st.write("**Voltajes de nodo (convención libro):**")
    voltajes_df = pd.DataFrame([
        {"Nodo": nodo, "Voltaje [V]": f"{v:.4f}"}
        for nodo, v in voltajes.items()
    ])
    st.dataframe(voltajes_df, use_container_width=True, hide_index=True)
    
    if corrientes_fuentes_v:
        st.write("**Corrientes en fuentes de voltaje:**")
        corrientes_fv_df = pd.DataFrame([
            {"Fuente": nombre, "Corriente [A]": f"{i:.4f}"}
            for nombre, i in corrientes_fuentes_v.items()
        ])
        st.dataframe(corrientes_fv_df, use_container_width=True, hide_index=True)
    
    # ========== 8. CORRIENTES EN RAMAS ==========
    st.markdown("### 🔄 Corrientes en Ramas")
    
    corrientes_data = []
    for c in componentes:
        if c['tipo'] == "Resistencia":
            nodo_o = c['nodo_origen']
            nodo_d = c['nodo_destino']
            v_o = voltajes.get(nodo_o, 0)
            v_d = voltajes.get(nodo_d, 0)
            R = c['valor_total']
            i = (v_o - v_d) / R
            
            if i > 0:
                direccion = f"{nodo_o} → {nodo_d}"
            elif i < 0:
                direccion = f"{nodo_d} → {nodo_o}"
            else:
                direccion = "Cero"
            
            corrientes_data.append({
                "Elemento": c['nombre'],
                "Tipo": c['tipo'],
                "Corriente [A]": f"{i:.4f}",
                "Dirección": direccion
            })
        elif c['tipo'] == "Fuente de Corriente":
            I_val = c['valor_total']
            if c['nodo_origen'] != "N0" and c['nodo_destino'] != "N0":
                direccion = f"{c['nodo_origen']} → {c['nodo_destino']}"
            elif c['nodo_origen'] != "N0":
                direccion = f"{c['nodo_origen']} → N0"
            else:
                direccion = f"N0 → {c['nodo_destino']}"
            
            corrientes_data.append({
                "Elemento": c['nombre'],
                "Tipo": c['tipo'],
                "Corriente [A]": f"{I_val:.4f}",
                "Dirección": direccion
            })
        elif c['tipo'] == "Fuente de Voltaje":
            I_val = corrientes_fuentes_v.get(c['nombre'], 0)
            if c['nodo_origen'] != "N0" and c['nodo_destino'] != "N0":
                direccion = f"{c['nodo_origen']} → {c['nodo_destino']}"
            elif c['nodo_origen'] != "N0":
                direccion = f"{c['nodo_origen']} → N0"
            else:
                direccion = f"N0 → {c['nodo_destino']}"
            
            corrientes_data.append({
                "Elemento": c['nombre'],
                "Tipo": c['tipo'],
                "Corriente [A]": f"{I_val:.4f}",
                "Dirección": direccion
            })
    
    if corrientes_data:
        corrientes_df = pd.DataFrame(corrientes_data)
        st.dataframe(corrientes_df, use_container_width=True, hide_index=True)
    
    # ========== 9. VALIDACIÓN KCL ==========
    st.markdown("### ✅ Validación KCL")
    st.caption("KCL: Suma de corrientes que entran al nodo = 0")
    
    kcl_data = []
    tolerancia = 1e-6
    for nodo in nodos_no_tierra:
        suma = 0
        for c in componentes:
            if c['tipo'] == "Resistencia":
                nodo_o = c['nodo_origen']
                nodo_d = c['nodo_destino']
                v_o = voltajes.get(nodo_o, 0)
                v_d = voltajes.get(nodo_d, 0)
                R = c['valor_total']
                i = (v_o - v_d) / R
                
                if nodo_o == nodo:
                    suma -= i
                elif nodo_d == nodo:
                    suma += i
            
            elif c['tipo'] == "Fuente de Corriente":
                I_val = c['valor_total']
                nodo_o = c['nodo_origen']
                nodo_d = c['nodo_destino']
                
                if nodo_o == nodo:
                    suma -= I_val
                elif nodo_d == nodo:
                    suma += I_val
            
            elif c['tipo'] == "Fuente de Voltaje":
                I_val = corrientes_fuentes_v.get(c['nombre'], 0)
                nodo_o = c['nodo_origen']
                nodo_d = c['nodo_destino']
                
                if nodo_o == nodo:
                    suma -= I_val
                elif nodo_d == nodo:
                    suma += I_val
        
        if abs(suma) < tolerancia:
            status = "✅ Satisfecha"
        else:
            status = "❌ No satisfecha"
        
        kcl_data.append({
            "Nodo": nodo,
            "Suma Corrientes [A]": f"{suma:.2e}",
            "Estado": status
        })
    
    if kcl_data:
        kcl_df = pd.DataFrame(kcl_data)
        st.dataframe(kcl_df, use_container_width=True, hide_index=True)
    
    # ========== 10. POTENCIAS ==========
    st.markdown("### ⚡ Potencias en Elementos")
    
    potencias_data = []
    for c in componentes:
        if c['tipo'] == "Resistencia":
            nodo_o = c['nodo_origen']
            nodo_d = c['nodo_destino']
            v_o = voltajes.get(nodo_o, 0)
            v_d = voltajes.get(nodo_d, 0)
            v = v_o - v_d
            i = v / c['valor_total']
            P = v * i
            
            if P < 0:
                P = -P
                v = abs(v)
                i = abs(i)
            
            potencias_data.append({
                "Elemento": c['nombre'],
                "Tipo": c['tipo'],
                "Voltaje [V]": f"{v:.4f}",
                "Corriente [A]": f"{i:.4f}",
                "Potencia [W]": f"{P:.4f}",
                "Comportamiento": "🔋 Disipa"
            })
        
        elif c['tipo'] == "Fuente de Corriente":
            nodo_o = c['nodo_origen']
            nodo_d = c['nodo_destino']
            v_o = voltajes.get(nodo_o, 0)
            v_d = voltajes.get(nodo_d, 0)
            v = v_o - v_d
            I_val = c['valor_total']
            P = v * I_val
            
            if P > 0:
                comportamiento = "⚡ Entrega"
            else:
                comportamiento = "🔋 Absorbe"
            
            potencias_data.append({
                "Elemento": c['nombre'],
                "Tipo": c['tipo'],
                "Voltaje [V]": f"{v:.4f}",
                "Corriente [A]": f"{I_val:.4f}",
                "Potencia [W]": f"{P:.4f}",
                "Comportamiento": comportamiento
            })
        
        elif c['tipo'] == "Fuente de Voltaje":
            nodo_o = c['nodo_origen']
            nodo_d = c['nodo_destino']
            v_o = voltajes.get(nodo_o, 0)
            v_d = voltajes.get(nodo_d, 0)
            v = v_o - v_d
            I_val = corrientes_fuentes_v.get(c['nombre'], 0)
            P = v * I_val
            
            if P > 0:
                comportamiento = "⚡ Entrega"
            else:
                comportamiento = "🔋 Absorbe"
            
            potencias_data.append({
                "Elemento": c['nombre'],
                "Tipo": c['tipo'],
                "Voltaje [V]": f"{v:.4f}",
                "Corriente [A]": f"{I_val:.4f}",
                "Potencia [W]": f"{P:.4f}",
                "Comportamiento": comportamiento
            })
    
    if potencias_data:
        potencias_df = pd.DataFrame(potencias_data)
        st.dataframe(potencias_df, use_container_width=True, hide_index=True)
    
    # ========== 11. BALANCE DE POTENCIA ==========
    st.markdown("### ⚖️ Balance de Potencia")
    
    potencia_total_disipada = sum(float(p["Potencia [W]"]) for p in potencias_data if "Disipa" in p["Comportamiento"])
    potencia_total_entregada = sum(float(p["Potencia [W]"]) for p in potencias_data if "Entrega" in p["Comportamiento"])
    potencia_total_absorbida = sum(float(p["Potencia [W]"]) for p in potencias_data if "Absorbe" in p["Comportamiento"])
    
    col_bal1, col_bal2, col_bal3 = st.columns(3)
    with col_bal1:
        st.metric("Potencia Disipada", f"{potencia_total_disipada:.4f} W")
    with col_bal2:
        st.metric("Potencia Entregada", f"{potencia_total_entregada:.4f} W")
    with col_bal3:
        st.metric("Potencia Absorbida", f"{potencia_total_absorbida:.4f} W")
    
    if abs(potencia_total_entregada - (potencia_total_disipada + abs(potencia_total_absorbida))) < 1e-6:
        st.success("✅ Balance de potencia verificado: Potencia Entregada = Potencia Disipada + Potencia Absorbida")
    else:
        st.warning("⚠️ Balance de potencia no verificado")

# ---------- FUNCIONES DE GRÁFICO ----------
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

# ---------- FUNCIONES PARA CIRCUITOS DINÁMICOS ESPECIALES ----------
def verificar_circuito_rc_valido(componentes):
    num_res = sum(1 for c in componentes if c['tipo'] == "Resistencia")
    num_cap = sum(1 for c in componentes if c['tipo'] == "Capacitor")
    num_fuente_v = sum(1 for c in componentes if c['tipo'] == "Fuente de Voltaje")
    num_fuente_i = sum(1 for c in componentes if c['tipo'] == "Fuente de Corriente")
    
    if num_res != 1 or num_cap != 1 or num_fuente_v
