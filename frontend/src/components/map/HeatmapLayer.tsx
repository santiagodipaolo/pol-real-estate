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
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const load = async () => {
      try {
        const heatmap = await getHeatmapData(operationType);
        setData(heatmap);
      } catch {
        // fail silently
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [operationType]);

  useEffect(() => {
    if (!map || !data || data.points.length === 0) return;

    // Clean previous
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

    map.addSource(SOURCE_ID, {
      type: "geojson",
      data: geojson,
    });

    map.addLayer({
      id: LAYER_ID,
      type: "heatmap",
      source: SOURCE_ID,
      paint: {
        "heatmap-weight": [
          "interpolate",
          ["linear"],
          ["get", "weight"],
          0, 0,
          0.5, 0.5,
          1, 1,
        ],
        "heatmap-intensity": [
          "interpolate",
          ["linear"],
          ["zoom"],
          10, 0.8,
          12, 1.5,
          14, 2.5,
          16, 3.5,
        ],
        "heatmap-color": [
          "interpolate",
          ["linear"],
          ["heatmap-density"],
          0,    "rgba(0, 0, 0, 0)",
          0.05, "rgba(49, 54, 149, 0.25)",
          0.1,  "rgba(69, 117, 180, 0.4)",
          0.2,  "rgba(116, 173, 209, 0.5)",
          0.3,  "rgba(171, 217, 233, 0.55)",
          0.4,  "rgba(224, 243, 248, 0.6)",
          0.5,  "rgba(255, 255, 191, 0.65)",
          0.6,  "rgba(254, 224, 144, 0.7)",
          0.7,  "rgba(253, 174, 97, 0.75)",
          0.8,  "rgba(244, 109, 67, 0.8)",
          0.9,  "rgba(215, 48, 39, 0.85)",
          1,    "rgba(165, 0, 38, 0.9)",
        ],
        "heatmap-radius": [
          "interpolate",
          ["linear"],
          ["zoom"],
          10, 25,
          11, 35,
          12, 50,
          13, 65,
          14, 80,
          15, 100,
          16, 120,
        ],
        "heatmap-opacity": [
          "interpolate",
          ["linear"],
          ["zoom"],
          10, 0.85,
          14, 0.75,
          16, 0.6,
        ],
      },
    });

    return () => {
      if (map.getLayer(LAYER_ID)) map.removeLayer(LAYER_ID);
      if (map.getSource(SOURCE_ID)) map.removeSource(SOURCE_ID);
    };
  }, [map, data]);

  if (loading && !data) {
    return null;
  }

  return null;
}
