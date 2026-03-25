#version 330

uniform vec2 u_resolution;
uniform vec2 u_center;
uniform float u_zoom;
uniform int u_max_iter;

out vec4 fragColor;

// Fiery palette
vec3 palette(float t) {
    vec3 a = vec3(0.5, 0.2, 0.05);
    vec3 b = vec3(0.5, 0.3, 0.15);
    vec3 c = vec3(1.0, 0.8, 0.4);
    vec3 d = vec3(0.0, 0.15, 0.35);
    return a + b * cos(6.28318 * (c * t + d));
}

void main() {
    vec2 uv = (gl_FragCoord.xy - u_resolution * 0.5) / u_resolution.y;
    // Flip imaginary axis so the "ship" faces the right way up
    vec2 c = u_center + vec2(uv.x, -uv.y) * u_zoom;

    vec2 z = vec2(0.0);
    int iter = 0;

    for (int i = 0; i < 1024; i++) {
        if (i >= u_max_iter) break;
        // Burning Ship: take absolute value of both components before squaring
        z = vec2(abs(z.x), abs(z.y));
        z = vec2(z.x * z.x - z.y * z.y, 2.0 * z.x * z.y) + c;
        if (dot(z, z) > 4.0) break;
        iter++;
    }

    if (iter == u_max_iter) {
        fragColor = vec4(0.0, 0.0, 0.0, 1.0);
    } else {
        float smooth_iter = float(iter) - log2(log2(dot(z, z))) + 4.0;
        float t = smooth_iter / float(u_max_iter);
        fragColor = vec4(palette(t), 1.0);
    }
}
