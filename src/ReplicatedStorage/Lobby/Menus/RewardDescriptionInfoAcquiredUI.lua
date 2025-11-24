-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:47 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_7 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_8 = require(game.ReplicatedStorage.Shared.ListAdapter)
local v_u_9 = require(game.ReplicatedStorage.Shared.HUDNotification)
local v_u_10 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_11 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_12 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_13 = require(game.ReplicatedStorage.Shared.CooldownDelay)
local v_u_14 = require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_15 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_16 = require(game.ReplicatedStorage.Crafting.CraftingMaterialBase)
local v_u_17 = require(game.ReplicatedStorage.AudioData.AudioMod)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v18 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_19 = nil
v18:require_shared(function() --[[ Line: 26 ]]
    --[[ Upvalues: (ref 1): v_u_19 ]]
    v_u_19 = require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
end)
local v_u_20 = {
    ["ListElement"] = {}
}
v_u_20.ListElement.new = function(_, p_u_21, p_u_22, p_u_23, p_u_24) --[[ Name: new ]] --[[ Line: 36 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_4, (copy 3): v_u_6, (copy 4): v_u_9, (copy 5): v_u_10, (copy 6): v_u_11, (ref 7): v_u_19, (copy 8): v_u_12, (copy 9): v_u_1, (copy 10): v_u_16, (copy 11): v_u_15, (copy 12): v_u_17 ]]
    local v25 = {
        ["layout"] = function(_) end
    }
    local v_u_26 = nil
    local v_u_27 = nil
    local v_u_28 = nil
    local v_u_29 = nil
    local v_u_30 = nil
    local v_u_31 = nil
    local v_u_32 = nil
    v25.get_data = function(_) --[[ Name: get_data ]] --[[ Line: 45 ]]
        --[[ Upvalues: (ref 1): v_u_32 ]]
        return v_u_32;
    end;
    local function f_cons() --[[ Name: cons ]] --[[ Line: 47 ]]
        --[[ Upvalues: (copy 1): p_u_23, (ref 2): v_u_26, (ref 3): v_u_27, (copy 4): p_u_22, (copy 5): p_u_21, (ref 6): v_u_5, (ref 7): v_u_4, (ref 8): v_u_32, (ref 9): v_u_6, (copy 10): p_u_24, (ref 11): v_u_29, (ref 12): v_u_30, (ref 13): v_u_31, (ref 14): v_u_28, (ref 15): v_u_9 ]]
        v_u_26 = p_u_23.PrimaryPart.SurfaceGui.Frame
        v_u_27 = p_u_22:add_cycle_element(p_u_21, 1, v_u_5:new(v_u_4:new(p_u_22, p_u_22:get_uichild_parent(), p_u_23.PrimaryPart), p_u_21._spui, function() --[[ Line: 54 ]]
            --[[ Upvalues: (ref 1): v_u_32, (ref 2): p_u_21, (ref 3): v_u_6, (ref 4): p_u_24 ]]
            if v_u_32 ~= nil then
                p_u_21._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
                p_u_24(v_u_32, true)
            end;
        end)):set_auto_zoffset_behaviour(true)
        v_u_27:set_visible(false)
        v_u_29 = v_u_26.Icon
        v_u_29.Visible = false
        v_u_30 = v_u_26.Overlay
        v_u_30.Visible = false
        v_u_31 = v_u_26.NewDisplay
        v_u_31.Visible = false
        v_u_28 = v_u_9:create_display_wrapper(v_u_26.Notification, v_u_26.Notification.Display)
        v_u_28:update_state(false, 0)
    end;
    v25.set_display_element = function(p33, p34) --[[ Name: set_display_element ]] --[[ Line: 75 ]]
        --[[ Upvalues: (ref 1): v_u_32, (ref 2): v_u_27, (ref 3): v_u_29, (ref 4): v_u_10, (ref 5): v_u_11, (ref 6): v_u_30, (ref 7): v_u_19, (copy 8): p_u_21, (ref 9): v_u_31, (ref 10): v_u_28 ]]
        v_u_32 = p34
        if v_u_32 then
            v_u_27:set_visible(true)
            v_u_29.Visible = true
            if v_u_32:get_type() == v_u_10.RewardType.Song then
                local v35 = v_u_32:get_id()
                v_u_11:singleton():render_coverimage_for_key(v_u_29, v_u_30, v35)
                if v_u_19:get_playerblob_songkey_in_collection(p_u_21._player_blob_manager:get_player_blob(), v35, p_u_21._player_blob_manager:get_cached_collection_info()) == false and p34:playerblob_get_display_owned_count(p_u_21._player_blob_manager:get_player_blob()) == 1 then
                    v_u_31.Visible = true
                end;
            else
                v_u_29.Image = v_u_32:get_image()
                v_u_30.Visible = false
                v_u_31.Visible = false
            end;
            if v_u_32:get_amount() > 1 then
                v_u_28:update_state(true, v_u_32:get_amount())
                return p33;
            else
                v_u_28:update_state(false, 0)
                return p33;
            end;
        else
            v_u_27:set_visible(false)
            v_u_29.Visible = false
            v_u_30.Visible = false
            v_u_28:update_state(false, 0)
            v_u_31.Visible = false
            return p33;
        end;
    end;
    local v_u_36 = 1
    v25.start_fade_in_animation = function(_) --[[ Name: start_fade_in_animation ]] --[[ Line: 114 ]]
        --[[ Upvalues: (ref 1): v_u_36, (ref 2): v_u_27 ]]
        v_u_36 = 0
        v_u_27:set_enabled(false, true)
    end;
    v25.behaviour_update = function(_, p37) --[[ Name: behaviour_update ]] --[[ Line: 119 ]]
        --[[ Upvalues: (ref 1): v_u_36, (ref 2): v_u_12, (ref 3): v_u_27, (ref 4): v_u_1, (ref 5): v_u_26, (ref 6): v_u_32, (ref 7): v_u_16, (ref 8): v_u_10, (ref 9): v_u_15, (ref 10): v_u_11, (ref 11): v_u_17, (copy 12): p_u_22, (copy 13): p_u_21, (ref 14): v_u_6, (copy 15): p_u_24 ]]
        if v_u_36 < 1 then
            v_u_36 = v_u_12:move_to(v_u_36, 1, 0.125, p37)
            if v_u_36 >= 1 then
                v_u_27:set_enabled(true)
                v_u_27:set_scale(1)
                v_u_1:r_set_alpha(v_u_26, 1)
                if v_u_32 then
                    local l_T2_0 = v_u_16.Tier.T2
                    if v_u_32:get_type() == v_u_10.RewardType.CraftingMaterials then
                        l_T2_0 = v_u_15:singleton():get_material_tier(v_u_32:get_id())
                    elseif v_u_32:get_type() == v_u_10.RewardType.Song and v_u_11:singleton():key_get_audiomod(v_u_32:get_id()) == v_u_17.Hard then
                        l_T2_0 = v_u_16.Tier.T5
                    end;
                    if l_T2_0 == v_u_16.Tier.T4 or l_T2_0 == v_u_16.Tier.T5 then
                        if p_u_22:get_sfx_cooldown():is_on_cooldown(l_T2_0) ~= true then
                            p_u_21._sfx_manager:play_sfx(v_u_6.SFX_FEVERCHEER_1)
                            p_u_22:get_sfx_cooldown():add_cooldown_to_id(l_T2_0, 0.75)
                        end;
                    elseif l_T2_0 == v_u_16.Tier.T3 then
                        if p_u_22:get_sfx_cooldown():is_on_cooldown(l_T2_0) ~= true then
                            p_u_21._sfx_manager:play_sfx(v_u_6.SFX_FANFARE)
                            p_u_22:get_sfx_cooldown():add_cooldown_to_id(l_T2_0, 0.5)
                        end;
                    elseif l_T2_0 == v_u_16.Tier.T2 then
                        if p_u_22:get_sfx_cooldown():is_on_cooldown(l_T2_0) ~= true then
                            p_u_21._sfx_manager:play_sfx(v_u_6.SFX_ACQUIRE)
                            p_u_22:get_sfx_cooldown():add_cooldown_to_id(l_T2_0, 0.25)
                        end;
                    else
                        p_u_21._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
                    end;
                    if p_u_22:has_any_pending_reward_desc_infos_to_show() then
                        p_u_24(v_u_32, false)
                    else
                        p_u_24(v_u_32, true)
                    end;
                end;
            else
                v_u_27:set_scale(v_u_12:BezierYForT(0, 1.5, 0, 1, 0.5, 1, 1, 1, v_u_36))
                v_u_1:r_set_alpha(v_u_26, (v_u_12:BezierYForT(0, 0, 0.5, 0, 1, 0.5, 1, 1, v_u_36)))
            end;
        end;
    end;
    v25.set_visible = function(p38, p39) --[[ Name: set_visible ]] --[[ Line: 178 ]]
        --[[ Upvalues: (ref 1): v_u_27 ]]
        v_u_27:set_visible(p39)
        return p38;
    end;
    v25.select = function(_) --[[ Name: select ]] --[[ Line: 183 ]]
        --[[ Upvalues: (ref 1): v_u_32, (copy 2): p_u_24 ]]
        if v_u_32 then
            p_u_24(v_u_32, false)
        end;
    end;
    f_cons()
    return v25;
end;
v_u_20.new = function(_, p_u_40, p_u_41, p_u_42, p43, p_u_44) --[[ Name: new ]] --[[ Line: 193 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_8, (copy 4): v_u_1, (copy 5): v_u_5, (copy 6): v_u_4, (copy 7): v_u_6, (copy 8): v_u_20, (copy 9): v_u_10, (copy 10): v_u_11, (copy 11): v_u_13, (copy 12): v_u_14, (copy 13): v_u_12, (copy 14): v_u_7 ]]
    local v_u_45 = v_u_3:new(p_u_41, p_u_42)
    local v_u_46 = v_u_2:new()
    local v_u_47 = nil
    local v_u_48 = nil
    local v_u_49 = nil
    local v_u_50 = nil
    local v_u_51 = nil
    local v_u_52 = nil
    local v_u_53 = nil
    for _, v54 in p43:key_itr() do
        v_u_46:push_back(v54)
    end;
    v_u_45.has_any_pending_reward_desc_infos_to_show = function(_) --[[ Name: has_any_pending_reward_desc_infos_to_show ]] --[[ Line: 208 ]]
        --[[ Upvalues: (copy 1): v_u_46 ]]
        return v_u_46:count() > 0;
    end;
    local v_u_55 = v_u_2:new()
    local v_u_56 = true
    v_u_45.show_description_extra_text = function(p57, p58) --[[ Name: show_description_extra_text ]] --[[ Line: 212 ]]
        --[[ Upvalues: (ref 1): v_u_56 ]]
        v_u_56 = p58
        return p57;
    end;
    local v_u_65 = v_u_8:new():set_fn_get_data_list(function() --[[ Line: 218 ]]
        --[[ Upvalues: (copy 1): v_u_55 ]]
        return v_u_55;
    end):set_fn_set_element_data(function(p59, p60, _, _) --[[ Line: 219 ]]
        if p60 == nil then
            p59:set_display_element(nil)
        else
            p59:set_display_element(p60)
        end;
    end):set_fn_next_prev_visible(function(p61, p62) --[[ Line: 226 ]]
        --[[ Upvalues: (copy 1): v_u_45, (ref 2): v_u_49, (ref 3): v_u_53 ]]
        if v_u_45:has_any_pending_reward_desc_infos_to_show() then
            v_u_49:set_visible(false)
            v_u_53:set_visible(false)
        else
            v_u_49:set_visible(p61)
            v_u_53:set_visible(p62)
        end;
    end):set_fn_update_page_display(function(p63, p64) --[[ Line: 235 ]]
        --[[ Upvalues: (ref 1): v_u_50 ]]
        v_u_50.Text = string.format("%d/%d", p63, p64)
    end)
    local function f_cons() --[[ Name: cons ]] --[[ Line: 239 ]]
        --[[ Upvalues: (ref 1): v_u_51, (ref 2): v_u_1, (copy 3): v_u_45, (ref 4): v_u_50, (ref 5): v_u_52, (ref 6): v_u_48, (ref 7): v_u_49, (copy 8): p_u_40, (ref 9): v_u_5, (ref 10): v_u_4, (copy 11): p_u_41, (ref 12): v_u_6, (copy 13): v_u_65, (ref 14): v_u_53, (copy 15): p_u_42, (ref 16): p_u_44, (ref 17): v_u_20, (ref 18): v_u_56, (ref 19): v_u_10, (ref 20): v_u_11, (ref 21): v_u_47 ]]
        v_u_51 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.Util.RewardDescriptionInfoAcquiredUI:Clone()
        v_u_51.Name = v_u_1:gen_name(v_u_51.Name)
        v_u_45:set_showing(true)
        v_u_45._native_size = v_u_51.PrimaryPart.Size
        v_u_45._size = v_u_45._native_size
        local l_Frame_0 = v_u_51.MainSurface.SurfaceGui.Frame
        v_u_50 = l_Frame_0.PageDisplay
        v_u_52 = l_Frame_0.HeaderDisplay
        v_u_52.Text = "Materials Acquired..."
        v_u_48 = l_Frame_0.SubDisplay
        v_u_48.Text = ""
        v_u_49 = v_u_45:add_cycle_element(p_u_40, 1, v_u_5:new(v_u_4:new(v_u_45, v_u_51.PrimaryPart, v_u_51.ArrowRight), p_u_41, function() --[[ Line: 257 ]]
            --[[ Upvalues: (ref 1): p_u_40, (ref 2): v_u_6, (ref 3): v_u_65 ]]
            p_u_40._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            v_u_65:next_page()
        end))
        v_u_53 = v_u_45:add_cycle_element(p_u_40, 1, v_u_5:new(v_u_4:new(v_u_45, v_u_51.PrimaryPart, v_u_51.ArrowLeft), p_u_41, function() --[[ Line: 266 ]]
            --[[ Upvalues: (ref 1): p_u_40, (ref 2): v_u_6, (ref 3): v_u_65 ]]
            p_u_40._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            v_u_65:prev_page()
        end))
        v_u_45:add_cycle_element(p_u_40, 1, v_u_5:new(v_u_4:new(v_u_45, v_u_51.PrimaryPart, v_u_51.BackButtonSurface), p_u_41, function() --[[ Line: 275 ]]
            --[[ Upvalues: (ref 1): p_u_40, (ref 2): v_u_6, (ref 3): p_u_42, (ref 4): v_u_45, (ref 5): p_u_44 ]]
            p_u_40._sfx_manager:play_sfx(v_u_6.SFX_MENU_CLOSE)
            p_u_42:remove_menu(v_u_45)
            if p_u_44 then
                p_u_44()
                p_u_44 = nil
            end;
        end))
        local l_SelectedInfoSection_0 = l_Frame_0.SelectedInfoSection
        local l_NameDisplay_0 = l_SelectedInfoSection_0.NameDisplay
        local l_TextColor3_0 = l_NameDisplay_0.TextColor3
        local l_DescriptionDisplay_0 = l_SelectedInfoSection_0.DescriptionDisplay
        local l_OwnedDisplay_0 = l_SelectedInfoSection_0.OwnedDisplay
        local l_Icon_0 = l_SelectedInfoSection_0.IconFrame.Icon
        local l_IconOverlay_0 = l_SelectedInfoSection_0.IconFrame.IconOverlay
        l_NameDisplay_0.Text = "-"
        l_DescriptionDisplay_0.Text = ""
        l_OwnedDisplay_0.Text = "-"
        l_Icon_0.Image = v_u_1:transparent_assetid()
        l_IconOverlay_0.Image = v_u_1:transparent_assetid()
        local l_Anchors_0 = v_u_51.Anchors
        v_u_65:create_list_elements_from_anchors_and_proto({
            l_Anchors_0.Anchor1,
            l_Anchors_0.Anchor2,
            l_Anchors_0.Anchor3,
            l_Anchors_0.Anchor4,
            l_Anchors_0.Anchor5,
            l_Anchors_0.Anchor6,
            l_Anchors_0.Anchor7,
            l_Anchors_0.Anchor8,
            l_Anchors_0.Anchor9,
            l_Anchors_0.Anchor10
        }, v_u_51.ElementProto, v_u_51, function(p66) --[[ Line: 315 ]]
            --[[ Upvalues: (ref 1): v_u_20, (ref 2): p_u_40, (ref 3): v_u_45, (ref 4): v_u_6, (copy 5): l_NameDisplay_0, (copy 6): l_TextColor3_0, (copy 7): l_DescriptionDisplay_0, (ref 8): v_u_56, (copy 9): l_OwnedDisplay_0, (ref 10): v_u_1, (ref 11): v_u_10, (ref 12): v_u_11, (copy 13): l_Icon_0, (copy 14): l_IconOverlay_0, (ref 15): v_u_47 ]]
            return v_u_20.ListElement:new(p_u_40, v_u_45, p66, function(p67, p68) --[[ Line: 316 ]]
                --[[ Upvalues: (ref 1): p_u_40, (ref 2): v_u_6, (ref 3): l_NameDisplay_0, (ref 4): l_TextColor3_0, (ref 5): l_DescriptionDisplay_0, (ref 6): v_u_56, (ref 7): l_OwnedDisplay_0, (ref 8): v_u_1, (ref 9): v_u_10, (ref 10): v_u_11, (ref 11): l_Icon_0, (ref 12): l_IconOverlay_0, (ref 13): v_u_47 ]]
                if p67 ~= nil then
                    if p68 then
                        p_u_40._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
                    end;
                    l_NameDisplay_0.Text = p67:get_name_with_amount()
                    local v69, v70 = p67:get_display_text_color()
                    if v70 then
                        l_NameDisplay_0.TextColor3 = l_TextColor3_0
                    else
                        l_NameDisplay_0.TextColor3 = v69
                    end;
                    l_DescriptionDisplay_0.Text = p67:get_description(v_u_56)
                    local v71 = p67:playerblob_get_display_owned_count(p_u_40._player_blob_manager:get_player_blob())
                    if v71 > 0 then
                        l_OwnedDisplay_0.Text = v_u_1:comma_value(v71)
                    else
                        l_OwnedDisplay_0.Text = "-"
                    end;
                    if p67:get_type() == v_u_10.RewardType.Song then
                        v_u_11:singleton():render_coverimage_for_key(l_Icon_0, l_IconOverlay_0, p67:get_id())
                        if p68 then
                            if v_u_47 == nil then
                                v_u_47 = p_u_40._bgm_manager:begin_preview_songkey()
                            end;
                            p_u_40._bgm_manager:preview_songkey(p67:get_id())
                            return;
                        end;
                    else
                        l_Icon_0.Image = p67:get_image()
                        l_IconOverlay_0.Image = v_u_1:transparent_assetid()
                    end;
                end;
            end);
        end)
        v_u_65:page_update()
        v_u_45:transition_update_visual(0)
        v_u_45:layout()
    end;
    v_u_45.set_header_text = function(p72, p73) --[[ Name: set_header_text ]] --[[ Line: 361 ]]
        --[[ Upvalues: (ref 1): v_u_52 ]]
        v_u_52.Text = p73
        return p72;
    end;
    v_u_45.set_sub_text = function(p74, p75) --[[ Name: set_sub_text ]] --[[ Line: 366 ]]
        --[[ Upvalues: (ref 1): v_u_48 ]]
        v_u_48.Text = p75
        return p74;
    end;
    v_u_45.finish_animation = function(p76) --[[ Name: finish_animation ]] --[[ Line: 371 ]]
        --[[ Upvalues: (copy 1): v_u_46, (copy 2): v_u_55, (copy 3): v_u_65 ]]
        while v_u_46:count() > 0 do
            v_u_55:push_back(v_u_46:pop_front())
        end;
        v_u_65:page_update()
        return p76;
    end;
    v_u_45.select_first_element = function(p77) --[[ Name: select_first_element ]] --[[ Line: 379 ]]
        --[[ Upvalues: (copy 1): v_u_65 ]]
        if v_u_65:get_display_elements():count() > 0 then
            v_u_65:get_display_elements():get(1):select()
        end;
        return p77;
    end;
    local v_u_78 = v_u_13:new()
    v_u_45.get_sfx_cooldown = function(_) --[[ Name: get_sfx_cooldown ]] --[[ Line: 387 ]]
        --[[ Upvalues: (copy 1): v_u_78 ]]
        return v_u_78;
    end;
    local v_u_79 = 0.25
    v_u_45.behaviour_update = function(p80, p81, _) --[[ Name: behaviour_update ]] --[[ Line: 390 ]]
        --[[ Upvalues: (copy 1): p_u_40, (copy 2): v_u_78, (ref 3): v_u_14, (ref 4): v_u_79, (copy 5): v_u_46, (copy 6): v_u_55, (copy 7): v_u_65, (ref 8): v_u_12 ]]
        p80:behaviour_update_base(p81, p_u_40)
        v_u_78:update(p81)
        if p80._current_mode == v_u_14.MODE_OPEN then
            if p80:has_any_pending_reward_desc_infos_to_show() then
                if v_u_79 >= 0.25 then
                    v_u_79 = 0
                    local v82 = v_u_46:pop_front()
                    v_u_55:push_back(v82)
                    v_u_65:page_update()
                    local v83 = nil
                    for _, v84 in v_u_65:get_display_elements():key_itr() do
                        if v84:get_data() == v82 then
                            v83 = v84
                            break;
                        end;
                    end;
                    if v83 == nil then
                        v_u_65:next_page()
                        for _, v85 in v_u_65:get_display_elements():key_itr() do
                            if v85:get_data() == v82 then
                                v83 = v85
                                break;
                            end;
                        end;
                    end;
                    if v83 then
                        v83:start_fade_in_animation()
                    end;
                else
                    v_u_79 = v_u_79 + v_u_12:TimescaleToDeltaTime(p81)
                end;
            end;
            for _, v86 in v_u_65:get_display_elements():key_itr() do
                v86:behaviour_update(p81)
            end;
        end;
    end;
    v_u_45.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 433 ]]
        --[[ Upvalues: (ref 1): v_u_47, (copy 2): p_u_40, (ref 3): p_u_44, (ref 4): v_u_51 ]]
        if v_u_47 then
            p_u_40._bgm_manager:stop_song_preview(v_u_47)
        end;
        if p_u_44 then
            p_u_44()
            p_u_44 = nil
        end;
        v_u_51:Destroy()
    end;
    local v_u_87 = 1
    local v_u_88 = 1
    v_u_45.layout = function(p89) --[[ Name: layout ]] --[[ Line: 446 ]]
        --[[ Upvalues: (copy 1): p_u_41, (ref 2): v_u_88, (ref 3): v_u_51, (copy 4): v_u_65 ]]
        p89:opt_rescale_to_max_nxy(p_u_41, 0.8, 0.8, v_u_88)
        local v90, v91 = p89:opt_update_cframe_params(p_u_41, {
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p89:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v90 == true then
            v_u_51:SetPrimaryPartCFrame(v91)
        end;
        v_u_65:layout()
    end;
    v_u_45.set_alpha = function(_, p92) --[[ Name: set_alpha ]] --[[ Line: 460 ]]
        --[[ Upvalues: (ref 1): v_u_87, (ref 2): v_u_1, (ref 3): v_u_51 ]]
        if v_u_87 ~= p92 then
            v_u_87 = p92
            v_u_1:r_set_alpha(v_u_51, v_u_87)
        end;
    end;
    v_u_45.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 466 ]]
        --[[ Upvalues: (ref 1): v_u_87 ]]
        return v_u_87;
    end;
    v_u_45.set_scale = function(_, p93) --[[ Name: set_scale ]] --[[ Line: 467 ]]
        --[[ Upvalues: (ref 1): v_u_88 ]]
        v_u_88 = p93
    end;
    v_u_45.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 468 ]]
        --[[ Upvalues: (ref 1): v_u_88 ]]
        return v_u_88;
    end;
    v_u_45.get_native_size = function(p94) --[[ Name: get_native_size ]] --[[ Line: 470 ]]
        return p94._native_size;
    end;
    v_u_45.get_size = function(p95) --[[ Name: get_size ]] --[[ Line: 473 ]]
        return p95._size;
    end;
    v_u_45.set_size = function(p96, p97) --[[ Name: set_size ]] --[[ Line: 476 ]]
        --[[ Upvalues: (ref 1): v_u_51 ]]
        p96._size = p97
        v_u_51.PrimaryPart.Size = Vector3.new(p97.X, p97.Y, 0)
    end;
    v_u_45.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 480 ]]
        --[[ Upvalues: (ref 1): v_u_51 ]]
        return v_u_51.PrimaryPart.Position;
    end;
    v_u_45.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 483 ]]
        --[[ Upvalues: (ref 1): v_u_51 ]]
        return v_u_51.PrimaryPart.SurfaceGui;
    end;
    v_u_45.set_showing = function(_, p98) --[[ Name: set_showing ]] --[[ Line: 486 ]]
        --[[ Upvalues: (ref 1): v_u_51, (ref 2): v_u_7 ]]
        if p98 then
            v_u_51.Parent = v_u_7:get_world_ui_folder()
        else
            v_u_51.Parent = nil
        end;
    end;
    v_u_45.get_uichild_parent = function(_) --[[ Name: get_uichild_parent ]] --[[ Line: 493 ]]
        --[[ Upvalues: (ref 1): v_u_51 ]]
        return v_u_51.PrimaryPart;
    end;
    f_cons()
    return v_u_45;
end;
return v_u_20;
