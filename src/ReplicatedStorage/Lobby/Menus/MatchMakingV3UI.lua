-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:39 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_4 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_6 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_7 = require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Menu.MenuSystem)
require(game.ReplicatedStorage.Local.GameJoinProtocol)
local v_u_8 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_9 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_10 = require(game.ReplicatedStorage.Lobby.UI.ChatUISection)
local v_u_11 = require(game.ReplicatedStorage.LocalShared.BGMManager)
local v_u_12 = require(game.ReplicatedStorage.Shared.MatchMakingSettings)
local v_u_13 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_14 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_15 = require(game.ReplicatedStorage.LocalShared.IntersectZoneManager)
local v_u_16 = require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_17 = require(game.ReplicatedStorage.Lobby.UI.UIToggleGroup)
local v_u_18 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_19 = require(game.ReplicatedStorage.Lobby.Menus.GameStartV2UI)
local v_u_20 = require(game.ReplicatedStorage.Lobby.Menus.VotePickV2UI)
local v_u_21 = require(game.ReplicatedStorage.Lobby.UI.MatchMakingV3PlayersSection)
local v_u_22 = require(game.ReplicatedStorage.Lobby.UI.MatchMakingV3GameStageSelectSection)
local v_u_23 = {
    ["Type"] = "MatchMakingV3UI"
}
local v_u_24 = v_u_12:new()
v_u_23.initial_settings_sync_update = function(_, p25) --[[ Name: initial_settings_sync_update ]] --[[ Line: 37 ]]
    --[[ Upvalues: (copy 1): v_u_12, (copy 2): v_u_24, (copy 3): v_u_18 ]]
    v_u_12:set_auto_equip_best_loadout(v_u_24, p25._player_settings_manager:get_key(v_u_18.Key.AutoEquipBestLoadout))
    v_u_12:set_selected_game_stage(v_u_24, p25._player_settings_manager:get_key(v_u_18.Key.SelectedGameStage))
end;
v_u_23.set_auto_equip_best_loadout = function(_, p26) --[[ Name: set_auto_equip_best_loadout ]] --[[ Line: 47 ]]
    --[[ Upvalues: (copy 1): v_u_12, (copy 2): v_u_24 ]]
    v_u_12:set_auto_equip_best_loadout(v_u_24, p26)
end;
v_u_23.get_local_matchmaking_settings = function(_) --[[ Name: get_local_matchmaking_settings ]] --[[ Line: 48 ]]
    --[[ Upvalues: (copy 1): v_u_24 ]]
    return v_u_24;
end;
v_u_23.new = function(_, p_u_27, p_u_28, p_u_29, p_u_30, p_u_31) --[[ Name: new ]] --[[ Line: 50 ]]
    --[[ Upvalues: (copy 1): v_u_13, (copy 2): v_u_12, (copy 3): v_u_24, (copy 4): v_u_16, (copy 5): v_u_7, (copy 6): v_u_4, (copy 7): v_u_23, (copy 8): v_u_3, (copy 9): v_u_1, (copy 10): v_u_2, (copy 11): v_u_15, (copy 12): v_u_11, (copy 13): v_u_21, (copy 14): v_u_10, (copy 15): v_u_6, (copy 16): v_u_5, (copy 17): v_u_9, (copy 18): v_u_17, (copy 19): v_u_22, (copy 20): v_u_8, (copy 21): v_u_20, (copy 22): v_u_19, (copy 23): v_u_14 ]]
    if v_u_13:singleton():contains_key(p_u_30) and typeof(p_u_27.songkey_opt_set_artist_event_info) == "function" then
        p_u_27:songkey_opt_set_artist_event_info(p_u_30)
    end;
    v_u_12:set_match_mode(v_u_24, v_u_16:get_selected_mode())
    local v_u_32
    if v_u_13:singleton():contains_key(p_u_30) == false then
        v_u_7:warnf("MatchMakingV3UI does not contain songkey(%d)", p_u_30)
        p_u_30 = -1
        v_u_32 = true
    else
        v_u_32 = false
    end;
    if v_u_13:singleton():contains_key(p_u_30) then
        p_u_27._game_join:set_last_loaded_songkey(p_u_30)
    end;
    local v_u_33 = v_u_4:new(p_u_28, p_u_29)
    v_u_33.Type = v_u_23.Type
    v_u_33.get_requested_song_key = function(_) --[[ Name: get_requested_song_key ]] --[[ Line: 71 ]]
        --[[ Upvalues: (ref 1): p_u_30 ]]
        return p_u_30;
    end;
    local v_u_34 = nil
    local v_u_35 = 1
    local v_u_36 = 1
    local l__game_join_protocol_0 = p_u_27._game_join_protocol
    local v_u_37 = nil
    local v_u_38 = v_u_3:new()
    local v_u_39 = nil
    local v_u_40 = nil
    local v_u_41 = nil
    local v_u_42 = nil
    local v_u_43 = nil
    local v_u_44 = nil
    local v_u_45 = nil
    local v_u_46 = nil
    local function f_cons() --[[ Name: cons ]] --[[ Line: 93 ]]
        --[[ Upvalues: (ref 1): v_u_34, (ref 2): v_u_1, (copy 3): v_u_33, (ref 4): v_u_32, (copy 5): p_u_31, (copy 6): l__game_join_protocol_0, (ref 7): p_u_30, (ref 8): v_u_24, (ref 9): v_u_46, (copy 10): p_u_27 ]]
        v_u_34 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.MatchMakingV3UI:Clone()
        v_u_34.Name = v_u_1:gen_name(v_u_34.Name)
        v_u_33:set_showing(true)
        v_u_33._native_size = v_u_34.PrimaryPart.Size
        v_u_33._size = v_u_33._native_size
        if v_u_32 ~= true then
            if p_u_31 == nil then
                l__game_join_protocol_0:mmv3_enqueue_player(p_u_30, v_u_24)
            else
                l__game_join_protocol_0:mmv3_join_target_player(p_u_30, p_u_31, v_u_24)
            end;
        end;
        v_u_46 = p_u_27._bgm_manager:begin_preview_songkey(p_u_30)
        v_u_33:create_ui()
        v_u_33:reset_selected_item()
        v_u_33:transition_update_visual(0)
        v_u_33:layout()
    end;
    v_u_33.handles_bgm = function(_) --[[ Name: handles_bgm ]] --[[ Line: 116 ]]
        return true;
    end;
    local v_u_47 = v_u_2:new():add_set_from_table_list({ v_u_15.ZoneName.Club })
    v_u_33.on_pushed_to_stack_top = function(_) --[[ Name: on_pushed_to_stack_top ]] --[[ Line: 121 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_27, (copy 3): v_u_47, (ref 4): v_u_15, (ref 5): v_u_11 ]]
        local _, v48 = v_u_1:get_local_character_humanoid_rootpart()
        if not (v48 and p_u_27._intersect_zone_manager:get_intersecting_zones_for_point(v48.Position, v_u_47):contains(v_u_15.ZoneName.Club)) == true then
            p_u_27._bgm_manager:play_bgm(v_u_11.BGM_MATCHMAKING)
        end;
    end;
    v_u_33.create_ui = function(p_u_49) --[[ Name: create_ui ]] --[[ Line: 135 ]]
        --[[ Upvalues: (ref 1): v_u_39, (ref 2): v_u_21, (copy 3): p_u_27, (copy 4): p_u_28, (copy 5): p_u_29, (ref 6): v_u_34, (ref 7): v_u_41, (ref 8): v_u_10, (ref 9): v_u_6, (ref 10): v_u_5, (ref 11): v_u_45, (copy 12): l__game_join_protocol_0, (ref 13): v_u_7, (ref 14): v_u_9, (ref 15): v_u_24, (ref 16): v_u_1, (ref 17): v_u_37, (copy 18): v_u_38, (ref 19): v_u_17, (ref 20): v_u_3, (ref 21): v_u_12, (ref 22): v_u_42, (ref 23): v_u_16, (ref 24): v_u_43, (ref 25): v_u_44, (ref 26): v_u_40, (ref 27): v_u_22 ]]
        v_u_39 = v_u_21:new(p_u_27, p_u_28, p_u_29, v_u_34, p_u_49)
        v_u_41 = v_u_10:new(p_u_27, p_u_28, p_u_49, v_u_34.MainSurface.SurfaceGui.Frame.ChatSection.ChatTextFrameOutline.ChatTextFrame, v_u_34.MainSurface.SurfaceGui.Frame.ChatSection.ChatBarFrame)
        local v_u_50 = nil
        v_u_50 = p_u_49:add_cycle_element(p_u_27, 1, v_u_6:new(v_u_5:new(p_u_49, v_u_34.PrimaryPart, v_u_34.BackButtonSurface), p_u_28, function() --[[ Line: 149 ]]
            --[[ Upvalues: (ref 1): v_u_50, (copy 2): p_u_49 ]]
            v_u_50:set_visible(false)
            p_u_49:back_action()
        end))
        v_u_45 = p_u_49:add_cycle_element(p_u_27, 1, v_u_6:new(v_u_5:new(p_u_49, v_u_34.PrimaryPart, v_u_34.ReadyButtonSurface), p_u_28, function() --[[ Line: 158 ]]
            --[[ Upvalues: (ref 1): l__game_join_protocol_0, (ref 2): v_u_7, (ref 3): p_u_27, (ref 4): v_u_9, (ref 5): v_u_24 ]]
            if l__game_join_protocol_0:mmv3_local_is_ready() == true then
                v_u_7:warnf("MatchMakingV3UI ready button press local_is_ready is true")
            else
                p_u_27._sfx_manager:play_sfx(v_u_9.SFX_MENU_OPEN_LONG)
                l__game_join_protocol_0:mmv3_fire_local_ready(v_u_24)
            end;
        end):set_passive_anim())
        local v_u_51 = v_u_1:get_list_of_children_of_classname(v_u_34.ReadyButtonSurface, "ImageLabel")
        v_u_1:get_list_of_children_of_classname(v_u_34.ReadyButtonSurface, "TextLabel")
        local function f_set_ready_button_alpha(p52) --[[ Name: set_ready_button_alpha ]] --[[ Line: 167 ]]
            --[[ Upvalues: (copy 1): v_u_51, (ref 2): v_u_1 ]]
            for v53 = 1, v_u_51:count() do
                local v54 = v_u_51:get(v53)
                v54.ImageTransparency = v_u_1:tra(p52)
                v54.Name = v_u_1:r_set_alpha_generate_name({
                    ["ImageAlpha"] = p52
                }, v54)
            end;
        end;
        v_u_45:set_enabled_anim_updatefn(function(_, p55) --[[ Line: 178 ]]
            --[[ Upvalues: (ref 1): v_u_45, (copy 2): f_set_ready_button_alpha ]]
            v_u_45:set_scale(p55 + 0.15)
            f_set_ready_button_alpha(p55)
        end):set_enabled(false, true)
        v_u_37 = v_u_5:new(p_u_49, v_u_34.PrimaryPart, v_u_34.SettingsPanel.PrimaryPart)
        v_u_38:push_back(v_u_17:new(v_u_3:new():push_back_table_list({ v_u_34.SettingsPanel.AutoEquipBestLoadout.True, v_u_34.SettingsPanel.AutoEquipBestLoadout.False }), v_u_3:new():push_back_table_list({ true, false }), function(p56) --[[ Line: 189 ]]
            --[[ Upvalues: (ref 1): p_u_27, (ref 2): v_u_9, (ref 3): v_u_12, (ref 4): v_u_24, (copy 5): p_u_49 ]]
            p_u_27._sfx_manager:play_sfx(v_u_9.SFX_BUTTONPRESS)
            v_u_12:set_auto_equip_best_loadout(v_u_24, p56)
            p_u_49:push_matchmaking_settings()
        end, function() --[[ Line: 194 ]]
            --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_24 ]]
            return v_u_12:get_auto_equip_best_loadout(v_u_24);
        end, p_u_49, v_u_34.PrimaryPart, p_u_27, p_u_28))
        v_u_42 = p_u_49:add_cycle_element(p_u_27, 1, v_u_6:new(v_u_5:new(v_u_37, v_u_34.SettingsPanel.PrimaryPart, v_u_34.SettingsPanel.MatchModeButton), p_u_28, function() --[[ Line: 203 ]]
            --[[ Upvalues: (ref 1): p_u_27, (ref 2): v_u_9, (ref 3): v_u_12, (ref 4): v_u_24, (ref 5): v_u_16, (copy 6): p_u_49 ]]
            p_u_27._sfx_manager:play_sfx(v_u_9.SFX_BUTTONPRESS)
            local v57
            if v_u_12:get_match_mode(v_u_24) == v_u_16.Compete then
                v57 = v_u_16.Casual
            else
                v57 = v_u_16.Compete
            end;
            v_u_16:set_selected_mode(v57)
            v_u_12:set_match_mode(v_u_24, v57)
            p_u_49:push_matchmaking_settings()
        end))
        v_u_43 = v_u_3:new():push_back_table_list({ v_u_42:get_part().SurfaceGui.Frame.ImageFront, v_u_42:get_part().SurfaceGui.Frame.ImageShadow })
        v_u_44 = v_u_37:get_child_part().SurfaceGui.Frame.ModeInfoDisplay
        v_u_40 = v_u_22:new(p_u_27, p_u_28, p_u_29, v_u_34, p_u_49)
        p_u_49:visual_update_matchmaking_settings()
    end;
    v_u_33.push_matchmaking_settings = function(p58) --[[ Name: push_matchmaking_settings ]] --[[ Line: 226 ]]
        --[[ Upvalues: (copy 1): l__game_join_protocol_0, (ref 2): v_u_24 ]]
        l__game_join_protocol_0:update_time()
        l__game_join_protocol_0:mmv3_local_update_settings(v_u_24)
        p58:visual_update_matchmaking_settings()
    end;
    v_u_33.visual_update_matchmaking_settings = function(_) --[[ Name: visual_update_matchmaking_settings ]] --[[ Line: 232 ]]
        --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_24, (ref 3): v_u_43, (ref 4): v_u_16, (ref 5): v_u_44 ]]
        local v59 = v_u_12:get_match_mode(v_u_24)
        for _, v60 in v_u_43:key_itr() do
            v60.Image = v_u_16:get_icon_for_mode(v59)
        end;
        v_u_44.Text = v_u_16:get_description_for_mode(v59)
    end;
    v_u_33.back_action = function(p_u_61) --[[ Name: back_action ]] --[[ Line: 238 ]]
        --[[ Upvalues: (copy 1): p_u_27, (ref 2): v_u_9, (copy 3): l__game_join_protocol_0, (copy 4): p_u_29 ]]
        p_u_27._sfx_manager:play_sfx(v_u_9.SFX_MENU_CLOSE)
        l__game_join_protocol_0:mmv3_player_leave(function() --[[ Line: 240 ]]
            --[[ Upvalues: (ref 1): p_u_29, (copy 2): p_u_61 ]]
            if p_u_29:contains_menu(p_u_61) then
                p_u_29:remove_menu(p_u_61)
            end;
        end)
    end;
    v_u_33.exit_with_error = function(p62, p63) --[[ Name: exit_with_error ]] --[[ Line: 247 ]]
        --[[ Upvalues: (copy 1): p_u_29, (ref 2): v_u_8, (copy 3): p_u_27, (copy 4): p_u_28 ]]
        p_u_29:push_menu(v_u_8:new(p_u_27, p_u_28, p_u_29):set_text("Could not join Match!", p63))
        p_u_29:remove_menu(p62)
    end;
    v_u_33.behaviour_update = function(p64, p65, p66) --[[ Name: behaviour_update ]] --[[ Line: 255 ]]
        --[[ Upvalues: (copy 1): p_u_27, (ref 2): v_u_39, (ref 3): v_u_41, (ref 4): v_u_32, (copy 5): l__game_join_protocol_0, (ref 6): v_u_45 ]]
        p64:behaviour_update_base(p65, p66)
        p_u_27._game_join_protocol:update(p65)
        v_u_39:behaviour_update(p65, p66)
        v_u_41:behaviour_update(p65)
        if v_u_32 == true then
            p64:exit_with_error("Invalid song selected")
            return;
        else
            local v67, v68 = l__game_join_protocol_0:getc_server_join_target_player_error()
            if v67 == true then
                p64:exit_with_error(v68)
                return;
            else
                local v69, v70 = l__game_join_protocol_0:getc_server_client_enqueue_error()
                if v69 then
                    p64:exit_with_error(v70)
                end;
                if l__game_join_protocol_0:has_been_updated() then
                    if l__game_join_protocol_0:mmv3_local_is_ready() then
                        v_u_45:set_enabled(false)
                    else
                        v_u_45:set_enabled(true)
                    end;
                end;
                if l__game_join_protocol_0:notify_client_do_preload() then
                    p64:push_gamestart_ui()
                elseif l__game_join_protocol_0:notify_client_do_votepick() then
                    p64:push_votesong_ui()
                end;
            end;
        end;
    end;
    v_u_33.push_votesong_ui = function(_) --[[ Name: push_votesong_ui ]] --[[ Line: 295 ]]
        --[[ Upvalues: (copy 1): p_u_29, (ref 2): v_u_20, (copy 3): p_u_27, (copy 4): p_u_28 ]]
        p_u_29:remove_all_menus()
        p_u_29:push_menu(v_u_20:new(p_u_27, p_u_28, p_u_29))
    end;
    v_u_33.push_gamestart_ui = function(_) --[[ Name: push_gamestart_ui ]] --[[ Line: 300 ]]
        --[[ Upvalues: (copy 1): p_u_29, (ref 2): v_u_19, (copy 3): p_u_27, (copy 4): p_u_28 ]]
        p_u_29:remove_all_menus()
        p_u_29:push_menu(v_u_19:new(p_u_27, p_u_28, p_u_29, p_u_27._game_join_protocol))
    end;
    v_u_33.exit_to_leavepenalty_singleplayer_match = function(p71) --[[ Name: exit_to_leavepenalty_singleplayer_match ]] --[[ Line: 305 ]]
        --[[ Upvalues: (ref 1): v_u_7, (copy 2): p_u_29 ]]
        v_u_7:warnf("MatchMakingV3UI:exit_to_leavepenalty_singleplayer_match() not implemented")
        p_u_29:remove_menu(p71)
    end;
    v_u_33.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 310 ]]
        --[[ Upvalues: (copy 1): p_u_27, (ref 2): v_u_46, (ref 3): v_u_41, (ref 4): v_u_34 ]]
        p_u_27._bgm_manager:stop_song_preview(v_u_46)
        v_u_41:cleanup()
        v_u_34:Destroy()
    end;
    v_u_33.layout = function(p72) --[[ Name: layout ]] --[[ Line: 316 ]]
        --[[ Upvalues: (copy 1): p_u_28, (ref 2): v_u_36, (ref 3): v_u_34, (ref 4): v_u_37, (ref 5): v_u_39, (ref 6): v_u_40 ]]
        p_u_28:uiobj_rescale_to_max_nxy(p72, 0.725, 0.875, v_u_36)
        v_u_34:SetPrimaryPartCFrame(p_u_28:get_cframe({
            ["PositionNXY"] = Vector2.new(0.5, 0.475),
            ["OffsetXYZ"] = p72:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        }))
        v_u_37:layout()
        v_u_39:layout()
        v_u_40:layout()
    end;
    v_u_33.visual_update = function(p73, p74, p75) --[[ Name: visual_update ]] --[[ Line: 328 ]]
        p73:visual_update_base(p74, p75)
    end;
    v_u_33.set_alpha = function(_, p76) --[[ Name: set_alpha ]] --[[ Line: 332 ]]
        --[[ Upvalues: (ref 1): v_u_35, (ref 2): v_u_1, (ref 3): v_u_34 ]]
        if v_u_35 ~= p76 then
            v_u_35 = p76
            v_u_1:r_set_alpha(v_u_34, v_u_35)
        end;
    end;
    v_u_33.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 338 ]]
        --[[ Upvalues: (ref 1): v_u_35 ]]
        return v_u_35;
    end;
    v_u_33.set_scale = function(_, p77) --[[ Name: set_scale ]] --[[ Line: 339 ]]
        --[[ Upvalues: (ref 1): v_u_36 ]]
        v_u_36 = p77
    end;
    v_u_33.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 340 ]]
        --[[ Upvalues: (ref 1): v_u_36 ]]
        return v_u_36;
    end;
    v_u_33.get_native_size = function(p78) --[[ Name: get_native_size ]] --[[ Line: 342 ]]
        return p78._native_size;
    end;
    v_u_33.get_size = function(p79) --[[ Name: get_size ]] --[[ Line: 345 ]]
        return p79._size;
    end;
    v_u_33.set_size = function(p80, p81) --[[ Name: set_size ]] --[[ Line: 348 ]]
        --[[ Upvalues: (ref 1): v_u_34 ]]
        p80._size = p81
        v_u_34.PrimaryPart.Size = Vector3.new(p81.X, p81.Y, 0)
    end;
    v_u_33.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 352 ]]
        --[[ Upvalues: (ref 1): v_u_34 ]]
        return v_u_34.PrimaryPart.Position;
    end;
    v_u_33.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 355 ]]
        --[[ Upvalues: (ref 1): v_u_34 ]]
        return v_u_34.PrimaryPart.SurfaceGui;
    end;
    v_u_33.set_showing = function(_, p82) --[[ Name: set_showing ]] --[[ Line: 358 ]]
        --[[ Upvalues: (ref 1): v_u_34, (ref 2): v_u_14 ]]
        if p82 then
            v_u_34.Parent = v_u_14:get_world_ui_folder()
        else
            v_u_34.Parent = nil
        end;
    end;
    f_cons()
    return v_u_33;
end;
return v_u_23;
