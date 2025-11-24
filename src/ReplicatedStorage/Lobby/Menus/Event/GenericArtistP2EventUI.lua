-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:48 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_7 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_8 = require(game.ReplicatedStorage.Shared.ListAdapter)
local v_u_9 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_10 = require(game.ReplicatedStorage.Lobby.UI.SongDisplayElement)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_11 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
local v_u_12 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_13 = require(game.ReplicatedStorage.Lobby.UI.ScrollingElementDisplay)
local v_u_14 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfoData.GenericArtistP2EventInfo)
local v15 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_16 = nil
local v_u_17 = nil
local v_u_18 = nil
v15:require_client(function() --[[ Line: 27 ]]
    --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_17, (ref 3): v_u_18 ]]
    v_u_16 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_17 = require(game.ReplicatedStorage.Lobby.Menus.MatchMakingV3UI)
    v_u_18 = require(game.ReplicatedStorage.Lobby.UI.MatchMakingV3GameStageSelectSection)
end)
local v19 = {}
local v_u_20 = 1
local v_u_21 = v2:new({
    {
        ["Name"] = "01 - life death & everything between",
        ["AssetId"] = "rbxassetid://13013884338"
    },
    {
        ["Name"] = "02 - simple",
        ["AssetId"] = "rbxassetid://13013882148"
    },
    {
        ["Name"] = "03 - loner",
        ["AssetId"] = "rbxassetid://13013882483"
    },
    {
        ["Name"] = "04 - nervous",
        ["AssetId"] = "rbxassetid://13013882928"
    },
    {
        ["Name"] = "05 - backseat driving",
        ["AssetId"] = "rbxassetid://13013883624"
    },
    {
        ["Name"] = "06 - coffee shop",
        ["AssetId"] = "rbxassetid://13013884692"
    },
    {
        ["Name"] = "07 - don\'t wanna be your friend",
        ["AssetId"] = "rbxassetid://13013881755"
    },
    {
        ["Name"] = "08 - monsters",
        ["AssetId"] = "rbxassetid://13013885109"
    },
    {
        ["Name"] = "09 - hi",
        ["AssetId"] = "rbxassetid://13013881896"
    },
    {
        ["Name"] = "10 - feeling like dancing",
        ["AssetId"] = "rbxassetid://13013881355"
    },
    {
        ["Name"] = "11 - falling in love",
        ["AssetId"] = "rbxassetid://13013880995"
    },
    {
        ["Name"] = "12 - flowers",
        ["AssetId"] = "rbxassetid://13013879305"
    },
    {
        ["Name"] = "13 - superglue",
        ["AssetId"] = "rbxassetid://13013884042"
    }
})
local v_u_22 = 0
v19.new = function(_, p_u_23, p_u_24, p_u_25) --[[ Name: new ]] --[[ Line: 94 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_7, (copy 3): v_u_5, (copy 4): v_u_4, (copy 5): v_u_6, (copy 6): v_u_14, (copy 7): v_u_9, (copy 8): v_u_10, (copy 9): v_u_8, (ref 10): v_u_22, (copy 11): v_u_11, (copy 12): v_u_12, (ref 13): v_u_18, (ref 14): v_u_17, (copy 15): v_u_13, (copy 16): v_u_21, (ref 17): v_u_20, (copy 18): v_u_1 ]]
    local v_u_26 = v_u_3:new(p_u_24, p_u_25)
    local v_u_27 = nil
    local v_u_28 = nil
    local v_u_29 = nil
    local v_u_30 = nil
    local v_u_31 = true
    local function f_cons() --[[ Name: cons ]] --[[ Line: 105 ]]
        --[[ Upvalues: (ref 1): v_u_27, (copy 2): v_u_26, (ref 3): v_u_29, (copy 4): p_u_23, (ref 5): v_u_7, (ref 6): v_u_5, (ref 7): v_u_4, (copy 8): p_u_24, (ref 9): v_u_6, (copy 10): p_u_25, (ref 11): v_u_28, (ref 12): v_u_14, (ref 13): v_u_9, (ref 14): v_u_10, (ref 15): v_u_8, (ref 16): v_u_22, (ref 17): v_u_11, (ref 18): v_u_12, (ref 19): v_u_18, (ref 20): v_u_17, (ref 21): v_u_30, (ref 22): v_u_13, (ref 23): v_u_21, (ref 24): v_u_20, (ref 25): v_u_31 ]]
        v_u_27 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.Event.GenericArtistP2EventUI:Clone()
        v_u_26:set_showing(true)
        v_u_29 = p_u_23._bgm_manager:begin_preview_songkey()
        v_u_26._native_size = v_u_27.PrimaryPart.Size
        v_u_26._size = v_u_26._native_size
        p_u_23:set_character_random_position_around_anchors_fn(function() --[[ Line: 114 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            return v_u_7:get_lobby_anchors().GenericArtistP2Event.StandAnchor, v_u_7:get_lobby_anchors().GenericArtistP2Event.LookAnchor;
        end)
        p_u_23:transition_local_camera_to_anchors_fn(function() --[[ Line: 118 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            return v_u_7:get_lobby_anchors().GenericArtistP2Event.CameraAnchor, v_u_7:get_lobby_anchors().GenericArtistP2Event.LookAnchor;
        end)
        v_u_26:add_cycle_element(p_u_23, 1, v_u_5:new(v_u_4:new(v_u_26, v_u_27.PrimaryPart, v_u_27.BackButtonSurface), p_u_24, function() --[[ Line: 126 ]]
            --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_6, (ref 3): p_u_25, (ref 4): v_u_26 ]]
            p_u_23._sfx_manager:play_sfx(v_u_6.SFX_MENU_CLOSE)
            p_u_25:remove_menu(v_u_26)
        end))
        local l_LoadedSection_0 = v_u_27.MainSurface.SurfaceGui.Frame.LoadedSection
        local l_SongPageDisplay_0 = l_LoadedSection_0.SongPageDisplay
        local v_u_32 = v_u_26:add_cycle_element(p_u_23, 1, v_u_5:new(v_u_4:new(v_u_26, v_u_27.PrimaryPart, v_u_27.ArrowLeft), p_u_24, function() --[[ Line: 157 ]]
            --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_6, (ref 3): v_u_28 ]]
            p_u_23._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            v_u_28:prev_page()
        end))
        local v_u_33 = v_u_26:add_cycle_element(p_u_23, 1, v_u_5:new(v_u_4:new(v_u_26, v_u_27.PrimaryPart, v_u_27.ArrowRight), p_u_24, function() --[[ Line: 166 ]]
            --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_6, (ref 3): v_u_28 ]]
            p_u_23._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            v_u_28:next_page()
        end))
        local v_u_34 = v_u_14:get_playable_song_set():key_list()
        v_u_34:sort(function(p35, p36) --[[ Line: 173 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            return v_u_9:singleton():get_difficulty_for_key(p36) - v_u_9:singleton():get_difficulty_for_key(p35);
        end)
        local v_u_37 = v_u_10:new(p_u_23, v_u_27.SongElementDisplay, v_u_4:new(v_u_26, v_u_27.PrimaryPart, v_u_27.SongElementDisplay.PrimaryPart))
        v_u_28 = v_u_8:new():set_fn_get_data_list(function() --[[ Line: 184 ]]
            --[[ Upvalues: (copy 1): v_u_34 ]]
            return v_u_34;
        end):set_fn_set_element_data(function(p38, p39) --[[ Line: 187 ]]
            p38:display_song(p39)
        end):set_fn_next_prev_visible(function(p40, p41) --[[ Line: 191 ]]
            --[[ Upvalues: (copy 1): v_u_33, (copy 2): v_u_32 ]]
            v_u_33:set_visible(p40)
            v_u_32:set_visible(p41)
        end):set_fn_update_page_display(function(p42, p43) --[[ Line: 195 ]]
            --[[ Upvalues: (copy 1): l_SongPageDisplay_0 ]]
            l_SongPageDisplay_0.Text = string.format("Song %d (of %d)", p42, p43)
        end):set_do_wrap(true):set_i_offset(v_u_22):set_fn_store_i_offset(function(p44) --[[ Line: 200 ]]
            --[[ Upvalues: (ref 1): v_u_22 ]]
            v_u_22 = p44
        end)
        v_u_28:push_display_element(v_u_37)
        v_u_28:page_update()
        v_u_26:add_cycle_element(p_u_23, 1, v_u_5:new(v_u_4:new(v_u_26, v_u_27.PrimaryPart, v_u_27.SongInfoButton), p_u_24, function() --[[ Line: 210 ]]
            --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_6, (ref 3): v_u_10, (copy 4): v_u_37 ]]
            p_u_23._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            v_u_10:show_song_info_popup(p_u_23, v_u_37:get_element_data())
        end))
        v_u_26:add_cycle_element(p_u_23, 1, v_u_5:new(v_u_4:new(v_u_26, v_u_27.PrimaryPart, v_u_27.PlayButton), p_u_24, function() --[[ Line: 266 ]]
            --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_6, (ref 3): v_u_11, (ref 4): v_u_12, (ref 5): v_u_18, (ref 6): v_u_14, (ref 7): v_u_17, (copy 8): v_u_37 ]]
            p_u_23._sfx_manager:play_sfx(v_u_6.SFX_MENU_OPEN)
            p_u_23._game_join_protocol:set_event_info(v_u_11.EventMission.GenericArtistP2Event)
            if p_u_23._player_settings_manager:get_key(v_u_12.Key.ArtistEventUseStage) == true then
                v_u_18:artist_event_set_custom_stage_id(v_u_14:get_stage_id())
            end;
            p_u_23._menus:push_menu(v_u_17:new(p_u_23, p_u_23._spui, p_u_23._menus, v_u_37:get_element_data()))
        end))
        v_u_30 = v_u_13:new(l_LoadedSection_0.ScrollingFrame.ScrollText1, l_LoadedSection_0.ScrollingFrame.ScrollText2)
        local function _() --[[ Name: update_scrolling_display ]] --[[ Line: 282 ]]
            --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_20, (ref 3): v_u_30, (ref 4): p_u_23, (ref 5): v_u_9 ]]
            local v45 = v_u_21:get(v_u_20)
            v_u_30:set_text("Now Playing: " .. v45.Name .. " - Album \'superglue\' by joan available now! ")
            p_u_23._bgm_manager:preview_songkey(v_u_9:invalid_songkey(), v45.AssetId, false)
        end;
        local v46 = v_u_21:get(v_u_20)
        v_u_30:set_text("Now Playing: " .. v46.Name .. " - Album \'superglue\' by joan available now! ")
        p_u_23._bgm_manager:preview_songkey(v_u_9:invalid_songkey(), v46.AssetId, false)
        v_u_26:add_cycle_element(p_u_23, 1, v_u_5:new(v_u_4:new(v_u_26, v_u_27.PrimaryPart, v_u_27.ScrollButtonLeft), p_u_24, function() --[[ Line: 292 ]]
            --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_6, (ref 3): v_u_20, (ref 4): v_u_21, (ref 5): v_u_30, (ref 6): v_u_9 ]]
            p_u_23._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            v_u_20 = v_u_20 - 1
            if v_u_20 < 1 then
                v_u_20 = v_u_21:count()
            end;
            local v47 = v_u_21:get(v_u_20)
            v_u_30:set_text("Now Playing: " .. v47.Name .. " - Album \'superglue\' by joan available now! ")
            p_u_23._bgm_manager:preview_songkey(v_u_9:invalid_songkey(), v47.AssetId, false)
        end))
        v_u_26:add_cycle_element(p_u_23, 1, v_u_5:new(v_u_4:new(v_u_26, v_u_27.PrimaryPart, v_u_27.ScrollButtonRight), p_u_24, function() --[[ Line: 305 ]]
            --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_6, (ref 3): v_u_20, (ref 4): v_u_21, (ref 5): v_u_30, (ref 6): v_u_9 ]]
            p_u_23._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            v_u_20 = v_u_20 + 1
            if v_u_20 > v_u_21:count() then
                v_u_20 = 1
            end;
            local v48 = v_u_21:get(v_u_20)
            v_u_30:set_text("Now Playing: " .. v48.Name .. " - Album \'superglue\' by joan available now! ")
            p_u_23._bgm_manager:preview_songkey(v_u_9:invalid_songkey(), v48.AssetId, false)
        end))
        v_u_26:add_cycle_element(p_u_23, 1, v_u_5:new(v_u_4:new(v_u_26, v_u_27.PrimaryPart, v_u_27.PreviewButton), p_u_24, function() --[[ Line: 318 ]]
            --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_6, (ref 3): v_u_21, (ref 4): v_u_20, (ref 5): v_u_9, (ref 6): v_u_31, (ref 7): v_u_26 ]]
            p_u_23._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            p_u_23._bgm_manager:preview_songkey(v_u_9:invalid_songkey(), v_u_21:get(v_u_20).AssetId, true)
            v_u_31 = false
            p_u_23._menus:remove_menu(v_u_26)
        end))
        v_u_26:transition_update_visual(0)
        v_u_26:layout()
    end;
    v_u_26.update_claim_button_status = function(_) end;
    v_u_26.on_refocus = function(p49) --[[ Name: on_refocus ]] --[[ Line: 341 ]]
        p49:update_claim_button_status()
    end;
    v_u_26.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 345 ]]
        --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_31, (copy 3): p_u_23, (ref 4): v_u_29 ]]
        v_u_27:Destroy()
        if v_u_31 then
            p_u_23._bgm_manager:stop_song_preview(v_u_29)
        end;
    end;
    v_u_26.visual_update = function(p50, p51, p52) --[[ Name: visual_update ]] --[[ Line: 353 ]]
        --[[ Upvalues: (copy 1): p_u_23 ]]
        if p_u_23:transition_local_camera_cframe_finished() ~= false then
            p50:visual_update_base(p51, p52)
        end;
    end;
    v_u_26.behaviour_update = function(p53, p54, _) --[[ Name: behaviour_update ]] --[[ Line: 361 ]]
        --[[ Upvalues: (copy 1): p_u_23, (ref 2): v_u_28, (ref 3): v_u_30 ]]
        p53:behaviour_update_base(p54, p_u_23)
        for _, v55 in v_u_28:get_display_elements():key_itr() do
            v55:behaviour_update(p54)
        end;
        v_u_30:update(p54)
    end;
    local v_u_56 = 1
    local v_u_57 = 1
    v_u_26.layout = function(p58) --[[ Name: layout ]] --[[ Line: 371 ]]
        --[[ Upvalues: (copy 1): p_u_24, (ref 2): v_u_57, (ref 3): v_u_27, (ref 4): v_u_28 ]]
        p58:opt_rescale_to_max_nxy(p_u_24, 0.8, 0.8, v_u_57)
        local v59, v60 = p58:opt_update_cframe_params(p_u_24, {
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p58:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v59 == true then
            v_u_27:SetPrimaryPartCFrame(v60)
        end;
        v_u_28:layout()
    end;
    v_u_26.set_alpha = function(_, p61) --[[ Name: set_alpha ]] --[[ Line: 384 ]]
        --[[ Upvalues: (ref 1): v_u_56, (ref 2): v_u_1, (ref 3): v_u_27 ]]
        if v_u_56 ~= p61 then
            v_u_56 = p61
            v_u_1:r_set_alpha(v_u_27, v_u_56)
        end;
    end;
    v_u_26.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 390 ]]
        --[[ Upvalues: (ref 1): v_u_56 ]]
        return v_u_56;
    end;
    v_u_26.set_scale = function(_, p62) --[[ Name: set_scale ]] --[[ Line: 391 ]]
        --[[ Upvalues: (ref 1): v_u_57 ]]
        v_u_57 = p62
    end;
    v_u_26.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 392 ]]
        --[[ Upvalues: (ref 1): v_u_57 ]]
        return v_u_57;
    end;
    v_u_26.get_native_size = function(p63) --[[ Name: get_native_size ]] --[[ Line: 394 ]]
        return p63._native_size;
    end;
    v_u_26.get_size = function(p64) --[[ Name: get_size ]] --[[ Line: 397 ]]
        return p64._size;
    end;
    v_u_26.set_size = function(p65, p66) --[[ Name: set_size ]] --[[ Line: 400 ]]
        --[[ Upvalues: (ref 1): v_u_27 ]]
        p65._size = p66
        v_u_27.PrimaryPart.Size = Vector3.new(p66.X, p66.Y, 0)
    end;
    v_u_26.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 404 ]]
        --[[ Upvalues: (ref 1): v_u_27 ]]
        return v_u_27.PrimaryPart.Position;
    end;
    v_u_26.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 407 ]]
        --[[ Upvalues: (ref 1): v_u_27 ]]
        return v_u_27.PrimaryPart.SurfaceGui;
    end;
    v_u_26.set_showing = function(_, p67) --[[ Name: set_showing ]] --[[ Line: 410 ]]
        --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_7 ]]
        if p67 then
            v_u_27.Parent = v_u_7:get_world_ui_folder()
        else
            v_u_27.Parent = nil
        end;
    end;
    f_cons()
    return v_u_26;
end;
return v19;
