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
            st.warning("Agrega componentes")
        else:
            # Mostrar componentes para depuración
            st.write("**Componentes detectados:**")
            for c in st.session_state.componentes:
                st.write(f"- {c['nombre']}: {c['tipo']} = {c['valor']}{c['prefijo']}{c['unidad']}")
            
            # Clasificar el circuito
            tipo_sistema, subtipo, orden = clasificar_circuito(st.session_state.componentes)
            
            st.info(f"**Tipo de sistema:** {tipo_sistema} | **Subtipo:** {subtipo} | **Orden:** {orden}")
            
            if tipo_sistema == "Estatico":
                generar_reporte_estatico(st.session_state.componentes)
            else:
                generar_reporte_dinamico(st.session_state.componentes, subtipo, orden)

with col3:
    if st.button("Codigo MATLAB", key="matlab"):
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
                    code = f"""% Circuito RC - Analisis Completo
clear; clc; close all;

R = {R:.6f}; C = {C:.6f}; Vin = {Vin:.6f}; tau = R*C;

syms Vc(t)
eq = diff(Vc, t) == -1/tau * Vc + Vin/tau;
cond = Vc(0) == 0;
Vc_sol = dsolve(eq, cond);

disp('=== SOLUCION DEL CIRCUITO RC ===');
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
                    st.download_button("Descargar codigo MATLAB", code, "circuito_rc.m", key="descargar_matlab")
                else:
                    st.info("No se detecto un circuito RC valido")
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
                    code = f"""% Circuito RL - Analisis Completo
clear; clc; close all;

R = {R:.6f}; L = {L:.6f}; Vin = {Vin:.6f}; tau = L/R;

syms iL(t)
eq = diff(iL, t) == -1/tau * iL + Vin/L;
cond = iL(0) == 0;
iL_sol = dsolve(eq, cond);

disp('=== SOLUCION DEL CIRCUITO RL ===');
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
                    st.download_button("Descargar codigo MATLAB", code, "circuito_rl.m", key="descargar_matlab")
                else:
                    st.info("No se detecto un circuito RL valido")
            else:
                st.info("Circuito no compatible con generacion automatica de codigo MATLAB")

with col4:
    if st.button("Limpiar Todo", key="limpiar_todo"):
        st.session_state.componentes = []
        st.rerun()
