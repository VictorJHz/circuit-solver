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
        else:
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
        
        primero = parts[0]
        
        if primero and primero[0] in tipo_por_letra:
            letra = primero[0]
            nombre = primero[1:] if len(primero) > 1 else primero
            tipo = tipo_por_letra[letra]
            
            if not nombre:
                nombre = primero
            
            nodo_origen = parts[1] if len(parts) > 1 else None
            nodo_destino = parts[2] if len(parts) > 2 else None
            
            # 🔧 FIX AQUI
            valor_str = parts[-1]
            
        else:
            letra = parts[0]
            if letra not in tipo_por_letra:
                errores.append(f"Linea {line_num}: Tipo '{letra}' no reconocido")
                continue
            tipo = tipo_por_letra[letra]
            nombre = parts[1] if len(parts) > 1 else None
            nodo_origen = parts[2] if len(parts) > 2 else None
            nodo_destino = parts[3] if len(parts) > 3 else None
            valor_str = parts[4] if len(parts) > 4 else None
        
        if not nombre:
            errores.append(f"Linea {line_num}: Falta nombre")
            continue
        if not nodo_origen or not nodo_destino:
            errores.append(f"Linea {line_num}: Faltan nodos")
            continue
        if not valor_str:
            errores.append(f"Linea {line_num}: Falta valor")
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

# ---------- (EL RESTO DE TU CÓDIGO SIGUE IGUAL SIN CAMBIOS) ----------
