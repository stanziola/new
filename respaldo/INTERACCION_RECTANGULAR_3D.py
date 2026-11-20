import numpy as np
import pint
from interaccion_graficas import graficar_c

ureg = pint.UnitRegistry()

# datos de seccion

h = 60 * ureg.cm    
b = 45 * ureg.cm
n_y = 3
n_x = 4
e_module_steel = 29000 * ureg.ksi
f_y = 60000 * ureg.psi
no_barra = 6
no_estribo= 3
recubrimiento = 4 * ureg.cm
fc = 5000 * ureg.psi

#CONFIGURACION DE C

n1, n2, n3 = 60, 25, 15          
n_c = n1 + n2 + n3

#FUNCIONES

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

def agregar_punto(lista, punto):
    if len(lista) == 0 or lista[-1] != punto:
        lista.append(punto)

#PROGRAMA

if __name__ == "__main__":
    #CALCULOS DE SECCION
    d_prima = recubrimiento + d_s(no_estribo) + d_s(no_barra)/2
    s_y = (h-2*d_prima)/(n_y-1)
    s_x = (b-2*d_prima)/(n_x-1)
    n_xy = 2*(n_x + n_y - 2)
    epsilon_y = (f_y/e_module_steel).to("dimensionless").magnitude
    r_barra = d_s(no_barra)/2

    b_cm = b.to(ureg.cm).magnitude
    h_cm = h.to(ureg.cm).magnitude
    d_prima_cm = d_prima.to(ureg.cm).magnitude
    s_x_cm = s_x.to(ureg.cm).magnitude
    s_y_cm = s_y.to(ureg.cm).magnitude

    seccion = np.array([[-b_cm/2, -h_cm/2],
                        [ b_cm/2, -h_cm/2],
                        [ b_cm/2,  h_cm/2],
                        [-b_cm/2,  h_cm/2],
                        [-b_cm/2, -h_cm/2]])

    contador_barra_acero = 0
    barra_acero = np.zeros((n_xy,2))

    #CALCULO DE POSICION DE BARRAS  
    for n_xi in range (0, n_x):
            for n_yi in range (0, n_y):
                if n_xi == 0 or n_xi == (n_x-1) or n_yi == 0 or n_yi == (n_y-1):
                    barra_acero[contador_barra_acero,0] = d_prima_cm + s_x_cm*(n_xi)-b_cm/2
                    barra_acero[contador_barra_acero,1] = d_prima_cm + s_y_cm*(n_yi)-h_cm/2
                    contador_barra_acero += 1

    #DEFINICION DE MATRICES
    c = np.zeros((361,n_c))
    a = np.zeros((361,n_c))
    seccion_girada = np.zeros((361, 5, 2))
    barras_giradas = np.zeros((361, n_xy, 2))
    coord_comp_todas = np.full((361, n_c, 6, 2), np.nan)
    n_comp = np.zeros((361, n_c), dtype=int)
    beta_1 = beta1(fc)
    area_comp = 0
    centroide_x_comp = 0
    centroide_y_comp = 0
    a_barra_cm2 = a_s(no_barra).to(ureg.cm**2).magnitude
    centroide_comp = np.zeros((361, n_c, 2))
    epsilon_s = np.zeros((361, n_c, n_xy))
    epsilon_t = np.zeros((361, n_c))
    fc_kgcm2 = fc.to(ureg.kgf/ureg.cm**2).magnitude
    es_kgcm2 = e_module_steel.to(ureg.kgf/ureg.cm**2).magnitude
    P_n = np.zeros((361, n_c))
    M_nx = np.zeros((361, n_c))
    M_ny = np.zeros((361, n_c))
    phi = np.zeros((361, n_c))

    for ang in range(0, 361):
        #CALCULO DE BARRAS Y SECCION ROTADAS
        seccion_girada[ang] = seccion @ m_rot(ang).T
        barras_giradas[ang] = barra_acero @ m_rot(ang).T
        x_max = seccion_girada[ang, :, 0].max()

        #CALCULO DE C
        for i in range(0, n1):
            c[ang,i] = x_max*0.9999 - x_max*2*(i)/(n1-1)
            a[ang,i] = beta_1*(x_max - c[ang,i])
        for i in range(n1, n1+n2):
            c[ang,i] = c[ang,n1-1] - x_max*4/n2*(i-(n1-1))
            a[ang,i] = beta_1*(x_max - c[ang,i])
        for i in range(n1+n2, n_c):
            c[ang,i] = c[ang,n1+n2-1] - x_max*3.2/n3*(i-(n1+n2-1))
            a[ang,i] = beta_1*(x_max - c[ang,i])

        for i in range(n_c):
            #CALCULO DE AREA EN COMPRESION
            coord_comp = []
            x_corte = x_max - a[ang,i]
            for coord_comp_i in range (0, len(seccion_girada[ang])-1):
                x_i = seccion_girada[ang,coord_comp_i,0]
                x_f = seccion_girada[ang,coord_comp_i+1,0]
                y_i = seccion_girada[ang,coord_comp_i,1]
                y_f = seccion_girada[ang,coord_comp_i+1,1]
                if x_i >= x_corte and x_f >= x_corte:
                    agregar_punto(coord_comp, [x_i, y_i])
                    agregar_punto(coord_comp, [x_f, y_f])
                elif x_i >= x_corte and x_f <= x_corte:
                    y_m = ((y_f-y_i)/(x_f-x_i))*(x_corte-x_i)+y_i
                    agregar_punto(coord_comp, [x_i, y_i])
                    agregar_punto(coord_comp, [x_corte, y_m])
                elif x_i <= x_corte and x_f >= x_corte:
                    y_m = ((y_f-y_i)/(x_f-x_i))*(x_corte-x_i)+y_i
                    agregar_punto(coord_comp, [x_corte, y_m])
                    agregar_punto(coord_comp, [x_f, y_f])
            if coord_comp[0] != coord_comp[-1]:
                coord_comp.append(coord_comp[0])
            n = len(coord_comp)
            n_comp[ang, i] = n
            coord_comp_todas[ang, i, :n] = coord_comp

            #CALCULO DE CENTROIDE
            area_comp = 0
            centroide_x_comp = 0
            centroide_y_comp = 0
            for coord_i in range(0, n-1):
                x_i, y_i = coord_comp[coord_i]
                x_ii, y_ii = coord_comp[coord_i+1]
                cruz = x_i*y_ii - x_ii*y_i
                area_comp += cruz/2
                centroide_x_comp += (x_i + x_ii)*cruz
                centroide_y_comp += (y_i + y_ii)*cruz
            centroide_x_comp = centroide_x_comp/(6*area_comp)
            centroide_y_comp = centroide_y_comp/(6*area_comp)
            centroide_comp[ang, i] = [centroide_x_comp, centroide_y_comp]

            #CALCULO DE DEFORMACIONES DEL ACERO
            for barra_i in range(0, n_xy):
                x_barra = barras_giradas[ang, barra_i, 0]
                epsilon_si = 0.003*(x_barra - c[ang,i])/(x_max - c[ang,i])
                epsilon_s[ang, i, barra_i] = min(max(epsilon_si, -epsilon_y), epsilon_y)

            #CALCULO DE PN, MNX Y MNY
            C_c = 0.85*fc_kgcm2*area_comp
            P_n[ang, i] = C_c
            M_nx[ang, i] = C_c*centroide_x_comp
            M_ny[ang, i] = C_c*centroide_y_comp
            for barra_i in range(0, n_xy):
                f_si = epsilon_s[ang, i, barra_i]*es_kgcm2
                if barras_giradas[ang, barra_i, 0] >= x_corte:
                    f_si = f_si - 0.85*fc_kgcm2
                F_si = f_si*a_barra_cm2
                P_n[ang, i] += F_si
                M_nx[ang, i] += F_si*barras_giradas[ang, barra_i, 0]
                M_ny[ang, i] += F_si*barras_giradas[ang, barra_i, 1]
                
            #CALCULO DE EPSILON T
            x_barra_min = barras_giradas[ang, :, 0].min()
            epsilon_t[ang, i] = -0.003*(x_barra_min - c[ang,i])/(x_max - c[ang,i])

            #CALCULO DE PHI
            if epsilon_t[ang, i] <= epsilon_y:
                phi[ang, i] = 0.65
            elif epsilon_t[ang, i] >= epsilon_y + 0.003:
                phi[ang, i] = 0.90
            else:
                phi[ang, i] = 0.65 + 0.25*(epsilon_t[ang, i] - epsilon_y)/0.003

    P_n = P_n/1000
    M_nx = M_nx/100000
    M_ny = M_ny/100000

    #CALCULO DE PN MAX
    f_y_kgcm2 = f_y.to(ureg.kgf/ureg.cm**2).magnitude
    A_st = n_xy*a_barra_cm2
    P_o = (0.85*fc_kgcm2*(b_cm*h_cm - A_st) + f_y_kgcm2*A_st)/1000
    P_n_max = 0.80*P_o
    phi_P_n = np.minimum(phi*P_n, 0.65*P_n_max)
    phi_M_nx = phi*M_nx
    phi_M_ny = phi*M_ny

    #MOMENTOS EN LOS EJES DE LA SECCION
    phi_M_x = np.zeros((361, n_c))
    phi_M_y = np.zeros((361, n_c))
    for ang in range(0, 361):
        coseno = np.cos(np.radians(ang))
        seno = np.sin(np.radians(ang))
        phi_M_x[ang] = phi_M_nx[ang]*coseno + phi_M_ny[ang]*seno
        phi_M_y[ang] = -phi_M_nx[ang]*seno + phi_M_ny[ang]*coseno

    graficar_c(seccion_girada, barras_giradas, r_barra.to(ureg.cm).magnitude, c, b_cm, h_cm, coord_comp_todas, n_comp, centroide_comp)
