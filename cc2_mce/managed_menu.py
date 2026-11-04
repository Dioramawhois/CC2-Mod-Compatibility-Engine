"""An owned Lua decorator identifying the managed set and locking game Mods."""

MENU_PATH = "scripts/screen_menu_main.lua"
POLICY = "sdk-screen-extension-v4"
SCREEN_DESCRIPTOR = "cc2x/screen_extensions.json"
SCREEN_SOURCE = "cc2x/ui/modloader_menu.lua"

# The SDK runs this after the actual screen's chunks, including when CC2 has
# disabled ordinary resource overlays. It contains no copied vanilla script.
ADAPTER = r"""
return function(env, selection_label)
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
    local badge_shown = false
    local ready_logged = false
    local function wrap_ui()
        local ui = env.g_ui
        if type(ui) ~= "table" or ui == wrapped_ui then return end
        wrapped_ui = ui
        if not ready_logged and type(env.cc2x) == "table"
            and type(env.cc2x.log) == "function" then
            ready_logged = true
            env.cc2x.log("MODLOADER_MENU_READY policy=sdk-screen-extension-v4")
        end
        local header = ui.header
        if type(header) == "function" then
            ui.header = function(self, ...)
                if is_screen(env.g_screen_index, "main") and not badge_shown then
                    badge_shown = true
                    header(self, "CC2 ModLoader")
                    if type(selection_label) == "string" and selection_label ~= "" then
                        self:text_basic(selection_label, env.color_grey_mid)
                    end
                    self:spacer(3)
                end
                return header(self, ...)
            end
        end
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
            badge_shown = false
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


def selection_label(selected_names: tuple[str, ...]) -> str:
    label = " + ".join(
        " ".join("".join(char if char.isprintable() else " " for char in name).split())
        for name in selected_names
    )
    return label if len(label) <= 140 else label[:137] + "..."


def decorate(source: bytes, selected_names: tuple[str, ...] = ()) -> bytes:
    # Decimal byte escapes are valid Lua 5.3, including UTF-8 and quote/backslash
    # characters. Mod names never become executable code or Lua escape syntax.
    label = selection_label(selected_names).encode("utf-8")
    literal = b'"' + b"".join(f"\\{byte:03d}".encode("ascii") for byte in label) + b'"'
    suffix = (
        b"\n\n-- CC2 ModLoader: managed mod selection\ndo\nlocal install = (function()\n"
        + ADAPTER
        + b"\nend)()\ninstall(_G, "
        + literal
        + b")\nend\n"
    )
    # Preserve every source byte and use its newline convention for owned code.
    return source + (suffix.replace(b"\n", b"\r\n") if b"\r\n" in source else suffix)


def screen_source(selected_names: tuple[str, ...]) -> bytes:
    """Owned screen extension; the SDK appends it after the actual stock menu."""
    return decorate(b"", selected_names)
