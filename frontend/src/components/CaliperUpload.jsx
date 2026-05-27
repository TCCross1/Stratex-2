import React, { useRef, useState } from "react";
import { Camera, Loader2, Check, AlertCircle, Upload } from "lucide-react";
import { api } from "@/lib/api";
import { toast } from "sonner";

/**
 * CaliperUpload — phone-camera capture for a Mitutoyo digital-caliper photo.
 * The backend (Gemini Vision via Emergent LLM Key) reads the display and
 * returns the thickness in mm + inches.
 *
 * Props:
 *   - onReading({thickness_mm, thickness_in, confidence}) — fires after a
 *     successful OCR. Parent component decides what to do (store, attach to
 *     a quote, etc).
 */
export default function CaliperUpload({ onReading }) {
  const fileRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handle = async (file) => {
    if (!file) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      toast.error("Use a JPEG, PNG, or WEBP photo of the calipers display.");
      return;
    }
    setBusy(true); setError(null); setResult(null);
    try {
      // Read as base64 (strip data: prefix server-side)
      const buf = await file.arrayBuffer();
      const bytes = new Uint8Array(buf);
      let bin = "";
      for (let i = 0; i < bytes.byteLength; i++) bin += String.fromCharCode(bytes[i]);
      const b64 = btoa(bin);
      const { data } = await api.post("/contractor/caliper-ocr", {
        image_base64: b64,
        mime_type: file.type,
      });
      if (data.ok && data.thickness_mm) {
        setResult(data);
        onReading?.(data);
        toast.success(`Calipers read: ${data.thickness_mm.toFixed(3)} mm (${data.thickness_in.toFixed(4)} in)`);
      } else {
        setError(data.message || "Could not read the calipers display — try again or enter manually.");
        toast.error("Calipers display unreadable.");
      }
    } catch (e) {
      const msg = e?.response?.data?.detail || e.message || "Upload failed";
      setError(msg);
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="border border-[#00F0FF]/25 bg-[#0B0F19] p-4" data-testid="caliper-upload">
      <div className="flex items-center gap-3 mb-3">
        <Camera size={16} className="text-teal" style={{ filter: "drop-shadow(0 0 4px rgba(0,240,255,0.55))" }} />
        <span className="font-mono text-[11px] tracking-widest uppercase text-silver">
          Shingle Thickness — Calipers OCR
        </span>
      </div>
      <p className="text-[11px] text-muted-hud font-body mb-4 leading-snug">
        Snap a photo of the digital calipers display measuring the shingle. STRATEX Vision will
        read the value automatically (Gemini Vision) — no typing required.
      </p>
      <input
        ref={fileRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        capture="environment"
        className="hidden"
        onChange={(e) => handle(e.target.files?.[0])}
        data-testid="caliper-upload-input"
      />
      <div className="flex flex-wrap gap-3 items-center">
        <button
          onClick={() => fileRef.current?.click()}
          disabled={busy}
          className="btn-hud disabled:opacity-50 disabled:cursor-not-allowed"
          data-testid="caliper-upload-btn"
        >
          {busy ? (<><Loader2 size={14} className="animate-spin" /> Reading…</>) : (<><Upload size={14} /> Capture Photo</>)}
        </button>
        {result && (
          <div className="flex items-center gap-2 px-3 py-1.5 border border-[#00F0FF]/45 font-mono text-[11px] tracking-widest uppercase text-teal" data-testid="caliper-result">
            <Check size={12} />
            <span>{result.thickness_mm?.toFixed(3)} mm · {result.thickness_in?.toFixed(4)} in</span>
            <span className="text-muted-hud">· conf {result.confidence}</span>
          </div>
        )}
        {error && (
          <div className="flex items-center gap-2 px-3 py-1.5 border border-plasma/50 font-mono text-[11px] tracking-widest uppercase text-plasma">
            <AlertCircle size={12} />
            <span>{error}</span>
          </div>
        )}
      </div>
    </div>
  );
}
