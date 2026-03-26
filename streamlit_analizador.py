import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
from sympy import symbols, Eq, Derivative, latex, Function, solve, dsolve, Matrix, zeros
import numpy as np
import re

# ---------- CONFIGURACIÓN ----------
st.set_page_config(page_title="Circuit Solver", layout="wide")
st.title("⚡ Circuit Solver")
st.caption("Analisis de circuitos electricos - Metodo de Tablueau en dominio tiempo")

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
        except ValueError:
            st.sidebar.error("Valor numerico invalido")

# ---------- NETLIST ----------
st.sidebar.divider()
st.sidebar.header("Netlist")
with st.sidebar.expander("Cargar desde Netlist", expanded=False):
    st.markdown("**Formato:** V1 N0 N1 9   o   R1 N1 N2 27k")
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

def dibujar_grafo_formal(cs):
    """
    Genera un grafo formal del circuito con:
    - Nodos: puntos de conexion
    - Ramas: flechas con orientacion
    - Polaridad: + en origen, - en destino
    - Solo flechas, sin simbolos electricos
    """
    G = nx.MultiDiGraph()
    
    # Obtener todos los nodos
    nodos = obtener_nodos(cs)
    for nodo in nodos:
        G.add_node(nodo)
    
    # Asignar nombres de ramas (b1, b2, b3, ...)
    ramas_info = []
    for idx, c in enumerate(cs, 1):
        nombre_rama = f"b{idx}"
        
        # Determinar orientacion y polaridad
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
            
            # Mostrar lista de nodos
            st.subheader("📌 Nodos del Circuito")
            st.write(f"Nodos identificados: {', '.join(nodos)}")
            st.caption("N0 = Tierra (referencia)")
            
            # Mostrar lista de ramas
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
            
            # Grafico formal
            st.subheader("📊 Grafo Formal del Circuito")
            st.caption("Representación: Nodos = puntos | Ramas = flechas | + = origen | - = destino")
            
            fig, ax = plt.subplots(figsize=(14, 10))
            
            # Disposicion circular para mejor visualizacion
            pos = nx.circular_layout(G)
            
            # Dibujar nodos
            nx.draw_networkx_nodes(G, pos, node_color='lightblue', 
                                   node_size=3000, ax=ax, edgecolors='black', linewidths=2)
            nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold', ax=ax)
            
            # Dibujar ramas (flechas)
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
            
            # Etiquetas de ramas (b1, b2, ...)
            edge_labels = {(u, v): d['label'] for u, v, d in G.edges(data=True)}
            nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, 
                                        font_size=10, ax=ax,
                                        bbox=dict(boxstyle="round,pad=0.3", 
                                                 facecolor="white", alpha=0.8))
            
            # Agregar signos de polaridad (+ y -) en cada rama
            for u, v, d in G.edges(data=True):
                # Calcular posicion media de la arista
                x1, y1 = pos[u]
                x2, y2 = pos[v]
                xm = (x1 + x2) / 2
                ym = (y1 + y2) / 2
                
                # Desplazar ligeramente para evitar solapamiento
                dx = (x2 - x1) * 0.15
                dy = (y2 - y1) * 0.15
                
                # Signo + en el origen
                ax.text(x1 + dx*0.5, y1 + dy*0.5, '+', 
                       fontsize=14, fontweight='bold', color='green',
                       ha='center', va='center')
                
                # Signo - en el destino
                ax.text(x2 - dx*0.5, y2 - dy*0.5, '-', 
                       fontsize=14, fontweight='bold', color='red',
                       ha='center', va='center')
            
            plt.title("Grafo Formal del Circuito", fontsize=16, fontweight='bold')
            plt.axis('off')
            
            # Leyenda (corregida)
            legend_elements = [
                plt.Line2D([0], [0], color='orange', linewidth=3, label='Rama Activa (Fuente)'),
                plt.Line2D([0], [0], color='gray', linewidth=2, label='Rama Pasiva (R, L, C)'),
                plt.Line2D([0], [0], marker='+', color='green', markersize=12, linestyle='None', label='Polo Positivo (+)'),
                plt.Line2D([0], [0], marker='_', color='red', markersize=12, linestyle='None', label='Polo Negativo (-)')
            ]
            ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
            
            st.pyplot(fig)
            
            # Informacion adicional
            with st.expander("📖 Interpretacion del Grafo Formal"):
                st.markdown(r"""
                **Convenciones utilizadas:**
                - **Nodos**: Puntos de conexion electrica (N0 = tierra)
                - **Ramas**: Elementos del circuito representados como flechas
                - **Direccion de la flecha**: Sentido de corriente positiva
                - **+ (verde)**: Terminal positivo (origen) - voltaje mas alto
                - **- (rojo)**: Terminal negativo (destino) - voltaje mas bajo
                
                **Para elementos pasivos (R, L, C):**
                - La corriente entra por el terminal positivo (+)
                
                **Para elementos activos (fuentes):**
                - La polaridad sigue la definicion de la fuente
                - Fuente de voltaje: + en el nodo de mayor potencial
                
                **Relacion con analisis nodal:**
                - $v_{\text{rama}} = e_{\text{origen}} - e_{\text{destino}}$
                - La matriz de incidencia A se construye con +1 en origen, -1 en destino
                """)

with b2:
    if st.button("Generar Ecuaciones", key="generar_eq"):
        if not st.session_state.componentes:
            st.warning("Agrega componentes")
        else:
            R, C, Vin = analizar_rc(st.session_state.componentes)
            if R is not None and C is not None and Vin is not None:
                generar_reporte_completo(R, C, Vin)
            else:
                st.info("Circuito no RC simple. Agrega una Resistencia, un Capacitor y una Fuente de Voltaje.")
                st.write("**Componentes actuales:**")
                for c in st.session_state.componentes:
                    st.write(f"- {c['nombre']}: {c['tipo']}")

with b3:
    if st.button("Codigo MATLAB", key="matlab"):
        R, C, Vin = analizar_rc(st.session_state.componentes)
        if R is not None and C is not None and Vin is not None:
            tau = R * C
            code = f"""% Circuito RC - Analisis Completo
% Metodo de Tablueau en dominio tiempo
clear; clc; close all;

%% Parametros del circuito
R = {R:.6f};  % Ohm
C = {C:.6f};  % Faradios
Vin = {Vin:.6f};  % Voltios
tau = R * C;  % Constante de tiempo [s]

%% Variable de estado
syms Vc(t)
eq = diff(Vc, t) == -1/tau * Vc + Vin/tau;
cond = Vc(0) == 0;
Vc_sol = dsolve(eq, cond);

%% Resultados analiticos
disp('=== SOLUCION DEL CIRCUITO RC ===');
disp('Ecuacion diferencial:');
disp(eq);
fprintf('\\nVc(t) = %.2f * (1 - exp(-t/%.4f)) [V]\\n', Vin, tau);
disp(' ');
pretty(Vc_sol);

%% Forma de estado
A = -1/tau;
B = 1/tau;
u = Vin;
fprintf('\\n=== FORMA DE ESTADO ===\\n');
fprintf('dx/dt = %.6f x + %.6f u\\n', A, B);
fprintf('u(t) = %.2f [V] (entrada)\\n', u);
fprintf('y(t) = x(t) [V] (salida)\\n');

%% Parametros del sistema
fprintf('\\n=== PARAMETROS DEL SISTEMA ===\\n');
fprintf('Constante de tiempo tau = %.4f [s]\\n', tau);
fprintf('Voltaje final en estado estable = %.2f [V]\\n', Vin);
fprintf('Tiempo de establecimiento (5tau) = %.4f [s]\\n', 5*tau);
fprintf('Velocidad de respuesta = 1/tau = %.4f [1/s]\\n', 1/tau);
fprintf('Polo del sistema = s = -%.4f [1/s]\\n', 1/tau);

%% Grafica de la respuesta
figure('Position', [100, 100, 800, 500]);
fplot(Vc_sol, [0 5*tau], 'LineWidth', 2, 'Color', 'b');
xlabel('t [s]', 'FontSize', 12);
ylabel('Vc(t) [V]', 'FontSize', 12);
title('Respuesta del Circuito RC - Carga del Capacitor', 'FontSize', 14);
grid on;
hold on;
plot([0 5*tau], [Vin Vin], '--r', 'LineWidth', 1.5);
legend('Vc(t)', 'Vin', 'Location', 'best');

%% Interpretacion fisica
fprintf('\\n=== INTERPRETACION FISICA ===\\n');
fprintf('El capacitor se carga desde 0 V hasta %.2f V\\n', Vin);
fprintf('El regimen transitorio dura %.2f segundos (5τ)\\n', 5*tau);
fprintf('La constante de tiempo τ = %.4f s representa el tiempo al 63.2%% de la carga final\\n', tau);
"""
            st.code(code, language="matlab")
            st.download_button("Descargar codigo MATLAB", code, "circuito_rc.m", key="descargar_matlab")
        else:
            st.info("Agrega una Resistencia, un Capacitor y una Fuente de Voltaje para generar el codigo MATLAB.")

with b4:
    if st.button("Limpiar Todo", key="limpiar_todo"):
        st.session_state.componentes = []
        st.rerun()

# ---------- FUNCION DE REPORTE ----------
def generar_reporte_completo(R, C, Vin):
    """Genera el reporte completo con todos los bloques de analisis"""
    tau = R * C
    
    st.markdown("---")
    st.header("📐 Analisis Completo del Circuito RC")
    
    # ========== 1. CONVENCION UNICA ==========
    st.markdown("### 🔷 CONVENCION UNICA Y CONSISTENTE")
    st.markdown(r"""
    **Convencion de signos adoptada (UNICA para todo el desarrollo):**
    - **KCL:** +1 = corriente sale del nodo | -1 = corriente entra al nodo
    - **KVL:** $v_{\text{rama}} = e_{\text{origen}} - e_{\text{destino}}$
    - **BR:** $v_{\text{rama}} = Z \cdot i_{\text{rama}} + V_s$ (dominio tiempo, $Z$ es operador diferencial)
    """)
    
    # ========== 2. MATRIZ DE INCIDENCIA A ==========
    st.markdown("### 1. Matriz de Incidencia A")
    st.write("**Orden de ramas:** [V1, R1, C1]")
    st.write("**Convencion:** +1 sale, -1 entra")
    st.latex(r"A = \begin{bmatrix} 1 & -1 & 0 \\ 0 & 1 & -1 \end{bmatrix}")
    st.caption("Filas: nodos N1, N2 | Columnas: ramas [V1, R1, C1]")
    
    # ========== 3. VECTOR e ==========
    st.markdown("### 2. Vector e (Potenciales nodales)")
    st.latex(r"e = \begin{bmatrix} V_{N1} \\ V_{N2} \end{bmatrix} \quad [V]")
    st.caption("Voltajes de los nodos respecto a tierra (N0 = 0V)")
    
    # ========== 4. KCL EN FORMA MATRICIAL ==========
    st.markdown("### 3. KCL en forma matricial")
    st.latex(r"A \cdot i = 0")
    st.latex(r"\begin{bmatrix} 1 & -1 & 0 \\ 0 & 1 & -1 \end{bmatrix} \begin{bmatrix} i_{V1} \\ i_{R1} \\ i_{C1} \end{bmatrix} = \begin{bmatrix} 0 \\ 0 \end{bmatrix}")
    st.caption("Ecuaciones: $i_{V1} - i_{R1} = 0$, $i_{R1} - i_{C1} = 0$")
    
    # ========== 5. KVL EN FORMA MATRICIAL ==========
    st.markdown("### 4. KVL en forma matricial")
    st.latex(r"v = A^T \cdot e")
    st.latex(r"\begin{bmatrix} v_{V1} \\ v_{R1} \\ v_{C1} \end{bmatrix} = \begin{bmatrix} 1 & 0 \\ -1 & 1 \\ 0 & -1 \end{bmatrix} \begin{bmatrix} V_{N1} \\ V_{N2} \end{bmatrix}")
    st.write("**Interpretacion explicita:**")
    st.latex(r"v_{V1} = V_{N1} - 0 = V_{N1} \quad [V]")
    st.latex(r"v_{R1} = V_{N1} - V_{N2} \quad [V]")
    st.latex(r"v_{C1} = V_{N2} - 0 = V_{N2} \quad [V]")
    
    # ========== 6. BR EN DOMINIO TIEMPO ==========
    st.markdown("### 5. Relaciones de los Componentes (BR) en dominio tiempo")
    st.latex(r"\text{Fuente V1:} \quad v_{V1} = V_{in} = " + f"{Vin:.1f}" + r"\ V")
    st.latex(r"\text{Resistencia R1:} \quad v_{R1} = R \cdot i_{R1} = " + f"{R:.0f}" + r"\ \Omega \cdot i_{R1}")
    st.latex(r"\text{Capacitor C1:} \quad i_{C1} = C \cdot \frac{d v_{C1}}{dt} = " + f"{C:.0e}" + r"\ F \cdot \frac{d v_{C1}}{dt}")
    st.write("")
    st.write("**Forma integral equivalente del capacitor:**")
    st.latex(r"v_{C1}(t) = \frac{1}{C} \int_{0}^{t} i_{C1}(\tau) d\tau + v_{C1}(0) \quad [V]")
    
    # ========== 7. MATRIZ Z (OPERADOR) ==========
    st.markdown("### 6. Matriz Z - Operador en dominio tiempo")
    st.latex(r"Z = \begin{bmatrix} 0 & 0 & 0 \\ 0 & R & 0 \\ 0 & 0 & \frac{1}{C} \left(\frac{d}{dt}\right)^{-1} \end{bmatrix}")
    st.caption(r"**Nota:** El operador $\left(\frac{d}{dt}\right)^{-1} \equiv \int dt$ representa **integracion en el tiempo**. Para el capacitor: $v_C = \frac{1}{C} \int i_C dt$")
    
    # ========== 8. VECTOR Vs ==========
    st.markdown("### 7. Vector Vs (Fuentes de voltaje)")
    st.latex(r"V_s = \begin{bmatrix} V_{in} \\ 0 \\ 0 \end{bmatrix} = \begin{bmatrix} " + f"{Vin:.1f}" + r" \\ 0 \\ 0 \end{bmatrix}")
    st.caption("**Mapeo:** Rama 1 (V1) → Fuente de voltaje Vin | Ramas 2 y 3 → 0")
    
    # ========== 9. METODO DE TABLEAU ==========
    st.markdown("### 8. Metodo de Tablueau - Estructura en Bloques")
    st.latex(r"\begin{bmatrix} A & 0 & 0 \\ 0 & I & 0 \\ A^T & 0 & -Z \end{bmatrix} \begin{bmatrix} e \\ i \\ v \end{bmatrix} = \begin{bmatrix} 0 \\ 0 \\ V_s \end{bmatrix}")
    st.write("")
    st.write("**Dimensiones de los bloques:**")
    st.write("- **A**: matriz de incidencia (2×3)")
    st.write("- **I**: matriz identidad (3×3)")
    st.write("- **Z**: matriz de operadores (3×3)")
    st.write("- **Sistema total**: 8 ecuaciones × 8 variables")
    st.write("")
    st.write("**Variables:**")
    st.latex(r"e = \begin{bmatrix} V_{N1} \\ V_{N2} \end{bmatrix}_{(2×1)},\quad i = \begin{bmatrix} i_{V1} \\ i_{R1} \\ i_{C1} \end{bmatrix}_{(3×1)},\quad v = \begin{bmatrix} v_{V1} \\ v_{R1} \\ v_{C1} \end{bmatrix}_{(3×1)}")
    
    # ========== 10. ECUACION DIFERENCIAL ==========
    st.markdown("### 9. Ecuacion Diferencial del Circuito")
    st.latex(rf"{Vin:.1f} - V_C = {R:.0f} \cdot {C:.0e} \cdot \frac{{dV_C}}{{dt}} \quad [V]")
    st.latex(rf"\frac{{dV_C}}{{dt}} + \frac{{1}}{{{tau:.4f}}} V_C = \frac{{{Vin:.1f}}}{{{tau:.4f}}} \quad [V/s]")
    st.caption(f"Unidades: $V_C$ [V], $t$ [s], $dV_C/dt$ [V/s]")
    
    # ========== 11. VARIABLE DE ESTADO ==========
    st.markdown("### 10. Variable de Estado")
    st.latex(r"x(t) = V_C(t) \quad [V]")
    st.latex(r"u(t) = V_{in} \quad \text{(Entrada)}")
    st.latex(r"y(t) = V_C(t) \quad \text{(Salida)}")
    
    # ========== 12. ECUACION DE ESTADO ==========
    st.markdown("### 11. Ecuacion de Estado")
    A_val = -1/tau
    B_val = 1/tau
    st.latex(rf"\dot{{x}} = -\frac{{1}}{{RC}} x + \frac{{1}}{{RC}} u")
    st.latex(rf"\dot{{x}} = {A_val:.6f} x + {B_val:.6f} u \quad [V/s]")
    st.latex(rf"u(t) = {Vin:.1f} \quad [V]")
    st.caption(f"Forma estandar: $\dot{{x}} = A x + B u$, $y = x$")
    st.latex(f"A = {A_val:.6f}\ [1/s],\quad B = {B_val:.6f}\ [1/s],\quad u(t) = {Vin:.1f}\ [V]")
    
    # ========== 13. CLASIFICACION DEL SISTEMA ==========
    st.markdown("### 12. Clasificacion del Sistema")
    st.write(f"- **Orden:** Sistema de primer orden")
    st.write(f"- **Linealidad:** Lineal")
    st.write(f"- **Invarianza:** Invariante en el tiempo")
    st.write(f"- **Tipo:** Pasa-bajas de primer orden")
    st.write(f"- **Estabilidad:** Asintoticamente estable (polo en $s = -{1/tau:.4f}$)")
    
    # ========== 14. INTERPRETACION FISICA ==========
    st.markdown("### 13. Interpretacion Fisica")
    st.markdown(f"""
    - **Carga del capacitor:** El capacitor se carga desde 0 V hasta {Vin:.1f} V
    - **Regimen transitorio:** Dura aproximadamente {5*tau:.2f} segundos (5τ)
    - **Estado estable:** Despues de {5*tau:.2f} s, $V_C \\approx {Vin:.1f}$ V
    - **Constante de tiempo:** $\\tau = {tau:.4f}$ s (63.2% de la carga final)
    - **Comportamiento:** Respuesta exponencial creciente: $V_C(t) = {Vin:.1f}(1 - e^{{-t/{tau:.4f}}})$
    """)
    
    # ========== 15. SOLUCION ANALITICA ==========
    st.markdown("### 14. Solucion Analitica")
    st.latex(f"V_C(t) = {Vin:.1f} \\cdot (1 - e^{{-t/{tau:.4f}}}) \\quad [V]")
