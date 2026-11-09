"""Matemática del giro animado de la cámara (solo numpy: se puede probar sin abrir ventanas).

Una cámara se describe con tres vectores: posición, foco (el punto al que mira) y "arriba".
Su orientación es una matriz de rotación, igual que la R de las barras: sus columnas son los ejes
de la cámara (derecha, arriba y atrás) escritos en ejes globales.

Para girar suavemente de una orientación a otra no se interpolan los vectores por separado: en un
giro de 180° (de la vista de arriba a la de abajo) el promedio de las dos direcciones es cero y no
sirve, y el "arriba" se tuerce. En cambio, cada matriz se pasa a un cuaternión y se usa slerp
(interpolación esférica): la cámara gira alrededor de un solo eje a velocidad constante.
"""
import numpy as np


def marco_camara(posicion, foco, arriba):
    """Matriz 3x3 con columnas [derecha, arriba, atrás]; atrás va del foco hacia la cámara."""
    atras = np.asarray(posicion, dtype=float) - np.asarray(foco, dtype=float)
    atras /= np.linalg.norm(atras)
    arriba = np.asarray(arriba, dtype=float)
    arriba = arriba - (arriba @ atras) * atras  # se quita la parte paralela a "atrás"
    arriba /= np.linalg.norm(arriba)
    derecha = np.cross(arriba, atras)           # ejes de mano derecha: det = +1
    return np.column_stack([derecha, arriba, atras])


def a_cuaternion(R):
    """Cuaternión unitario (w, x, y, z) de una matriz de rotación."""
    traza = np.trace(R)
    if traza > 0:                               # caso normal
        s = 2.0 * np.sqrt(traza + 1.0)
        q = [0.25 * s, (R[2, 1] - R[1, 2]) / s, (R[0, 2] - R[2, 0]) / s, (R[1, 0] - R[0, 1]) / s]
    else:                                       # giros cercanos a 180°: se parte del mayor de la diagonal
        i = int(np.argmax(np.diag(R)))
        j, k = (i + 1) % 3, (i + 2) % 3
        s = 2.0 * np.sqrt(1.0 + R[i, i] - R[j, j] - R[k, k])
        q = np.zeros(4)
        q[0] = (R[k, j] - R[j, k]) / s
        q[1 + i] = 0.25 * s
        q[1 + j] = (R[j, i] + R[i, j]) / s
        q[1 + k] = (R[k, i] + R[i, k]) / s
    q = np.asarray(q, dtype=float)
    return q / np.linalg.norm(q)


def a_matriz(q):
    """Matriz de rotación de un cuaternión unitario (w, x, y, z)."""
    w, x, y, z = q
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
        [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
        [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
    ])


def slerp(q0, q1, t):
    """Interpolación esférica entre dos cuaterniones unitarios (t = 0 da q0; t = 1 da q1)."""
    q0, q1 = np.asarray(q0, dtype=float), np.asarray(q1, dtype=float)
    coseno = q0 @ q1
    if coseno < 0:                              # q y -q son el mismo giro: se toma el camino corto
        q1, coseno = -q1, -coseno
    if coseno > 0.9995:                         # casi iguales: lineal, para no dividir entre sen(0)
        q = q0 + t * (q1 - q0)
        return q / np.linalg.norm(q)
    angulo = np.arccos(coseno)
    return (np.sin((1 - t) * angulo) * q0 + np.sin(t * angulo) * q1) / np.sin(angulo)


def suavizar(t):
    """Arranca y frena suave: 0 -> 0 y 1 -> 1, con pendiente cero en los extremos."""
    return t * t * (3.0 - 2.0 * t)


def interpolar_camara(inicio, fin, s):
    """Cámara intermedia entre inicio y fin, dadas como (posición, foco, arriba); s va de 0 a 1.

    La orientación gira con slerp; el foco y la distancia al foco cambian linealmente.
    """
    p0, f0, _ = (np.asarray(v, dtype=float) for v in inicio)
    p1, f1, _ = (np.asarray(v, dtype=float) for v in fin)
    q = slerp(a_cuaternion(marco_camara(*inicio)), a_cuaternion(marco_camara(*fin)), s)
    R = a_matriz(q)
    foco = f0 + s * (f1 - f0)
    distancia = (1 - s) * np.linalg.norm(p0 - f0) + s * np.linalg.norm(p1 - f1)
    return foco + distancia * R[:, 2], foco, R[:, 1]
