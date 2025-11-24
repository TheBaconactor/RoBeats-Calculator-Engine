-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:03 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_4 = require(game.ReplicatedStorage.Menu.CycleElementBase)
local v_u_5 = require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.SPVector)
return {
    ["new"] = function(_, p_u_6, _, p_u_7) --[[ Name: new ]] --[[ Line: 12 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_1, (copy 3): v_u_2, (copy 4): v_u_3, (copy 5): v_u_5 ]]
        local v_u_8 = v_u_4:new()
        local v_u_9 = p_u_6:get_child_part()
        v_u_8.get_part = function(_) --[[ Name: get_part ]] --[[ Line: 16 ]]
            --[[ Upvalues: (copy 1): v_u_9 ]]
            return v_u_9;
        end;
        v_u_8.get_uichild = function(_) --[[ Name: get_uichild ]] --[[ Line: 17 ]]
            --[[ Upvalues: (copy 1): p_u_6 ]]
            return p_u_6;
        end;
        v_u_8.get_callback = function(_) --[[ Name: get_callback ]] --[[ Line: 18 ]]
            --[[ Upvalues: (copy 1): p_u_7 ]]
            return p_u_7;
        end;
        local v_u_10 = false
        local v_u_11 = v_u_8:get_part():FindFirstChild("SurfaceGui")
        local v_u_12 = nil
        v_u_8.bind_data = function(p13, p14) --[[ Name: bind_data ]] --[[ Line: 23 ]]
            --[[ Upvalues: (ref 1): v_u_12 ]]
            v_u_12 = p14
            return p13;
        end;
        v_u_8.get_bound_data = function(_) --[[ Name: get_bound_data ]] --[[ Line: 27 ]]
            --[[ Upvalues: (ref 1): v_u_12 ]]
            return v_u_12;
        end;
        local v_u_15 = v_u_1:rand_rangef(0, 6.28)
        local v_u_16 = 0
        local v_u_17 = false
        local v_u_18 = nil
        local v_u_19 = 1
        local v_u_20 = true
        local v_u_21 = false
        local v_u_22 = false
        local v_u_23 = nil
        v_u_8.set_auto_zoffset_behaviour = function(p24, p25, p26) --[[ Name: set_auto_zoffset_behaviour ]] --[[ Line: 42 ]]
            --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_23 ]]
            v_u_22 = p25
            v_u_23 = p26
            return p24;
        end;
        local v_u_27 = false
        v_u_8.set_override_auto_zoffset_behaviour = function(p28, p29) --[[ Name: set_override_auto_zoffset_behaviour ]] --[[ Line: 49 ]]
            --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_22 ]]
            v_u_27 = p29
            v_u_22 = true
            return p28;
        end;
        local function _() --[[ Name: cons ]] --[[ Line: 56 ]]
            --[[ Upvalues: (copy 1): v_u_8 ]]
            v_u_8:set_visible(true, true)
            v_u_8:layout()
        end;
        v_u_8.layout = function(p30) --[[ Name: layout ]] --[[ Line: 61 ]]
            --[[ Upvalues: (copy 1): p_u_6, (copy 2): v_u_9 ]]
            p_u_6:layout()
            p30._native_size = v_u_9.Size
            p30._size = p30._native_size
        end;
        v_u_8.set_enabled_anim_updatefn = function(p31, p32) --[[ Name: set_enabled_anim_updatefn ]] --[[ Line: 67 ]]
            --[[ Upvalues: (ref 1): v_u_18 ]]
            v_u_18 = p32
            return p31;
        end;
        v_u_8.set_enabled = function(p33, p34, p35) --[[ Name: set_enabled ]] --[[ Line: 72 ]]
            --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_19, (ref 3): v_u_20 ]]
            if p34 == false then
                v_u_10 = false
                if p35 == true then
                    v_u_19 = 0
                end;
            end;
            v_u_20 = p34
            return p33;
        end;
        local v_u_36 = v_u_2:new()
        local v_u_37 = nil
        v_u_8.get_visible = function(_) --[[ Name: get_visible ]] --[[ Line: 85 ]]
            --[[ Upvalues: (ref 1): v_u_37 ]]
            return v_u_37;
        end;
        v_u_8.set_visible = function(p38, p39, p40) --[[ Name: set_visible ]] --[[ Line: 88 ]]
            --[[ Upvalues: (ref 1): v_u_37, (copy 2): v_u_36, (ref 3): v_u_1, (copy 4): v_u_9 ]]
            if not p40 and v_u_37 == p39 then
                return p38;
            end;
            v_u_37 = p39
            v_u_36:clear()
            v_u_1:fill_list_of_direct_children_of_classname(v_u_9, "SurfaceGui", v_u_36)
            for v41 = 1, v_u_36:count() do
                local v42 = v_u_36:get(v41)
                if p39 == true then
                    v42.Enabled = true
                else
                    v42.Enabled = false
                end;
            end;
            v_u_36:clear()
            p38:set_enabled(p39)
            return p38;
        end;
        local v_u_43 = 2.5
        v_u_8.set_selected_rotation_amplitude = function(p44, p45) --[[ Name: set_selected_rotation_amplitude ]] --[[ Line: 111 ]]
            --[[ Upvalues: (ref 1): v_u_43 ]]
            v_u_43 = p45
            return p44;
        end;
        local v_u_46 = 1.25
        v_u_8.set_selected_tar_scale = function(p47, p48) --[[ Name: set_selected_tar_scale ]] --[[ Line: 117 ]]
            --[[ Upvalues: (ref 1): v_u_46 ]]
            v_u_46 = p48
            return p47;
        end;
        local v_u_49 = v_u_11 == nil and 500 or v_u_11.ZOffset
        local v_u_50 = 0
        local function _() --[[ Name: calc_selected_zoffset ]] --[[ Line: 130 ]]
            --[[ Upvalues: (ref 1): v_u_50, (ref 2): v_u_49 ]]
            v_u_50 = v_u_49 + 500
        end;
        local v_u_51 = v_u_49 + 500
        v_u_8.set_unselected_zoffset = function(p52, p53) --[[ Name: set_unselected_zoffset ]] --[[ Line: 135 ]]
            --[[ Upvalues: (ref 1): v_u_49, (copy 2): p_u_6, (ref 3): v_u_51 ]]
            v_u_49 = p53 + p_u_6:get_child_id()
            v_u_51 = v_u_49 + 500
            return p52;
        end;
        v_u_8.get_sgui_offset = function(_) --[[ Name: get_sgui_offset ]] --[[ Line: 141 ]]
            --[[ Upvalues: (ref 1): v_u_49, (ref 2): v_u_51 ]]
            return v_u_49, v_u_51;
        end;
        local v_u_54 = false
        v_u_8.set_passive_anim = function(p55, p56) --[[ Name: set_passive_anim ]] --[[ Line: 144 ]]
            --[[ Upvalues: (ref 1): v_u_54 ]]
            if p56 == false then
                v_u_54 = false
                return p55;
            else
                v_u_54 = true
                return p55;
            end;
        end;
        local v_u_57 = 1
        v_u_8.set_scale = function(p58, p59) --[[ Name: set_scale ]] --[[ Line: 154 ]]
            --[[ Upvalues: (ref 1): v_u_57 ]]
            v_u_57 = p59
            return p58;
        end;
        local v_u_60 = nil
        v_u_8.get_pre_layout_fn = function(_) --[[ Name: get_pre_layout_fn ]] --[[ Line: 160 ]]
            --[[ Upvalues: (ref 1): v_u_60 ]]
            return v_u_60;
        end;
        v_u_8.set_pre_layout_fn = function(p61, p62) --[[ Name: set_pre_layout_fn ]] --[[ Line: 161 ]]
            --[[ Upvalues: (ref 1): v_u_60 ]]
            v_u_60 = p62
            p62(0)
            return p61;
        end;
        local v_u_63 = -1
        v_u_8.update = function(p64, p65, _) --[[ Name: update ]] --[[ Line: 164 ]]
            --[[ Upvalues: (ref 1): v_u_57, (ref 2): v_u_10, (ref 3): v_u_46, (ref 4): v_u_15, (ref 5): v_u_43, (ref 6): v_u_3, (ref 7): v_u_54, (ref 8): v_u_20, (ref 9): v_u_16, (copy 10): p_u_6, (ref 11): v_u_19, (copy 12): v_u_11, (ref 13): v_u_22, (ref 14): v_u_27, (ref 15): v_u_51, (ref 16): v_u_49, (ref 17): v_u_23, (ref 18): v_u_63, (ref 19): v_u_18, (ref 20): v_u_60 ]]
            local v66 = v_u_57
            local v67 = 0
            if v_u_10 == true then
                v66 = v66 * v_u_46
                v67 = math.sin(v_u_15) * v_u_43
                v_u_15 = v_u_3:IncrementWrap(v_u_15, 0.05 * p65, 6.283185307179586)
            elseif v_u_54 == true and v_u_20 == true then
                v67 = math.sin(v_u_15) * v_u_43 * 0.5
                v_u_15 = v_u_3:IncrementWrap(v_u_15, 0.05 * p65, 6.283185307179586)
            end;
            local v68 = v66 + v_u_16
            v_u_16 = v_u_3:Expt(v_u_16, 0, v_u_3:NormalizedDefaultExptValueInSeconds(0.5), p65)
            p_u_6:set_scale(v_u_3:Expt(p_u_6:get_scale(), v68, v_u_3:NormalizedDefaultExptValueInSeconds(0.5), p65))
            p_u_6:set_rotation_z(v_u_3:Expt(p_u_6:get_rotation().Z, v67, v_u_3:NormalizedDefaultExptValueInSeconds(0.5), p65))
            if v_u_20 == true then
                v_u_19 = v_u_3:Expt(v_u_19, 1, v_u_3:exptvsec(0.5), p65)
            else
                v_u_19 = v_u_3:Expt(v_u_19, 0, v_u_3:exptvsec(0.5), p65)
            end;
            if v_u_11 ~= nil and v_u_22 == true then
                local v69 = v_u_10 or v_u_27
                if v69 then
                    v_u_11.ZOffset = v_u_51
                else
                    v_u_11.ZOffset = v_u_49
                end;
                if v_u_23 then
                    v_u_23(v69)
                end;
            end;
            if v_u_63 ~= v_u_19 and v_u_18 ~= nil then
                v_u_18(v_u_20, v_u_19)
            end;
            v_u_63 = v_u_19
            if v_u_60 ~= nil then
                v_u_60(p65)
            end;
            p64:layout()
        end;
        v_u_8.get_selected = function(_) --[[ Name: get_selected ]] --[[ Line: 235 ]]
            --[[ Upvalues: (ref 1): v_u_10 ]]
            return v_u_10;
        end;
        local v_u_70 = 1
        v_u_8.set_triggered_scale_offset = function(p71, p72) --[[ Name: set_triggered_scale_offset ]] --[[ Line: 240 ]]
            --[[ Upvalues: (ref 1): v_u_70 ]]
            v_u_70 = p72
            return p71;
        end;
        v_u_8.apply_triggered_scale_offset = function(p73) --[[ Name: apply_triggered_scale_offset ]] --[[ Line: 245 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_70 ]]
            v_u_16 = v_u_70
            return p73;
        end;
        v_u_8.trigger_element = function(_, p74) --[[ Name: trigger_element ]] --[[ Line: 250 ]]
            --[[ Upvalues: (copy 1): p_u_7, (ref 2): v_u_16, (ref 3): v_u_70, (ref 4): v_u_17 ]]
            p74._input:clear_just_pressed_keys()
            p74._input:clear_just_released_keys()
            p74._input:set_has_frame_focused_element(true)
            p_u_7()
            v_u_16 = v_u_70
            v_u_17 = true
        end;
        v_u_8.did_raise_trigger_element = function(_) --[[ Name: did_raise_trigger_element ]] --[[ Line: 259 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            local v75 = v_u_17
            v_u_17 = false
            return v75;
        end;
        v_u_8.is_selectable = function(_) --[[ Name: is_selectable ]] --[[ Line: 265 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            return v_u_20;
        end;
        v_u_8.set_selected = function(_, _, p76) --[[ Name: set_selected ]] --[[ Line: 269 ]]
            --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_21 ]]
            if v_u_10 == false and p76 == true then
                v_u_21 = true
            end;
            v_u_10 = p76
        end;
        v_u_8.raise_just_selected = function(_) --[[ Name: raise_just_selected ]] --[[ Line: 276 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            local v77 = v_u_21
            v_u_21 = false
            return v77;
        end;
        v_u_8.get_native_size = function(p78) --[[ Name: get_native_size ]] --[[ Line: 282 ]]
            return p78._native_size;
        end;
        v_u_8.get_size = function(p79) --[[ Name: get_size ]] --[[ Line: 285 ]]
            return p79._size;
        end;
        v_u_8.set_size = function(p80, p81) --[[ Name: set_size ]] --[[ Line: 288 ]]
            --[[ Upvalues: (copy 1): v_u_9 ]]
            p80._size = p81
            v_u_9.Size = Vector3.new(p81.X, p81.Y, 0)
        end;
        v_u_8.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 292 ]]
            --[[ Upvalues: (copy 1): v_u_9 ]]
            return v_u_9.Position;
        end;
        v_u_8.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 296 ]]
            --[[ Upvalues: (ref 1): v_u_5 ]]
            v_u_5:errf("SPUIButton get_sgui not implemented")
            return nil;
        end;
        local v_u_82 = 1
        v_u_8.set_alpha = function(p83, p84) --[[ Name: set_alpha ]] --[[ Line: 302 ]]
            --[[ Upvalues: (ref 1): v_u_82 ]]
            v_u_82 = p84
            return p83;
        end;
        v_u_8.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 306 ]]
            --[[ Upvalues: (ref 1): v_u_82 ]]
            return v_u_82;
        end;
        v_u_8:set_visible(true, true)
        v_u_8:layout()
        return v_u_8;
    end,
    ["button_add_enabled_anim"] = function(_, p85, p_u_86) --[[ Name: button_add_enabled_anim ]] --[[ Line: 312 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3 ]]
        local v_u_87 = p85:get_part()
        local v_u_88 = 1
        local v_u_89 = v_u_1:get_list_of_children_of_classname(v_u_87, "ImageLabel")
        local v_u_90 = v_u_1:get_list_of_children_of_classname(v_u_87, "TextLabel")
        p85:set_enabled_anim_updatefn(function(_, p91) --[[ Line: 317 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_88, (ref 3): v_u_1, (copy 4): v_u_89, (copy 5): v_u_90, (copy 6): v_u_87, (copy 7): p_u_86 ]]
            local v92 = v_u_3:YForPointOf2PtLine(Vector2.new(0, 0.25), Vector2.new(1, 1), p91)
            if v_u_88 ~= v92 then
                v_u_88 = v92
                v_u_1:list_set_alpha_name(v_u_89, {
                    ["ImageAlpha"] = v_u_88
                })
                v_u_1:list_set_alpha_name(v_u_90, {
                    ["TextAlpha"] = v_u_88
                })
                v_u_1:r_set_alpha(v_u_87, p_u_86())
            end;
        end)
        return p85;
    end,
    ["button_add_enabled_anim_r_set_alpha_v2"] = function(_, p93, p_u_94) --[[ Name: button_add_enabled_anim_r_set_alpha_v2 ]] --[[ Line: 329 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3 ]]
        local v_u_95 = p93:get_part()
        local v_u_96 = 1
        local v_u_97 = v_u_1:get_list_of_children_of_classname(v_u_95, "ImageLabel")
        local v_u_98 = v_u_1:get_list_of_children_of_classname(v_u_95, "TextLabel")
        p93:set_enabled_anim_updatefn(function(_, p99) --[[ Line: 334 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_96, (ref 3): v_u_1, (copy 4): v_u_97, (copy 5): v_u_98, (copy 6): v_u_95, (copy 7): p_u_94 ]]
            local v100 = v_u_3:YForPointOf2PtLine(Vector2.new(0, 0.25), Vector2.new(1, 1), p99)
            if v_u_96 ~= v100 then
                v_u_96 = v100
                v_u_1:list_apply_suffix_alpha_attribute(v_u_97, "button_add_enabled_anim_r_set_alpha_v2", v_u_96)
                v_u_1:list_apply_suffix_alpha_attribute(v_u_98, "button_add_enabled_anim_r_set_alpha_v2", v_u_96)
                v_u_1:r_set_alpha_v2(v_u_95, p_u_94())
            end;
        end)
        return p93;
    end,
    ["button_bind_anim_toggle"] = function(_, p_u_101, p_u_102) --[[ Name: button_bind_anim_toggle ]] --[[ Line: 346 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        local v103 = {}
        local v_u_104 = p_u_101:get_part()
        local v_u_105 = v_u_1:get_list_of_children_of_classname(v_u_104, "ImageLabel")
        local v_u_106 = v_u_1:get_list_of_children_of_classname(v_u_104, "TextLabel")
        local v_u_107 = 0.5
        local v_u_108 = nil
        v103.set_toggle_off_alpha = function(p109, p110) --[[ Name: set_toggle_off_alpha ]] --[[ Line: 355 ]]
            --[[ Upvalues: (ref 1): v_u_107 ]]
            v_u_107 = p110
            return p109;
        end;
        v103.get_toggle = function(_) --[[ Name: get_toggle ]] --[[ Line: 359 ]]
            --[[ Upvalues: (ref 1): v_u_108 ]]
            return v_u_108;
        end;
        local v_u_111 = false
        v103.use_r_set_alpha_v2 = function(p112) --[[ Name: use_r_set_alpha_v2 ]] --[[ Line: 362 ]]
            --[[ Upvalues: (ref 1): v_u_111 ]]
            v_u_111 = true
            return p112;
        end;
        local v_u_113 = -1
        v103.set_toggle = function(_, p114) --[[ Name: set_toggle ]] --[[ Line: 365 ]]
            --[[ Upvalues: (ref 1): v_u_108, (ref 2): v_u_107, (ref 3): v_u_113, (ref 4): v_u_111, (ref 5): v_u_1, (copy 6): v_u_105, (copy 7): v_u_106, (copy 8): v_u_104, (copy 9): p_u_102 ]]
            v_u_108 = p114
            local v115 = p114 ~= false and 1 or v_u_107
            if v_u_113 ~= v115 then
                if v_u_111 == true then
                    v_u_1:list_apply_suffix_alpha_attribute(v_u_105, "button_bind_anim_toggle", v115)
                    v_u_1:list_apply_suffix_alpha_attribute(v_u_106, "button_bind_anim_toggle", v115)
                    v_u_1:r_set_alpha_v2(v_u_104, p_u_102())
                else
                    v_u_1:list_set_alpha_name(v_u_105, {
                        ["ImageAlpha"] = v115
                    })
                    v_u_1:list_set_alpha_name(v_u_106, {
                        ["TextAlpha"] = v115
                    })
                    v_u_1:r_set_alpha(v_u_104, p_u_102())
                end;
                v_u_113 = v115
            end;
        end;
        v103.get_button = function(_) --[[ Name: get_button ]] --[[ Line: 386 ]]
            --[[ Upvalues: (copy 1): p_u_101 ]]
            return p_u_101;
        end;
        return v103;
    end,
    ["set_button_text"] = function(_, p116, p117) --[[ Name: set_button_text ]] --[[ Line: 391 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        for _, v118 in v_u_1:get_list_of_children_of_classname(p116:get_part(), "TextLabel"):key_itr() do
            if v118:GetAttribute("NoButtonText") == nil then
                v118.Text = p117
            end;
        end;
    end
};
