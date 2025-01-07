odoo.define("hr_task_planner.timeline_renderer", function (require) {
    "use strict";

    const TimelineRenderer = require("web_timeline.TimelineRenderer");

    TimelineRenderer.include({
        events: _.extend({}, TimelineRenderer.prototype.events, {
            "click .oe_hr_task_planner_new_task": "_onNewTask",
        }),
        _onNewTask: function (ev) {
            ev.preventDefault();
            this.on_add(ev, () => {
                console.log("on_add");
            });
        },
    });
});
