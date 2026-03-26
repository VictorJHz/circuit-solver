with b2:
    if st.button("Generar Ecuaciones", key="generar_eq"):
        if not st.session_state.componentes:
            st.warning("Agrega componentes")
        else:
            # Clasificar el circuito
            tipo_sistema, subtipo, orden = clasificar_circuito(st.session_state.componentes)
            
            st.info(f"**Tipo de sistema:** {tipo_sistema} | **Subtipo:** {subtipo} | **Orden:** {orden}")
            
            if tipo_sistema == "Estatico":
                generar_reporte_estatico(st.session_state.componentes)
            else:
                generar_reporte_dinamico(st.session_state.componentes, subtipo, orden)

with b3:
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

with b4:
    if st.button("Limpiar Todo", key="limpiar_todo"):
        st.session_state.componentes = []
        st.rerun()
