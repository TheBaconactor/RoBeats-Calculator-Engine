-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:03 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_4 = require(game.ReplicatedStorage.LocalShared.FrameIndex)
local v_u_5 = {
    ["INPUT_MODE_CURSOR"] = 1,
    ["INPUT_MODE_PAD"] = 2,
    ["MODE_TRANSITION_IN"] = 0,
    ["MODE_OPEN"] = 1,
    ["MODE_TRANSITION_OUT"] = 2,
    ["MODE_HIDDEN"] = 3
}
v_u_5.new = function(_) --[[ Name: new ]] --[[ Line: 21 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_5, (copy 3): v_u_3, (copy 4): v_u_4, (copy 5): v_u_1 ]]
    local v8 = {
        ["top_menu_swallows_input"] = function(p6) --[[ Name: top_menu_swallows_input ]] --[[ Line: 231 ]]
            local v7 = p6:get_top_element()
            if v7 == nil then
                return false;
            else
                return v7:swallows_input();
            end;
        end
    }
    local v_u_9 = v_u_2:new()
    local v_u_10 = v_u_2:new()
    local l_INPUT_MODE_CURSOR_0 = v_u_5.INPUT_MODE_CURSOR
    v8.get_input_mode = function(_) --[[ Name: get_input_mode ]] --[[ Line: 27 ]]
        --[[ Upvalues: (copy 1): l_INPUT_MODE_CURSOR_0 ]]
        return l_INPUT_MODE_CURSOR_0;
    end;
    v8.get_menu_stack = function(_) --[[ Name: get_menu_stack ]] --[[ Line: 29 ]]
        --[[ Upvalues: (copy 1): v_u_9 ]]
        return v_u_9;
    end;
    v8.menu_count = function(_) --[[ Name: menu_count ]] --[[ Line: 30 ]]
        --[[ Upvalues: (copy 1): v_u_9 ]]
        return v_u_9:count();
    end;
    local v_u_11 = v_u_2:new()
    v8.get_menus_to_push = function(_) --[[ Name: get_menus_to_push ]] --[[ Line: 33 ]]
        --[[ Upvalues: (copy 1): v_u_11 ]]
        return v_u_11;
    end;
    v8.push_menu = function(_, p12) --[[ Name: push_menu ]] --[[ Line: 34 ]]
        --[[ Upvalues: (ref 1): v_u_3, (copy 2): v_u_11 ]]
        if p12 == nil then
            v_u_3:errf("MenuSystem:push_menu nil")
        end;
        v_u_11:push_back(p12)
        return p12;
    end;
    v8.contains_menu = function(_, p13) --[[ Name: contains_menu ]] --[[ Line: 41 ]]
        --[[ Upvalues: (copy 1): v_u_9 ]]
        for v14 = 1, v_u_9:count() do
            if v_u_9:get(v14) == p13 then
                return true;
            end;
        end;
        return false;
    end;
    local function f_remove_menu_from_list(p15, p16) --[[ Name: remove_menu_from_list ]] --[[ Line: 50 ]]
        --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_10 ]]
        local v17 = nil
        for v18 = v_u_9:count(), 1, -1 do
            local v19 = p16:get(v18)
            if v19 == p15 then
                p16:remove_at(v18)
                v17 = v19
            end;
        end;
        if v17 ~= nil then
            v17:set_is_top_element(false)
            v_u_10:push_back(v17)
        end;
    end;
    v8.remove_menu = function(_, p20) --[[ Name: remove_menu ]] --[[ Line: 68 ]]
        --[[ Upvalues: (copy 1): f_remove_menu_from_list, (copy 2): v_u_11, (copy 3): v_u_9 ]]
        f_remove_menu_from_list(p20, v_u_11)
        f_remove_menu_from_list(p20, v_u_9)
    end;
    v8.remove_all_menus_except = function(_, p21, p22) --[[ Name: remove_all_menus_except ]] --[[ Line: 73 ]]
        --[[ Upvalues: (copy 1): v_u_11, (copy 2): f_remove_menu_from_list, (copy 3): v_u_9 ]]
        for v23 = v_u_11:count(), 1, -1 do
            local v24 = v_u_11:get(v23)
            local v25 = true
            if v24 == p21 then
                v25 = false
            elseif p22 ~= nil then
                v25 = not p22(v24)
            end;
            if v25 then
                f_remove_menu_from_list(v24, v_u_11)
            end;
        end;
        for v26 = v_u_9:count(), 1, -1 do
            local v27 = v_u_9:get(v26)
            local v28 = true
            if v27 == p21 then
                v28 = false
            elseif p22 ~= nil then
                v28 = not p22(v27)
            end;
            if v28 then
                f_remove_menu_from_list(v27, v_u_9)
            end;
        end;
    end;
    v8.remove_menu_if = function(_, p29) --[[ Name: remove_menu_if ]] --[[ Line: 100 ]]
        --[[ Upvalues: (copy 1): v_u_11, (copy 2): f_remove_menu_from_list, (copy 3): v_u_9 ]]
        for v30 = v_u_11:count(), 1, -1 do
            local v31 = v_u_11:get(v30)
            if p29(v31) == true then
                f_remove_menu_from_list(v31, v_u_11)
            end;
        end;
        for v32 = v_u_9:count(), 1, -1 do
            local v33 = v_u_9:get(v32)
            if p29(v33) == true then
                f_remove_menu_from_list(v33, v_u_9)
            end;
        end;
    end;
    v8.remove_all_menus = function(_) --[[ Name: remove_all_menus ]] --[[ Line: 123 ]]
        --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_10 ]]
        for v34 = v_u_9:count(), 1, -1 do
            local v35 = v_u_9:get(v34)
            v_u_9:remove_at(v34)
            v35:set_is_top_element(false)
            v_u_10:push_back(v35)
        end;
    end;
    local l_MenuVisualUpdate_0 = v_u_4.Test.MenuVisualUpdate
    v_u_4:register_ui_needs_refresh_should_run_test_type(l_MenuVisualUpdate_0)
    local l_MenuBehaviourUpdate_0 = v_u_4.Test.MenuBehaviourUpdate
    v_u_4:register_ui_needs_refresh_should_run_test_type(l_MenuBehaviourUpdate_0)
    v8.update = function(_, p36, p37) --[[ Name: update ]] --[[ Line: 139 ]]
        --[[ Upvalues: (copy 1): v_u_10, (ref 2): v_u_5, (copy 3): v_u_11, (copy 4): v_u_9, (ref 5): v_u_4, (copy 6): l_MenuVisualUpdate_0, (ref 7): v_u_1, (copy 8): l_MenuBehaviourUpdate_0 ]]
        for v38 = v_u_10:count(), 1, -1 do
            p37._input:set_has_frame_focused_element(true)
            local v39 = v_u_10:get(v38)
            v39:visual_update(p36, p37)
            if v39._current_mode == v_u_5.MODE_HIDDEN then
                v39:do_remove(p37)
                v_u_10:remove_at(v38)
            end;
        end;
        for v40 = 1, v_u_11:count() do
            p37._input:set_has_frame_focused_element(true)
            local v41 = v_u_11:get(v40)
            v_u_9:push_back(v41)
            v41:on_pushed_to_stack_top()
        end;
        v_u_11:clear()
        local v42 = v_u_4:singleton()
        if v42:should_run(l_MenuVisualUpdate_0) then
            local v43 = v42:get_test_state(l_MenuVisualUpdate_0)
            local v44 = v43:get_dt_scale()
            p37._input:set_frame_index_state(v43)
            v_u_1:profilebegin("_menus:update visual_update")
            for v45 = v_u_9:count(), 1, -1 do
                local v46 = v_u_9:get(v45)
                if v45 == v_u_9:count() then
                    v46:set_is_top_element(true)
                else
                    v46:set_is_top_element(false)
                end;
                if v46._current_mode ~= v_u_5.MODE_HIDDEN then
                    v46:visual_update(v44, p37)
                end;
            end;
            v_u_1:profileend()
            p37._input:set_frame_index_state(nil)
        end;
        if v42:should_run(l_MenuBehaviourUpdate_0) then
            local v47 = v42:get_test_state(l_MenuBehaviourUpdate_0)
            local v48 = v47:get_dt_scale()
            p37._input:set_frame_index_state(v47)
            v_u_1:profilebegin("_menus:update behaviour_update")
            if v_u_9:count() > 0 then
                v_u_9:back():behaviour_update(v48, p37)
            end;
            v_u_1:profileend()
            p37._input:set_frame_index_state(nil)
        end;
    end;
    v8.get_top_element = function(_) --[[ Name: get_top_element ]] --[[ Line: 223 ]]
        --[[ Upvalues: (copy 1): v_u_9 ]]
        return v_u_9:back();
    end;
    v8.menus_transitioning = function(_) --[[ Name: menus_transitioning ]] --[[ Line: 227 ]]
        --[[ Upvalues: (copy 1): v_u_11, (copy 2): v_u_10 ]]
        return v_u_11:count() > 0 and true or v_u_10:count() > 0;
    end;
    return v8;
end;
return v_u_5;
