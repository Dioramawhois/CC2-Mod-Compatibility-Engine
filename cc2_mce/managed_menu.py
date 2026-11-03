"""An owned Lua decorator for the generated package's read-only game mod list."""

MENU_PATH = "scripts/screen_menu_main.lua"
POLICY = "read-only-mod-list-v1"

# This wraps published menu callbacks after resource merging. It does not parse
# or rewrite another mod's Lua, and contains no copied vanilla script.
ADAPTER = r"""
return function(env)
    local function locked()
        return type(env.g_screens) == "table" and env.g_screen_index == env.g_screens.mods
    end
    local wrapped_ui = nil
    local notice_shown = false
    local function wrap_ui()
        local ui = env.g_ui
        if type(ui) ~= "table" or ui == wrapped_ui then return end
        wrapped_ui = ui
        local details = ui.mod_details
        if type(details) == "function" then
            ui.mod_details = function(self, ...)
                if not locked() then return details(self, ...) end
                if not notice_shown then
                    notice_shown = true
                    self:text_basic("CC2 ModLoader", env.color_grey_mid)
                    self:spacer(2)
                end
                local window = self:get_window()
                local active = window.is_active
                window.is_active = false
                local ok, result = pcall(details, self, ...)
                window.is_active = active
                if not ok then error(result, 0) end
                return false
            end
        end
        local button = ui.button
        if type(button) == "function" then
            ui.button = function(self, label, enabled, ...)
                if locked() and label == env.update_get_loc(env.e_loc.upp_disable_all) then
                    button(self, label, false, ...)
                    return false
                end
                return button(self, label, enabled, ...)
            end
        end
    end
    local begin_original = env.begin
    if type(begin_original) == "function" then
        env.begin = function(...)
            begin_original(...)
            wrap_ui()
        end
    end
    local update_original = env.update
    if type(update_original) == "function" then
        env.update = function(...)
            notice_shown = false
            wrap_ui()
            if locked() then
                env.g_selected_mod_id = 0
                env.g_selected_mod_confirm = false
                env.g_disable_mods_confirm = false
            end
            return update_original(...)
        end
    end
    -- Defense against stale dialogs and keyboard actions in this menu VM.
    -- Other screen VMs and engine activation/network code are unaffected.
    env.update_set_is_mod_enabled = function() return false end
end
""".strip().encode("utf-8")


def decorate(source: bytes) -> bytes:
    suffix = (
        b"\n\n-- CC2 ModLoader: managed mod selection\ndo\nlocal install = (function()\n"
        + ADAPTER
        + b"\nend)()\ninstall(_G)\nend\n"
    )
    # Preserve every source byte and use its newline convention for owned code.
    return source + (suffix.replace(b"\n", b"\r\n") if b"\r\n" in source else suffix)
