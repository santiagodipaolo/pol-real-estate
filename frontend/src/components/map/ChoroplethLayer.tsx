"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import maplibregl from "maplibre-gl";
import { getChoropleth, type GeoJSONFeatureCollection } from "@/lib/api";

interface ChoroplethLayerProps {
  map: maplibregl.Map | null;
  metric?: string;
  operationType?: string;
  propertyType?: string;
  onBarrioClick?: (properties: Record<string, unknown>) => void;
  onBarrioHover?: (properties: Record<string, unknown> | null) => void;
}

// Vibrant sequential palette for dark map backgrounds
const COLOR_SCALE = [
  "#0d1b2a",
  "#1b3a5c",
  "#1a6b8a",
  "#1d9a8c",
  "#3ec47e",
  "#7ddf64",
  "#c5e84d",
  "#ffe23b",
  "#ffb627",
];

const METRIC_LABELS: Record<string, string> = {
  median_price_usd_m2: "Mediana USD/m\u00b2",
  avg_price_usd_m2: "Promedio USD/m\u00b2",
  listing_count: "Listings",
  avg_days_on_market: "D\u00edas en mercado",
  rental_yield_estimate: "Rental Yield",
};

const SOURCE_ID = "barrios-choropleth";
const LAYER_ID = "barrios-fill";
const OUTLINE_LAYER_ID = "barrios-outline";
const HOVER_LAYER_ID = "barrios-hover";

function formatMetricValue(value: number | null | undefined, metric: string): string {
  if (value == null) return "\u2014";
  if (metric === "listing_count") return String(Math.round(value));
  if (metric === "rental_yield_estimate") return `${value.toFixed(1)}%`;
  if (metric === "avg_days_on_market") return `${Math.round(value)}d`;
  return `$${value.toLocaleString("es-AR", { maximumFractionDigits: 0 })}`;
}

export default function ChoroplethLayer({
  map,
  metric = "median_price_usd_m2",
  operationType = "sale",
  propertyType,
  onBarrioClick,
  onBarrioHover,
}: ChoroplethLayerProps) {
  const [data, setData] = useState<GeoJSONFeatureCollection | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const hoveredIdRef = useRef<number | string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const geojson = await getChoropleth(metric, operationType, propertyType);
        setData(geojson);
      } catch {
        // fail silently
      }
    };
    load();
  }, [metric, operationType, propertyType]);

  const handleClick = useCallback(
    (e: maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }) => {
      if (!map || !e.features || e.features.length === 0) return;
      const props = e.features[0].properties as Record<string, unknown>;
      onBarrioClick?.(props);
    },
    [map, onBarrioClick]
  );

  useEffect(() => {
    if (!map || !data) return;

    // Create popup (reusable, no close button)
    const popup = new maplibregl.Popup({
      closeButton: false,
      closeOnClick: false,
      className: "barrio-popup",
      offset: 12,
      maxWidth: "260px",
    });
    popupRef.current = popup;

    // Compute min/max for color interpolation
    const values = data.features
      .map((f) => f.properties.metric_value ?? f.properties.value)
      .filter((v): v is number => v !== null && v !== undefined);

    const minVal = Math.min(...values);
    const maxVal = Math.max(...values);

    // Build color stops
    const stops: [number, string][] = COLOR_SCALE.map((color, i) => [
      minVal + (maxVal - minVal) * (i / (COLOR_SCALE.length - 1)),
      color,
    ]);

    // Remove existing layers/sources
    if (map.getLayer(HOVER_LAYER_ID)) map.removeLayer(HOVER_LAYER_ID);
    if (map.getLayer(LAYER_ID)) map.removeLayer(LAYER_ID);
    if (map.getLayer(OUTLINE_LAYER_ID)) map.removeLayer(OUTLINE_LAYER_ID);
    if (map.getSource(SOURCE_ID)) map.removeSource(SOURCE_ID);

    map.addSource(SOURCE_ID, {
      type: "geojson",
      data: data as unknown as GeoJSON.FeatureCollection,
    });

    map.addLayer({
      id: LAYER_ID,
      type: "fill",
      source: SOURCE_ID,
      paint: {
        "fill-color": [
          "interpolate",
          ["linear"],
          ["coalesce", ["get", "metric_value"], ["get", "value"], 0],
          ...stops.flat(),
        ],
        "fill-opacity": [
          "case",
          ["boolean", ["feature-state", "hover"], false],
          0.92,
          0.7,
        ],
      },
    });

    map.addLayer({
      id: OUTLINE_LAYER_ID,
      type: "line",
      source: SOURCE_ID,
      paint: {
        "line-color": "rgba(255, 255, 255, 0.15)",
        "line-width": 0.8,
      },
    });

    // Hover highlight border
    map.addLayer({
      id: HOVER_LAYER_ID,
      type: "line",
      source: SOURCE_ID,
      paint: {
        "line-color": "#ffffff",
        "line-width": [
          "case",
          ["boolean", ["feature-state", "hover"], false],
          2.5,
          0,
        ],
        "line-opacity": [
          "case",
          ["boolean", ["feature-state", "hover"], false],
          0.9,
          0,
        ],
      },
    });

    // --- Mouse events ---
    const handleMouseMove = (e: maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }) => {
      if (!e.features || e.features.length === 0) return;

      map.getCanvas().style.cursor = "pointer";

      const feature = e.features[0];
      const fid = feature.id as number | string;
      const props = feature.properties;

      // Update feature state for hover effect
      if (hoveredIdRef.current !== null && hoveredIdRef.current !== fid) {
        map.setFeatureState({ source: SOURCE_ID, id: hoveredIdRef.current }, { hover: false });
      }
      map.setFeatureState({ source: SOURCE_ID, id: fid }, { hover: true });
      hoveredIdRef.current = fid;

      // Notify parent
      onBarrioHover?.(props as Record<string, unknown>);

      // Build popup HTML
      const name = props?.name || props?.barrio_name || "Barrio";
      const val = props?.metric_value ?? props?.value;
      const listings = props?.listing_count;
      const metricLabel = METRIC_LABELS[metric] || metric;
      const formatted = formatMetricValue(val != null ? Number(val) : null, metric);

      popup.setLngLat(e.lngLat).setHTML(`
        <div class="barrio-tooltip">
          <div class="barrio-tooltip-name">${name}</div>
          <div class="barrio-tooltip-row">
            <span class="barrio-tooltip-label">${metricLabel}</span>
            <span class="barrio-tooltip-value">${formatted}</span>
          </div>
          ${listings != null ? `
          <div class="barrio-tooltip-row">
            <span class="barrio-tooltip-label">Publicaciones</span>
            <span class="barrio-tooltip-count">${listings}</span>
          </div>` : ""}
          <div class="barrio-tooltip-hint">Click para ver detalle</div>
        </div>
      `).addTo(map);
    };

    const handleMouseLeave = () => {
      map.getCanvas().style.cursor = "";
      popup.remove();
      if (hoveredIdRef.current !== null) {
        map.setFeatureState({ source: SOURCE_ID, id: hoveredIdRef.current }, { hover: false });
        hoveredIdRef.current = null;
      }
      onBarrioHover?.(null);
    };

    map.on("click", LAYER_ID, handleClick);
    map.on("mousemove", LAYER_ID, handleMouseMove);
    map.on("mouseleave", LAYER_ID, handleMouseLeave);

    return () => {
      popup.remove();
      map.off("click", LAYER_ID, handleClick);
      map.off("mousemove", LAYER_ID, handleMouseMove);
      map.off("mouseleave", LAYER_ID, handleMouseLeave);
    };
  }, [map, data, metric, handleClick, onBarrioHover]);

  return null;
}
