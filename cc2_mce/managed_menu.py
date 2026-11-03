"""An owned Lua decorator disabling the generated package's game Mods entry."""

MENU_PATH = "scripts/screen_menu_main.lua"
POLICY = "locked-mods-menu-v2"

# This wraps published menu callbacks after resource merging. It does not parse
# or rewrite another mod's Lua, and contains no copied vanilla script.
ADAPTER = r"""
return function(env)
    local function is_screen(index, name)
        return type(env.g_screens) == "table" and env.g_screens[name] ~= nil
            and index == env.g_screens[name]
    end
    local function locked()
        return is_screen(env.g_screen_index, "mods")
    end
    local function leave_mods()
        if locked() then
            env.g_screen_index = env.g_screens.main
            env.g_screen_nav_stack = {}
            env.g_selected_mod_id = 0
            env.g_selected_mod_confirm = false
            env.g_disable_mods_confirm = false
        end
    end
    local wrapped_ui = nil
    local notice_shown = false
    local function wrap_ui()
        local ui = env.g_ui
        if type(ui) ~= "table" or ui == wrapped_ui then return end
        wrapped_ui = ui
        local list_item = ui.list_item
        if type(list_item) == "function" then
            ui.list_item = function(self, label, select_on_hover, enabled, ...)
                if is_screen(env.g_screen_index, "main")
                    and label == env.update_get_loc(env.e_loc.upp_mods) then
                    list_item(self, label, select_on_hover, false, ...)
                    return false
                end
                return list_item(self, label, select_on_hover, enabled, ...)
            end
        end
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
    local nav_original = env.nav_set_screen
    if type(nav_original) == "function" then
        env.nav_set_screen = function(index, ...)
            if is_screen(index, "mods") then return false end
            return nav_original(index, ...)
        end
    end
    local begin_original = env.begin
    if type(begin_original) == "function" then
        env.begin = function(...)
            begin_original(...)
            wrap_ui()
            leave_mods()
        end
    end
    local update_original = env.update
    if type(update_original) == "function" then
        env.update = function(...)
            notice_shown = false
            wrap_ui()
            leave_mods()
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
