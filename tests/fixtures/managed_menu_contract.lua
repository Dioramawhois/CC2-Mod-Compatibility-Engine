-- Owned synthetic UI; no game/mod Lua is executed by this fixture.
local window = {is_active=true}
local items, rows, buttons, notices, writes, updates = {}, {}, {}, 0, 0, 0
local labels = {[20]='Disable all', [21]='Mods', [22]='New game'}
local function make_ui()
    return {
        get_window=function() return window end,
        text_basic=function(_, text) assert(text=='CC2 ModLoader');notices=notices+1 end,
        spacer=function() end,
        list_item=function(_, label, hover, enabled, extra)
            items[#items+1]={label=label,hover=hover,enabled=enabled,extra=extra}
            return true, 'item-result' -- Ignore enabled: the wrapper must suppress clicks too.
        end,
        mod_details=function(_, name, author, enabled)
            rows[#rows+1]={name=name,enabled=enabled,active=window.is_active}
            return true -- Ignore active: the fallback must still suppress clicks.
        end,
        button=function(_, label, enabled) buttons[#buttons+1]=enabled;return true end,
    }
end
local env={g_screens={main=0,join=3,mods=15},g_screen_index=15,
    g_screen_nav_stack={0,3},g_selected_mod_id=99,g_selected_mod_confirm=true,
    g_disable_mods_confirm=true,e_loc={upp_disable_all=20,upp_mods=21,upp_new_game=22},
    update_get_loc=function(id) return assert(labels[id]) end,
    update_set_is_mod_enabled=function() writes=writes+1 end,
}
local navigation_calls = 0
local function mark_stale()
    env.g_screen_index=env.g_screens.mods
    env.g_screen_nav_stack={0,15}
    env.g_selected_mod_id=99;env.g_selected_mod_confirm=true;env.g_disable_mods_confirm=true
end
env.nav_set_screen=function(index, extra)
    navigation_calls=navigation_calls+1
    env.g_screen_nav_stack[#env.g_screen_nav_stack+1]=env.g_screen_index
    env.g_screen_index=index
    return 'navigation-result', extra
end
env.begin=function() env.g_ui=make_ui() end
env.update=function(marker)
    updates=updates+1
    assert(env.g_screen_index==env.g_screens.main)
    assert(env.g_selected_mod_id==0 and not env.g_selected_mod_confirm and not env.g_disable_mods_confirm)
    local ui=env.g_ui
    assert(not ui:list_item(labels[21],true,true,'mods-extra'))
    local result,extra=ui:list_item(labels[22],false,true,'new-extra')
    assert(result and extra=='item-result')
    assert(not items[#items-1].enabled and items[#items-1].hover)
    assert(items[#items-1].extra=='mods-extra')
    assert(items[#items].enabled and items[#items].hover==false)
    assert(items[#items].extra=='new-extra')
    env.update_set_is_mod_enabled(2,true) -- stale confirmation / keyboard path
    return marker
end
POLICY(env)

env.begin()
assert(env.g_screen_index==env.g_screens.main and #env.g_screen_nav_stack==0)
for i=1,2 do
    assert(env.update('frame-result')=='frame-result')
end
assert(updates==2 and #items==4 and writes==0)

-- Keyboard/controller callers cannot enter Mods or leave a stale back-stack entry.
local stack=env.g_screen_nav_stack
env.nav_set_screen(env.g_screens.mods,'blocked')
assert(navigation_calls==0 and env.g_screen_index==0 and env.g_screen_nav_stack==stack and #stack==0)
local result,extra=env.nav_set_screen(env.g_screens.join,'preserved')
assert(result=='navigation-result' and extra=='preserved' and navigation_calls==1)
assert(env.g_screen_index==3 and #stack==1 and stack[1]==0)
-- The label has no special meaning outside the main menu.
assert(env.g_ui:list_item(labels[21],false,true))
assert(items[#items].enabled and items[#items].hover==false)

-- Retain row/dialog defenses if another callback puts the VM into Mods directly.
mark_stale()
assert(not env.g_ui:mod_details('CC2 ModLoader: selected','Team',true))
assert(not env.g_ui:mod_details('Other mod','Author',false))
assert(not env.g_ui:button(labels[20],true,1))
assert(rows[1].enabled and not rows[2].enabled and notices==1)
for _,row in ipairs(rows) do assert(not row.active) end
assert(not buttons[#buttons] and window.is_active)
assert(env.update('recovered')=='recovered')
assert(#env.g_screen_nav_stack==0 and writes==0)
assert(env.g_ui:mod_details('Other screen','Author',true))
assert(rows[#rows].active and window.is_active)
assert(env.g_ui:button(labels[20],true,1) and buttons[#buttons])

-- Resolve localization each time; recreated UI instances retain the guard.
local previous_ui=env.g_ui
labels[21]='Modifications'
env.begin()
assert(env.g_ui~=previous_ui)
local before=#items
assert(env.update('localized')=='localized')
assert(#items==before+2 and items[before+1].label=='Modifications')
local wrapped_item=env.g_ui.list_item
env.update('repeated')
assert(env.g_ui.list_item==wrapped_item)
print('PASS managed menu: disabled localized Mods entry, preserved hover/other items, blocked navigation, stale recovery, read-only fallback, recreated UI')
