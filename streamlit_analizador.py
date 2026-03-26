import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
from sympy import symbols, Eq, Derivative, latex, Function, solve, dsolve, Matrix, zeros, simplify, eye
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
        
        nombre = parts[0]
        letra = nombre[0].upper()
        
        if letra not in tipo_por_letra:
            errores.append(f"Línea {line_num}: Tipo '{letra}' no reconocido")
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
            errores.append(f"Línea {line_num}: No se encontró valor")
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
    
    # Identificar fuentes de voltaje
    fuentes_v = [c for c in componentes if c['tipo'] == "Fuente de Voltaje"]
    m = len(fuentes_v)
    
    # Mapeo de nodos a índices
    nodo_idx = {nodo: i for i, nodo in enumerate(nodos_no_tierra)}
    
    # Tamaño del sistema MNA: n_nodos + m
    N = n_nodos + m
    
    # Inicializar matrices
    G = zeros(n_nodos, n_nodos)  # Matriz de conductancias
    B = zeros(n_nodos, m)        # Matriz de incidencia de fuentes de voltaje
    I = zeros(n_nodos, 1)        # Vector de corrientes (fuentes de corriente)
    E = zeros(m, 1)              # Vector de voltajes de fuentes
    
    # ========== 1. PROCESAR RESISTENCIAS ==========
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
    
    # ========== 2. PROCESAR FUENTES DE CORRIENTE ==========
    for c in componentes:
        if c['tipo'] == "Fuente de Corriente":
            I_val = c['valor_total']
            nodo_o = c['nodo_origen']
            nodo_d = c['nodo_destino']
            
            # Convención: corriente fluye de nodo_origen → nodo_destino
            if nodo_o != "N0":
                I[nodo_idx[nodo_o], 0] -= I_val  # Sale del nodo → negativo
            if nodo_d != "N0":
                I[nodo_idx[nodo_d], 0] += I_val  # Entra al nodo → positivo
    
    # ========== 3. PROCESAR FUENTES DE VOLTAJE ==========
    for idx_v, c in enumerate(fuentes_v):
        nodo_o = c['nodo_origen']
        nodo_d = c['nodo_destino']
        V_val = c['valor_total']
        
        # Vector E: voltaje de la fuente
        E[idx_v, 0] = V_val
        
        # Matriz B: incidencia de la fuente
        if nodo_o != "N0":
            B[nodo_idx[nodo_o], idx_v] = 1   # Corriente sale del nodo origen
        if nodo_d != "N0":
            B[nodo_idx[nodo_d], idx_v] = -1  # Corriente entra al nodo destino
    
    # ========== 4. CONSTRUIR SISTEMA MNA ==========
    # Matriz superior izquierda: [G, B]
    top_left = G.row_join(B)
    
    # Matriz inferior izquierda: [B^T, 0]
    bottom_left = B.T.row_join(zeros(m, m))
    
    # Matriz completa M
    M = top_left.col_join(bottom_left)
    
    # Vector de fuentes
    b = I.col_join(E)
    
    return M, b, n_nodos, m, fuentes_v

def resolver_mna(M, b):
    """Resuelve el sistema MNA y retorna los resultados"""
    try:
        if M.det() != 0:
            sol = M.inv() * b
            return sol, None
        else:
            return None, "La matriz MNA es singular (circuito mal definido)"
    except Exception as e:
        return None, str(e)

def generar_reporte_estatico_mna(componentes):
    """Genera reporte para circuitos estáticos usando MNA"""
    st.subheader("📐 Análisis de Circuito Estático - Modified Nodal Analysis (MNA)")
    
    st.write("**Componentes detectados:**")
    for c in componentes:
        st.write(f"- {c['nombre']}: {c['tipo']} = {c['valor']}{c['prefijo']}{c['unidad']}")
    
    nodos = obtener_nodos(componentes)
    nodos_no_tierra = [n for n in nodos if n != "N0"]
    
    # Construir sistema MNA
    M, b, n_nodos, m, fuentes_v = construir_sistema_mna(componentes, nodos)
    
    st.write(f"**Nodos:** {nodos_no_tierra} (N0 = tierra)")
    st.write(f"**Fuentes de voltaje:** {len(fuentes_v)}")
    st.write(f"**Tamaño del sistema MNA:** {M.shape[0]} × {M.shape[1]}")
    
    # Mostrar matrices
    with st.expander("📊 Matrices del Sistema MNA"):
        st.write("**Matriz M = [G, B; B^T, 0]**")
        st.latex(latex(M))
        st.write("**Vector b = [I; E]**")
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
    
    # ========== PARTE 1: RESULTADOS ==========
    st.markdown("### 📖 Resultados")
    
    # Voltajes nodales
    st.write("**Voltajes nodales:**")
    voltajes_df = pd.DataFrame([
        {"Nodo": nodo, "Voltaje [V]": f"{v:.4f}"}
        for nodo, v in voltajes.items()
    ])
    st.dataframe(voltajes_df, use_container_width=True, hide_index=True)
    
    # Corrientes en fuentes de voltaje
    if corrientes_fuentes_v:
        st.write("**Corrientes en fuentes de voltaje:**")
        corrientes_fv_df = pd.DataFrame([
            {"Fuente": nombre, "Corriente [A]": f"{i:.4f}"}
            for nombre, i in corrientes_fuentes_v.items()
        ])
        st.dataframe(corrientes_fv_df, use_container_width=True, hide_index=True)
    
    # ========== PARTE 2: CORRIENTES EN RESISTENCIAS ==========
    st.markdown("### 🔄 Corrientes en Ramas")
    
    corrientes_data = []
    for c in componentes:
        if c['tipo'] == "Resistencia":
            nodo_o = c['nodo_origen']
            nodo_d = c['nodo_destino']
            v_o = voltajes.get(nodo_o, 0)
            v_d = voltajes.get(nodo_d, 0)
            R = c['valor_total']
            i_libro = (v_o - v_d) / R
            
            if i_libro > 0:
                direccion = f"{nodo_o} → {nodo_d}"
            elif i_libro < 0:
                direccion = f"{nodo_d} → {nodo_o}"
            else:
                direccion = "Cero"
            
            corrientes_data.append({
                "Elemento": c['nombre'],
                "Tipo": c['tipo'],
                "Corriente [A]": f"{i_libro:.4f}",
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
    
    # ========== PARTE 3: VALIDACIÓN KCL ==========
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
                    suma -= i  # Sale → negativo
                elif nodo_d == nodo:
                    suma += i  # Entra → positivo
            
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
    
    # ========== PARTE 4: POTENCIAS ==========
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
    
    # ========== PARTE 5: BALANCE DE POTENCIA ==========
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

# ---------- FUNCIONES EXISTENTES PARA CIRCUITOS DINÁMICOS ----------
def verificar_circuito_rc_valido(componentes):
    """Verifica si el circuito es un RC serie válido (1R, 1C, 1V en serie)"""
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
    """Verifica si el circuito es un RL serie válido (1R, 1L, 1V en serie)"""
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
    """Verifica si el circuito es un RLC serie válido (1R, 1L, 1C, 1V en serie)"""
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
    st.markdown("### 🔷 CONVENCIÓN ÚNICA Y CONSISTENTE")
    st.markdown(r"""
    **Convención de signos adoptada:**
    - **KCL:** +1 = corriente que entra al nodo
    - **KVL:** $v_{\text{rama}} = e_{\text{origen}} - e_{\text{destino}}$
    - **Convención de libro:** Las corrientes en resistencias fluyen del nodo de mayor potencial al de menor potencial
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
    
    st.markdown("### 5. Ecuación Diferencial")
    st.latex(rf"{Vin:.1f} - V_C = {R:.0f} \cdot {C:.0e} \cdot \frac{{dV_C}}{{dt}}")
    st.latex(rf"\frac{{dV_C}}{{dt}} + \frac{{1}}{{{tau:.4f}}} V_C = \frac{{{Vin:.1f}}}{{{tau:.4f}}}")
    
    st.markdown("### 6. Variable de Estado")
    st.latex(r"x(t) = V_C(t)")
    
    st.markdown("### 7. Ecuación de Estado")
    st.latex(rf"\dot{{x}} = -\frac{{1}}{{{tau:.4f}}} x + \frac{{{Vin:.1f}}}{{{tau:.4f}}}")
    
    st.markdown("### 8. Solución Analítica")
    st.latex(f"V_C(t) = {Vin:.1f} \\cdot (1 - e^{{-t/{tau:.4f}}}) \\quad [V]")

def generar_reporte_rl(R, L, Vin, tau):
    """Genera reporte para circuito RL"""
    st.markdown("### 🔷 Circuito RL Serie")
    
    st.markdown("### 1. Relaciones de los Componentes")
    st.latex(r"\text{Fuente:} \quad v_{V1} = V_{in} = " + f"{Vin:.1f}" + r"\ V")
    st.latex(r"\text{Resistencia:} \quad v_{R1} = R \cdot i_{R1} = " + f"{R:.0f}" + r"\ \Omega \cdot i_{R1}")
    st.latex(r"\text{Inductor:} \quad v_{L1} = L \cdot \frac{d i_{L1}}{dt} = " + f"{L:.0e}" + r"\ H \cdot \frac{d i_{L1}}{dt}")
    
    st.markdown("### 2. Ecuación Diferencial")
    st.latex(rf"{Vin:.1f} = {R:.0f} \cdot i_L + {L:.0e} \cdot \frac{{di_L}}{{dt}}")
    st.latex(rf"\frac{{di_L}}{{dt}} + \frac{{1}}{{{tau:.4f}}} i_L = \frac{{{Vin:.1f}}}{{{L:.0e}}}")
    
    st.markdown("### 3. Variable de Estado")
    st.latex(r"x(t) = i_L(t) \quad [A]")
    
    st.markdown("### 4. Ecuación de Estado")
    st.latex(rf"\dot{{x}} = -\frac{{1}}{{{tau:.4f}}} x + \frac{{{Vin:.1f}}}{{{L:.0e}}}")
    
    st.markdown("### 5. Solución Analítica")
    st.latex(f"i_L(t) = {Vin/R:.4f} \\cdot (1 - e^{{-t/{tau:.4f}}}) \\quad [A]")

def generar_reporte_rlc(R, L, C, Vin):
    """Genera reporte para circuito RLC"""
    alpha = R / (2 * L)
    omega0 = 1 / np.sqrt(L * C)
    
    st.markdown("### 🔷 Circuito RLC Serie")
    
    st.markdown("### 1. Ecuación Diferencial")
    st.latex(rf"L C \frac{{d^2 v_C}}{{dt^2}} + R C \frac{{d v_C}}{{dt}} + v_C = V_{{in}}")
    
    st.markdown("### 2. Parámetros del Sistema")
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

def generar_reporte_dinamico(componentes, subtipo, orden):
    """Genera reporte para circuitos dinámicos"""
    st.subheader(f"📐 Análisis de Circuito Dinámico - Tipo: {subtipo}")
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
        st.info("Circuito dinámico general - análisis básico")
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

# ---------- FUNCIONES DE GRAFICO ----------
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
b1, b2, b3, b4 = st.columns(4)

with b1:
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
            st.dataframe(ramas_df, use_container_width=True, hide_index=True)
            
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

with b2:
    if st.button("Generar Ecuaciones", key="generar_eq"):
        if not st.session_state.componentes:
            st.warning("Agrega componentes")
        else:
            # Mostrar componentes para depuración
            st.write("**Componentes detectados:**")
            for c in st.session_state.componentes:
                st.write(f"- {c['nombre']}: {c['tipo']} = {c['valor']}{c['prefijo']}{c['unidad']}")
            
            # Clasificar el circuito
            tipo_sistema, subtipo, orden = clasificar_circuito(st.session_state.componentes)
            
            st.info(f"**Tipo de sistema:** {tipo_sistema} | **Subtipo:** {subtipo} | **Orden:** {orden}")
            
            if tipo_sistema == "Estático":
                generar_reporte_estatico_mna(st.session_state.componentes)
            else:
                generar_reporte_dinamico(st.session_state.componentes, subtipo, orden)

with b3:
    if st.button("Código MATLAB", key="matlab"):
        if not st.session_state.componentes:
            st.warning("Agrega componentes")
        else:
            tipo_sistema, subtipo, orden = clasificar_circuito(st.session_state.componentes)
            
            if subtipo == "RC" and verificar_circuito_rc_valido(st.session_state.componentes):
                R, C, Vin = None, None, None
                for c in st.session_state.componentes:
                    if c['tipo'] == "Resistencia":
                        R = c['valor_total']
                    elif c['tipo'] == "Capacitor":
                        C = c['valor_total']
                    elif c['tipo'] == "Fuente de Voltaje":
                        Vin = c['valor_total']
                
                if R and C and Vin:
                    tau = R * C
                    code = f"""% Circuito RC - Análisis Completo
clear; clc; close all;

R = {R:.6f}; C = {C:.6f}; Vin = {Vin:.6f}; tau = R*C;

syms Vc(t)
eq = diff(Vc, t) == -1/tau * Vc + Vin/tau;
cond = Vc(0) == 0;
Vc_sol = dsolve(eq, cond);

disp('=== SOLUCIÓN DEL CIRCUITO RC ===');
fprintf('Vc(t) = %.2f * (1 - exp(-t/%.4f)) [V]\\n', Vin, tau);
pretty(Vc_sol);

figure;
fplot(Vc_sol, [0 5*tau], 'LineWidth', 2);
xlabel('t [s]'); ylabel('Vc(t) [V]');
title('Respuesta del Circuito RC');
grid on;
hold on;
plot([0 5*tau], [Vin Vin], '--r');
legend('Vc(t)', 'Vin');
"""
                    st.code(code, language="matlab")
                    st.download_button("Descargar código MATLAB", code, "circuito_rc.m", key="descargar_matlab_rc")
                else:
                    st.info("No se detectó un circuito RC válido")
            
            elif subtipo == "RL" and verificar_circuito_rl_valido(st.session_state.componentes):
                R, L, Vin = None, None, None
                for c in st.session_state.componentes:
                    if c['tipo'] == "Resistencia":
                        R = c['valor_total']
                    elif c['tipo'] == "Inductor":
                        L = c['valor_total']
                    elif c['tipo'] == "Fuente de Voltaje":
                        Vin = c['valor_total']
                
                if R and L and Vin:
                    tau = L / R
                    code = f"""% Circuito RL - Análisis Completo
clear; clc; close all;

R = {R:.6f}; L = {L:.6f}; Vin = {Vin:.6f}; tau = L/R;

syms iL(t)
eq = diff(iL, t) == -1/tau * iL + Vin/L;
cond = iL(0) == 0;
iL_sol = dsolve(eq, cond);

disp('=== SOLUCIÓN DEL CIRCUITO RL ===');
fprintf('iL(t) = %.4f * (1 - exp(-t/%.4f)) [A]\\n', Vin/R, tau);
pretty(iL_sol);

figure;
fplot(iL_sol, [0 5*tau], 'LineWidth', 2);
xlabel('t [s]'); ylabel('iL(t) [A]');
title('Respuesta del Circuito RL');
grid on;
hold on;
plot([0 5*tau], [Vin/R Vin/R], '--r');
legend('iL(t)', 'Valor final');
"""
                    st.code(code, language="matlab")
                    st.download_button("Descargar código MATLAB", code, "circuito_rl.m", key="descargar_matlab_rl")
                else:
                    st.info("No se detectó un circuito RL válido")
            
            else:
                # Generar código MATLAB para MNA general
                nodos = obtener_nodos(st.session_state.componentes)
                nodos_no_tierra = [n for n in nodos if n != "N0"]
                n_nodos = len(nodos_no_tierra)
                fuentes_v = [c for c in st.session_state.componentes if c['tipo'] == "Fuente de Voltaje"]
                m = len(fuentes_v)
                
                if n_nodos > 0:
                    nodo_idx = {nodo: i for i, nodo in enumerate(nodos_no_tierra)}
                    
                    matlab_code = f"""% Circuito General - Modified Nodal Analysis (MNA)
clear; clc;

% Nodos: {n_nodos}
% Fuentes de voltaje: {m}
% Tamaño del sistema MNA: {n_nodos + m}

% Inicializar matrices
G = zeros({n_nodos},{n_nodos});
B = zeros({n_nodos},{m});
I = zeros({n_nodos},1);
E = zeros({m},1);

"""
                    # Agregar resistencias
                    for c in st.session_state.componentes:
                        if c['tipo'] == "Resistencia":
                            G_val = 1 / c['valor_total']
                            nodo_o = c['nodo_origen']
                            nodo_d = c['nodo_destino']
                            
                            if nodo_o != "N0" and nodo_d != "N0":
                                i = nodo_idx[nodo_o]
                                j = nodo_idx[nodo_d]
                                matlab_code += f"G({i+1},{i+1}) = G({i+1},{i+1}) + {G_val:.6f};\n"
                                matlab_code += f"G({j+1},{j+1}) = G({j+1},{j+1}) + {G_val:.6f};\n"
                                matlab_code += f"G({i+1},{j+1}) = G({i+1},{j+1}) - {G_val:.6f};\n"
                                matlab_code += f"G({j+1},{i+1}) = G({j+1},{i+1}) - {G_val:.6f};\n"
                            elif nodo_o != "N0":
                                i = nodo_idx[nodo_o]
                                matlab_code += f"G({i+1},{i+1}) = G({i+1},{i+1}) + {G_val:.6f};\n"
                            elif nodo_d != "N0":
                                i = nodo_idx[nodo_d]
                                matlab_code += f"G({i+1},{i+1}) = G({i+1},{i+1}) + {G_val:.6f};\n"
                    
                    # Agregar fuentes de corriente
                    for c in st.session_state.componentes:
                        if c['tipo'] == "Fuente de Corriente":
                            I_val = c['valor_total']
                            nodo_o = c['nodo_origen']
                            nodo_d = c['nodo_destino']
                            
                            if nodo_o != "N0":
                                i = nodo_idx[nodo_o]
                                matlab_code += f"I({i+1}) = I({i+1}) - {I_val:.6f};\n"
                            if nodo_d != "N0":
                                i = nodo_idx[nodo_d]
                                matlab_code += f"I({i+1}) = I({i+1}) + {I_val:.6f};\n"
                    
                    # Agregar fuentes de voltaje
                    for idx_v, c in enumerate(fuentes_v):
                        V_val = c['valor_total']
                        nodo_o = c['nodo_origen']
                        nodo_d = c['nodo_destino']
                        
                        matlab_code += f"E({idx_v+1}) = {V_val:.6f};\n"
                        
                        if nodo_o != "N0":
                            i = nodo_idx[nodo_o]
                            matlab_code += f"B({i+1},{idx_v+1}) = 1;\n"
                        if nodo_d != "N0":
                            i = nodo_idx[nodo_d]
                            matlab_code += f"B({i+1},{idx_v+1}) = -1;\n"
                    
                    matlab_code += """
% Construir sistema MNA
M = [G, B; B', zeros(size(B,2))];
b = [I; E];

% Resolver sistema
x = M \\ b;

% Extraer resultados
n_nodos = size(G,1);
m = size(B,2);
V = x(1:n_nodos);
Iv = x(n_nodos+1:end);

% Mostrar resultados
disp('=== SOLUCIÓN DEL CIRCUITO ===');
disp('Voltajes nodales:');
"""
                    for i, nodo in enumerate(nodos_no_tierra):
                        matlab_code += f"fprintf('V_{nodo} = %.4f V\\n', V({i+1}));\n"
                    
                    if m > 0:
                        matlab_code += """
disp('\\nCorrientes en fuentes de voltaje:');
"""
                        for idx_v, c in enumerate(fuentes_v):
                            matlab_code += f"fprintf('{c['nombre']}: i = %.4f A\\n', Iv({idx_v+1}));\n"
                    
                    st.code(matlab_code, language="matlab")
                    st.download_button("Descargar código MATLAB", matlab_code, "circuito_mna.m", key="descargar_matlab_mna")
                else:
                    st.info("Circuito sin nodos válidos para análisis")

with b4:
    if st.button("Limpiar Todo", key="limpiar_todo"):
        st.session_state.componentes = []
        st.rerun()
