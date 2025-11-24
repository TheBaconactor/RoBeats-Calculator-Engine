-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:43 PM
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
local v_u_8 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_9 = require(game.ReplicatedStorage.Menu.CycleElementBase)
local v_u_10 = require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_11 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_12 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_13 = require(game.ReplicatedStorage.LocalShared.SongPreviewUIButton)
local v_u_14 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
local v_u_15 = require(game.ReplicatedStorage.Shared.CooldownDelay)
local v_u_16 = {
    ["ListElement"] = {}
}
local v_u_17 = 0
v_u_16.new = function(_, p_u_18, p_u_19, p_u_20, p_u_21, p_u_22) --[[ Name: new ]] --[[ Line: 26 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_15, (copy 4): v_u_1, (copy 5): v_u_7, (copy 6): v_u_13, (copy 7): v_u_5, (copy 8): v_u_4, (copy 9): v_u_6, (copy 10): v_u_11, (copy 11): v_u_14, (copy 12): v_u_12, (copy 13): v_u_16, (copy 14): v_u_10, (ref 15): v_u_17, (copy 16): v_u_8 ]]
    local v23 = v_u_3:new(p_u_19, p_u_20)
    local v_u_24 = nil
    local v_u_25 = 1
    local v_u_26 = 1
    local v_u_27 = v_u_2:new()
    local v_u_28 = nil
    local v_u_29 = nil
    local v_u_30 = nil
    local v_u_31 = nil
    local v_u_32 = nil
    local v_u_33 = nil
    local v_u_34 = nil
    local v_u_35 = nil
    local v_u_36 = nil
    local v_u_37 = v_u_15:new()
    v23.get_sfx_cooldown = function(_) --[[ Name: get_sfx_cooldown ]] --[[ Line: 47 ]]
        --[[ Upvalues: (copy 1): v_u_37 ]]
        return v_u_37;
    end;
    v23.cons = function(p_u_38) --[[ Name: cons ]] --[[ Line: 49 ]]
        --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_1, (ref 3): v_u_7, (ref 4): v_u_36, (copy 5): p_u_18, (ref 6): v_u_28, (ref 7): v_u_29, (ref 8): v_u_30, (ref 9): v_u_31, (ref 10): v_u_32, (ref 11): v_u_33, (ref 12): v_u_34, (ref 13): v_u_35, (ref 14): v_u_13, (copy 15): p_u_21, (ref 16): v_u_5, (ref 17): v_u_4, (copy 18): p_u_19, (copy 19): p_u_20, (ref 20): v_u_6 ]]
        v_u_24 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.SongsAcquiredUI:Clone()
        v_u_24.Name = v_u_1:gen_name(v_u_24.Name)
        v_u_24.Parent = v_u_7:get_world_ui_folder()
        p_u_38._native_size = v_u_24.PrimaryPart.Size
        p_u_38._size = p_u_38._native_size
        v_u_36 = p_u_18._bgm_manager:begin_preview_songkey()
        local l_SelectedInfoSection_0 = v_u_24.PrimaryPart.SurfaceGui.Frame.SelectedInfoSection
        v_u_28 = l_SelectedInfoSection_0.IconFrame.Icon
        v_u_29 = l_SelectedInfoSection_0.IconFrame.IconOverlay
        v_u_30 = l_SelectedInfoSection_0.IconFrame.ColorSection
        v_u_31 = l_SelectedInfoSection_0.NameDisplay
        v_u_32 = l_SelectedInfoSection_0.DescriptionDisplay
        v_u_33 = l_SelectedInfoSection_0.OwnedDisplay
        v_u_34 = l_SelectedInfoSection_0.DifficultyDisplay
        v_u_28.Image = v_u_1:transparent_assetid()
        v_u_31.Text = ""
        v_u_32.Text = ""
        v_u_33.Text = ""
        v_u_30.Visible = false
        v_u_35 = p_u_38:add_cycle_element(p_u_18, 1, v_u_13:new(p_u_18, p_u_38, v_u_24.PrimaryPart, v_u_24.PlayPreviewButton))
        v_u_35:set_target_songkey(p_u_21[1])
        p_u_38:add_cycle_element(p_u_18, 1, v_u_5:new(v_u_4:new(p_u_38, v_u_24.PrimaryPart, v_u_24.BackButtonSurface), p_u_19, function() --[[ Line: 80 ]]
            --[[ Upvalues: (ref 1): p_u_20, (copy 2): p_u_38, (ref 3): p_u_18, (ref 4): v_u_6 ]]
            p_u_20:remove_menu(p_u_38)
            p_u_18._sfx_manager:play_sfx(v_u_6.SFX_MENU_CLOSE)
        end))
        p_u_38:setup_list_elements()
        p_u_38:reset_selected_item()
        p_u_38:transition_update_visual(0)
        p_u_38:layout()
    end;
    v23.list_element_pressed = function(_, p39, _, p40) --[[ Name: list_element_pressed ]] --[[ Line: 94 ]]
        --[[ Upvalues: (copy 1): p_u_18, (ref 2): v_u_6, (ref 3): v_u_35, (copy 4): v_u_27, (ref 5): v_u_11, (ref 6): v_u_28, (ref 7): v_u_29, (ref 8): v_u_14, (ref 9): v_u_30, (ref 10): v_u_31, (ref 11): v_u_32, (ref 12): v_u_33, (ref 13): v_u_12, (ref 14): v_u_34 ]]
        p_u_18._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
        v_u_35:set_target_songkey(p40)
        for v41 = 1, v_u_27:count() do
            local v42 = v_u_27:get(v41)
            if v42 == p39 then
                v42:set_highlighted(true)
            else
                v42:set_highlighted(false)
            end;
        end;
        v_u_11:singleton():render_coverimage_for_key(v_u_28, v_u_29, p40)
        v_u_14:render_songkey_colorsection(p40, v_u_30)
        v_u_31.Text = v_u_11:singleton():get_title_for_key(p40)
        v_u_32.Text = v_u_11:singleton():get_description_for_key(p40)
        v_u_33.Text = string.format("%d", v_u_12:get_song_key_owned_count(p_u_18._player_blob_manager:get_player_blob(), p40))
        v_u_34.Text = string.format("%d", v_u_11:singleton():get_difficulty_for_key(p40))
    end;
    v23.setup_list_elements = function(p43) --[[ Name: setup_list_elements ]] --[[ Line: 116 ]]
        --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_2, (copy 3): p_u_21, (ref 4): v_u_16, (copy 5): p_u_18, (ref 6): v_u_4, (copy 7): p_u_19, (copy 8): p_u_22, (copy 9): v_u_27 ]]
        local l_AcquiredItemProto_0 = v_u_24.AcquiredItemProto
        l_AcquiredItemProto_0.Parent = nil
        local v44 = v_u_2:new()
        for v45 = 1, 12 do
            v44:push_back(v_u_24.Anchors:FindFirstChild(string.format("Anchor%d", v45)))
        end;
        for v46 = 1, #p_u_21 do
            if v44:count() < v46 then
                break;
            end;
            local v47 = v44:get(v46)
            local v48 = l_AcquiredItemProto_0:Clone()
            v48.Name = string.format("AcquiredItem(%d)", v46)
            v48.Parent = v_u_24
            v48.Position = v47.Position
            local v49 = v_u_16.ListElement:new(p_u_18, v_u_4:new(p43, v_u_24.PrimaryPart, v48), p_u_19, p43, v46, (v46 - 1) * 0.35 + 0.001, p_u_22)
            v49:set_song_key(p_u_21[v46])
            p43:add_cycle_element(p_u_18, 1, v49)
            v_u_27:push_back(v49)
        end;
    end;
    v23.behaviour_update = function(p50, p51, p52) --[[ Name: behaviour_update ]] --[[ Line: 151 ]]
        --[[ Upvalues: (copy 1): p_u_18, (copy 2): v_u_37, (ref 3): v_u_10, (ref 4): v_u_17, (ref 5): v_u_8, (copy 6): v_u_27 ]]
        p50:behaviour_update_base(p51, p_u_18)
        v_u_37:update(p51)
        if p50._current_mode == v_u_10.MODE_OPEN then
            if v_u_17 > 0 then
                v_u_17 = v_u_17 - v_u_8:TimescaleToDeltaTime(p51)
            end;
            for v53 = 1, v_u_27:count() do
                v_u_27:get(v53):behaviour_update(p51, p52)
            end;
        end;
    end;
    v23.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 164 ]]
        --[[ Upvalues: (copy 1): p_u_18, (ref 2): v_u_36, (ref 3): v_u_24 ]]
        p_u_18._bgm_manager:stop_song_preview(v_u_36)
        v_u_24:Destroy()
    end;
    v23.layout = function(p54) --[[ Name: layout ]] --[[ Line: 169 ]]
        --[[ Upvalues: (copy 1): p_u_19, (ref 2): v_u_26, (ref 3): v_u_24, (copy 4): v_u_27 ]]
        p54:opt_rescale_to_max_nxy(p_u_19, 0.88, 0.8, v_u_26)
        local v55, v56 = p54:opt_update_cframe_params(p_u_19, {
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p54:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v55 == true then
            v_u_24:SetPrimaryPartCFrame(v56)
        end;
        for v57 = 1, v_u_27:count() do
            v_u_27:get(v57):layout()
        end;
    end;
    v23.set_alpha = function(_, p58) --[[ Name: set_alpha ]] --[[ Line: 185 ]]
        --[[ Upvalues: (ref 1): v_u_25, (copy 2): v_u_27, (ref 3): v_u_1, (ref 4): v_u_24 ]]
        if v_u_25 ~= p58 then
            v_u_25 = p58
            for v59 = 1, v_u_27:count() do
                v_u_27:get(v59):set_parent_alpha(v_u_25)
            end;
            v_u_1:r_set_alpha(v_u_24, v_u_25)
        end;
    end;
    v23.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 194 ]]
        --[[ Upvalues: (ref 1): v_u_25 ]]
        return v_u_25;
    end;
    v23.set_scale = function(_, p60) --[[ Name: set_scale ]] --[[ Line: 195 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        v_u_26 = p60
    end;
    v23.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 196 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        return v_u_26;
    end;
    v23.get_native_size = function(p61) --[[ Name: get_native_size ]] --[[ Line: 198 ]]
        return p61._native_size;
    end;
    v23.get_size = function(p62) --[[ Name: get_size ]] --[[ Line: 201 ]]
        return p62._size;
    end;
    v23.set_size = function(p63, p64) --[[ Name: set_size ]] --[[ Line: 204 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        p63._size = p64
        v_u_24.PrimaryPart.Size = Vector3.new(p64.X, p64.Y, 0)
    end;
    v23.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 208 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        return v_u_24.PrimaryPart.Position;
    end;
    v23.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 211 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        return v_u_24.PrimaryPart.SurfaceGui;
    end;
    v23:cons()
    return v23;
end;
v_u_16.ListElement.new = function(_, p_u_65, p_u_66, _, p_u_67, p_u_68, p_u_69, p_u_70) --[[ Name: new ]] --[[ Line: 220 ]]
    --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_11, (copy 3): v_u_14, (copy 4): v_u_8, (copy 5): v_u_6, (copy 6): v_u_1 ]]
    local v71 = v_u_9:new()
    local v_u_72 = false
    local v_u_73 = p_u_66:get_child_part()
    local v_u_74 = nil
    local v_u_75 = nil
    local v_u_76 = nil
    local v_u_77 = nil
    local v_u_78 = nil
    local v_u_79 = nil
    local v_u_80 = -1
    local v_u_81 = nil
    local v_u_82 = 0
    v71.cons = function(p83) --[[ Name: cons ]] --[[ Line: 233 ]]
        --[[ Upvalues: (ref 1): v_u_74, (copy 2): v_u_73, (ref 3): v_u_75, (ref 4): v_u_76, (ref 5): v_u_77, (ref 6): v_u_78, (ref 7): v_u_79, (ref 8): v_u_81 ]]
        v_u_74 = v_u_73.SurfaceGui.Frame.Pane.Icon
        v_u_75 = v_u_73.SurfaceGui.Frame.Pane.IconOverlay
        v_u_76 = v_u_73.SurfaceGui.Frame.Pane.Icon.ColorSection.PrimaryColorIcon
        v_u_77 = v_u_73.SurfaceGui.Frame.Pane.Icon.ColorSection.SecondaryColorIcon
        v_u_78 = v_u_73.SurfaceGui.Frame.Pane.NameDisplay
        v_u_79 = v_u_73.SurfaceGui.Frame.Pane
        v_u_81 = v_u_73.SurfaceGui.Frame.NewIcon
        p83:set_alpha(0)
        p83:set_selected(nil, false)
        p83:layout()
    end;
    v71.set_song_key = function(_, p84) --[[ Name: set_song_key ]] --[[ Line: 248 ]]
        --[[ Upvalues: (ref 1): v_u_80, (ref 2): v_u_11, (ref 3): v_u_74, (ref 4): v_u_75, (ref 5): v_u_14, (ref 6): v_u_76, (ref 7): v_u_77, (ref 8): v_u_78, (ref 9): v_u_81, (copy 10): p_u_70 ]]
        v_u_80 = p84
        v_u_11:singleton():render_coverimage_for_key(v_u_74, v_u_75, v_u_80)
        v_u_14:render_songkey_color_icons(v_u_80, v_u_76, v_u_77)
        v_u_78.Text = v_u_11:singleton():get_title_for_key(v_u_80)
        v_u_81.Visible = p_u_70:contains(p84)
    end;
    v71.behaviour_update = function(p85, p86, _) --[[ Name: behaviour_update ]] --[[ Line: 256 ]]
        --[[ Upvalues: (ref 1): p_u_69, (ref 2): v_u_8, (copy 3): p_u_67, (copy 4): p_u_68, (ref 5): v_u_80, (copy 6): p_u_70, (copy 7): p_u_65, (ref 8): v_u_6, (ref 9): v_u_11, (ref 10): v_u_82, (ref 11): v_u_1, (copy 12): p_u_66, (ref 13): v_u_72 ]]
        if p_u_69 > 0 then
            p_u_69 = p_u_69 - v_u_8:TimescaleToDeltaTime(p86)
            if p_u_69 <= 0 then
                p_u_67:list_element_pressed(p85, p_u_68, v_u_80)
                if p_u_70:contains(v_u_80) then
                    if p_u_67:get_sfx_cooldown():is_on_cooldown(0) ~= true then
                        p_u_65._sfx_manager:play_sfx(v_u_6.SFX_FEVERCHEER_1)
                        p_u_67:get_sfx_cooldown():add_cooldown_to_id(0, 0.75)
                        return;
                    end;
                else
                    if v_u_11:singleton():key_get_audiomod(v_u_80) ~= v_u_11.MOD_HARDMODE then
                        p_u_65._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
                        return;
                    end;
                    if p_u_67:get_sfx_cooldown():is_on_cooldown(1) ~= true then
                        p_u_65._sfx_manager:play_sfx(v_u_6.SFX_ACQUIRE)
                        p_u_67:get_sfx_cooldown():add_cooldown_to_id(1, 0.25)
                        return;
                    end;
                end;
            end;
        else
            if v_u_82 < 1 then
                v_u_82 = v_u_1:clamp(v_u_82 + v_u_8:SecondsToTick(0.25) * p86, 0, 1)
                p_u_66:set_scale(v_u_8:BezierYForT(0, 1.5, 0, 1, 0.5, 1, 1, 1, v_u_82))
                p85:set_alpha(v_u_8:BezierYForT(0, 0, 0.5, 0, 1, 0.5, 1, 1, v_u_82))
                return;
            end;
            p_u_66:set_scale(v_u_8:Expt(p_u_66:get_scale(), v_u_72 == true and 1.1 or 1, v_u_8:NormalizedDefaultExptValueInSeconds(0.5), p86))
        end;
    end;
    v71.layout = function(p87) --[[ Name: layout ]] --[[ Line: 297 ]]
        --[[ Upvalues: (copy 1): p_u_66, (copy 2): v_u_73 ]]
        p_u_66:layout()
        p87._native_size = v_u_73.Size
        p87._size = p87._native_size
    end;
    local v_u_88 = true
    v71.set_enabled = function(p89, p90) --[[ Name: set_enabled ]] --[[ Line: 304 ]]
        --[[ Upvalues: (ref 1): v_u_72, (ref 2): v_u_88 ]]
        if p90 == false then
            v_u_72 = false
        else
            p89:set_alpha(1)
        end;
        v_u_88 = p90
        return p89;
    end;
    v71.set_visible = function(p91, p92) --[[ Name: set_visible ]] --[[ Line: 314 ]]
        --[[ Upvalues: (copy 1): v_u_73 ]]
        if p92 == true then
            v_u_73.SurfaceGui.Enabled = true
        else
            v_u_73.SurfaceGui.Enabled = false
        end;
        p91:set_enabled(p92)
        return p91;
    end;
    v71.is_selectable = function(_) --[[ Name: is_selectable ]] --[[ Line: 324 ]]
        --[[ Upvalues: (ref 1): v_u_88, (ref 2): p_u_69, (ref 3): v_u_82 ]]
        local v93 = v_u_88
        if v93 then
            if p_u_69 <= 0 then
                v93 = v_u_82 >= 0
            else
                v93 = false
            end;
        end;
        return v93;
    end;
    v71.get_selected = function(_) --[[ Name: get_selected ]] --[[ Line: 325 ]]
        --[[ Upvalues: (ref 1): v_u_72 ]]
        return v_u_72;
    end;
    v71.trigger_element = function(p94, _) --[[ Name: trigger_element ]] --[[ Line: 326 ]]
        --[[ Upvalues: (copy 1): p_u_66, (copy 2): p_u_67, (copy 3): p_u_68, (ref 4): v_u_80 ]]
        p_u_66:set_scale(1.5)
        p_u_67:list_element_pressed(p94, p_u_68, v_u_80)
    end;
    v71.set_highlighted = function(_, _) end;
    v71.set_selected = function(_, _, p95) --[[ Name: set_selected ]] --[[ Line: 335 ]]
        --[[ Upvalues: (ref 1): v_u_72, (copy 2): v_u_73, (copy 3): p_u_66 ]]
        v_u_72 = p95
        if v_u_72 then
            v_u_73.SurfaceGui.ZOffset = 1500 + p_u_66:get_child_id()
        else
            v_u_73.SurfaceGui.ZOffset = 1000 + p_u_66:get_child_id()
        end;
    end;
    v71.get_native_size = function(p96) --[[ Name: get_native_size ]] --[[ Line: 345 ]]
        return p96._native_size;
    end;
    v71.get_size = function(p97) --[[ Name: get_size ]] --[[ Line: 346 ]]
        return p97._size;
    end;
    v71.set_size = function(p98, p99) --[[ Name: set_size ]] --[[ Line: 347 ]]
        --[[ Upvalues: (copy 1): v_u_73 ]]
        p98._size = p99
        v_u_73.Size = Vector3.new(p99.X, p99.Y, 0)
    end;
    v71.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 351 ]]
        --[[ Upvalues: (copy 1): v_u_73 ]]
        return v_u_73.Position;
    end;
    local v_u_100 = 1
    v71.set_parent_alpha = function(_, p101) --[[ Name: set_parent_alpha ]] --[[ Line: 354 ]]
        --[[ Upvalues: (ref 1): v_u_100 ]]
        v_u_100 = p101
    end;
    local v_u_102 = 1
    v71.set_alpha = function(_, p103) --[[ Name: set_alpha ]] --[[ Line: 359 ]]
        --[[ Upvalues: (ref 1): v_u_102, (ref 2): v_u_1, (copy 3): v_u_73, (ref 4): v_u_100 ]]
        if p103 ~= v_u_102 then
            v_u_102 = p103
            v_u_1:list_set_alpha_name(v_u_1:get_list_of_children_of_classname(v_u_73, "TextLabel"), {
                ["TextAlpha"] = v_u_102
            })
            v_u_1:list_set_alpha_name(v_u_1:get_list_of_children_of_classname(v_u_73, "ImageLabel"), {
                ["ImageAlpha"] = v_u_102
            })
            v_u_1:r_set_alpha(v_u_73, v_u_100)
        end;
    end;
    v71:cons()
    return v71;
end;
return v_u_16;
