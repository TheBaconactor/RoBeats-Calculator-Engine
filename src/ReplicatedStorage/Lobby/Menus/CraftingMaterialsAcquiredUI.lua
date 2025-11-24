-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:41 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Local.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_7 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_8 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_9 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_10 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_11 = require(game.ReplicatedStorage.Menu.CycleElementBase)
local v_u_12 = require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_13 = require(game.ReplicatedStorage.Crafting.CraftingMaterialBase)
local v_u_14 = require(game.ReplicatedStorage.Shared.CooldownDelay)
local v_u_15 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_16 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_20 = {
    ["material_id_list_tab_to_reward_desc_info_list"] = function(_, p17) --[[ Name: material_id_list_tab_to_reward_desc_info_list ]] --[[ Line: 25 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_15 ]]
        local v18 = v_u_2:new()
        for _, v19 in pairs(p17) do
            v18:push_back(v_u_15.RewardInfo:new(v_u_15.RewardType.CraftingMaterials, 1, v19))
        end;
        return v18;
    end,
    ["ListElement"] = {}
}
v_u_20.new = function(_, p_u_21, p_u_22, p_u_23, p_u_24, p_u_25) --[[ Name: new ]] --[[ Line: 33 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_14, (copy 4): v_u_1, (copy 5): v_u_7, (copy 6): v_u_5, (copy 7): v_u_4, (copy 8): v_u_6, (copy 9): v_u_8, (copy 10): v_u_15, (copy 11): v_u_9, (copy 12): v_u_16, (copy 13): v_u_20, (copy 14): v_u_12 ]]
    local v_u_26 = v_u_3:new(p_u_22, p_u_23)
    local v_u_27 = nil
    local v_u_28 = 1
    local v_u_29 = 1
    local v_u_30 = v_u_2:new()
    local v_u_31 = nil
    local v_u_32 = nil
    local v_u_33 = nil
    local v_u_34 = nil
    local v_u_35 = nil
    local v_u_36 = nil
    local v_u_37 = v_u_14:new()
    v_u_26.get_sfx_cooldown = function(_) --[[ Name: get_sfx_cooldown ]] --[[ Line: 49 ]]
        --[[ Upvalues: (copy 1): v_u_37 ]]
        return v_u_37;
    end;
    local function f_cons() --[[ Name: cons ]] --[[ Line: 51 ]]
        --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_1, (ref 3): v_u_7, (copy 4): v_u_26, (ref 5): v_u_31, (ref 6): v_u_32, (ref 7): v_u_33, (ref 8): v_u_34, (ref 9): v_u_35, (ref 10): v_u_36, (copy 11): p_u_21, (ref 12): v_u_5, (ref 13): v_u_4, (copy 14): p_u_22, (copy 15): p_u_25, (copy 16): p_u_23, (ref 17): v_u_6 ]]
        v_u_27 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.CraftingMaterialsAcquiredUI:Clone()
        v_u_27.Name = v_u_1:gen_name(v_u_27.Name)
        v_u_27.Parent = v_u_7:get_world_ui_folder()
        v_u_26._native_size = v_u_27.PrimaryPart.Size
        v_u_26._size = v_u_26._native_size
        local l_SelectedInfoSection_0 = v_u_27.PrimaryPart.SurfaceGui.Frame.SelectedInfoSection
        v_u_31 = l_SelectedInfoSection_0.IconFrame.Icon
        v_u_32 = l_SelectedInfoSection_0.NameDisplay
        v_u_33 = l_SelectedInfoSection_0.DescriptionDisplay
        v_u_34 = l_SelectedInfoSection_0.OwnedDisplay
        v_u_35 = v_u_27.PrimaryPart.SurfaceGui.Frame.TitleText
        v_u_35.Text = "Materials Acquired!"
        v_u_36 = v_u_27.PrimaryPart.SurfaceGui.Frame.SubDisplay
        v_u_36.Text = ""
        v_u_31.Image = v_u_1:transparent_assetid()
        v_u_32.Text = ""
        v_u_33.Text = ""
        v_u_34.Text = ""
        v_u_26:add_cycle_element(p_u_21, 1, v_u_5:new(v_u_4:new(v_u_26, v_u_27.PrimaryPart, v_u_27.BackButtonSurface), p_u_22, function() --[[ Line: 78 ]]
            --[[ Upvalues: (ref 1): p_u_25, (ref 2): p_u_23, (ref 3): v_u_26, (ref 4): p_u_21, (ref 5): v_u_6 ]]
            if p_u_25 then
                p_u_25()
            end;
            p_u_23:remove_menu(v_u_26)
            p_u_21._sfx_manager:play_sfx(v_u_6.SFX_MENU_CLOSE)
        end))
        v_u_26:setup_list_elements()
        v_u_26:reset_selected_item()
        v_u_26:transition_update_visual(0)
        v_u_26:layout()
    end;
    v_u_26.set_text_display = function(p38, p39, p40) --[[ Name: set_text_display ]] --[[ Line: 94 ]]
        --[[ Upvalues: (ref 1): v_u_35, (ref 2): v_u_36 ]]
        v_u_35.Text = p39
        v_u_36.Text = p40
        return p38;
    end;
    v_u_26.finish_animation = function(p41) --[[ Name: finish_animation ]] --[[ Line: 100 ]]
        --[[ Upvalues: (copy 1): v_u_30 ]]
        for _, v42 in v_u_30:key_itr() do
            v42:finish_animation()
        end;
        return p41;
    end;
    v_u_26.list_element_pressed = function(_, p43, _, p44) --[[ Name: list_element_pressed ]] --[[ Line: 107 ]]
        --[[ Upvalues: (copy 1): p_u_21, (ref 2): v_u_6, (copy 3): v_u_30, (ref 4): v_u_31, (ref 5): v_u_32, (ref 6): v_u_8, (ref 7): v_u_15, (ref 8): v_u_33, (ref 9): v_u_34, (ref 10): v_u_9, (ref 11): v_u_1, (ref 12): v_u_16 ]]
        p_u_21._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
        for v45 = 1, v_u_30:count() do
            local v46 = v_u_30:get(v45)
            if v46 == p43 then
                v46:set_highlighted(true)
            else
                v46:set_highlighted(false)
            end;
        end;
        v_u_31.Image = p44:get_image()
        if p44:get_amount() == 1 then
            v_u_32.Text = p44:get_name()
        else
            v_u_32.Text = p44:get_name_with_amount()
        end;
        v_u_32.TextColor3 = v_u_8:singleton():tier_get_color(p43:get_display_tier())
        if p44:get_type() == v_u_15.RewardType.CraftingMaterials then
            v_u_33.Text = v_u_8:singleton():get_material_description(p44:get_id())
        else
            v_u_33.Text = p44:get_name_with_amount()
        end;
        local v47 = p_u_21._player_blob_manager:get_player_blob()
        if p44:get_type() == v_u_15.RewardType.CraftingMaterials then
            v_u_34.Text = string.format("%d", v_u_9:get_count_of_material(v47, p44:get_id()))
            return;
        elseif p44:get_type() == v_u_15.RewardType.Coins then
            v_u_34.Text = v_u_1:comma_value(v_u_16:get_coin_currency(v47))
            return;
        elseif p44:get_type() == v_u_15.RewardType.Stars then
            v_u_34.Text = v_u_1:comma_value(v_u_16:get_star_currency(v47))
        else
            v_u_34.Text = "-"
        end;
    end;
    v_u_26.setup_list_elements = function(p48) --[[ Name: setup_list_elements ]] --[[ Line: 144 ]]
        --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_2, (copy 3): p_u_24, (ref 4): v_u_20, (copy 5): p_u_21, (ref 6): v_u_4, (copy 7): p_u_22, (copy 8): v_u_30 ]]
        local l_AcquiredItemProto_0 = v_u_27.AcquiredItemProto
        l_AcquiredItemProto_0.Parent = nil
        local v49 = v_u_2:new()
        for v50 = 1, 12 do
            v49:push_back(v_u_27.Anchors:FindFirstChild(string.format("Anchor%d", v50)))
        end;
        for v51 = 1, p_u_24:count() do
            if v49:count() < v51 then
                break;
            end;
            local v52 = v49:get(v51)
            local v53 = l_AcquiredItemProto_0:Clone()
            v53.Name = string.format("AcquiredItem(%d)", v51)
            v53.Parent = v_u_27
            v53.Position = v52.Position
            local v54 = v_u_20.ListElement:new(p_u_21, v_u_4:new(p48, v_u_27.PrimaryPart, v53), p_u_22, p48, v51, (v51 - 1) * 0.35 + 0.001)
            v54:set_reward_desc_info(p_u_24:get(v51))
            p48:add_cycle_element(p_u_21, 1, v54)
            v_u_30:push_back(v54)
        end;
    end;
    v_u_26.behaviour_update = function(p55, p56, p57) --[[ Name: behaviour_update ]] --[[ Line: 178 ]]
        --[[ Upvalues: (copy 1): p_u_21, (copy 2): v_u_37, (ref 3): v_u_12, (copy 4): v_u_30 ]]
        p55:behaviour_update_base(p56, p_u_21)
        v_u_37:update(p56)
        if p55._current_mode == v_u_12.MODE_OPEN then
            for v58 = 1, v_u_30:count() do
                v_u_30:get(v58):behaviour_update(p56, p57)
            end;
        end;
    end;
    v_u_26.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 188 ]]
        --[[ Upvalues: (ref 1): v_u_27 ]]
        v_u_27:Destroy()
    end;
    v_u_26.layout = function(p59) --[[ Name: layout ]] --[[ Line: 192 ]]
        --[[ Upvalues: (copy 1): p_u_22, (ref 2): v_u_29, (ref 3): v_u_27, (copy 4): v_u_30 ]]
        p59:opt_rescale_to_max_nxy(p_u_22, 0.88, 0.8, v_u_29)
        local v60, v61 = p59:opt_update_cframe_params(p_u_22, {
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p59:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v60 == true then
            v_u_27:SetPrimaryPartCFrame(v61)
        end;
        for v62 = 1, v_u_30:count() do
            v_u_30:get(v62):layout()
        end;
    end;
    v_u_26.set_alpha = function(_, p63) --[[ Name: set_alpha ]] --[[ Line: 208 ]]
        --[[ Upvalues: (ref 1): v_u_28, (copy 2): v_u_30, (ref 3): v_u_1, (ref 4): v_u_27 ]]
        if v_u_28 ~= p63 then
            v_u_28 = p63
            for v64 = 1, v_u_30:count() do
                v_u_30:get(v64):set_parent_alpha(v_u_28)
            end;
            v_u_1:r_set_alpha(v_u_27, v_u_28)
        end;
    end;
    v_u_26.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 217 ]]
        --[[ Upvalues: (ref 1): v_u_28 ]]
        return v_u_28;
    end;
    v_u_26.set_scale = function(_, p65) --[[ Name: set_scale ]] --[[ Line: 218 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        v_u_29 = p65
    end;
    v_u_26.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 219 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        return v_u_29;
    end;
    v_u_26.get_native_size = function(p66) --[[ Name: get_native_size ]] --[[ Line: 221 ]]
        return p66._native_size;
    end;
    v_u_26.get_size = function(p67) --[[ Name: get_size ]] --[[ Line: 224 ]]
        return p67._size;
    end;
    v_u_26.set_size = function(p68, p69) --[[ Name: set_size ]] --[[ Line: 227 ]]
        --[[ Upvalues: (ref 1): v_u_27 ]]
        p68._size = p69
        v_u_27.PrimaryPart.Size = Vector3.new(p69.X, p69.Y, 0)
    end;
    v_u_26.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 231 ]]
        --[[ Upvalues: (ref 1): v_u_27 ]]
        return v_u_27.PrimaryPart.Position;
    end;
    v_u_26.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 234 ]]
        --[[ Upvalues: (ref 1): v_u_27 ]]
        return v_u_27.PrimaryPart.SurfaceGui;
    end;
    f_cons()
    return v_u_26;
end;
v_u_20.ListElement.new = function(_, p_u_70, p_u_71, _, p_u_72, p_u_73, p_u_74) --[[ Name: new ]] --[[ Line: 243 ]]
    --[[ Upvalues: (copy 1): v_u_11, (copy 2): v_u_15, (copy 3): v_u_13, (copy 4): v_u_8, (copy 5): v_u_10, (copy 6): v_u_6, (copy 7): v_u_1 ]]
    local v_u_75 = v_u_11:new()
    local v_u_76 = false
    local v_u_77 = p_u_71:get_child_part()
    local v_u_78 = nil
    local v_u_79 = nil
    local v_u_80 = nil
    local v_u_81 = v_u_15.RewardInfo:new(v_u_15.RewardType.None, 0, -1)
    local v_u_82 = 0
    local l_T2_0 = v_u_13.Tier.T2
    v_u_75.get_display_tier = function(_) --[[ Name: get_display_tier ]] --[[ Line: 255 ]]
        --[[ Upvalues: (ref 1): l_T2_0 ]]
        return l_T2_0;
    end;
    local v_u_83 = 0
    local function f_cons() --[[ Name: cons ]] --[[ Line: 258 ]]
        --[[ Upvalues: (ref 1): v_u_83, (copy 2): v_u_77, (ref 3): v_u_78, (ref 4): v_u_79, (ref 5): v_u_80, (copy 6): v_u_75 ]]
        v_u_83 = v_u_77.SurfaceGui.ZOffset
        v_u_78 = v_u_77.SurfaceGui.Frame.Pane.Icon
        v_u_79 = v_u_77.SurfaceGui.Frame.Pane.NameDisplay
        v_u_80 = v_u_77.SurfaceGui.Frame.Pane
        v_u_75:set_alpha(0)
        v_u_75:set_selected(nil, false)
        v_u_75:layout()
    end;
    v_u_75.set_reward_desc_info = function(_, p84) --[[ Name: set_reward_desc_info ]] --[[ Line: 270 ]]
        --[[ Upvalues: (ref 1): v_u_81, (ref 2): v_u_79, (ref 3): v_u_78, (ref 4): v_u_15, (ref 5): l_T2_0, (ref 6): v_u_8, (ref 7): v_u_13 ]]
        v_u_81 = p84
        v_u_79.Text = v_u_81:get_name_with_amount()
        v_u_78.Image = v_u_81:get_image()
        if p84:get_type() == v_u_15.RewardType.CraftingMaterials then
            l_T2_0 = v_u_8:singleton():get_material_tier(p84:get_id())
        else
            l_T2_0 = v_u_13.Tier.T2
        end;
        v_u_79.TextColor3 = v_u_8:singleton():tier_get_color(l_T2_0)
    end;
    v_u_75.behaviour_update = function(p85, p86) --[[ Name: behaviour_update ]] --[[ Line: 282 ]]
        --[[ Upvalues: (ref 1): p_u_74, (ref 2): v_u_10, (copy 3): p_u_72, (copy 4): p_u_73, (ref 5): v_u_81, (ref 6): l_T2_0, (ref 7): v_u_13, (copy 8): p_u_70, (ref 9): v_u_6, (ref 10): v_u_82, (ref 11): v_u_1, (copy 12): p_u_71, (ref 13): v_u_76 ]]
        if p_u_74 > 0 then
            p_u_74 = p_u_74 - v_u_10:TimescaleToDeltaTime(p86)
            if p_u_74 <= 0 then
                p_u_72:list_element_pressed(p85, p_u_73, v_u_81)
                if l_T2_0 == v_u_13.Tier.T4 or l_T2_0 == v_u_13.Tier.T5 then
                    if p_u_72:get_sfx_cooldown():is_on_cooldown(l_T2_0) ~= true then
                        p_u_70._sfx_manager:play_sfx(v_u_6.SFX_FEVERCHEER_1)
                        p_u_72:get_sfx_cooldown():add_cooldown_to_id(l_T2_0, 0.75)
                        return;
                    end;
                elseif l_T2_0 == v_u_13.Tier.T3 then
                    if p_u_72:get_sfx_cooldown():is_on_cooldown(l_T2_0) ~= true then
                        p_u_70._sfx_manager:play_sfx(v_u_6.SFX_FANFARE)
                        p_u_72:get_sfx_cooldown():add_cooldown_to_id(l_T2_0, 0.5)
                        return;
                    end;
                else
                    if l_T2_0 ~= v_u_13.Tier.T2 then
                        p_u_70._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
                        return;
                    end;
                    if p_u_72:get_sfx_cooldown():is_on_cooldown(l_T2_0) ~= true then
                        p_u_70._sfx_manager:play_sfx(v_u_6.SFX_ACQUIRE)
                        p_u_72:get_sfx_cooldown():add_cooldown_to_id(l_T2_0, 0.25)
                        return;
                    end;
                end;
            end;
        else
            if v_u_82 < 1 then
                v_u_82 = v_u_1:clamp(v_u_82 + v_u_10:SecondsToTick(0.25) * p86, 0, 1)
                p_u_71:set_scale(v_u_10:BezierYForT(0, 1.5, 0, 1, 0.5, 1, 1, 1, v_u_82))
                p85:set_alpha(v_u_10:BezierYForT(0, 0, 0.5, 0, 1, 0.5, 1, 1, v_u_82))
                return;
            end;
            p_u_71:set_scale(v_u_10:Expt(p_u_71:get_scale(), v_u_76 == true and 1.1 or 1, v_u_10:NormalizedDefaultExptValueInSeconds(0.5), p86))
        end;
    end;
    v_u_75.finish_animation = function(p87) --[[ Name: finish_animation ]] --[[ Line: 331 ]]
        --[[ Upvalues: (ref 1): p_u_74, (ref 2): v_u_82 ]]
        p_u_74 = 0
        v_u_82 = 1
        p87:set_alpha(1)
    end;
    v_u_75.layout = function(p88) --[[ Name: layout ]] --[[ Line: 337 ]]
        --[[ Upvalues: (copy 1): p_u_71, (copy 2): v_u_77 ]]
        p_u_71:layout()
        p88._native_size = v_u_77.Size
        p88._size = p88._native_size
    end;
    local v_u_89 = true
    v_u_75.set_enabled = function(p90, p91) --[[ Name: set_enabled ]] --[[ Line: 344 ]]
        --[[ Upvalues: (ref 1): v_u_76, (ref 2): v_u_89 ]]
        if p91 == false then
            v_u_76 = false
        else
            p90:set_alpha(1)
        end;
        v_u_89 = p91
        return p90;
    end;
    v_u_75.set_visible = function(p92, p93) --[[ Name: set_visible ]] --[[ Line: 354 ]]
        --[[ Upvalues: (copy 1): v_u_77 ]]
        if p93 == true then
            v_u_77.SurfaceGui.Enabled = true
        else
            v_u_77.SurfaceGui.Enabled = false
        end;
        p92:set_enabled(p93)
        return p92;
    end;
    v_u_75.is_selectable = function(_) --[[ Name: is_selectable ]] --[[ Line: 364 ]]
        --[[ Upvalues: (ref 1): v_u_89, (ref 2): p_u_74, (ref 3): v_u_82 ]]
        local v94 = v_u_89
        if v94 then
            if p_u_74 <= 0 then
                v94 = v_u_82 >= 0
            else
                v94 = false
            end;
        end;
        return v94;
    end;
    v_u_75.get_selected = function(_) --[[ Name: get_selected ]] --[[ Line: 365 ]]
        --[[ Upvalues: (ref 1): v_u_76 ]]
        return v_u_76;
    end;
    v_u_75.trigger_element = function(p95, _) --[[ Name: trigger_element ]] --[[ Line: 366 ]]
        --[[ Upvalues: (copy 1): p_u_71, (copy 2): p_u_72, (copy 3): p_u_73, (ref 4): v_u_81 ]]
        p_u_71:set_scale(1.5)
        p_u_72:list_element_pressed(p95, p_u_73, v_u_81)
    end;
    v_u_75.set_highlighted = function(_, _) end;
    v_u_75.set_selected = function(_, _, p96) --[[ Name: set_selected ]] --[[ Line: 375 ]]
        --[[ Upvalues: (ref 1): v_u_76, (copy 2): v_u_77, (ref 3): v_u_83, (copy 4): p_u_71 ]]
        v_u_76 = p96
        if v_u_76 then
            v_u_77.SurfaceGui.ZOffset = v_u_83 + 500 + p_u_71:get_child_id()
        else
            v_u_77.SurfaceGui.ZOffset = v_u_83 + p_u_71:get_child_id()
        end;
    end;
    v_u_75.get_native_size = function(p97) --[[ Name: get_native_size ]] --[[ Line: 385 ]]
        return p97._native_size;
    end;
    v_u_75.get_size = function(p98) --[[ Name: get_size ]] --[[ Line: 386 ]]
        return p98._size;
    end;
    v_u_75.set_size = function(p99, p100) --[[ Name: set_size ]] --[[ Line: 387 ]]
        --[[ Upvalues: (copy 1): v_u_77 ]]
        p99._size = p100
        v_u_77.Size = Vector3.new(p100.X, p100.Y, 0)
    end;
    v_u_75.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 391 ]]
        --[[ Upvalues: (copy 1): v_u_77 ]]
        return v_u_77.Position;
    end;
    local v_u_101 = 1
    v_u_75.set_parent_alpha = function(_, p102) --[[ Name: set_parent_alpha ]] --[[ Line: 394 ]]
        --[[ Upvalues: (ref 1): v_u_101 ]]
        v_u_101 = p102
    end;
    local v_u_103 = 1
    v_u_75.set_alpha = function(_, p104) --[[ Name: set_alpha ]] --[[ Line: 399 ]]
        --[[ Upvalues: (ref 1): v_u_103, (ref 2): v_u_1, (copy 3): v_u_77, (ref 4): v_u_101 ]]
        if p104 ~= v_u_103 then
            v_u_103 = p104
            v_u_1:list_set_alpha_name(v_u_1:get_list_of_children_of_classname(v_u_77, "TextLabel"), {
                ["TextAlpha"] = v_u_103
            })
            v_u_1:list_set_alpha_name(v_u_1:get_list_of_children_of_classname(v_u_77, "ImageLabel"), {
                ["ImageAlpha"] = v_u_103
            })
            v_u_1:r_set_alpha(v_u_77, v_u_101)
        end;
    end;
    f_cons()
    return v_u_75;
end;
return v_u_20;
