"use client";

import { useEffect, useState, useCallback } from "react";
import type maplibregl from "maplibre-gl";
import { getChoropleth, type GeoJSONFeatureCollection } from "@/lib/api";

interface ChoroplethLayerProps {
  map: maplibregl.Map | null;
  metric?: string;
  operationType?: string;
  onBarrioClick?: (properties: Record<string, unknown>) => void;
}

const COLOR_SCALE = [
  "#f7fcf5",
  "#e5f5e0",
  "#c7e9c0",
  "#a1d99b",
  "#74c476",
  "#41ab5d",
  "#238b45",
  "#006d2c",
  "#00441b",
];

const SOURCE_ID = "barrios-choropleth";
const LAYER_ID = "barrios-fill";
const OUTLINE_LAYER_ID = "barrios-outline";

export default function ChoroplethLayer({
  map,
  metric = "median_price_usd_m2",
  operationType = "sale",
  onBarrioClick,
}: ChoroplethLayerProps) {
  const [data, setData] = useState<GeoJSONFeatureCollection | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const geojson = await getChoropleth(metric, operationType);
        setData(geojson);
      } catch {
        // fail silently
      }
    };
    load();
  }, [metric, operationType]);

  const handleClick = useCallback(
    (e: maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }) => {
      if (e.features && e.features.length > 0) {
        onBarrioClick?.(e.features[0].properties as Record<string, unknown>);
      }
    },
    [onBarrioClick]
  );

  useEffect(() => {
    if (!map || !data) return;

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
        "fill-opacity": 0.7,
      },
    });

    map.addLayer({
      id: OUTLINE_LAYER_ID,
      type: "line",
      source: SOURCE_ID,
      paint: {
        "line-color": "#333",
        "line-width": 1,
        "line-opacity": 0.5,
      },
    });

    map.on("click", LAYER_ID, handleClick);

    map.on("mouseenter", LAYER_ID, () => {
      map.getCanvas().style.cursor = "pointer";
    });

    map.on("mouseleave", LAYER_ID, () => {
      map.getCanvas().style.cursor = "";
    });

    return () => {
      map.off("click", LAYER_ID, handleClick);
    };
  }, [map, data, handleClick]);

  return null;
}
