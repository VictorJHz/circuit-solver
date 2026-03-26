def clasificar_circuito(componentes):
    """Clasifica el circuito segun sus componentes"""
    tiene_resistencia = any(c['tipo'] == "Resistencia" for c in componentes)
    tiene_capacitor = any(c['tipo'] == "Capacitor" for c in componentes)
    tiene_inductor = any(c['tipo'] == "Inductor" for c in componentes)
    tiene_fuente_v = any(c['tipo'] == "Fuente de Voltaje" for c in componentes)
    tiene_fuente_i = any(c['tipo'] == "Fuente de Corriente" for c in componentes)
    
    tiene_fuente = tiene_fuente_v or tiene_fuente_i
    
    if tiene_capacitor or tiene_inductor:
        tipo = "Dinamico"
        
        # Contar elementos para orden
        orden = sum(1 for c in componentes if c['tipo'] in ["Capacitor", "Inductor"])
        
        # Determinar subtipo basado en componentes presentes
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
    # Contar componentes
    num_res = sum(1 for c in componentes if c['tipo'] == "Resistencia")
    num_cap = sum(1 for c in componentes if c['tipo'] == "Capacitor")
    num_fuente_v = sum(1 for c in componentes if c['tipo'] == "Fuente de Voltaje")
    num_fuente_i = sum(1 for c in componentes if c['tipo'] == "Fuente de Corriente")
    
    # Un RC valido debe tener exactamente: 1R, 1C, 1V (sin fuentes de corriente)
    if num_res != 1 or num_cap != 1 or num_fuente_v != 1 or num_fuente_i != 0:
        return False
    
    # Obtener los componentes
    R = next(c for c in componentes if c['tipo'] == "Resistencia")
    C = next(c for c in componentes if c['tipo'] == "Capacitor")
    V = next(c for c in componentes if c['tipo'] == "Fuente de Voltaje")
    
    # Verificar que estan conectados en serie
    # Buscar nodos comunes entre componentes
    nodos_R = {R['nodo_origen'], R['nodo_destino']}
    nodos_C = {C['nodo_origen'], C['nodo_destino']}
    nodos_V = {V['nodo_origen'], V['nodo_destino']}
    
    # En un circuito serie, deben compartir nodos formando una cadena
    # Verificar que los tres componentes forman una unica cadena cerrada
    # Usando NetworkX para verificar conectividad
    import networkx as nx
    G = nx.Graph()
    
    for comp in [R, C, V]:
        G.add_edge(comp['nodo_origen'], comp['nodo_destino'])
    
    # Verificar que todos los nodos estan conectados (un solo componente conexo)
    if nx.number_connected_components(G) != 1:
        return False
    
    # Verificar que hay exactamente 3 nodos (circuito serie simple)
    nodos = set()
    for comp in [R, C, V]:
        nodos.add(comp['nodo_origen'])
        nodos.add(comp['nodo_destino'])
    
    # Un circuito serie simple debe tener 3 nodos (ej: N0-N1, N1-N2, N2-N0)
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
    
    import networkx as nx
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
    
    import networkx as nx
    G = nx.Graph()
    
    for comp in [R, L, C, V]:
        G.add_edge(comp['nodo_origen'], comp['nodo_destino'])
    
    if nx.number_connected_components(G) != 1:
        return False
    
    nodos = set()
    for comp in [R, L, C, V]:
        nodos.add(comp['nodo_origen'])
        nodos.add(comp['nodo_destino'])
    
    # Circuito serie RLC debe tener 3 nodos (cadena cerrada)
    if len(nodos) != 3:
        return False
    
    return True

def generar_reporte_dinamico(componentes, subtipo, orden):
    """Genera reporte para circuitos dinamicos (RC, RL, RLC)"""
    st.subheader(f"📐 Analisis de Circuito Dinamico - Tipo: {subtipo}")
    st.write(f"**Orden del sistema:** {orden}")
    
    # Detectar componentes especificos
    R_val = None
    C_val = None
    L_val = None
    Vin_val = None
    Iin_val = None
    
    for c in componentes:
        if c['tipo'] == "Resistencia":
            R_val = c['valor_total']
        elif c['tipo'] == "Capacitor":
            C_val = c['valor_total']
        elif c['tipo'] == "Inductor":
            L_val = c['valor_total']
        elif c['tipo'] == "Fuente de Voltaje":
            Vin_val = c['valor_total']
        elif c['tipo'] == "Fuente de Corriente":
            Iin_val = c['valor_total']
    
    # ========== CASO RC VALIDO (topologia correcta) ==========
    if subtipo == "RC" and verificar_circuito_rc_valido(componentes):
        tau = R_val * C_val
        generar_reporte_rc(R_val, C_val, Vin_val, tau)
    
    # ========== CASO RL VALIDO ==========
    elif subtipo == "RL" and verificar_circuito_rl_valido(componentes):
        tau = L_val / R_val
        generar_reporte_rl(R_val, L_val, Vin_val, tau)
    
    # ========== CASO RLC VALIDO ==========
    elif subtipo == "RLC" and verificar_circuito_rlc_valido(componentes):
        generar_reporte_rlc(R_val, L_val, C_val, Vin_val)
    
    else:
        # Caso general dinamico (circuito con C y/o L pero no es el caso simple)
        st.info("Circuito dinamico general - analisis basico (no es un caso simple RC/RL/RLC serie)")
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
        
        # Generar ecuaciones KCL
        st.write("**KCL - Ley de Corrientes de Kirchhoff:**")
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
        
        # Generar BR
        st.write("**BR - Relaciones de los Componentes:**")
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
