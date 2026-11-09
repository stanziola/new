import numpy as np
from configuracion.calculo import TOL_LONGITUD

def k_local(e, g, a, l, iy, iz, j):
    return (e / l**3) * np.array([
        [ a*l**2,     0,        0,        0,           0,          0,         -a*l**2,     0,        0,        0,           0,          0        ],
        [ 0,          12*iz,    0,        0,           0,          6*l*iz,     0,         -12*iz,    0,        0,           0,          6*l*iz   ],
        [ 0,          0,        12*iy,    0,          -6*l*iy,     0,          0,          0,       -12*iy,    0,          -6*l*iy,     0        ],
        [ 0,          0,        0,        g*j*l**2/e,  0,          0,          0,          0,        0,       -g*j*l**2/e,  0,          0        ],
        [ 0,          0,       -6*l*iy,   0,           4*l**2*iy,  0,          0,          0,        6*l*iy,   0,           2*l**2*iy,  0        ],
        [ 0,          6*l*iz,   0,        0,           0,          4*l**2*iz,  0,         -6*l*iz,   0,        0,           0,          2*l**2*iz],
        [-a*l**2,     0,        0,        0,           0,          0,          a*l**2,     0,        0,        0,           0,          0        ],
        [ 0,         -12*iz,    0,        0,           0,         -6*l*iz,     0,          12*iz,    0,        0,           0,         -6*l*iz   ],
        [ 0,          0,       -12*iy,    0,           6*l*iy,     0,          0,          0,        12*iy,    0,           6*l*iy,     0        ],
        [ 0,          0,        0,       -g*j*l**2/e,  0,          0,          0,          0,        0,        g*j*l**2/e,  0,          0        ],
        [ 0,          0,       -6*l*iy,   0,           2*l**2*iy,  0,          0,          0,        6*l*iy,   0,           4*l**2*iy,  0        ],
        [ 0,          6*l*iz,   0,        0,           0,          2*l**2*iz,  0,         -6*l*iz,   0,        0,           0,          4*l**2*iz],
    ], dtype=float)

def angulos(nodo_i, nodo_f):
    dx = nodo_f[0] - nodo_i[0]
    dy = nodo_f[1] - nodo_i[1]
    dz = nodo_f[2] - nodo_i[2]
    l = np.sqrt(dx**2 + dy**2 + dz**2)
    if l < TOL_LONGITUD:
        raise ValueError("Barra de longitud 0")
    gamma = np.arctan2(dy, dx)
    beta = -np.arctan2(dz, np.sqrt(dx**2 + dy**2))   # negativo por la convención de B
    return beta, gamma, l

def rotacion(alfa, beta, gamma):
    ca, sa = np.cos(alfa), np.sin(alfa)
    cb, sb = np.cos(beta), np.sin(beta)
    cg, sg = np.cos(gamma), np.sin(gamma)

    A = np.array([[1,   0,   0],
                  [0,  ca,  sa],
                  [0, -sa,  ca]])

    B = np.array([[cb, 0, -sb],
                  [0,  1,   0],
                  [sb, 0,  cb]])

    C = np.array([[ cg, sg, 0],
                  [-sg, cg, 0],
                  [  0,  0, 1]])

    return A @ B @ C

def transformacion(r):
    t = np.zeros((12, 12))
    for k in range(4):
        t[3*k:3*k+3, 3*k:3*k+3] = r
    return t

def k_global_barra(e, g, a, iy, iz, j, nodo_i, nodo_f, alfa=0.0):
    beta, gamma, l = angulos(nodo_i, nodo_f)
    r = rotacion(alfa, beta, gamma)
    t = transformacion(r)
    return t.T @ k_local(e, g, a, l, iy, iz, j) @ t