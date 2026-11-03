-- Owned synthetic UI; no game/mod Lua is executed by this fixture.
local window = {is_active=true}
local rows, buttons, notices, writes, updates = {}, {}, 0, 0, 0
local ui = {
    get_window=function() return window end,
    text_basic=function(_, text) assert(text=='CC2 ModLoader');notices=notices+1 end,
    spacer=function() end,
    mod_details=function(_, name, author, enabled)
        rows[#rows+1]={name=name,enabled=enabled,active=window.is_active}
        return true -- Deliberately ignore active: wrapper must still suppress clicks.
    end,
    button=function(_, label, enabled) buttons[#buttons+1]=enabled;return true end,
}
local env={g_screens={main=0,mods=15},g_screen_index=15,
    e_loc={upp_disable_all=20},update_get_loc=function() return 'Disable all' end,
    update_set_is_mod_enabled=function() writes=writes+1 end,
    begin=function() end,
}
env.begin=function() env.g_ui=ui end
env.update=function()
    updates=updates+1
    assert(env.g_selected_mod_id==0 and not env.g_selected_mod_confirm and not env.g_disable_mods_confirm)
    assert(not ui:mod_details('CC2 ModLoader: selected', 'Team', true))
    assert(not ui:mod_details('Other mod', 'Author', false))
    assert(not ui:button('Disable all',true,1))
    env.update_set_is_mod_enabled(2,true) -- stale confirmation / keyboard path
end
POLICY(env)
env.begin()
for i=1,2 do
    env.g_selected_mod_id=99;env.g_selected_mod_confirm=true;env.g_disable_mods_confirm=true
    env.update()
    assert(window.is_active and notices==i)
end
assert(updates==2 and #rows==4 and #buttons==2 and writes==0)
assert(rows[1].enabled and not rows[2].enabled)
for _,row in ipairs(rows) do assert(not row.active) end
for _,enabled in ipairs(buttons) do assert(not enabled) end
env.g_screen_index=0
assert(ui:mod_details('Other screen','Author',true))
assert(rows[#rows].active and window.is_active)
print('PASS managed menu: gray/read-only rows, real selected state, keyboard/dialog suppression, disable-all, other screens, repeated frames')
