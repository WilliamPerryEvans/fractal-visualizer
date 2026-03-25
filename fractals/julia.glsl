#version 330

uniform vec2 u_resolution;
uniform vec2 u_center;
uniform float u_zoom;
uniform int u_max_iter;

out vec4 fragColor;

vec3 palette(float t) {
    vec3 a = vec3(0.5, 0.5, 0.5);
    vec3 b = vec3(0.5, 0.5, 0.5);
    vec3 c = vec3(1.0, 1.0, 1.0);
    vec3 d = vec3(0.0, 0.33, 0.67);
    return a + b * cos(6.28318 * (c * t + d));
}

void main() {
    vec2 uv = (gl_FragCoord.xy - u_resolution * 0.5) / u_resolution.y;

    // z starts at the pixel position; c is a fixed parameter
    vec2 z = u_center + uv * u_zoom;
    vec2 c = vec2(-0.7269, 0.1889);

    int iter = 0;
    for (int i = 0; i < 1024; i++) {
        if (i >= u_max_iter) break;
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
