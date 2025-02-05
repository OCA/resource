/** @odoo-module **/

import {FormViewDialog} from "@web/views/view_dialogs/form_view_dialog";
import {makeContext} from "@web/core/context";
import {patch} from "@web/core/utils/patch";
import {TimelineController} from "@web_timeline/views/timeline/timeline_controller.esm";
import {serializeDateTime} from "@web/core/l10n/dates";
const {DateTime} = luxon;

patch(TimelineController.prototype, {
    /**
     * Triggered when a timeline item gets added and opens a form view.
     *
     * @private
     * @param {Object} item
     * @param {Function} callback
     */
    _onAdd(item, callback) {
        console.log(item);
        // Initialize default values for creation
        const context = {};
        let item_start = false,
            item_end = false;
        item_start = DateTime.now();
        context[`default_${this.date_start}`] = serializeDateTime(item_start);
        if (this.date_delay) {
            context[`default_${this.date_delay}`] = 1;
        }
        if (this.date_stop && item.end) {
            item_end = DateTime.now();
            context[`default_${this.date_stop}`] = serializeDateTime(item_end);
        }
        if (this.date_delay && this.date_stop && item_end) {
            const diff = item_end.diff(item_start, "hours");
            context[`default_${this.date_delay}`] = diff.hours;
        }
        if (item.group > 0) {
            context[`default_${this.model.last_group_bys[0]}`] = item.group;
        }
        // Show popup
        this.dialogService.add(
            FormViewDialog,
            {
                resId: false,
                context: makeContext([context], this.env.searchModel.context),
                onRecordSaved: async (record) => {
                    const new_record = await this.model.create_completed(record.resId);
                    callback(new_record);
                },
                resModel: this.model.model_name,
            },
            {onClose: () => callback()}
        );
    },
});
