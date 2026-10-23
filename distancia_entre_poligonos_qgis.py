# -*- coding: utf-8 -*-
"""
Distancia entre polígonos
=========================
Algoritmo de procesamiento para QGIS 3.22+.

Crea una capa de LÍNEAS con la distancia mínima entre polígonos vecinos.
El campo principal ``distancia_m`` almacena la medida en metros.

No asume que los polígonos tengan la misma orientación: la línea se calcula
con QgsGeometry.shortestLine() sobre el contorno real de cada geometría
(los dos puntos más cercanos, no los centroides).

Instalación
-----------
1. Caja de herramientas de procesos > Scripts > Añadir script a la caja
   de herramientas...
2. Elige este archivo .py
3. Ejecuta PolyDist > Distancia entre polígonos
"""

from qgis.PyQt.QtCore import QCoreApplication, QVariant
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


def _polygon_type():
    if hasattr(QgsProcessing, "TypeVectorPolygon"):
        return QgsProcessing.TypeVectorPolygon
    return QgsProcessing.SourceType.VectorPolygon


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
    """Pinta las líneas en rojo y etiqueta distancia_m, como en el ejemplo."""

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
            layer.setLabelsEnabled(False)
            layer.triggerRepaint()
        except Exception:
            pass


class DistanciaEntrePoligonosAlgorithm(QgsProcessingAlgorithm):
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
        return DistanciaEntrePoligonosAlgorithm()

    def name(self):
        return "distancia_entre_poligonos"

    def displayName(self):
        return self.tr("Distancia entre polígonos")

    def group(self):
        return self.tr("PolyDist")

    def groupId(self):
        return "polydist"

    def tags(self):
        return [
            "distancia",
            "poligonos",
            "shortestLine",
            "metros",
            "vecinos",
            "parcelas",
        ]

    def shortHelpString(self):
        return self.tr(
            "<p>Calcula la <b>distancia mínima</b> entre polígonos y genera "
            "una capa de <b>líneas</b>. Cada línea une los dos puntos más "
            "cercanos de un par y el campo principal <b>distancia_m</b> "
            "guarda la medida en metros.</p>"
            "<p>No importa que los polígonos no compartan orientación o "
            "sentido: <code>shortestLine</code> opera sobre el contorno real, "
            "no sobre centroides ni ejes.</p>"
            "<p><b>Modos</b></p>"
            "<ul>"
            "<li><b>Pares dentro de distancia máxima</b> — todas las parejas "
            "cuya distancia sea menor o igual al umbral (el caso del ejemplo "
            "de parcelas alargadas).</li>"
            "<li><b>K vecinos más próximos</b> — para cada polígono, solo las "
            "K distancias más cortas.</li>"
            "</ul>"
            "<p>Si la capa está en un SRC geográfico (grados), las geometrías "
            "se reproyectan a UTM para medir en metros y las líneas de salida "
            "vuelven al SRC original.</p>"
            "<p>Recomendado: guardar el resultado como <b>GeoPackage</b> "
            "(no Shapefile) para conservar el nombre <code>distancia_m</code>.</p>"
        )

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr("Capa de polígonos"),
                [_polygon_type()],
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
                self.tr("Omitir polígonos que se tocan o intersectan (distancia 0)"),
                defaultValue=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr("Líneas de distancia"),
            )
        )

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
            if QgsWkbTypes.geometryType(geom.wkbType()) != QgsWkbTypes.PolygonGeometry:
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
                self.tr("Se necesitan al menos 2 polígonos válidos.")
            )

        feedback.pushInfo(self.tr("Polígonos válidos: {0}").format(n))

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
                    line = ga.shortestLine(gb)
                    if line is None or line.isEmpty():
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
                    line = ga.shortestLine(gb)
                    if line is None or line.isEmpty():
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

        feedback.pushInfo(self.tr("Líneas creadas: {0}").format(written[0]))
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
