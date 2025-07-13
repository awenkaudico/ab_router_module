####################################################################### DEV : AWENK AUDICO / SAHIDINAOLA@GMAIL.COM (AWAL KODE) ########################################################################################
import random
import json
from flowork_kernel.api_contract import BaseModule
import ttkbootstrap as ttk
from tkinter import StringVar, IntVar, Listbox, Toplevel, simpledialog, END, LEFT, RIGHT, BOTH, X, Y, TclError
from flowork_kernel.ui_shell.custom_widgets.tooltip import ToolTip
from flowork_kernel.ui_shell.shared_properties import create_debug_and_reliability_ui, create_loop_settings_ui

class ListboxData:
    """Helper class to get data from the listbox."""
    def __init__(self, listbox_widget):
        self.listbox = listbox_widget
    def get(self):
        return [{'name': item.strip()} for item in self.listbox.get(0, END)]

class ABRouterModule(BaseModule):
    TIER = "premium"

    def __init__(self, module_id, services):
        super().__init__(module_id, services)
        self.available_listbox = None
        self.selected_listbox = None
        self.parent_properties_frame = None

    def execute(self, payload, config, status_updater, ui_callback, mode='EXECUTE'):
        routing_variants = config.get('routing_variants', [])
        node_id = config.get('__internal_node_id', self.module_id)

        if not routing_variants:
            status_updater(self.loc.get('ab_router_error_no_presets_configured'), "ERROR")
            self.logger(self.loc.get('ab_router_error_no_presets_configured'), "ERROR")
            return {"payload": payload, "output_name": "output_path"}

        state_key = f"ab_router_cycle_index::{node_id}"
        last_index = self.kernel.state.get(state_key, -1)
        next_index = (last_index + 1) % len(routing_variants)
        selected_preset_info = routing_variants[next_index]
        self.kernel.state.set(state_key, next_index)
        selected_preset_name = selected_preset_info['name']

        status_updater(self.loc.get('ab_router_status_routing', selected_preset_name=selected_preset_name), "INFO")
        self.logger(f"Multi-Variant Router: Merutekan trafik (Giliran ke-{next_index + 1}) ke: {selected_preset_name}.", "INFO")

        workflow_data = self.kernel.preset_manager.get_preset_data(selected_preset_name)

        if not workflow_data:
            status_updater(self.loc.get('ab_router_error_preset_not_found', selected_preset_name=selected_preset_name), "ERROR")
            self.logger(self.loc.get('ab_router_error_preset_not_found', selected_preset_name=selected_preset_name), "ERROR")
            return {"payload": payload, "output_name": "output_path"}

        nodes = {node['id']: node for node in workflow_data.get('nodes', [])}
        connections = {conn['id']: conn for conn in workflow_data.get('connections', [])}

        if not nodes:
            status_updater(self.loc.get('ab_router_error_empty_preset', selected_preset_name=selected_preset_name), "ERROR")
            self.logger(self.loc.get('ab_router_error_empty_preset', selected_preset_name=selected_preset_name), "ERROR")
            return {"payload": payload, "output_name": "output_path"}

        try:
            original_payload_for_loop = payload.copy()

            final_payload_from_sub = self.kernel.workflow_executor.execute_workflow_synchronous(
                nodes=nodes,
                connections=connections,
                initial_payload=payload,
                logger=self.logger,
                status_updater=lambda node_id, msg, lvl: status_updater(f"[{selected_preset_name}] {msg}", lvl),
                highlighter=lambda *args: None,
                ui_callback=ui_callback,
                workflow_context_id=f"sub_workflow_for_{config.get('__internal_node_id', self.module_id)}",
                mode=mode
            )
            status_updater(self.loc.get('ab_router_status_completed', selected_preset_name=selected_preset_name), "SUCCESS")
            self.logger(f"Multi-Variant Router: Eksekusi '{selected_preset_name}' selesai.", "INFO")

            original_payload_for_loop['output_name'] = "output_path"
            return original_payload_for_loop

        except Exception as e:
            status_updater(self.loc.get('ab_router_error_execution', selected_preset_name=selected_preset_name, error=e), "ERROR")
            self.logger(self.loc.get('ab_router_error_execution', selected_preset_name=selected_preset_name, error=e), "ERROR")
            return payload

    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        property_vars = {}
        current_config = get_current_config()
        saved_variants = current_config.get('routing_variants', [])
        self.parent_properties_frame = parent_frame

        main_container = ttk.LabelFrame(parent_frame, text=self.loc.get('ab_router_prop_title'))
        main_container.pack(fill=X, expand=False, padx=5, pady=10)

        left_frame = ttk.Frame(main_container)
        left_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=5, pady=5)
        ttk.Label(left_frame, text=self.loc.get('ab_router_available_presets_label')).pack(anchor='w')
        self.available_listbox = Listbox(left_frame, selectmode='extended', exportselection=False, background=self.kernel.theme_manager.get_colors().get('dark'), foreground=self.kernel.theme_manager.get_colors().get('fg'), selectbackground=self.kernel.theme_manager.get_colors().get('selectbg'), selectforeground=self.kernel.theme_manager.get_colors().get('selectfg'), borderwidth=0, highlightthickness=0)
        self.available_listbox.pack(fill=BOTH, expand=True)

        middle_frame = ttk.Frame(main_container)
        middle_frame.pack(side=LEFT, fill=Y, padx=5, pady=5)
        btn_add = ttk.Button(middle_frame, text=">", command=self._add_variant, width=3)
        btn_add.pack(pady=5); ToolTip(btn_add).update_text(self.loc.get('ab_router_tooltip_add_variant'))
        btn_add_all = ttk.Button(middle_frame, text=">>", command=self._add_all_presets, width=3)
        btn_add_all.pack(pady=5); ToolTip(btn_add_all).update_text(self.loc.get('tooltip_add_all_presets'))
        btn_remove = ttk.Button(middle_frame, text="<", command=self._remove_variant, width=3)
        btn_remove.pack(pady=5); ToolTip(btn_remove).update_text(self.loc.get('ab_router_tooltip_remove_variant'))
        btn_remove_all = ttk.Button(middle_frame, text="<<", command=self._remove_all_presets, width=3)
        btn_remove_all.pack(pady=5); ToolTip(btn_remove_all).update_text(self.loc.get('tooltip_remove_all_presets'))

        right_frame = ttk.Frame(main_container)
        right_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=5, pady=5)
        ttk.Label(right_frame, text=self.loc.get('ab_router_configured_variants_label')).pack(anchor='w')
        right_content_frame = ttk.Frame(right_frame)
        right_content_frame.pack(fill=BOTH, expand=True)
        self.selected_listbox = Listbox(right_content_frame, selectmode='extended', exportselection=False, background=self.kernel.theme_manager.get_colors().get('dark'), foreground=self.kernel.theme_manager.get_colors().get('fg'), selectbackground=self.kernel.theme_manager.get_colors().get('selectbg'),selectforeground=self.kernel.theme_manager.get_colors().get('selectfg'), borderwidth=0, highlightthickness=0)
        self.selected_listbox.pack(side=LEFT, fill=BOTH, expand=True)

        order_btn_frame = ttk.Frame(right_content_frame)
        order_btn_frame.pack(side=LEFT, fill=Y, padx=(5,0))
        btn_up = ttk.Button(order_btn_frame, text="↑", command=self._move_up, width=2)
        btn_up.pack(pady=5); ToolTip(btn_up).update_text(self.loc.get('tooltip_move_up'))
        btn_down = ttk.Button(order_btn_frame, text="↓", command=self._move_down, width=2)
        btn_down.pack(pady=5); ToolTip(btn_down).update_text(self.loc.get('tooltip_move_down'))

        all_presets = self.kernel.preset_manager.get_preset_list()
        saved_variant_names = {v['name'] for v in saved_variants}
        available_for_adding = sorted([p for p in all_presets if p not in saved_variant_names])
        for preset in available_for_adding:
            self.available_listbox.insert(END, preset)
        for variant_info in saved_variants:
            self.selected_listbox.insert(END, f"{variant_info['name']}")

        property_vars['routing_variants'] = ListboxData(self.selected_listbox)

        debug_vars = create_debug_and_reliability_ui(parent_frame, current_config, self.loc)
        property_vars.update(debug_vars)
        loop_vars = create_loop_settings_ui(parent_frame, current_config, self.loc, available_vars)
        property_vars.update(loop_vars)

        return property_vars

    def _add_variant(self):
        selected_indices = self.available_listbox.curselection()
        if not selected_indices: return
        for i in reversed(selected_indices):
            preset_name = self.available_listbox.get(i)
            self.selected_listbox.insert(END, preset_name)
            self.available_listbox.delete(i)

    def _remove_variant(self):
        selected_indices = self.selected_listbox.curselection()
        if not selected_indices: return
        for i in reversed(selected_indices):
            preset_name = self.selected_listbox.get(i)
            self.available_listbox.insert(END, preset_name)
            self.selected_listbox.delete(i)
        current_available_items = list(self.available_listbox.get(0, END))
        self.available_listbox.delete(0, END)
        for item in sorted(current_available_items):
            self.available_listbox.insert(END, item)

    def _add_all_presets(self):
        for item in self.available_listbox.get(0, END):
            self.selected_listbox.insert(END, item)
        self.available_listbox.delete(0, END)

    def _remove_all_presets(self):
        for item in self.selected_listbox.get(0, END):
            self.available_listbox.insert(END, item)
        self.selected_listbox.delete(0, END)
        current_items = list(self.available_listbox.get(0, END))
        self.available_listbox.delete(0, END)
        for item in sorted(current_items):
            self.available_listbox.insert(END, item)

    def _move_up(self):
        selected_indices = self.selected_listbox.curselection()
        for i in selected_indices:
            if i > 0:
                text = self.selected_listbox.get(i)
                self.selected_listbox.delete(i)
                self.selected_listbox.insert(i-1, text)
                self.selected_listbox.selection_set(i-1)

    def _move_down(self):
        selected_indices = self.selected_listbox.curselection()
        for i in reversed(selected_indices):
            if i < self.selected_listbox.size() - 1:
                text = self.selected_listbox.get(i)
                self.selected_listbox.delete(i)
                self.selected_listbox.insert(i+1, text)
                self.selected_listbox.selection_set(i+1)
####################################################################### DEV : AWENK AUDICO / SAHIDINAOLA@GMAIL.COM (AKHIR DARI KODE) ########################################################################################