"""Capítulo: Secciones de acero (calculo/acero.py). Fórmulas y código."""
from calculo import acero


def capitulo(m):
    m.titulo("Secciones de acero")
    m.parrafo("Propiedades de las secciones de acero para el análisis: tubo circular y perfil I. Código: "
              "`calculo/acero.py`, en m y kN/m².")

    m.titulo("Material", 2)
    m.ecuacion(r"G = \frac{E}{2 \left( 1 + \nu \right)}")
    m.parrafo("$E$ y $\\nu$ son datos del usuario (por defecto 200 000 MPa y 0.3). Peso unitario por defecto: "
              "492 lb/ft³ = 77.29 kN/m³.")
    m.parrafo("ASCE 7-05, Tabla C3-2, \"Steel, cold-drawn\" (PDF p. 295).").style = "Cita"
    m.codigo(acero.modulo_cortante)

    m.titulo("Tubo circular", 2)
    m.ecuacion(r"d = D - 2t, \quad A = \frac{\pi \left( D^2 - d^2 \right)}{4}, \quad "
               r"I_y = I_z = \frac{\pi \left( D^4 - d^4 \right)}{64}, \quad J = 2 I")
    m.codigo(acero.propiedades_tubo)

    m.titulo("Perfil I", 2)
    m.parrafo("Peralte $d$ en el eje local $z$ y alas de ancho $b_f$ en el local $y$ (como $h$ y $b$ del concreto): "
              "en vigas y columnas, $I_y$ es la inercia fuerte. Sin filetes.")
    m.ecuacion(r"A = 2 b_f t_f + \left( d - 2 t_f \right) t_w")
    m.ecuacion(r"I_y = \frac{b_f d^3 - \left( b_f - t_w \right) \left( d - 2 t_f \right)^3}{12}, \quad "
               r"I_z = \frac{2 t_f b_f^3}{12} + \frac{\left( d - 2 t_f \right) t_w^3}{12}")
    m.ecuacion(r"J \approx \frac{2 b_f t_f^3 + \left( d - t_f \right) t_w^3}{3}")
    m.codigo(acero.propiedades_perfil_i)

    m.titulo("Limitaciones", 2)
    m.lista([
        "Perfil I sin los filetes del laminado: A e I quedan algo menores que las de las tablas (como en Ftool).",
        "J del perfil I por rectángulos delgados (aproximada).",
        "Solo propiedades para el análisis: todavía sin diseño de acero (AISC 360 no está en las normas del proyecto).",
    ])
