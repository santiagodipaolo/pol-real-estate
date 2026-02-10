"use client";

import { useRef, useEffect, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

interface MapContainerProps {
  className?: string;
  center?: [number, number];
  zoom?: number;
  onMapReady?: (map: maplibregl.Map) => void;
  children?: React.ReactNode;
}

// CABA centroid
const CABA_CENTER: [number, number] = [-58.4450, -34.6140];

// Strict CABA bounding box with minimal padding
const CABA_BOUNDS: [[number, number], [number, number]] = [
  [-58.54, -34.71], // SW
  [-58.33, -34.53], // NE
];

const STYLE_URL =
  process.env.NEXT_PUBLIC_MAPLIBRE_STYLE ||
  "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

export default function MapContainer({
  className = "w-full h-full",
  center = CABA_CENTER,
  zoom = 12,
  onMapReady,
  children,
}: MapContainerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: STYLE_URL,
      center,
      zoom,
      minZoom: 11,
      maxZoom: 18,
      maxBounds: CABA_BOUNDS,
      attributionControl: false,
      fadeDuration: 100,
    });

    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-left");

    map.on("load", () => {
      setIsReady(true);
      onMapReady?.(map);
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className={`relative ${className}`}>
      <div ref={containerRef} className="w-full h-full rounded-2xl" />
      {!isReady && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-900 rounded-2xl">
          <div className="flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-slate-400 text-sm">Cargando mapa...</p>
          </div>
        </div>
      )}
      {children}
    </div>
  );
}
