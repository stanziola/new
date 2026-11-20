import numpy as np
import pint
from interaccion_graficas import graficar_c

ureg = pint.UnitRegistry()

# datos

h = 50 * ureg.cm    
b = 50 * ureg.cm
n_y = 3
n_x = 3
e_module_steel = 29000 * ureg.ksi
f_y = 60000 * ureg.psi
no_barra = 6
no_estribo= 3
recubrimiento = 4 * ureg.cm
fc = 5000 * ureg.psi

# funciones

def beta1(fc):
    if fc < 2500 * ureg.psi:
        raise ValueError("fc debe ser mayor o igual a 2500 psi")
    elif fc <= 4000 * ureg.psi:
        return 0.85
    elif fc <= 8000 * ureg.psi:
        return 0.85 - 0.05 * ((fc.to(ureg.psi).magnitude - 4000) / 1000)
    else:
        return 0.65

def m_rot(ang):
    c, s = np.cos(np.radians(ang)), np.sin(np.radians(ang))
    return np.array([[c, -s],
                     [s,  c]])

def a_s(no_barra):
    return (no_barra/8)**2*(np.pi/4) * ureg.inch**2

def d_s(no_barra):
    return 2*(a_s(no_barra)/np.pi)**0.5

# programa

if __name__ == "__main__":
    d_prima = recubrimiento + d_s(no_estribo) + d_s(no_barra)/2
    s_y = (h-2*d_prima)/(n_y-1)
    s_x = (b-2*d_prima)/(n_x-1)
    n_xy = 2*(n_x + n_y - 2)
    epsilon_y = (f_y/e_module_steel).to("dimensionless").magnitude
    r_barra = d_s(no_barra)/2

    b_cm = b.to(ureg.cm).magnitude
    h_cm = h.to(ureg.cm).magnitude
    seccion = np.array([[-b_cm/2, -h_cm/2],
                        [ b_cm/2, -h_cm/2],
                        [ b_cm/2,  h_cm/2],
                        [-b_cm/2,  h_cm/2],
                        [-b_cm/2, -h_cm/2]])

    c = np.zeros((361,30))

    for ang in range(0, 361):
        x_max = (seccion @ m_rot(ang).T)[:, 0].max()

        for i in range(0,16):
            c[ang,i] = x_max*0.9999 - x_max*2*(i)/15
        for i in range(16,26):
            c[ang,i] = c[ang,15] - x_max*2/5*(i-15)
        for i in range(26,30):
            c[ang,i] = c[ang,25] - x_max*4/5*(i-25)

    graficar_c(seccion, c, b_cm, h_cm, m_rot)
