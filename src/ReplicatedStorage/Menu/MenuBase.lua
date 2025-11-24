-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:03 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPMultiDict)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_4 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_6 = require(game.ReplicatedStorage.Menu.MenuSystem)
require(game.ReplicatedStorage.Local.DebugOut)
local v7 = {}
local v_u_8 = Vector2.new(0, 1.25)
local v_u_9 = Vector2.new(0, 0)
local v_u_10 = Vector2.new(1, 1)
local v_u_11 = Vector2.new(0, 1)
local v_u_12 = Vector2.new(1, 1.25)
local v_u_13 = Vector2.new(1, 0)
v7.new = function(_, p_u_14, _) --[[ Name: new ]] --[[ Line: 20 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_6, (copy 3): v_u_4, (copy 4): v_u_1, (copy 5): v_u_8, (copy 6): v_u_10, (copy 7): v_u_9, (copy 8): v_u_11, (copy 9): v_u_12, (copy 10): v_u_13, (copy 11): v_u_2, (copy 12): v_u_5 ]]
    local v15 = v_u_3:SPUIObjectBase()
    v15._current_mode = v_u_6.MODE_TRANSITION_IN
    v15.is_current_mode_open = function(p16) --[[ Name: is_current_mode_open ]] --[[ Line: 24 ]]
        --[[ Upvalues: (ref 1): v_u_6 ]]
        return p16._current_mode == v_u_6.MODE_OPEN;
    end;
    v15._transition_t = 0
    v15._transition_incr = v_u_4:NormalizedDefaultExptValueInSeconds(1)
    v15.do_remove = function(_, _) end;
    v15.visual_update = function(p17, p18, p19) --[[ Name: visual_update ]] --[[ Line: 31 ]]
        p17:visual_update_base(p18, p19)
    end;
    v15.behaviour_update = function(p20, p21, p22) --[[ Name: behaviour_update ]] --[[ Line: 32 ]]
        p20:behaviour_update_base(p21, p22)
    end;
    v15.swallows_input = function(_) --[[ Name: swallows_input ]] --[[ Line: 33 ]]
        return true;
    end;
    v15.handles_bgm = function(_) --[[ Name: handles_bgm ]] --[[ Line: 34 ]]
        return false;
    end;
    v15.on_pushed_to_stack_top = function(_) end;
    v15.on_refocus = function(_) end;
    v15.get_restore_name = function(_) --[[ Name: get_restore_name ]] --[[ Line: 37 ]]
        return nil;
    end;
    v15.set_alpha = function(_, _) end;
    v15.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 40 ]]
        return 1;
    end;
    v15.set_scale = function(_, _) end;
    v15.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 42 ]]
        return 1;
    end;
    v15.layout = function(_) end;
    v15.visual_update_base = function(p23, p24, p25) --[[ Name: visual_update_base ]] --[[ Line: 46 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        v_u_1:profilebegin("MenuBase:visual_update_base")
        p23:transition_update(p24, p25)
        p23:layout()
        p23:update_cycle_elements(p24, p25)
        v_u_1:profileend()
    end;
    local v_u_26 = false
    local l_MODE_TRANSITION_IN_0 = v_u_6.MODE_TRANSITION_IN
    v15.behaviour_update_base = function(p27, p28, p29) --[[ Name: behaviour_update_base ]] --[[ Line: 56 ]]
        --[[ Upvalues: (ref 1): l_MODE_TRANSITION_IN_0, (ref 2): v_u_6, (ref 3): v_u_26, (ref 4): v_u_1 ]]
        if p27._current_mode ~= l_MODE_TRANSITION_IN_0 then
            if p27._current_mode == v_u_6.MODE_OPEN then
                if v_u_26 == false then
                    v_u_26 = true
                else
                    p27:on_refocus()
                end;
            end;
            l_MODE_TRANSITION_IN_0 = p27._current_mode
        end;
        if p27._current_mode == v_u_6.MODE_OPEN then
            v_u_1:profilebegin("MenuBase:behaviour_update_base")
            p27:update_default_cycle_element_behaviour(p28, p29)
            p27:behaviour_update_cycle_elements(p28, p29)
            v_u_1:profileend()
        end;
    end;
    v15.set_is_top_element = function(p30, p31) --[[ Name: set_is_top_element ]] --[[ Line: 75 ]]
        --[[ Upvalues: (ref 1): v_u_6 ]]
        if p31 then
            if p30._current_mode == v_u_6.MODE_TRANSITION_OUT then
                p30._current_mode = v_u_6.MODE_TRANSITION_IN
                p30._transition_t = 1 - p30._transition_t
                return;
            end;
            if p30._current_mode == v_u_6.MODE_HIDDEN then
                p30._current_mode = v_u_6.MODE_TRANSITION_IN
                p30._transition_t = 0
                return;
            end;
        else
            if p30._current_mode == v_u_6.MODE_TRANSITION_IN then
                p30._current_mode = v_u_6.MODE_TRANSITION_OUT
                p30._transition_t = 1 - p30._transition_t
                return;
            end;
            if p30._current_mode == v_u_6.MODE_OPEN then
                p30._current_mode = v_u_6.MODE_TRANSITION_OUT
                p30._transition_t = 0
            end;
        end;
    end;
    v15.transition_update = function(p32, p33, _) --[[ Name: transition_update ]] --[[ Line: 96 ]]
        --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_1 ]]
        if p32._current_mode == v_u_6.MODE_TRANSITION_IN then
            p32._transition_t = v_u_1:clamp(p32._transition_t + p32._transition_incr * p33, 0, 1)
            if p32._transition_t >= 1 then
                p32._current_mode = v_u_6.MODE_OPEN
            end;
        elseif p32._current_mode ~= v_u_6.MODE_OPEN and p32._current_mode == v_u_6.MODE_TRANSITION_OUT then
            p32._transition_t = v_u_1:clamp(p32._transition_t + p32._transition_incr * p33, 0, 1)
            if p32._transition_t >= 1 then
                p32._current_mode = v_u_6.MODE_HIDDEN
            end;
        end;
        p32:transition_update_visual(p32._transition_t)
    end;
    local v_u_34 = -1
    local v_u_35 = -1
    v15.transition_update_visual = function(p36, _) --[[ Name: transition_update_visual ]] --[[ Line: 117 ]]
        --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_4, (ref 3): v_u_8, (ref 4): v_u_10, (ref 5): v_u_9, (ref 6): v_u_11, (ref 7): v_u_12, (ref 8): v_u_13, (ref 9): v_u_34, (ref 10): v_u_35 ]]
        local v37 = 1
        local v38 = 1
        if p36._current_mode == v_u_6.MODE_TRANSITION_IN then
            v37 = v_u_4:YForPointOf2PtLine(v_u_8, v_u_10, p36._transition_t)
            v38 = v_u_4:YForPointOf2PtLine(v_u_9, v_u_10, p36._transition_t)
        elseif p36._current_mode == v_u_6.MODE_OPEN then
            v37 = 1
            v38 = 1
        elseif p36._current_mode == v_u_6.MODE_TRANSITION_OUT then
            v37 = v_u_4:YForPointOf2PtLine(v_u_11, v_u_12, p36._transition_t)
            v38 = v_u_4:YForPointOf2PtLine(v_u_11, v_u_13, p36._transition_t)
        elseif p36._current_mode == v_u_6.MODE_HIDDEN then
            v37 = 1.25
            v38 = 0
        end;
        if p36._current_mode == v_u_6.MODE_HIDDEN then
            p36:set_showing(false)
        else
            p36:set_showing(true)
        end;
        if v37 ~= v_u_34 then
            v_u_34 = v37
            p36:set_scale(v_u_34)
        end;
        if v38 ~= v_u_35 then
            v_u_35 = v38
            p36:set_alpha(v_u_35)
        end;
    end;
    v15.set_showing = function(_, _) end;
    v15._cycle_lists = v_u_2:new()
    v15._cycle_list_horizontal_i = 1
    v15._cycle_list_vertical_i = 1
    v15.get_cycle_list_selected_element = function(p39) --[[ Name: get_cycle_list_selected_element ]] --[[ Line: 158 ]]
        if p39._cycle_lists:count_of(p39._cycle_list_horizontal_i) < p39._cycle_list_vertical_i then
            return nil;
        else
            return p39._cycle_lists:list_of(p39._cycle_list_horizontal_i):get(p39._cycle_list_vertical_i);
        end;
    end;
    v15.reset_selected_item = function(p40) --[[ Name: reset_selected_item ]] --[[ Line: 165 ]]
        p40._cycle_list_horizontal_i = 1
        p40._cycle_list_vertical_i = 1
    end;
    v15.update_default_cycle_element_behaviour = function(p41, p42, p43) --[[ Name: update_default_cycle_element_behaviour ]] --[[ Line: 170 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        v_u_1:profilebegin("MenuBase:update_default_cycle_element_behaviour")
        p41:update_default_input_cursor_cycle_element_behaviour(p42, p43)
        v_u_1:profileend()
    end;
    v15.update_default_input_cursor_cycle_element_behaviour = function(p44, p45, p46) --[[ Name: update_default_input_cursor_cycle_element_behaviour ]] --[[ Line: 183 ]]
        p44:update_default_input_cursor_cycle_element_behaviour_base(p45, p46)
    end;
    local v_u_47 = nil
    local v_u_48 = nil
    v15.get_frame_selected_element = function(_) --[[ Name: get_frame_selected_element ]] --[[ Line: 189 ]]
        --[[ Upvalues: (ref 1): v_u_47 ]]
        return v_u_47;
    end;
    v15.get_triggered_element = function(_) --[[ Name: get_triggered_element ]] --[[ Line: 190 ]]
        --[[ Upvalues: (ref 1): v_u_48 ]]
        return v_u_48;
    end;
    v15.update_default_input_cursor_cycle_element_behaviour_base = function(p49, _, p50) --[[ Name: update_default_input_cursor_cycle_element_behaviour_base ]] --[[ Line: 192 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_14, (ref 3): v_u_47, (ref 4): v_u_5, (ref 5): v_u_48 ]]
        v_u_1:profilebegin("MenuBase:update_default_input_cursor_cycle_element_behaviour_base")
        local v51 = p_u_14:get_cursor_nxy()
        v_u_47 = nil
        if p50._input:get_has_frame_focused_element() == false then
            for v52 = 1, p49._cycle_lists:count() do
                local v53 = p49._cycle_lists:list_of(v52)
                for v54 = 1, v53:count() do
                    local v55 = v53:get(v54)
                    if v55:is_selectable() and v55:get_nrect(p_u_14):contains_vec2(v51) then
                        p49._cycle_list_horizontal_i = v52
                        p49._cycle_list_vertical_i = v54
                        v_u_47 = v55
                    end;
                end;
            end;
        end;
        for v56 = 1, p49._cycle_lists:count() do
            local v57 = p49._cycle_lists:list_of(v56)
            for v58 = 1, v57:count() do
                local v59 = v57:get(v58)
                if v59 == v_u_47 then
                    v59:set_selected(p50, true)
                else
                    v59:set_selected(p50, false)
                end;
            end;
        end;
        if p50._input:control_just_pressed(v_u_5.KEY_CLICK) and v_u_47 ~= nil then
            v_u_47:trigger_element(p50)
            v_u_48 = v_u_47
        end;
        if v_u_47 == nil then
            v_u_48 = nil
        else
            p50._input:set_has_frame_focused_element(true)
            if v_u_48 ~= nil and v_u_47 ~= v_u_48 then
                v_u_48 = nil
            end;
        end;
        v_u_1:profileend()
    end;
    v15.update_default_input_pad_cycle_element_behaviour = function(_, _, _) end;
    v15.update_cycle_elements = function(p60, p61, p62) --[[ Name: update_cycle_elements ]] --[[ Line: 270 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        v_u_1:profilebegin("MenuBase:update_cycle_elements (visual_update aka update)")
        for v63 = 1, p60._cycle_lists:count() do
            local v64 = p60._cycle_lists:list_of(v63)
            for v65 = 1, v64:count() do
                v64:get(v65):update(p61, p62)
            end;
        end;
        v_u_1:profileend()
    end;
    v15.behaviour_update_cycle_elements = function(p66, p67, p68) --[[ Name: behaviour_update_cycle_elements ]] --[[ Line: 283 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        v_u_1:profilebegin("MenuBase:behaviour_update_cycle_elements")
        for v69 = 1, p66._cycle_lists:count() do
            local v70 = p66._cycle_lists:list_of(v69)
            for v71 = 1, v70:count() do
                v70:get(v71):behaviour_update(p67, p68)
            end;
        end;
        v_u_1:profileend()
    end;
    v15.add_cycle_element = function(p72, _, p73, p74) --[[ Name: add_cycle_element ]] --[[ Line: 295 ]]
        p72._cycle_lists:push_back_to(p73, p74)
        return p74;
    end;
    v15.remove_cycle_element = function(p75, p76) --[[ Name: remove_cycle_element ]] --[[ Line: 303 ]]
        for v77 = 1, p75._cycle_lists:count() do
            p75._cycle_lists:list_of(v77):remove(p76)
        end;
    end;
    v15.cycle_list_updated = function(p78, p79) --[[ Name: cycle_list_updated ]] --[[ Line: 310 ]]
        for v80 = 1, p78._cycle_lists:count() do
            local v81 = p78._cycle_lists:list_of(v80)
            for v82 = 1, v81:count() do
                local v83 = v81:get(v82)
                if v83:is_selectable() and (v80 == p78._cycle_list_horizontal_i and v82 == p78._cycle_list_vertical_i) then
                    v83:set_selected(p79, true)
                else
                    v83:set_selected(p79, false)
                end;
            end;
        end;
    end;
    return v15;
end;
return v7;
