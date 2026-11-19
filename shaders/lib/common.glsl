/*
    Copyright (c) 2024 Josh Britain (jbritain)
    Licensed under a custom non-commercial license.
    See LICENSE for full terms.

     __   __ __   ______   __  __   ______   __           __   __ __   ______   ______   ______   __   __   ______   ______    
    /\ \ / //\ \ /\  ___\ /\ \/\ \ /\  __ \ /\ \         /\ \ / //\ \ /\  == \ /\  == \ /\  __ \ /\ "-.\ \ /\  ___\ /\  ___\   
    \ \ \'/ \ \ \\ \___  \\ \ \_\ \\ \  __ \\ \ \____    \ \ \'/ \ \ \\ \  __< \ \  __< \ \  __ \\ \ \-.  \\ \ \____\ \  __\   
     \ \__|  \ \_\\/\_____\\ \_____\\ \_\ \_\\ \_____\    \ \__|  \ \_\\ \_____\\ \_\ \_\\ \_\ \_\\ \_\\"\_\\ \_____\\ \_____\ 
      \/_/    \/_/ \/_____/ \/_____/ \/_/\/_/ \/_____/     \/_/    \/_/ \/_____/ \/_/ /_/ \/_/\/_/ \/_/ \/_/ \/_____/ \/_____/ 
                                                                                                                        
    
    By jbritain
    https://jbritain.net
                                            
*/

#ifndef COMMON_GLSL
#define COMMON_GLSL

#include "/lib/common/settings.glsl"

#include "/lib/common/debug.glsl"

#include "/lib/common/syntax.glsl"
#ifdef VOXY
#define dhRenderDistance vxRenderDistance
#define dhProjection vxProj
#define dhProjectionInverse vxProjInv
#define dhDepthTex0 vxDepthTexTrans
#define dhDepthTex1 vxDepthTexOpaque
#endif

#ifndef GBUFFERS_VOXY
#include "/lib/common/uniforms.glsl"
#else
vec2 resolution = vec2(viewWidth, viewHeight);
vec2 EB = vec2(eyeBrightness) / 240.0;
vec2 EBS = vec2(eyeBrightnessSmooth) / 240.0;
#endif
#include "/lib/common/util.glsl"

#include "/lib/common/materialIDs.glsl"
#include "/lib/common/material.glsl"
#include "/lib/common/spaceConversions.glsl"


#define worldTimeCounter ((worldTime / 20.0) + (worldDay * 1200.0))

const float sunAngularRadius = PI/90.0;
const float moonAngularRadius = 2.5 * PI / 180.0;

vec3 sunIrradiance = fogColor * vec3(4.0, 2.0, 1.0) * 0.5;
vec3 sunRadiance = sunIrradiance / sunAngularRadius;
const vec3 moonIrradiance = vec3(0.01, 0.01, 0.05) * 4.0;

const float wetnessHalflife = 25.0;
const float drynessHalflife = 25.0;

#ifdef IS_MONOCLE
monocle_not_supported
#endif

vec3 sunDir = normalize(sunPosition);
vec3 worldSunDir = mat3(gbufferModelViewInverse) * sunDir;

vec3 lightDir = normalize(shadowLightPosition);
vec3 worldLightDir = mat3(gbufferModelViewInverse) * lightDir;

bool isDay = sunDir == lightDir;
#define isNight !isDay

#ifndef GBUFFERS_VOXY
layout(std430, binding = 0) buffer environmentData {
    vec3 sunlightColor;
    vec3 skylightColor;
    float weatherFrameTimeCounter; // only increments when it is raining
    uint encodedHeldLightColor;
};

layout(std430, binding = 1) buffer smoothedData {
    float sunVisibilitySmooth;
};
#endif

float skyMultiplier = clamp01(constantMood > 0.9 ? 0.0 : 1.0);

const bool colortex3Clear = false;

// BUFFER FORMATS
/*
    const int colortex0Format = RGB16F;
    const int colortex5Format = R8;
*/

#ifdef BLOOM
/*
    const int colortex2Format = RGB16F;
*/
#endif

#ifdef TEMPORAL_FILTER
/*
    const int colortex3Format = RGB16F;
*/
#endif

const vec4 colortex4ClearColor = vec4(1.0, 1.0, 1.0, 1.0);

/*
    const int colortex4Format = RGB8;
*/

#if defined DISTANT_HORIZONS || defined VOXY
/*
    const int colortex6Format = R16;
*/
#endif

#ifdef ROUGH_SKY_REFLECTIONS
/*
    const int colortex7Format = R11F_G11F_B10F;
*/
const bool colortex7Clear = false;
#endif

#ifdef INFINITE_OCEAN
#endif

#ifdef VANILLA_CLOUD_TEXTURE
#endif

#ifdef INTEGRATED_EMISSION
#endif

#endif // COMMON_GLSL