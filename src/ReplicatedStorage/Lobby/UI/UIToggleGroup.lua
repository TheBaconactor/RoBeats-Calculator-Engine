-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:53 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_3 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_4 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPList)
return {
    ["new"] = function(_, p_u_6, p_u_7, p_u_8, p_u_9, p_u_10, p_u_11, p_u_12, p_u_13, p14) --[[ Name: new ]] --[[ Line: 9 ]]
        --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_3, (copy 3): v_u_2, (copy 4): v_u_4, (copy 5): v_u_1 ]]
        local v_u_15 = p14 == nil and {} or p14
        local v_u_16 = {}
        v_u_16.get_obj_list = function(_) --[[ Name: get_obj_list ]] --[[ Line: 24 ]]
            --[[ Upvalues: (copy 1): p_u_6 ]]
            return p_u_6;
        end;
        v_u_16.get_value_list = function(_) --[[ Name: get_value_list ]] --[[ Line: 25 ]]
            --[[ Upvalues: (ref 1): p_u_7 ]]
            return p_u_7;
        end;
        v_u_16.set_value_list = function(_, p17) --[[ Name: set_value_list ]] --[[ Line: 26 ]]
            --[[ Upvalues: (ref 1): p_u_7 ]]
            p_u_7 = p17
        end;
        v_u_16.get_selected_callback = function(_) --[[ Name: get_selected_callback ]] --[[ Line: 27 ]]
            --[[ Upvalues: (copy 1): p_u_8 ]]
            return p_u_8;
        end;
        v_u_16.get_value_callback = function(_) --[[ Name: get_value_callback ]] --[[ Line: 28 ]]
            --[[ Upvalues: (copy 1): p_u_9 ]]
            return p_u_9;
        end;
        local v_u_18 = 0.5
        v_u_16.set_alpha_hidden = function(p19, p20) --[[ Name: set_alpha_hidden ]] --[[ Line: 31 ]]
            --[[ Upvalues: (ref 1): v_u_18 ]]
            v_u_18 = p20
            return p19;
        end;
        local v_u_21 = v_u_5:new()
        local v_u_22 = v_u_5:new()
        v_u_16.get_button_for_value = function(_, p23) --[[ Name: get_button_for_value ]] --[[ Line: 36 ]]
            --[[ Upvalues: (ref 1): p_u_7, (copy 2): v_u_22 ]]
            return v_u_22:get((p_u_7:find(p23)));
        end;
        local function _() --[[ Name: cons ]] --[[ Line: 41 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): p_u_6, (ref 3): p_u_7, (copy 4): p_u_10, (copy 5): p_u_12, (ref 6): v_u_3, (ref 7): v_u_2, (copy 8): p_u_11, (copy 9): p_u_13, (ref 10): v_u_15, (ref 11): v_u_4, (copy 12): p_u_8, (copy 13): v_u_16, (copy 14): v_u_22, (ref 15): v_u_1, (copy 16): v_u_21, (copy 17): p_u_9, (ref 18): v_u_18 ]]
            v_u_5:for_each(p_u_6, function(p_u_24, p_u_25) --[[ Line: 42 ]]
                --[[ Upvalues: (ref 1): p_u_7, (ref 2): p_u_10, (ref 3): p_u_12, (ref 4): v_u_3, (ref 5): v_u_2, (ref 6): p_u_11, (ref 7): p_u_13, (ref 8): v_u_15, (ref 9): v_u_4, (ref 10): p_u_8, (ref 11): v_u_16, (ref 12): v_u_22, (ref 13): v_u_1, (ref 14): v_u_21, (ref 15): p_u_9, (ref 16): v_u_18 ]]
                local function f_fn_get_value() --[[ Name: fn_get_value ]] --[[ Line: 43 ]]
                    --[[ Upvalues: (ref 1): p_u_7, (copy 2): p_u_25 ]]
                    return p_u_7:get(p_u_25);
                end;
                local v_u_26 = p_u_10:add_cycle_element(p_u_12, 1, v_u_3:new(v_u_2:new(p_u_10, p_u_11, p_u_24), p_u_13, function() --[[ Line: 49 ]]
                    --[[ Upvalues: (ref 1): v_u_15, (ref 2): p_u_12, (ref 3): v_u_4, (ref 4): p_u_8, (copy 5): f_fn_get_value, (ref 6): v_u_16 ]]
                    if v_u_15.NoSFX == nil then
                        p_u_12._sfx_manager:play_sfx(v_u_4.SFX_MENU_OPEN)
                    end;
                    p_u_8(f_fn_get_value())
                    v_u_16:update_displays()
                end))
                v_u_22:push_back(v_u_26)
                local v_u_27 = v_u_1:get_list_of_children_of_classname(p_u_24, "ImageLabel")
                local v_u_28 = v_u_1:get_list_of_children_of_classname(p_u_24, "TextLabel")
                v_u_21:push_back(function() --[[ Line: 61 ]]
                    --[[ Upvalues: (ref 1): p_u_7, (copy 2): p_u_25, (copy 3): v_u_26, (ref 4): v_u_15, (copy 5): f_fn_get_value, (ref 6): p_u_9, (ref 7): v_u_1, (copy 8): v_u_27, (copy 9): v_u_28, (ref 10): v_u_18, (copy 11): p_u_24 ]]
                    if p_u_7:get(p_u_25) == nil then
                        v_u_26:set_visible(false)
                        return;
                    else
                        v_u_26:set_visible(true)
                        if v_u_15.FnOnButtonUpdateDisplay ~= nil then
                            v_u_15.FnOnButtonUpdateDisplay(v_u_26, f_fn_get_value())
                        end;
                        if v_u_15.UseRSetAlphaV2 == true then
                            if p_u_9() == p_u_7:get(p_u_25) then
                                v_u_1:list_apply_suffix_alpha_attribute(v_u_27, "UIToggleGroup", 1)
                                v_u_1:list_apply_suffix_alpha_attribute(v_u_28, "UIToggleGroup", 1)
                            else
                                v_u_1:list_apply_suffix_alpha_attribute(v_u_27, "UIToggleGroup", v_u_18 * 0.5)
                                v_u_1:list_apply_suffix_alpha_attribute(v_u_28, "UIToggleGroup", v_u_18)
                            end;
                            v_u_1:r_set_alpha_v2(p_u_24, 1)
                            return;
                        elseif p_u_9() == p_u_7:get(p_u_25) then
                            v_u_1:list_set_alpha_name(v_u_27, {
                                ["ImageAlpha"] = 1
                            })
                            v_u_1:list_set_alpha_name(v_u_28, {
                                ["TextAlpha"] = 1
                            })
                            v_u_1:r_set_alpha(p_u_24, 1)
                        else
                            v_u_1:list_set_alpha_name(v_u_27, {
                                ["ImageAlpha"] = v_u_18 * 0.5
                            })
                            v_u_1:list_set_alpha_name(v_u_28, {
                                ["TextAlpha"] = v_u_18
                            })
                            v_u_1:r_set_alpha(p_u_24, 1)
                        end;
                    end;
                end)
            end)
            v_u_16:update_displays()
        end;
        v_u_16.update_displays = function(p29) --[[ Name: update_displays ]] --[[ Line: 99 ]]
            --[[ Upvalues: (ref 1): v_u_15, (copy 2): v_u_21 ]]
            if v_u_15.FnOnPreUpdateDisplays ~= nil then
                v_u_15.FnOnPreUpdateDisplays(p29)
            end;
            for v30 = 1, v_u_21:count() do
                v_u_21:get(v30)()
            end;
        end;
        v_u_5:for_each(p_u_6, function(p_u_31, p_u_32) --[[ Line: 42 ]]
            --[[ Upvalues: (ref 1): p_u_7, (copy 2): p_u_10, (copy 3): p_u_12, (ref 4): v_u_3, (ref 5): v_u_2, (copy 6): p_u_11, (copy 7): p_u_13, (ref 8): v_u_15, (ref 9): v_u_4, (copy 10): p_u_8, (copy 11): v_u_16, (copy 12): v_u_22, (ref 13): v_u_1, (copy 14): v_u_21, (copy 15): p_u_9, (ref 16): v_u_18 ]]
            local function f_fn_get_value() --[[ Name: fn_get_value ]] --[[ Line: 43 ]]
                --[[ Upvalues: (ref 1): p_u_7, (copy 2): p_u_32 ]]
                return p_u_7:get(p_u_32);
            end;
            local v_u_33 = p_u_10:add_cycle_element(p_u_12, 1, v_u_3:new(v_u_2:new(p_u_10, p_u_11, p_u_31), p_u_13, function() --[[ Line: 49 ]]
                --[[ Upvalues: (ref 1): v_u_15, (ref 2): p_u_12, (ref 3): v_u_4, (ref 4): p_u_8, (copy 5): f_fn_get_value, (ref 6): v_u_16 ]]
                if v_u_15.NoSFX == nil then
                    p_u_12._sfx_manager:play_sfx(v_u_4.SFX_MENU_OPEN)
                end;
                p_u_8(f_fn_get_value())
                v_u_16:update_displays()
            end))
            v_u_22:push_back(v_u_33)
            local v_u_34 = v_u_1:get_list_of_children_of_classname(p_u_31, "ImageLabel")
            local v_u_35 = v_u_1:get_list_of_children_of_classname(p_u_31, "TextLabel")
            v_u_21:push_back(function() --[[ Line: 61 ]]
                --[[ Upvalues: (ref 1): p_u_7, (copy 2): p_u_32, (copy 3): v_u_33, (ref 4): v_u_15, (copy 5): f_fn_get_value, (ref 6): p_u_9, (ref 7): v_u_1, (copy 8): v_u_34, (copy 9): v_u_35, (ref 10): v_u_18, (copy 11): p_u_31 ]]
                if p_u_7:get(p_u_32) == nil then
                    v_u_33:set_visible(false)
                    return;
                else
                    v_u_33:set_visible(true)
                    if v_u_15.FnOnButtonUpdateDisplay ~= nil then
                        v_u_15.FnOnButtonUpdateDisplay(v_u_33, f_fn_get_value())
                    end;
                    if v_u_15.UseRSetAlphaV2 == true then
                        if p_u_9() == p_u_7:get(p_u_32) then
                            v_u_1:list_apply_suffix_alpha_attribute(v_u_34, "UIToggleGroup", 1)
                            v_u_1:list_apply_suffix_alpha_attribute(v_u_35, "UIToggleGroup", 1)
                        else
                            v_u_1:list_apply_suffix_alpha_attribute(v_u_34, "UIToggleGroup", v_u_18 * 0.5)
                            v_u_1:list_apply_suffix_alpha_attribute(v_u_35, "UIToggleGroup", v_u_18)
                        end;
                        v_u_1:r_set_alpha_v2(p_u_31, 1)
                        return;
                    elseif p_u_9() == p_u_7:get(p_u_32) then
                        v_u_1:list_set_alpha_name(v_u_34, {
                            ["ImageAlpha"] = 1
                        })
                        v_u_1:list_set_alpha_name(v_u_35, {
                            ["TextAlpha"] = 1
                        })
                        v_u_1:r_set_alpha(p_u_31, 1)
                    else
                        v_u_1:list_set_alpha_name(v_u_34, {
                            ["ImageAlpha"] = v_u_18 * 0.5
                        })
                        v_u_1:list_set_alpha_name(v_u_35, {
                            ["TextAlpha"] = v_u_18
                        })
                        v_u_1:r_set_alpha(p_u_31, 1)
                    end;
                end;
            end)
        end)
        v_u_16:update_displays()
        return v_u_16;
    end
};
