/** @odoo-module */

import TimelineController from "web_timeline.TimelineController";

TimelineController.include({
    create_completed: function (id) {
        const self = this;
        return this._rpc({
            model: this.model.modelName,
            method: "read",
            args: [id, this.model.fieldNames],
            context: this.context,
        }).then((records) => {
            const new_event = this.renderer.event_data_transform(records[0]);
            const items = this.renderer.timeline.itemsData;
            items.add(new_event);

            self.model.data.data.push(records[0]);
            const params = {
                domain: this.renderer.last_domains,
                context: this.context,
                groupBy: this.renderer.last_group_bys,
            };
            this.update(params, {adjust_window: false});
        });
    },
});
