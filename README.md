# ⚡ Circuit Solver

![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

## 📌 Descripción

**Circuit Solver** es una herramienta educativa interactiva para el análisis de circuitos eléctricos lineales. Permite a los estudiantes y profesionales:

- Construir circuitos de forma intuitiva agregando componentes
- Visualizar la topología del circuito con polaridad y direcciones de corriente
- Generar automáticamente las ecuaciones KCL, KVL y BR
- Realizar análisis nodal con matriz de conductancias
- Exportar código MATLAB para resolver el sistema simbólicamente
- Validar la estructura del circuito y detectar errores comunes

Desarrollado con **Streamlit**, esta aplicación está optimizada para funcionar tanto en computadoras como en dispositivos móviles.

---

## ✨ Características principales

| Característica | Descripción |
|----------------|-------------|
| **Agregar componentes** | Resistencias, capacitores, inductores, fuentes de voltaje y corriente |
| **Grafo del circuito** | Visualización con colores por tipo de componente y direcciones de corriente |
| **Ecuaciones KCL** | Ley de corrientes de Kirchhoff para cada nodo |
| **Ecuaciones BR** | Relaciones constitutivas de cada componente |
| **Análisis Nodal** | Matriz de conductancias G y vector de corrientes I |
| **Sistema completo** | Visualización de todas las ecuaciones (KCL + BR) |
| **Validación** | Detección de errores: falta de tierra, nombres duplicados, valores inválidos |
| **Exportación MATLAB** | Código listo para ejecutar en MATLAB |

---

## 🚀 Cómo usar

### Opción 1: Demo en línea (Streamlit Cloud)
Próximamente disponible en: `https://circuit-solver.streamlit.app`

### Opción 2: Ejecutar localmente

**Requisitos:**
- Python 3.8 o superior
- pip

**Instalación:**
```bash
# Clonar el repositorio
git clone https://github.com/tu-usuario/circuit-solver.git
cd circuit-solver

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar la aplicación
streamlit run circuit_solver.py
