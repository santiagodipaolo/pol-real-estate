"use client";

import { useEffect, useState, useRef } from "react";
import maplibregl from "maplibre-gl";
import { getHeatmapData, getChoropleth, type HeatmapResponse, type GeoJSONFeatureCollection } from "@/lib/api";

interface HeatmapLayerProps {
  map: maplibregl.Map | null;
  operationType?: string;
  propertyType?: string;
  onBarrioHover?: (properties: Record<string, unknown> | null) => void;
}

const SOURCE_ID = "price-heatmap";
const LAYER_ID = "price-heatmap-layer";

// Invisible interaction layer IDs
const INTERACT_SOURCE = "heatmap-barrio-interact";
const INTERACT_FILL = "heatmap-barrio-fill";

export default function HeatmapLayer({
  map,
  operationType = "sale",
  propertyType,
  onBarrioHover,
}: HeatmapLayerProps) {
  const [data, setData] = useState<HeatmapResponse | null>(null);
  const [barrioData, setBarrioData] = useState<GeoJSONFeatureCollection | null>(null);
  const [loading, setLoading] = useState(true);
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const hoveredIdRef = useRef<number | string | null>(null);

  // Fetch both heatmap points AND choropleth polygons for interaction
  useEffect(() => {
    setLoading(true);
    const load = async () => {
      try {
        const [heatmap, choropleth] = await Promise.all([
          getHeatmapData(operationType, undefined, propertyType),
          getChoropleth("median_price_usd_m2", operationType, propertyType),
        ]);
        setData(heatmap);
        setBarrioData(choropleth);
      } catch {
        // fail silently
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [operationType, propertyType]);

  // Heatmap layer
  useEffect(() => {
    if (!map || !data || data.points.length === 0) return;

    if (map.getLayer(LAYER_ID)) map.removeLayer(LAYER_ID);
    if (map.getSource(SOURCE_ID)) map.removeSource(SOURCE_ID);

    const geojson: GeoJSON.FeatureCollection = {
      type: "FeatureCollection",
      features: data.points.map((p) => ({
        type: "Feature" as const,
        geometry: {
          type: "Point" as const,
          coordinates: [p.lon, p.lat],
        },
        properties: {
          weight: p.weight,
        },
      })),
    };

    map.addSource(SOURCE_ID, { type: "geojson", data: geojson });

    map.addLayer({
      id: LAYER_ID,
      type: "heatmap",
      source: SOURCE_ID,
      paint: {
        "heatmap-weight": [
          "interpolate", ["linear"], ["get", "weight"],
          0, 0, 0.15, 0.1, 0.5, 0.45, 1, 1,
        ],
        "heatmap-intensity": [
          "interpolate", ["linear"], ["zoom"],
          10, 0.6, 12, 1.2, 14, 2.0, 16, 3.0,
        ],
        "heatmap-color": [
          "interpolate", ["linear"], ["heatmap-density"],
          0,    "rgba(0, 0, 0, 0)",
          0.05, "rgba(10, 20, 60, 0.3)",
          0.1,  "rgba(20, 80, 180, 0.45)",
          0.2,  "rgba(0, 180, 220, 0.55)",
          0.3,  "rgba(0, 230, 200, 0.6)",
          0.4,  "rgba(80, 250, 160, 0.65)",
          0.5,  "rgba(180, 255, 80, 0.7)",
          0.6,  "rgba(255, 230, 40, 0.75)",
          0.7,  "rgba(255, 180, 20, 0.8)",
          0.8,  "rgba(255, 120, 30, 0.85)",
          0.9,  "rgba(240, 50, 50, 0.9)",
          1,    "rgba(200, 20, 60, 0.95)",
        ],
        "heatmap-radius": [
          "interpolate", ["linear"], ["zoom"],
          10, 20, 11, 30, 12, 45, 13, 60, 14, 75, 15, 95, 16, 115,
        ],
        "heatmap-opacity": [
          "interpolate", ["linear"], ["zoom"],
          10, 0.9, 14, 0.8, 16, 0.65,
        ],
      },
    });

    return () => {
      if (map.getLayer(LAYER_ID)) map.removeLayer(LAYER_ID);
      if (map.getSource(SOURCE_ID)) map.removeSource(SOURCE_ID);
    };
  }, [map, data]);

  // Transparent barrio interaction layer on top of heatmap
  useEffect(() => {
    if (!map || !barrioData) return;

    const popup = new maplibregl.Popup({
      closeButton: false,
      closeOnClick: false,
      className: "barrio-popup",
      offset: 12,
      maxWidth: "260px",
    });
    popupRef.current = popup;

    if (map.getLayer(INTERACT_FILL)) map.removeLayer(INTERACT_FILL);
    if (map.getSource(INTERACT_SOURCE)) map.removeSource(INTERACT_SOURCE);

    map.addSource(INTERACT_SOURCE, {
      type: "geojson",
      data: barrioData as unknown as GeoJSON.FeatureCollection,
    });

    // Fully transparent fill — only for hover detection
    map.addLayer({
      id: INTERACT_FILL,
      type: "fill",
      source: INTERACT_SOURCE,
      paint: {
        "fill-color": "#ffffff",
        "fill-opacity": [
          "case",
          ["boolean", ["feature-state", "hover"], false],
          0.08,
          0,
        ],
      },
    });

    const handleMouseMove = (e: maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }) => {
      if (!e.features || e.features.length === 0) return;

      map.getCanvas().style.cursor = "pointer";
      const feature = e.features[0];
      const fid = feature.id as number | string;
      const props = feature.properties;

      if (hoveredIdRef.current !== null && hoveredIdRef.current !== fid) {
        map.setFeatureState({ source: INTERACT_SOURCE, id: hoveredIdRef.current }, { hover: false });
      }
      map.setFeatureState({ source: INTERACT_SOURCE, id: fid }, { hover: true });
      hoveredIdRef.current = fid;

      onBarrioHover?.(props as Record<string, unknown>);

      const name = props?.name || props?.barrio_name || "Barrio";
      const val = props?.metric_value ?? props?.value;
      const formatted = val != null
        ? `$${Number(val).toLocaleString("es-AR", { maximumFractionDigits: 0 })}`
        : "\u2014";
      const listings = props?.listing_count;

      popup.setLngLat(e.lngLat).setHTML(`
        <div class="barrio-tooltip">
          <div class="barrio-tooltip-name">${name}</div>
          <div class="barrio-tooltip-row">
            <span class="barrio-tooltip-label">Mediana USD/m\u00b2</span>
            <span class="barrio-tooltip-value">${formatted}</span>
          </div>
          ${listings != null ? `
          <div class="barrio-tooltip-row">
            <span class="barrio-tooltip-label">Publicaciones</span>
            <span class="barrio-tooltip-count">${listings}</span>
          </div>` : ""}
        </div>
      `).addTo(map);
    };

    const handleMouseLeave = () => {
      map.getCanvas().style.cursor = "";
      popup.remove();
      if (hoveredIdRef.current !== null) {
        map.setFeatureState({ source: INTERACT_SOURCE, id: hoveredIdRef.current }, { hover: false });
        hoveredIdRef.current = null;
      }
      onBarrioHover?.(null);
    };

    map.on("mousemove", INTERACT_FILL, handleMouseMove);
    map.on("mouseleave", INTERACT_FILL, handleMouseLeave);

    return () => {
      popup.remove();
      map.off("mousemove", INTERACT_FILL, handleMouseMove);
      map.off("mouseleave", INTERACT_FILL, handleMouseLeave);
      if (map.getLayer(INTERACT_FILL)) map.removeLayer(INTERACT_FILL);
      if (map.getSource(INTERACT_SOURCE)) map.removeSource(INTERACT_SOURCE);
    };
  }, [map, barrioData, onBarrioHover]);

  if (loading && !data) {
    return null;
  }

  return null;
}
