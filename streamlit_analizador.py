""")

netlist_texto = st.text_area("Pega tu netlist aqui:", height=150)

col_net1, col_net2 = st.columns(2)
with col_net1:
    if st.button("Cargar Netlist", use_container_width=True):
        if netlist_texto.strip():
            nuevos_componentes, errores = parsear_netlist(netlist_texto)
            
            if errores:
                for err in errores:
                    st.sidebar.error(err)
            
            if nuevos_componentes:
                # Verificar nombres duplicados con los existentes
                nombres_existentes = [c['nombre'] for c in st.session_state.componentes]
                for c in nuevos_componentes:
                    if c['nombre'] in nombres_existentes:
                        st.sidebar.warning(f"Componente {c['nombre']} ya existe, se omitio")
                    else:
                        st.session_state.componentes.append(c)
                        st.sidebar.success(f"Agregado: {c['nombre']}")
                st.sidebar.success(f"Se cargaron {len([c for c in nuevos_componentes if c['nombre'] not in nombres_existentes])} componentes")
        else:
            st.sidebar.warning("Ingresa un netlist")

with col_net2:
    if st.button("Ejemplo RC", use_container_width=True):
        ejemplo = "V1 N0 N1 9\nR1 N1 N2 27k\nC1 N2 N0 100u"
        st.session_state.netlist_ejemplo = ejemplo
        st.rerun()

# Mostrar ejemplo si existe
if 'netlist_ejemplo' in st.session_state:
st.sidebar.code(st.session_state.netlist_ejemplo, language="text")
del st.session_state.netlist_ejemplo

# ---------- MOSTRAR COMPONENTES ----------
st.subheader("Componentes agregados")
if st.session_state.componentes:
# Boton para limpiar todos
col_clear1, col_clear2 = st.columns([4, 1])
with col_clear2:
    if st.button("Limpiar Todos", key="clear_all_btn"):
        st.session_state.componentes = []
        st.rerun()

for i, c in enumerate(st.session_state.componentes):
    col1, col2 = st.columns([4, 1])
    with col1:
        st.write(f"**{c['nombre']}**: {c['tipo']} ({c['tipo_elec']}) | Valor: {c['valor']}{c['prefijo']}{c['unidad']} | Nodos: {c['nodo_origen']} -> {c['nodo_destino']}")
    with col2:
        if st.button(f"Eliminar", key=f"del_{i}"):
            st.session_state.componentes.pop(i)
            st.rerun()
else:
st.info("No hay componentes agregados. Agrega individualmente o carga un netlist.")

# ---------- FUNCIONES PARA ANALISIS ----------
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

# ----- Generar Sistema de Ecuaciones -----
with col2:
if st.button("Generar Ecuaciones"):
    if not st.session_state.componentes:
        st.warning("Agrega componentes primero")
    else:
        R, C, Vin = analizar_circuito_rc(st.session_state.componentes)
        
        if R is not None and C is not None and Vin is not None:
            tau = R * C
            st.subheader("Analisis Completo del Circuito RC")
            
            st.write("### 🔷 CONVENCION UNICA Y CONSISTENTE")
            st.markdown("""
            **Convencion de signos adoptada (UNICA para todo el desarrollo):**
            - **KCL:** +1 = corriente sale del nodo | -1 = corriente entra al nodo
            - **KVL:** v_rama = e_origen - e_destino
            - **BR:** v_rama = Z·i_rama + V_s (dominio tiempo, Z es operador diferencial)
            """)
            
            st.write("**1. Matriz de Incidencia A (UNICA)**")
            st.write("**Orden de ramas:** [V1, R1, C1]")
            st.write("**Convencion:** +1 sale, -1 entra")
            st.latex(r"A = \begin{bmatrix} 1 & -1 & 0 \\ 0 & 1 & -1 \end{bmatrix}")
            st.caption("Filas: nodos N1, N2 | Columnas: ramas [V1, R1, C1]")
            
            st.write("**2. Vector e (Potenciales nodales)**")
            st.latex(r"e = \begin{bmatrix} V_{N1} \\ V_{N2} \end{bmatrix} \quad [V]")
            
            st.write("**3. KCL en forma matricial**")
            st.latex(r"A \cdot i = 0")
            st.latex(r"\begin{bmatrix} 1 & -1 & 0 \\ 0 & 1 & -1 \end{bmatrix} \begin{bmatrix} i_{V1} \\ i_{R1} \\ i_{C1} \end{bmatrix} = \begin{bmatrix} 0 \\ 0 \end{bmatrix}")
            
            st.write("**4. KVL en forma matricial**")
            st.latex(r"v = A^T \cdot e")
            st.latex(r"\begin{bmatrix} v_{V1} \\ v_{R1} \\ v_{C1} \end{bmatrix} = \begin{bmatrix} 1 & 0 \\ -1 & 1 \\ 0 & -1 \end{bmatrix} \begin{bmatrix} V_{N1} \\ V_{N2} \end{bmatrix}")
            st.write("**Interpretacion explicita:**")
            st.latex(r"v_{V1} = V_{N1} - 0 = V_{N1} \quad [V]")
            st.latex(r"v_{R1} = V_{N1} - V_{N2} \quad [V]")
            st.latex(r"v_{C1} = V_{N2} - 0 = V_{N2} \quad [V]")
            
            st.write("**5. Relaciones de los Componentes (BR) en dominio tiempo**")
            st.latex(r"\text{Fuente V1:} \quad v_{V1} = V_{in} \quad [V]")
            st.latex(r"\text{Resistencia R1:} \quad v_{R1} = R \cdot i_{R1} \quad [V]")
            st.latex(r"\text{Capacitor C1:} \quad i_{C1} = C \cdot \frac{d v_{C1}}{dt} \quad [A]")
            st.write("")
            st.write("**Forma integral equivalente del capacitor:**")
            st.latex(r"v_{C1}(t) = \frac{1}{C} \int_{0}^{t} i_{C1}(\tau) d\tau + v_{C1}(0) \quad [V]")
            
            st.write("**6. Estructura del Metodo de Tablueau (Forma Estandar)**")
            st.latex(r"\begin{bmatrix} A & 0 & 0 \\ 0 & I & -I \\ A^T & 0 & -Z \end{bmatrix} \begin{bmatrix} e \\ i \\ v \end{bmatrix} = \begin{bmatrix} 0 \\ 0 \\ V_s \end{bmatrix}")
            
            st.write("**7. Vector Vs (Fuentes de voltaje)**")
            st.latex(r"V_s = \begin{bmatrix} V_{in} \\ 0 \\ 0 \end{bmatrix}")
            st.caption("**Mapeo:** Rama 1 (V1) → Fuente de voltaje Vin | Ramas 2 y 3 → 0")
            
            st.write("**8. Ecuacion Diferencial del Circuito (dominio tiempo)**")
            st.latex(rf"{Vin:.1f} - V_C = {R:.0f} \cdot {C:.0e} \cdot \frac{{dV_C}}{{dt}} \quad [V]")
            st.latex(rf"\frac{{dV_C}}{{dt}} + \frac{{1}}{{{tau:.4f}}} V_C = \frac{{{Vin:.1f}}}{{{tau:.4f}}} \quad [V/s]")
            
            st.write("**9. Variable de Estado**")
            st.latex(r"x(t) = V_C(t) \quad [V]")
            
            st.write("**10. Ecuacion de Estado**")
            a = -1/tau
            b = Vin/tau
            st.latex(rf"\dot{{x}} = -\frac{{1}}{{RC}} x + \frac{{V_{{in}}}}{{RC}}")
            st.latex(rf"\dot{{x}} = {a:.4f} x + {b:.4f} \quad [V/s]")
            
            st.write("**11. Clasificacion del Sistema**")
            st.write(f"- **Orden:** Sistema de primer orden")
            st.write(f"- **Linealidad:** Lineal")
            st.write(f"- **Invarianza:** Invariante en el tiempo")
            
            st.write("**12. Interpretacion Fisica**")
            st.markdown(f"""
            - **Carga del capacitor:** Se carga desde 0 V hasta {Vin:.1f} V
            - **Regimen transitorio:** Dura {5*tau:.2f} s (5τ)
            - **Constante de tiempo:** τ = {tau:.4f} s
            """)
            
            st.write("**13. Solucion Analitica**")
            st.latex(f"V_C(t) = {Vin:.1f} \\cdot (1 - e^{{-t/{tau:.4f}}}) \\quad [V]")
            
        else:
            st.subheader("Circuito no RC")
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
            matlab_code = f"""%% Circuito RC
clear; clc; close all;

%% Parametros
R = {R:.10f}; C = {C:.10f}; Vin = {Vin:.10f};
tau = R*C;

%% Variable de estado
syms Vc(t)
eq = diff(Vc, t) == -1/tau*Vc + Vin/tau;
cond = Vc(0) == 0;
Vc_sol = dsolve(eq, cond);

%% Resultados
disp('Vc(t) = '); pretty(Vc_sol);
fprintf('tau = %.4f s\\n', tau);

%% Grafica
figure;
fplot(Vc_sol, [0 5*tau], 'LineWidth', 2);
xlabel('t (s)'); ylabel('Vc(t) (V)');
title('Respuesta del Circuito RC');
grid on;
hold on;
plot([0 5*tau], [Vin Vin], '--r');
legend('Vc(t)', 'Vin');
"""
        else:
            matlab_code = "%% Circuito General\nclear; clc;\n% Agregar ecuaciones manualmente\n"
        
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

with col5:
with st.expander("Validar Circuito", expanded=False):
    if st.button("Ejecutar Validacion", key="validar"):
        if not st.session_state.componentes:
            st.warning("Agrega componentes")
        else:
            hay_tierra = any(c['nodo_origen'] == "N0" or c['nodo_destino'] == "N0" for c in st.session_state.componentes)
            if not hay_tierra:
                st.error("No hay nodo de referencia (N0)")
            else:
                st.success("Circuito valido")

with col6:
with st.expander("Matriz de Incidencia A", expanded=False):
    st.write("**Matriz A (UNICA)**")
    st.latex(r"A = \begin{bmatrix} 1 & -1 & 0 \\ 0 & 1 & -1 \end{bmatrix}")
    st.caption("+1 sale, -1 entra | Orden: [V1, R1, C1]")

with col7:
with st.expander("Metodo de Tablueau", expanded=False):
    st.write("**Forma estandar:**")
    st.latex(r"\begin{bmatrix} A & 0 & 0 \\ 0 & I & -I \\ A^T & 0 & -Z \end{bmatrix} \begin{bmatrix} e \\ i \\ v \end{bmatrix} = \begin{bmatrix} 0 \\ 0 \\ V_s \end{bmatrix}")
    st.write("**Para circuito RC:**")
    st.latex(r"e = \begin{bmatrix} V_{N1} \\ V_{N2} \end{bmatrix},\quad i = \begin{bmatrix} i_{V1} \\ i_{R1} \\ i_{C1} \end{bmatrix},\quad v = \begin{bmatrix} v_{V1} \\ v_{R1} \\ v_{C1} \end{bmatrix}")

# ---------- INFORMACION ADICIONAL ----------
with st.sidebar.expander("Instrucciones"):
st.markdown("""
### Como usar:
1. Agrega componentes individualmente o carga un netlist
2. Usa N0 como tierra
3. Ejemplo netlist:
