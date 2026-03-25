#version 330

in vec2 in_position;

uniform vec2 u_resolution;
uniform vec2 u_center;
uniform float u_zoom;

void main() {
    // Map from complex-plane coordinates to NDC, matching the fragment shader mapping.
    // In the fragment shaders: c = u_center + (fragCoord - res/2) / res.y * u_zoom
    // So NDC.x = (pos.x - center.x) / (zoom * 0.5 * aspect)
    //    NDC.y = (pos.y - center.y) / (zoom * 0.5)
    float aspect = u_resolution.x / u_resolution.y;
    float nx = (in_position.x - u_center.x) / (u_zoom * 0.5 * aspect);
    float ny = (in_position.y - u_center.y) / (u_zoom * 0.5);
    gl_Position = vec4(nx, ny, 0.0, 1.0);
    gl_PointSize = 1.5;
}
