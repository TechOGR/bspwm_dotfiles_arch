#!/bin/sh
# TechOGR login: run the LightDM greeter with WebKit's GPU paths off.
# WebKitGTK 2.4x+ renders through DMA-BUF/EGL; under vmwgfx (VMware) and
# other weak GL stacks the greeter window then stays a solid color and
# the theme is never painted. Software rendering is plenty for a login.
export WEBKIT_DISABLE_DMABUF_RENDERER=1
export WEBKIT_DISABLE_COMPOSITING_MODE=1
exec "$@"
