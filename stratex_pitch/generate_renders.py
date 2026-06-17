"""
Generate photorealistic CAD-style digital twin renders for the STRATEX
Strategic Briefing pitch deck using Gemini Nano Banana via emergentintegrations.

Output: /app/stratex_pitch/assets/render_*.png

USAGE:  python /app/stratex_pitch/generate_renders.py
"""
import asyncio
import base64
import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage

load_dotenv("/app/backend/.env")

ASSETS = Path("/app/stratex_pitch/assets")
ASSETS.mkdir(parents=True, exist_ok=True)

MODEL = "gemini-3.1-flash-image-preview"

SYSTEM = (
    "You are an architectural CAD visualization engine. You render "
    "photorealistic isometric digital twins of residential roof systems. "
    "Every render must look like a high-end Autodesk Revit or Rhino 3D "
    "render — clean geometry, accurate proportions, soft cinematic lighting, "
    "dark studio background, neon cyan accent lines for edges, no text labels, "
    "no watermarks, no people."
)

# Each tuple: (filename, prompt)
RENDERS = [
    (
        "render_full_twin.png",
        "A photorealistic isometric 3D digital twin render of a complete "
        "complex hip-and-valley residential asphalt-shingle roof system. "
        "Charcoal architectural shingles with visible course lines. "
        "Multiple intersecting hip and valley lines, two dormers, a chimney "
        "with proper flashing, ridge vents, drip edges. "
        "Subtle cyan neon wireframe edges overlaying each facet to indicate "
        "scan-measurement points. Small red anomaly hotspot on one rear facet "
        "indicating moisture damage. Dark navy studio backdrop, soft rim "
        "lighting from upper-left, slight atmospheric haze. "
        "Render quality: 8K, professional architectural visualization, "
        "Revit + V-Ray style. Camera 35-degree elevated isometric. "
        "ABSOLUTELY NO TEXT, NO LABELS, NO WATERMARKS."
    ),
    (
        "render_layer1_shingle.png",
        "A photorealistic isometric 3D render of ONLY the finished roof "
        "shingle layer of a hip-and-valley residential roof — floating in "
        "dark space as if scanned. Architectural charcoal asphalt shingles "
        "with visible tab pattern, ridge caps, valley metal. Cyan neon "
        "wireframe edges trace each facet polygon. "
        "Layer is shown alone, hovering, slightly tilted, with measurement "
        "callout dots on corners (no text). Dark navy background, soft "
        "studio lighting. Cinematic CAD visualization style. NO TEXT, "
        "NO LABELS, NO WATERMARKS."
    ),
    (
        "render_layer2_decking.png",
        "A photorealistic isometric 3D render of ONLY the plywood roof "
        "decking layer (7/16-inch CDX sheathing) of a hip-and-valley "
        "residential roof — floating in dark space. Visible 4-foot by "
        "8-foot plywood sheet seams in a staggered pattern. Light tan "
        "OSB/plywood texture. Amber/orange neon wireframe edges trace "
        "the seams and perimeter. One sheet on the rear slope is shown "
        "in slightly darker tone indicating rot/moisture (no text labels). "
        "Dark navy background, soft studio lighting. NO TEXT, NO LABELS, "
        "NO WATERMARKS."
    ),
    (
        "render_layer3_framing.png",
        "A photorealistic isometric 3D render of ONLY the structural "
        "framing layer of a hip-and-valley residential roof — floating "
        "in dark space. 2x8 SPF rafters at 16-inch on-center spacing, "
        "main ridge beam, hip rafters meeting at the ridge, ceiling "
        "joists at the bottom, hurricane ties at the wall plate "
        "connections. Light blonde lumber wood texture. Green neon "
        "wireframe edges trace each rafter and the structural connections. "
        "Dark navy background, soft studio lighting, cinematic CAD style. "
        "NO TEXT, NO LABELS, NO WATERMARKS."
    ),
    (
        "render_cut_section.png",
        "A photorealistic isometric architectural cut-section detail "
        "showing a residential eave/overhang assembly cut in half: from "
        "top to bottom — charcoal asphalt shingles, ice-and-water shield "
        "underlayment, 7/16-inch CDX plywood deck, 2x8 SPF rafter, "
        "R-21 batt insulation in the cavity, vented soffit at the bottom, "
        "aluminum drip edge at the fascia. Each layer is clearly visible "
        "in cross-section like an architectural detail drawing. Subtle "
        "cyan neon edges trace each material boundary. Dark navy studio "
        "background, soft cinematic lighting. NO TEXT, NO LABELS, "
        "NO WATERMARKS."
    ),
    (
        "render_drone_capture.png",
        "A photorealistic isometric render of a DJI Matrice 4TD enterprise "
        "quadcopter drone hovering above a complex residential hip-and-valley "
        "asphalt-shingle roof, capturing a photogrammetry scan. Cyan neon "
        "scan-grid lines emanate from the drone's downward LiDAR onto the "
        "roof surface, mapping every facet. The drone has visible RTK GPS "
        "antenna and thermal payload. Twilight sky with slight atmospheric "
        "haze, dramatic side lighting. Cinematic, professional product-shot "
        "quality. NO TEXT, NO LABELS, NO WATERMARKS."
    ),
]


async def gen_one(filename: str, prompt: str) -> bool:
    out = ASSETS / filename
    print(f"  -> {filename}: generating...")
    try:
        chat = LlmChat(
            api_key=os.environ["EMERGENT_LLM_KEY"],
            session_id=f"stratex-render-{uuid.uuid4().hex[:8]}",
            system_message=SYSTEM,
        ).with_model("gemini", MODEL).with_params(modalities=["image", "text"])

        msg = UserMessage(text=prompt)
        text, images = await chat.send_message_multimodal_response(msg)

        if not images:
            print(f"     FAIL: no images returned. text={text[:120] if text else ''}")
            return False

        img_bytes = base64.b64decode(images[0]["data"])
        out.write_bytes(img_bytes)
        print(f"     OK ({len(img_bytes)//1024} KB)")
        return True
    except Exception as e:
        print(f"     ERROR: {e}")
        return False


async def main():
    print(f"Generating {len(RENDERS)} CAD digital twin renders -> {ASSETS}\n")
    ok = 0
    for fname, prompt in RENDERS:
        if await gen_one(fname, prompt):
            ok += 1
    print(f"\nDONE: {ok}/{len(RENDERS)} succeeded")
    return 0 if ok == len(RENDERS) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
