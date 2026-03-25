#version 330

uniform vec2 u_resolution;
uniform vec2 u_center;
uniform float u_zoom;
uniform int u_max_iter;

out vec4 fragColor;

const float S3 = 1.7320508;

// Returns positive if p is to the left of edge a→b (CCW winding)
float edgeSign(vec2 p, vec2 a, vec2 b) {
    return (b.x - a.x) * (p.y - a.y) - (b.y - a.y) * (p.x - a.x);
}

bool inTriangle(vec2 p, vec2 a, vec2 b, vec2 c) {
    float d1 = edgeSign(p, a, b);
    float d2 = edgeSign(p, b, c);
    float d3 = edgeSign(p, c, a);
    bool hasNeg = (d1 < 0.0) || (d2 < 0.0) || (d3 < 0.0);
    bool hasPos = (d1 > 0.0) || (d2 > 0.0) || (d3 > 0.0);
    return !(hasNeg && hasPos);
}

vec3 palette(float t) {
    vec3 a = vec3(0.1, 0.4, 0.3);
    vec3 b = vec3(0.4, 0.4, 0.3);
    vec3 c = vec3(1.0, 0.8, 0.5);
    vec3 d = vec3(0.0, 0.25, 0.55);
    return a + b * cos(6.28318 * (c * t + d));
}

void main() {
    vec2 uv = (gl_FragCoord.xy - u_resolution * 0.5) / u_resolution.y;
    vec2 p = u_center + uv * u_zoom;

    // Starting triangle: circumradius 1, centered at origin
    vec2 v0 = vec2(0.0,         1.0);   // top
    vec2 v1 = vec2(-S3 / 2.0, -0.5);   // bottom-left
    vec2 v2 = vec2( S3 / 2.0, -0.5);   // bottom-right

    // Outside the main triangle → background
    if (!inTriangle(p, v0, v1, v2)) {
        fragColor = vec4(0.05, 0.05, 0.08, 1.0);
        return;
    }

    // Iteratively subdivide. At each level, check if the point falls in
    // the removed middle triangle. If so, colour by depth and stop.
    for (int i = 0; i < 64; i++) {
        if (i >= u_max_iter) break;

        vec2 m01 = (v0 + v1) * 0.5;   // mid left edge
        vec2 m02 = (v0 + v2) * 0.5;   // mid right edge
        vec2 m12 = (v1 + v2) * 0.5;   // mid bottom edge

        // Middle (removed) triangle — this is a gap in the fractal
        if (inTriangle(p, m01, m12, m02)) {
            float t = float(i) / float(u_max_iter);
            fragColor = vec4(palette(t), 1.0);
            return;
        }

        // Navigate into the sub-triangle that contains p
        if (inTriangle(p, v0, m01, m02)) {
            // Top sub-triangle
            v1 = m01;
            v2 = m02;
        } else if (inTriangle(p, m01, v1, m12)) {
            // Bottom-left sub-triangle
            v0 = m01;
            v2 = m12;
        } else {
            // Bottom-right sub-triangle
            v0 = m02;
            v1 = m12;
        }
    }

    // Reached max depth — solidly inside the fractal
    fragColor = vec4(0.0, 0.02, 0.05, 1.0);
}
