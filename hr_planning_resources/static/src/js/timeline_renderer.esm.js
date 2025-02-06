/** @odoo-module **/

import {TimelineRenderer} from "@web_timeline/views/timeline/timeline_renderer.esm";
import {patch} from "@web/core/utils/patch";

patch(TimelineRenderer.prototype, {
    _onNewTask(ev) {
        ev.preventDefault();
        this.on_add(ev, () => {
            console.log("on_add");
        });
    },
});
