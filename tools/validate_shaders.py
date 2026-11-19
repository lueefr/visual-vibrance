#!/usr/bin/env python3
"""Static Voxy contract checks and offline GLSL compilation (not an in-game test)."""

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "shaders"
WORLDS = ("world0", "world-1", "world1")
STAGES = ("voxy_opaque.glsl", "voxy_translucent.glsl")
INC = re.compile(r'^\s*#include\s+"(/[^"]+)"\s*$', re.MULTILINE)


def check(ok, message):
    if not ok:
        raise ValueError(message)


def expand(name, stack=()):
    relative = Path(name.lstrip("/"))
    check(".." not in relative.parts, f"Include outside shaders: {name}")
    path = (ROOT / relative).resolve()
    check(path.is_relative_to(ROOT.resolve()) and path.is_file(), f"Missing source: {name}")
    check(path not in stack, f"Recursive include: {name}")
    src = path.read_text(encoding="utf8")
    return INC.sub(lambda m: expand(m.group(1), stack + (path,)), src)


def validate():
    conf = json.loads((ROOT / "program/voxy.json").read_text())
    check(conf.get("version") == 1, "Voxy version must be 1")
    check(conf.get("opaqueDrawBuffers") == [0, 1], "Opaque draw buffers changed")
    check(conf.get("translucentDrawBuffers") == [0, 1], "Translucent draw buffers changed")
    check(conf.get("excludeLodsFromVanillaDepth") is True, "Invalid Voxy depth setting")
    check(conf.get("blending", {}).get("1") == "off", "Normal blending must be disabled")
    check("taaOffset" in conf, "Missing Voxy TAA setting")
    uniforms = conf.get("uniforms", [])
    check(len(uniforms) == len(set(uniforms)), "Duplicated uniforms")
    needed = {"vxProj", "vxProjInv", "vxProjPrev", "vxModelView",
              "vxModelViewInv", "vxModelViewPrev", "vxRenderDistance",
              "cameraPosition", "frameCounter", "frameTimeCounter"}
    check(needed <= set(uniforms), f"Missing uniforms: {sorted(needed - set(uniforms))}")
    samplers = conf.get("samplers", {})
    needed = {"depthtex0", "blueNoiseTex", "perlinNoiseTex", "noisetex",
              "shadowtex0HW", "shadowtex1HW", "sunTransmittanceLUTTex",
              "multipleScatteringLUTTex", "skyViewLUTTex"}
    check(needed <= set(samplers), f"Missing samplers: {sorted(needed - set(samplers))}")
    check({"0", "1"} <= set(conf.get("ssbos", {})), "Voxy SSBO configuration incomplete")

    props = (ROOT / "shaders.properties").read_text()
    fog = (ROOT / "lib/atmosphere/fog.glsl").read_text()
    common = (ROOT / "lib/common.glsl").read_text()
    hook = (ROOT / "program/gbuffers_voxy.glsl").read_text()
    check("uniform.float.combined_far = vxRenderDistance" in props, "Voxy projection missing")
    check("#if defined DISTANT_HORIZONS || defined VOXY" in fog, "Voxy fog missing")
    for key in ("vxDepthTexTrans", "vxDepthTexOpaque", "vxProjInv", "vxRenderDistance"):
        check(key in common, f"Missing Voxy integration: {key}")
    for key in ("ATMOSPHERIC_FOG", "CLOUDY_FOG", "MORNING_FOG_DENSITY", "BASE_FOG_DENSITY"):
        check(key in props or key in (ROOT / "lib/common/settings.glsl").read_text(), f"Fog option missing: {key}")
    check("void voxy_emitFragment(VoxyFragmentParameters params)" in hook,
          "Voxy entrypoint missing")

    for name in ("program/composite.glsl", "program/composite1.glsl",
                 "program/composite3.glsl", "program/composite5.glsl",
                 "program/deferred1.glsl"):
        expand(name)
    for world in WORLDS:
        check((ROOT / world / "voxy.json").read_text().strip() ==
              '#include "/program/voxy.json"', f"Invalid Voxy JSON include: {world}")
        for stage in STAGES:
            code = (ROOT / world / stage).read_text()
            check('#include "/program/gbuffers_voxy.glsl"' in code,
                  f"Invalid Voxy hook: {world}/{stage}")
            expand(f"{world}/{stage}")
    print("PASS: Voxy buffers, uniforms, samplers, SSBOs, fog, dimensions, includes")
    return conf


def compile_glsl(conf):
    compiler = shutil.which("glslangValidator")
    check(compiler is not None, "glslangValidator is required (no skipped compilation)")
    # Voxy injects uniforms/samplers/SSBOs before the patch; mirror that here.
    uniforms = expand("lib/common/uniforms.glsl")
    stub = """
uniform mat4 vxProj, vxProjInv, vxProjPrev;
uniform mat4 vxModelView, vxModelViewInv, vxModelViewPrev;
uniform int vxRenderDistance;
uniform sampler2D vxDepthTexTrans, vxDepthTexOpaque;
struct VoxyFragmentParameters {
  vec4 sampledColour; vec2 tile; vec2 uv; uint face;
  uint modelId; vec2 lightMap; vec4 tinting; uint customId;
};
"""
    for index, body in sorted(conf["ssbos"].items()):
        check(index.isdigit() and body.strip().startswith("{") and body.strip().endswith("}"),
              f"Unsupported SSBO {index}")
        stub += f"layout(std430, binding={index}) buffer VoxySSBO{index} {body};\n"
    main = """
void main() {
  VoxyFragmentParameters p;
  p.sampledColour = vec4(1.0);
  p.tinting = vec4(1.0);
  p.lightMap = vec2(1.0);
  p.face = 0u;
  p.customId = 1000u;
  voxy_emitFragment(p);
}
"""
    with tempfile.TemporaryDirectory(prefix="voxy-glsl-") as directory:
        for world in WORLDS:
            for stage in STAGES:
                source = ("#version 460 compatibility\n#define VOXY 1\n" +
                          uniforms + "\n" + stub + "\n" +
                          expand(f"{world}/{stage}") + "\n" + main)
                filename = Path(directory) / f"{world}_{stage}.frag"
                filename.write_text(source)
                result = subprocess.run([compiler, "-S", "frag", str(filename)],
                                        capture_output=True, text=True)
                check(result.returncode == 0,
                      f"GLSL compile error ({world}/{stage}):\n{result.stdout}\n{result.stderr}")
                print(f"PASS: GLSL {world}/{stage}")


def main():
    try:
        compile_glsl(validate())
    except (ValueError, OSError, json.JSONDecodeError) as err:
        print(f"FAIL: {err}", file=sys.stderr)
        return 1
    print("PASS: offline Voxy shader validation completed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
