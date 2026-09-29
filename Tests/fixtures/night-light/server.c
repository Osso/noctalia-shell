/* Private gamma fixture adapted from the isolated wlsunset 0.4.0 reproduction.
 * SPDX-License-Identifier: MIT (gamma protocol XML in this directory carries its own license).
 */
#define _POSIX_C_SOURCE 200809L
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <unistd.h>
#include <wayland-server.h>
#include "gamma-server.h"

#define RAMP_SIZE 256
static struct wl_display *display;
static struct wl_resource *owner;
static unsigned acquisitions, failures, releases, ramps;

static void stop_server(int signum) {
    (void)signum;
    wl_display_terminate(display);
}

static void control_gone(struct wl_resource *resource) {
    if (resource == owner) {
        owner = NULL;
        printf("RELEASE count=%u restored=neutral\n", ++releases);
    }
}

static void control_destroy(struct wl_client *client, struct wl_resource *resource) {
    (void)client;
    wl_resource_destroy(resource);
}

static void set_gamma(struct wl_client *client, struct wl_resource *resource, int32_t fd) {
    (void)client;
    uint16_t data[RAMP_SIZE * 3];
    ssize_t count = pread(fd, data, sizeof data, 0);
    close(fd);
    if (resource != owner || count != sizeof data) {
        wl_resource_post_error(resource, ZWLR_GAMMA_CONTROL_V1_ERROR_INVALID_GAMMA, "invalid ramp");
        return;
    }
    printf("RAMP count=%u red_last=%u green_last=%u blue_last=%u\n", ++ramps,
           data[RAMP_SIZE - 1], data[2 * RAMP_SIZE - 1], data[3 * RAMP_SIZE - 1]);
}

static const struct zwlr_gamma_control_v1_interface control_impl = {
    .set_gamma = set_gamma, .destroy = control_destroy,
};

static void get_control(struct wl_client *client, struct wl_resource *manager,
                        uint32_t id, struct wl_resource *output) {
    (void)manager;
    if (wl_resource_get_client(output) != client) {
        wl_client_post_implementation_error(client, "foreign output");
        return;
    }
    struct wl_resource *control = wl_resource_create(client, &zwlr_gamma_control_v1_interface, 1, id);
    if (!control) { wl_client_post_no_memory(client); return; }
    wl_resource_set_implementation(control, &control_impl, NULL, control_gone);
    if (owner) {
        printf("FAILED count=%u\n", ++failures);
        zwlr_gamma_control_v1_send_failed(control);
        return;
    }
    owner = control;
    printf("ACQUIRE count=%u\n", ++acquisitions);
    zwlr_gamma_control_v1_send_gamma_size(control, RAMP_SIZE);
}

static void manager_destroy(struct wl_client *client, struct wl_resource *manager) {
    (void)client;
    wl_resource_destroy(manager);
}

static const struct zwlr_gamma_control_manager_v1_interface manager_impl = {
    .get_gamma_control = get_control, .destroy = manager_destroy,
};

static void bind_manager(struct wl_client *client, void *data, uint32_t version, uint32_t id) {
    (void)data;
    struct wl_resource *manager = wl_resource_create(client, &zwlr_gamma_control_manager_v1_interface, version, id);
    if (!manager) { wl_client_post_no_memory(client); return; }
    wl_resource_set_implementation(manager, &manager_impl, NULL, NULL);
}

static void bind_output(struct wl_client *client, void *data, uint32_t version, uint32_t id) {
    (void)data;
    struct wl_resource *output = wl_resource_create(client, &wl_output_interface, version, id);
    if (!output) { wl_client_post_no_memory(client); return; }
    wl_output_send_geometry(output, 0, 0, 600, 340, WL_OUTPUT_SUBPIXEL_UNKNOWN, "fixture", "virtual", WL_OUTPUT_TRANSFORM_NORMAL);
    wl_output_send_mode(output, WL_OUTPUT_MODE_CURRENT, 1920, 1080, 60000);
    wl_output_send_scale(output, 1);
    wl_output_send_name(output, "REPRO-1");
    wl_output_send_done(output);
}

int main(void) {
    display = wl_display_create();
    if (!display) return 1;
    if (!wl_global_create(display, &wl_output_interface, 4, NULL, bind_output) ||
        !wl_global_create(display, &zwlr_gamma_control_manager_v1_interface, 1, NULL, bind_manager)) return 2;
    if (wl_display_add_socket(display, "repro-gamma") != 0) return 3;
    struct sigaction action = { .sa_handler = stop_server };
    sigaction(SIGTERM, &action, NULL);
    setvbuf(stdout, NULL, _IOLBF, 0);
    puts("READY");
    wl_display_run(display);
    wl_display_destroy_clients(display);
    wl_display_destroy(display);
    return 0;
}
