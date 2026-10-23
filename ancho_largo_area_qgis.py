# -*- coding: utf-8 -*-
"""
ANCHO, LARGO Y AREA (m2) DE POLIGONOS  -  Script de Processing para QGIS 3.x
===========================================================================

Pide como parametro la capa de poligonos y agrega los campos a ESA MISMA
capa (no crea capa de salida):

    LARGO    largo del poligono (m)
    ANCHO    ancho medio (m)  =  AREA_M2 / LARGO
    AREA_M2  area (m2)

METODOS PARA EL LARGO:

    0. Linea central (por defecto): esqueleto de Voronoi + camino mas largo,
       prolongado hasta el borde. Sigue la forma de poligonos curvos o
       irregulares, como tiras, calles o surcos.
    1. Rectangulo minimo orientado: muy rapido, pero en poligonos curvos
       sobreestima el ancho y subestima el largo.

INSTALACION:
    Caja de herramientas de Procesos -> icono de Python -> "Agregar script
    a la caja de herramientas..." -> elegir este archivo.
    Queda en  Scripts > Mis scripts.

IMPORTANTE:
    La capa debe estar en un CRS proyectado en metros.
"""

import math
import heapq

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterEnum,
    QgsProcessingParameterNumber,
    QgsProcessingParameterBoolean,
    QgsVectorDataProvider,
    QgsField,
    NULL,
    QgsGeometry,
    QgsPointXY,
    QgsPoint,
    QgsWkbTypes,
)


# ============================================================================
# CONSTANTES
# ============================================================================

NOMBRES_NUEVOS = ("LARGO", "ANCHO", "AREA_M2")

MAX_PUNTOS = 4000       # tope de vertices por poligono (velocidad)
SIMPLIFICAR = 0.25      # tolerancia al simplificar la linea central (m)
PODA_FACTOR = 2.0       # poda de ramas hacia esquinas (ver script de lineas)


# ============================================================================
# GEOMETRIA AUXILIAR
# ============================================================================

def _densificar_anillo(anillo, paso, salida):
    for i in range(len(anillo) - 1):
        a = anillo[i]
        b = anillo[i + 1]
        dx = b.x() - a.x()
        dy = b.y() - a.y()
        largo = math.hypot(dx, dy)
        if largo <= 1e-12:
            continue
        k = max(1, int(math.ceil(largo / paso)))
        for j in range(k):
            t = j / float(k)
            salida.append(QgsPointXY(a.x() + dx * t, a.y() + dy * t))


def _puntos_borde(poligono_xy, paso):
    pts = []
    for anillo in poligono_xy:
        _densificar_anillo(anillo, paso, pts)
    return pts


def _dijkstra(adj, origen):
    dist = {origen: 0.0}
    prev = {}
    cola = [(0.0, origen)]
    while cola:
        d, u = heapq.heappop(cola)
        if d > dist[u]:
            continue
        for v, w in adj[u]:
            nd = d + w
            if nd < dist.get(v, 1e300):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(cola, (nd, v))
    return dist, prev


def _camino_mas_largo(adj):
    vistos = set()
    mejor_largo = 0.0
    mejor = None

    for nodo in adj:
        if nodo in vistos:
            continue
        dist, _ = _dijkstra(adj, nodo)
        vistos.update(dist.keys())

        a = max(dist, key=dist.get)
        dist2, prev = _dijkstra(adj, a)
        b = max(dist2, key=dist2.get)

        if dist2[b] > mejor_largo:
            mejor_largo = dist2[b]
            mejor = (a, b, prev)

    if mejor is None:
        return None

    a, b, prev = mejor
    camino = [b]
    while camino[-1] != a:
        camino.append(prev[camino[-1]])
    return camino


def _podar_extremo(camino, adj, frontera, escala):
    """camino[0] es el extremo. Corta las ramas que van hacia las esquinas."""
    if len(camino) < 3:
        return camino

    limite = 4.0 * escala
    cum = 0.0
    corte = None

    for i in range(1, len(camino) - 1):
        a = camino[i - 1]
        b = camino[i]
        cum += math.hypot(b[0] - a[0], b[1] - a[1])
        if cum > limite:
            break

        if len(adj.get(b, ())) >= 3:
            radio = frontera.distance(
                QgsGeometry.fromPointXY(QgsPointXY(b[0], b[1])))
            if radio > 0 and cum <= PODA_FACTOR * radio:
                corte = i

    if corte is None:
        return camino
    return camino[corte:]


def _extender_extremo(camino, poli_geom, escala, paso):
    """camino[0] es el extremo. Devuelve el punto donde toca el borde."""
    if len(camino) < 2:
        return None

    p0 = camino[0]

    cum = 0.0
    ref = camino[-1]
    for i in range(1, len(camino)):
        cum += math.hypot(camino[i][0] - camino[i - 1][0],
                          camino[i][1] - camino[i - 1][1])
        if cum >= 0.5 * escala:
            ref = camino[i]
            break

    dx = p0[0] - ref[0]
    dy = p0[1] - ref[1]
    n = math.hypot(dx, dy)
    if n <= 1e-9:
        return None
    dx /= n
    dy /= n

    largo = max(6.0 * escala, 5.0 * paso)
    a = QgsPointXY(p0[0], p0[1])
    b = QgsPointXY(p0[0] + dx * largo, p0[1] + dy * largo)

    try:
        inter = QgsGeometry.fromPolylineXY([a, b]).intersection(poli_geom)
        if inter is None or inter.isEmpty():
            return None
        if inter.isMultipart():
            partes = inter.asMultiPolyline()
        else:
            partes = [inter.asPolyline()]
    except Exception:
        return None

    pa = QgsGeometry.fromPointXY(a)
    mejor = None
    mejor_d = 1e300
    for pl in partes:
        if len(pl) < 2:
            continue
        d = QgsGeometry.fromPolylineXY(pl).distance(pa)
        if d < mejor_d:
            mejor_d = d
            mejor = pl

    if mejor is None or mejor_d > 1e-3:
        return None

    q0, q1 = mejor[0], mejor[-1]
    lejano = q1 if q0.distance(a) < q1.distance(a) else q0
    if lejano.distance(a) <= 1e-6:
        return None
    return (lejano.x(), lejano.y())


# ============================================================================
# LARGO POR LINEA CENTRAL
# ============================================================================

def _largo_central(poli_geom, poli_xy, paso_base):
    """Largo del eje principal de UNA parte, de borde a borde."""

    try:
        perimetro = poli_geom.constGet().perimeter()
    except Exception:
        perimetro = poli_geom.length()
    if perimetro <= 0:
        return None

    paso = max(paso_base, perimetro / float(MAX_PUNTOS))

    pts = _puntos_borde(poli_xy, paso)
    if len(pts) < 4:
        return None

    vor = QgsGeometry.fromMultiPointXY(pts).voronoiDiagram(edgesOnly=True)
    if vor is None or vor.isNull() or vor.isEmpty():
        return None

    try:
        aristas = vor.asMultiPolyline()
    except Exception:
        return None
    if not aristas:
        return None

    motor = QgsGeometry.createGeometryEngine(poli_geom.constGet())
    motor.prepareGeometry()
    cache = {}

    def dentro(clave):
        r = cache.get(clave)
        if r is None:
            r = bool(motor.intersects(QgsPoint(clave[0], clave[1])))
            cache[clave] = r
        return r

    adj = {}
    for arista in aristas:
        for i in range(len(arista) - 1):
            p = arista[i]
            q = arista[i + 1]
            ka = (round(p.x(), 5), round(p.y(), 5))
            kb = (round(q.x(), 5), round(q.y(), 5))
            if ka == kb:
                continue
            if not (dentro(ka) and dentro(kb)):
                continue
            w = math.hypot(kb[0] - ka[0], kb[1] - ka[1])
            adj.setdefault(ka, []).append((kb, w))
            adj.setdefault(kb, []).append((ka, w))

    if not adj:
        return None

    camino = _camino_mas_largo(adj)
    if not camino or len(camino) < 2:
        return None

    escala = poli_geom.area() / perimetro
    if escala <= 1e-9:
        escala = paso

    # Podar ramas hacia las esquinas
    if len(camino) >= 3:
        try:
            frontera = QgsGeometry(poli_geom.constGet().boundary())
        except Exception:
            frontera = poli_geom.convertToType(
                QgsWkbTypes.LineGeometry, False)
        if frontera is not None and not frontera.isEmpty():
            camino = _podar_extremo(camino, adj, frontera, escala)
            camino = _podar_extremo(
                camino[::-1], adj, frontera, escala)[::-1]

    # Prolongar hasta el borde: el largo debe cubrir todo el poligono
    nuevo = _extender_extremo(camino, poli_geom, escala, paso)
    if nuevo is not None:
        camino.insert(0, nuevo)
    nuevo = _extender_extremo(camino[::-1], poli_geom, escala, paso)
    if nuevo is not None:
        camino.append(nuevo)

    linea = QgsGeometry.fromPolylineXY(
        [QgsPointXY(x, y) for x, y in camino])

    # Quitar el zigzag del esqueleto para no inflar el largo
    if SIMPLIFICAR > 0:
        simple = linea.simplify(SIMPLIFICAR)
        if simple is not None and not simple.isEmpty():
            linea = simple

    largo = linea.length()
    return largo if largo > 0 else None


# ============================================================================
# LARGO POR RECTANGULO ORIENTADO
# ============================================================================

def _largo_rectangulo(poli_geom):
    try:
        r = poli_geom.orientedMinimumBoundingBox()
        return max(float(r[3]), float(r[4]))
    except Exception:
        return None


# ============================================================================
# PARTES DEL POLIGONO
# ============================================================================

def _partes_poligono(geom):
    if geom.isMultipart():
        listas = geom.asMultiPolygon()
    else:
        listas = [geom.asPolygon()]

    partes = []
    for poli_xy in listas:
        if not poli_xy:
            continue
        g = QgsGeometry.fromPolygonXY(poli_xy)
        if g is None or g.isEmpty():
            continue
        partes.append((g, poli_xy))
    return partes


def _reparar(geom):
    if geom.isGeosValid():
        return geom
    rep = geom.makeValid()
    if rep is not None and not rep.isEmpty():
        rep = rep.convertToType(QgsWkbTypes.PolygonGeometry, True)
        if rep is not None and not rep.isEmpty():
            return rep
    return geom


# ============================================================================
# CAMPOS EN LA CAPA
# ============================================================================

def _buscar_indice(layer, nombre):
    """
    Busca el campo sin distinguir mayusculas/minusculas.
    Si hay uno con el nombre exacto lo prefiere; si no, el que coincida
    ignorando mayusculas (ej. 'area_m2' para 'AREA_M2').
    """
    objetivo = nombre.upper()
    parcial = -1
    for i, f in enumerate(layer.fields()):
        if f.name() == nombre:
            return i
        if parcial == -1 and f.name().upper() == objetivo:
            parcial = i
    return parcial


def _usar_campo_existente(layer, prov, i, nombre, en_edicion, feedback):
    """Renombra a MAYUSCULAS el campo existente (si hace falta) y lo usa."""

    fld = layer.fields()[i]
    actual = fld.name()

    if actual != nombre:
        ok = False
        try:
            if en_edicion:
                ok = layer.renameAttribute(i, nombre)
            else:
                caps = prov.capabilities()
                if caps & QgsVectorDataProvider.RenameAttributes:
                    ok = prov.renameAttributes({i: nombre})
        except Exception:
            ok = False

        layer.updateFields()

        if ok:
            feedback.pushInfo(
                "Campo '{0}' renombrado a '{1}'.".format(actual, nombre))
        else:
            feedback.pushInfo(
                "No se pudo renombrar '{0}' a '{1}'; se usa tal cual."
                .format(actual, nombre))

    tipo = fld.typeName().lower()
    es_decimal = (fld.type() == QVariant.Double or
                  "real" in tipo or "double" in tipo or "float" in tipo)
    if not es_decimal:
        feedback.pushInfo(
            "AVISO: el campo '{0}' no es decimal ({1}); los valores "
            "pueden quedar redondeados o truncados.".format(
                actual, fld.typeName()))

    return i


def _asegurar_campo(layer, prov, nombre, en_edicion, feedback):
    """Devuelve el indice del campo; lo crea solo si no existe."""

    i = _buscar_indice(layer, nombre)
    if i != -1:
        return _usar_campo_existente(
            layer, prov, i, nombre, en_edicion, feedback)

    campo = QgsField(nombre, QVariant.Double, "double", 20, 3)

    if en_edicion:
        ok = layer.addAttribute(campo)
    else:
        ok = prov.addAttributes([campo])

    if not ok:
        raise QgsProcessingException(
            "No se pudo crear el campo {0} en la capa.".format(nombre))

    layer.updateFields()
    i = _buscar_indice(layer, nombre)

    if i == -1 and not en_edicion:
        try:
            prov.reloadData()
        except Exception:
            pass
        layer.updateFields()
        i = _buscar_indice(layer, nombre)

    if i == -1 and not en_edicion:
        i = prov.fields().indexFromName(nombre)

    if i == -1:
        raise QgsProcessingException(
            "No se encontro el campo {0} despues de crearlo.".format(nombre))

    return i


# ============================================================================
# ALGORITMO DE PROCESSING
# ============================================================================

class AnchoLargoArea(QgsProcessingAlgorithm):

    INPUT = "INPUT"
    METODO = "METODO"
    PASO = "PASO"
    SOLO_SEL = "SOLO_SEL"

    def tr(self, texto):
        return QCoreApplication.translate("Processing", texto)

    def createInstance(self):
        return AnchoLargoArea()

    def name(self):
        return "ancho_largo_area"

    def displayName(self):
        return self.tr("Calcular ancho, largo y area (m2) de poligonos")

    def group(self):
        return self.tr("Mis scripts")

    def groupId(self):
        return "mis_scripts"

    def flags(self):
        # Modifica la capa del proyecto: debe correr en el hilo principal
        return super().flags() | QgsProcessingAlgorithm.FlagNoThreading

    def shortHelpString(self):
        return self.tr(
            "Agrega a la MISMA capa los campos LARGO, ANCHO (medio = "
            "AREA_M2 / LARGO) y AREA_M2. Si ya existen, se sobrescriben. "
            "La capa debe estar en un CRS proyectado en metros. El metodo "
            "'Linea central' es el mas preciso en poligonos curvos; el "
            "rectangulo orientado es mas rapido.")

    def initAlgorithm(self, config=None):

        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT,
                self.tr("Capa de poligonos (se modifica)"),
                [QgsProcessing.TypeVectorPolygon]))

        self.addParameter(
            QgsProcessingParameterEnum(
                self.METODO,
                self.tr("Metodo para calcular el largo"),
                options=[
                    self.tr("Linea central (preciso, sigue curvas)"),
                    self.tr("Rectangulo minimo orientado (rapido)"),
                ],
                defaultValue=0))

        self.addParameter(
            QgsProcessingParameterNumber(
                self.PASO,
                self.tr("Paso de densificado del borde (m) - solo linea "
                        "central"),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=0.5,
                minValue=0.01))

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.SOLO_SEL,
                self.tr("Solo entidades seleccionadas"),
                defaultValue=False))

    def processAlgorithm(self, parameters, context, feedback):

        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(
                self.invalidSourceError(parameters, self.INPUT))

        metodo = self.parameterAsEnum(parameters, self.METODO, context)
        paso_base = self.parameterAsDouble(parameters, self.PASO, context)
        solo_sel = self.parameterAsBool(parameters, self.SOLO_SEL, context)

        if layer.crs().isGeographic():
            raise QgsProcessingException(
                "La capa esta en coordenadas geograficas. Reproyectala a "
                "un CRS en metros antes de ejecutar.")

        en_edicion = layer.isEditable()
        prov = layer.dataProvider()

        if not en_edicion:
            caps = prov.capabilities()
            if (not (caps & QgsVectorDataProvider.AddAttributes) or
                    not (caps & QgsVectorDataProvider.ChangeAttributeValues)):
                raise QgsProcessingException(
                    "El formato de la capa no permite agregar campos ni "
                    "modificar valores (solo lectura).")

        # ----------------------------------------------------------------
        # Crear los campos que falten en la misma capa
        # ----------------------------------------------------------------

        idx = {}
        for nombre in NOMBRES_NUEVOS:
            idx[nombre] = _asegurar_campo(
                layer, prov, nombre, en_edicion, feedback)

        # ----------------------------------------------------------------
        # Entidades a procesar
        # ----------------------------------------------------------------

        if solo_sel and layer.selectedFeatureCount() > 0:
            entidades = layer.getSelectedFeatures()
            total = layer.selectedFeatureCount()
        else:
            entidades = layer.getFeatures()
            total = layer.featureCount()

        paso_avance = 100.0 / total if total else 0
        cambios = {}          # fid -> {indice_campo: valor}
        n_respaldo = 0
        n_sin_dato = 0

        for i, f in enumerate(entidades):

            if feedback.isCanceled():
                break

            geom = f.geometry()
            largo = ancho = area = None

            if geom is not None and not geom.isEmpty():

                area = geom.area()
                geom_ok = _reparar(geom)

                suma_largo = 0.0
                for g_parte, poli_xy in _partes_poligono(geom_ok):

                    l = None
                    if metodo == 0:
                        try:
                            l = _largo_central(g_parte, poli_xy, paso_base)
                        except Exception:
                            l = None
                        if l is None:
                            l = _largo_rectangulo(g_parte)
                            n_respaldo += 1
                    else:
                        l = _largo_rectangulo(g_parte)

                    if l is not None:
                        suma_largo += l

                if suma_largo > 0:
                    largo = suma_largo
                    ancho = area / suma_largo
                else:
                    n_sin_dato += 1
            else:
                n_sin_dato += 1

            cambios[f.id()] = {
                idx["LARGO"]: NULL if largo is None else round(largo, 3),
                idx["ANCHO"]: NULL if ancho is None else round(ancho, 3),
                idx["AREA_M2"]: NULL if area is None else round(area, 3),
            }

            feedback.setProgress(int((i + 1) * paso_avance))

        # ----------------------------------------------------------------
        # Escribir los valores en la capa
        # ----------------------------------------------------------------

        if en_edicion:
            # La capa ya estaba en edicion: se usa el buffer de edicion
            for fid, valores in cambios.items():
                for k, v in valores.items():
                    layer.changeAttributeValue(fid, k, v)
            feedback.pushInfo(
                "La capa esta en modo edicion: guarda los cambios para "
                "conservarlos.")
        else:
            if cambios and not prov.changeAttributeValues(cambios):
                raise QgsProcessingException(
                    "No se pudieron escribir los valores en la capa.")

        layer.triggerRepaint()

        feedback.pushInfo(
            "Entidades actualizadas: {0}".format(len(cambios)))
        if n_respaldo:
            feedback.pushInfo(
                "{0} parte(s) usaron el rectangulo orientado como respaldo "
                "(la linea central no pudo calcularse).".format(n_respaldo))
        if n_sin_dato:
            feedback.pushInfo(
                "{0} poligono(s) quedaron sin LARGO/ANCHO (geometria vacia "
                "o sin resultado).".format(n_sin_dato))

        return {}