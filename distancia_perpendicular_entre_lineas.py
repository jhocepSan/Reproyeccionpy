# -*- coding: utf-8 -*-
"""
Distancia perpendicular entre líneas
=========================
Algoritmo de procesamiento para QGIS 3.22+.

Crea una capa de segmentos perpendiculares entre líneas vecinas paralelas.
El campo ``distancia_m`` almacena la separación en metros.
Solo mide parejas cuyas líneas se solapan longitudinalmente y cuya dirección
es paralela dentro de una tolerancia de 5 grados.

Instalación
-----------
1. Caja de herramientas de procesos > Scripts > Añadir script a la caja
   de herramientas...
2. Elige este archivo .py
3. Ejecuta LineDist > Distancia perpendicular entre líneas
"""

import math

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import QgsPointXY
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterNumber,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterField,
    QgsProcessingParameterDefinition,
    QgsFeature,
    QgsGeometry,
    QgsField,
    QgsFields,
    QgsWkbTypes,
    QgsFeatureSink,
    QgsSpatialIndex,
    QgsCoordinateTransform,
    QgsCoordinateReferenceSystem,
    QgsUnitTypes,
    QgsProcessingException,
    QgsLineSymbol,
    QgsPalLayerSettings,
    QgsTextFormat,
    QgsTextBufferSettings,
    QgsVectorLayerSimpleLabeling,
    QgsProcessingLayerPostProcessorInterface,
)
from qgis.PyQt.QtGui import QColor, QFont


def _line_type():
    if hasattr(QgsProcessing, "TypeVectorLine"):
        return QgsProcessing.TypeVectorLine
    return QgsProcessing.SourceType.VectorLine


def _flag_advanced():
    if hasattr(QgsProcessingParameterDefinition, "FlagAdvanced"):
        return QgsProcessingParameterDefinition.FlagAdvanced
    return QgsProcessingParameterDefinition.Flag.Advanced


def _num_type(kind):
    """Double / Integer compatibles con QGIS 3.22 y 3.38+."""
    val = getattr(QgsProcessingParameterNumber, kind, None)
    if val is not None and not callable(val):
        return val
    enum = getattr(QgsProcessingParameterNumber, "Type", None)
    if enum is not None:
        return getattr(enum, kind)
    return QgsProcessingParameterNumber.Double


class _StyleDistanceLines(QgsProcessingLayerPostProcessorInterface):
    """Pinta las mediciones en rojo y etiqueta distancia_m."""

    def postProcessLayer(self, layer, context, feedback):  # noqa: N802
        if layer is None or not layer.isValid():
            return
        try:
            symbol = QgsLineSymbol.createSimple(
                {
                    "color": "226,59,50",
                    "width": "0.35",
                    "capstyle": "round",
                    "joinstyle": "round",
                }
            )
            layer.renderer().setSymbol(symbol)

            settings = QgsPalLayerSettings()
            settings.fieldName = "distancia_m"
            settings.isExpression = False
            settings.enabled = True
            if hasattr(settings, "placement"):
                settings.placement = QgsPalLayerSettings.Line
            fmt = QgsTextFormat()
            fmt.setSize(8)
            fmt.setFont(QFont("Sans Serif", 8))
            fmt.setColor(QColor(40, 20, 20))
            buf = QgsTextBufferSettings()
            buf.setEnabled(True)
            buf.setSize(0.8)
            buf.setColor(QColor(255, 255, 255))
            fmt.setBuffer(buf)
            settings.setFormat(fmt)
            layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
            layer.setLabelsEnabled(True)
            layer.triggerRepaint()
        except Exception:
            pass


class DistanciaPerpendicularEntreLineasAlgorithm(QgsProcessingAlgorithm):
    INPUT = "INPUT"
    ID_FIELD = "ID_FIELD"
    MODE = "MODE"
    MAX_DISTANCE = "MAX_DISTANCE"
    MIN_DISTANCE = "MIN_DISTANCE"
    K_NEIGHBORS = "K_NEIGHBORS"
    SKIP_ZERO = "SKIP_ZERO"
    OUTPUT = "OUTPUT"

    def __init__(self):
        super().__init__()
        self._post = None

    def tr(self, string):
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        return DistanciaPerpendicularEntreLineasAlgorithm()

    def name(self):
        return "distancia_perpendicular_entre_lineas"

    def displayName(self):
        return self.tr("Distancia perpendicular entre líneas")

    def group(self):
        return self.tr("LineDist")

    def groupId(self):
        return "polydist"

    def tags(self):
        return [
            "distancia",
            "lineas",
            "perpendicular",
            "metros",
            "vecinos",
            "lineas paralelas",
        ]

    def shortHelpString(self):
        return self.tr(
            "<p>Calcula la <b>distancia perpendicular entre líneas paralelas</b> y genera una capa de líneas de medición. El campo <code>distancia_m</code> almacena la distancia en metros.</p>"
            "<p>Para cada pareja, se busca la zona donde las líneas se solapan en su dirección longitudinal y se crea el segmento perpendicular en el punto medio de ese solapamiento. Así, la medición no conecta extremos desplazados.</p>"
            "<p><b>Importante:</b> las entidades deben ser líneas rectas (o polilíneas cuyos vértices estén alineados) y paralelas entre sí. Las parejas sin solapamiento longitudinal o con direcciones que difieren más de 5 grados se omiten.</p>"
            "<p><b>Modos:</b> pares dentro de una distancia máxima, o K vecinos más próximos. Si el SRC está en grados, el cálculo se hace en una zona UTM y la salida vuelve al SRC original.</p>"
            "<p>Se recomienda guardar la salida en GeoPackage para conservar los campos.</p>"
        )

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr("Capa de líneas"),
                [_line_type()],
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.ID_FIELD,
                self.tr("Campo identificador (opcional)"),
                parentLayerParameterName=self.INPUT,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.MODE,
                self.tr("Modo de emparejamiento"),
                options=[
                    self.tr("Pares dentro de distancia máxima"),
                    self.tr("K vecinos más próximos"),
                ],
                defaultValue=0,
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.MAX_DISTANCE,
                self.tr("Distancia máxima de búsqueda (metros). 0 = sin límite"),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=25.0,
                minValue=0.0,
            )
        )

        k_param = QgsProcessingParameterNumber(
            self.K_NEIGHBORS,
            self.tr("K vecinos (solo modo K vecinos)"),
            type=QgsProcessingParameterNumber.Integer,
            defaultValue=1,
            minValue=1,
            maxValue=50,
        )
        k_param.setFlags(k_param.flags() | _flag_advanced())
        self.addParameter(k_param)

        min_param = QgsProcessingParameterNumber(
            self.MIN_DISTANCE,
            self.tr("Distancia mínima a conservar (metros)"),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=0.0,
            minValue=0.0,
        )
        min_param.setFlags(min_param.flags() | _flag_advanced())
        self.addParameter(min_param)

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.SKIP_ZERO,
                self.tr("Omitir líneas que se tocan o intersectan (distancia 0)"),
                defaultValue=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr("Líneas de distancia"),
            )
        )

    def _perpendicular_line(self, geom_a, geom_b):
        """Busca una perpendicular real desde geom_a hasta geom_b.

        Se prueban vértices y puntos medios de los segmentos de A. Desde cada
        punto se traza una normal a la dirección local del segmento y se busca
        su intersección con B. Así, los extremos de la medición caen sobre las
        dos líneas y la medición es perpendicular a la dirección local de A.
        Para líneas paralelas, también lo será respecto a B.
        """
        if geom_a is None or geom_b is None or geom_a.isEmpty() or geom_b.isEmpty():
            return None

        va = [QgsPointXY(v.x(), v.y()) for v in geom_a.vertices()]
        vb = [QgsPointXY(v.x(), v.y()) for v in geom_b.vertices()]
        if len(va) < 2 or len(vb) < 2:
            return None

        # Rechazar líneas cuya dirección general difiera más de 5 grados.
        ax, ay = va[-1].x() - va[0].x(), va[-1].y() - va[0].y()
        bx, by = vb[-1].x() - vb[0].x(), vb[-1].y() - vb[0].y()
        alen, blen = math.hypot(ax, ay), math.hypot(bx, by)
        if alen <= 1e-9 or blen <= 1e-9:
            return None
        cross = abs((ax / alen) * (by / blen) - (ay / alen) * (bx / blen))
        if cross > math.sin(math.radians(10.0)):
            return None

        rect = geom_a.boundingBox()
        rect.combineExtentWith(geom_b.boundingBox())
        reach = max(rect.width(), rect.height(), 1.0) * 4.0
        candidates = []

        # Cada segmento de A aporta sus extremos y su punto medio como origen
        # de una perpendicular a la dirección de ese segmento.
        for p0, p1 in zip(va[:-1], va[1:]):
            dx, dy = p1.x() - p0.x(), p1.y() - p0.y()
            seg_len = math.hypot(dx, dy)
            if seg_len <= 1e-9:
                continue
            tx, ty = dx / seg_len, dy / seg_len
            nx, ny = -ty, tx
            samples = (p0, QgsPointXY((p0.x()+p1.x())/2.0, (p0.y()+p1.y())/2.0), p1)
            for p in samples:
                a = QgsPointXY(p.x() - nx * reach, p.y() - ny * reach)
                b = QgsPointXY(p.x() + nx * reach, p.y() + ny * reach)
                normal = QgsGeometry.fromPolylineXY([a, b])
                inter = normal.intersection(geom_b)
                if inter is None or inter.isEmpty():
                    continue
                for v in inter.vertices():
                    q = QgsPointXY(v.x(), v.y())
                    # La intersección debe estar dentro de la extensión de la
                    # línea B por construcción; descartar distancias nulas.
                    dist = math.hypot(q.x() - p.x(), q.y() - p.y())
                    if dist > 1e-8:
                        candidates.append((dist, QgsGeometry.fromPolylineXY([p, q])))

        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0])
        return candidates[0][1]

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        if source is None:
            raise QgsProcessingException(
                self.invalidSourceError(parameters, self.INPUT)
            )

        id_field = self.parameterAsString(parameters, self.ID_FIELD, context)
        mode = self.parameterAsEnum(parameters, self.MODE, context)
        max_dist = self.parameterAsDouble(parameters, self.MAX_DISTANCE, context)
        min_dist = self.parameterAsDouble(parameters, self.MIN_DISTANCE, context)
        k_neighbors = self.parameterAsInt(parameters, self.K_NEIGHBORS, context)
        skip_zero = self.parameterAsBoolean(parameters, self.SKIP_ZERO, context)

        src_crs = source.sourceCrs()
        if not src_crs.isValid():
            raise QgsProcessingException(
                self.tr("La capa de entrada no tiene un SRC válido.")
            )

        extent = source.sourceExtent()
        work_crs = self._metric_crs(src_crs, extent, context)
        need_xform = work_crs != src_crs
        to_work = None
        to_src = None
        if need_xform:
            to_work = QgsCoordinateTransform(
                src_crs, work_crs, context.transformContext()
            )
            to_src = QgsCoordinateTransform(
                work_crs, src_crs, context.transformContext()
            )
            feedback.pushInfo(
                self.tr(
                    "SRC de entrada {0} no está en metros. "
                    "Cálculo en {1}; las líneas se devuelven en el SRC original."
                ).format(src_crs.authid(), work_crs.authid())
            )

        features = []
        for feat in source.getFeatures():
            if feedback.isCanceled():
                break
            geom = feat.geometry()
            if geom is None or geom.isEmpty():
                continue
            if QgsWkbTypes.geometryType(geom.wkbType()) != QgsWkbTypes.LineGeometry:
                continue
            if not geom.isGeosValid():
                geom = geom.makeValid()
            if geom is None or geom.isEmpty():
                continue
            geom_w = QgsGeometry(geom)
            if to_work is not None:
                if geom_w.transform(to_work) != 0:
                    continue
            ident = feat.id()
            if id_field:
                try:
                    ident = feat[id_field]
                except Exception:
                    ident = feat.id()
            features.append(
                {
                    "fid": feat.id(),
                    "id": ident,
                    "geom": geom_w,
                }
            )

        n = len(features)
        if n < 2:
            raise QgsProcessingException(
                self.tr("Se necesitan al menos 2 líneas válidas.")
            )

        feedback.pushInfo(self.tr("Líneas válidas: {0}").format(n))

        index = QgsSpatialIndex()
        for i, item in enumerate(features):
            dummy = QgsFeature()
            dummy.setId(i)
            dummy.setGeometry(item["geom"])
            index.addFeature(dummy)

        fields = QgsFields()
        fields.append(QgsField("distancia_m", QVariant.Double, "", 20, 4))
        fields.append(QgsField("id_origen", QVariant.String, "", 64))
        fields.append(QgsField("id_destino", QVariant.String, "", 64))
        fields.append(QgsField("fid_origen", QVariant.LongLong))
        fields.append(QgsField("fid_destino", QVariant.LongLong))

        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            fields,
            QgsWkbTypes.LineString,
            src_crs,
        )
        if sink is None:
            raise QgsProcessingException(
                self.invalidSinkError(parameters, self.OUTPUT)
            )

        search_r = max_dist if max_dist > 0 else 1.0e9
        written = [0]
        skipped_perpendicular = [0]
        seen = set()

        def emit(i, j, line_geom, length_m):
            pair = (
                min(features[i]["fid"], features[j]["fid"]),
                max(features[i]["fid"], features[j]["fid"]),
            )
            if pair in seen:
                return
            seen.add(pair)
            if skip_zero and length_m <= 1e-6:
                return
            if length_m < min_dist:
                return
            if max_dist > 0 and length_m > max_dist + 1e-6:
                return

            out_g = QgsGeometry(line_geom)
            if out_g.wkbType() != QgsWkbTypes.LineString:
                try:
                    out_g = QgsGeometry.fromPolylineXY(out_g.asPolyline())
                except Exception:
                    pass
            if to_src is not None:
                out_g.transform(to_src)

            out = QgsFeature(fields)
            out.setGeometry(out_g)
            out.setAttributes(
                [
                    round(float(length_m), 4),
                    str(features[i]["id"]),
                    str(features[j]["id"]),
                    int(features[i]["fid"]),
                    int(features[j]["fid"]),
                ]
            )
            sink.addFeature(out, QgsFeatureSink.FastInsert)
            written[0] += 1

        def bbox_gap(ga, gb):
            return QgsGeometry.fromRect(ga.boundingBox()).distance(
                QgsGeometry.fromRect(gb.boundingBox())
            )

        if mode == 0:
            for i, item in enumerate(features):
                if feedback.isCanceled():
                    break
                if i % 25 == 0:
                    feedback.setProgress(int(100.0 * i / n))
                    feedback.setProgressText(
                        self.tr("Emparejando {0} / {1}").format(i, n)
                    )

                rect = item["geom"].boundingBox()
                rect.grow(search_r)
                for j in index.intersects(rect):
                    if j <= i:
                        continue
                    ga = item["geom"]
                    gb = features[j]["geom"]
                    if bbox_gap(ga, gb) > search_r:
                        continue
                    line = self._perpendicular_line(ga, gb)
                    if line is None or line.isEmpty():
                        skipped_perpendicular[0] += 1
                        continue
                    emit(i, j, line, line.length())
        else:
            for i, item in enumerate(features):
                if feedback.isCanceled():
                    break
                if i % 25 == 0:
                    feedback.setProgress(int(100.0 * i / n))

                rect = item["geom"].boundingBox()
                rect.grow(search_r)
                neigh = []
                for j in index.intersects(rect):
                    if j == i:
                        continue
                    ga = item["geom"]
                    gb = features[j]["geom"]
                    line = self._perpendicular_line(ga, gb)
                    if line is None or line.isEmpty():
                        skipped_perpendicular[0] += 1
                        continue
                    length_m = line.length()
                    if skip_zero and length_m <= 1e-6:
                        continue
                    if max_dist > 0 and length_m > search_r:
                        continue
                    neigh.append((length_m, j, line))
                neigh.sort(key=lambda t: t[0])
                for length_m, j, line in neigh[:k_neighbors]:
                    emit(i, j, line, length_m)

        feedback.pushInfo(self.tr("Líneas de medición creadas: {0}").format(written[0]))
        if skipped_perpendicular[0]:
            feedback.pushInfo(self.tr("Parejas omitidas por no ser paralelas (tolerancia 5 grados) o no tener separación medible: {0}").format(skipped_perpendicular[0]))
        feedback.setProgress(100)

        try:
            details = context.layerToLoadOnCompletionDetails(dest_id)
            self._post = _StyleDistanceLines()
            details.setPostProcessor(self._post)
        except Exception:
            pass

        return {self.OUTPUT: dest_id}

    def _metric_crs(self, src_crs, extent, context):
        if (
            not src_crs.isGeographic()
            and src_crs.mapUnits() == QgsUnitTypes.DistanceMeters
        ):
            return src_crs

        wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
        xform = QgsCoordinateTransform(src_crs, wgs84, context.transformContext())
        try:
            center = xform.transform(extent.center())
        except Exception:
            return QgsCoordinateReferenceSystem("EPSG:3857")

        lon = center.x()
        lat = center.y()
        zone = int((lon + 180.0) / 6.0) + 1
        if zone < 1:
            zone = 1
        if zone > 60:
            zone = 60
        epsg = (32600 if lat >= 0.0 else 32700) + zone
        crs = QgsCoordinateReferenceSystem.fromEpsgId(epsg)
        if not crs.isValid():
            crs = QgsCoordinateReferenceSystem("EPSG:3857")
        return crs
