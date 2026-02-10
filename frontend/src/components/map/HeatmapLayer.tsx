"use client";

import { useEffect, useState } from "react";
import type maplibregl from "maplibre-gl";
import { getHeatmapData, type HeatmapResponse } from "@/lib/api";

interface HeatmapLayerProps {
  map: maplibregl.Map | null;
  operationType?: string;
}

const SOURCE_ID = "price-heatmap";
const LAYER_ID = "price-heatmap-layer";

export default function HeatmapLayer({
  map,
  operationType = "sale",
}: HeatmapLayerProps) {
  const [data, setData] = useState<HeatmapResponse | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const heatmap = await getHeatmapData(operationType);
        setData(heatmap);
      } catch {
        // fail silently
      }
    };
    load();
  }, [operationType]);

  useEffect(() => {
    if (!map || !data || data.points.length === 0) return;

    // Remove existing layers/sources
    if (map.getLayer(LAYER_ID)) map.removeLayer(LAYER_ID);
    if (map.getSource(SOURCE_ID)) map.removeSource(SOURCE_ID);

    // Convert points to GeoJSON
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

    map.addSource(SOURCE_ID, {
      type: "geojson",
      data: geojson,
    });

    map.addLayer({
      id: LAYER_ID,
      type: "heatmap",
      source: SOURCE_ID,
      paint: {
        // Weight based on the weight property
        "heatmap-weight": [
          "interpolate",
          ["linear"],
          ["get", "weight"],
          0, 0,
          1, 1,
        ],
        // Increase intensity as zoom level increases
        "heatmap-intensity": [
          "interpolate",
          ["linear"],
          ["zoom"],
          10, 0.5,
          14, 2,
        ],
        // Color ramp from transparent to intense
        "heatmap-color": [
          "interpolate",
          ["linear"],
          ["heatmap-density"],
          0, "rgba(0, 0, 0, 0)",
          0.1, "rgba(99, 102, 241, 0.15)",
          0.2, "rgba(99, 102, 241, 0.3)",
          0.4, "rgba(79, 70, 229, 0.5)",
          0.6, "rgba(245, 158, 11, 0.6)",
          0.8, "rgba(239, 68, 68, 0.7)",
          1, "rgba(220, 38, 38, 0.85)",
        ],
        // Radius increases with zoom
        "heatmap-radius": [
          "interpolate",
          ["linear"],
          ["zoom"],
          10, 20,
          12, 30,
          14, 50,
        ],
        // Opacity decreases slightly at higher zoom
        "heatmap-opacity": [
          "interpolate",
          ["linear"],
          ["zoom"],
          10, 0.9,
          14, 0.7,
        ],
      },
    });

    return () => {
      if (map.getLayer(LAYER_ID)) map.removeLayer(LAYER_ID);
      if (map.getSource(SOURCE_ID)) map.removeSource(SOURCE_ID);
    };
  }, [map, data]);

  return null;
}
