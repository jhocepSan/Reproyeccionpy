           
-- estadisticas upf
                INSERT INTO cmpc.estadistica_swc( gid_poligono, fecha, promedio, minimo, maximo,acumulado,desviacion)
                SELECT 
                    p.gid,
                    '2026/10/14' as fecha,
                    AVG(p.val) AS promedio, 
                    MIN(p.val) AS minimo, 
                    MAX(p.val) AS maximo,
                    SUM(p.val) AS acumulado,
                    STDDEV(p.val) AS desviacion
                FROM (
                    SELECT (ST_PixelAsPoints(ST_Clip(r.rast, 1, p.the_geom,TRUE,TRUE))).*,p.gid
                    FROM "14102026_swc4_26_100" r
                    JOIN public.fundos_riego p
                    ON ST_Intersects(r.rast, p.the_geom) 
                ) AS p
                WHERE p.val > 0
                group by p.gid;
                --calculo estadisticas utb
                INSERT INTO cmpc.estadistica_swc_utb(
                    gid_poligono, fecha, valor)
                SELECT 
                    p.gid,
                    '2026/10/14' as fecha,
                    (p.val) AS valor
                FROM (
                    SELECT (ST_PixelAsPoints(ST_Clip(r.rast, 1, ST_Buffer(p.the_geom,-0.01),TRUE,TRUE))).*,p.gid
                    FROM "14102026_swc4_26_100" r
                    JOIN public.ri_utbs_riego p
                    ON ST_Intersects(r.rast, p.the_geom) 
                ) AS p
                WHERE p.val > 0 ;
            
-- estadisticas upf
                INSERT INTO cmpc.estadistica_swc( gid_poligono, fecha, promedio, minimo, maximo,acumulado,desviacion)
                SELECT 
                    p.gid,
                    '2026/10/16' as fecha,
                    AVG(p.val) AS promedio, 
                    MIN(p.val) AS minimo, 
                    MAX(p.val) AS maximo,
                    SUM(p.val) AS acumulado,
                    STDDEV(p.val) AS desviacion
                FROM (
                    SELECT (ST_PixelAsPoints(ST_Clip(r.rast, 1, p.the_geom,TRUE,TRUE))).*,p.gid
                    FROM "16102026_swc4_26_100" r
                    JOIN public.fundos_riego p
                    ON ST_Intersects(r.rast, p.the_geom) 
                ) AS p
                WHERE p.val > 0
                group by p.gid;
                --calculo estadisticas utb
                INSERT INTO cmpc.estadistica_swc_utb(
                    gid_poligono, fecha, valor)
                SELECT 
                    p.gid,
                    '2026/10/16' as fecha,
                    (p.val) AS valor
                FROM (
                    SELECT (ST_PixelAsPoints(ST_Clip(r.rast, 1, ST_Buffer(p.the_geom,-0.01),TRUE,TRUE))).*,p.gid
                    FROM "16102026_swc4_26_100" r
                    JOIN public.ri_utbs_riego p
                    ON ST_Intersects(r.rast, p.the_geom) 
                ) AS p
                WHERE p.val > 0 ;
            
-- estadisticas upf
                INSERT INTO cmpc.estadistica_swc( gid_poligono, fecha, promedio, minimo, maximo,acumulado,desviacion)
                SELECT 
                    p.gid,
                    '2026/10/17' as fecha,
                    AVG(p.val) AS promedio, 
                    MIN(p.val) AS minimo, 
                    MAX(p.val) AS maximo,
                    SUM(p.val) AS acumulado,
                    STDDEV(p.val) AS desviacion
                FROM (
                    SELECT (ST_PixelAsPoints(ST_Clip(r.rast, 1, p.the_geom,TRUE,TRUE))).*,p.gid
                    FROM "17102026_swc4_26_100" r
                    JOIN public.fundos_riego p
                    ON ST_Intersects(r.rast, p.the_geom) 
                ) AS p
                WHERE p.val > 0
                group by p.gid;
                --calculo estadisticas utb
                INSERT INTO cmpc.estadistica_swc_utb(
                    gid_poligono, fecha, valor)
                SELECT 
                    p.gid,
                    '2026/10/17' as fecha,
                    (p.val) AS valor
                FROM (
                    SELECT (ST_PixelAsPoints(ST_Clip(r.rast, 1, ST_Buffer(p.the_geom,-0.01),TRUE,TRUE))).*,p.gid
                    FROM "17102026_swc4_26_100" r
                    JOIN public.ri_utbs_riego p
                    ON ST_Intersects(r.rast, p.the_geom) 
                ) AS p
                WHERE p.val > 0 ;